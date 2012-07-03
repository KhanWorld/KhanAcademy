from google.appengine.api import users

import datetime
import logging
import user_util

from google.appengine.api import memcache

class RateLimiter:
    
    def __init__(self, user_data, hourly_limit, desc):
        self.hourly_limit = hourly_limit
        self.desc = desc
        self.user_data = user_data

    def is_allowed(self):
        return len(self.purge()) < self.hourly_limit or \
                user_util.is_current_user_developer() or \
                self.user_data.moderator

    def increment(self):
        if not self.is_allowed():
            return False

        self.add_new()
        return True

    def get_key(self):
        return "rate_limiter_%s_%s" % (self.__class__.__name__, self.user_data.key_email) 

    def add_new(self):
        key = self.get_key()

        dates = memcache.get(key)
        if not dates:
            dates = []
        dates.append(datetime.datetime.now())

        memcache.set(key, dates)

    def purge(self):
        key = self.get_key()

        dates = memcache.get(key)
        if not dates:
            return []

        date_now = datetime.datetime.now()
        modified = False

        for date in dates:
            if (date_now - date) > datetime.timedelta(seconds=3600):
                modified = True
                dates.remove(date)

        if modified:
            memcache.set(key, dates)

        return dates

    def denied_desc(self):
        return self.desc % self.hourly_limit

class VoteRateLimiter(RateLimiter):
    def __init__(self, user_data):
        RateLimiter.__init__(self, user_data, 10, "You can only vote %s times every hour.")

class FlagRateLimiter(RateLimiter):
    def __init__(self, user_data):
        RateLimiter.__init__(self, user_data, 10, "You can only flag %s times every hour.")
