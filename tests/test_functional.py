import pytest
import boto3

from cdn_bypass.lib import create_cloudfront_distribution, delete_cloudfront_distribution
from cdn_bypass.main import CloudFrontBypass


@pytest.fixture
def sess():
    return boto3.session.Session(region_name='us-east-1')


@pytest.fixture
def cloudfront(sess):
    return CloudFrontBypass(sess, 'example.com')


@pytest.fixture
def distribution(sess):
    return create_cloudfront_distribution(sess, 'target')


def test_delete_cloudfront_distribution(sess, distribution):
    assert delete_cloudfront_distribution(sess, distribution)


def test_deploy_destroy(cloudfront):
    cloudfront.deploy()
    cloudfront.destroy()
