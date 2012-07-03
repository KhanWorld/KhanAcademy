import datetime

import models
import activity_summary
from badges import models_badges, util_badges
from templatefilters import seconds_to_time_string

class ActivityBucketType:
    HOUR = 0
    DAY = 1
    
def get_bucket_type(dt_start_utc, dt_end_utc):
    if (dt_end_utc - dt_start_utc).days > 1:
        return ActivityBucketType.DAY
    else:
        return ActivityBucketType.HOUR

def get_bucket_timedelta(bucket_type):
    if bucket_type == ActivityBucketType.DAY:
        return datetime.timedelta(days = 1)
    else:
        return datetime.timedelta(minutes = 60)

def get_bucket_value(dt_utc, tz_offset, bucket_type):
    dt_ctz = dt_utc + datetime.timedelta(minutes=tz_offset)

    if bucket_type == ActivityBucketType.DAY:
        return datetime.date(dt_ctz.year, dt_ctz.month, dt_ctz.day)
    else:
        return datetime.datetime(dt_ctz.year, dt_ctz.month, dt_ctz.day, dt_ctz.hour).strftime("%I:%M %p")

def get_empty_dict_bucket(bucket_list):
    dict_bucket = {}
    for bucket in bucket_list:
        dict_bucket[bucket] = None
    return dict_bucket

def get_bucket_list(dt_start_utc, dt_end_utc, tz_offset, bucket_type):

    bucket_list = []

    dt = dt_start_utc
    dt_last = dt

    while (dt < dt_end_utc):
        bucket_list.append(get_bucket_value(dt, tz_offset, bucket_type))
        dt_last = dt
        dt += get_bucket_timedelta(bucket_type)

    if get_bucket_value(dt_end_utc, tz_offset, bucket_type) != get_bucket_value(dt_last, tz_offset, bucket_type):
        # Make sure we always have the last bucket
        bucket_list.append(get_bucket_value(dt_end_utc, tz_offset, bucket_type))

    return bucket_list

def add_bucket_html_summary(dict_bucket, key, limit):
    for bucket in dict_bucket:
        if dict_bucket[bucket]:
            dict_entries = dict_bucket[bucket][key]
            list_entries = []
            c = 0
            for entry in dict_entries:
                if c >= limit:
                    list_entries.append("<em>...and %d more</em>" % (len(dict_entries) - limit))
                    break
                list_entries.append(entry)
                c += 1
            dict_bucket[bucket]["html_summary"] = "<br/>".join(list_entries)

def get_exercise_activity_data(user_data, bucket_list, bucket_type, daily_activity_logs, dt_start_utc, dt_end_utc, tz_offset):

    dict_bucket = get_empty_dict_bucket(bucket_list)

    for daily_activity_log in daily_activity_logs:
        activity_summary = daily_activity_log.activity_summary
        for hour in activity_summary.hourly_summaries:

            hourly_activity_summary = activity_summary.hourly_summaries[hour]

            # We need to filter for dates outside of our range here because we expanded our DB query
            # to make sure we got the entire client time zone date range
            if hourly_activity_summary.date < dt_start_utc or hourly_activity_summary.date > dt_end_utc:
                continue

            key = get_bucket_value(hourly_activity_summary.date, tz_offset, bucket_type)

            if not dict_bucket.has_key(key) or not hourly_activity_summary.has_exercise_activity():
                continue;

            if not dict_bucket[key]:
                dict_bucket[key] = {"minutes": 0, "seconds": 0, "points": 0, "exercise_names": {}}

            for exercise_key in hourly_activity_summary.dict_exercises.keys():
                activity_summary_exercise_item = hourly_activity_summary.dict_exercises[exercise_key]
                dict_bucket[key]["minutes"] += (activity_summary_exercise_item.time_taken / 60.0)
                dict_bucket[key]["seconds"] += activity_summary_exercise_item.time_taken
                dict_bucket[key]["points"] += activity_summary_exercise_item.points_earned
                dict_bucket[key]["exercise_names"][models.Exercise.to_display_name(activity_summary_exercise_item.exercise)] = True

    for bucket in bucket_list:
        if dict_bucket[bucket]:
            dict_bucket[bucket]["time_spent"] = seconds_to_time_string(dict_bucket[bucket]["seconds"], False)

    add_bucket_html_summary(dict_bucket, "exercise_names", 5)

    return dict_bucket

