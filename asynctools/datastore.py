#!/usr/bin/env python
#
# Copyright 2007 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# Modified by Ben Kamens to fix http://code.google.com/p/asynctools/issues/detail?id=14
#

"""The Python datastore API used by app developers.

Defines Entity, Query, and Iterator classes, as well as methods for all of the
datastore's calls. Also defines conversions between the Python classes and
their PB counterparts.

The datastore errors are defined in the datastore_errors module. That module is
only required to avoid circular imports. datastore imports datastore_types,
which needs BadValueError, so it can't be defined in datastore.
"""
import logging

from google.appengine.api import apiproxy_stub_map
from google.appengine.api import datastore_errors
from google.appengine.api.api_base_pb import Integer64Proto
from google.appengine.api.datastore_types import Key
from google.appengine.datastore import datastore_index
from google.appengine.datastore import datastore_pb
from google.appengine.runtime import apiproxy_errors

from google.appengine.api.datastore import _ToDatastoreError
from google.appengine.api.datastore import Entity,_MaybeSetupTransaction



def put_callback(rpc, result, exception, callback=None):
    try:
        assert isinstance(rpc.request, datastore_pb.PutRequest), "request should be a PutRequest"
        assert isinstance(rpc.response, datastore_pb.PutResponse), "response should be a PutResponse"

        response = generic_rpc_handler(rpc)
        result.append(response)
    except (datastore_errors.Error, apiproxy_errors.Error), exp:
        logging.debug("Exception (Delete):%s", exp)
        exception.append(exp)
    if callback:
        callback(rpc)


def get_rpc_handler(rpc):
  try:
      rpc.check_success()
  except apiproxy_errors.ApplicationError, err:
    raise _ToDatastoreError(err)
  resp = rpc.response
  entities = []
  for group in resp.entity_list():
    if group.has_entity():
      entities.append(Entity._FromPb(group.entity()))
    else:
      entities.append(None)

  return entities

def get_callback(rpc, result, exception, callback=None):
    try:
        assert isinstance(rpc.request, datastore_pb.GetRequest), "request should be a GetRequest"
        assert isinstance(rpc.response, datastore_pb.GetResponse), "response should be a GetResponse"

        response = get_rpc_handler(rpc)
        result.append(response)
    except (datastore_errors.Error, apiproxy_errors.Error), exp:
        logging.debug("Exception (Get):%s", exp)
        exception.append(exp)
    if callback:
        callback(rpc)



def generic_rpc_handler(rpc):
  try:
    rpc.check_success()
  except apiproxy_errors.ApplicationError, err:
    raise  _ToDatastoreError(err)
  return rpc.response

def delete_callback(rpc, result, exception, callback=None):
    try:
        assert isinstance(rpc.request, datastore_pb.DeleteRequest), "request should be a DeleteRequest"
        assert isinstance(rpc.response, datastore_pb.DeleteResponse), "response should be a DeleteResponse"

        response = generic_rpc_handler(rpc)
        result.append(response)
    except (datastore_errors.Error, apiproxy_errors.Error), exp:
        logging.debug("Exception (Delete):%s", exp)
        exception.append(exp)
    if callback:
        callback(rpc)


def count_callback(rpc, result, exception, callback=None):
    try:
        assert isinstance(rpc.request, datastore_pb.Query), "request should be a query"
        assert isinstance(rpc.response, Integer64Proto), "response should be a QueryResult"

        response = run_rpc_handler(rpc)
        result.append(response.value())
    except (datastore_errors.Error, apiproxy_errors.Error), exp:
        logging.debug("Exception (Count):%s", exp)
        exception.append(exp)
    if callback:
        callback(rpc)

def run_rpc_handler(rpc):
  try:
    rpc.check_success()
  except apiproxy_errors.ApplicationError, err:
    try:
      _ToDatastoreError(err)
    except datastore_errors.NeedIndexError, exc:
      yaml = datastore_index.IndexYamlForQuery(
        *datastore_index.CompositeIndexForQuery(rpc.request)[1:-1])
      raise datastore_errors.NeedIndexError(
        str(exc) + '\nThis query needs this index:\n' + yaml)

  return rpc.response

def process_query_result(result):
    if result.keys_only():
        return [Key._FromPb(e.key()) for e in result.result_list()]
    else:
        return [Entity._FromPb(e) for e in result.result_list()]


def run_callback(rpc, entities, exception, callback=None):
    try:
        assert isinstance(rpc.request,datastore_pb.Query), "request should be a query"
        assert isinstance(rpc.response,datastore_pb.QueryResult), "response should be a QueryResult"

        response = run_rpc_handler(rpc)
        entities += process_query_result(response)
        limit = rpc.request.limit()

        if len(entities) > limit:
            del entities[limit:]
        elif response.more_results() and len(entities) < limit:
            # create rpc for running


            count = limit - len(entities)

            req = datastore_pb.NextRequest()
            req.set_count(count)
            req.mutable_cursor().CopyFrom(rpc.response.cursor())
            result = datastore_pb.QueryResult()

            nextrpc = create_rpc(deadline=rpc.deadline)
            nextrpc.callback = lambda: next_callback(nextrpc, entities, exception, callback=callback)
            rpc.runner.append(nextrpc)

            nextrpc.make_call('Next', req, result)

            if rpc.runner:
                rpc.runner.append(nextrpc)
            else:
                nextrpc.Wait()

    except (datastore_errors.Error, apiproxy_errors.Error), exp:
        logging.debug("Exception (RunQuery):%s", exp)
        exception.append(exp)
        if callback:
            callback(rpc)

def next_rpc_handler(rpc):
    try:
        rpc.check_success()
    except apiproxy_errors.ApplicationError, err:
      logging.debug("next_rpc_handler")
      raise _ToDatastoreError(err)
    return rpc.response

def next_callback(rpc, entities, exception, callback=None):
    try:
        assert isinstance(rpc.request,datastore_pb.NextRequest), "request should be a query"
        assert isinstance(rpc.response,datastore_pb.QueryResult), "response should be a QueryResult"

        result = next_rpc_handler(rpc)
        entity_list = process_query_result(result)
        count = rpc.request.count()

        if len(entity_list) > count:
            del entity_list[count:]

        entities += entity_list


        if result.more_results() and len(entity_list) < count:
            # create rpc for running


            count = count - len(entity_list)

            req = datastore_pb.NextRequest()
            req.set_count(count)
            req.mutable_cursor().CopyFrom(rpc.response.cursor())
            result = datastore_pb.QueryResult()

            nextrpc = create_rpc(deadline=rpc.deadline)
            nextrpc.callback = lambda: next_callback(nextrpc, entities, exception, callback=callback)
            rpc.runner.append(nextrpc)

            nextrpc.make_call('Next', req, result)

            if rpc.runner:
                rpc.runner.append(nextrpc)
            else:
                nextrpc.Wait()

    except (datastore_errors.Error, apiproxy_errors.Error), exp:
        logging.debug("Exception (Next):%s", exp)
        exception.append(exp)
        if callback:
            callback(rpc)



def create_rpc(deadline=None, callback=None):
    return apiproxy_stub_map.UserRPC('datastore_v3', deadline, callback)






