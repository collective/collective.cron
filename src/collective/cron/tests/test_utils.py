import unittest2 as unittest
import datetime
from pytz import UTC, timezone
from collective.cron.tests import base
from collective.cron.utils import (
    su_plone,
    asbool,
    NoSuchUserError,
    splitstrip,
    to_utc,
)

from collective.cron.adapters import utils as autils

class UtilsTest(base.IntegrationTestCase):
    def test_utils_suplone(self):
        acl = self.portal.acl_users
        user = su_plone(self.app, self.portal, ['test-user'])
        self.assertEquals(user._login, 'test-user')
        user = su_plone(self.app, self.portal, ['Plone_manager'])
        self.assertEquals(user._login, 'Plone_manager')
        self.assertRaises(
            NoSuchUserError, su_plone,
            self.app, self.portal, ['foo']
        )
        user = su_plone(self.app, self.portal, ['test-user'])

    def test_getfolder(self):
        self.login('Plone_manager')
        util = autils.CCRONUtils(self.portal, self.cron)
        f1 = util.getFolder('foocron', 'Foo Cron')
        SJ = '/'.join
        self.assertEquals(f1.getId(), 'foocron')
        self.assertEquals(f1.Title(), 'Foo Cron')
        self.assertEquals(SJ(f1.getPhysicalPath()), '/plone/foocron')
        f2 = util.getFolder('foocron', 'Foo Cron', f1)
        self.assertEquals(f2.getId(), 'foocron')
        self.assertEquals(f2.Title(), 'Foo Cron')
        self.assertEquals(SJ(f2.getPhysicalPath()), '/plone/foocron/foocron')
        self.logout()
         

class UtilsStest(base.SimpleTestCase):
    def test_asboolt(self):
        tests = {
            False:(0, None, -1, '0', False, 
                   'off', 'no', 'n', 'f', 'false',),
            True: (1, True, 'y', 'yes', 
                   'YES', 't', 'true', 'True', '1',)
        }
        for dest in tests:
            for orig in tests[dest]:
                self.assertEquals(
                    asbool(orig), dest, repr(orig))

    def test_splitstrip(self):
        self.assertEquals(splitstrip("""a   
                                     b   c"""), ["a", "b", "c"])


def test_suite():
    return unittest.defaultTestLoader.loadTestsFromName(__name__)

