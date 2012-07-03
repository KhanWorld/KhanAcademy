from google.appengine.api import users

import util
import user_util

class Privileges:

    UP_VOTE_THRESHOLD = 5000
    DOWN_VOTE_THRESHOLD = 20000

    @staticmethod
    def has_privilege(user_data, points_required):
        return user_util.is_current_user_developer() or \
                user_data.moderator or \
                user_data.points >= points_required

    @staticmethod
    def can_up_vote(user_data):
        return Privileges.has_privilege(user_data, Privileges.UP_VOTE_THRESHOLD)
    
    @staticmethod
    def can_down_vote(user_data):
        return Privileges.has_privilege(user_data, Privileges.DOWN_VOTE_THRESHOLD)

    @staticmethod
    def need_points_desc(points, verb):
        return "You need at least %s energy points to %s." % (util.thousands_separated_number(points), verb)
 
