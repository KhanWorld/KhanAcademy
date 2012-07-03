import logging
import urllib
import os

import flask
from flask import request, redirect
from flask import current_app

from api import route
from api.auth.auth_models import OAuthMap
from api.auth.auth_util import oauth_error_response, append_url_params, requested_oauth_callback, access_token_response, custom_scheme_redirect, set_current_oauth_map_in_session
from api.auth.google_util import google_request_token_handler
from api.auth.facebook_utils import facebook_request_token_handler
from api.auth.decorators import oauth_required

from oauth_provider.oauth import OAuthError
from oauth_provider.utils import initialize_server_request
from oauth_provider.stores import check_valid_callback

# Our API's OAuth authentication and authorization is designed to encapsulate the OAuth support
# of our identity providers (Google/Facebook), so each of our mobile apps and client applications 
# don't have to handle each auth provider independently. We behave as one single OAuth set of endpoints
# for them to interact with.

# Request token endpoint
#
# Flask-friendly version of oauth_providers.oauth_request.RequestTokenHandler that 
# hands off to Google/Facebook to gather the appropriate request tokens.
@route("/api/auth/request_token", methods=["GET", "POST"])
def request_token():

    oauth_server, oauth_request = initialize_server_request(request)

    if oauth_server is None:
        return oauth_error_response(OAuthError('Invalid request parameters.'))

    try:
        # Create our request token
        token = oauth_server.fetch_request_token(oauth_request)
    except OAuthError, e:
        return oauth_error_response(e)

    if OAuthMap.get_from_request_token(token.key_):
        return oauth_error_response(OAuthError("OAuth parameters already used."))

    # Start a new OAuth mapping
    oauth_map = OAuthMap()
    oauth_map.request_token_secret = token.secret
    oauth_map.request_token = token.key_
    oauth_map.callback_url = requested_oauth_callback()
    
    if request.values.get("view") == "mobile":
        oauth_map.view = "mobile"

    oauth_map.put()

    chooser_url = "/login/mobileoauth?oauth_map_id=%s&view=%s" % (oauth_map.key().id(), oauth_map.view)

    oauth_consumer = oauth_server._get_consumer(oauth_request)
    if oauth_consumer and oauth_consumer.anointed:
        chooser_url += "&an=1"

    return redirect(chooser_url)

@route("/api/auth/request_token_callback/<provider>/<oauth_map_id>", methods=["GET"])
def request_token_callback(provider, oauth_map_id):

    oauth_map = OAuthMap.get_by_id_safe(oauth_map_id)
    if not oauth_map:
        return oauth_error_response(OAuthError("Unable to find OAuthMap by id during request token callback."))

    if provider == "google":
        return google_request_token_handler(oauth_map)
    elif provider == "facebook":
        return facebook_request_token_handler(oauth_map)

# Token authorization endpoint
#
# Flask-friendly version of oauth_providers.oauth_request.AuthorizeHandler that doesn't
# require user authorization for our side of the OAuth. Just log in, and we'll authorize.
@route("/api/auth/authorize", methods=["GET", "POST"])
def authorize_token():

    oauth_server, oauth_request = initialize_server_request(request)

    if oauth_server is None:
        return oauth_error_response(OAuthError('Invalid request parameters.'))

    try:
        # get the request token
        token = oauth_server.fetch_request_token(oauth_request)
    except OAuthError, e:
        return oauth_error_response(e)

    oauth_map = OAuthMap.get_from_request_token(token.key_)
    if not oauth_map:
        raise OAuthError("Unable to find oauth_map from request token during authorization.")

    # Get user from oauth map using either FB or Google access token
    user_data = oauth_map.get_user_data()
    if not user_data:
        return oauth_error_response(OAuthError("User not logged in during authorize_token process."))

    try:
        # For now we don't require user intervention to authorize our tokens,
        # since the user already authorized FB/Google. If we need to do this
        # for security reasons later, there's no reason we can't.
        token = oauth_server.authorize_token(token, user_data.user)
        oauth_map.verifier = token.verifier
        oauth_map.put()

        return custom_scheme_redirect(oauth_map.callback_url_with_request_token_params(include_verifier=True))

    except OAuthError, e:
        return oauth_error_response(e)

# Access token endpoint
#
# Flask-friendly version of oauth_providers.oauth_request.AccessTokenHandler
# that creates our access token and then hands off to Google/Facebook to let them
# create theirs before associating the two.
@route("/api/auth/access_token", methods=["GET", "POST"])
def access_token():

    oauth_server, oauth_request = initialize_server_request(request)

    if oauth_server is None:
        return oauth_error_response(OAuthError('Invalid request parameters.'))

    try:
        # Create our access token
        token = oauth_server.fetch_access_token(oauth_request)
        if not token:
            return oauth_error_response(OAuthError("Cannot find corresponding access token."))

        # Grab the mapping of access tokens to our identity providers 
        oauth_map = OAuthMap.get_from_request_token(oauth_request.get_parameter("oauth_token"))
        if not oauth_map:
            return oauth_error_response(OAuthError("Cannot find oauth mapping for request token."))

        oauth_map.access_token = token.key_
        oauth_map.access_token_secret = token.secret
        oauth_map.put()

    except OAuthError, e:
        return oauth_error_response(e)

    return access_token_response(oauth_map)

# Default callback
#
# If user doesn't supply an oauth_callback parameter, we'll send 'em here
# when redirecting after request_token creation and authorization.
@route("/api/auth/default_callback", methods=["GET"])
def default_callback():
    return "OK"

# Use OAuth token to login via session cookie
@route("/api/auth/token_to_session", methods=["GET"])
@oauth_required(require_anointed_consumer=True)
def token_to_session():
    set_current_oauth_map_in_session()
    return redirect(request.request_string("continue", default="/"))
