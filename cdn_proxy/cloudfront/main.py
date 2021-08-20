import io
import os
import re
import zipfile
from pathlib import Path
from time import time, sleep

import botocore.exceptions

from cdn_proxy.lib import CdnProxyException


class CloudFront:
    def __init__(self, sess, target, x_forwarded_for=None):
        self.sess = sess
        self.target = target
        self.x_forwarded_for = x_forwarded_for
        self.lambda_role_name = 'cdn-bypass-lambda-execution-{}'.format(target.replace('.', '-'))
        self.lambda_function_name = 'cdn-bypass-lambda-request-{}'.format(target.replace('.', '-'))
        self.lambda_arn = None
        self.lambda_role_arn = None
        self.distribution_id = None
        self.domain_name = None

    def create(self):
        yield from self.create_lambda_role()
        yield from self.create_function(self.lambda_role_arn)
        yield from self.create_distribution(self.lambda_arn)
        yield from self.wait_for_distribution()
        yield f'Deployment for {self.target} finished.'

    def delete(self):
        try:
            dist_id = dict(self.__class__.list(self.sess))[self.target]
            yield from self.delete_distribution(dist_id)
        except KeyError:
            print('\n[ERROR] No distribution found for target "{}"'.format(self.target))

        yield from self.delete_function()

        try:
            yield from self.delete_lambda_role()
        except botocore.exceptions.ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchEntity':
                print('\n[ERROR] No IAM Role found for target "{}"'.format(self.target))
            else:
                raise e

        yield f'Deployment for {self.target} deleted'

    @staticmethod
    def list(sess):
        client = sess.client('cloudfront')
        resp = client.list_distributions()
        for dist in resp['DistributionList']['Items']:
            tags_resp = client.list_tags_for_resource(Resource=dist['ARN'])
            for item in tags_resp['Tags']['Items']:
                if item['Key'] == 'cdn-proxy-target':
                    yield item['Value'], dist['Id']

    def create_lambda_role(self):
        yield f'Lambda@Edge IAM Role {self.lambda_role_name} -- Creating'
        iam = self.sess.client('iam', region_name='us-east-1')

        try:
            resp = iam.get_role(RoleName=self.lambda_role_name)
            self.lambda_role_arn = resp['Role']['Arn']
            yield f'Lambda@Edge IAM Role {self.lambda_role_name} -- Already Exists'
            return
        except botocore.exceptions.ClientError as e:
            if e.response['Error']['Code'] != 'NoSuchEntity':
                raise e

        resp = iam.create_role(
            RoleName=self.lambda_role_name,
            AssumeRolePolicyDocument='''{
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
            }''',
            Description='Execution roles for lambdas created by the cdn-bypass burp plugin.',
        )

        yield f'Lambda@Edge IAM Role {self.lambda_role_name} -- Adding Policy'
        iam.put_role_policy(
            RoleName=self.lambda_role_name,
            PolicyName='basic-execution',
            PolicyDocument='''{{
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
                            "arn:aws:logs:*:*:log-group:/aws/lambda/{}:*"
                        ]
                    }}
                ]
            }}'''.format(self.lambda_function_name)
        )
        self.lambda_role_arn = resp['Role']['Arn']
        yield f'Lambda@Edge IAM Role {self.lambda_role_name} -- Created'

    def delete_lambda_role(self):
        yield f'Lambda@Edge IAM Role {self.lambda_role_name} -- Deleting'
        iam = self.sess.client('iam', region_name='us-east-1')

        iam.delete_role_policy(RoleName=self.lambda_role_name, PolicyName='basic-execution')

        try:
            iam.delete_role(RoleName=self.lambda_role_name)
        except botocore.exceptions.ClientError as e:
            if e.response['Error']['Code'] != 'NoSuchEntity':
                raise e

        yield f'Lambda@Edge IAM Role {self.lambda_role_name} -- Deleted'

    def create_function(self, lambda_role_arn):
        yield f'Lambda@Edge Function {self.lambda_function_name} -- Creating package'
        main = Path(__file__).parents[1]/'lambdas/request/main.py'
        with open(main, 'r') as f:
            source_code = f.read()

        # Lambda@Edge functions can't use environment variables so set this as a global.
        source_code = re.sub(r'HOST\s+=.*$', 'HOST = "{}"'.format(self.target), source_code)

        if self.x_forwarded_for:
            source_code = re.sub(r'X_FORWARDED_FOR\s+=.*$', 'X_FORWARDED_FOR = "{}"'.format(self.x_forwarded_for),
                                 source_code)

        zip = io.BytesIO()
        with zipfile.ZipFile(zip, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            zip_file.writestr('main.py', source_code)
        zip.seek(0)

        lamb = self.sess.client('lambda', region_name='us-east-1')

        try:
            resp = lamb.get_function(FunctionName=self.lambda_function_name)
            latest = self.get_latest_lambda_version(resp['Configuration']['FunctionName'])
            self.lambda_arn = "{}:{}".format(resp['Configuration']['FunctionArn'], latest)
            return
        except botocore.exceptions.ClientError as e:
            if e.response['Error']['Code'] != 'ResourceNotFoundException':
                raise e

        yield f'Lambda@Edge Function {self.lambda_function_name} -- Creating function'
        resp = lamb.create_function(
            FunctionName=self.lambda_function_name,
            Runtime='python3.8',
            Role=lambda_role_arn,
            Handler='main.lambda_handler',
            Code={
                'ZipFile': zip.read(),
            },
            Description='Request handler for the cdn-bypass Burp plugin.',
            Timeout=30,
            MemorySize=128,
            Publish=False,
            PackageType='Zip',
        )

        yield f'Lambda@Edge Function {self.lambda_function_name} -- Adding replicator permissions'
        lamb.add_permission(
            StatementId='replicator',
            FunctionName=resp['FunctionName'],
            Principal='replicator.lambda.amazonaws.com',
            Action='lambda:GetFunction',
        )
        yield f'Lambda@Edge Function {self.lambda_function_name} -- Publishing latest version'
        lamb.publish_version(FunctionName=resp['FunctionName'])

        latest = self.get_latest_lambda_version(resp['FunctionName'])
        self.lambda_arn = "{}:{}".format(resp['FunctionArn'], latest)

    def delete_function(self):
        lamb = self.sess.client('lambda', region_name='us-east-1')
        yield f'Lambda@Edge Function {self.lambda_function_name} -- Deleting'

        # It takes some time after you disassociate a lambda function from a CloudFront distribution before you can
        # delete it successfully.
        while True:
            i = 1
            try:
                yield f'Lambda@Edge Function {self.lambda_function_name} -- Deleting (attempt {i}, this may take a ' \
                      'while)'
                lamb.delete_function(FunctionName=self.lambda_function_name)
                break
            except botocore.exceptions.ClientError as e:
                if e.response['Error']['Code'] == 'InvalidParameterValueException':
                    pass
                elif e.response['Error']['Code'] == 'ResourceNotFoundException':
                    print("\n[ERROR] Lambda function {} not found.".format(self.lambda_function_name))
                    return
                else:
                    raise e

            i += 1
            sleep(10)

        yield f'Lambda@Edge Function {self.lambda_function_name} -- Deleted'

    def create_distribution(self, lambda_arn):
        yield 'CloudFront Distribution -- Creating'
        client = self.sess.client('cloudfront', region_name='us-east-1')
        try:
            resp = client.create_distribution_with_tags(
                DistributionConfigWithTags={
                    'DistributionConfig': {
                        'CallerReference': str(time()),
                        'Origins': {
                            'Quantity': 1,
                            'Items': [
                                {
                                    'Id': 'default',
                                    'DomainName': self.target,
                                    'CustomOriginConfig': {
                                        'HTTPPort': 80,
                                        'HTTPSPort': 443,
                                        'OriginProtocolPolicy': 'http-only',
                                        # TODO: Add option for this | 'match-viewer' | 'https-only',
                                        'OriginSslProtocols': {
                                            'Quantity': 4,
                                            'Items': [
                                                'SSLv3',
                                                'TLSv1',
                                                'TLSv1.1',
                                                'TLSv1.2',
                                            ]
                                        },
                                    },
                                    'OriginShield': {
                                        'Enabled': False,
                                    }
                                },
                            ]
                        },
                        'DefaultCacheBehavior': {
                            'TargetOriginId': 'default',
                            'ViewerProtocolPolicy': 'allow-all',
                            'AllowedMethods': {
                                'Quantity': 7,
                                'Items': [
                                    'GET',
                                    'HEAD',
                                    'POST',
                                    'PUT',
                                    'PATCH',
                                    'OPTIONS',
                                    'DELETE',
                                ],
                                'CachedMethods': {
                                    'Quantity': 2,
                                    'Items': [
                                        'GET',
                                        'HEAD',
                                    ]
                                }
                            },
                            'Compress': False,
                            'LambdaFunctionAssociations': {
                                'Quantity': 1,
                                'Items': [
                                    {
                                        'LambdaFunctionARN': lambda_arn,
                                        'EventType': 'origin-request',
                                        'IncludeBody': False,
                                    },
                                    # Rewrite all links?
                                    # {
                                    #     'LambdaFunctionARN': ...,
                                    #     'EventType': 'origin-response',
                                    #     'IncludeBody': True | False
                                    # },
                                ]
                            },
                            'CachePolicyId': '4135ea2d-6df8-44a3-9df3-4b5a84be39ad',
                        },
                        'CacheBehaviors': {
                            'Quantity': 0,
                        },
                        'Comment': 'cdn-proxy distribution for {}'.format(self.target),
                        'PriceClass': 'PriceClass_100',
                        'Enabled': True,
                        'ViewerCertificate': {
                            'CloudFrontDefaultCertificate': True,
                            'MinimumProtocolVersion': 'TLSv1.2_2018',
                        },
                        'HttpVersion': 'http1.1',
                        'IsIPV6Enabled': False,
                    },
                    'Tags': {
                        'Items': [
                            {
                                'Key': 'cdn-proxy-target',
                                'Value': self.target,
                            },
                        ]
                    }
                }
            )
        except botocore.exceptions.ClientError as e:
            if e.response['Error']['Code'] == 'DistributionAlreadyExists':
                raise CdnProxyException('A distribution for the specified target already exists.')
            else:
                raise e
        self.distribution_id = resp['Distribution']['Id']
        self.domain_name = resp['Distribution']['DomainName']
        yield f'CloudFront Distribution {self.distribution_id} -- Created (but not propagated)'

    def wait_for_distribution(self):
        yield 'CloudFront Distribution -- Waiting for propagation (this may take a while)'
        client = self.sess.client('cloudfront')
        waiter = client.get_waiter('distribution_deployed')
        waiter.wait(Id=self.distribution_id)
        yield f'CloudFront Distribution {self.distribution_id} -- Created'

    def delete_distribution(self, dist_id):
        yield f'CloudFront Distribution {dist_id} -- Getting current config'
        client = self.sess.client('cloudfront', region_name='us-east-1')
        try:
            resp = client.get_distribution_config(Id=dist_id)
        except botocore.exceptions.ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchDistribution':
                raise CdnProxyException('The specified distribution ID does not exist.\n\nDid you pass a target '
                                        'instead by chance? Try running `cdn-proxy cloudfront list` to get this value '
                                        'if so.')
        config = resp['DistributionConfig']
        config['Enabled'] = False
        config['DefaultCacheBehavior']['LambdaFunctionAssociations'] = {
            "Quantity": 0,
        }
        yield f'CloudFront Distribution {dist_id} -- Disabling'
        client.update_distribution(Id=dist_id, DistributionConfig=config, IfMatch=resp['ETag'])
        yield f'CloudFront Distribution {dist_id} -- Waiting for propagation (this may take a while)'
        waiter = client.get_waiter('distribution_deployed')
        waiter.wait(Id=dist_id)
        yield f'CloudFront Distribution {dist_id} -- Deleting'
        resp = client.get_distribution_config(Id=dist_id)
        client.delete_distribution(Id=dist_id, IfMatch=resp['ETag'])
        yield f'CloudFront Distribution {dist_id} -- Deleted'

    # Apparently the latest version isn't always 1, even if we just created the function.
    def get_latest_lambda_version(self, lambda_name):
        lamb = self.sess.client('lambda', region_name='us-east-1')
        resp = lamb.list_versions_by_function(FunctionName=lambda_name)
        versions = [v['Version'] for v in resp['Versions']]
        versions.remove('$LATEST')
        return max(versions)