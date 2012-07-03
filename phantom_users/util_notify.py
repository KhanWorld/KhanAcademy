import logging

from google.appengine.api import memcache

import util
import models
from notifications import UserNotifier
import phantom_util
import request_handler

def welcome(user_data):
    if user_data == None:
        return False
    UserNotifier.push_login_for_user_data(user_data,"Welcome to Khan Academy! To get the best experience you should [login]")
    
def update(user_data, user_exercise, threshold=False, isProf=False, gotBadge=False):
    if user_data == None:
        return False
        
    if not user_data.is_phantom:
        return False

    numquest = None
    numbadge = None
    numpoint = None

    if user_exercise != None:
        numquest = user_exercise.total_done
        prof = str(models.Exercise.to_display_name(user_exercise.exercise))


    numbadge = user_data.badges
    numpoint = user_data.points

    # First question
    if (numquest == 1):
        UserNotifier.push_login_for_user_data(user_data,"You've answered your first question! You should [login]")  
    # Every 10 questions, more than 20 every 5  
    if (numquest != None and numquest % 10 == 0) or \
       (numquest != None and numquest > 20 and numquest % 5 == 0):
        UserNotifier.push_login_for_user_data(user_data,"You've answered "+str(numquest)+" questions! You should [login]")
    #Proficiency
    if isProf:
        UserNotifier.push_login_for_user_data(user_data,"You're proficient in "+str(prof)+". You should [login]")
    #First Badge
    if numbadge != None and len(numbadge) == 1 and gotBadge:
        UserNotifier.push_login_for_user_data(user_data,"Congrats on your first <a href='/profile'>badge</a>! You should [login]")
    #Every badge after
    if numbadge != None and len(numbadge) > 1 and gotBadge:
        UserNotifier.push_login_for_user_data(user_data,"You've earned <a href='/profile'>"+str(len(numbadge))+" badges</a> so far. You should [login]")
    #Every 2.5k points
    if numpoint != None and threshold:
        numpoint = 2500*(numpoint/2500)+2500
        UserNotifier.push_login_for_user_data(user_data,"You've earned over <a href='/profile'>"+str(numpoint)+ " points</a>! You should [login]")


#Toggle Notify allows the user to close the notification bar (by deleting the memcache) until a new notification occurs. 
class ToggleNotify(request_handler.RequestHandler):
    def post(self):
        UserNotifier.clear_login()

