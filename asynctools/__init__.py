"""
datastore_v3'
CRUD
'Put'
'Get'
'Delete'

DatastoreQuery
'RunQUery'
'Count'
'Next'

Unplanned
'AllocatIds'
'BeginTransaction'
'Rollback'
'Commit'

capability_service
'IsEnabled'
"""



import logging
from google.appengine.api import apiproxy_stub_map
from google.appengine.api import memcache as memcache_builtin
from google.pyglib.gexcept import AbstractMethod
from google.appengine.api import urlfetch as urlfetch_builtin
from google.appengine.api.datastore import datastore_pb, Query, MultiQuery, Entity
from google.appengine.api.datastore import _MaybeSetupTransaction, NormalizeAndTypeCheck, NormalizeAndTypeCheckKeys
from google.appengine.api.datastore import datastore_errors
from google.appengine.api.datastore_types import Key

from google.appengine.api.api_base_pb import Integer64Proto
from google.appengine.ext import db

from asynctools import datastore


class RpcTask(object):

    def __init__(self, rpc, *args, **kwargs):
        self.__user_rpc=rpc
        self.__args = args
        self.__kwargs = kwargs
        self.__cache_result = None
        self.__client_state = kwargs.get('client_state')

    def __set_runner(self, runner):
        self.__user_rpc.runner = runner
    def __get_runner(self):
        return self.__user_rpc.runner
    runner = property(__get_runner, __set_runner)

    @property
    def client_state(self):
        return self.__client_state

    @property
    def rpc(self):
        return self.__user_rpc

    @property
    def cache_key(self):
        raise AbstractMethod

    def __get_cache_result(self):
        return self.__cache_result

    def __set_cache_result(self, result):
        self.__cache_result = result

    cache_result = property(__get_cache_result, __set_cache_result)

    def make_call(self):
        """ common call to dispatch rpc
            access args and kwargs to call services make_call with arguments
        """
        raise AbstractMethod

    def wait(self):
        self.rpc.wait()

    def get_result(self):
        if self.cache_result is not None:
            return self.cache_result
        else:
            return self.rpc.get_result()

    @property
    def args(self):
        return self.__args

    @property
    def kwargs(self):
        return self.__kwargs

    def __repr__(self):
        try:
            return "%s%s" % (type(self), self.cache_key)
        except Exception: # cache_key may raise exception for tasks that cannot be cached
            return "%s %s %s" % (type(self), repr(self.__args), repr(self.__kwargs))


class UrlFetchTask(RpcTask):

    def __init__(self, url, deadline=None, callback=None, urlfetch=None, **kw):
        assert url, "Url cannot be None or empty string"
        self._fetch_mechanism = urlfetch or urlfetch_builtin
        rpc = self._fetch_mechanism.create_rpc(deadline=deadline, callback=callback)
        super(UrlFetchTask, self).__init__(rpc, url, **kw)
        self.__url = url

    @property
    def url(self):
        return self.__url

    @property
    def cache_key(self):
        """ compute cache key
            Throws attributeError if make_call_args has not been called
        """
        return self.__url

    def make_call(self):
        self._fetch_mechanism.make_fetch_call(self.rpc, *self.args, **self.kwargs)


class DatastoreTask(RpcTask):

    def __init__(self,  deadline=None, callback=None, **kw):

        self._results = []
        self._exception = []

        rpc = datastore.create_rpc(deadline=deadline, callback=callback)
        rpc.callback = self.rpc_callback(rpc, self._results, self.exception, callback=callback)
        super(DatastoreTask, self).__init__(rpc, **kw)

    def get_result(self):
        raise AbstractMethod

    def rpc_callback(self, rpc, results, exceptions, callback):
        raise AbstractMethod

    def make_call(self):
        raise AbstractMethod

    @property
    def results(self):
        return self._results

    @property
    def exception(self):
        return self._exception


class DatastoreCrudTask(DatastoreTask):
    pass

