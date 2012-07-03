import logging

import request_handler
import library

class Content(request_handler.RequestHandler):

    def get(self):

        self.render_jinja2_template(self.request.path[1:], {})

class LinkerHelpmee(request_handler.RequestHandler):

    def get(self):

        self.render_jinja2_template('nl-content/contribute.html', {})
