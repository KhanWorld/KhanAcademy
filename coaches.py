from app import App
import app
import facebook_util
import util
import user_util
from request_handler import RequestHandler

from models import UserData, CoachRequest, StudentList
from badges import util_badges

from profiles.util_profile import ExercisesOverTimeGraph, ExerciseProblemsGraph
from profiles.util_profile import ClassProgressReportGraph, ClassEnergyPointsPerMinuteGraph, ClassTimeGraph

from phantom_users.phantom_util import disallow_phantoms
import profiles.util_profile as util_profile
import simplejson as json


class ViewCoaches(RequestHandler):
    @disallow_phantoms
    def get(self):
        user_data = UserData.current()

        if user_data:
            invalid_coach = self.request_bool("invalid_coach", default = False)

            coach_requests = CoachRequest.get_for_student(user_data).fetch(1000)

            template_values = {
                        "coach_emails": user_data.coach_emails(),
                        "invalid_coach": invalid_coach,
                        "coach_requests": coach_requests,
                        "student_id": user_data.email,
                        'selected_nav_link': 'coach'
                    }

            self.render_jinja2_template('viewcoaches.html', template_values)
        else:
            self.redirect(util.create_login_url(self.request.uri))


class ViewStudents(RequestHandler):
    @disallow_phantoms
    def get(self):
        user_data = UserData.current()

        if user_data:

            user_data_override = self.request_user_data("coach_email")
            if user_util.is_current_user_developer() and user_data_override:
                user_data = user_data_override

            invalid_student = self.request_bool("invalid_student", default = False)

            coach_requests = [x.student_requested_data.email for x in CoachRequest.get_for_coach(user_data) if x.student_requested_data]

            student_lists_models = StudentList.get_for_coach(user_data.key())
            student_lists_list = [];
            for student_list in student_lists_models:
                student_lists_list.append({
                    'key': str(student_list.key()),
                    'name': student_list.name,
                })
            student_lists_dict = dict((g['key'], g) for g in student_lists_list)

            students_data = user_data.get_students_data()
            students = map(lambda s: {
                'key': str(s.key()),
                'email': s.email,
                'nickname': s.nickname,
                'student_lists': [l for l in [student_lists_dict.get(str(list_id)) for list_id in s.student_lists] if l],
            }, students_data)
            students.sort(key=lambda s: s['nickname'])

            template_values = {
                "students": students,
                "students_json": json.dumps(students),
                "student_lists": student_lists_list,
                "student_lists_json": json.dumps(student_lists_list),
                "invalid_student": invalid_student,
                "coach_requests": coach_requests,
                "coach_requests_json": json.dumps(coach_requests),
                'selected_nav_link': 'coach'
            }
            self.render_jinja2_template('viewstudentlists.html', template_values)
        else:
            self.redirect(util.create_login_url(self.request.uri))


class RegisterCoach(RequestHandler):
    @disallow_phantoms
    def post(self):
        user_data = UserData.current()

        if not user_data:
            self.redirect(util.create_login_url(self.request.uri))
            return

        user_data_coach = self.request_user_data("coach")
        if user_data_coach:
            if not user_data.is_coached_by(user_data_coach):
                user_data.coaches.append(user_data_coach.key_email)
                user_data.put()

            if not self.is_ajax_request():
                self.redirect("/coaches")
            return

        if self.is_ajax_request():
            self.response.set_status(400)
        else:
            self.redirect("/coaches?invalid_coach=1")

class RequestStudent(RequestHandler):
    @disallow_phantoms
    def post(self):
        user_data = UserData.current()

        if not user_data:
            self.redirect(util.create_login_url(self.request.uri))
            return
        user_data_student = self.request_user_data("student_email")
        if user_data_student:
            if not user_data_student.is_coached_by(user_data):
                coach_request = CoachRequest.get_or_insert_for(user_data, user_data_student)
                if coach_request:
                    if not self.is_ajax_request():
                        self.redirect("/students")
                    return

        if self.is_ajax_request():
            self.response.set_status(404)
        else:
            self.redirect("/students?invalid_student=1")


