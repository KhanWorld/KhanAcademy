from google.appengine.ext import db
from time import mktime
import pickle
import datetime as dt

class ExerciseStatisticShard(db.Model):
    exid = db.StringProperty(required=True)
    start_dt = db.DateTimeProperty(required=True)
    end_dt = db.DateTimeProperty(required=True)
    cursor = db.StringProperty()
    blob_val = db.BlobProperty()

    @staticmethod
    def make_key(exid, start_dt, end_dt, cursor):
        unix_start = int(mktime(start_dt.timetuple()))
        unix_end = int(mktime(end_dt.timetuple()))
        key_name = "%s_%d_%d_%s" % (exid, unix_start, unix_end, cursor)
        return key_name

class ExerciseStatistic(db.Model):
    exid = db.StringProperty(required=True)
    start_dt = db.DateTimeProperty(required=True)
    end_dt = db.DateTimeProperty(required=True)
    blob_val = db.BlobProperty(required=True)
    log_count = db.IntegerProperty(required=True)
    time_logged = db.DateTimeProperty(auto_now_add=True)

    @staticmethod
    def make_key(exid, start_dt, end_dt):
        unix_start = int(mktime(start_dt.timetuple()))
        unix_end = int(mktime(end_dt.timetuple()))
        key_name = "%s_%d_%d" % (exid, unix_start, unix_end)
        return key_name

    @property
    def histogram(self):
        return pickle.loads(self.blob_val)

    @staticmethod
    def date_to_bounds(date):
        start_dt = dt.datetime.combine(date, dt.time())
        end_dt = start_dt + dt.timedelta(days=1)
        return (start_dt, end_dt)

    @staticmethod
    def get_by_date(exid, date):
        bounds = ExerciseStatistic.date_to_bounds(date)
        key_name = ExerciseStatistic.make_key(exid, bounds[0], bounds[1])
        return ExerciseStatistic.get_by_key_name(key_name)

    @staticmethod
    def get_by_dates_and_exids(exids, dates):
        # TODO: Optimizations: we could either parallelize the datastore calls or
        #     do a batch get of all the keys to reduce round trips
        ex_stats = []
        for exid in exids:
            ex_stats += [ ExerciseStatistic.get_by_date(exid, d) for d in dates ]

        return filter(lambda x: x != None, ex_stats)

    def num_proficient(self):
        return sum(self.histogram['proficiency_problem_number_frequencies'].values())

    def num_problems_done(self):
        return int(self.log_count)

    # This accessor takes a default because new_user_count is a new property
    # added and not all ExerciseStatistic objects have it
    def num_new_users(self, default=0):
        return self.histogram.get('new_user_count', default)
