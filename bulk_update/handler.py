#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (c) 2010, Dean Brettle (dean@brettle.com)
# All rights reserved.
# Licensed under the New BSD License: http://www.opensource.org/licenses/bsd-license.php
#
# Redistribution and use in source and binary forms, with or without modification,
# are permitted provided that the following conditions are met:
#
#    * Redistributions of source code must retain the above copyright notice,
#      this list of conditions and the following disclaimer.
#    * Redistributions in binary form must reproduce the above copyright notice,
#      this list of conditions and the following disclaimer in the documentation
#      and/or other materials provided with the distribution.
#    * Neither the name of Dean Brettle nor the names of its contributors may be
#      used to endorse or promote products derived from this software without 
#      specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND 
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED 
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED.
# IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT,
# INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT
# NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR
# PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY,
# WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE 
# POSSIBILITY OF SUCH DAMAGE.

""" A handler that supports updating many entities in the datastore without hitting
request timeout limits.

To use to re-put (i.e. put without changes):

1. Place this file in: /bulk_update/handler.py

2. In your main.py:

import bulk_update.handler

def main():
    application = webapp.WSGIApplication([ 
        ('/admin/reput', bulk_update.handler.UpdateKind),
        ])
    run_wsgi_app(application)

3. Add the following to your app.yaml:
  handlers:
  - url: /admin/.*
    script: main.py
    login: admin
    
4. To re-put (ie. a null update) all the entities of kind ModelClass, visit:
   /admin/reput?kind=ModelClass
   
To actually make changes, add the following in main.py:

class MyUpdateKind(bulk_update.handler.UpdateKind):
    def update(self, entity):
        entity.attr1 = new_value1
        entity.attr2 = new_value2
        ...
        return True

def main():
    application = webapp.WSGIApplication([ 
        ('/admin/myupdate', MyUpdateKind),
        ])
    run_wsgi_app(application)
    
and then visit /admin/myupdate?kind=ModelClass.

You may also start the update by calling:

bulk_update.handler.start_task('/admin/myupdate', {'kind': 'ModelClass'})

 
"""

import cgi
import datetime
import logging
import user_util
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.api import users
from google.appengine.ext import db
from google.appengine.api import memcache
from google.appengine.api import taskqueue
from google.appengine.runtime import DeadlineExceededError

KEY_FORMAT = "bulk_update_%s"

def start_task(task_path, task_params):
    if _is_in_progress(task_path):
        logging.info('Task %s is already in progress.' % task_path)
        return False
    _set_in_progress(task_path, True)
    taskqueue.add(url=task_path, params=task_params)
    logging.info('Task %s(%s) started.' % (task_path, task_params))
    return True

def cancel_task(task_path):
    _set_in_progress(task_path, False)
    
def _set_in_progress(task_path, val):
    memcache.set(KEY_FORMAT % task_path, val)
    
def _is_in_progress(task_path):
    result = memcache.get(KEY_FORMAT % task_path)
    return result
    
class UpdateKind(webapp.RequestHandler):
    @user_util.admin_only
    def get(self):
        if self.request.get('cancel'):
            cancel_task(self.request.path)
            self.response.out.write('Your request to interrupt has been filed.')
        elif _is_in_progress(self.request.path):
            self.response.out.write('Your request is already in progress.')
        else:
            if start_task(self.request.path, self.request.params):
                self.response.out.write('Your request has been added to task queue.  Monitor the log for status updates. ')
            else:
                cancel_uri = self.request.path_url + '?' + self.request.query_string + '&cancel=1'
                self.response.out.write('To interrupt the request, <a href="%s">click here</a>.' % cancel_uri)

    def post(self):        
        # To prevent CSRF attacks, all requests must be from the task queue
        if 'X-AppEngine-QueueName' not in self.request.headers:
            logging.error("Potential CSRF attack detected")
            self.response.set_status(403, message="Potential CSRF attack detected due to missing header.")
            return
        
        if not _is_in_progress(self.request.path):
            logging.info('Cancelled.')
            return
        cursor = self.request.get('cursor')
        count = self.request.get('count')
        if not count:
            count = 0
        count = int(count)
        kind = self.request.get('kind')        
        query = self.get_keys_query(kind)
        if cursor:
            query.with_cursor(cursor)
        done = False
        new_cursor = cursor
        # dev server doesn't throw DeadlineExceededError so we do it ourselves
        deadline = datetime.datetime.now() + datetime.timedelta(seconds=25)
        try:
            for key in query:
                def do_update():
                    e = db.get(key)
                    if self.update(e):
                        e.put()
                    if datetime.datetime.now() > deadline:
                        raise DeadlineExceededError
                if self.use_transaction():
                    db.run_in_transaction(do_update)
                else:
                    do_update()
                new_cursor = query.cursor()
                count = count + 1
            _set_in_progress(self.request.path, False)
            logging.info('Finished! %d %s processed.', count, kind)
            done = True
        except DeadlineExceededError:
            pass
        except:
            logging.exception('Unexpected exception')
        finally:
            if done:
                return
            if new_cursor == cursor:
                logging.error('Stopped due to lack of progress at %d %s with cursor = %s', count, kind, new_cursor)
                _set_in_progress(self.request.path, False)
            else:
                logging.info('Processed %d %s so far.  Continuing in a new task...', count, kind)
                new_params = {}
                for name, value in self.request.params.items():
                    new_params[name] = value
                new_params['cursor'] = new_cursor
                new_params['count']= count
                taskqueue.add(url=self.request.path, params=new_params)
                
    def get_keys_query(self, kind):
        """Returns a keys-only query to get the keys of the entities to update"""
        return db.GqlQuery('select __key__ from %s' % kind)
    
    def update(self, entity):
        """Override in subclasses to make changes to an entity"""
        return True

    def use_transaction(self):
        """Override in subclasses to not run each update in a transaction"""
        return True
