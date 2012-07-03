import os

import shared_jinja
from notifications import UserNotifier

def login_notifications(user_data, continue_url):
    login_notifications = UserNotifier.pop_for_current_user_data()["login"]
    return login_notifications_html(login_notifications, user_data, continue_url)

def login_notifications_html(login_notifications, user_data, continue_url="/"):
    login_notification = None if len(login_notifications) == 0 else login_notifications[0]

    context = {"login_notification": login_notification, "continue": continue_url, "user_data":user_data}
    return shared_jinja.get().render_template("phantom_users/notifications.html", **context)

def badge_info(user_data):
    from .badges import badges, util_badges

    counts_dict = {}
    if user_data:
        counts_dict = util_badges.get_badge_counts(user_data)
    else:
        counts_dict = badges.BadgeCategory.empty_count_dict()

    sum_counts = 0
    for key in counts_dict:
        sum_counts += counts_dict[key]

    context = {
            "sum": sum_counts,
            "bronze": counts_dict[badges.BadgeCategory.BRONZE],
            "silver": counts_dict[badges.BadgeCategory.SILVER],
            "gold": counts_dict[badges.BadgeCategory.GOLD],
            "platinum": counts_dict[badges.BadgeCategory.PLATINUM],
            "diamond": counts_dict[badges.BadgeCategory.DIAMOND],
            "master": counts_dict[badges.BadgeCategory.MASTER],
    }
    return shared_jinja.get().render_template("phantom_users/badge_counts.html", **context)
    
def point_info(user_data):
    if user_data:
        points = user_data.points
    else:
        points = 0
    context = {"points": points}
    return shared_jinja.get().render_template("phantom_users/user_points.html", **context)

