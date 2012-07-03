import os
import logging
import datetime
import urllib
import simplejson
import sys
import re
import traceback

from google.appengine.api import users
from google.appengine.runtime.apiproxy_errors import CapabilityDisabledError

import webapp2
import shared_jinja

from custom_exceptions import MissingVideoException, MissingExerciseException, SmartHistoryLoadException
from app import App
import cookie_util

from api.jsonify import jsonify

class RequestInputHandler(object):

    def request_string(self, key, default = ''):
        return self.request.get(key, default_value=default)

    def request_int(self, key, default = None):
        try:
            return int(self.request_string(key))
        except ValueError:
            if default is not None:
                return default
            else:
                raise # No value available and no default supplied, raise error

    def request_date(self, key, format_string, default = None):
        try:
            return datetime.datetime.strptime(self.request_string(key), format_string)
        except ValueError:
            if default is not None:
                return default
            else:
                raise # No value available and no default supplied, raise error

    def request_date_iso(self, key, default = None):
        s_date = self.request_string(key)

        # Pull out milliseconds b/c Python 2.5 doesn't play nicely w/ milliseconds in date format strings
        if "." in s_date:
            s_date = s_date[:s_date.find(".")]

        # Try to parse date in our approved ISO 8601 format
        try:
            return datetime.datetime.strptime(s_date, "%Y-%m-%dT%H:%M:%SZ")
        except ValueError:
            if default is not None:
                return default
            else:
                raise # No value available and no default supplied, raise error

    def request_user_data(self, key):
        email = self.request_string(key)
        return UserData.get_possibly_current_user(email)

    # get the UserData instance based on the querystring. The precedence is:
    # 1. email
    # 2. student_email
    # the precendence is reversed when legacy is True. A warning will be logged
    # if a legacy parameter is encountered when not expected.
    def request_student_user_data(self, legacy=False):
        if legacy:
            email = self.request_student_email_legacy()
        else:
            email = self.request_student_email()
        return UserData.get_possibly_current_user(email)

    def request_student_email_legacy(self):
        email = self.request_string("email")
        email = self.request_string("student_email", email)
        # no warning is logged here as we should aim to completely move to
        # email, but no effort has been made to update old calls yet.
        return email

    def request_student_email(self):
        email = self.request_string("student_email")
        if email:
            logging.warning("API called with legacy student_email parameter")
        email = self.request_string("email", email)
        return email

    def request_float(self, key, default = None):
        try:
            return float(self.request_string(key))
        except ValueError:
            if default is not None:
                return default
            else:
                raise # No value available and no default supplied, raise error

    def request_bool(self, key, default = None):
        if default is None:
            return self.request_int(key) == 1
        else:
            return self.request_int(key, 1 if default else 0) == 1

