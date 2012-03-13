import pytz
import datetime

from zope import schema
from zope.interface import implements
from five import grok
from zope.component import getUtility
import transaction

from Products.PloneTestCase import PloneTestCase as ptc
from Products.CMFCore.utils import getToolByName

from zc.async.testing import set_now, setUpDatetime, tearDownDatetime

from plone.app.async.interfaces import IAsyncService
from plone.app.async.testing import AsyncSandbox

from collective.cron.tests.layer import layer
from collective.cron.tests.backend import SomeJobRunner

class BaseTestCase(ptc.PloneTestCase):
    """We use this base class for all the tests in this package.
    If necessary, we can put common utility or setup code in here.
    """
    layer = layer

class FunctionalTestCase(ptc.FunctionalTestCase):
    """Functionnal base TestCase."""
    layer = layer

class SandboxedTestCase(AsyncSandbox, BaseTestCase):
    def setUp(self):
        BaseTestCase.setUp(self)

    def tearDown(self):
        BaseTestCase.tearDown(self)

    def afterSetUp(self):
        AsyncSandbox.afterSetUp(self)
        BaseTestCase.afterSetUp(self)

    def afterClear(self):
        AsyncSandbox.afterClear(self)
        BaseTestCase.afterClear(self)


class TestCase(SandboxedTestCase):
    def setUp(self):
        BaseTestCase.setUp(self)
        setUpDatetime()
        self.setRoles(['CollectiveCron'])
        setattr(SomeJobRunner, '_old_run', getattr(SomeJobRunner, 'run'))
        def run(klass):
            """."""
            return ['foo']
        setattr(SomeJobRunner, 'run', run)
        self.async = getUtility(IAsyncService)
        self.queue = self.async.getQueues()['']
        self.folder.invokeFactory('SomeScrap', 'g')
        self.assertEquals( len(self.queue), 0)
        self.g = self.folder['g']
        self.g.activated = True
        self.g.periodicity = '%s * * * * *' %','.join([repr(a) for a in  range(0,60)])
        self.async = getUtility(IAsyncService)
        self.queue = self.async.getQueues()['']
        set_now(datetime.datetime(2008, 1, 1, 1, 1, tzinfo=pytz.UTC))
        transaction.commit()

    def tearDown(self):
        self.folder.manage_delObjects(['g'])
        noecho = [self.queue.remove(j) for j in self.queue]
        tearDownDatetime()
        BaseTestCase.tearDown(self)

# vim:set et sts=4 ts=4 tw=80:
