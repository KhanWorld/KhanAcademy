from __future__ import absolute_import

import layer_cache
import request_handler
import user_util

from models import ProblemLog, Exercise, Setting
from .models import ExerciseStatistic

import bisect
import cgi
import datetime as dt
import math
import random
import time
import simplejson as json
from google.appengine.ext import db

import logging

# Constants for Geckoboard display.
NUM_BUCKETS = 19
PAST_DAYS_TO_SHOW = 7
REFRESH_SECS = 30

CACHE_EXPIRATION_SECS = 60 * 60

# For a point on the exercise map
MAX_POINT_RADIUS = 15

################################################################################

# Create a new list of KVPs with the values of all KVPs with identical keys summed
def sum_keys(key_value_pairs):
    histogram = {}
    for k, v in key_value_pairs:
        histogram[k] = histogram.get(k, 0) + v

    return list(histogram.items())

def to_unix_secs(date_and_time):
    return int(time.mktime(date_and_time.timetuple()))

def exercises_in_bucket(num_buckets, bucket_index):
    exercise_names = [ex.name for ex in Exercise.get_all_use_cache()]
    exercise_names.sort()

    # These calculations evenly distribute exercises among buckets, with excess
    # going to the first few buckets.
    # In particular, max_capacity(buckets) - min_capacity(buckets) <= 1.
    num_exercises = len(exercise_names)
    min_bucket_size = num_exercises / num_buckets
    bucket_rem = num_exercises % num_buckets

    first = bucket_index * min_bucket_size + min(bucket_rem, bucket_index)
    return exercise_names[ first : first + get_bucket_size(num_buckets, bucket_index) ]

def get_bucket_size(num_buckets, bucket_index):
    num_exercises = len(Exercise.get_all_use_cache())
    bucket_rem = num_exercises % num_buckets
    return (num_exercises / num_buckets) + (1 if bucket_index < bucket_rem else 0)

# Choose the exercise based on the time, so we can cycle predictably and also
# use the cache
def get_bucket_cursor(refresh_secs, bucket_size):
    unix_secs = to_unix_secs(dt.datetime.now())
    ret = (unix_secs / refresh_secs) % bucket_size
    return ret

################################################################################

class ExerciseOverTimeGraph(request_handler.RequestHandler):
    def get(self):
        self.render_jsonp(self.get_json_response())

    def get_json_response(self):
        # Currently accepts: { "buckets", "all", "newest" }
        to_show = self.request_string('show', 'buckets')
        past_days = self.request_int('past_days', 7)
        refresh_secs = self.request_int('rsecs', 30)

        today = dt.date.today()
        # We don't use App Engine Query filters so as to avoid adding entries to index.yaml
        days = [ today - dt.timedelta(days=i) for i in range(0, past_days) ]

        if to_show == 'all':
            exercise_names = [ex.name for ex in Exercise.get_all_use_cache()]
            return self.exercise_over_time_for_highcharts(exercise_names, days, 'All Exercises', showLegend=True)

        if to_show == 'newest':
            exercises = Exercise.get_all_use_cache()
            exercises.sort(key=lambda ex: ex.creation_date, reverse=True)
            exercise_names = [ex.name for ex in exercises]

            num_newest = self.request_int('newest', 5)
            exid = exercise_names[get_bucket_cursor(refresh_secs, num_newest)]

            title = 'Newest Exercises - %s' % Exercise.to_display_name(exid)

            return self.exercise_over_time_for_highcharts([exid], days, title, showLegend=True)

        num_buckets = self.request_int('buckets', NUM_BUCKETS)
        bucket_index = self.request_int('ix', 0)
        bucket_size = get_bucket_size(num_buckets, bucket_index)
        bucket_cursor = get_bucket_cursor(refresh_secs, bucket_size)

        exercise_names = exercises_in_bucket(num_buckets, bucket_index)
        exid = exercise_names[bucket_cursor]

        return self.exercise_over_time_for_highcharts([exid], days, Exercise.to_display_name(exid))

    # TODO: What's the best way to deal with the wrapped function having default values?
    def get_cache_key(self, exids, dates, title='', showLegend=False):
        return "%s|%s|%s|%s|%s" % (Setting.cached_exercises_date(),
            sorted(exids), sorted(dates), title, showLegend)

    @layer_cache.cache_with_key_fxn(get_cache_key,
        expiration=CACHE_EXPIRATION_SECS, layer=layer_cache.Layers.Memcache)
    def exercise_over_time_for_highcharts(self, exids, dates, title='', showLegend=False):
        exercise_stats = ExerciseStatistic.get_by_dates_and_exids(exids, dates)

        prof_list, done_list, new_users_list = [], [], []
        for ex in exercise_stats:
            start_unix = to_unix_secs(ex.start_dt) * 1000
            prof_list.append([start_unix, ex.num_proficient()])
            done_list.append([start_unix, ex.num_problems_done()])
            new_users_list.append([start_unix, ex.num_new_users()])

        # It's possible that the ExerciseStats that we go through has multiple
        # entries for a particular day (eg. if we were aggregating more than
        # one exercise). Sum them.
        done_list = sum_keys(done_list)
        prof_list = sum_keys(prof_list)
        new_users_list = sum_keys(new_users_list)

        # Make the peak of the new users and proficiency series about half as
        # high as the peak of the # problems line
        left_axis_max = max([x[1] for x in done_list]) if done_list else 1
        right_axis_max = max([x[1] for x in new_users_list + prof_list]) * 2 if new_users_list else 1

        dates_to_display_unix = [x[0] for x in done_list] if done_list else [0]

        # TODO: Call a function to render all values in this dict as JSON
        #     string before giving it to the template, so we don't need to call
        #     json.dumps on all the values.
        context = {
            'title': title,
            'series': [
                {
                    'name': 'Problems done',
                    'type': 'areaspline',
                    'data_values': json.dumps(done_list),
                    'axis': 0,
                },
                {
                    'name': 'Proficient',
                    'type': 'column',
                    'data_values': json.dumps(prof_list),
                    'axis': 1,
                },
                {
                    'name': 'First attempts',
                    'type': 'spline',
                    'data_values': json.dumps(new_users_list),
                    'axis': 1,
                },
            ],
            'axes': [
                { 'max': left_axis_max },
                { 'max': right_axis_max },
            ],
            'minXValue': min(dates_to_display_unix),
            'maxXValue': max(dates_to_display_unix),
            'showLegend': json.dumps(showLegend),
        }

        return self.render_jinja2_template_to_string(
            'exercisestats/highcharts_area_spline.json', context)

