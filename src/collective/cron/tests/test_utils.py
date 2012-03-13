import unittest
import datetime
from pytz import UTC, timezone
from collective.cron.tests import base
from collective.cron.utils import su_plone
from collective.cron.utils import NoSuchUserError
from collective.cron.utils import to_utc

class UtilsTest(base.TestCase):
    def test_suplone(self):
        rf = self.g.results_folder()
        acl = self.portal.acl_users
        userid = acl.searchUsers()[0]['userid']
        user = su_plone(self.app, self.portal, [userid])
        self.assertEquals(user._login, 'test_user_1_')
        user = su_plone(self.app, self.portal, ['portal_owner'])
        self.assertEquals(user._login, 'portal_owner')
        self.assertRaises(
            NoSuchUserError, su_plone,
            self.app, self.portal, ['foo']
        )

    def test_ToUtc(self):
        dt = datetime.datetime
        paris = timezone('Europe/Paris')
        tests = [
            (dt(2009, 1, 1, 1, 1, tzinfo=UTC),   dt(2009,1,1,1,1,tzinfo=UTC)),
            (dt(2009, 1, 1, 1, 1),               dt(2009,1,1,0,1,tzinfo=UTC)),
            (dt(2009, 1, 1, 1, 1, tzinfo=paris), dt(2009,1,1,0,1,tzinfo=UTC)),
        ]
        for orig, dest in tests:
            self.assertEquals(to_utc(orig), dest)

def test_suite():
    return unittest.defaultTestLoader.loadTestsFromName(__name__)

