import request_handler
import user_util
import util_badges
from badges import Badge, BadgeCategory
from models_badges import CustomBadgeType
from models import UserData

class CustomBadge(Badge):

    @staticmethod
    def all():
        custom_badges = []
        custom_badge_types = CustomBadgeType.all().fetch(1000)
        for custom_badge_type in custom_badge_types:
            custom_badges.append(CustomBadge(custom_badge_type))
        return custom_badges

    def __init__(self, custom_badge_type):
        Badge.__init__(self)
        self.is_hidden_if_unknown = True

        self.name = custom_badge_type.key().name()
        self.description = custom_badge_type.description
        self.full_description = custom_badge_type.full_description
        self.points = custom_badge_type.points
        self.badge_category = custom_badge_type.category
        self.custom_icon_src = custom_badge_type.icon_src

    def is_satisfied_by(self, *args, **kwargs):
        return False # Custom badges are only handed out manually

    def extended_description(self):
        return self.full_description

    def icon_src(self):
        if self.custom_icon_src:
            return self.custom_icon_src
        return Badge.icon_src(self)

class CreateCustomBadge(request_handler.RequestHandler):
    @user_util.developer_only
    def get(self):
        template_values = {
                "badge_categories": [(badge_id, BadgeCategory.get_type_label(badge_id)) for badge_id in BadgeCategory.empty_count_dict()],
                "failed": self.request_bool("failed", default=False),
                }

        self.render_jinja2_template("badges/create_custom_badge.html", template_values)

    @user_util.developer_only
    def post(self):
        name = self.request_string("name")
        description = self.request_string("description")
        full_description = self.request_string("full_description")
        points = self.request_int("points", default = -1)
        badge_category = self.request_int("badge_category", default = -1)
        icon_src = self.request_string("icon_src", default="")

        # Create custom badge
        if CustomBadgeType.insert(name, description, full_description, points, badge_category, icon_src):

            util_badges.all_badges(bust_cache=True)
            util_badges.all_badges_dict(bust_cache=True)

            self.redirect("/badges/custom/award")
            return

        self.redirect("/badges/custom/create?failed=1")

class AwardCustomBadge(request_handler.RequestHandler):
    @user_util.developer_only
    def get(self):
        template_values = {
                "custom_badges": CustomBadge.all(),
                }

        self.render_jinja2_template("badges/award_custom_badge.html", template_values)

    @user_util.developer_only
    def post(self):
        custom_badge_name = self.request_string("name", default="")
        custom_badges = CustomBadge.all()
        custom_badge_awarded = None
        emails_awarded = []
        
        for custom_badge in custom_badges:
            if custom_badge.name == custom_badge_name:
                custom_badge_awarded = custom_badge

        if custom_badge_awarded:
            # Award badges and show successful email addresses
            emails_newlines = self.request_string("emails", default="")
            emails = emails_newlines.split()
            emails = map(lambda email: email.strip(), emails)

            for email in emails:
                user_data = UserData.get_from_user_input_email(email)
                if user_data:
                    if not custom_badge_awarded.is_already_owned_by(user_data):
                        custom_badge_awarded.award_to(user_data)
                        user_data.put()
                        emails_awarded.append(email)
        
        template_values = {
                "custom_badges": CustomBadge.all(),
                "custom_badge_awarded": custom_badge_awarded, 
                "emails_awarded": emails_awarded
                }

        self.render_jinja2_template("badges/award_custom_badge.html", template_values)

