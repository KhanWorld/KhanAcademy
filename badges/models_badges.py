#!/usr/bin/python
# -*- coding: utf-8 -*-

import datetime
import models

from google.appengine.ext import db

class BadgeStat(db.Model):
    badge_name = db.StringProperty()
    count_awarded = db.IntegerProperty(default = 0)
    dt_last_calculated = db.DateTimeProperty()

    @staticmethod
    def get_or_insert_for(badge_name):
        if not badge_name:
            return None

        return BadgeStat.get_or_insert(
                key_name = "badgestat_%s" % badge_name,
                badge_name = badge_name,
                count_awarded = 0
                )

    @staticmethod
    def count_by_badge_name(badge_name):
        badge = BadgeStat.get_or_insert_for(badge_name)
        return badge.count_awarded

    @property
    def time_since_calculation(self):
        if not self.dt_last_calculated:
            return datetime.timedelta.max

        return datetime.datetime.now() - self.dt_last_calculated

    def needs_update(self):
        """ Update this badge's stats if it's been at least 6 hours since last calculation.

        This code runs in a task queue, so if the task fails and requeues itself
        this protects us from multiple updates per badge in a short time frame.
        """
        return self.time_since_calculation.seconds > (60 * 60 * 6)

    def update(self):
        dt_last_calculated_next = datetime.datetime.now()

        if self.dt_last_calculated:
            # Only calculate 10 days at a time in case we've fallen into a hole
            # and need to dig ourselves out.
            dt_last_calculated_next = min(dt_last_calculated_next, self.dt_last_calculated + datetime.timedelta(days=10))

        self.count_awarded += UserBadge.count_by_badge_name_between_dts(
                self.badge_name, 
                self.dt_last_calculated, 
                dt_last_calculated_next)

        self.dt_last_calculated = dt_last_calculated_next

class CustomBadgeType(db.Model):
    description = db.StringProperty()
    full_description = db.TextProperty()
    points = db.IntegerProperty(default = 0)
    category = db.IntegerProperty(default = 0)
    icon_src = db.StringProperty(default = "")

    @staticmethod
    def insert(name, description, full_description, points, badge_category, icon_src = ""):

        if not name or not description or not full_description or points < 0 or badge_category < 0:
            return None

        if icon_src and not icon_src.startswith("/"):
            return None

        custom_badge_type = CustomBadgeType.get_by_key_name(key_names = name)
        if not custom_badge_type:
            return CustomBadgeType.get_or_insert(
                    key_name = name,
                    description = description,
                    full_description = full_description,
                    points = points,
                    category = badge_category,
                    icon_src = icon_src
                    )

        return None

class UserBadge(db.Model):
    user = db.UserProperty()
    date = db.DateTimeProperty(auto_now_add=True)
    badge_name = db.StringProperty()
    target_context = db.ReferenceProperty()
    target_context_name = db.StringProperty()
    points_earned = db.IntegerProperty(default = 0)

    _serialize_blacklist = ["badge"]

    @staticmethod
    def get_for(user_data):
        query = UserBadge.all()
        query.filter('user =', user_data.user)
        query.order('badge_name')
        query.order('-date')
        return query.fetch(2500)

    @staticmethod
    def get_for_user_data_between_dts(user_data, dt_a, dt_b):
        query = UserBadge.all()
        query.filter('user =', user_data.user)
        query.filter('date >=', dt_a)
        query.filter('date <=', dt_b)
        query.order('date')
        return query

    @staticmethod
    def count_by_badge_name_between_dts(name, dt_a, dt_b):
        query = UserBadge.all(keys_only=True)

        if dt_a:
            query.filter('date >=', dt_a)

        if dt_b:
            query.filter('date <', dt_b)

        query.filter('badge_name = ', name)

        count = 0
        while count % 1000 == 0:

            current_count = len(query.fetch(1000))
            if current_count == 0:
                break

            count += current_count

            if current_count == 1000:
                cursor = query.cursor()
                query.with_cursor(cursor)

        return count

