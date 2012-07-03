import os
import simplejson
import urllib
import urllib2

from google.appengine.ext.webapp import RequestHandler

from gandalf import gandalf
from gandalf.models import GandalfBridge, GandalfFilter
from gandalf.filters import BridgeFilter

# See gandalf/tests/run_tests.py for the full explanation/sequence of these tests

GANDALF_API_PREFIX = "http://localhost:8080/gandalf/api/v1/"

class RunStep(RequestHandler):

    def get(self):

        if not os.environ["SERVER_SOFTWARE"].startswith('Development'):
            return

        # Delete all bridges and filters so that we have a fresh testing environment
        for bridge in GandalfBridge.all():
            bridge.delete()
    
        for filter in GandalfFilter.all():
            filter.delete()

        step = self.request.get("step")
        v = None

        if step == "creating_bridge":
            v = self.creating_bridge()
        elif step == "can_cross_empty_bridge":
            v = self.can_cross_empty_bridge()
        elif step == "can_cross_all_users_whitelist":
            v = self.can_cross_all_users_whitelist()
        elif step == "can_cross_all_users_blacklist":
            v = self.can_cross_all_users_blacklist()
        elif step == "can_cross_all_users_whitelist_and_blacklist":
            v = self.can_cross_all_users_whitelist_and_blacklist()
        elif step == "can_cross_all_users_inside_percentage":
            v = self.can_cross_all_users_inside_percentage()
        elif step == "can_cross_all_users_outside_percentage":
            v = self.can_cross_all_users_outside_percentage()

        self.response.out.write(simplejson.dumps(v))

    # TODO (jpulgarin): This hangs on urlopen, fix
    def creating_bridge(self):
        bridge_name = self.request.get('bridge_name')

        data = {
            'bridge_name': bridge_name,
        }

        req = urllib2.Request(os.path.join(GANDALF_API_PREFIX, "bridges/update"), urllib.urlencode(data))

        response = urllib2.urlopen(req)
        try:
            content = response.read()
        finally:
            response.close()

        return content

    def can_cross_empty_bridge(self):
        bridge_name = "balrog"
        filter_type = "all-users"

        bridge = GandalfBridge.get_or_insert(bridge_name)

        return gandalf(bridge_name)


    def can_cross_all_users_whitelist(self):
        bridge_name = "balrog"
        filter_type = "all-users"

        bridge = GandalfBridge.get_or_insert(bridge_name)

        GandalfFilter(bridge=bridge, filter_type=filter_type, whitelist=True).put()

        return gandalf(bridge_name)

    def can_cross_all_users_blacklist(self):
        bridge_name = "balrog"
        filter_type = "all-users"

        bridge = GandalfBridge.get_or_insert(bridge_name)

        GandalfFilter(bridge=bridge, filter_type=filter_type, whitelist=False).put()

        return gandalf(bridge_name)

    def can_cross_all_users_whitelist_and_blacklist(self):
        bridge_name = "balrog"
        filter_type = "all-users"

        bridge = GandalfBridge.get_or_insert(bridge_name)

        GandalfFilter(bridge=bridge, filter_type=filter_type, whitelist=True).put()
        GandalfFilter(bridge=bridge, filter_type=filter_type, whitelist=False).put()

        return gandalf(bridge_name)

    def can_cross_all_users_inside_percentage(self):
        bridge_name = "balrog"
        filter_type = "all-users"

        bridge = GandalfBridge.get_or_insert(bridge_name)

        filter = GandalfFilter(bridge=bridge, filter_type=filter_type, whitelist=True)
        filter.put()
        
        identity_percentage = BridgeFilter._identity_percentage(filter.key())

        filter.percentage = identity_percentage + 1
        filter.put()

        return gandalf(bridge_name)

    def can_cross_all_users_outside_percentage(self):
        bridge_name = "balrog"
        filter_type = "all-users"

        bridge = GandalfBridge.get_or_insert(bridge_name)

        filter = GandalfFilter(bridge=bridge, filter_type=filter_type, whitelist=True)
        filter.put()

        identity_percentage = BridgeFilter._identity_percentage(filter.key())

        filter.percentage = identity_percentage
        filter.put()

        return gandalf(bridge_name)
