import json
import urllib.parse
import urllib.request
from flask import Flask, request, jsonify
from flask_restful import Resource, Api, reqparse
from datetime import datetime
import nexmo
import messagebird
import ovh

app = Flask(__name__)
api = Api(app)


def ovhAPI(region, applicationKey, applicationSecret, consumerKey, recipient, message):
    client = ovh.Client(region,
                        application_key=applicationKey,
                        application_secret=applicationSecret,
                        consumer_key=consumerKey
                        )
    ck = client.new_consumer_key_request()
    ck.add_recursive_rules(ovh.API_READ_WRITE, "/sms")

    res = client.get('/sms')
    url = '/sms/' + res[0] + '/jobs'
    result_send = client.post(url,
                              charset='UTF-8',
                              coding='8bit',
                              message=message,
                              noStopClause=True,
                              priority='high',
                              receivers=[recipient],
                              senderForResponse=False,
                              validityPeriod=3600,
                              sender="LockSelf"
                              )

    print(json.dumps(result_send, indent=4))


def nexmoAPI(key, secret, messageTitle, recipient, message):
    client = nexmo.Client(key=key, secret=secret)

    client.send_message({
        'from': messageTitle,
        'to': recipient,
        'text': message
    })


def messageBirdAPI(key, messageTitle, recipient, message):
    client = messagebird.Client(key)
    message = client.message_create(
        messageTitle,
        recipient,
        message
    )
    print(message)


def telemessageAPI(username, password, recipient, message):
    url = "https://secure.telemessage.com/jsp/receiveSMS.jsp?userid=%s&password=%s&to=%s&text=%s" % (
        username, password, recipient, message)
    with urllib.request.urlopen(url) as f:
        if f.getcode() == 200:
            timestamp = datetime.now().strftime("[%Y-%m-%d %H:%M:%S %z]")
            print("%s Sent SMS to %s" % (timestamp, recipient))


class SMS(Resource):
    config = dict()

    def __init__(self):
        self.get_config()

    def get(self):
        return "SMS Proxy. Use POST (https://prometheus.io/docs/alerting/configuration/#webhook_config)."

    def get_config(self):
        with open('config') as f:
            self.config = json.load(f)

    def post(self):
        args = parser.parse_args()
        content = request.json

        try:
            if (self.config['username'] != "" and self.config['provider'] != "") or self.config['provider'] == "ovh":
                for a in content['alerts']:
                    print("tatat3")
                    prefix = "** "
                    if a['status'] in 'firing':
                        prefix = "** PROBLEM alert"

                    if a['status'] in 'resolved':
                        prefix = "** RECOVERY alert"

                    if self.config['provider'] == "ovh":
                        message = "%s - %s\n" % (prefix, a['labels'])
                    else:
                        message = urllib.parse.quote("%s - %s\nURL: %s" % (prefix, a['labels'], a['generatorURL']))

                    for recipient in self.config['recipients']:
                        print("tatat4")
                        if self.config['provider'] == "nexmo":
                            nexmoAPI(self.config['username'],
                                     self.config['password'],
                                     self.config['messageTitle'],
                                     recipient,
                                     message)
                        elif self.config['provider'] == "telemessage":
                            messageBirdAPI(self.config['username'],
                                           self.config['messageTitle'],
                                           recipient,
                                           message)
                        elif self.config['provider'] == "messagebird":
                            telemessageAPI(self.config['username'],
                                           self.config['password'],
                                           self.config['messageTitle'],
                                           recipient,
                                           message)
                        elif self.config['provider'] == "ovh":
                            ovhAPI(self.config['ovh_region'],
                                   self.config['ovh_application_key'],
                                   self.config['ovh_application_secret'],
                                   self.config['ovh_consumer_key'],
                                   recipient,
                                   message)
            else:
                print("Missing User/Key or SMS Provider")
        except Exception as e:
            print(e)


api.add_resource(SMS, '/')
parser = reqparse.RequestParser()

if __name__ == '__main__':
    app.run(debug=True)
