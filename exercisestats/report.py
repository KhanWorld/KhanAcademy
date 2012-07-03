from __future__ import absolute_import

import request_handler
import user_util

from itertools import groupby
from models import ProblemLog
from .models import ExerciseStatistic

import datetime as dt

class Test(request_handler.RequestHandler):
    @user_util.developer_only
    def get(self):
        return self.from_exercise_stats()

    def from_exercise_stats(self):
        hist = self.request_string('hist', 'time_taken_frequencies')
        exid = self.request_string('exid', 'addition_1')
        date = self.request_string('date')

        yesterday = dt.date.today() - dt.timedelta(days=1)
        yesterday_dt = dt.datetime.combine(yesterday, dt.time())
        date = self.request_date('date', "%Y/%m/%d", yesterday_dt)

        bounds = ExerciseStatistic.date_to_bounds(date)
        key_name = ExerciseStatistic.make_key(exid, bounds[0], bounds[1])
        ex = ExerciseStatistic.get_by_key_name(key_name)
        if not ex:
            raise Exception("No ExerciseStatistic found with key_name %s", key_name)

        return self.render_hist(ex.histogram[hist])

    # only used for testing
    def from_problem_logs(self):
        problem_log_query = ProblemLog.all()
        problem_logs = problem_log_query.fetch(1000)

        problem_logs.sort(key=lambda log: log.time_taken)
        grouped = dict((k, sum(1 for i in v)) for (k, v) in groupby(problem_logs, key=lambda log: log.time_taken))
        return self.render_hist(grouped)

    def render_hist(self, data):
        max_t = min(180, max(data.keys()))
        hist = []
        total = sum(data[k] for k in data)
        cumulative = 0
        for time in range(max_t+2):
            count = data.get(time, 0)
            cumulative += count
            hist.append({
                'time': time,
                'count': count,
                'cumulative': cumulative,
                'percent': 100.0 * count / total,
                'percent_cumulative': 100.0 * cumulative / total,
                'percent_cumulative_tenth': 10.0 * cumulative / total,
            })

        context = { 'selected_nav_link': 'practice', 'hist': hist, 'total': total }

        self.render_jinja2_template('exercisestats/test.html', context)
