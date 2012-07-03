import logging
import simplejson
import os

from google.appengine.ext import webapp

from gae_mini_profiler import profiler

register = webapp.template.create_template_register()

@register.simple_tag
def profiler_includes_request_id(request_id, show_immediately = False):
    if not request_id:
        return ""

    js_path = "/gae_mini_profiler/static/js/profiler.js"
    css_path = "/gae_mini_profiler/static/css/profiler.css"

    return """
<link rel="stylesheet" type="text/css" href="%s" />
<script type="text/javascript" src="%s"></script>
<script type="text/javascript">GaeMiniProfiler.init("%s", %s)</script>
    """ % (css_path, js_path, request_id, simplejson.dumps(show_immediately))

@register.simple_tag
def profiler_includes():
    return profiler_includes_request_id(profiler.request_id)


