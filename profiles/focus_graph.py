import datetime
import time
import logging

from templatefilters import seconds_to_time_string, pluralize

import models
import util
import activity_summary

def get_playlist_focus_data(daily_activity_logs, dt_start_utc, dt_end_utc):
    total_seconds = 0
    dict_playlist_seconds = {}

    for daily_activity_log in daily_activity_logs:
        activity_summary = daily_activity_log.activity_summary
        for hour in activity_summary.hourly_summaries:

            hourly_activity_summary = activity_summary.hourly_summaries[hour]

            # We need to filter for dates outside of our range here because we expanded our DB query
            # to make sure we got the entire client time zone date range
            if hourly_activity_summary.date < dt_start_utc or hourly_activity_summary.date > dt_end_utc:
                continue

            for video_key in hourly_activity_summary.dict_videos.keys():
                hourly_activity_summary_video_item = hourly_activity_summary.dict_videos[video_key]

                playlist_title = "Other"
                if hourly_activity_summary_video_item.playlist_titles:
                    playlist_title = hourly_activity_summary_video_item.playlist_titles[0] # Only count against the first playlist for now

                key_playlist = playlist_title.lower()
                if dict_playlist_seconds.has_key(key_playlist):
                    dict_playlist_seconds[key_playlist]["seconds"] += hourly_activity_summary_video_item.seconds_watched
                else:
                    dict_playlist_seconds[key_playlist] = {"playlist_title": playlist_title, "seconds": hourly_activity_summary_video_item.seconds_watched, "videos": {}}

                key_video = hourly_activity_summary_video_item.video_title.lower()
                if dict_playlist_seconds[key_playlist]["videos"].has_key(key_video):
                    dict_playlist_seconds[key_playlist]["videos"][key_video]["seconds"] += hourly_activity_summary_video_item.seconds_watched
                else:
                    dict_playlist_seconds[key_playlist]["videos"][key_video] = {"video_title": hourly_activity_summary_video_item.video_title, "seconds": hourly_activity_summary_video_item.seconds_watched}

                total_seconds += hourly_activity_summary_video_item.seconds_watched

    for key_playlist in dict_playlist_seconds:
        dict_playlist_seconds[key_playlist]["percentage"] = 0
        if total_seconds > 0:
            dict_playlist_seconds[key_playlist]["percentage"] = int(float(dict_playlist_seconds[key_playlist]["seconds"]) / float(total_seconds) * 100.0)

        dict_playlist_seconds[key_playlist]["time_spent"] = seconds_to_time_string(dict_playlist_seconds[key_playlist]["seconds"], False)

        tooltip_more = ""
        c_videos_tooltip = 0
        c_videos_tooltip_max = 8
        for key_video in dict_playlist_seconds[key_playlist]["videos"]:
            if c_videos_tooltip < c_videos_tooltip_max:
                video_title = dict_playlist_seconds[key_playlist]["videos"][key_video]["video_title"]
                time_spent = seconds_to_time_string(dict_playlist_seconds[key_playlist]["videos"][key_video]["seconds"], False)
                tooltip_more += "<em>%s</em><br> - %s" % (video_title, time_spent) + "<br/>"
            elif c_videos_tooltip == c_videos_tooltip_max:
                tooltip_more += "<em>...and %d more</em>" % (len(dict_playlist_seconds[key_playlist]["videos"]) - c_videos_tooltip_max)
            c_videos_tooltip += 1
        dict_playlist_seconds[key_playlist]["tooltip_more"] = tooltip_more

    return (total_seconds, dict_playlist_seconds)

