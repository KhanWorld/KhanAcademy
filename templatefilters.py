import re
import os
import datetime
import math
import logging

import util
from app import App

def timesince_ago(content):
    if not content:
        return ""
    return append_ago(seconds_to_time_string(util.seconds_since(content)))

def seconds_to_time_string(seconds_init, short_display = True):

    seconds = seconds_init

    years = math.floor(seconds / (86400 * 365))
    seconds -= years * (86400 * 365)

    days = math.floor(seconds / 86400)
    seconds -= days * 86400

    months = math.floor(days / 30.5)
    weeks = math.floor(days / 7)

    hours = math.floor(seconds / 3600)
    seconds -= hours * 3600

    minutes = math.floor(seconds / 60)
    seconds -= minutes * 60

    if years:
        return "%d year%s" % (years, pluralize(years))
    elif months:
        return "%d month%s" % (months, pluralize(months))
    elif weeks:
        return "%d week%s" % (weeks, pluralize(weeks))
    elif days and hours and not short_display:
        return "%d day%s and %d hour%s" % (days, pluralize(days), hours, pluralize(hours))
    elif days:
        return "%d day%s" % (days, pluralize(days))
    elif hours:
        if minutes and not short_display:
            return "%d hour%s and %d minute%s" % (hours, pluralize(hours), minutes, pluralize(minutes))
        else:
            return "%d hour%s" % (hours, pluralize(hours))
    else:
        if seconds and not minutes:
            return "%d second%s" % (seconds, pluralize(seconds))
        return "%d minute%s" % (minutes, pluralize(minutes))

def youtube_timestamp_links(content):
    dict_replaced = {}
    html_template = "<span class='youTube' seconds='%s'>%s</span>"

    for match in re.finditer("(\d+:\d{2})", content):
        time = match.group(0)

        if not dict_replaced.has_key(time):
            rg_time = time.split(":")
            minutes = int(rg_time[0])
            seconds = int(rg_time[1])
            html_link = youtube_jump_link(time, (minutes * 60) + seconds)
            content = content.replace(time, html_link)
            dict_replaced[time] = True

    return content

def youtube_jump_link(content, seconds):
    return "<span class='youTube' seconds='%s'>%s</span>" % (seconds, content)

def phantom_login_link(login_notifications, continue_url):
    return login_notifications.replace("[login]", "<a href='/login?continue="+continue_url+"' class='simple-button action-gradient green'>Log in to save your progress</a>")

def append_ago(s_time):
    if not s_time:
        return ""
    return re.sub("^0 minutes ago", "just now", s_time + " ago")

def in_list(content, list):
    return content in list

def find_column_index(content, column_index_list):
    for index, column_breakpoint in enumerate(column_index_list):
        if (content < column_breakpoint):
            return index
    return len(column_index_list)

def column_height(list_item_index, column_breakpoints):
    height = list_item_index
    if not column_breakpoints.index(list_item_index) == 0:
        height = list_item_index - column_breakpoints[column_breakpoints.index(list_item_index) - 1]
    return height

def slugify(value):
    # Just like Django's version of slugify
    "Converts to lowercase, removes non-alpha chars and converts spaces to hyphens"
    value = re.sub('[^\w\s-]', '', value).strip().lower()
    return re.sub('[-\s]+', '-', value)

def mygetattr(obj, name):
    return getattr(obj, name)

_base_js_escapes = (
    ('\\', r'\u005C'),
    ('\'', r'\u0027'),
    ('"', r'\u0022'),
    ('>', r'\u003E'),
    ('<', r'\u003C'),
    ('&', r'\u0026'),
    ('=', r'\u003D'),
    ('-', r'\u002D'),
    (';', r'\u003B'),
    (u'\u2028', r'\u2028'),
    (u'\u2029', r'\u2029')
)

# Escape every ASCII character with a value less than 32.
_js_escapes = (_base_js_escapes +
               tuple([('%c' % z, '\\u%04X' % z) for z in range(32)]))

# escapejs from Django: https://www.djangoproject.com/
def escapejs(value):
    """Hex encodes characters for use in JavaScript strings."""
    if not isinstance(value, basestring):
        value = str(value)

    for bad, good in _js_escapes:
        value = value.replace(bad, good)

    return value

def static_url(relative_url):
    if App.is_dev_server or not os.environ['HTTP_HOST'].lower().endswith(".khanacademy.org"):
        return relative_url
    else:
        return "http://khan-academy.appspot.com%s" % relative_url

def linebreaksbr(s):
    return unicode(s).replace('\n', '<br />')

def linebreaksbr_ellipsis(content, ellipsis_content = "&hellip;"):

    # After a specified number of linebreaks, apply span with a CSS class
    # to the rest of the content so it can be optionally hidden or shown
    # based on its context.
    max_linebreaks = 4

    # We use our specific "linebreaksbr" filter, so we don't
    # need to worry about alternate representations of the <br /> tag.
    content = linebreaksbr(content.strip())

    rg_s = re.split("<br />", content)
    if len(rg_s) > (max_linebreaks + 1):
        # More than max_linebreaks <br />'s were found.
        # Place everything after the 3rd <br /> in a hidden span that can be exposed by CSS later, and
        # Append an ellipsis at the cutoff point with a class that can also be controlled by CSS.
        rg_s[max_linebreaks] = "<span class='ellipsisExpand'>%s</span><span class='hiddenExpand'>%s" % (ellipsis_content, rg_s[max_linebreaks])
        rg_s[-1] += "</span>"

    # Join the string back up w/ its original <br />'s
    return "<br />".join(rg_s)

def pluralize(i):
    return "" if i == 1 else "s"
