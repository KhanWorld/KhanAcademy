import datetime
import urllib

from profiles import templatetags
import request_handler
import util
import models
import consts
from api.auth.xsrf import ensure_xsrf_cookie
from badges import util_badges
from phantom_users.phantom_util import disallow_phantoms
from models import StudentList, UserData
import simplejson

def get_last_student_list(request_handler, student_lists, use_cookie=True):
    student_lists = student_lists.fetch(100)

    # default_list is the default list for this user
    if student_lists:
        default_list = str(student_lists[0].key())
    else:
        default_list = 'allstudents'

    # desired list is the list the user asked for (via cookie or querystring)
    desired_list = None

    if use_cookie:
        cookie_val = request_handler.get_cookie_value('studentlist_id')
        desired_list = cookie_val or desired_list

    # override cookie with explicitly set querystring
    desired_list = request_handler.request_string('list_id', desired_list)

    # now validate desired_list exists
    current_list = None
    list_id = 'allstudents'
    if desired_list != 'allstudents':
        for s in student_lists:
            if str(s.key()) == desired_list:
                current_list = s
                list_id = desired_list
                break

        if current_list is None:
            list_id = default_list

    if use_cookie:
        request_handler.set_cookie('studentlist_id', list_id, max_age=2629743)

    return list_id, current_list

def get_student(coach, request_handler):
    student = request_handler.request_student_user_data(legacy=True)
    if student is None:
        raise Exception("No student found with email='%s'."
            % request_handler.request_student_email_legacy())
    if not student.is_coached_by(coach):
        raise Exception("Not your student!")
    return student

def get_student_list(coach, list_key):
    student_list = StudentList.get(list_key)
    if student_list is None:
        raise Exception("No list found with list_key='%s'." % list_key)
    if coach.key() not in student_list.coaches:
        raise Exception("Not your list!")
    return student_list

# Return a list of students, either from the list or from the user data,
# dependent on the contents of a querystring parameter.
def get_students_data(user_data, list_key=None):
    student_list = None
    if list_key and list_key != 'allstudents':
        student_list = get_student_list(user_data, list_key)

    if student_list:
        return student_list.get_students_data()
    else:
        return user_data.get_students_data()

def get_coach_student_and_student_list(request_handler):
    coach = UserData.current()
    student_list = get_student_list(coach,
        request_handler.request_string("list_id"))
    student = get_student(coach, request_handler)
    return (coach, student, student_list)

class ViewClassProfile(request_handler.RequestHandler):
    @disallow_phantoms
    @ensure_xsrf_cookie
    def get(self):
        coach = UserData.current()

        if coach:

            user_override = self.request_user_data("coach_email")
            if user_override and user_override.are_students_visible_to(coach):
                # Only allow looking at a student list other than your own
                # if you are a dev, admin, or coworker.
                coach = user_override

            student_lists = StudentList.get_for_coach(coach.key())

            student_lists_list = [{
                'key': 'allstudents',
                'name': 'All students',
            }];
            for student_list in student_lists:
                student_lists_list.append({
                    'key': str(student_list.key()),
                    'name': student_list.name,
                })

            list_id, _ = get_last_student_list(self, student_lists, coach==UserData.current())
            current_list = None
            for student_list in student_lists_list:
                if student_list['key'] == list_id:
                    current_list = student_list

            selected_graph_type = self.request_string("selected_graph_type") or ClassProgressReportGraph.GRAPH_TYPE
            if selected_graph_type == 'progressreport' or selected_graph_type == 'goals': # TomY This is temporary until all the graphs are API calls
                initial_graph_url = "/api/v1/user/students/%s?coach_email=%s&%s" % (selected_graph_type, urllib.quote(coach.email), urllib.unquote(self.request_string("graph_query_params", default="")))
            else:
                initial_graph_url = "/profile/graph/%s?coach_email=%s&%s" % (selected_graph_type, urllib.quote(coach.email), urllib.unquote(self.request_string("graph_query_params", default="")))
            initial_graph_url += 'list_id=%s' % list_id

            template_values = {
                    'user_data_coach': coach,
                    'coach_email': coach.email,
                    'list_id': list_id,
                    'student_list': current_list,
                    'student_lists': student_lists_list,
                    'student_lists_json': simplejson.dumps(student_lists_list),
                    'coach_nickname': coach.nickname,
                    'selected_graph_type': selected_graph_type,
                    'initial_graph_url': initial_graph_url,
                    'exercises': models.Exercise.get_all_use_cache(),
                    'is_profile_empty': not coach.has_students(),
                    'selected_nav_link': 'coach',
                    "view": self.request_string("view", default=""),
                    'stats_charts_class': 'coach-view',
                    }
            self.render_jinja2_template('viewclassprofile.html', template_values)
        else:
            self.redirect(util.create_login_url(self.request.uri))

