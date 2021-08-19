import io
import os
import re
import zipfile
from datetime import time

import botocore.exceptions

from botocore.compat import XMLParseError
from xml.etree import ElementTree
from xml.etree import cElementTree


def xml_parser(**_):
    class Parser(object):
        def feed(self, data):
            """Feed encoded data to parser."""
            try:
                self.parser.Parse(data, False)
            except self._error as v:
                self._raiseerror(v)

        @staticmethod
        def close(self):
            """Finish feeding data to parser and return element structure."""
            try:
                self.parser.Parse(b"", True) # end of data
            except self._error as v:
                self._raiseerror(v)
            try:
                close_handler = self.target.close
            except AttributeError:
                pass
            else:
                return close_handler()
            finally:
                # get rid of circular references
                del self.parser, self._parser
                del self.target, self._target

    return Parser()


# ElementTree.XMLParser = xml_parser
cElementTree.XMLParser = xml_parser

# from xml.parsers import expat
# expat._mangled_xerces_parser_name = "org.apache.xerces.parsers.SAXParser"


import xml
if "_xmlplus" in xml.__path__[0]: # PyXML sub-module
    xml.__path__.reverse() # If both are available, prefer stdlib over PyXML
# import xml.parsers.expat
# xml.parsers.expat._xerces_parser_name = "org.apache.xerces.parsers.SAXParser"
# from java.net import URLClassLoader
# from java.lang import Thread
# from java.net import URL


def create_function(sess, function_name, role_arn, target):
    main = os.path.join(os.path.split(__file__)[0], 'lambdas/request/main.py')
    with open(main, 'r') as f:
        source_code = f.read()
    # Lambda@Edge functions can't use environment variables so set this as a global.
    source_code = re.sub(r'HOST\w+=.*$', 'HOST = {}'.format(target), source_code)

    zip = io.BytesIO()
    with zipfile.ZipFile(zip, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        zip_file.writestr('main.py', source_code)
    zip.seek(0)

    lamb = sess.client('lambda', region_name='us-east-1')

    try:
        resp = lamb.get_function(FunctionName=function_name)
        latest = get_latest_lambda_version(sess, resp['Configuration']['FunctionName'])
        return "{}:{}".format(resp['Configuration']['FunctionArn'], latest)
    except botocore.exceptions.ClientError as e:
        if e.response['Error']['Code'] != 'ResourceNotFoundException':
            raise e

    resp = lamb.create_function(
        FunctionName=function_name,
        Runtime='python3.8',
        Role=role_arn,
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

    lamb.add_permission(
        StatementId='replicator',
        FunctionName=resp['FunctionName'],
        Principal='replicator.lambda.amazonaws.com',
        Action='lambda:GetFunction',
    )
    lamb.publish_version(FunctionName=resp['FunctionName'])

    latest = get_latest_lambda_version(sess, resp['FunctionName'])
    return "{}:{}".format(resp['FunctionArn'], latest)


# Apparently the latest version isn't always 1, even if we just created the function.
def get_latest_lambda_version(sess, lambda_name):
    lamb = sess.client('lambda', region_name='us-east-1')
    resp = lamb.list_versions_by_function(FunctionName=lambda_name)
    versions = [v['Version'] for v in resp['Versions']]
    versions.remove('$LATEST')
    return max(versions)

def create_lambda_role(sess, function_name, role_name):
    iam = sess.client('iam', region_name='us-east-1')

    try:
        resp = iam.get_role(RoleName=role_name)
        return resp['Role']['Arn']
    except botocore.exceptions.ClientError as e:
        if e.response['Error']['Code'] != 'NoSuchEntity':
            raise e

    resp = iam.create_role(
        RoleName=role_name,
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
    iam.put_role_policy(
        RoleName=role_name,
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
        }}'''.format(function_name)
    )
    return resp['Role']['Arn']


def create_cloudfront_distribution(sess, target, lambda_arn):
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


def delete_cloudfront_distribution(sess, distribution_id):
    client = sess.client('cloudfront', region_name='us-east-1')
    resp = client.get_distribution_config(Id=distribution_id)
    config = resp['DistributionConfig']
    config['Enabled'] = False
    client.update_distribution(Id=distribution_id, DistributionConfig=config, IfMatch=resp['ETag'])
    waiter = client.get_waiter('distribution_deployed')
    waiter.wait(Id=distribution_id)
    resp = client.get_distribution_config(Id=distribution_id)
    client.delete_distribution(Id=distribution_id, IfMatch=resp['ETag'])
