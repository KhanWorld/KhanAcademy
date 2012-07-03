import datetime
import logging

from mapreduce import control
from google.appengine.ext import db

import util
import request_handler
import models
import consts
import points
import fast_slow_queue

class ActivitySummaryExerciseItem:
    def __init__(self):
        self.c_problems = 0
        self.c_correct = 0
        self.time_taken = 0
        self.points_earned = 0
        self.exercise = None

class ActivitySummaryVideoItem:
    def __init__(self):
        self.seconds_watched = 0
        self.points_earned = 0
        self.playlist_titles = None
        self.video_title = None

class DailyActivitySummary:

    def __init__(self):
        self.user_data = None
        self.date = None
        self.hourly_summaries = {}

    def has_activity(self):
        return len(self.hourly_summaries) > 0

    @staticmethod
    def build(user_data, date, problem_logs, video_logs):
        summary = DailyActivitySummary()
        summary.user_data = user_data

        # Chop off hours, minutes, and seconds
        summary.date = datetime.datetime(date.year, date.month, date.day)

        date_next = date + datetime.timedelta(days=1)
        problem_logs_filtered = filter(lambda problem_log: date <= problem_log.time_done < date_next, problem_logs)
        video_logs_filtered = filter(lambda video_log: date <= video_log.time_watched < date_next, video_logs)

        for problem_log in problem_logs_filtered:
            hour = problem_log.time_done.hour
            if not summary.hourly_summaries.has_key(hour):
                summary.hourly_summaries[hour] = HourlyActivitySummary(summary.date, hour)
            summary.hourly_summaries[hour].add_problem_log(problem_log)

        for video_log in video_logs_filtered:
            hour = video_log.time_watched.hour
            if not summary.hourly_summaries.has_key(hour):
                summary.hourly_summaries[hour] = HourlyActivitySummary(summary.date, hour)
            summary.hourly_summaries[hour].add_video_log(video_log)

        return summary

class HourlyActivitySummary:

    def __init__(self, date, hour):
        self.date = datetime.datetime(date.year, date.month, date.day, hour)
        self.dict_exercises = {}
        self.dict_videos = {}

    def has_video_activity(self):
        return len(self.dict_videos) > 0

    def has_exercise_activity(self):
        return len(self.dict_exercises) > 0

    def add_problem_log(self, problem_log):
        if not self.dict_exercises.has_key(problem_log.exercise):
            self.dict_exercises[problem_log.exercise] = ActivitySummaryExerciseItem()

        summary_item = self.dict_exercises[problem_log.exercise]
        summary_item.time_taken += problem_log.time_taken_capped_for_reporting()
        summary_item.points_earned += problem_log.points_earned
        summary_item.c_problems += 1
        summary_item.exercise = problem_log.exercise
        if problem_log.correct:
            summary_item.c_correct += 1

    def add_video_log(self, video_log):
        video_key = video_log.key_for_video()
        if not self.dict_videos.has_key(video_key):
            self.dict_videos[video_key] = ActivitySummaryVideoItem()

        summary_item = self.dict_videos[video_key]
        summary_item.seconds_watched += video_log.seconds_watched
        summary_item.points_earned += video_log.points_earned
        summary_item.playlist_titles = video_log.playlist_titles
        summary_item.video_title = video_log.video_title