class ViewProfile(request_handler.RequestHandler):

    @ensure_xsrf_cookie
    def get(self):
        student = UserData.current() or UserData.pre_phantom()

        user_override = self.request_student_user_data(legacy=True)
        if user_override and user_override.key_email != student.key_email:
            if not user_override.is_visible_to(student):
                # If current user isn't an admin or student's coach, they can't
                # look at anything other than their own profile.
                self.redirect("/profile")
                return
            else:
                # Allow access to this student's profile
                student = user_override
        user_badges = util_badges.get_user_badges(student)
        selected_graph_type = (self.request_string("selected_graph_type") or
                               ActivityGraph.GRAPH_TYPE)

        # TODO: deal with this one-off hackery. Some graphs use the API
        # to fetch data, instead of the /profile/graph methods.
        if selected_graph_type == "exerciseprogress":
            initial_graph_url = ("/api/v1/user/exercises?email=%s" %
                                 urllib.quote(student.email))
        elif selected_graph_type == "goals":
            initial_graph_url = ("/api/v1/user/goals?email=%s" %
                                 urllib.quote(student.email))
        else:
            initial_graph_url = "/profile/graph/%s?student_email=%s&%s" % (
                    selected_graph_type,
                    urllib.quote(student.email),
                    urllib.unquote(self.request_string("graph_query_params",
                                                       default="")))
        tz_offset = self.request_int("tz_offset", default=0)

        template_values = {
            'student_email': student.email,
            'student_nickname': student.nickname,
            'selected_graph_type': selected_graph_type,
            'initial_graph_url': initial_graph_url,
            'tz_offset': tz_offset,
            'student_points': student.points,
            'count_videos': models.Setting.count_videos(),
            'count_videos_completed': student.get_videos_completed(),
            'count_exercises': models.Exercise.get_count(),
            'count_exercises_proficient': len(student.all_proficient_exercises),
            'badge_collections': user_badges['badge_collections'],
            'user_badges_bronze': user_badges['bronze_badges'],
            'user_badges_silver': user_badges['silver_badges'],
            'user_badges_gold': user_badges['gold_badges'],
            'user_badges_platinum': user_badges['platinum_badges'],
            'user_badges_diamond': user_badges['diamond_badges'],
            'user_badges_master': user_badges['user_badges_master'],
            'user_badges': [user_badges['bronze_badges'], user_badges['silver_badges'], user_badges['gold_badges'], user_badges['platinum_badges'], user_badges['diamond_badges'],user_badges['user_badges_master']],
            'user_data_student': student,
            "show_badge_frequencies": self.request_bool("show_badge_frequencies", default=False),
            "view": self.request_string("view", default=""),
        }

        self.render_jinja2_template('viewprofile.html', template_values)

