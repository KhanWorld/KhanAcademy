import cgi
import logging
import os
import urllib
import urlparse

from google.appengine.api import urlfetch

import flask
from flask import current_app, request, redirect, session
from flask.session import Session

from app import App
from api.auth.auth_models import OAuthMap
from api.auth.xsrf import validate_xsrf_value
from oauth_provider.oauth import build_authenticate_header, OAuthError
import cookie_util

def oauth_error_response(e):
    return current_app.response_class("OAuth error. %s" % e.message, status=401, headers=build_authenticate_header(realm="http://www.khanacademy.org"))

def unauthorized_response():
    return current_app.response_class("Unauthorized", status=401)

def access_token_response(oauth_map):
    if not oauth_map:
        raise OAuthError("Missing oauth_map while returning access_token_response")

    return "oauth_token=%s&oauth_token_secret=%s" % (oauth_map.access_token, oauth_map.access_token_secret)

def authorize_token_redirect(oauth_map):
    if not oauth_map:
        raise OAuthError("Missing oauth_map while returning authorize_token_redirect")

    if not oauth_map.callback_url:
        raise OAuthError("Missing callback URL during authorize_token_redirect")

    params = {
        "oauth_token": oauth_map.request_token,
        "oauth_token_secret": oauth_map.request_token_secret,
        "oauth_callback": oauth_map.callback_url_with_request_token_params(),
    }
    return redirect(append_url_params("/api/auth/authorize", params))

def custom_scheme_redirect(url_redirect):
    # urlparse.urlsplit doesn't currently handle custom schemes,
    # which we want our callback URLs to support so mobile apps can register
    # their own callback scheme handlers.
    # See http://bugs.python.org/issue9374
    # and http://stackoverflow.com/questions/1417958/parse-custom-uris-with-urlparse-python

    scheme = urlparse.urlsplit(url_redirect)[0]

    scheme_lists = [urlparse.uses_netloc, urlparse.uses_query, urlparse.uses_fragment, urlparse.uses_params, urlparse.uses_relative]
    scheme_lists_modified = []

    # Modify urlparse's internal scheme lists so it properly handles custom schemes
    if scheme:
        for scheme_list in scheme_lists:
            if scheme not in scheme_list:
                scheme_list.append(scheme)
                scheme_lists_modified.append(scheme_list)

    # Clear cache before re-parsing url_redirect
    urlparse.clear_cache()

    # Grab flask/werkzeug redirect result
    redirect_result = redirect(url_redirect)

    # Restore previous urlparse scheme list
    for scheme_list in scheme_lists_modified:
        scheme_list.remove(scheme)

    return redirect_result

def requested_oauth_callback():
    return request.values.get("oauth_callback") or ("%sapi/auth/default_callback" % request.host_url)

def allow_cookie_based_auth():

    # Don't allow cookie-based authentication for API calls which
    # may return JSONP, unless they include a valid XSRF token.
    path = os.environ.get("PATH_INFO")

    if path and path.lower().startswith("/api/"):
        return validate_xsrf_value()

    return True

def current_oauth_map():
    oauth_map = None

    if hasattr(flask.g, "oauth_map"):
        oauth_map = flask.g.oauth_map

    if not oauth_map and allow_cookie_based_auth():
        oauth_map = current_oauth_map_from_session_unsafe()

    return oauth_map

class RequestMock(object):
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

def current_oauth_map_from_session_unsafe():

    # We have to use plain 'ole cookie handling before we switch over to a Flask-only
    # app, at which point we can strictly rely on Flask sessions.
    session_cookie_name = "session"
    session_cookie_value = cookie_util.get_cookie_value(session_cookie_name)
    if session_cookie_value and App.flask_secret_key:

        # Strip double quotes
        if session_cookie_value.startswith("\""):
            session_cookie_value = session_cookie_value[1:-1]

        # Fake little Flask request object to load up the Flask session cookie.
        fake_request = RequestMock(cookies={session_cookie_name: unicode(session_cookie_value)})

        # Flask's sessions are secured by the secret key.
        session_cookie = Session.load_cookie(fake_request, session_cookie_name, secret_key=App.flask_secret_key)
        if session_cookie and session_cookie.has_key("oam"):

            oauth_map_id = session_cookie["oam"]
            oauth_map = OAuthMap.get_by_id_safe(oauth_map_id)
            if oauth_map:
                return oauth_map

    return None

def set_current_oauth_map_in_session():
    session["oam"] = flask.g.oauth_map.key().id()

def get_response(url, params={}):
    url_with_params = append_url_params(url, params)

    result = None

    # Be extra forgiving w/ timeouts during API auth consumer calls
    # in case Facebook or Google is slow.
    c_tries_left = 5
    while not result and c_tries_left > 0:

        try:
            result = urlfetch.fetch(url_with_params, deadline=10)
        except Exception, e:
            c_tries_left -= 1
            logging.warning("Trying to get response for %s again (tries left: %s) due to error: %s" % (url, c_tries_left, e.message))

    if result:

        if result.status_code == 200:
            return result.content
        else:
            raise OAuthError("Error in get_response, received status %s for url %s" % (result.status_code, url))

    elif c_tries_left == 0:

        raise OAuthError("Failed to get response for %s due to errors." % url)

    return ""

def append_url_params(url, params={}):
    if params:
        if "?" in url:
            url += "&"
        else:
            url += "?"
        url += urllib.urlencode(params)
    return url

def get_parsed_params(resp):
    if not resp:
        return {}
    return cgi.parse_qs(resp)
