import cookie_util
import base64
import os
import logging
import time
from functools import wraps
from api import XSRF_API_VERSION, XSRF_COOKIE_KEY, XSRF_HEADER_KEY, is_current_api_version

def ensure_xsrf_cookie(func):
    """ This is a decorator for a method that ensures when the response to
    this request is sent, the user's browser has the appropriate XSRF cookie
    set.
    
    The XSRF cookie is required for making successful API calls from our site
    for calls that require oauth.
    """
    @wraps(func)
    def wrapper(self, *args, **kwargs):

        xsrf_token = get_xsrf_cookie_value()
        if not xsrf_token or not is_current_api_version(xsrf_token):
            timestamp = int(time.time())
            xsrf_value = "%s_%s_%d" % (XSRF_API_VERSION, base64.urlsafe_b64encode(os.urandom(10)), timestamp)

            # Set a cookie containing the XSRF value.
            # The JavaScript is responsible for returning the cookie in a matching header
            # that is validated by validate_xsrf_cookie.
            self.set_cookie(XSRF_COOKIE_KEY, xsrf_value, httponly=False)
            cookie_util.set_request_cookie(XSRF_COOKIE_KEY, xsrf_value)

        return func(self, *args, **kwargs)

    return wrapper

def get_xsrf_cookie_value():
    return cookie_util.get_cookie_value(XSRF_COOKIE_KEY)

def validate_xsrf_value():
    header_value = os.environ.get(XSRF_HEADER_KEY)
    cookie_value = get_xsrf_cookie_value()
    if not header_value or not cookie_value or header_value != cookie_value:
        logging.info("Mismatch between XSRF header (%s) and cookie (%s)" % (header_value, cookie_value))
        return False
        
    return True
