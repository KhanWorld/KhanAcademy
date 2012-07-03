import util
import models_badges
import phantom_users.util_notify
from notifications import UserNotifier

# Badges can either be Exercise badges (can earn one for every Exercise),
# Playlist badges (one for every Playlist),
# or context-less which means they can only be earned once.
class BadgeContextType:
    NONE = 0
    EXERCISE = 1
    PLAYLIST = 2

class BadgeCategory(object):
    # Sorted by astronomical size...
    BRONZE = 0 # Meteorite, "Common"
    SILVER = 1 # Moon, "Uncommon"
    GOLD = 2 # Earth, "Rare"
    PLATINUM = 3 # Sun, "Epic"
    DIAMOND = 4 # Black Hole, "Legendary"
    MASTER = 5 # Summative/Academic Achievement

    _serialize_blacklist = [
            "BRONZE", "SILVER", "GOLD",
            "PLATINUM", "DIAMOND", "MASTER",
            ]

    def __init__(self, category):
        self.category = category

    @staticmethod
    def empty_count_dict():
        count_dict = {}
        for category in BadgeCategory.list_categories():
            count_dict[category] = 0
        return count_dict

    @staticmethod
    def all():
        return map(lambda category: BadgeCategory(category),
                   BadgeCategory.list_categories())

    @staticmethod
    def list_categories():
        return [
            BadgeCategory.BRONZE,
            BadgeCategory.SILVER,
            BadgeCategory.GOLD,
            BadgeCategory.PLATINUM,
            BadgeCategory.DIAMOND,
            BadgeCategory.MASTER,
        ]

    @property
    def description(self):
        return BadgeCategory.get_description(self.category)

    @staticmethod
    def get_description(category):
        if category == BadgeCategory.BRONZE:
            return "Meteorite badges are common and easy to earn when just getting started."
        elif category == BadgeCategory.SILVER:
            return "Moon badges are uncommon and represent an investment in learning."
        elif category == BadgeCategory.GOLD:
            return "Earth badges are rare. They require a significant amount of learning."
        elif category == BadgeCategory.PLATINUM:
            return "Sun badges are epic. Earning them is a true challenge, and they require impressive dedication."
        elif category == BadgeCategory.DIAMOND:
            return "Black Hole badges are legendary and unknown. They are the most unique Khan Academy awards."
        elif category == BadgeCategory.MASTER:
            return "Challenge Patches are special awards for completing challenge exercises."
        return ""

    @property
    def icon_src(self):
        return BadgeCategory.get_icon_src(self.category)

    @staticmethod
    def get_icon_src(category):
        src = "/images/badges/half-moon-small.png"

        if category == BadgeCategory.BRONZE:
            src = "/images/badges/meteorite-small.png"
        elif category == BadgeCategory.SILVER:
            src = "/images/badges/moon-small.png"
        elif category == BadgeCategory.GOLD:
            src = "/images/badges/earth-small.png"
        elif category == BadgeCategory.PLATINUM:
            src = "/images/badges/sun-small.png"
        elif category == BadgeCategory.DIAMOND:
            src = "/images/badges/eclipse-small.png"
        elif category == BadgeCategory.MASTER:
            src = "/images/badges/master-challenge-blue-small.png"

        return util.static_url(src)

    @property
    def large_icon_src(self):
        return BadgeCategory.get_large_icon_src(self.category)

    @staticmethod
    def get_large_icon_src(category):
        src = "/images/badges/half-moon.png"

        if category == BadgeCategory.BRONZE:
            src = "/images/badges/meteorite.png"
        elif category == BadgeCategory.SILVER:
            src = "/images/badges/moon.png"
        elif category == BadgeCategory.GOLD:
            src = "/images/badges/earth.png"
        elif category == BadgeCategory.PLATINUM:
            src = "/images/badges/sun.png"
        elif category == BadgeCategory.DIAMOND:
            src = "/images/badges/eclipse.png"
        elif category == BadgeCategory.MASTER:
            src = "/images/badges/master-challenge-blue.png"

        return util.static_url(src)

    @property
    def chart_icon_src(self):
        return BadgeCategory.get_chart_icon_src(self.category)

    @staticmethod
    def get_chart_icon_src(category):
        src = "/images/badges/meteorite-small-chart.png"

        if category == BadgeCategory.BRONZE:
            src = "/images/badges/meteorite-small-chart.png"
        elif category == BadgeCategory.SILVER:
            src = "/images/badges/moon-small-chart.png"
        elif category == BadgeCategory.GOLD:
            src = "/images/badges/earth-small-chart.png"
        elif category == BadgeCategory.PLATINUM:
            src = "/images/badges/sun-small-chart.png"
        elif category == BadgeCategory.DIAMOND:
            src = "/images/badges/eclipse-small-chart.png"
        elif category == BadgeCategory.MASTER:
            src = "/images/badges/master-challenge-blue-chart.png"

        return util.static_url(src)

    @property
    def type_label(self):
        return BadgeCategory.get_type_label(self.category)

    @staticmethod
    def get_type_label(category):
        if category == BadgeCategory.BRONZE:
            return "Meteorite"
        elif category == BadgeCategory.SILVER:
            return "Moon"
        elif category == BadgeCategory.GOLD:
            return "Earth"
        elif category == BadgeCategory.PLATINUM:
            return "Sun"
        elif category == BadgeCategory.DIAMOND:
            return "Black Hole"
        elif category == BadgeCategory.MASTER:
            return "Challenge Patches"
        return "Common"

