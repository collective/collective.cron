import unittest2 as unittest
import datetime
from pytz import UTC, timezone
from collective.cron.tests import base
from collective.cron.utils import (
    su_plone,
    asbool,
)

from collective.cron import interfaces as i
from collective.cron.crontab import runJob, Runner
from zope.component import getGlobalSiteManager, getAdapters, queryMultiAdapter, adapts, adapter
from zope.interface import implements

from Products.CMFPlone.interfaces.siteroot import IPloneSiteRoot


_finished = []
_started = []
_results = []
_counter = 0
class SimpleRunner(Runner):

    def run(self):
        from collective.cron.tests import test_jobrunner
        test_jobrunner._counter += 1
        test_jobrunner._results.append(test_jobrunner._counter)


class SimpleRunnerWithWarn(SimpleRunner):

    def run(self):
        SimpleRunner.run(self)
        return 'warn'


class LocalSimpleRunner(SimpleRunner):

    def run(self):
        SimpleRunner.run(self)
        return 'local'


class FailureRunner(Runner):

    def run(self):
        raise Exception('foo')


@adapter(i.IStartedCronJobEvent)
def started_event(event):
    from collective.cron.tests import test_jobrunner
    test_jobrunner._started.append(1)


@adapter(i.IFinishedCronJobEvent)
def finished_event(event):
    from collective.cron.tests import test_jobrunner
    test_jobrunner._finished.append(1)


class JobRunnerTest(base.IntegrationTestCase):

    def setUp(self):
        base.IntegrationTestCase.setUp(self)
        self.gsm = getGlobalSiteManager()
        self.psm = self.portal.getSiteManager()
        [self.queue.remove(j) for j in self.queue]

    def tearDown(self):
        base.IntegrationTestCase.tearDown(self)
        _counter = 0
        _results[:] = []
        _finished[:] = []
        _started[:] = []
        [self.queue.remove(j) for j in self.queue]

    def get_adp(self, cron):
        return queryMultiAdapter((self.portal, cron),
                          i.IJobRunner, name=cron.name)

    def test_crontab_runjob_event(self):
        # a job withtout any utility attached must run as NOTRUN
        # even if it is a NOOP
        self.cron.logs = []
        self.crontab.save()
        adp =  self.get_adp(self.cron)
        self.assertTrue(adp is None)
        self.gsm.registerHandler(finished_event)
        self.gsm.registerHandler(started_event)
        ret = runJob(self.portal, self.cron)
        self.assertEquals(self.cron.logs[-1].status, 3)
        self.assertEquals(_started[0], 1)
        self.gsm.unregisterHandler(finished_event)
        self.gsm.unregisterHandler(started_event)
        ret = runJob(self.portal, self.cron)
        self.assertEquals(len(self.cron.logs), 2)
        self.assertEquals(len(_started), 1)

    def test_crontab_runjob_run(self):
        # a job withtout any utility attached must run as NOTRUN
        # even if it is a NOOP
        adp =  self.get_adp(self.cron)
        self.assertTrue(adp is None)
        ret = runJob(self.portal, self.cron)
        self.assertEquals(self.cron.logs[-1].status, 3)
        #
        # register an adapter with trivial code
        # no failure
        #
        self.gsm.registerAdapter(SimpleRunner, name=self.cron.name)
        adp = self.get_adp(self.cron)
        self.assertFalse(adp is None)
        ret = runJob(self.portal, self.cron)
        self.assertEquals(_results, [1])
        self.assertEquals(
            ret,
            (1, [], self.cron.uid, ('', 'plone')))
        self.gsm.unregisterAdapter(SimpleRunner, name=self.cron.name)

        #
        # same with logs
        #
        self.gsm.registerAdapter(SimpleRunnerWithWarn, name=self.cron.name)
        ret = runJob(self.portal, self.cron)
        self.assertEquals(_results, [1, 2])
        self.assertEquals(
            ret,
            (2, [u'warn'], self.cron.uid, ('', 'plone')))
        self.assertEquals(self.cron.logs[-1].status, 2)
        self.assertEquals(self.cron.logs[-1].messages, [u'warn'])
        self.gsm.unregisterAdapter(SimpleRunnerWithWarn, name=self.cron.name)

        #
        # register an adapter with trivial code
        # which raise a failure
        #
        self.gsm.registerAdapter(FailureRunner, name=self.cron.name)
        ret = runJob(self.portal, self.cron)
        self.assertEquals(
            ret,
            (0, [u'foo'], self.cron.uid, ('', 'plone')))
        self.gsm.unregisterAdapter(FailureRunner)
        self.assertEquals(self.cron.logs[-1].status, 0)
        self.assertEquals(self.cron.logs[-1].messages, [u'foo'])
        self.gsm.unregisterAdapter(FailureRunner, name=self.cron.name)

        #
        # register an adapter with trivial code
        # no failure / registered locally
        #
        ret = runJob(self.portal, self.cron)
        self.assertEquals(self.cron.logs[-1].status, 3)
        self.psm.registerAdapter(LocalSimpleRunner, name=self.cron.name)
        ret = runJob(self.portal, self.cron)
        self.assertEquals(_results, [1, 2, 3])
        self.assertEquals(self.cron.logs[-1].messages, [u'local'])
        self.psm.unregisterAdapter(LocalSimpleRunner, name=self.cron.name)

def test_suite():
    return unittest.defaultTestLoader.loadTestsFromName(__name__)

