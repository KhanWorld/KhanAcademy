import util
from badges import Badge, BadgeCategory
from templatefilters import seconds_to_time_string

# All badges awarded for completing being a member of the Khan Academy for various periods of time
# from TenureBadge
class TenureBadge(Badge):

    def is_satisfied_by(self, *args, **kwargs):
        user_data = kwargs.get("user_data", None)
        if user_data is None:
            return False

        # Make sure they've been a member for at least X years
        if user_data.joined is None or util.seconds_since(user_data.joined) < self.seconds_required:
            return False

        return True

    def extended_description(self):
        return "Remain a member of the Khan Academy for %s" % seconds_to_time_string(self.seconds_required)

class YearOneBadge(TenureBadge):
    def __init__(self):
        TenureBadge.__init__(self)
        self.seconds_required = 60 * 60 * 24 * 365
        self.description = "Cypress"
        self.badge_category = BadgeCategory.BRONZE
        self.points = 0

class YearTwoBadge(TenureBadge):
    def __init__(self):
        TenureBadge.__init__(self)
        self.seconds_required = 60 * 60 * 24 * 365 * 2
        self.description = "Redwood"
        self.badge_category = BadgeCategory.SILVER
        self.points = 0

class YearThreeBadge(TenureBadge):
    def __init__(self):
        TenureBadge.__init__(self)
        self.seconds_required = 60 * 60 * 24 * 365 * 3
        self.description = "Sequoia"
        self.badge_category = BadgeCategory.GOLD
        self.points = 0

