import os

from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.ext.webapp import WSGIApplication, template, RequestHandler

class RedirectGTV(RequestHandler):
    def get(self):
        self.redirect("/gtv/")

class ViewGTV(RequestHandler):
    def get(self):
        path = os.path.join(os.path.dirname(__file__), "index.html")
        self.response.out.write(template.render(path, {}))

application = WSGIApplication([
    ('/gtv/', ViewGTV),
    ('/gtv', RedirectGTV),
])

def main():
    run_wsgi_app(application)

if __name__ == "__main__":
    main()

