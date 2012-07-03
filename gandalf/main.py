from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app

from gandalf import dashboard, api, middleware

application = webapp.WSGIApplication([
    ("/gandalf", dashboard.Dashboard),
    ("/gandalf/api/v1/bridges", api.Bridges),
    ("/gandalf/api/v1/bridges/filters", api.Filters),
    ("/gandalf/api/v1/bridges/update", api.UpdateBridge),
    ("/gandalf/api/v1/bridges/filters/update", api.UpdateFilter),
])
application = middleware.GandalfWSGIMiddleware(application)

def main():
    run_wsgi_app(application)

if __name__ == "__main__":
    main()
