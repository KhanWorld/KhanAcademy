
from google.appengine.api import users

import util
import request_handler
from models import UserData

class SaveExpandedAllExercises(request_handler.RequestHandler):
    def post(self):
        user_data = UserData.current()

        if user_data:
            expanded = self.request_bool("expanded")

            user_data.expanded_all_exercises = expanded
            user_data.put() 

class SaveMapCoords(request_handler.RequestHandler):

    def get(self):
        return

    def post(self):
        user_data = UserData.current()

        if user_data:
            try:
                lat = self.request_float("lat")
                lng = self.request_float("lng")
                zoom = self.request_int("zoom")
            except ValueError:
                # If any of the above values aren't present in request, don't try to save.
                return

            user_data.map_coords = serializeMapCoords(lat, lng, zoom)
            user_data.put()
 
def serializeMapCoords(lat, lng, zoom):
    return "%s:%s:%s" % (lat, lng, zoom)

def deserializeMapCoords(s):

    if (not s):
        return (0, 0, 0)

    try:
        rg = s.split(":")
        lat = float(rg[0])
        lng = float(rg[1])
        zoom = int(rg[2])
    except ValueError:
        return (0, 0, 0)

    return (lat, lng, zoom)

