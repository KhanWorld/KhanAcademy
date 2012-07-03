import logging

from wsgiref.handlers import CGIHandler

import request_cache
from app import App
from gae_mini_profiler import profiler
from gae_bingo import middleware

# While not referenced directly, these imports have necessary side-effects.
# (e.g. Paths are mapped to the API request handlers with the "route" wrapper)
from api import api_app
from api import api_request_class #@UnusedImport
from api import auth #@UnusedImport
from api import v0 #@UnusedImport
from api import v1 #@UnusedImport

def real_main():

    wsgi_app = request_cache.RequestCacheMiddleware(api_app)
    wsgi_app = profiler.ProfilerWSGIMiddleware(wsgi_app)
    wsgi_app = middleware.GAEBingoWSGIMiddleware(wsgi_app)

    if App.is_dev_server:
        try:
            # Run debugged app
            from werkzeug_debugger_appengine import get_debugged_app
            api_app.debug = True
            debugged_app = get_debugged_app(wsgi_app)
            CGIHandler().run(debugged_app)
            return
        except Exception, e:
            api_app.debug = False
            logging.warning("Error running debugging version of werkzeug app, running production version: %s" % e)

    # Run production app
    from google.appengine.ext.webapp.util import run_wsgi_app
    run_wsgi_app(wsgi_app)

def profile_main():
    # This is the main function for profiling
    # We've renamed our original main() above to real_main()
    import cProfile, pstats
    prof = cProfile.Profile()
    prof = prof.runctx("real_main()", globals(), locals())
    print "<pre>"
    stats = pstats.Stats(prof)
    stats.sort_stats("cumulative")  # time or cumulative
    stats.print_stats(80)  # 80 = how many to print
    # The rest is optional.
    # stats.print_callees()
    stats.print_callers()
    print "</pre>"
    
main = real_main
# Uncomment the following line to enable profiling 
# main = profile_main

# Use App Engine app caching
if __name__ == "__main__":
    main()