# This redirect is to eliminate duplicate code so we don't have to change every
# Geckoboard widgets' URL for a general change
class GeckoboardExerciseRedirect(request_handler.RequestHandler):
    def get(self):
        bucket_index = self.request_int('ix', 0)
        return self.redirect('/exercisestats/exerciseovertime?chart=area_spline&past_days=%d&rsecs=%d&buckets=%d&ix=%d'
            % (PAST_DAYS_TO_SHOW, REFRESH_SECS, NUM_BUCKETS, bucket_index))

# TODO: Either allow returning graphs for other statistics, such as #
#     proficient, or somehow display more statistics on the same graph nicely
class ExerciseStatsMapGraph(request_handler.RequestHandler):
    # TODO: Just move this logic into get and make get_use_cache take a day parameter.
    def get_request_params(self):
        default_day = dt.date.today() - dt.timedelta(days=2)
        interested_day = self.request_date('date', "%Y/%m/%d", default_day)

        return {
            'interested_day': interested_day
        }

    def get(self):
        self.response.out.write(self.get_use_cache())

    @layer_cache.cache_with_key_fxn(lambda self: "%s|%s" % (Setting.cached_exercises_date(), self.get_request_params()),
        expiration=CACHE_EXPIRATION_SECS, layer=layer_cache.Layers.Memcache)
    def get_use_cache(self):
        params = self.get_request_params()

        # Get the maximum so we know how the data label circles should be scaled
        most_new_users = 1
        ex_stat_dict = {}
        for ex in Exercise.get_all_use_cache():
            stat = ExerciseStatistic.get_by_date(ex.name, params['interested_day'])
            ex_stat_dict[ex.name] = stat
            if stat:
                most_new_users = max(most_new_users, stat.num_new_users())

        data_points = []
        min_y, max_y = -1, 1
        for ex in Exercise.get_all_use_cache():
            stat = ex_stat_dict[ex.name]

            y, x = -int(ex.h_position), int(ex.v_position)

            min_y, max_y = min(y, min_y), max(y, max_y)

            # Set the area of the circle proportional to the data value
            radius = 1
            if stat:
                radius = math.sqrt(float(stat.num_new_users()) / most_new_users) * MAX_POINT_RADIUS

            point = {
                'x': x,
                'y': y,
                'name': ex.display_name,
                'marker': {
                    'radius': max(radius, 1)
                },
            }
            data_points.append(point)

        context = {
            'title': 'Exercises map - First attempts',
            'series': {
                'name': 'First attempts',
                'data_values': json.dumps(data_points),
            },
            'minYValue': min_y - 1,
            'maxYValue': max_y + 1,
        }

        return self.render_jinja2_template_to_string(
            'exercisestats/highcharts_scatter_map.json', context)

class ExercisesLastAuthorCounter(request_handler.RequestHandler):
    def get(self):
        self.render_json(self.exercise_counter_for_geckoboard_rag())

    @staticmethod
    @layer_cache.cache_with_key_fxn(lambda: "last_author_%s" % Setting.cached_exercises_date(),
        expiration=CACHE_EXPIRATION_SECS, layer=layer_cache.Layers.Memcache)
    def exercise_counter_for_geckoboard_rag():
        exercises = Exercise.get_all_use_cache()
        exercises.sort(key=lambda ex: ex.creation_date, reverse=True)

        last_exercise = exercises[0]
        num_exercises = len(exercises)
        last_exercise_author = last_exercise.author.nickname() if last_exercise.author else 'random person'

        text = "Thanks %s for %s!" % (last_exercise_author, last_exercise.display_name)

        return {
            'item': [
                {
                    'value': None,
                    'text': '',
                },
                {
                    'value': None,
                    'text': '',
                },
                {
                    'value': num_exercises,
                    'text': text,
                },
            ]
        }