class DatastorePutTask(DatastoreCrudTask):
    """Store one or more entities in the datastore.

    The entities may be new or previously existing. For new entities, Put() will
    fill in the app id and key assigned by the datastore.

    If the argument is a single Entity, a single Key will be returned. If the
    argument is a list of Entity, a list of Keys will be returned.

    Args:
      entities: Entity or list of Entities

    Returns:
      Key or list of Keys

    Raises:
      TransactionFailedError, if the Put could not be committed.
    """

    def __init__(self, models, deadline=None, callback=None, **kw):
        models, self.multiple = NormalizeAndTypeCheck(models, db.Model)
        self._entities = [model._populate_internal_entity() for model in models]
        super(DatastorePutTask, self).__init__(deadline=deadline, callback=callback, **kw)


    def rpc_callback(self, rpc, results, exception, callback):
        return lambda: datastore.put_callback(rpc, results, exception, callback=callback)

    def make_call(self):
        entities, multiple = NormalizeAndTypeCheck(self._entities, Entity)
        self.multiple = multiple

        # TODO handle this
        #if multiple and not entities:
        #  return []

        for entity in entities:
          if not entity.kind() or not entity.app_id_namespace():
            raise datastore_errors.BadRequestError(
                'App and kind must not be empty, in entity: %s' % entity)

        req = datastore_pb.PutRequest()
        req.entity_list().extend([e._ToPb() for e in entities])
        
        keys = [e.key() for e in entities]
        self.tx = _MaybeSetupTransaction(req, keys)

        resp = datastore_pb.PutResponse()
        self.rpc.make_call('Put', req, resp)



    def get_result(self):
        if self.cache_result is not None:
            return self.cache_result
        if len(self.exception) >= 1:
            raise self.exception[0]

        resp = self.rpc.response
        keys = resp.key_list()
        entities = self._entities
        multiple = self.multiple
        tx = self.tx


        num_keys = len(keys)
        num_entities = len(entities)
        if num_keys != num_entities:
           raise datastore_errors.InternalError(
               'Put accepted %d entities but returned %d keys.' %
               (num_entities, num_keys))

        for entity, key in zip(entities, keys):
           entity._Entity__key._Key__reference.CopyFrom(key)

        if tx:
           tx.entity_group = entities[0].entity_group()

        if multiple:
           return [Key._FromPb(k) for k in keys]
        else:
           return Key._FromPb(resp.key(0))


class DatastoreGetTask(DatastoreCrudTask):
    """Retrieves one or more entities from the datastore.

    Retrieves the entity or entities with the given key(s) from the datastore
    and returns them as fully populated Entity objects, as defined below. If
    there is an error, raises a subclass of datastore_errors.Error.

    If keys is a single key or string, an Entity will be returned, or
    EntityNotFoundError will be raised if no existing entity matches the key.

    However, if keys is a list or tuple, a list of entities will be returned
    that corresponds to the sequence of keys. It will include entities for keys
    that were found and None placeholders for keys that were not found.

    Args:
      # the primary key(s) of the entity(ies) to retrieve
      keys: Key or string or list of Keys or strings

    Returns:
      Entity or list of Entity objects
    """

    def __init__(self, keys, deadline=None, callback=None, **kw):
        self._keys = keys
        super(DatastoreGetTask, self).__init__(deadline=deadline, callback=callback, **kw)


    def rpc_callback(self, rpc, results, exception, callback):
        return lambda: datastore.get_callback(rpc, results, exception, callback=callback)

    def make_call(self):
        keys, multiple = NormalizeAndTypeCheckKeys(self._keys)
        self.multiple = multiple

        # TODO handle
        #if multiple and not keys:
        #    return []
        req = datastore_pb.GetRequest()
        req.key_list().extend([key._Key__reference for key in keys])
        _MaybeSetupTransaction(req, keys)

        resp = datastore_pb.GetResponse()
        self.rpc.make_call('Get', req, resp)


    def get_result(self):
        if self.cache_result is not None:
            return self.cache_result
        if len(self.exception) >= 1:
            raise self.exception[0]

        entities = self.results[0]
        if self.multiple:
          return entities
        else:
          if entities[0] is None:
            raise datastore_errors.EntityNotFoundError()
          return entities[0]


