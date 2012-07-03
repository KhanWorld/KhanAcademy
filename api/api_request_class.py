from flask import Request

from request_handler import RequestInputHandler
from api import api_app

class ApiRequest(Request, RequestInputHandler):

    # Patch up a flask request object to behave a little more like webapp.RequestHandler
    # for the sake of our 3rd party oauth_provider library
    
    # Make arguments behave like webapp.arguments
    def arguments(self):
        return [val for val in self.values]

    # Make get behave like webapp.get
    def get(self, key, default_value=None):
        v = self.values.get(key)
        if v == None:
            return default_value
        return v

    # Make request_string behave like request_handler.RequestHandler.request_string
    # so the rest of RequestInputHandler inherits properly.
    def request_string(self, key, default=''):
        return self.get(key, default_value=default)

api_app.request_class = ApiRequest
