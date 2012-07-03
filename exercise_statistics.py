import math
import functools
import logging

from mapreduce import control
from mapreduce import operation as op

import request_handler
import models
import consts

# /admin/startnewexercisestatisticsmapreduce is called periodically by a cron job
class StartNewExerciseStatisticsMapReduce(request_handler.RequestHandler):

    def get(self):

        # Admin-only restriction is handled by /admin/* URL pattern
        # so this can be called by a cron job.

        # Start a new Mapper task for calling statistics_update_map
        mapreduce_id = control.start_map(
                name = "UpdateExerciseStatistics",
                handler_spec = "exercise_statistics.statistics_update_map",
                reader_spec = "mapreduce.input_readers.DatastoreInputReader",
                reader_parameters = {"entity_kind": "models.Exercise"},
                queue_name = "exercise-statistics-mapreduce-queue",
                )

        self.response.out.write("OK: " + str(mapreduce_id))

# statistics_update_map is called by a background MapReduce task.
# Each call updates the statistics for a single exercise.
def statistics_update_map(exercise):
    
    # Get the last 5,000 correct problems for this exercise for analysis
    query = models.ProblemLog.all()
    query.filter('exercise =', exercise.name)
    query.filter('correct = ', True)
    query.order('-time_done')

    problem_logs = query.fetch(consts.LATEST_PROBLEMS_FOR_EXERCISE_STATISTICS)

    list_time_taken = []

    for problem_log in problem_logs:
        # Ignore outliers
        if problem_log.time_taken > 3.0 and problem_log.time_taken < consts.MAX_WORKING_ON_PROBLEM_SECONDS:
            list_time_taken.append(float(problem_log.time_taken))

    if len(list_time_taken) <= consts.REQUIRED_PROBLEMS_FOR_EXERCISE_STATISTICS:
        return

    list_time_taken = sorted(list_time_taken)

    # The smallest times are the fastest 25th percentile
    fastest_percentile = percentile(list_time_taken, consts.FASTEST_EXERCISE_PERCENTILE)
    fastest_percentile = min(consts.MAX_SECONDS_PER_FAST_PROBLEM, fastest_percentile)
    fastest_percentile = max(consts.MIN_SECONDS_PER_FAST_PROBLEM, fastest_percentile)

    exercise.seconds_per_fast_problem = fastest_percentile
    yield op.db.Put(exercise)

# See http://code.activestate.com/recipes/511478-finding-the-percentile-of-the-values/
def percentile(N, percent, key=lambda x:x):
    """
    Find the percentile of a list of values.

    @parameter N - is a list of values. Note N MUST BE already sorted.
    @parameter percent - a float value from 0.0 to 1.0.
    @parameter key - optional key function to compute value from each element of N.

    @return - the percentile of the values
    """
    if not N:
        return None
    k = (len(N)-1) * percent
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return key(N[int(k)])
    d0 = key(N[int(f)]) * (k-f)
    d1 = key(N[int(c)]) * (c-k)
    return d0+d1

