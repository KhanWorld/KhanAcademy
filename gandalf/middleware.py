from gandalf.cache import flush_request_cache

class GandalfWSGIMiddleware(object):

    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):

        # Make sure request-cached values are cleared at start of request
        flush_request_cache()

        result = self.app(environ, start_response)
        for value in result:
            yield value
