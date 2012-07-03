import datetime
import time
import logging
import os
from types import GeneratorType

from google.appengine.ext import deferred

# fast_slow_queue relies on the deferred library,
# and as such it is susceptible to the same path manipulation weaknesses explained here:
# http://stackoverflow.com/questions/2502215/permanenttaskfailure-in-appengine-deferred-library
#
# ...if you need to run one-time configuration or path manipulation code when an instance
# is started, you may need to add that code to this file as this file will become
# a possibly instance-starting entry point. See above Stack Oveflow question.

QUEUE_NAME = "fast-background-queue"
SLOW_QUEUE_NAME = "slow-background-queue"

func_cache = {}

def handler(func_peek):

    def queue_decorator(func):

        # Deferred can't target inner/wrapped functions, so we 
        # always target guarantee_slow and use func_cache to keep
        # wrapped func references around.
        func_key = "%s.%s" % (func.__module__, func.__name__)
        func_cache[func_key] = func

        def wrapped(*args, **kwargs):

            # If quick peek function passes
            if func_peek(*args, **kwargs):

                # Defer execution of (guaranteed) slow function
                kwargs["_queue"] = SLOW_QUEUE_NAME
                kwargs["_func_key"] = func_key
                deferred.defer(guarantee_slow, *args, **kwargs)

                logging.debug("fast_slow_queue deferred execution of %s" % func_key)

        return wrapped

    return queue_decorator

def guarantee_slow(*args, **kwargs):
    
    func_key = kwargs.get("_func_key")
    if not func_key or not func_key in func_cache:
        return

    func = func_cache[func_key]

    # Remove any keyword arguments added by queue_decorator
    fixed_kw_args = {}
    accepted_kw_names = func.func_code.co_varnames[:func.func_code.co_argcount]
    for name in accepted_kw_names:
        if name in kwargs:
            fixed_kw_args[name] = kwargs[name]

    then = datetime.datetime.now()

    result = func(*args, **fixed_kw_args)

    if type(result) == GeneratorType:
        raise Exception("fast_slow_queue cannot queue generator functions.")

    now = datetime.datetime.now()

    if (now - then).seconds < 1:
        # If execution of this func didn't take at least 1000ms, sleep for a full second.
        # This will tend to overcompensate, but it's safer than trying to sleep for (1000ms - duration)
        # as time.sleep accuracy depends on the OS's clock, and we never want to risk averaging < 1000ms.
        logging.debug("Delaying execution of task to guarantee 1000ms slowness")

        if not os.environ["SERVER_SOFTWARE"].startswith('Development'):
            time.sleep(1)
