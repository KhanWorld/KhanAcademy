import unittest
from google.appengine.ext import testbed
from google.appengine.datastore import datastore_stub_util
from google.appengine.ext import db

class SettingTest(unittest.TestCase):

    def setUp(self):
        self.testbed = testbed.Testbed()
        self.testbed.activate()

        # Create a consistency policy that will simulate the High Replication consistency model.
        self.policy = datastore_stub_util.PseudoRandomHRConsistencyPolicy(probability=0)

        self.testbed.init_datastore_v3_stub(consistency_policy=self.policy)
        self.testbed.init_user_stub()
        self.testbed.init_memcache_stub()

    def tearDown(self):
        self.testbed.deactivate()

    def testMigration(self):
        from models import Setting

        # put in some old values
        self.policy.SetProbability(1)
        db.put([
            Setting(key_name='test', parent=None, value='old and busted'),
            Setting(key_name='another', parent=None, value='another old value'),
        ])
        Setting._get_settings_dict(bust_cache=True)
        self.policy.SetProbability(0)

        self.assertEqual(Setting._get_or_set_with_key('test'), 'old and busted')
        self.assertEqual(Setting._get_or_set_with_key('another'), 'another old value')


        # simulate a write
        Setting._get_or_set_with_key('test', 'new hotness')

        # now assert that old and new style settings were updated
        old = Setting.get_by_key_name('test', parent=None)
        self.assertEqual(old.value, 'new hotness')
        new = Setting.get_by_key_name('test', parent=Setting.entity_group_key())
        self.assertEqual(new.value, 'new hotness')

        # finally, check the caching layers work too
        self.assertEqual(Setting._cache_get_by_key_name("test"), 'new hotness')
        self.assertEqual(Setting._get_or_set_with_key("another"), 'another old value')

    def testConsistency(self):
        from models import Setting

        # put in some old values
        self.policy.SetProbability(1)
        Setting.count_videos(10)
        self.policy.SetProbability(0)

        self.assertEqual(Setting.count_videos(), '10')


        Setting.count_videos(15)
        self.assertEqual(Setting.count_videos(), '15')

