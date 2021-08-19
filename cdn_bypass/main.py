from __future__ import print_function

from time import time

from cdn_bypass.lib import create_function, create_lambda_role, create_cloudfront_distribution, \
    delete_cloudfront_distribution


# import xml.parsers.expat
# xml.parsers.expat._xerces_parser_name = "org.apache.xerces.parsers.SAXParser"

class CdnBypass(object):
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
        role_arn = create_lambda_role(self.sess, LAMBDA_FUNCTION_NAME, LAMBDA_ROLE_NAME)
        # lambda_arn = create_function(self.sess, LAMBDA_FUNCTION_NAME, role_arn, self.target)
        # self.distribution_id = create_cloudfront_distribution(self.sess, self.target, lambda_arn)
        print('CloudFront deployed')
        # return self.distribution_id

    def destroy(self):
        delete_cloudfront_distribution(self.sess, self.distribution_id)
