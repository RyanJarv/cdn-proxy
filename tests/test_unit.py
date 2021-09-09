import os
from unittest.mock import Mock

import pytest
import boto3
from moto import mock_iam, mock_lambda

from cdn_proxy.cloudfront import CloudFront, CloudFrontProxy
from cdn_proxy.lib import trim, networks_to_hosts


@pytest.fixture(scope="module")
def aws_credentials():
    """Mocked AWS Credentials for moto."""
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"


@pytest.fixture(scope="module")
def sess(aws_credentials):
    with (mock_iam(), mock_lambda()):
        yield boto3.session.Session(region_name="us-east-1")


@pytest.fixture(scope="module")
def cloudfront(sess) -> "CloudFront":
    CloudFront.status = Mock()
    CloudFront.status.return_value = CloudFrontProxy(
        distribution_id="test-id",
        domain="test-domain",
    )
    return CloudFront(sess)


# moto complains if you try to create a function using a role that doesn't exist, so these need to be tested together.
@pytest.fixture
def lambda_role_arn(cloudfront: "CloudFront") -> "CloudFront":
    for msg in cloudfront.create_lambda_role():
        print(msg)
    return cloudfront.lambda_role_arn


def test_lambda_role_arn(lambda_role_arn: str):
    assert lambda_role_arn == "arn:aws:iam::123456789012:role/cdn-proxy-request"


# moto complains if you try to create a function using a role that doesn't exist, so these need to be tested together.
@pytest.fixture
def function(cloudfront: "CloudFront", lambda_role_arn: "str") -> "CloudFront":
    for msg in cloudfront.create_function(cloudfront.lambda_role_arn):
        print(msg)


def test_get_lambda_versions(cloudfront: "CloudFront", function):
    assert cloudfront.get_lambda_versions() == ["1"]


def test_delete_lambda_role(cloudfront: "CloudFront"):
    cloudfront.delete_lambda_role()


def test_delete_function(cloudfront: "CloudFront", function):
    cloudfront.delete_function()


def test_trim():
    assert trim("1234567890", 7) == "1234567..."
    assert trim("123456", 7) == "123456"


def test_networks_to_hosts():
    assert list(networks_to_hosts(["192.168.0.1/32", "192.168.1.0/30"])) == [
        "192.168.0.1",
        "192.168.1.1",
        "192.168.1.2",
    ]
