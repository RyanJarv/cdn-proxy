import os

import pytest
import boto3
from moto import mock_iam, mock_lambda

from cdn_bypass.lib import create_function, create_lambda_role


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


# moto complains if you try to create a function using a role that doesn't exist, so these need to be tested together.
def test_lib(sess):
    role_arn = create_lambda_role(sess, 'test-function', 'lambda-cfn')
    create_function(sess, 'test-function', role_arn, 'target')