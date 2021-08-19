import pytest
import boto3

from cdn_bypass.lib import create_cloudfront_distribution
from cdn_bypass.main import CloudFrontBypass


@pytest.fixture
def sess():
    return boto3.session.Session(region_name='us-east-1')


@pytest.fixture
def cloudfront(sess):
    return CloudFrontBypass(sess, 'example.com')


def test_create_cloudfront_distribution(cloudfront):
    assert create_cloudfront_distribution(sess, 'target')