def fill_realtime_recent_daily_activity_summaries(daily_activity_logs, user_data, dt_end):

    if user_data.last_daily_summary and dt_end <= user_data.last_daily_summary:
        return daily_activity_logs

    # We're willing to fill the last 2 days with realtime data if summary logs haven't
    # been compiled for some reason.
    dt_end = min(dt_end, datetime.datetime.now())
    dt_start = dt_end - datetime.timedelta(days=2)

    if user_data.last_daily_summary:
        dt_start = max(dt_end - datetime.timedelta(days=2), user_data.last_daily_summary)

    query_problem_logs = models.ProblemLog.get_for_user_data_between_dts(user_data, dt_start, dt_end)
    query_video_logs = models.VideoLog.get_for_user_data_between_dts(user_data, dt_start, dt_end)

    results = util.async_queries([query_problem_logs, query_video_logs])

    problem_logs = results[0].get_result()
    video_logs = results[1].get_result()

    # Chop off hours, minutes, and seconds
    dt_start = datetime.datetime(dt_start.year, dt_start.month, dt_start.day)
    dt_end = datetime.datetime(dt_end.year, dt_end.month, dt_end.day)

    dt = dt_start

    while dt <= dt_end:
        summary = DailyActivitySummary.build(user_data, dt, problem_logs, video_logs)
        if summary.has_activity():
            log = models.DailyActivityLog.build(user_data, dt, summary)
            daily_activity_logs.append(log)
        dt += datetime.timedelta(days=1)

    return daily_activity_logs

def next_daily_activity_dates(user_data):

    if not user_data or not user_data.points:
        return (None, None)

    # Start summarizing after the last summary
    dt_start = user_data.last_daily_summary or datetime.datetime.min

    # Stop summarizing at the last sign of activity
    dt_end = datetime.datetime.now()
    if user_data.last_activity:
        # Make sure we always include the full day that contained the user's last activity
        dt_end = user_data.last_activity + datetime.timedelta(days=1)

    # Never summarize the most recent day
    # (it'll be summarized later, and we'll use the more detailed logs for this data)
    dt_end = min(dt_end, datetime.datetime.now() - datetime.timedelta(days=1))

    # Never summarize more than 30 days into the past
    dt_start = max(dt_start, dt_end - datetime.timedelta(days=30))

    # Chop off hours, minutes, and seconds
    dt_start = datetime.datetime(dt_start.year, dt_start.month, dt_start.day)
    dt_end = datetime.datetime(dt_end.year, dt_end.month, dt_end.day)

    # If at least one day has passed b/w last summary and latest activity
    if (dt_end - dt_start) >= datetime.timedelta(days=1):

        # Only iterate over 10 days per mapreduce
        dt_end = min(dt_end, dt_start + datetime.timedelta(days=10))

        return (dt_start, dt_end)

    return (None, None)

def is_daily_activity_waiting(user_data):
    dt_start, dt_end = next_daily_activity_dates(user_data)
    return dt_start and dt_end

@fast_slow_queue.handler(is_daily_activity_waiting)
def daily_activity_summary_map(user_data):

    dt_start, dt_end = next_daily_activity_dates(user_data)

    if not dt_start or not dt_end:
        return

    dt = dt_start
    list_entities_to_put = []

    problem_logs = models.ProblemLog.get_for_user_data_between_dts(user_data, dt_start, dt_end).fetch(100000)
    video_logs = models.VideoLog.get_for_user_data_between_dts(user_data, dt_start, dt_end).fetch(100000)

    while dt <= dt_end:
        summary = DailyActivitySummary.build(user_data, dt, problem_logs, video_logs)
        if summary.has_activity():
            log = models.DailyActivityLog.build(user_data, dt, summary)
            list_entities_to_put.append(log)

        dt += datetime.timedelta(days=1)

    user_data.last_daily_summary = dt_end

    list_entities_to_put.append(user_data)

    db.put(list_entities_to_put)

class StartNewDailyActivityLogMapReduce(request_handler.RequestHandler):
    def get(self):
        # Admin-only restriction is handled by /admin/* URL pattern
        # so this can be called by a cron job.
        # Start a new Mapper task for calling statistics_update_map
        mapreduce_id = control.start_map(
                name = "DailyActivityLog",
                handler_spec = "activity_summary.daily_activity_summary_map",
                reader_spec = "mapreduce.input_readers.DatastoreInputReader",
                reader_parameters = {"entity_kind": "models.UserData", "processing_rate": 250},
                mapreduce_parameters = {},
                shard_count = 64,
                queue_name = fast_slow_queue.QUEUE_NAME,)
        self.response.out.write("OK: " + str(mapreduce_id))


