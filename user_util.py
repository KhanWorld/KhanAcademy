from functools import wraps
import logging
import urllib

from google.appengine.api import users

import models
import request_cache

def admin_only(method):
    '''Decorator that requires a admin account.'''

    @wraps(method)
    def wrapper(self, *args, **kwargs):
        if users.is_current_user_admin():
            return method(self, *args, **kwargs)
        else:
            user_data = models.UserData.current()
            if user_data:
                logging.warning("Attempt by %s to access admin-only page" % user_data.user_id)

            # can't import util here because of circular dependencies
            url = "/login?continue=%s" % urllib.quote(self.request.uri)

            self.redirect(url)
            return

    return wrapper

@request_cache.cache()
def is_current_user_developer():
    user_data = models.UserData.current()
    return bool(users.is_current_user_admin() or (user_data and user_data.developer))

def developer_only(method):
    '''Decorator that requires a developer account.'''

    @wraps(method)
    def wrapper(self, *args, **kwargs):
        if is_current_user_developer():
            return method(self, *args, **kwargs)
        else:
            user_data = models.UserData.current()
            if user_data:
                logging.warning("Attempt by %s to access developer-only page" % user_data.user_id)

            # can't import util here because of circular dependencies
            url = "/login?continue=%s" % urllib.quote(self.request.uri)

            self.redirect(url)
            return

    return wrapper