# Badge is the base class used by various badge subclasses (ExerciseBadge, PlaylistBadge, TimedProblemBadge, etc).
# 
# Each baseclass overrides sets up a couple key pieces of data (description, badge_category, points)
# and implements a couple key functions (is_satisfied_by, is_already_owned_by, award_to, extended_description).
#
# The most important rule to follow with badges is to *never talk to the datastore when checking is_satisfied_by or is_already_owned_by*.
# Many badge calculations need to run every time a user answers a question or watches part of a video, and a couple slow badges can slow down
# the whole system.
# These functions are highly optimized and should only ever use data that is already stored in UserData or is passed as optional keyword arguments
# that have already been calculated / retrieved.
class Badge(object):

    _serialize_whitelist = [
            "points", "badge_category", "description",
            "safe_extended_description", "name", "user_badges"
            ]

    def __init__(self):
        # Initialized by subclasses:
        #   self.description,
        #   self.badge_category,
        #   self.points

        # Keep .name constant even if description changes.
        # This way we only remove existing badges from people if the class name changes.
        self.name = self.__class__.__name__.lower()
        self.badge_context_type = BadgeContextType.NONE

        # Replace the badge's description with question marks
        # on the "all badges" page if the badge hasn't been achieved yet
        self.is_teaser_if_unknown = False

        # Hide the badge from all badge lists if it hasn't been achieved yet
        self.is_hidden_if_unknown = False

        self.is_owned = False
        
    @staticmethod
    def add_target_context_name(name, target_context_name):
        return "%s[%s]" % (name, target_context_name)

    @staticmethod
    def remove_target_context(name_with_context):
        ix = name_with_context.rfind("[")
        if ix >= 0:
            return name_with_context[:ix]
        else:
            return name_with_context

    def category_description(self):
        return BadgeCategory.get_description(self.badge_category)

    def icon_src(self):
        return BadgeCategory.get_icon_src(self.badge_category)

    def chart_icon_src(self):
        return BadgeCategory.get_chart_icon_src(self.badge_category)

    def type_label(self):
        return BadgeCategory.get_type_label(self.badge_category)

    def name_with_target_context(self, target_context_name):
        if target_context_name is None:
            return self.name
        else:
            return Badge.add_target_context_name(self.name, target_context_name)

    def is_hidden(self):
        return self.is_hidden_if_unknown and not self.is_owned

    @property
    def safe_extended_description(self):
        desc = self.extended_description()
        if self.is_teaser_if_unknown and not self.is_owned:
            desc = "???"
        return desc

    # Overridden by individual badge implementations
    def extended_description(self):
        return ""

    # Overridden by individual badge implementations which each grab various parameters from args and kwargs.
    # *args and **kwargs should contain all the data necessary for is_satisfied_by's logic, and implementations of is_satisfied_by 
    # should never talk to the datastore or memcache, etc.
    def is_satisfied_by(self, *args, **kwargs):
        return False

    # Overridden by individual badge implementations which each grab various parameters from args and kwargs
    # *args and **kwargs should contain all the data necessary for is_already_owned_by's logic, and implementations of is_already_owned_by
    # should never talk to the datastore or memcache, etc.
    def is_already_owned_by(self, user_data, *args, **kwargs):
        return self.name in user_data.badges

    # Calculates target_context and target_context_name from data passed in and calls complete_award_to appropriately.
    #
    # Overridden by individual badge implementations which each grab various parameters from args and kwargs
    # It's ok for award_to to talk to the datastore, because it is run relatively infrequently.
    def award_to(self, user_data, *args, **kwargs):
        self.complete_award_to(user_data)

    # Awards badge to user within given context
    def complete_award_to(self, user_data, target_context=None, target_context_name=None):
        name_with_context = self.name_with_target_context(target_context_name)
        key_name = user_data.key_email + ":" + name_with_context

        if user_data.badges is None:
            user_data.badges = []

        user_data.badges.append(name_with_context)

        user_badge = models_badges.UserBadge.get_by_key_name(key_name)

        if user_badge is None:
            user_data.add_points(self.points)

            user_badge = models_badges.UserBadge(
                    key_name = key_name,
                    user = user_data.user,
                    badge_name = self.name,
                    target_context = target_context,
                    target_context_name = target_context_name,
                    points_earned = self.points)

            user_badge.put()

        # call notifications
        phantom_users.util_notify.update(user_data,None,threshold = False, isProf = False, gotBadge = True)
        UserNotifier.push_badge_for_user_data(user_data, user_badge)

    def frequency(self):
        return models_badges.BadgeStat.count_by_badge_name(self.name)
