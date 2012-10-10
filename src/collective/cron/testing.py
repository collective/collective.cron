import datetime
from Testing import ZopeTestCase as ztc
from zc.async import testing as zcatesting
import os
import croniter
import transaction
from OFS.Folder import Folder

from zope.component import getUtility

import unittest2 as unittest

from zope.configuration import xmlconfig

from plone.app.testing import (
    FunctionalTesting as BFunctionalTesting,
    IntegrationTesting as BIntegrationTesting,
    PLONE_FIXTURE,
    helpers,
    PloneSandboxLayer,
    setRoles,

    SITE_OWNER_NAME,
    SITE_OWNER_PASSWORD,
    TEST_USER_ID,
    TEST_USER_ID,
    TEST_USER_NAME,
    TEST_USER_NAME,
    TEST_USER_ROLES,
)
from plone.app.testing.selenium_layers import (
    SELENIUM_FUNCTIONAL_TESTING as SELENIUM_TESTING
)
from plone.testing import Layer, zodb, zca, z2


from collective.cron import crontab
from collective.cron.adapters import (
    manager,
    utils as autils,
)
from plone.app.async.interfaces import IAsyncService
from plone.app.async import testing as base
from plone.app.async.testing import (
    PLONE_MANAGER_NAME,
    PLONE_MANAGER_ID,
    PLONE_MANAGER_PASSWORD,
)


from collective.cron import utils

croniter.old_datetime = zcatesting.old_datetime
old_datetime = zcatesting._datetime
old_set_now = zcatesting.set_now
old__now = zcatesting._now
GENTOO_FF_UA = 'Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.9.1.3) Gecko/20090912 Gentoo Shiretoko/3.5.3'

class _datetime(old_datetime):
    """ A more complete patched datetime"""

    def astimezone(self, tz):
        try:
            dt = zcatesting.old_datetime.astimezone(
                self, tz)
        except ValueError, e:
            dt = utils.to_tz(self, tz)
        return _datetime(*dt.__reduce__()[1])

    def replace(self, *args, **kwargs):
        return _datetime(
            *zcatesting.old_datetime.replace(
                self, *args, **kwargs).__reduce__()[1])

    def __repr__(self):
        raw = zcatesting.old_datetime.__repr__(self)
        return "datetime.datetime%s" % ( raw[raw.index('('):],)

    def __add__(self, other):
        try:
            inewdt = zcatesting.old_datetime.__add__(self, other).__reduce__()[1]
        except:
            inewdt = other.__radd__(self).__reduce__()[1]
        return _datetime(*inewdt)

    def __reduce__(self):
        return (zcatesting.argh, zcatesting.old_datetime.__reduce__(self)[1])

    @classmethod
    def fromtimestamp(klass, ts):
        return klass(*zcatesting.old_datetime.fromtimestamp(ts).__reduce__()[1])

    @classmethod
    def utcnow(klass):
        dt = utils.to_utc(klass.now()).replace(tzinfo=None)
        return dt

    @classmethod
    def fromordinal(klass, ordinal): # pragma: no cover
        return klass(*zcatesting.old_datetime.fromordinal(ordinal).__reduce__()[1])

set_now = zcatesting.set_now

def setUpDatetime():
    zcatesting._datetime = _datetime
    zcatesting.setUpDatetime()
    reload(croniter)
    croniter.old_datetime = zcatesting.old_datetime
    croniter.datetime = _datetime
    set_now(datetime.datetime(2012,10,9,12,0))

def tearDownDatetime():
    croniter.datetime = zcatesting._datetime= old_datetime
    zcatesting._now  = old__now
    zcatesting.tearDownDatetime()


class CollectiveCronLayer(base.AsyncLayer):
    def setUpZope(self, app, configurationContext):
        base.AsyncLayer.setUpZope(self, app, configurationContext)
        import collective.cron
        from collective.cron import tests
        self.loadZCML('configure.zcml', package=collective.cron)
        z2.installProduct(app, 'collective.cron')
        self.loadZCML('test.zcml', package=tests)

    def setUpPloneSite(self, portal):
        base.AsyncLayer.setUpPloneSite(self, portal)
        self.applyProfile(portal, 'collective.cron:default')

COLLECTIVE_CRON_FIXTURE             = CollectiveCronLayer()