class ExerciseNumberTrivia(request_handler.RequestHandler):
    def get(self):
        number = self.request_int('num', len(Exercise.get_all_use_cache()))
        self.render_json(self.number_facts_for_geckboard_text(number))

    @staticmethod
    @layer_cache.cache_with_key_fxn(lambda number: "%s|%s" % (Setting.cached_exercises_date(), number),
        expiration=CACHE_EXPIRATION_SECS, layer=layer_cache.Layers.Memcache)
    def number_facts_for_geckboard_text(number):
        import exercisestats.number_trivia as number_trivia

        math_fact = number_trivia.math_facts.get(number,
            'This number is interesting. Why? Suppose there exists uninteresting '
            'natural numbers. Then the smallest in that set would be '
            'interesting by virtue of being the first: a contradiction. '
            'Thus all natural numbers are interesting.')
        year_fact = number_trivia.year_facts.get(number, 'nothing interesting happened')

        misc_fact_keys = sorted(number_trivia.misc_facts.keys())
        first_available_num = misc_fact_keys[bisect.bisect_left(misc_fact_keys, number) - 1]
        greater_than_fact = number_trivia.misc_facts[first_available_num]

        text1 = 'We now have more exercises than %s (%s)!' % (
            cgi.escape(greater_than_fact), str(first_available_num))
        text2 = math_fact
        text3 = "In year %d, %s" % (number, cgi.escape(year_fact))

        return {
            'item': [
                { 'text': text1 },
                { 'text': text2 },
                { 'text': text3 },
            ]
        }

class UserLocationsMap(request_handler.RequestHandler):
    def get(self):
        default_day = dt.date.today() - dt.timedelta(days=2)
        date = self.request_date('date', "%Y/%m/%d", default_day)

        self.render_json(self.get_ip_addresses_for_geckoboard_map(date))

    @staticmethod
    @layer_cache.cache_with_key_fxn(lambda date: str(date),
        expiration=CACHE_EXPIRATION_SECS, layer=layer_cache.Layers.Memcache)
    def get_ip_addresses_for_geckoboard_map(date):
        ip_addresses = []

        for ex in Exercise.get_all_use_cache():
            stat = ExerciseStatistic.get_by_date(ex.name, date)

            if stat:
                ip_addresses += stat.histogram.get('ip_addresses', [])

        return {
            'points': {
                'point': [{'ip': addr} for addr in ip_addresses]
            }
        }

class ExercisesCreatedHistogram(request_handler.RequestHandler):
    def get(self):
        past_days = self.request_int('past_days', 7)
        today_dt = dt.datetime.combine(dt.date.today(), dt.time())
        earliest_dt = today_dt- dt.timedelta(days=past_days)

        self.response.out.write(self.get_histogram_spline_for_highcharts(earliest_dt))

    @layer_cache.cache_with_key_fxn(lambda self, date: "%s|%s" % (Setting.cached_exercises_date(), date),
        expiration=CACHE_EXPIRATION_SECS, layer=layer_cache.Layers.Memcache)
    def get_histogram_spline_for_highcharts(self, earliest_dt=dt.datetime.min):
        histogram = {}
        for ex in Exercise.get_all_use_cache():
            if ex.creation_date:
                creation_day = dt.datetime.combine(ex.creation_date, dt.time())
                timestamp = to_unix_secs(creation_day) * 1000
                histogram[timestamp] = histogram.get(timestamp, 0) + 1

        total_exercises = {}
        prev_value = 0
        for day, value in sorted(histogram.items()):
            prev_value = total_exercises[day] = prev_value + value

        # Only retain recent dates
        earliest_unix = to_unix_secs(earliest_dt) * 1000
        histogram = [[k,v] for k,v in histogram.items() if k >= earliest_unix]
        total_exercises = [[k,v] for k,v in total_exercises.items() if k >= earliest_unix]

        context = {
            'series': [
                {
                    'name': 'Histogram (created per day)',
                    'type': 'column',
                    'data_values': json.dumps(histogram),
                    'axis': 0,
                },
                {
                    'name': 'Total exercises',
                    'type': 'spline',
                    'data_values': json.dumps(total_exercises),
                    'axis': 1,
                }
            ],
            # Let highcharts determine the scales for now.
            'axes': [
                { 'max': 'null' },
                { 'max': 'null' },
            ],
        }

        return self.render_jinja2_template_to_string(
            'exercisestats/highcharts_exercises_created_histogram.json', context)

class SetAllExerciseCreationDates(request_handler.RequestHandler):
    def get(self):
        date_to_set = self.request_date('date', "%Y/%m/%d")

        exercises = Exercise.get_all_use_cache()
        updated = []
        for ex in exercises:
            ex.creation_date = date_to_set
            updated.append(ex)

        db.put(updated)
