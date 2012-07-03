import logging
import urllib
import urllib2
import datetime
import xml.dom.minidom as minidom

import simplejson

from app import App
import request_handler

CONSTANT_CONTACT_USERNAME = "shantanu@khanacademy.org"

def constant_contact_request(url, xml_payload = None, put_request = False):
    password_mgr = urllib2.HTTPPasswordMgrWithDefaultRealm()
    password_mgr.add_password(None, 
            "api.constantcontact.com", 
            App.constant_contact_api_key + "%" + App.constant_contact_username, 
            App.constant_contact_password)

    handler = urllib2.HTTPBasicAuthHandler(password_mgr)
    opener = urllib2.build_opener(handler)

    response = ""

    try:
        if xml_payload:
            request_entity = urllib2.Request(url, xml_payload, {"Content-Type": "application/atom+xml"})
            if put_request:
                request_entity.get_method = lambda: 'PUT'
            request = opener.open(request_entity)
        else:
            request = opener.open(url)
        response = request.read()
    except urllib2.HTTPError, e:
        return (e.code, "")

    return (200, response)

def create_new_constant_contact(email, list_url):

    contacts_url = "https://api.constantcontact.com/ws/customers/%s/contacts" % CONSTANT_CONTACT_USERNAME

    xml_payload = """<entry xmlns="http://www.w3.org/2005/Atom">
          <title type="text"> </title>
          <updated>%s</updated>
          <author></author>
          <id>data:,none</id>
          <summary type="text">Contact</summary>
          <content type="application/vnd.ctct+xml">
            <Contact xmlns="http://ws.constantcontact.com/ns/1.0/">
              <EmailAddress>%s</EmailAddress>
              <OptInSource>ACTION_BY_CONTACT</OptInSource>
              <ContactLists>
                <ContactList id="%s" />
              </ContactLists>
            </Contact>
          </content>
        </entry>""" % (str(datetime.datetime.now()), email, list_url)

    # Constant Contact passes back "201 Created" response for successful creation.
    return constant_contact_request(contacts_url, xml_payload)[0] == 201

def get_constant_contact_url(email):

    search_url = "https://api.constantcontact.com/ws/customers/%s/contacts?email=%s" % (CONSTANT_CONTACT_USERNAME, urllib.quote(email))
    xml_response = constant_contact_request(search_url)[1]

    if not xml_response:
        return ""

    dom_contact = minidom.parseString(xml_response)
    node_contact = dom_contact.getElementsByTagName("Contact")[0]

    url = node_contact.getAttribute("id")
    return url.replace("http:", "https:")

def add_list_to_constant_contact(email, list_url):

    contact_url = get_constant_contact_url(email)
    if not contact_url:
        return

    xml_contact = constant_contact_request(contact_url)[1]

    if not xml_contact:
        return

    dom_contact = minidom.parseString(xml_contact)
    node_contact = dom_contact.getElementsByTagName("entry")[0]
    node_contact_lists = node_contact.getElementsByTagName("ContactLists")[0]

    # Add new contactlist entity
    node_new_list = minidom.parseString("<ContactList id=\"%s\" />" % list_url).firstChild
    node_contact_lists.appendChild(node_new_list)

    resp = constant_contact_request(contact_url, node_contact.toxml(), True)

def subscribe_to_constant_contact(email, list_id):
    if not email or not list_id:
        return False

    list_url = "https://api.constantcontact.com/ws/customers/%s/lists/%s" % (CONSTANT_CONTACT_USERNAME, list_id)

    if create_new_constant_contact(email, list_url):
        return True
    else:
        # Contact may already exist. Try to modify.
        return add_list_to_constant_contact(email, list_url)

    return False

class Subscribe(request_handler.RequestHandler):
    def post(self):

        email = self.request_string("email")
        list_id = self.request_string("list_id")

        result = subscribe_to_constant_contact(email, list_id)
        self.response.out.write(simplejson.dumps({"result": result}, True))