def get_playlist_activity_data(user_data, bucket_list, bucket_type, daily_activity_logs, dt_start_utc, dt_end_utc, tz_offset):

    dict_bucket = get_empty_dict_bucket(bucket_list)

    for daily_activity_log in daily_activity_logs:
        activity_summary = daily_activity_log.activity_summary
        for hour in activity_summary.hourly_summaries:

            hourly_activity_summary = activity_summary.hourly_summaries[hour]

            # We need to filter for dates outside of our range here because we expanded our DB query
            # to make sure we got the entire client time zone date range
            if hourly_activity_summary.date < dt_start_utc or hourly_activity_summary.date > dt_end_utc:
                continue

            key = get_bucket_value(hourly_activity_summary.date, tz_offset, bucket_type)
            if not dict_bucket.has_key(key) or not hourly_activity_summary.has_video_activity():
                continue;

            if not dict_bucket[key]:
                dict_bucket[key] = {"minutes": 0, "seconds": 0, "points": 0, "video_titles": {}}

            for video_key in hourly_activity_summary.dict_videos.keys():
                activity_summary_video_item = hourly_activity_summary.dict_videos[video_key]
                dict_bucket[key]["minutes"] += (activity_summary_video_item.seconds_watched / 60.0)
                dict_bucket[key]["seconds"] += activity_summary_video_item.seconds_watched
                dict_bucket[key]["points"] += activity_summary_video_item.points_earned
                dict_bucket[key]["video_titles"][activity_summary_video_item.video_title] = True

    for bucket in bucket_list:
        if dict_bucket[bucket]:
            dict_bucket[bucket]["time_spent"] = seconds_to_time_string(dict_bucket[bucket]["seconds"], False)

    add_bucket_html_summary(dict_bucket, "video_titles", 5)

    return dict_bucket

def get_badge_activity_data(user_data, bucket_list, bucket_type, dt_start_utc, dt_end_utc, tz_offset):

    dict_bucket = get_empty_dict_bucket(bucket_list)
    user_badges = models_badges.UserBadge.get_for_user_data_between_dts(user_data, dt_start_utc, dt_end_utc).fetch(1000)
    badges_dict = util_badges.all_badges_dict()

    for user_badge in user_badges:
        key = get_bucket_value(user_badge.date, tz_offset, bucket_type)

        badge = badges_dict.get(user_badge.badge_name)
        if not badge:
            continue

        if not dict_bucket.has_key(key):
            continue;

        if not dict_bucket[key]:
            dict_bucket[key] = {"points": 0, "badge_category": -1, "badge_url": "", "badge_descriptions": {}}

        dict_bucket[key]["points"] += user_badge.points_earned
        dict_bucket[key]["badge_descriptions"][badge.description] = True

        if badge.badge_category > dict_bucket[key]["badge_category"]:
            dict_bucket[key]["badge_url"] = badge.chart_icon_src()
            dict_bucket[key]["badge_category"] = badge.badge_category

    add_bucket_html_summary(dict_bucket, "badge_descriptions", 3)

    return dict_bucket

def get_proficiency_activity_data(user_data, bucket_list, bucket_type, dt_start_utc, dt_end_utc, tz_offset):

    dict_bucket = get_empty_dict_bucket(bucket_list)
    user_exercise_graph = models.UserExerciseGraph.get(user_data)

    for graph_dict in user_exercise_graph.graph_dicts():

        if not graph_dict["proficient_date"]:
            continue

        if graph_dict["proficient_date"] < dt_start_utc or graph_dict["proficient_date"] > dt_end_utc:
            continue

        key = get_bucket_value(graph_dict["proficient_date"], tz_offset, bucket_type)

        if not dict_bucket.has_key(key):
            continue;

        if not dict_bucket[key]:
            dict_bucket[key] = {"exercise_names": {}}

        dict_bucket[key]["exercise_names"][models.Exercise.to_display_name(graph_dict["name"])] = True

    add_bucket_html_summary(dict_bucket, "exercise_names", 3)

    return dict_bucket

