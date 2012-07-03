import os

import shared_jinja

from profiles import focus_graph, activity_graph, exercises_over_time_graph, exercise_problems_graph, exercise_progress_graph, recent_activity
from profiles import class_exercises_over_time_graph, class_energy_points_per_minute_graph, class_time_graph

from urlparse import urlunparse
from urllib import urlencode

def profile_graph_control():
    return {}

def render_graph_html_and_context(filename, context):
    path = os.path.join("profiles", filename)
    return {"html": shared_jinja.get().render_template(path, **context), "context": context}

# Profile Graph Types
def profile_activity_graph(user_data_student, dt_start, dt_end, tz_offset):
    return render_graph_html_and_context("activity_graph.html", activity_graph.activity_graph_context(user_data_student, dt_start, dt_end, tz_offset))
def profile_focus_graph(user_data_student, dt_start, dt_end):
    return render_graph_html_and_context("focus_graph.html", focus_graph.focus_graph_context(user_data_student, dt_start, dt_end))
def profile_exercises_over_time_graph(user_data_student):
    return render_graph_html_and_context("exercises_over_time_graph.html", exercises_over_time_graph.exercises_over_time_graph_context(user_data_student))
def profile_exercise_problems_graph(user_data_student, exid):
    return render_graph_html_and_context("exercise_problems_graph.html", exercise_problems_graph.exercise_problems_graph_context(user_data_student, exid))
def profile_exercise_progress_graph(user_data_student):
    return render_graph_html_and_context("exercise_progress_graph.html", exercise_progress_graph.exercise_progress_graph_context(user_data_student))
# End profile graph types

# Class profile graph types
def class_profile_exercises_over_time_graph(user_data_coach, student_list):
    return render_graph_html_and_context("class_exercises_over_time_graph.html", class_exercises_over_time_graph.class_exercises_over_time_graph_context(user_data_coach, student_list))
def class_profile_energy_points_per_minute_graph(user_data_coach, student_list):
    return render_graph_html_and_context("class_energy_points_per_minute_graph.html", class_energy_points_per_minute_graph.class_energy_points_per_minute_graph_context(user_data_coach, student_list))
def class_profile_energy_points_per_minute_update(user_data_coach, student_list):
    return class_energy_points_per_minute_graph.class_energy_points_per_minute_update(user_data_coach, student_list)
def class_profile_time_graph(user_data_coach, dt, tz_offset, student_list):
    return render_graph_html_and_context("class_time_graph.html", class_time_graph.class_time_graph_context(user_data_coach, dt, tz_offset, student_list))
# End class profile graph types

def get_graph_url(graph_type, student, coach, list_id):
    qs = {}
    if student:
        qs['student_email'] = student.email
    if coach:
        qs['coach_email'] = coach.email
    if list_id:
        qs['list_id'] = list_id

    urlpath = "/profile/graph/%s" % graph_type
    return urlunparse(('', '', urlpath, '', urlencode(qs), ''))

def get_api_url(prefix, api_function, student, coach, list_id):
    qs = {}
    if student:
        # Note - the API expects the email as "email", not "student_email"
        # like in the legacy graph URL's!
        qs['email'] = student.email
    if coach:
        qs['coach_email'] = coach.email
    if list_id:
        qs['list_id'] = list_id

    urlpath = "/api/v1/%s/%s" % (prefix, api_function)
    return urlunparse(('', '', urlpath, '', urlencode(qs), ''))

def profile_recent_activity(user_data, view="standard"):
    context = recent_activity.recent_activity_context(user_data)
    context["view"] = view

    return shared_jinja.get().render_template("profiles/recent_activity.html", **context)
