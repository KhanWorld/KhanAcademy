# -*- coding: utf-8 -*-
import os
import shutil
import sys
import commands

def append_paths():

    os.environ["SERVER_SOFTWARE"] = ""
    os.environ["CURRENT_VERSION_ID"] = ""

    # Can only deploy on unix-based systems for now
    dev_appserver_path = os.path.realpath( commands.getoutput("which dev_appserver.py") )

    gae_path = None
    if dev_appserver_path:
        gae_path = os.path.dirname(dev_appserver_path)
        
    if not gae_path:
        # Default to Mac's default location
        gae_path = "/Applications/GoogleAppEngineLauncher.app/Contents/Resources/GoogleAppEngine-default.bundle/Contents/Resources/google_appengine"

    extra_paths = [
        os.path.abspath("."),
        gae_path,
        # These paths are required by the SDK.
        os.path.join(gae_path, 'lib', 'antlr3'),
        os.path.join(gae_path, 'lib', 'ipaddr'),
        os.path.join(gae_path, 'lib', 'webob'),
        os.path.join(gae_path, 'lib', 'simplejson'),
        os.path.join(gae_path, 'lib', 'yaml', 'lib'),
    ]

    for path in extra_paths:
        sys.path.append(path)

# Append app and GAE paths so we can simulate our app environment
# when precompiling templates (otherwise compilation will bail on errors)
#
append_paths()

# Pull in some jinja magic
from jinja2 import FileSystemLoader
import webapp2
from webapp2_extras import jinja2

# Using our app's standard jinja config so we pick up custom globals and filters
import config_jinja

def compile_templates():

    src_path = os.path.join(os.path.dirname(__file__), "..", "templates")
    dest_path = os.path.join(os.path.dirname(__file__), "..", "compiled_templates.zip")

    jinja2.default_config["environment_args"]["loader"] = FileSystemLoader(src_path)

    env = jinja2.get_jinja2(app=webapp2.WSGIApplication()).environment

    try:
        shutil.rmtree(dest_path)
    except:
        pass

    # Compile templates to zip, crashing on any compilation errors
    env.compile_templates(dest_path, extensions=["html", "json", "xml"], 
            ignore_errors=False, py_compile=False, zip='deflated')

if __name__ == "__main__":
    compile_templates()
