import models

class ExerciseData:
        def __init__(self, nickname, exid, days_until_proficient, proficient_date):
            self.nickname = nickname
            self.exid = exid
            self.days_until_proficient = days_until_proficient
            self.proficient_date = proficient_date

        def display_name(self):
            return  models.Exercise.to_display_name(self.exid)

def class_exercises_over_time_graph_context(user_data, student_list):

    if not user_data:
        return {}
 
    if student_list:
        students_data = student_list.get_students_data()
    else:
        students_data = user_data.get_students_data()
  
    dict_student_exercises = {}
    user_exercise_cache_list = models.UserExerciseCache.get(students_data)
    for i, user_data_student in enumerate(students_data):
        student_nickname = user_data_student.nickname
        dict_student_exercises[student_nickname] = { "nickname": student_nickname, "email": user_data_student.email, "exercises": [] }
            
        for exercise, user_exercise in user_exercise_cache_list[i].dicts.iteritems():
            if user_exercise["proficient_date"]:
                joined = min(user_data_student.joined, user_exercise["proficient_date"])
                days_until_proficient = (user_exercise["proficient_date"] - joined).days
                proficient_date = user_exercise["proficient_date"].strftime('%m/%d/%Y')
                data = ExerciseData(student_nickname, exercise, days_until_proficient, proficient_date)
                dict_student_exercises[student_nickname]["exercises"].append(data)
   
        dict_student_exercises[student_nickname]["exercises"].sort(key = lambda k : k.days_until_proficient)


    return {
            "dict_student_exercises": dict_student_exercises,
            "user_data_students": students_data,
            "c_points": reduce(lambda a, b: a + b, map(lambda s: s.points, students_data), 0)
            }

