import io
import zipfile
from dataclasses import dataclass
from pathlib import Path
from time import time, sleep
from typing import Optional

import botocore.exceptions

from cdn_proxy.lib import CdnProxyException, trim

# All JS and CSS is compiled into index.html, this just makes it easier to deploy and serve from the lambda.
STATIC_PAGE = Path(__file__).parent/'req_lambda/build/index.html'

@dataclass
class CloudFrontProxy:
    distribution_id: str
    domain: str


class CloudFront:
    def __init__(self, sess):
        self.sess = sess
        # Role names must be under 64 characters.
        self.lambda_role_name = "cdn-proxy-request"
        self.lambda_function_name = "cdn-proxy-request"
        self.lambda_arn = None
        self.lambda_role_arn = None
        self.distribution_id = None
        self.domain_name = None

        try:
            self.distribution = self.status(sess)
        except IndexError:
            self.distribution = None

    def create(self):
        proxy = self.status(self.sess)
        yield from self.create_lambda_role()
        yield from self.create_function(self.lambda_role_arn)

        if proxy:
            raise CdnProxyException(
                f"A deployment already exists. It can be accessed through the CloudFront "
                f"distribution {proxy.distribution_id} with a URL of https://{proxy.domain} or "
                f"http://{proxy.domain}."
            )

        yield from self.create_distribution(self.lambda_arn)
        yield from self.wait_for_distribution()
        yield f"Deployment completed."

    def delete(self):
        status = self.status(self.sess)
        if status:
            yield from self.delete_distribution(status.distribution_id)
        else:
            print("\n[ERROR] No existing deployment found.")

        try:
            yield from self.delete_lambda_role()
        except botocore.exceptions.ClientError as e:
            if e.response["Error"]["Code"] == "NoSuchEntity":
                print("\n[ERROR] No existing IAM Role found")
            else:
                raise e

        yield f"Deployment deleted"

    @staticmethod
    def status(sess) -> Optional[CloudFrontProxy]:
        client = sess.client("cloudfront")
        resp = client.list_distributions()
        for dist in resp.get("DistributionList", {}).get("Items", []):
            tags_resp = client.list_tags_for_resource(Resource=dist["ARN"])
            for item in tags_resp["Tags"]["Items"]:
                if item["Key"] == "cdn-proxy-target":
                    return CloudFrontProxy(
                        distribution_id=dist["Id"],
                        domain=dist["DomainName"],
                    )
        return None

    def create_lambda_role(self):
        yield f"Lambda Role {trim(self.lambda_role_name, 15)}... -- Creating"
        iam = self.sess.client("iam", region_name="us-east-1")

        try:
            resp = iam.get_role(RoleName=self.lambda_role_name)
            self.lambda_role_arn = resp["Role"]["Arn"]
            yield f"IAM Role {trim(self.lambda_role_name, 15)}... -- Already Exists"
            return
        except botocore.exceptions.ClientError as e:
            if e.response["Error"]["Code"] != "NoSuchEntity":
                raise e

        resp = iam.create_role(
            RoleName=self.lambda_role_name,
            AssumeRolePolicyDocument="""{
              "Version": "2012-10-17",
              "Statement": [
                {
                  "Effect": "Allow",
                  "Principal": {
                    "Service": [
                      "edgelambda.amazonaws.com",
                      "lambda.amazonaws.com"
                    ]
                  },
                  "Action": "sts:AssumeRole"
                }
              ]
            }""",
            Description="Execution roles for lambdas created by the cdn-bypass burp plugin.",
        )

        yield f"IAM Role {trim(self.lambda_role_name, 15)}... -- Adding Policy"
        iam.put_role_policy(
            RoleName=self.lambda_role_name,
            PolicyName="basic-execution",
            # TODO: fix resource
            PolicyDocument="""{{
                "Version": "2012-10-17",
                "Statement": [
                    {{
                        "Effect": "Allow",
                        "Action": "logs:CreateLogGroup",
                        "Resource": "arn:aws:logs:*:*:*"
                    }},
                    {{
                        "Effect": "Allow",
                        "Action": [
                            "logs:CreateLogStream",
                            "logs:PutLogEvents"
                        ],
                        "Resource": [
                            "arn:aws:logs:*:*:log-group:/aws/lambda/{name:}:*",
                            "arn:aws:logs:*:*:log-group:/aws/lambda/*.{name}:*"
                        ]
                    }}
                ]
            }}""".format(
                name=self.lambda_function_name
            ),
        )
        self.lambda_role_arn = resp["Role"]["Arn"]
        yield f"IAM Role {trim(self.lambda_role_name, 15)}... -- Created"

    def delete_lambda_role(self):
        yield f"IAM Role {trim(self.lambda_role_name, 15)}... -- Deleting"
        iam = self.sess.client("iam", region_name="us-east-1")

        iam.delete_role_policy(
            RoleName=self.lambda_role_name, PolicyName="basic-execution"
        )

        try:
            iam.delete_role(RoleName=self.lambda_role_name)
        except botocore.exceptions.ClientError as e:
            if e.response["Error"]["Code"] != "NoSuchEntity":
                raise e

        yield f"IAM Role {trim(self.lambda_role_name, 15)}... -- Deleted"

    def create_function(self, role_arn):
        yield f"Lambda {trim(self.lambda_function_name, 15)}... -- Creating"

        zip = io.BytesIO()
        with zipfile.ZipFile(zip, "w", zipfile.ZIP_DEFLATED) as zip_file:
            main = Path(__file__).parent / "req_lambda/main.py"
            with open(main, "r") as f:
                source_code = f.read()
            zip_file.writestr("main.py", source_code)

            with open(STATIC_PAGE, "r") as f:
                source_code = f.read()
            zip_file.writestr("index.html", source_code)

        lamb = self.sess.client("lambda", region_name="us-east-1")

        exists = False
        try:
            lamb.get_function(FunctionName=self.lambda_function_name)
            exists = True
        except botocore.exceptions.ClientError as e:
            if e.response["Error"]["Code"] != "ResourceNotFoundException":
                raise e

        if exists:
            zip.seek(0)
            resp = lamb.update_function_code(
                FunctionName=self.lambda_function_name,
                ZipFile=zip.read(),
                Publish=False,
            )
        else:
            i = 1
            resp = None
            while not resp:
                yield f"Lambda {trim(self.lambda_function_name, 15)}... -- Creating function ({i})"
                try:
                    zip.seek(0)
                    resp = lamb.create_function(
                        FunctionName=self.lambda_function_name,
                        Runtime="python3.8",
                        Role=role_arn,
                        Handler="main.lambda_handler",
                        Code={
                            "ZipFile": zip.read(),
                        },
                        Description="Request handler for the cdn-bypass Burp plugin.",
                        Timeout=30,
                        MemorySize=128,
                        Publish=False,
                        PackageType="Zip",
                    )
                except botocore.exceptions.ClientError as e:
                    # It seems this sometimes happens if the function is created to soon after creating the role.
                    if e.response["Error"]["Code"] != "InvalidParameterValueException":
                        raise e
                    i += 1
                    sleep(5)

            yield f"Lambda {trim(self.lambda_function_name, 15)}... -- Adding permissions"
            lamb.add_permission(
                StatementId="replicator",
                FunctionName=resp["FunctionName"],
                Principal="replicator.lambda.amazonaws.com",
                Action="lambda:GetFunction",
            )
            yield f"Lambda {trim(self.lambda_function_name, 15)}... -- Publishing"

        resp = lamb.publish_version(FunctionName=resp["FunctionName"])
        self.lambda_arn = resp["FunctionArn"]

    def delete_function(self):
        lamb = self.sess.client("lambda", region_name="us-east-1")
        yield f"Lambda {trim(self.lambda_function_name, 15)}... -- Deleting"

        # It seems deleting the versions first gets this process unstuck sometimes.
        versions = self.get_lambda_versions()

        # Append None to delete the main function.
        versions.append(None)

        for ver in versions:
            # It takes some time after you disassociate a lambda function from a CloudFront distribution before you can
            # delete it successfully.
            deleted = False
            for i in range(30):
                try:
                    yield f"Lambda {trim(self.lambda_function_name, 15)}... -- Deleting ({i}, this may " f"take a while)"
                    lamb.delete_function(
                        FunctionName=self.lambda_function_name, Qualifier=ver
                    )
                    deleted = True
                    break
                except botocore.exceptions.ClientError as e:
                    if e.response["Error"]["Code"] == "InvalidParameterValueException":
                        pass
                    elif e.response["Error"]["Code"] == "ResourceNotFoundException":
                        print(
                            "\n[ERROR] Lambda function {} not found.".format(
                                self.lambda_function_name
                            )
                        )
                        return
                    else:
                        raise e
                i += 1
                sleep(30)

            if not deleted:
                print(
                    "[ERROR] Failed to delete lambda function {}. This happens when Lambda@Edge functions have been "
                    "in use recently on a CloudFront distribution. Try removing this in an hour or so it should "
                    "work."
                )

        yield f"Lambda {trim(self.lambda_function_name, 15)}... -- Deleted"

    def create_distribution(self, lambda_arn):
        yield "Distribution -- Creating"
        client = self.sess.client("cloudfront", region_name="us-east-1")

        policy_name = "cdn-proxy"
        policy_id = None

        resp = client.list_origin_request_policies(Type="custom")
        for policy in resp["OriginRequestPolicyList"]["Items"]:
            if (
                policy["OriginRequestPolicy"]["OriginRequestPolicyConfig"]["Name"]
                == policy_name
            ):
                policy_id = policy["OriginRequestPolicy"]["Id"]

        if not policy_id:
            req_policy_resp = client.create_origin_request_policy(
                OriginRequestPolicyConfig={
                    "Comment": "Allow all w/ proto",
                    "Name": policy_name,
                    "HeadersConfig": {
                        "HeaderBehavior": "allViewerAndWhitelistCloudFront",
                        "Headers": {
                            "Quantity": 1,
                            "Items": [
                                "CloudFront-Forwarded-Proto",
                            ],
                        },
                    },
                    "CookiesConfig": {
                        "CookieBehavior": "all",
                    },
                    "QueryStringsConfig": {
                        "QueryStringBehavior": "all",
                    },
                }
            )
            policy_id = req_policy_resp["OriginRequestPolicy"]["Id"]

        resp = None
        i = 1
        while not resp:
            try:
                yield f"Distribution -- Creating ({i})"
                resp = client.create_distribution_with_tags(
                    DistributionConfigWithTags={
                        "DistributionConfig": {
                            "CallerReference": str(time()),
                            "Origins": {
                                "Quantity": 1,
                                "Items": [
                                    {
                                        "Id": "default",
                                        # Doesn't really matter what the origin is here, we require overriding it
                                        # via the Cdn-Proxy-Origin header in all requests.
                                        "DomainName": "example.com",
                                        "CustomOriginConfig": {
                                            "HTTPPort": 80,
                                            "HTTPSPort": 443,
                                            "OriginProtocolPolicy": "match-viewer",
                                            # TODO: Add option for this | 'match-viewer' | 'https-only',
                                            "OriginSslProtocols": {
                                                "Quantity": 4,
                                                "Items": [
                                                    "SSLv3",
                                                    "TLSv1",
                                                    "TLSv1.1",
                                                    "TLSv1.2",
                                                ],
                                            },
                                            "OriginReadTimeout": 30,  # TODO: Make this configurable.
                                        },
                                        "ConnectionAttempts": 1,  # TODO: Make this configurable.
                                        "ConnectionTimeout": 10,  # TODO: Make this configurable.
                                        "OriginShield": {
                                            "Enabled": False,
                                        },
                                    },
                                ],
                            },
                            "DefaultCacheBehavior": {
                                "TargetOriginId": "default",
                                "ViewerProtocolPolicy": "allow-all",
                                "AllowedMethods": {
                                    "Quantity": 7,
                                    "Items": [
                                        "GET",
                                        "HEAD",
                                        "POST",
                                        "PUT",
                                        "PATCH",
                                        "OPTIONS",
                                        "DELETE",
                                    ],
                                    "CachedMethods": {
                                        "Quantity": 2,
                                        "Items": [
                                            "GET",
                                            "HEAD",
                                        ],
                                    },
                                },
                                "Compress": False,
                                "LambdaFunctionAssociations": {
                                    "Quantity": 1,
                                    "Items": [
                                        {
                                            "LambdaFunctionARN": lambda_arn,
                                            "EventType": "origin-request",
                                            "IncludeBody": False,
                                        }
                                    ],
                                },
                                "CachePolicyId": "4135ea2d-6df8-44a3-9df3-4b5a84be39ad",
                                "OriginRequestPolicyId": policy_id,
                            },
                            "CacheBehaviors": {
                                "Quantity": 0,
                            },
                            "Comment": "cdn-proxy distribution",
                            "PriceClass": "PriceClass_100",
                            "Enabled": True,
                            "ViewerCertificate": {
                                "CloudFrontDefaultCertificate": True,
                                "MinimumProtocolVersion": "TLSv1.2_2018",
                            },
                            "HttpVersion": "http1.1",
                            "IsIPV6Enabled": False,
                        },
                        "Tags": {
                            "Items": [
                                {
                                    "Key": "cdn-proxy-target",
                                    "Value": "example.com",
                                },
                            ]
                        },
                    }
                )
            except botocore.exceptions.ClientError as e:
                if e.response["Error"]["Code"] == "DistributionAlreadyExists":
                    raise CdnProxyException(
                        "A distribution for the specified target already exists."
                    )
                # This seems to happen on the first try occasionally.
                elif e.response["Error"]["Code"] != "InvalidLambdaFunctionAssociation":
                    raise e
                i += 1
                sleep(10)
        self.distribution_id = resp["Distribution"]["Id"]
        self.domain_name = resp["Distribution"]["DomainName"]
        yield f"Distribution {self.distribution_id} -- Created (but not propagated)"

    def wait_for_distribution(self):
        yield "Distribution -- Waiting for propagation (this may take a while)"
        client = self.sess.client("cloudfront")
        waiter = client.get_waiter("distribution_deployed")
        waiter.wait(Id=self.distribution_id)
        yield f"Distribution {self.distribution_id} -- Created"

    def delete_distribution(self, dist_id):
        yield f"Distribution {dist_id} -- Getting current config"
        client = self.sess.client("cloudfront", region_name="us-east-1")
        try:
            resp = client.get_distribution_config(Id=dist_id)
        except botocore.exceptions.ClientError as e:
            if e.response["Error"]["Code"] == "NoSuchDistribution":
                raise CdnProxyException(
                    "The specified distribution ID does not exist.\n\nDid you pass a target "
                    "instead by chance? Try running `cdn-proxy cloudfront list` to get this value "
                    "if so."
                )
        config = resp["DistributionConfig"]
        config["Enabled"] = False
        config["DefaultCacheBehavior"]["LambdaFunctionAssociations"] = {
            "Quantity": 0,
        }
        yield f"Distribution {dist_id} -- Disabling"
        client.update_distribution(
            Id=dist_id, DistributionConfig=config, IfMatch=resp["ETag"]
        )
        yield f"Distribution {dist_id} -- Waiting for propagation (this may take a while)"
        waiter = client.get_waiter("distribution_deployed")
        waiter.wait(Id=dist_id)
        yield f"Distribution {dist_id} -- Deleting"
        resp = client.get_distribution_config(Id=dist_id)
        client.delete_distribution(Id=dist_id, IfMatch=resp["ETag"])
        yield f"Distribution {dist_id} -- Deleted"

    def get_lambda_versions(self):
        lamb = self.sess.client("lambda", region_name="us-east-1")
        resp = lamb.list_versions_by_function(FunctionName=self.lambda_function_name)
        versions = [v["Version"] for v in resp["Versions"]]
        versions.remove("$LATEST")
        return versions