class ProfileGraph(request_handler.RequestHandler):

    def get(self):
        html = ""
        json_update = ""

        user_data_target = self.get_profile_target_user_data()
        if user_data_target:

            if self.redirect_if_not_ajax(user_data_target):
                return

            if self.request_bool("update", default=False):
                json_update = self.json_update(user_data_target)
            else:
                html_and_context = self.graph_html_and_context(user_data_target)

                if html_and_context["context"].has_key("is_graph_empty") and html_and_context["context"]["is_graph_empty"]:
                    # This graph is empty of activity. If it's a date-restricted graph, see if bumping out the time restrictions can help.
                    if self.redirect_for_more_data():
                        return

                html = html_and_context["html"]

        if len(json_update) > 0:
            self.response.out.write(json_update)
        else:
            self.response.out.write(html)

    def get_profile_target_user_data(self):
        student = UserData.current() or UserData.pre_phantom()

        if student:
            user_override = self.request_student_user_data(legacy=True)
            if user_override and user_override.key_email != student.key_email:
                if not user_override.is_visible_to(student):
                    # If current user isn't an admin or student's coach, they can't look at anything other than their own profile.
                    student = None
                else:
                    # Allow access to this student's profile
                    student = user_override

        return student

    def redirect_if_not_ajax(self, student):
        if not self.is_ajax_request():
            # If it's not an ajax request, redirect to the appropriate /profile URL
            self.redirect("/profile?selected_graph_type=%s&student_email=%s&graph_query_params=%s" %
                    (self.GRAPH_TYPE, urllib.quote(student.email), urllib.quote(urllib.quote(self.request.query_string))))
            return True
        return False

    def redirect_for_more_data(self):
        return False

    def json_update(self, user_data):
        return ""

class ClassProfileGraph(ProfileGraph):
    def get_profile_target_user_data(self):
        coach = UserData.current()

        if coach:
            user_override = self.request_user_data("coach_email")
            if user_override and user_override.are_students_visible_to(coach):
                # Only allow looking at a student list other than your own
                # if you are a dev, admin, or coworker.
                coach = user_override

        return coach

    def redirect_if_not_ajax(self, coach):
        if not self.is_ajax_request():
            # If it's not an ajax request, redirect to the appropriate /profile URL
            self.redirect("/class_profile?selected_graph_type=%s&coach_email=%s&graph_query_params=%s" %
                    (self.GRAPH_TYPE, urllib.quote(coach.email), urllib.quote(urllib.quote(self.request.query_string))))
            return True
        return False

    def get_student_list(self, coach):
        student_lists = StudentList.get_for_coach(coach.key())
        _, actual_list = get_last_student_list(self, student_lists, coach.key()==UserData.current().key())
        return actual_list

class ProfileDateToolsGraph(ProfileGraph):

    DATE_FORMAT = "%Y-%m-%d"

    @staticmethod
    def inclusive_start_date(dt):
        return datetime.datetime(dt.year, dt.month, dt.day, 0, 0, 0) # Inclusive of start date

    @staticmethod
    def inclusive_end_date(dt):
        return datetime.datetime(dt.year, dt.month, dt.day, 23, 59, 59) # Inclusive of end date

    def request_date_ctz(self, key):
        # Always work w/ client timezone dates on the client and UTC dates on the server
        dt = self.request_date(key, self.DATE_FORMAT, default=datetime.datetime.min)
        if dt == datetime.datetime.min:
            s_dt = self.request_string(key, default="")
            if s_dt == "today":
                dt = self.inclusive_start_date(self.utc_to_ctz(datetime.datetime.now()))
            elif s_dt == "yesterday":
                dt = self.inclusive_start_date(self.utc_to_ctz(datetime.datetime.now()) - datetime.timedelta(days=1))
            elif s_dt == "lastweek":
                dt = self.inclusive_start_date(self.utc_to_ctz(datetime.datetime.now()) - datetime.timedelta(days=6))
            elif s_dt == "lastmonth":
                dt = self.inclusive_start_date(self.utc_to_ctz(datetime.datetime.now()) - datetime.timedelta(days=29))
        return dt

    def tz_offset(self):
        return self.request_int("tz_offset", default=0)

    def ctz_to_utc(self, dt_ctz):
        return dt_ctz - datetime.timedelta(minutes=self.tz_offset())

    def utc_to_ctz(self, dt_utc):
        return dt_utc + datetime.timedelta(minutes=self.tz_offset())

class ClassProfileDateGraph(ClassProfileGraph, ProfileDateToolsGraph):

    DATE_FORMAT = "%m/%d/%Y"

    def get_date(self):
        dt_ctz = self.request_date_ctz("dt")

        if dt_ctz == datetime.datetime.min:
            # If no date, assume looking at today
            dt_ctz = self.utc_to_ctz(datetime.datetime.now())

        return self.ctz_to_utc(self.inclusive_start_date(dt_ctz))

