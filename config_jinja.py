# Jinja2 config

from urllib import quote_plus
import simplejson as json
import os

from webapp2_extras import jinja2

# We configure django's version here just to make sure
# we've got it specified in case a 3rd-party library wants to use it.
# (gae_mini_profiler and gae_bingo currently use it)
from google.appengine.dist import use_library
use_library('django', '0.96')

# Bring in our globally available custom templates and tags.
# When possible, we now use jinja macros instead of these global tags.
from models import UserData
import templatetags
import templatefilters
import badges.templatetags
import profiles.templatetags
import social.templatetags
import phantom_users.templatetags
import js_css_packages.templatetags
import gae_mini_profiler.templatetags
import api.auth.xsrf
import util
from app import App

jinja2.default_config = {
    "template_path": os.path.join(os.path.dirname(__file__), "templates"),
    "compiled_path": os.path.join(os.path.dirname(__file__), "compiled_templates.zip"),
    "force_compiled": not App.is_dev_server, # Only use compiled templates in production 
    "cache_size": 0 if App.is_dev_server else -1, # Only cache in production
    "auto_reload": App.is_dev_server, # Don't check for template updates in production
    "globals": {
        "templatetags": templatetags,
        "social": social.templatetags,
        "profiles": profiles.templatetags,
        "badges": badges.templatetags,
        "phantom_users": phantom_users.templatetags,
        "js_css_packages": js_css_packages.templatetags,
        "gae_mini_profiler": gae_mini_profiler.templatetags,
        "xsrf": api.auth.xsrf,
        "UserData": UserData,
        "json": json,
        "App": App,
    }, 
    "filters": {
        "urlencode": lambda s: quote_plus(s or ""),
        "escapejs": templatefilters.escapejs,
        "phantom_login_link": templatefilters.phantom_login_link,
        "slugify": templatefilters.slugify,
        "pluralize": templatefilters.pluralize,
        "linebreaksbr": templatefilters.linebreaksbr,
        "linebreaksbr_ellipsis": templatefilters.linebreaksbr_ellipsis,
        "youtube_timestamp_links": templatefilters.youtube_timestamp_links,
        "timesince_ago": templatefilters.timesince_ago,
        "seconds_to_time_string": templatefilters.seconds_to_time_string,
        "mygetattr": templatefilters.mygetattr,
        "find_column_index": templatefilters.find_column_index,
        "in_list": templatefilters.in_list,
        "column_height": templatefilters.column_height,
        "thousands_separated": util.thousands_separated_number,
        "static_url": util.static_url,
        "login_url": util.create_login_url,
    }, 
    "environment_args": {
        "autoescape": False, 
        "extensions": [],
        }, 
    }

