import io
import zipfile
from datetime import time
from pathlib import Path

import botocore.exceptions
import boto3.exceptions


def create_function(sess, function_name, role_arn, target):
    source_code = (Path(__file__).parent / 'lambdas/request/main.py').read_text()
    zip = io.BytesIO()
    with zipfile.ZipFile(zip, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        zip_file.writestr('main.py', source_code)
    zip.seek(0)

    lamb = sess.client('lambda', region_name='us-east-1')
    lambda_exists = False
    try:
        lamb.get_function(FunctionName=function_name)
        lambda_exists = True
    except Exception as e:
        if e.response['Error']['Code'] != 'ResourceNotFoundException':
            raise e

    if not lambda_exists:
        lamb.create_function(
            FunctionName=function_name,
            Runtime='python3.9',
            Role=role_arn,
            Handler='main.lambda_handler',
            Code={
                'ZipFile': zip.read(),
            },
            Description='Request handler for the cdn-bypass Burp plugin.',
            Timeout=31,
            MemorySize=128,
            Publish=True,
            PackageType='Zip',
            Environment={
                'Variables': {
                    'HOST': target,
                }
            },
        )


def create_lambda_role(sess, function_name, role_name):
    iam = sess.client('iam', region_name='us-east-1')
    role_exists = False
    try:
        iam.get_role(RoleName=role_name)
        role_exists = True
    except botocore.exceptions.ClientError as e:
        if e.response['Error']['Code'] != 'NoSuchEntity':
            raise e

    if role_exists:
        return

    resp = iam.create_role(
        RoleName=role_name,
        AssumeRolePolicyDocument='''
            {
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
            }
        ''',
        Description='Execution roles for lambdas created by the cdn-bypass burp plugin.',
    )
    iam.put_role_policy(
        RoleName=role_name,
        PolicyName='basic-execution',
        PolicyDocument=f'''
            {{
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
                            "arn:aws:logs:*:*:log-group:/aws/lambda/{function_name}:*"
                        ]
                    }}
                ]
            }}
        '''
    )
    return resp['Role']['Arn']


def create_cloudfront_distribution(sess, target):
    client = sess.client('cloudfront', region_name='us-east-1')
    resp = client.create_distribution(
        DistributionConfig={
            'CallerReference': str(time()),
            'Origins': {
                'Quantity': 1,
                'Items': [
                    {
                        'Id': 'default',
                        'DomainName': target,
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
                            'LambdaFunctionARN': ...,
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
            'Comment': 'cdn-bypass todo update description',
            'PriceClass': 'PriceClass_100',
            'Enabled': True,
            'ViewerCertificate': {
                'CloudFrontDefaultCertificate': True,
                'MinimumProtocolVersion': 'TLSv1.2_2018',
            },
            'HttpVersion': 'http1.1',
            'IsIPV6Enabled': False,
        }
    )
    return resp['Distribution']['Id']
