import datetime
import logging
import urllib
import urllib2

from google.appengine.api import mail

from app import App
import request_handler

#PAYPAL_IPN_URL = "https://www.sandbox.paypal.com/cgi-bin/webscr"
PAYPAL_IPN_URL = "https://www.paypal.com/cgi-bin/webscr"

FROM_EMAIL = "no-reply@khan-academy.appspotmail.com"

# See http://blog.awarelabs.com/2008/paypal-ipn-python-code/ for inspiration
class IPN(request_handler.RequestHandler):

    def get(self):
        self.post()

    def post(self):

        if self.request_string("payment_status") != "Completed":
            logging.error("Paypal IPN payment_status was not 'Completed': %s" % (self.request_string("payment_status")))
            return

        # Wrap up all params
        charset = self.request_string("charset")
        parameters = dict((arg, self.request_string(arg).encode(charset)) for arg in self.request.arguments())
        logging.info("Paypal params: %s" % parameters)

        # Send 'em back to paypal for validation
        parameters["cmd"]="_notify-validate"
        req = urllib2.Request(PAYPAL_IPN_URL, urllib.urlencode(parameters))
        req.add_header("Content-type", "application/x-www-form-urlencoded")

        try:
            response = urllib2.urlopen(req)
            status = response.read()
        except Exception, e:
            logging.error("Error while verifying Paypal IPN request: %s" % e)
            raise

        # If verified as legit...
        if status != "VERIFIED":
            logging.error("Paypal IPN request could not be verified, ignoring. %s" % status)
            return

        email = parameters["payer_email"]
        first_name = parameters.get("first_name", "")

        greeting = ""
        if first_name:
            greeting = "Dear %s,\n\n" % first_name

        # ...send thank you email
        mail.send_mail( \
                sender = FROM_EMAIL, \
                to = email, \
                subject = "Thank you!", \
                body = """%sWe greatly appreciate your contribution. With the support of generous donors like you, we are able to increase our efforts to create more video and exercise content, translate content into the world's most common languages, improve our website functionality, and extend our educational reach.

We are excited about the progress that has been made, but we realize that we have only just begun. Thank you for believing in Khan Academy and supporting our mission to provide a free world class education to anyone anywhere.

Best wishes,

Sal Khan

Khan Academy, a 501(c)(3) not for profit organization, has not provided any goods or services to you in consideration for this voluntary contribution. The donation is tax deductible to the extent allowed by law. For federal tax purposes Khan Academy's FEIN # is: 26-1544963. 
""" % greeting)

        logging.info("Sent 'thank you for your donation' email to %s" % email)

