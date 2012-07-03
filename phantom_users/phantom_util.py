import os
import Cookie
import logging
import hashlib
from functools import wraps

import models
from cookie_util import set_request_cookie

# TODO: consolidate this with the constants in models.py:UserData
PHANTOM_ID_EMAIL_PREFIX = "http://nouserid.khanacademy.org/"
PHANTOM_MORSEL_KEY = 'ureg_id'

def is_phantom_id(user_id):
    return user_id.startswith(PHANTOM_ID_EMAIL_PREFIX)

def get_phantom_user_id_from_cookies():
    cookies = None
    try:
        cookies = Cookie.BaseCookie(os.environ.get('HTTP_COOKIE',''))
    except Cookie.CookieError, error:
        logging.critical("Ignoring Cookie Error: '%s'" % error)
        return None

    morsel = cookies.get(PHANTOM_MORSEL_KEY)
    if morsel and morsel.value:
        return PHANTOM_ID_EMAIL_PREFIX+morsel.value
    else:
        return None

def _create_phantom_user_id():
    rs = os.urandom(20)
    random_string = hashlib.md5(rs).hexdigest()
    return PHANTOM_ID_EMAIL_PREFIX+random_string

def create_phantom(method):
    '''Decorator used to create phantom users if necessary.

    Warning:
    - Only use on get methods where a phantom user should be created.
    '''

    @wraps(method)
    def wrapper(self, *args, **kwargs):
        user_data = models.UserData.current()

        if not user_data:
            user_id = _create_phantom_user_id()
            user_data = models.UserData.insert_for(user_id, user_id)

            # we set just a 20 digit random string as the cookie,
            # not the entire fake email
            cookie = user_id.split(PHANTOM_ID_EMAIL_PREFIX)[1]
            # set the cookie on the user's computer
            self.set_cookie(PHANTOM_MORSEL_KEY, cookie)
            # make it appear like the cookie was already set
            set_request_cookie(PHANTOM_MORSEL_KEY, str(cookie))

            # Bust the cache so later calls to models.UserData.current() return
            # the phantom user
            models.UserData.current(bust_cache=True)

        return method(self, *args, **kwargs)
    return wrapper

def api_create_phantom(method):
    '''Decorator used to create phantom users in api calls if necessary.'''

    @wraps(method)
    def wrapper(*args, **kwargs):
        if models.UserData.current():
            return method(*args, **kwargs)
        else:
            # This mirrors create_phantom above, see there for clarification
            user_id = _create_phantom_user_id()
            user_data = models.UserData.insert_for(user_id, user_id)

            cookie = user_data.email.split(PHANTOM_ID_EMAIL_PREFIX)[1]
            set_request_cookie(PHANTOM_MORSEL_KEY, str(cookie))

            user_data = models.UserData.current(bust_cache=True)

            if not user_data:
                logging.warning("api_create_phantom failed to create user_data properly")

            response = method(*args, **kwargs)

            response.set_cookie(PHANTOM_MORSEL_KEY, cookie)
            return response

    return wrapper

def disallow_phantoms(method, redirect_to='/login'):
    '''Decorator used to redirect phantom users.'''

    @wraps(method)
    def wrapper(self, *args, **kwargs):
        user_data = models.UserData.current()

        if user_data and user_data.is_phantom:
            self.redirect(redirect_to)
        else:
            return method(self, *args, **kwargs)
    return wrapper
