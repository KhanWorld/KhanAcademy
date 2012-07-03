from flask import current_app
import logging

def api_created_response(message):
    return current_app.response_class(message, status=201)

def api_invalid_param_response(message):
    return current_app.response_class(message, status=400)

def api_unauthorized_response(message):
    return current_app.response_class(message, status=401)

def api_error_response(e):
    logging.error("API error: %s" % e)
    return current_app.response_class("API error. %s" % e.message, status=500)
