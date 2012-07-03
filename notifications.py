import logging

from google.appengine.api import memcache

import util
import request_cache
import models

class UserNotifier:
    # Only show up to 2 badge notifications at a time, rest
    # will be visible from main badges page.
    NOTIFICATION_LIMIT = 2
    
    @staticmethod
    def key_for_user_data(user_data):
        return "notifications_dict_for_%s" % user_data.key_email

    @staticmethod
    def push_login_for_user_data(user_data, user_alert):
        if user_data is None or user_alert is None:
            return

        notifications = UserNotifier.get_or_create_notifications(user_data)
        notifications["login"] = [user_alert]

        memcache.set(UserNotifier.key_for_user_data(user_data), notifications)
    
    @staticmethod
    def push_badge_for_user_data(user_data, user_badge):
        if user_data is None or user_badge is None:
            return

        notifications = UserNotifier.get_or_create_notifications(user_data)
        
        if notifications["badges"] is None:
            notifications["badges"] = []

        if len(notifications["badges"]) < UserNotifier.NOTIFICATION_LIMIT:
            notifications["badges"].append(user_badge)
            memcache.set(UserNotifier.key_for_user_data(user_data), notifications)
    
    @staticmethod
    @request_cache.cache()
    def pop_for_current_user_data():
        return UserNotifier.pop_for_user_data(models.UserData.current())

    @staticmethod
    def pop_for_user_data(user_data):
        if not user_data:
            return UserNotifier.empty_notifications()

        notifications = UserNotifier.get_or_create_notifications(user_data)

        user_badges = notifications["badges"] or []
        if len(user_badges) > 0:
            notifications["badges"] = []
            memcache.set(UserNotifier.key_for_user_data(user_data), notifications)
            notifications["badges"] = user_badges

        return notifications

    @staticmethod
    def empty_notifications():
        return { "badges": [], "login": [] }
        
    @staticmethod
    def clear_login():
        notifications = UserNotifier.empty_notifications()
        notifications["badges"] = UserNotifier.pop_for_current_user_data()["badges"]
        memcache.set(UserNotifier.key_for_user_data(models.UserData.current()), notifications)
    
    @staticmethod
    def clear_all(user_data):
        memcache.set(UserNotifier.key_for_user_data(user_data), UserNotifier.empty_notifications())
    
    @staticmethod
    def get_or_create_notifications(user_data):
        return memcache.get(UserNotifier.key_for_user_data(user_data)) or UserNotifier.empty_notifications()
