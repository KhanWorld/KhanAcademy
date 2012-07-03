from __future__ import with_statement
import os

from google.appengine.ext.webapp import RequestHandler

from gandalf.config import can_control_gandalf

class Dashboard(RequestHandler):

    def get(self):
        if not can_control_gandalf():
            self.redirect("/")
            return

        path = os.path.join(os.path.dirname(__file__), "templates/base.html")

        with open(path) as f:
            html = f.read()

        self.response.out.write(html)
