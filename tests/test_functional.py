# import pytest
# import boto3

# from cdn_proxy.lib import create_cloudfront_distribution, delete_cloudfront_distribution
# from cdn_proxy.main import CloudFrontBypass

from typer.testing import CliRunner

from cdn_proxy.cli import app

runner = CliRunner()


def test_cloudfront_create():
    result = runner.invoke(app, ["cloudfront", "create", "--host", "example.com", "example.com"])
    assert result.stdout == ""
    assert result.exit_code == 0

# @pytest.fixture
# def sess():
#     return boto3.session.Session(region_name='us-east-1')
#
#
# @pytest.fixture
# def cloudfront(sess):
#     return CloudFrontBypass(sess, 'example.com')
#
#
# @pytest.fixture
# def distribution(sess):
#     return create_cloudfront_distribution(sess, 'target')
#
#
# def test_delete_cloudfront_distribution(sess, distribution):
#     assert delete_cloudfront_distribution(sess, distribution)
#
#
# def test_deploy_destroy(cloudfront):
#     cloudfront.create()
#     cloudfront.destroy()