_layer = None
class LayerMixin(base.LayerMixin):
    defaultBases = (COLLECTIVE_CRON_FIXTURE,)
    def testTearDown(self):
        from collective.cron import testing as crontesting
        crontesting._layer = None
        transaction.commit()
    def testSetUp(self):
        base.LayerMixin.testSetUp(self)
        self['cron'] = crontab.Cron(
            name=u'testcron',
            activated = True,
            periodicity=u'*/1 * * * *')
        self['crontab'] = crontab.Crontab.load([self['cron']])
        self['crontab_manager'] = manager.CrontabManager(
            self['portal'], self['crontab'])
        self['cron_manager'] = manager.CronManager(
            self['portal'], self['cron'])
        self['cron_queue'] = self['crontab_manager'].queue
        self['crontab_marker'] = self['cron_queue'].marker
        self['async'] = self['cron_queue'].service
        self['queue'] = self['cron_queue'].queue
        self['cron_utils'] = autils.CCRONUtils(
            self['portal'], self['cron'])
        from collective.cron import testing as crontesting
        crontesting._layer = self
        transaction.commit()

class IntegrationTesting(LayerMixin, base.IntegrationTesting):
    def testTearDown(self):
        LayerMixin.testTearDown(self)
        base.IntegrationTesting.testTearDown(self)

    def testSetUp(self):
        base.IntegrationTesting.testSetUp(self)
        LayerMixin.testSetUp(self)

class FunctionalTesting(LayerMixin, base.FunctionalTesting):
    def testTearDown(self):
        transaction.commit()
        LayerMixin.testTearDown(self)
        transaction.commit()
        base.FunctionalTesting.testTearDown(self)
    def testSetUp(self): # pragma: no cover
        base.FunctionalTesting.testSetUp(self)
        transaction.commit()
        LayerMixin.testSetUp(self)
        transaction.commit()

class TimedTesting(Layer):
    def setUp(self):
        setUpDatetime()

    def tearDown(self):
        tearDownDatetime()

class TimedFunctionalTesting(FunctionalTesting):
    defaultBases = ((TimedTesting(),) + FunctionalTesting.defaultBases)

    def testSetUp(self):
        set_now(datetime.datetime(2008,1,1,1,1))
        transaction.commit()
        FunctionalTesting.testSetUp(self)
        transaction.commit()

    def testTearDown(self):
        transaction.commit()
        FunctionalTesting.testTearDown(self)
        transaction.commit()

class SimpleLayer(Layer):
    defaultBases = tuple()

COLLECTIVE_CRON_SIMPLE              = SimpleLayer(name='CollectiveCron:Simple')
COLLECTIVE_CRON_INTEGRATION_TESTING = IntegrationTesting(
    name = "CollectiveCron:Integration")
COLLECTIVE_CRON_FUNCTIONAL_TESTING  = FunctionalTesting(
    name = "CollectiveCron:Functional")
COLLECTIVE_CRON_TFUNCTIONAL_TESTING  = TimedFunctionalTesting(
    name = "CollectiveCron:TFunctional")
COLLECTIVE_CRON_SELENIUM_TESTING    = FunctionalTesting(
    bases = (SELENIUM_TESTING,
             COLLECTIVE_CRON_FUNCTIONAL_TESTING,),
    name = "CollectiveCron:Selenium")

"""
Register our layers as using async storage
"""
base.registerAsyncLayers(
    [COLLECTIVE_CRON_FIXTURE,
     COLLECTIVE_CRON_INTEGRATION_TESTING,
     COLLECTIVE_CRON_FUNCTIONAL_TESTING,
     COLLECTIVE_CRON_SELENIUM_TESTING]
)


class Browser(z2.Browser): # pragma: no cover
    """Patch the browser class to be a little more like a webbrowser."""

    def __init__(self, app, url=None, headers=None):
        if headers is None: headers = []
        z2.Browser.__init__(self, app, url)
        self.mech_browser.set_handle_robots(False)
        for h in headers:
            k, val = h
            self.addHeader(k, val)
        if url is not None:
            self.open(url)

    def print_contents_to_file(self, dest='~/.browser.html'):

        fic = open(os.path.expanduser(dest), 'w')
        fic.write(self.contents)
        fic.flush()
        fic.close()

    @property
    def print_contents(self):
        """Print the browser contents somewhere for you to see its
        context in doctest pdb, t
        ype browser.print_contents(browser) and that's it,
        open firefox with file://~/browser.html."""
        self.print_contents_to_file()

    @classmethod
    def new(cls, url, user=None, passwd=None, headers=None, login=False):
        """instantiate and return a testbrowser for convenience """
        if headers is None: headers = []
        if user: login = True
        if not user: user = PLONE_MANAGER_NAME
        if not passwd: passwd = PLONE_MANAGER_PASSWORD
        if login:
            auth = 'Basic %s:%s' % (user, passwd)
            headers.append(('Authorization', auth))
        headers.append(('User-agent' , GENTOO_FF_UA))
        browser = cls(_layer['app'], url, headers=headers)
        return browser

