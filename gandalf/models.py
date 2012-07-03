import datetime

from google.appengine.ext import db

from gandalf.object_property import UnvalidatedObjectProperty
from gandalf.filters import BridgeFilter

class GandalfBridge(db.Model):
    date_created = db.DateTimeProperty(auto_now_add=True, indexed=False)

    def put(self, **kwargs):
        super(GandalfBridge, self).put(**kwargs)
        from gandalf.cache import GandalfCache
        GandalfCache.delete_from_memcache()

    def delete(self, **kwargs):
        super(GandalfBridge, self).delete(**kwargs)
        from gandalf.cache import GandalfCache
        GandalfCache.delete_from_memcache()
    
    @property
    def status(self):
        days_running = (datetime.datetime.now() - self.date_created).days
        
        if days_running < 1:
            return "Running for less than a day"
        else:
            return "Running for %s day%s" % (days_running, ("" if days_running == 1 else "s"))


class GandalfFilter(db.Model):
    bridge = db.ReferenceProperty(GandalfBridge, required=True)
    filter_type = db.StringProperty(required=True, indexed=False)
    whitelist = db.BooleanProperty(default=True, indexed=False)
    percentage = db.IntegerProperty(default=100, indexed=False)
    context = UnvalidatedObjectProperty(indexed=False)

    def put(self, **kwargs):
        from gandalf.cache import GandalfCache
        super(GandalfFilter, self).put(**kwargs)
        GandalfCache.delete_from_memcache()

    def delete(self, **kwargs):
        super(GandalfFilter, self).delete(**kwargs)
        from gandalf.cache import GandalfCache
        GandalfCache.delete_from_memcache()

    @property
    def filter_class(self):
        return BridgeFilter.find_subclass(self.filter_type)

    @property
    def html(self):
        return self.filter_class.render()

    @property
    def proper_name(self):
        return self.filter_class.proper_name()
