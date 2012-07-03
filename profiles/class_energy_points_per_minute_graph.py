from google.appengine.api import users

import simplejson

import models
import util

def class_energy_points_per_minute_update(user_data, student_list):
    points = 0
    if user_data or student_list:
        if student_list:
            students_data = student_list.get_students_data()
        else:
            students_data = user_data.get_students_data()
        for student_data in students_data:
            points += student_data.points
    return simplejson.dumps({"points": points})

def class_energy_points_per_minute_graph_context(user_data, student_list):
    if not user_data:
        return {}

    if student_list:
        students_data = student_list.get_students_data()
    else:
        students_data = user_data.get_students_data()

    return {
            'user_data_coach': user_data,
            'user_data_students': students_data,
            'c_points': reduce(lambda a, b: a + b, map(lambda s: s.points, students_data), 0)
            }