class AcceptCoach(RequestHandler):
    @RequestHandler.exceptions_to_http(400)
    @disallow_phantoms
    def get(self):
        user_data = UserData.current()

        if not user_data:
            self.redirect(util.create_login_url(self.request.uri))
            return

        accept_coach = self.request_bool("accept", default = False)
        user_data_coach = self.request_user_data("coach_email")
        user_data_student = self.request_user_data('student_email')

        if bool(user_data_coach) == bool(user_data_student):
            raise Exception('must provide coach_email xor student_email')

        if user_data_coach:
            user_data_student = user_data
        elif user_data_student:
            user_data_coach = user_data

        if user_data_coach and not user_data_student.is_coached_by(user_data_coach):
            coach_request = CoachRequest.get_for(user_data_coach, user_data_student)
            if coach_request:
                coach_request.delete()

                if user_data.key_email == user_data_student.key_email and accept_coach:
                    user_data_student.coaches.append(user_data_coach.key_email)
                    user_data_student.put()

        if not self.is_ajax_request():
            self.redirect("/coaches")

class UnregisterStudentCoach(RequestHandler):
    @staticmethod
    def remove_student_from_coach(student, coach):
        if student.student_lists:
            actual_lists = StudentList.get(student.student_lists)
            student.student_lists = [l.key() for l in actual_lists if coach.key() not in l.coaches]

        try:
            student.coaches.remove(coach.key_email)
        except ValueError:
            pass

        try:
            student.coaches.remove(coach.key_email.lower())
        except ValueError:
            pass

        student.put()

    def do_request(self, student, coach, redirect_to):
        if not UserData.current():
            self.redirect(util.create_login_url(self.request.uri))
            return

        if student and coach:
            self.remove_student_from_coach(student, coach)

        if not self.is_ajax_request():
            self.redirect(redirect_to)

class UnregisterCoach(UnregisterStudentCoach):
    @disallow_phantoms
    def get(self):
        return self.do_request(
            UserData.current(),
            self.request_user_data("coach"),
            "/coaches"
        )

class UnregisterStudent(UnregisterStudentCoach):
    @disallow_phantoms
    def get(self):
        return self.do_request(
            self.request_user_data("student_email"),
            UserData.current(),
            "/students"
        )

class CreateStudentList(RequestHandler):
    @RequestHandler.exceptions_to_http(400)
    def post(self):
        coach_data = UserData.current()

        if not coach_data:
            return

        list_name = self.request_string('list_name')
        if not list_name:
            raise Exception('Invalid list name')

        student_list = StudentList(coaches=[coach_data.key()], name=list_name)
        student_list.put()

        student_list_json = {
            'name': student_list.name,
            'key': str(student_list.key())
        }

        self.render_json(student_list_json)

class DeleteStudentList(RequestHandler):
    @RequestHandler.exceptions_to_http(400)
    def post(self):
        coach_data = UserData.current()

        if not coach_data:
            return

        student_list = util_profile.get_student_list(coach_data,
            self.request_string('list_id'))
        student_list.delete()
        if not self.is_ajax_request():
            self.redirect_to('/students')

class AddStudentToList(RequestHandler):
    @RequestHandler.exceptions_to_http(400)
    def post(self):
        coach_data, student_data, student_list = util_profile.get_coach_student_and_student_list(self)

        if student_list.key() in student_data.student_lists:
            raise Exception("Student %s is already in list %s" % (student_data.key(), student_list.key()))

        student_data.student_lists.append(student_list.key())
        student_data.put()

class RemoveStudentFromList(RequestHandler):
    @RequestHandler.exceptions_to_http(400)
    def post(self):
        coach_data, student_data, student_list = util_profile.get_coach_student_and_student_list(self)

        # due to a bug, we have duplicate lists in the collection. fix this:
        student_data.student_lists = list(set(student_data.student_lists))

        student_data.student_lists.remove(student_list.key())
        student_data.put()

class ViewIndividualReport(RequestHandler):
    def get(self):
        # Individual reports being replaced by user profile
        self.redirect("/profile")

class ViewSharedPoints(RequestHandler):
    def get(self):
        self.redirect("/class_profile?selected_graph_type=%s" % ClassEnergyPointsPerMinuteGraph.GRAPH_TYPE)

class ViewProgressChart(RequestHandler):
    def get(self):
        self.redirect("/profile?selected_graph_type=" + ExercisesOverTimeGraph.GRAPH_TYPE)

class ViewClassTime(RequestHandler):
    def get(self):
        self.redirect("/class_profile?selected_graph_type=%s" % ClassTimeGraph.GRAPH_TYPE)

class ViewClassReport(RequestHandler):
    def get(self):
        self.redirect("/class_profile?selected_graph_type=%s" % ClassProgressReportGraph.GRAPH_TYPE)

class ViewCharts(RequestHandler):
    def get(self):
        student_email = self.request_student_email_legacy()
        url = "/profile?selected_graph_type=%s&student_email=%s&exid=%s" % (
            ExerciseProblemsGraph.GRAPH_TYPE,
            student_email,
            self.request_string("exercise_name"))
        self.redirect(url)
