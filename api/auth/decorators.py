from functools import wraps

from google.appengine.api import users

import flask
from flask import request

from api.auth.auth_util import oauth_error_response, unauthorized_response
from api.auth.auth_models import OAuthMap

from oauth_provider.decorators import is_valid_request, validate_token
from oauth_provider.oauth import OAuthError

import util
import models

# TODO: rename this to be something more generic, since it's not just
# oauth specific.
def oauth_required(require_anointed_consumer = False):
    """ Decorator for validating an authenticated request.

    There are two possible cases of valid requests:
        1. using Oauth with valid tokens
        2. using cookie auth with a valid XSRF token presented in a header

    If a valid user is not retrieved from either of the two methods, an error
    is returned. Note that phantom users with exercise data is considered
    a valid user.

    """
    def outer_wrapper(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if is_valid_request(request):
                try:
                    consumer, token, parameters = validate_token(request)
                    if (not consumer) or (not token):
                        return oauth_error_response(OAuthError(
                                "Not valid consumer or token"))
                    # If this API method requires an anointed consumer,
                    # restrict any that haven't been manually approved.
                    if require_anointed_consumer and not consumer.anointed:
                        return oauth_error_response(OAuthError(
                                "Consumer access denied."))

                    # Store the OAuthMap containing all auth info in the request
                    # global for easy access during the rest of this request.
                    flask.g.oauth_map = OAuthMap.get_from_access_token(token.key_)

                    if not util.get_current_user_id():
                        # If our OAuth provider thinks you're logged in but the
                        # identity providers we consume (Google/Facebook)
                        # disagree, we act as if our token is no longer valid.
                        return oauth_error_response(OAuthError(
                            "Unable to get current user from oauth token"))

                except OAuthError, e:
                    return oauth_error_response(e)

            elif util.allow_cookie_based_auth():
                if not util.get_current_user_id_from_cookies_unsafe():
                    return oauth_error_response(OAuthError(
                            "Unable to read user value from cookies"))
            else:
                return oauth_error_response(OAuthError(
                        "Invalid parameters to Oauth request"))

            # Request validated - proceed with the method.
            return func(*args, **kwargs)

        return wrapper
    return outer_wrapper

def oauth_optional(require_anointed_consumer = False):
    """ Decorator for validating an oauth request and storing the OAuthMap for use
    in the rest of the request.

    If oauth credentials don't pass, continue on,
    but util.get_current_user_id() may return None.

    """
    def outer_wrapper(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if is_valid_request(request):
                try:
                    consumer, token, parameters = validate_token(request)
                    if consumer and token:

                        # Store the OAuthMap containing all auth info in the request global
                        # for easy access during the rest of this request.
                        flask.g.oauth_map = OAuthMap.get_from_access_token(token.key_)

                        # If this API method requires an anointed consumer,
                        # restrict any that haven't been manually approved.
                        if require_anointed_consumer and not consumer.anointed:
                            flask.g.oauth_map = None

                        if not util.get_current_user_id():
                            # If our OAuth provider thinks you're logged in but the
                            # identity providers we consume (Google/Facebook) disagree,
                            # we act as if our token is no longer valid.
                            flask.g.oauth_map = None

                except OAuthError, e:
                    # OAuthErrors are ignored, treated as user that's just not logged in
                    pass

            # Run decorated function regardless of whether or not oauth succeeded
            return func(*args, **kwargs)

        return wrapper
    return outer_wrapper

def admin_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):

        # Make sure current UserData exists as well as is_current_user_admin
        # because UserData properly verifies xsrf token
        user_data = models.UserData.current()

        if user_data and users.is_current_user_admin():
            return func(*args, **kwargs)

        return unauthorized_response()
    return wrapper

def developer_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        user_data = models.UserData.current()

        if user_data and (users.is_current_user_admin() or user_data.developer):
            return func(*args, **kwargs)

        return unauthorized_response()
    return wrapper

