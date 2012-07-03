from google.appengine.api import users

from models import UserData
from api.decorators import pickle, unpickle, compress, decompress, base64_encode, base64_decode
import request_cache
import layer_cache
import models_discussion

@request_cache.cache()
def is_current_user_moderator():
    return users.is_current_user_admin() or (UserData.current() and UserData.current().moderator)

def is_honeypot_empty(request):
    return not request.get("honey_input") and not request.get("honey_textarea")

def feedback_query(target_key):
    query = models_discussion.Feedback.all()
    query.filter("targets =", target_key)
    query.filter("deleted =", False)
    query.filter("is_hidden_by_flags =", False)
    query.order('-date')
    return query

@request_cache.cache_with_key_fxn(models_discussion.Feedback.memcache_key_for_video)
@unpickle
@base64_decode
@decompress
@layer_cache.cache_with_key_fxn(models_discussion.Feedback.memcache_key_for_video, layer=layer_cache.Layers.Memcache)
@compress
@base64_encode
@pickle
def get_feedback_for_video(video):
    return feedback_query(video.key()).fetch(500)

@request_cache.cache_with_key_fxn(lambda v, ud: str(v) + str(ud))
def get_feedback_for_video_by_user(video_key, user_data_key):
    query = models_discussion.Feedback.all()
    query.ancestor(user_data_key)
    query.filter("targets =", video_key)
    query.order('-date')
    return feedback_query(video_key).fetch(20)

def get_feedback_by_type_for_video(video, feedback_type, user_data=None):
    feedback = [f for f in get_feedback_for_video(video) if feedback_type in f.types]
    feedback_dict = dict([(f.key(), f) for f in feedback])

    user_feedback = []
    if user_data:
        user_feedback = get_feedback_for_video_by_user(video.key(), user_data.key())
    user_feedback_dict = dict([(f.key(), f) for f in user_feedback if feedback_type in f.types])

    feedback_dict.update(user_feedback_dict)
    # It's possible that an entity was deleted or flagged by the user.
    # They'll still be in the main query, but remove the ones by the user here.
    feedback = feedback_dict.values()
    feedback = filter(lambda f: not (f.deleted or f.is_hidden_by_flags), feedback)

    return sorted(feedback, key=lambda s: s.date, reverse=True)
