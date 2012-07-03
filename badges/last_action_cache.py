from google.appengine.api import memcache
from google.appengine.ext import db
from google.appengine.datastore import entity_pb

# LastActionCache stores a highly compressed cache of the most recent actions
# each individual user has taken. The data is stored in memcache only at the moment
# for performance reasons. If reliability becomes an issue we can consider persisting this data
# in the datastore in a background thread.
#
# LastActionCache is used to quickly assess badge completion based on each users' recent actions.
#
# LastActionCache explicitly stores only the protobuf versions of each cached action for extremely
# fast serialization and deserialization of the action cache to and from memcache on every action request.
# We only take the time to turn each protobuf instance into a real DB model on demand (when needed for badge assessment).

class LastActionCache:

    CACHED_ACTIONS_PER_TYPE = 500
    VERSION = 2

    @staticmethod
    def key_for_email(email):
        return "last_action_cache_%s_%s" % (LastActionCache.VERSION, email)

    @staticmethod
    def get_for_user_data(user_data):
        action_cache = memcache.get(LastActionCache.key_for_email(user_data.key_email))
        if action_cache is None:
            action_cache = LastActionCache(user_data)
        return action_cache

    def __init__(self, user_data):
        self.problem_logs = [] # Protobuf version of problem logs for extremely fast (de)serialization
        self.problem_log_models = {} # Deserialized problem log models

        self.video_logs = [] # Protobuf version of video logs for extremely fast (de)serialization
        self.video_log_models = {} # Deserialized video log models

        self.key_email = user_data.key_email

    # Push a new problem log to the cache and return the LastActionCache
    @staticmethod
    def get_cache_and_push_problem_log(user_data, problem_log):
        action_cache = LastActionCache.get_for_user_data(user_data)
        action_cache.push_problem_log(problem_log)
        return action_cache

    # Push a new problem log using protobuf for fast serialization/pickle
    def push_problem_log(self, problem_log):
        self.problem_logs.append(db.model_to_protobuf(problem_log).Encode())
        if len(self.problem_logs) > LastActionCache.CACHED_ACTIONS_PER_TYPE:
            self.problem_logs = self.problem_logs[-1 * LastActionCache.CACHED_ACTIONS_PER_TYPE:]

        self.store()

    # Get a new problem log from the cache via protobuf deserialization
    def get_problem_log(self, ix):
        if not self.problem_log_models.has_key(ix):
            self.problem_log_models[ix] = db.model_from_protobuf(entity_pb.EntityProto(self.problem_logs[ix]))
        return self.problem_log_models[ix]

    # Push a new video log to the cache and return the LastActionCache
    @staticmethod
    def get_cache_and_push_video_log(user_data, video_log):
        action_cache = LastActionCache.get_for_user_data(user_data)
        action_cache.push_video_log(video_log)
        return action_cache

    # Push a new video log to the cache using protobuf for fast serialization/pickle
    def push_video_log(self, video_log):
        self.video_logs.append(db.model_to_protobuf(video_log).Encode())
        if len(self.video_logs) > LastActionCache.CACHED_ACTIONS_PER_TYPE:
            self.video_logs = self.video_logs[-1 * LastActionCache.CACHED_ACTIONS_PER_TYPE:]

        self.store()

    # Get a new video log from the cache via protobuf deserialization
    def get_video_log(self, ix):
        if not self.video_log_models.has_key(ix):
            self.video_log_models[ix] = db.model_from_protobuf(entity_pb.EntityProto(self.video_logs[ix]))
        return self.video_log_models[ix]

    def get_last_video_log(self):
        c = len(self.video_logs)
        if c <= 0:
            return None
        return self.get_video_log(c - 1)

    def store(self):
        # Wipe out deserialized models before serialization for speed
        self.problem_log_models = {}
        self.video_log_models = {}

        memcache.set(LastActionCache.key_for_email(self.key_email), self)