class DatastoreDeleteTask(DatastoreCrudTask):
    """Deletes one or more entities from the datastore. Use with care!

    Deletes the given entity(ies) from the datastore. You can only delete
    entities from your app. If there is an error, raises a subclass of
    datastore_errors.Error.

    Args:
        # the primary key(s) of the entity(ies) to delete
        keys: Key or string or list of Keys or strings

    Raises:
        TransactionFailedError, if the Delete could not be committed.
    """

    def __init__(self, keys, deadline=None, callback=None, **kw):
        self._keys = keys
        super(DatastoreDeleteTask, self).__init__(deadline=deadline, callback=callback, **kw)

    def rpc_callback(self, rpc, results, exception, callback):
        return lambda: datastore.delete_callback(rpc, results, exception, callback=callback)

    def make_call(self):
        keys, multiple = NormalizeAndTypeCheckKeys(self._keys)

        #TODO handle
        #if multiple and not keys:
        #    return

        req = datastore_pb.DeleteRequest()
        req.key_list().extend([key._Key__reference for key in keys])

        tx = _MaybeSetupTransaction(req, keys)

        resp = datastore_pb.DeleteResponse()
        self.rpc.make_call('Delete', req, resp)


    def get_result(self):
        if len(self.exception) >= 1:
            raise self.exception[0]

class DatastoreQueryTask(DatastoreTask):

    def __init__(self, query, limit=None, offset=None, deadline=None, callback=None, **kw):

        self._query = query._get_query() if isinstance(query, (db.GqlQuery, db.Query)) else query
        
        assert isinstance(self._query, (Query)) and not isinstance(self._query, MultiQuery), \
            "Query must be of instance Query, MultiQuery not handled yet"

        self._limit = limit
        self._offset = offset
        self._cache_key = "%s,query=%s,limit=%s,offset=%s" % (self.__class__.__name__, str(self._query),str(limit),str(offset))

        super(DatastoreQueryTask, self).__init__(**kw)

    @property
    def cache_key(self):
        return self._cache_key

    @property
    def limit(self):
        return self._limit

    @property
    def offset(self):
        return self._offset

    @property
    def query(self):
        return self._query


class QueryTask(DatastoreQueryTask):

    def make_call(self):
        pb = self._query._ToPb(self.limit, self.offset)
        result = datastore_pb.QueryResult()
        self.rpc.make_call('RunQuery', pb, result)        

    def rpc_callback(self, rpc, results, exception, callback):
        return lambda: datastore.run_callback(rpc, results, exception, callback=callback)
    
    def get_result(self):
        if self.cache_result is not None:
            return self.cache_result
        if len(self.exception) >= 1:
            raise self.exception[0]
        else:
            return [db.class_for_kind(e.kind()).from_entity(e) if isinstance(e, Entity) else e for e in self.results]

class CountTask(DatastoreQueryTask):

    def make_call(self):
        pb = self._query._ToPb(self.limit, self.offset)
        result = Integer64Proto()
        # datastore_v3, Count, request, result
        self.rpc.make_call('Count', pb, result)

    def rpc_callback(self, rpc, results, exception, callback):
        return lambda: datastore.count_callback(rpc, results, exception, callback=callback)

    def get_result(self):
        if self.cache_result is not None:
            return self.cache_result
        if len(self.exception) >= 1:
            raise self.exception[0]
        else:
            return self.results[0]