class ProfileDateRangeGraph(ProfileDateToolsGraph):

    def get_start_date(self):
        dt_ctz = self.request_date_ctz("dt_start")

        if dt_ctz == datetime.datetime.min:
            # If no start date, assume looking at last 7 days
            dt_ctz = self.utc_to_ctz(datetime.datetime.now() - datetime.timedelta(days=6))

        return self.ctz_to_utc(self.inclusive_start_date(dt_ctz))

    def get_end_date(self):
        dt_ctz = self.request_date_ctz("dt_end")
        dt_start_ctz_test = self.request_date_ctz("dt_start")
        dt_start_ctz = self.utc_to_ctz(self.get_start_date())

        if (dt_ctz == datetime.datetime.min and dt_start_ctz_test == datetime.datetime.min):
            # If no end date or start date specified, assume looking at 7 days after start date
            dt_ctz = dt_start_ctz + datetime.timedelta(days=6)
        elif dt_ctz == datetime.datetime.min:
            # If start date specified but no end date, assume one day
            dt_ctz = dt_start_ctz

        if (dt_ctz - dt_start_ctz).days > consts.MAX_GRAPH_DAY_RANGE or dt_start_ctz > dt_ctz:
            # Maximum range of 30 days for now
            dt_ctz = dt_start_ctz + datetime.timedelta(days=consts.MAX_GRAPH_DAY_RANGE)

        return self.ctz_to_utc(self.inclusive_end_date(dt_ctz))

    def redirect_for_more_data(self):
        dt_start_ctz_test = self.request_date_ctz("dt_start")
        dt_end_ctz_test = self.request_date_ctz("dt_end")

        # If no dates were specified and activity was empty, try max day range instead of default 7.
        if dt_start_ctz_test == datetime.datetime.min and dt_end_ctz_test == datetime.datetime.min:
            self.redirect(self.request_url_with_additional_query_params("dt_start=lastmonth&dt_end=today&is_ajax_override=1"))
            return True

        return False

class ActivityGraph(ProfileDateRangeGraph):
    GRAPH_TYPE = "activity"
    def graph_html_and_context(self, student):
        return templatetags.profile_activity_graph(student, self.get_start_date(), self.get_end_date(), self.tz_offset())

class FocusGraph(ProfileDateRangeGraph):
    GRAPH_TYPE = "focus"
    def graph_html_and_context(self, student):
        return templatetags.profile_focus_graph(student, self.get_start_date(), self.get_end_date())

class ExercisesOverTimeGraph(ProfileGraph):
    GRAPH_TYPE = "exercisesovertime"
    def graph_html_and_context(self, student):
        return templatetags.profile_exercises_over_time_graph(student)

class ExerciseProblemsGraph(ProfileGraph):
    GRAPH_TYPE = "exerciseproblems"
    def graph_html_and_context(self, student):
        return templatetags.profile_exercise_problems_graph(student, self.request_string("exercise_name"))

class ExerciseProgressGraph(ProfileGraph):
    GRAPH_TYPE = "exerciseprogress"
    def graph_html_and_context(self, student):
        return templatetags.profile_exercise_progress_graph(student)

class ClassExercisesOverTimeGraph(ClassProfileGraph):
    GRAPH_TYPE = "classexercisesovertime"
    def graph_html_and_context(self, coach):
        student_list = self.get_student_list(coach)
        return templatetags.class_profile_exercises_over_time_graph(coach, student_list)

class ClassProgressReportGraph(ClassProfileGraph):
    GRAPH_TYPE = "progressreport"

class ClassTimeGraph(ClassProfileDateGraph):
    GRAPH_TYPE = "classtime"
    def graph_html_and_context(self, coach):
        student_list = self.get_student_list(coach)
        return templatetags.class_profile_time_graph(coach, self.get_date(), self.tz_offset(), student_list)

class ClassEnergyPointsPerMinuteGraph(ClassProfileGraph):
    GRAPH_TYPE = "classenergypointsperminute"
    def graph_html_and_context(self, coach):
        student_list = self.get_student_list(coach)
        return templatetags.class_profile_energy_points_per_minute_graph(coach, student_list)

    def json_update(self, coach):
        student_list = self.get_student_list(coach)
        return templatetags.class_profile_energy_points_per_minute_update(coach, student_list)
