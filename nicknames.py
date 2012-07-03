from phantom_users.phantom_util import is_phantom_id
import facebook_util

# Now that we're supporting unicode nicknames, ensure all callers get a
# consistent type of object back by converting everything to unicode.
# This fixes issue #4297.
def to_unicode(s):
    if not isinstance(s, unicode):
        return unicode(s, 'utf-8', 'ignore')
    else:
        return s

def get_nickname_for(user_data):

    if not user_data:
        return None

    user_id = user_data.user_id
    email = user_data.email

    if not user_id or not email:
        return None
        
    if facebook_util.is_facebook_user_id(user_id):
        nickname = facebook_util.get_facebook_nickname(user_id)
    elif is_phantom_id(user_id):
        nickname =  "" # No nickname, results in "Login" in header
    else:
        nickname = email.split('@')[0]
    return to_unicode(nickname)
