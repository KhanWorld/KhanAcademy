from __future__ import absolute_import

from google.appengine.api import users
from google.appengine.ext import db

from models import UserData

def can_control_gandalf():
    """CUSTOMIZE can_control_gandalf however you want to specify
    whether or not the currently-logged-in user has access
    to Gandalf dashboard."
    """
    user_data = UserData.current(bust_cache=True)
    return users.is_current_user_admin() or (user_data and user_data.developer)

def current_logged_in_identity():
    """This should return one of the following:

        A) a db.Model that identifies the current user, like models.UserData.current()
        B) a unique string that consistently identifies the current user, like users.get_current_user().user_id()

    Ideally, this should be connected to your app's existing identity system.

    Examples:
        return models.UserData.current()
             ...or...
        from google.appengine.api import users
        return users.get_current_user().user_id() if users.get_current_user() else None"""
    return UserData.current(bust_cache=True)

def current_logged_in_identity_string():
    identity = current_logged_in_identity()

    if not identity:
        return None

    if isinstance(identity, db.Model):
        return str(identity.key())
    else:
        return str(identity)
