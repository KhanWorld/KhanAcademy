#!/usr/bin/env python

# This hack is currently necessary to allow remote_api to work when the app is in Federated Login (aka OpenID) mode.
# For details, see: http://blog.notdot.net/2010/06/Using-remote-api-with-OpenID-authentication

from google.appengine.ext.remote_api import handler
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.api import users
import re

from app import App

cookie_re = re.compile('^"([^:]+):.*"$')

class ApiCallHandler(handler.ApiCallHandler):
  def CheckIsAdmin(self):
    if not App.accepts_openid or App.remote_api_secret is None:
      # We probably don't need to check both is_users.current_user_admin() 
      # and handler.ApiCallHandler.CheckIsAdmin(self) below, but since we don't have any
      # control over handler.ApiCallHandler.CheckIsAdmin(self), we are being extra careful.
      return App.is_dev_server or (users.is_current_user_admin() and handler.ApiCallHandler.CheckIsAdmin(self))
    login_cookie = self.request.cookies.get('dev_appserver_login', '')
    match = cookie_re.search(login_cookie)
    if (match and match.group(1) == App.remote_api_secret
        and 'X-appcfg-api-version' in self.request.headers):
      return True
    else:
      self.redirect('/_ah/login')
      return False


application = webapp.WSGIApplication([('.*', ApiCallHandler)])


def main():
  run_wsgi_app(application)


if __name__ == '__main__':
  main()

