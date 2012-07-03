import datetime
import util
import logging

from models import UserExercise, Exercise, UserData, UserExerciseGraph

def exercise_progress_graph_context(user_data_student):

    if not user_data_student:
        return {}
    
    exercise_data = {}
    
    exercises = Exercise.get_all_use_cache()
    user_exercise_graph = UserExerciseGraph.get(user_data_student)

    review_exercise_names = user_exercise_graph.review_exercise_names()

    for exercise in exercises:
        chart_link =""
        status = ""
        color = "transparent"
        exercise_display = Exercise.to_display_name(exercise.name)
        hover = "<b>%s</b><br/><em><nobr>Status: %s</nobr></em><br/><em>Progress: %s</em><br/><em>Problems attempted: %s</em>" % ( exercise_display, "Not Started", '0%', 0)

        chart_link = "/profile/graph/exerciseproblems?student_email=%s&exercise_name=%s" % (user_data_student.email, exercise.name) 
                
        graph_dict = user_exercise_graph.graph_dict(exercise.name)

        if graph_dict["proficient"]:

            if exercise.name in review_exercise_names:
                status = "Review"
                color = "review light"
            else:
                status = "Proficient"
                color = "proficient"
                if not graph_dict["explicitly_proficient"]:
                    status = "Proficient (due to proficiency in a more advanced module)"

        elif graph_dict["struggling"]:
            status = "Struggling"
            color = "struggling"
        elif graph_dict["total_done"] > 0:
            status = "Started"
            color = "started"

        if len(status) > 0:
            hover = "<b>%s</b><br/><em><nobr>Status: %s</nobr></em><br/><em>Progress: %s</em><br/><em>Problems attempted: %s</em>" % (exercise_display, 
                        status, 
                        UserExercise.to_progress_display(graph_dict["progress"]),
                        graph_dict["total_done"])

        exercise_data[exercise.name] = {
                "short_name": exercise.short_name(),
                "chart_link": chart_link,
                "ex_link": exercise.relative_url,
                "hover": hover,
                "color": color
                }
                
    return { 'exercises': exercises, 'exercise_data': exercise_data, }
