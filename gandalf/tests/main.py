from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app

from gandalf.tests import RunStep
from gandalf import middleware

application = webapp.WSGIApplication([
    ("/gandalf/tests/run_step", RunStep),
])
application = middleware.GandalfWSGIMiddleware(application)

def main():
    run_wsgi_app(application)

if __name__ == "__main__":
    main()
