# AUTHOR: Dave Yesland @daveysec, Rhino Security Labs @rhinosecurity
# Burp Suite extension which uses AWS API Gateway to change your IP on every request to bypass IP blocking.
# More Info: https://rhinosecuritylabs.com/aws/bypassing-ip-based-blocking-aws/
from time import time

from javax.swing import JPanel, JTextField, JButton, JLabel, BoxLayout, JPasswordField, JCheckBox, JRadioButton, \
    ButtonGroup
from burp import IBurpExtender, IExtensionStateListener, ITab, IHttpListener
from java.awt import GridLayout
import boto3
import re

EXT_NAME = 'IP Rotate'
ENABLED = '<html><h2><font color="green">Enabled</font></h2></html>'
DISABLED = '<html><h2><font color="red">Disabled</font></h2></html>'
STAGE_NAME = 'burpendpoint'
API_NAME = 'BurpAPI'


class BurpExtender(IBurpExtender, IExtensionStateListener, ITab, IHttpListener):
    def __init__(self):
        self.allEndpoints = []
        self.currentEndpoint = 0
        self.aws_access_key_id = ''
        self.aws_secret_accesskey = ''

    def registerExtenderCallbacks(self, callbacks):
        self.callbacks = callbacks
        self.helpers = callbacks.helpers
        self.isEnabled = False

        callbacks.registerHttpListener(self)
        callbacks.registerExtensionStateListener(self)
        callbacks.setExtensionName(EXT_NAME)
        callbacks.addSuiteTab(self)

    def getTargetProtocol(self):
        if self.https_button.isSelected() == True:
            return 'https'
        else:
            return 'http'

    # AWS functions

    # Uses boto3 to test the AWS keys and make sure they are valid NOT IMPLEMENTED
    def testKeys(self):
        return

    # Uses boto3 to spin up an API Gateway
    def startAPIGateway(self):
        self.client = boto3.client(
            'cloudfront',
            aws_access_key_id=self.access_key.text,
            aws_secret_access_key=self.secret_key.text,
            region_name='us-east-1',
        )

        resp = self.client.create_distribution(
            DistributionConfig={
                'CallerReference': time(),
                'Origins': {
                    'Quantity': 1,
                    'Items': [
                        {
                            'Id': 'default',
                            'DomainName': self.target_host.text,
                            'CustomOriginConfig': {
                                'HTTPPort': 123,
                                'HTTPSPort': 123,
                                'OriginProtocolPolicy': 'http-only', # TODO: Add option for this | 'match-viewer' | 'https-only',
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
                            'Quantity': 7,
                            'Items': [
                                'GET',
                                'HEAD',
                                'POST',
                                'PUT',
                                'PATCH',
                                'OPTIONS',
                                'DELETE',
                            ]
                        }
                    },
                    'Compress': False,
                    # 'LambdaFunctionAssociations': {
                    #     'Quantity': 123,
                    #     'Items': [
                    #         {
                    #             'LambdaFunctionARN': 'string',
                    #             'EventType': 'viewer-request' | 'viewer-response' | 'origin-request' | 'origin-response',
                    #             'IncludeBody': True | False
                    #         },
                    #     ]
                    # },
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
        print resp
        self.distribution_id = resp['Distribution']['Id']

        print 'CloudFront deployed'

    # Uses boto3 to delete the API Gateway
    def deleteAPIGateway(self):
        self.client = boto3.client(
            'cloudfront',
            aws_access_key_id=self.access_key.text,
            aws_secret_access_key=self.secret_key.text,
            region_name='us-east-1',
        )

        resp = self.client.delete_distribution(
            Id=self.distribution_id,
        )
        print resp

        print 'CloudFront deleted'

    # Called on "save" button click to save the settings
    def saveKeys(self, event):
        aws_access_key_id = self.access_key.text
        aws_secret_access_key = self.secret_key.text
        self.callbacks.saveExtensionSetting("aws_access_key_id", aws_access_key_id)
        self.callbacks.saveExtensionSetting("aws_secret_access_key", aws_secret_access_key)
        return

    # Called on "Enable" button click to spin up the API Gateway
    def enableGateway(self, event):
        self.startAPIGateway()
        self.status_indicator.text = ENABLED
        self.isEnabled = True
        self.enable_button.setEnabled(False)
        self.secret_key.setEnabled(False)
        self.access_key.setEnabled(False)
        self.target_host.setEnabled(False)
        self.disable_button.setEnabled(True)
        return

    # Called on "Disable" button click to delete API Gateway
    def disableGateway(self, event):
        self.deleteAPIGateway()
        self.status_indicator.text = DISABLED
        self.isEnabled = False
        self.enable_button.setEnabled(True)
        self.secret_key.setEnabled(True)
        self.access_key.setEnabled(True)
        self.target_host.setEnabled(True)
        self.disable_button.setEnabled(False)
        return

    def getCurrEndpoint():

        return

    # Traffic redirecting
    def processHttpMessage(self, toolFlag, messageIsRequest, messageInfo):
        # only process requests
        if not messageIsRequest or not self.isEnabled:
            return

        # get the HTTP service for the request
        httpService = messageInfo.getHttpService()

        # Modify the request host, host header, and path to point to the new API endpoint
        # Should always use HTTPS because API Gateway only uses HTTPS
        if ':' in self.target_host.text:  # hacky fix for https://github.com/RhinoSecurityLabs/IPRotate_Burp_Extension/issues/14
            host_no_port = self.target_host.text.split(':')[0]

        else:
            host_no_port = self.target_host.text

        if (host_no_port == httpService.getHost()):
            # Cycle through all the endpoints each request until then end of the list is reached
            if self.currentEndpoint < len(self.allEndpoints) - 1:
                self.currentEndpoint += 1
            # Reset to 0 when end it reached
            else:
                self.currentEndpoint = 0

            messageInfo.setHttpService(
                self.helpers.buildHttpService(
                    self.allEndpoints[self.currentEndpoint],
                    443, True
                )
            )

            requestInfo = self.helpers.analyzeRequest(messageInfo)
            new_headers = requestInfo.headers

            # Update the path to point to the API Gateway path
            req_head = new_headers[0]
            # hacky fix for https://github.com/RhinoSecurityLabs/IPRotate_Burp_Extension/issues/14
            if 'http://' in req_head or 'https://' in req_head:
                cur_path = re.findall('https?:\/\/.*?\/(.*) ', req_head)[0]
                new_headers[0] = re.sub(' (.*?) ', " /" + STAGE_NAME + "/" + cur_path + " ", req_head)

            else:
                new_headers[0] = re.sub(' \/', " /" + STAGE_NAME + "/", req_head)

            # Replace the Host header with the Gateway host
            for header in new_headers:
                if header.startswith('Host: '):
                    host_header_index = new_headers.index(header)
                    new_headers[host_header_index] = 'Host: ' + self.allEndpoints[self.currentEndpoint]

            # Update the headers insert the existing body
            body = messageInfo.request[requestInfo.getBodyOffset():len(messageInfo.request)]
            messageInfo.request = self.helpers.buildHttpMessage(
                new_headers,
                body
            )

    # Tab name
    def getTabCaption(self):
        return EXT_NAME

    # Handle extension unloading
    def extensionUnloaded(self):
        self.deleteAPIGateway()
        return

    # Layout the UI
    def getUiComponent(self):
        aws_access_key_id = self.callbacks.loadExtensionSetting("aws_access_key_id")
        aws_secret_accesskey = self.callbacks.loadExtensionSetting("aws_secret_access_key")
        if aws_access_key_id:
            self.aws_access_key_id = aws_access_key_id
        if aws_secret_accesskey:
            self.aws_secret_accesskey = aws_secret_accesskey

        self.panel = JPanel()

        self.main = JPanel()
        self.main.setLayout(BoxLayout(self.main, BoxLayout.Y_AXIS))

        self.access_key_panel = JPanel()
        self.main.add(self.access_key_panel)
        self.access_key_panel.setLayout(BoxLayout(self.access_key_panel, BoxLayout.X_AXIS))
        self.access_key_panel.add(JLabel('Access Key: '))
        self.access_key = JTextField(self.aws_access_key_id, 25)
        self.access_key_panel.add(self.access_key)

        self.secret_key_panel = JPanel()
        self.main.add(self.secret_key_panel)
        self.secret_key_panel.setLayout(BoxLayout(self.secret_key_panel, BoxLayout.X_AXIS))
        self.secret_key_panel.add(JLabel('Secret Key: '))
        self.secret_key = JPasswordField(self.aws_secret_accesskey, 25)
        self.secret_key_panel.add(self.secret_key)

        self.target_host_panel = JPanel()
        self.main.add(self.target_host_panel)
        self.target_host_panel.setLayout(BoxLayout(self.target_host_panel, BoxLayout.X_AXIS))
        self.target_host_panel.add(JLabel('Target host: '))
        self.target_host = JTextField('example.com', 25)
        self.target_host_panel.add(self.target_host)

        self.buttons_panel = JPanel()
        self.main.add(self.buttons_panel)
        self.buttons_panel.setLayout(BoxLayout(self.buttons_panel, BoxLayout.X_AXIS))
        self.save_button = JButton('Save Keys', actionPerformed=self.saveKeys)
        self.buttons_panel.add(self.save_button)
        self.enable_button = JButton('Enable', actionPerformed=self.enableGateway)
        self.buttons_panel.add(self.enable_button)
        self.disable_button = JButton('Disable', actionPerformed=self.disableGateway)
        self.buttons_panel.add(self.disable_button)
        self.disable_button.setEnabled(False)

        self.protocol_panel = JPanel()
        self.main.add(self.protocol_panel)
        self.protocol_panel.setLayout(BoxLayout(self.protocol_panel, BoxLayout.Y_AXIS))
        self.protocol_panel.add(JLabel("Target Protocol:"))
        self.https_button = JRadioButton("HTTPS", True)
        self.http_button = JRadioButton("HTTP", False)
        self.protocol_panel.add(self.http_button)
        self.protocol_panel.add(self.https_button)
        buttongroup = ButtonGroup()
        buttongroup.add(self.https_button)
        buttongroup.add(self.http_button)

        self.status = JPanel()
        self.main.add(self.status)
        self.status.setLayout(BoxLayout(self.status, BoxLayout.X_AXIS))
        self.status_indicator = JLabel(DISABLED, JLabel.CENTER)
        self.status.add(self.status_indicator)

        self.panel.add(self.main)
        return self.panel
