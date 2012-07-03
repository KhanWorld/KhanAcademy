# Essentially the same as the general sharded-counter from app-engine-samples,
# so... here's the notice:

# Copyright 2008 Google Inc.
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

import random
import logging

from google.appengine.ext import db

#
# Sharded counters are useful for keeping a global count. See user_counter.py
# for an example of their use.
#

class ShardedCounterConfig(db.Model):
    '''Holds the configuration for a class of `ShardedCounter`s.'''
    name = db.StringProperty(required=True)
    num_shards = db.IntegerProperty(required=True, default=20)

class ShardedCounter(db.Model):
    '''`ShardedCounter`s work together to hold a global count.
    This model is intended to be written often and read rarely (once a day). If
    you need a global that will be read often consider writing a similar model
    using memcache.
    '''
    name = db.StringProperty(required=True)
    count = db.IntegerProperty(required=True, default=0)

def get_count(name):
    '''Get the count'''
    try:
        total = 0
        for counter in ShardedCounter.all().filter('name = ', name):
            total += counter.count
        return total

    except Exception, e:
        logging.error("Error in get_count: %s" % e)
        return 0

def add(name, n):
    '''Add n to the counter (n < 0 is valid)'''
    try:
        config = ShardedCounterConfig.get_or_insert(name, name=name)
        def transaction():
            index = random.randint(0, config.num_shards - 1)
            shard_name = name + str(index)
            counter = ShardedCounter.get_by_key_name(shard_name)
            if counter is None:
                counter = ShardedCounter(key_name=shard_name, name=name)
            counter.count += n
            counter.put()

        db.run_in_transaction(transaction)

    except Exception, e:
        logging.error("Error in add: %s" % e)

def change_number_of_shards(name, num):
    '''Change the number of shards to num'''
    try:
        config = ShardedCounterConfig.get_or_insert(name, name=name)
        def transaction():
            if config.num_shards > num:
                for i in range(num, config.num_shards):
                    del_shard_name = name + str(i)
                    del_counter = ShardedCounter.get_by_key_name(del_shard_name)

                    keep_index = random.randint(0, num-1)
                    keep_shard_name = name + str(keep_index)
                    keep_counter = ShardedCounter.get_by_key_name(keep_shard_name)

                    if keep_counter is None:
                        keep_counter = ShardedCounter(key_name=shard_name, name=name)
                    keep_counter.count += del_counter.count

                    keep_counter.put()
                    del_counter.delete()

            # if num > num_shards, we don't have to do data transfer

            config.num_shards = num
            config.put()

        db.run_in_transaction(transaction)

    except Exception, e:
        logging.error("Error in change_number_of_shards: %s" % e)
