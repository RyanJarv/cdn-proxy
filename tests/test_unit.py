import os
from unittest.mock import Mock

import pytest
import boto3
from moto import mock_iam, mock_lambda

from cdn_proxy.cloudfront import CloudFront, CloudFrontProxy


@pytest.fixture
def aws_credentials():
    """Mocked AWS Credentials for moto."""
    os.environ['AWS_ACCESS_KEY_ID'] = 'testing'
    os.environ['AWS_SECRET_ACCESS_KEY'] = 'testing'
    os.environ['AWS_SECURITY_TOKEN'] = 'testing'
    os.environ['AWS_SESSION_TOKEN'] = 'testing'


@pytest.fixture
def sess(aws_credentials):
    with (mock_iam(), mock_lambda()):
        yield boto3.session.Session(region_name='us-east-1')

@pytest.fixture
def cloudfront(sess):
    CloudFront.status = Mock()
    CloudFront.status.return_value = CloudFrontProxy(
        id='test-id',
        domain='test-domain',
    )
    return CloudFront(sess)


# moto complains if you try to create a function using a role that doesn't exist, so these need to be tested together.
def test_lib(cloudfront):
    role_arn = cloudfront.create_lambda_role('test-function', 'lambda-cfn')
    cloudfront.create_function('test-function', role_arn)