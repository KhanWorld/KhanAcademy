import logging
from mapreduce import operation as op
import facebook_util
from google.appengine.ext import db

def check_user_properties(user_data):
    if not user_data or not user_data.user:
        return

    if not user_data.current_user:
        logging.critical("Missing current_user: %s" % user_data.user)

    if not user_data.user_id:
        logging.critical("Missing user_id: %s" % user_data.user)

    if not user_data.user_email:
        logging.critical("Missing user_email: %s" % user_data.user)

    if user_data.current_user.email() != user_data.user_email:
        logging.warning("current_user does not match user_email: %s" % user_data.user)

    if facebook_util.is_facebook_user_id(user_data.user_id) or facebook_util.is_facebook_user_id(user_data.user_email):
        if user_data.user_id != user_data.user_email:
            logging.critical("facebook user's user_id does not match user_email: %s" % user_data.user)

def remove_deleted_studentlists(studentlist):
    try:
        deleted = studentlist.deleted
        del studentlist.deleted
        if deleted:
            yield op.db.Delete(studentlist)
        else:
            yield op.db.Put(studentlist)
    except AttributeError:
        pass
        # do nothing, as this studentlist is fine.

def dedupe_related_videos(exercise):
    exvids = exercise.related_videos_query().fetch(100)
    video_keys = set()
    for exvid in exvids:
        video_key = exvid.video.key()
        if video_key in video_keys:
            logging.critical("Deleting ExerciseVideo for %s, %s",
                exercise.name,
                video_key.id_or_name())
            yield op.db.Delete(exvid)
        else:
            video_keys.add(video_key)

def migrate_userdata(key):
    def tn(key):
        user_data = db.get(key)
        # remove blank entries if present
        user_data.all_proficient_exercises.remove('')
        user_data.proficient_exercises.remove('')
        user_data.badges.remove('')
        user_data.put()
    db.run_in_transaction(tn, key)

def update_user_exercise_progress(user_exercise):
    # If a UserExercise object doesn't have the _progress property, it means
    # the user hasn't done a problem of that exercise since the accuracy model
    # rollout. This means that what they see on their dashboards and on the
    # exercise page is unchanged from the streak model. So, we can just
    # backfill with what their progress would be under the streak model.
    if user_exercise._progress is None:
        user_exercise._progress = user_exercise.get_progress_from_streak()
        yield op.db.Put(user_exercise)

def transactional_entity_put(entity_key):
    def entity_put(entity_key):
        entity = db.get(entity_key)
        entity.put()
    db.run_in_transaction(entity_put, entity_key)

def fix_has_current_goal(goal):
    '''Some user_data entities have inaccurate has_current_goal values due to
    non-atomic puts. Fix them up!'''

    if not goal.completed:
        user_data = goal.parent()
        if user_data and not user_data.has_current_goals:
            user_data.has_current_goals = True
            yield op.db.Put(user_data)
