from __future__ import print_function

from time import time

from cdn_bypass.lib import create_function, create_lambda_role, create_cloudfront_distribution


class CdnBypass:
    def __init__(self, target):
        self.target = target

    def deploy(self):
        pass

    def destroy(self):
        pass


LAMBDA_ROLE_NAME = 'cdn-bypass-lambda-execution'
LAMBDA_FUNCTION_NAME = 'cdn-bypass-lambda-request'


class CloudFrontBypass(CdnBypass):
    def __init__(self, sess, *args, **kwargs):
        self.sess = sess
        self.distribution_id = None
        super(CloudFrontBypass, self).__init__(*args, **kwargs)

    def deploy(self):
        create_lambda_role(LAMBDA_FUNCTION_NAME, LAMBDA_ROLE_NAME)
        create_function(LAMBDA_FUNCTION_NAME, LAMBDA_ROLE_NAME, self.target)
        self.distribution_id = create_cloudfront_distribution(self.target)
        print('CloudFront deployed')
        return self.distribution_id

    def destroy(self):
        client = self.sess.client('cloudfront', region_name='us-east-1')
        resp = client.delete_distribution(Id=self.distribution_id)
        print('CloudFront destroyed')