class RequestHandler(webapp2.RequestHandler, RequestInputHandler):

    def is_ajax_request(self):
        # jQuery sets X-Requested-With header for this detection.
        if self.request.headers.has_key("x-requested-with"):
            s_requested_with = self.request.headers["x-requested-with"]
            if s_requested_with and s_requested_with.lower() == "xmlhttprequest":
                return True
        return self.request_bool("is_ajax_override", default=False)

    def request_url_with_additional_query_params(self, params):
        url = self.request.url
        if url.find("?") > -1:
            url += "&"
        else:
            url += "?"
        return url + params

    def handle_exception(self, e, *args):

        silence_report = False

        title = "Oops. We broke our streak."
        message_html = "We ran into a problem. It's our fault, and we're working on it."
        sub_message_html = "This has been reported to us, and we'll be looking for a fix. If the problem continues, feel free to <a href='/reportissue?type=Defect'>send us a report directly</a>."

        if type(e) is CapabilityDisabledError:

            # App Engine maintenance period
            title = "Shhh. We're studying."
            message_html = "We're temporarily down for maintenance, and we expect this to last approximately one hour. In the meantime, you can watch all of our videos at the <a href='http://www.youtube.com/user/khanacademy'>Khan Academy YouTube channel</a>."
            sub_message_html = "We're really sorry for the inconvenience, and we're working to restore access as soon as possible."

        elif type(e) is MissingExerciseException:

            title = "This exercise isn't here right now."
            message_html = "Either this exercise doesn't exist or it's temporarily hiding. You should <a href='/exercisedashboard'>head back to our other exercises</a>."
            sub_message_html = "If this problem continues and you think something is wrong, please <a href='/reportissue?type=Defect'>let us know by sending a report</a>."

        elif type(e) is MissingVideoException:

            # We don't log missing videos as errors because they're so common due to malformed URLs or renamed videos.
            # Ask users to report any significant problems, and log as info in case we need to research.
            silence_report = True
            logging.info(e)
            title = "This video is no longer around."
            message_html = "You're looking for a video that either never existed or wandered away. <a href='/'>Head to our video library</a> to find it."
            sub_message_html = "If this problem continues and you think something is wrong, please <a href='/reportissue?type=Defect'>let us know by sending a report</a>."

        elif type(e) is SmartHistoryLoadException:
            # 404s are very common with Smarthistory as bots have gotten hold of bad urls, silencing these reports and log as info instead
            silence_report = True
            logging.info(e)
            title = "This page of the Smarthistory section of Khan Academy does not exist"
            message_html = "Go to <a href='/'>our Smarthistory homepage</a> to find more art history content."
            sub_message_html = "If this problem continues and you think something is wrong, please <a href='/reportissue?type=Defect'>let us know by sending a report</a>."

        if not silence_report:
            self.error(500)
            logging.exception(e)

        # Show a nice stack trace on development machines, but not in production
        if App.is_dev_server or users.is_current_user_admin():
            try:
                import google

                exc_type, exc_value, exc_traceback = sys.exc_info()

                # Grab module and convert "__main__" to just "main"
                class_name = '%s.%s' % (re.sub(r'^__|__$', '', self.__class__.__module__), type(self).__name__)

                http_method = self.request.method
                title = '%s in %s.%s' % ((exc_value.exc_info[0] if hasattr(exc_value, 'exc_info') else exc_type).__name__, class_name, http_method.lower())

                message = str(exc_value.exc_info[1]) if hasattr(exc_value, 'exc_info') else str(exc_value)

                sdk_root = os.path.normpath(os.path.join(os.path.dirname(google.__file__), '..'))
                sdk_version = os.environ['SDK_VERSION'] if os.environ.has_key('SDK_VERSION') else os.environ['SERVER_SOFTWARE'].split('/')[-1]
                app_root = App.root
                r_sdk_root = re.compile(r'^%s/' % re.escape(sdk_root))
                r_app_root = re.compile(r'^%s/' % re.escape(app_root))

                (template_filename, template_line, extracted_source) = (None, None, None)
                if hasattr(exc_value, 'source'):
                    origin, (start, end) = exc_value.source
                    template_filename = str(origin)

                    f = open(template_filename)
                    template_contents = f.read()
                    f.close()

                    template_lines = template_contents.split('\n')
                    template_line = 1 + template_contents[:start].count('\n')
                    template_end_line = 1 + template_contents[:end].count('\n')

                    ctx_start = max(1, template_line - 3)
                    ctx_end = min(len(template_lines), template_end_line + 3)

                    extracted_source = '\n'.join('%s: %s' % (num, template_lines[num - 1]) for num in range(ctx_start, ctx_end + 1))

                def format_frame(frame):
                    filename, line, function, text = frame
                    filename = r_sdk_root.sub('google_appengine (%s) ' % sdk_version, filename)
                    filename = r_app_root.sub('', filename)
                    return "%s:%s:in `%s'" % (filename, line, function)

                extracted = traceback.extract_tb(exc_traceback)
                if hasattr(exc_value, 'exc_info'):
                    extracted += traceback.extract_tb(exc_value.exc_info[2])

                application_frames = reversed([frame for frame in extracted if r_app_root.match(frame[0])])
                framework_frames = reversed([frame for frame in extracted if not r_app_root.match(frame[0])])
                full_frames = reversed([frame for frame in extracted])

                application_trace = '\n'.join(format_frame(frame) for frame in application_frames)
                framework_trace = '\n'.join(format_frame(frame) for frame in framework_frames)
                full_trace = '\n'.join(format_frame(frame) for frame in full_frames)

                param_keys = self.request.arguments()
                params = ',\n    '.join('%s: %s' % (repr(k.encode('utf8')), repr(self.request.get(k).encode('utf8'))) for k in param_keys)
                params_dump = '{\n    %s\n}' % params if len(param_keys) else '{}'

                environ = self.request.environ
                env_dump = '\n'.join('%s: %s' % (k, environ[k]) for k in sorted(environ))

                self.response.clear()
                self.render_jinja2_template('viewtraceback.html', { "title": title, "message": message, "template_filename": template_filename, "template_line": template_line, "extracted_source": extracted_source, "app_root": app_root, "application_trace": application_trace, "framework_trace": framework_trace, "full_trace": full_trace, "params_dump": params_dump, "env_dump": env_dump })
            except:
                # We messed something up showing the backtrace nicely; just show it normally
                pass
        else:
            self.response.clear()
            self.render_jinja2_template('viewerror.html', { "title": title, "message_html": message_html, "sub_message_html": sub_message_html })

    @classmethod
    def exceptions_to_http(klass, status):
        def decorator(fn):
            def wrapper(self, *args, **kwargs):
                try:
                    fn(self, *args, **kwargs);
                except Exception, e:
                    self.response.clear()
                    self.response.set_status(status)
            return wrapper
        return decorator

    def user_agent(self):
        return str(self.request.headers['User-Agent'])

    def is_mobile_capable(self):
        user_agent_lower = self.user_agent().lower()
        return user_agent_lower.find("ipod") > -1 or \
                user_agent_lower.find("ipad") > -1 or \
                user_agent_lower.find("iphone") > -1 or \
                user_agent_lower.find("webos") > -1 or \
                user_agent_lower.find("android") > -1

    def is_older_ie(self):
        user_agent_lower = self.user_agent().lower()
        return user_agent_lower.find("msie 7.") > -1 or \
                user_agent_lower.find("msie 6.") > -1

    def is_webos(self):
        user_agent_lower = self.user_agent().lower()
        return user_agent_lower.find("webos") > -1 or \
                user_agent_lower.find("hp-tablet") > -1

    def is_mobile(self):
        if self.is_mobile_capable():
            return not self.has_mobile_full_site_cookie()
        return False

    def has_mobile_full_site_cookie(self):
        return self.get_cookie_value("mobile_full_site") == "1"

    def set_mobile_full_site_cookie(self, is_mobile):
        self.set_cookie("mobile_full_site", "1" if is_mobile else "0")

    @staticmethod
    def get_cookie_value(key):
        return cookie_util.get_cookie_value(key)

    # Cookie handling from http://appengine-cookbook.appspot.com/recipe/a-simple-cookie-class/
    def set_cookie(self, key, value='', max_age=None,
                   path='/', domain=None, secure=None, httponly=False,
                   version=None, comment=None):

        # We manually add the header here so we can support httponly cookies in Python 2.5,
        # which self.response.set_cookie does not.
        header_value = cookie_util.set_cookie_value(key, value, max_age, path, domain, secure, httponly, version, comment)
        self.response.headerlist.append(('Set-Cookie', header_value))

    def delete_cookie(self, key, path='/', domain=None):
        self.set_cookie(key, '', path=path, domain=domain, max_age=0)

    def add_global_template_values(self, template_values):
        template_values['App'] = App
        template_values['None'] = None

        if not template_values.has_key('user_data'):
            user_data = UserData.current()
            template_values['user_data'] = user_data

        user_data = template_values['user_data']

        template_values['username'] = user_data.nickname if user_data else ""
        template_values['points'] = user_data.points if user_data else 0
        template_values['logged_in'] = not user_data.is_phantom if user_data else False

        # Always insert a post-login request before our continue url
        template_values['continue'] = util.create_post_login_url(template_values.get('continue') or self.request.uri)
        template_values['login_url'] = ('%s&direct=1' % util.create_login_url(template_values['continue']))
        template_values['logout_url'] = util.create_logout_url(self.request.uri)

        template_values['is_mobile'] = False
        template_values['is_mobile_capable'] = False

        if self.is_mobile_capable():
            template_values['is_mobile_capable'] = True
            if 'is_mobile_allowed' in template_values and template_values['is_mobile_allowed']:
                template_values['is_mobile'] = self.is_mobile()

        # overridable hide_analytics querystring that defaults to true in dev
        # mode but false for prod.
        hide_analytics = self.request_bool("hide_analytics", App.is_dev_server)
        template_values['hide_analytics'] = hide_analytics

        if user_data:
            goals = GoalList.get_current_goals(user_data)
            goals_data = [g.get_visible_data() for g in goals]
            if goals_data:
                template_values['global_goals'] = jsonify(goals_data)

        return template_values

    def render_jinja2_template(self, template_name, template_values):
        self.add_global_template_values(template_values)
        self.response.write(self.render_jinja2_template_to_string(template_name, template_values))

    def render_jinja2_template_to_string(self, template_name, template_values):
        return shared_jinja.get().render_template(template_name, **template_values)

    def render_json(self, obj):
        json = simplejson.dumps(obj, ensure_ascii=False)
        self.response.out.write(json)

    def render_jsonp(self, obj):
        json = obj if isinstance(obj, basestring) else simplejson.dumps(obj, ensure_ascii=False, indent=4)
        callback = self.request_string("callback")
        if callback:
            self.response.out.write("%s(%s)" % (callback, json))
        else:
            self.response.out.write(json)

from models import UserData
import util
from goals.models import GoalList
