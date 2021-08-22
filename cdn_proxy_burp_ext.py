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


from cdn_bypass.main import CloudFrontBypass


# import xml.parsers.expat
# xml.parsers.expat._xerces_parser_name = "org.apache.xerces.parsers.SAXParser"

EXT_NAME = 'IP Rotate'
ENABLED = '<html><h2><font color="green">Enabled</font></h2></html>'
DISABLED = '<html><h2><font color="red">Disabled</font></h2></html>'
STAGE_NAME = 'burpendpoint'
API_NAME = 'BurpAPI'

# import xml.etree.ElementTree as ET
# ET.fromstring('<test></test>')

class BurpExtender(IBurpExtender, IExtensionStateListener, ITab, IHttpListener):
    def __init__(self):
        self.cloudfront = None
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

    # Called on "save" button click to save the settings
    def saveKeys(self, event):
        aws_access_key_id = self.access_key.text
        aws_secret_access_key = self.secret_key.text
        self.callbacks.saveExtensionSetting("aws_access_key_id", aws_access_key_id)
        self.callbacks.saveExtensionSetting("aws_secret_access_key", aws_secret_access_key)
        return

    # Called on "Enable" button click to spin up the API Gateway
    def deploy_cloudfront(self, event):
        sess = boto3.session.Session(
            aws_access_key_id=self.aws_access_key_id,
            aws_secret_access_key=self.aws_secret_accesskey,
        )
        self.cloudfront = CloudFrontBypass(sess, self.target_host)
        self.cloudfront.deploy()

    # Called on "Disable" button click to delete API Gateway
    def destroy_cloudfront(self, event):
        self.cloudfront.destroy()

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
        if self.cloudfront:
            self.destroy_cloudfront()

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
        self.enable_button = JButton('Enable', actionPerformed=self.deploy_cloudfront)
        self.buttons_panel.add(self.enable_button)
        self.disable_button = JButton('Disable', actionPerformed=self.destroy_cloudfront)
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
