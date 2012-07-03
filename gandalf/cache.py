from google.appengine.ext import db
from google.appengine.datastore import entity_pb
from google.appengine.api import memcache

from gandalf.models import GandalfBridge, GandalfFilter

_request_cache = {}

def flush_request_cache():
    global _request_cache
    _request_cache = {}

def init_request_cache_from_memcache():
    if not _request_cache.get("loaded_from_memcache"):
        _request_cache[GandalfCache.MEMCACHE_KEY] = memcache.get(GandalfCache.MEMCACHE_KEY)
        _request_cache["loaded_from_memcache"] = True

class GandalfCache(object):

    MEMCACHE_KEY = "_gandalf_cache"

    def __init__(self):

        self.bridges = {} # Protobuf version of bridges for extremely fast (de)serialization
        self.bridge_models = {} # Deserialized bridge models

        self.filters = {} # Protobuf version of filters for extremely fast (de)serialization
        self.filter_models = {} # Deserialized filter models

    @staticmethod
    def get():
        init_request_cache_from_memcache()

        if not _request_cache.get(GandalfCache.MEMCACHE_KEY):
            _request_cache[GandalfCache.MEMCACHE_KEY] = GandalfCache.load_from_datastore()

        return _request_cache[GandalfCache.MEMCACHE_KEY]

    @staticmethod
    def load_from_datastore():
        gandalf_cache = GandalfCache()

        bridges = GandalfBridge.all()

        for bridge in bridges:

            key = bridge.key().name()

            gandalf_cache.bridges[key] = db.model_to_protobuf(bridge).Encode()

            filters = bridge.gandalffilter_set

            gandalf_cache.filters[key] = []

            for filter in filters:
                gandalf_cache.filters[key].append(db.model_to_protobuf(filter).Encode())

        memcache.set(GandalfCache.MEMCACHE_KEY, gandalf_cache)

        return gandalf_cache

    @staticmethod
    def delete_from_memcache():
        memcache.delete(GandalfCache.MEMCACHE_KEY)

    def get_bridge_model(self, bridge_name):
        if bridge_name in self.bridges:
            return self.bridge_models.setdefault(bridge_name,
                db.model_from_protobuf(entity_pb.EntityProto(self.bridges[bridge_name])))
        else:
            return None

    def get_filter_models(self, bridge_name):
        if bridge_name in self.filters:
            return self.filter_models.setdefault(bridge_name,
                [db.model_from_protobuf(entity_pb.EntityProto(filter)) for filter in self.filters[bridge_name]])
        else:
            return None