def get_points_activity_data(bucket_list, dict_playlist_buckets, dict_exercise_buckets, dict_badge_buckets):
    dict_bucket = get_empty_dict_bucket(bucket_list)

    for bucket in bucket_list:
        dict_bucket[bucket] = 0
        if dict_playlist_buckets[bucket]:
            dict_bucket[bucket] += dict_playlist_buckets[bucket]["points"]
        if dict_exercise_buckets[bucket]:
            dict_bucket[bucket] += dict_exercise_buckets[bucket]["points"]
        if dict_badge_buckets[bucket]:
            dict_bucket[bucket] += dict_badge_buckets[bucket]["points"]

    return dict_bucket

def map_scatter_y_values(dict_target, dict_exercise_buckets, dict_playlist_buckets):
    # Icon's y coordinate is set just above the highest playlist/exercise time spent
    for key in dict_target:
        if dict_target[key]:
            bucket_minutes_playlist = dict_playlist_buckets[key]["minutes"] if dict_playlist_buckets[key] else 0
            bucket_minutes_exercise= dict_exercise_buckets[key]["minutes"] if dict_exercise_buckets[key] else 0
            dict_target[key]["y"] = bucket_minutes_playlist + bucket_minutes_exercise

def has_activity_type(dict_target, bucket, key_activity):
    return dict_target[bucket] and dict_target[bucket][key_activity]

def activity_graph_context(user_data_student, dt_start_utc, dt_end_utc, tz_offset):

    if not user_data_student:
        return {}

    # We have to expand by 1 day on each side to be sure we grab proper 'day' in client's time zone,
    # then we filter for proper time zone daily boundaries
    dt_start_utc_expanded = dt_start_utc - datetime.timedelta(days=1)
    dt_end_utc_expanded = dt_end_utc + datetime.timedelta(days=1)
    daily_activity_logs = models.DailyActivityLog.get_for_user_data_between_dts(user_data_student, dt_start_utc_expanded, dt_end_utc_expanded).fetch(1000)
    daily_activity_logs = activity_summary.fill_realtime_recent_daily_activity_summaries(daily_activity_logs, user_data_student, dt_end_utc_expanded)

    bucket_type = get_bucket_type(dt_start_utc, dt_end_utc)
    bucket_list = get_bucket_list(dt_start_utc, dt_end_utc, tz_offset, bucket_type)

    dict_playlist_buckets = get_playlist_activity_data(user_data_student, bucket_list, bucket_type, daily_activity_logs, dt_start_utc, dt_end_utc, tz_offset)
    dict_exercise_buckets = get_exercise_activity_data(user_data_student, bucket_list, bucket_type, daily_activity_logs, dt_start_utc, dt_end_utc, tz_offset)
    dict_badge_buckets = get_badge_activity_data(user_data_student, bucket_list, bucket_type, dt_start_utc, dt_end_utc, tz_offset)
    dict_proficiency_buckets = get_proficiency_activity_data(user_data_student, bucket_list, bucket_type, dt_start_utc, dt_end_utc, tz_offset)
    dict_points_buckets = get_points_activity_data(bucket_list, dict_playlist_buckets, dict_exercise_buckets, dict_badge_buckets)

    map_scatter_y_values(dict_badge_buckets, dict_playlist_buckets, dict_exercise_buckets)
    map_scatter_y_values(dict_proficiency_buckets, dict_playlist_buckets, dict_exercise_buckets)

    has_activity = False
    for bucket in bucket_list:
        if (has_activity_type(dict_playlist_buckets, bucket, "minutes") or
            has_activity_type(dict_exercise_buckets, bucket, "minutes") or
            has_activity_type(dict_badge_buckets, bucket, "badge_category")):
                has_activity = True
                break

    graph_title = ""
    if bucket_type == ActivityBucketType.HOUR:
        graph_title = str(get_bucket_value(dt_start_utc, tz_offset, ActivityBucketType.DAY))

    return {
            "is_graph_empty": not has_activity,
            "bucket_list": bucket_list,
            "enable_drill_down": (bucket_type != ActivityBucketType.HOUR),
            "dict_playlist_buckets": dict_playlist_buckets,
            "dict_exercise_buckets": dict_exercise_buckets,
            "dict_badge_buckets": dict_badge_buckets,
            "dict_proficiency_buckets": dict_proficiency_buckets,
            "dict_points_buckets": dict_points_buckets,
            "student_email": user_data_student.email,
            "tz_offset": tz_offset,
            "graph_title": graph_title,
            }