def get_exercise_focus_data(user_data, daily_activity_logs, dt_start_utc, dt_end_utc):

    total_seconds = 0
    dict_exercise_seconds = {}

    for daily_activity_log in daily_activity_logs:
        activity_summary = daily_activity_log.activity_summary
        for hour in activity_summary.hourly_summaries:

            hourly_activity_summary = activity_summary.hourly_summaries[hour]

            # We need to filter for dates outside of our range here because we expanded our DB query
            # to make sure we got the entire client time zone date range
            if hourly_activity_summary.date < dt_start_utc or hourly_activity_summary.date > dt_end_utc:
                continue

            for exercise_key in hourly_activity_summary.dict_exercises.keys():
                hourly_activity_summary_exercise_item = hourly_activity_summary.dict_exercises[exercise_key]

                exid = hourly_activity_summary_exercise_item.exercise

                key_exercise = exid.lower()
                if not dict_exercise_seconds.has_key(key_exercise):
                    dict_exercise_seconds[key_exercise] = {"exercise_title": models.Exercise.to_display_name(exid), "exid": exid, "seconds": 0, "correct": 0, "problems": 0}

                dict_exercise_seconds[key_exercise]["seconds"] += hourly_activity_summary_exercise_item.time_taken
                dict_exercise_seconds[key_exercise]["problems"] += hourly_activity_summary_exercise_item.c_problems
                dict_exercise_seconds[key_exercise]["correct"] += hourly_activity_summary_exercise_item.c_correct

                total_seconds += hourly_activity_summary_exercise_item.time_taken

    keys = dict_exercise_seconds.keys()
    for key_exercise in keys:
        percentage = 0
        if total_seconds > 0:
            percentage = int(float(dict_exercise_seconds[key_exercise]["seconds"]) / float(total_seconds) * 100.0)
        if percentage:
            dict_exercise_seconds[key_exercise]["percentage"] = percentage
            dict_exercise_seconds[key_exercise]["time_spent"] = seconds_to_time_string(dict_exercise_seconds[key_exercise]["seconds"], False)

            correct = dict_exercise_seconds[key_exercise]["correct"]
            dict_exercise_seconds[key_exercise]["s_correct_problems"] = "%d correct problem%s without a hint" % (correct, pluralize(correct))

            problems = dict_exercise_seconds[key_exercise]["problems"]
            dict_exercise_seconds[key_exercise]["s_problems"] = "%d total problem%s" % (problems, pluralize(problems))

            dict_exercise_seconds[key_exercise]["proficient"] = user_data.is_proficient_at(key_exercise)

        else:
            # Don't bother showing 0 percentage exercises
            del dict_exercise_seconds[key_exercise]

    return (total_seconds, dict_exercise_seconds)

def focus_graph_context(user_data_student, dt_start_utc, dt_end_utc):

    if not user_data_student:
        return {}

    # We have to expand by 1 day on each side to be sure we grab proper 'day' in client's time zone,
    # then we filter for proper time zone daily boundaries
    dt_start_utc_expanded = dt_start_utc - datetime.timedelta(days=1)
    dt_end_utc_expanded = dt_end_utc + datetime.timedelta(days=1)
    daily_activity_logs = models.DailyActivityLog.get_for_user_data_between_dts(user_data_student, dt_start_utc_expanded, dt_end_utc_expanded).fetch(1000)
    daily_activity_logs = activity_summary.fill_realtime_recent_daily_activity_summaries(daily_activity_logs, user_data_student, dt_end_utc_expanded)

    playlist_focus_data = get_playlist_focus_data(daily_activity_logs, dt_start_utc, dt_end_utc)
    exercise_focus_data = get_exercise_focus_data(user_data_student, daily_activity_logs, dt_start_utc, dt_end_utc)

    total_playlist_seconds = playlist_focus_data[0]
    dict_playlist_seconds = playlist_focus_data[1]

    total_exercise_seconds = exercise_focus_data[0]
    dict_exercise_seconds = exercise_focus_data[1]

    return {
            "student_email": user_data_student.email,
            "total_playlist_seconds": total_playlist_seconds,
            "dict_playlist_seconds": dict_playlist_seconds,
            "total_exercise_seconds": total_exercise_seconds,
            "dict_exercise_seconds": dict_exercise_seconds,
            "is_graph_empty": (total_playlist_seconds + total_exercise_seconds <= 0),
            }


