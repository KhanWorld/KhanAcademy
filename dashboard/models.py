import datetime

from google.appengine.ext import db
from google.appengine.ext.db import stats

from itertools import groupby

class DailyStatisticLog(db.Model):
    val = db.IntegerProperty(required=True, default=0)
    dt = db.DateTimeProperty(auto_now_add=True)
    stat_name = db.StringProperty(required=True)

    @staticmethod
    def make_key(stat_name, dt):
        # Use stat name and date (w/ hours/secs/mins stripped) as keyname so we
        # don't record duplicate stats
        return "%s:%s" % (stat_name, dt.date().isoformat())

class DailyStatistic(object):
    """ Abstract base type for some kind of statistic that can be tracked.
    
    Subclasses should implement the calc method to implement collection of
    the statistic.
    
    This data is typically used for diagnostic or analytics purposes
    for development. The data is not intended for end-user consumption.
    
    """

    @classmethod
    def all(cls): #@ReservedAssignment
        return DailyStatisticLog.all().filter("stat_name =", cls.__name__)

    def calc(self):
        raise Exception("Not implemented")

    def name(self):
        # Use subclass name as stat identifier
        stat_name = self.__class__.__name__

        if stat_name == DailyStatistic.__name__:
            raise Exception("DailyStatistic cannot be used directly. " +
                            "Must use an implementing subclass.")

        return stat_name

    def record(self, val = None, dt = None):
        """ Computes the internal value (if needed) and writes to the db. """

        if val is None:
            # Grab actual stat value, implemented by subclass
            val = self.calc()

        if dt is None:
            dt = datetime.datetime.now()

        if val is not None:
            stat_name = self.name()

            return DailyStatisticLog.get_or_insert(
                    key_name = DailyStatisticLog.make_key(stat_name, dt),
                    stat_name = stat_name,
                    val = val,
                    dt = dt,
                    )

        return None

    @staticmethod
    def record_all():
        dt = datetime.datetime.now()

        # Record stats for all implementing subclasses
        for subclass in DailyStatistic.__subclasses__():
            instance = subclass()
            instance.record(dt = dt)

class EntityStatistic(DailyStatistic):
    """ A generic statistic about a particular Entity count in the database """

    def __init__(self, kind_name=None):
        self.kind_name = kind_name

    def all(self): #@ReservedAssignment
        return DailyStatisticLog.all().filter("stat_name =", self.kind_name+'Count')

    # actually updates for all entity kinds
    def record(self, val = None, dt = None):
        kind_stats = [s for s in stats.KindStat.all()]

        logs = []
        kind_stats.sort(key=lambda s: s.kind_name)
        for key, kinds in groupby(kind_stats, lambda s: s.kind_name):
            stat = kinds.next()
            logs.append(DailyStatisticLog(
                key_name=DailyStatisticLog.make_key(stat.kind_name, dt),
                stat_name=stat.kind_name+'Count',
                val=stat.count,
                dt=dt
            ))
        db.put(logs)