class AsyncMultiTask(list):
    """
        Context for running async tasks in.
        Add an rpc that is ready to be Waited on.
        After it has been run it should be ready to have CheckSuccess called.
    """
    def __init__(self, tasks=None):
        if tasks is None:
            super(AsyncMultiTask, self).__init__()
        else:
            super(AsyncMultiTask, self).__init__(tasks)

        for task in self:
            task.runner = self

    def run(self):
        """Runs the tasks, some tasks create additional rpc objects which are appended to self
           when all tasks and rpcs have been waited on the extra items are deleted from self
        """
        tasks = list(self)
        [ task.make_call() for task in self ]
        [ task.wait() for task in self ]
        self[:] = tasks

    def append(self, task):
        """Bind self to the task so the task, userrpc can append additional tasks to be run"""
        list.append(self, task)
        if isinstance(task, (RpcTask, apiproxy_stub_map.UserRPC)):
            task.runner = self

    def __repr__(self):
        return "%s%s" % (type(self), list.__repr__(self))


def determine_cache_hits_misses(tasks, cache_results):
    have = []
    todo = []
    for task in tasks:
        result = cache_results.get(task.cache_key)
        if result:
            have.append(task)
            task.cache_result = result
        else:
            todo.append(task)
    return have, todo


class CachedMultiTask(list):
    """
    CachedMultiTask is a runner that will first attempt to locate task results in cache.
    For items that miss, an AsyncMultiTask will be used to retrieve results and those results are cached.
    """
    
    def __init__(self, tasks=None, time=0, namespace=None, memcache=None, runner_type=None):
        """
        Constructs a caching multi task runner.
        
        @tasks a list of tasks to provide caching over
        @time expiration time in seconds, as defined by memcache.set_multi()
        @namespace a memcache namespace, as defined by memcache.set_multi()
        @memcache the memcache implementation to use, defaults to google.appengine.api.memcache.Client
        @runner_type the runner to use for tasks that are not found in cache, defaults to AsyncMultiTask
        """
        if tasks is None:
            super(CachedMultiTask,self).__init__()
        else:
            super(CachedMultiTask,self).__init__(tasks)
        self.time = time
        self.namespace = namespace
        self.memcache = memcache or memcache_builtin.Client()
        self.runner_type = runner_type or AsyncMultiTask
        
    @property
    def _cache_keys(self):
        """
        Returns a list of cache keys from the tasks.
        """
        return [t.cache_key for t in self]
        
    def delete_cached_entries(self, seconds=0):
        """
        Using the tasks' cache_keys, existing entries will be removed from cache.
        @seconds Optional number of seconds to make deleted items 'locked' for 'add' operations, as defined by memcache.delete_mutli()
        
        The return value is True if all operations completed successfully. False if one or more failed to complete.
        """
        return self.memcache.delete_multi(self._cache_keys, seconds=seconds, namespace=self.namespace)

    def run(self):
        """
        run tasks asyncronously, tasks may create additional UserRPC objects that are also inturn waited on.

        1. Fetch from memcache
        2. Filter into hits and misses (have, todo)
        3. Async run todo
        4. Set todo results into memcache
        """
        cache_keys = self._cache_keys

        cache_results = self.memcache.get_multi(cache_keys, namespace=self.namespace)

        have, todo = determine_cache_hits_misses(self, cache_results)
        # determine cached tasks
        if len(todo) > 0:
            task_runner = self.runner_type(todo)
            task_runner.run()
        set_dict = {}
        for task in todo:
            try:
                set_dict[task.cache_key] = task.get_result()
            except Exception:
                logging.info("Exception retrieving items after cache miss. Continuing.", exc_info=True)
        if set_dict:
            failed = self.memcache.set_multi(set_dict, time=self.time, namespace=self.namespace)
            if failed:
                logging.info("Memcache set_multi failed. %d items failed: %s", len(failed), failed)
            if len(failed) == len(todo):
                logging.error("Memcache set_multi failed entirely.")

    def __repr__(self):
        return "%s%s" % (type(self), list.__repr__(self))
