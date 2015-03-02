from Products.PythonScripts.tests.testPythonScript import VerifiedPythonScript
import transaction
import unittest2 as unittest
import datetime
from pytz import UTC, timezone
from collective.cron.tests import base
from collective.cron.utils import (
    su_plone,
    asbool,
)

from collective.cron import interfaces as i
from collective.cron.crontab import runJob, Runner, Crontab
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
        self.cron.name = u'testcron'
        self.cron.save()
        _counter = 0
        _results[:] = []
        _finished[:] = []
        _started[:] = []
        [self.queue.remove(j) for j in self.queue]

        #remove any leftover pythonscripts
#        for id in self.portal.objectIds(['Script (Python)']):
#            self.portal.manage_delObjects([id])

    def get_adp(self, cron):
        return queryMultiAdapter((self.portal, cron),
                          i.IJobRunner, name=cron.name)

    def _newPS(self, txt, bind=None):
        ps = VerifiedPythonScript('ps')
        ps.ZBindings_edit(bind or {})
        ps.write(txt)
        ps._makeFunction()
        if ps.errors:
            raise SyntaxError, ps.errors[0]
        return ps


    def test_crontab_runjob_event(self):
        # a job withtout any utility attached must run as NOTRUN
        # even if it is a NOOP
        self.cron.logs = []
        self.cron.name = u'testjobrunnercron'
        self.cron.save()                               
        adp =  self.get_adp(self.cron)
        self.assertTrue(adp is None)
        self.gsm.registerHandler(finished_event)
        self.gsm.registerHandler(started_event)
        ret = runJob(self.portal, self.cron)
        self.assertEquals(Crontab.load().by_name('testjobrunnercron')[0].logs[0].status, 3)
        self.assertEquals(_started[0], 1)
        self.gsm.unregisterHandler(finished_event)
        self.gsm.unregisterHandler(started_event)
        ret = runJob(self.portal, self.cron)
        self.assertEquals(len(Crontab.load().by_name('testjobrunnercron')[-1].logs), 2)
        self.assertEquals(len(_started), 1)
        self.cron.name = u'testcron'
        self.cron.save()                                

    def test_crontab_runjob_run(self):
        # a job withtout any utility attached must run as NOTRUN
        # even if it is a NOOP
        [self.layer['queue'].remove(a) for a in self.layer['queue']]
        self.cron.name = u'testjobrunnercron'
        self.cron.save()
        adp =  self.get_adp(self.cron)
        self.assertTrue(adp is None)
        ret = runJob(self.portal, self.cron)
        self.assertEquals(Crontab.load().by_name('testjobrunnercron')[0].logs[0].status, 3)
        #
        # register an adapter with trivial code
        # no failure
        #
        gsm = getGlobalSiteManager()
        psm = self.portal.getSiteManager() 
        gsm.registerAdapter(SimpleRunner, name=self.cron.name)
        transaction.commit()
        adp = self.get_adp(self.cron)
        self.assertFalse(adp is None)
        ret = runJob(self.portal, self.cron)
        self.assertEquals(_results, [1])
        self.assertEquals(
            ret,
            (1, [], self.cron.uid, ('', 'plone')))
        gsm.unregisterAdapter(SimpleRunner, name=self.cron.name)
        transaction.commit()

        #
        # same with logs
        #
        gsm.registerAdapter(SimpleRunnerWithWarn, name=self.cron.name)
        transaction.commit()
        ret = runJob(self.portal, self.cron)
        self.assertEquals(_results, [1, 2])
        self.assertEquals(
            ret,
            (2, [u'warn'], self.cron.uid, ('', 'plone')))
        self.assertEquals(Crontab.load().by_name('testjobrunnercron')[0].logs[0].status, 2)
        self.assertEquals(Crontab.load().by_name('testjobrunnercron')[0].logs[0].messages, [u'warn'])
        transaction.commit()
        gsm.unregisterAdapter(SimpleRunnerWithWarn, name=self.cron.name)
        transaction.commit()

        #
        # register an adapter with trivial code
        # which raise a failure
        #
        gsm.registerAdapter(FailureRunner, name=self.cron.name)
        transaction.commit()
        ret = runJob(self.portal, self.cron)
        self.assertEquals(
            ret,
            (0, [u'foo'], self.cron.uid, ('', 'plone')))
        gsm.unregisterAdapter(FailureRunner)
        transaction.commit()
        self.assertEquals(Crontab.load().by_name('testjobrunnercron')[0].logs[0].status, 0)
        self.assertEquals(Crontab.load().by_name('testjobrunnercron')[0].logs[0].messages, [u'foo'])
        gsm.unregisterAdapter(FailureRunner, name=self.cron.name)
        transaction.commit()

        #
        # register an adapter with trivial code
        # no failure / registered locally
        #
        ret = runJob(self.portal, self.cron)
        self.assertEquals(Crontab.load().by_name('testjobrunnercron')[0].logs[0].status, 3)
        psm.registerAdapter(LocalSimpleRunner, name=self.cron.name)
        transaction.commit()
        ret = runJob(self.portal, self.cron)
        self.assertEquals(_results, [1, 2, 3])
        self.assertEquals(Crontab.load().by_name('testjobrunnercron')[0].logs[0].messages, [u'local'])
        psm.unregisterAdapter(LocalSimpleRunner, name=self.cron.name)
        transaction.commit()
        self.cron.name = u'testcron'
        self.cron.save() 
        transaction.commit()

    def test_crontab_runjob_pathrun(self):
        # a job withtout any utility attached must run as NOTRUN
        # even if it is a NOOP
        [self.layer['queue'].remove(a) for a in self.layer['queue']]
        self.cron.name = u'testjobrunnercron_path'
        self.cron.save()
        ret = runJob(self.portal, self.cron)
        self.assertEquals(Crontab.load().by_name('testjobrunnercron_path')[0].logs[0].status, 3)
        #
        # don't register adapter. Instead create simple python script and cron.name path to script
        #
        txt = "context.result.append(1)"
        ps = self._newPS(txt, {'name_context': 'context'})
        # zope can't create use unicode ids
        self.portal[self.cron.name.encode('ascii')] = ps
        self.portal.result = []

        transaction.commit()
        ret = runJob(self.portal, self.cron)
        self.assertEquals(
            ret,
            (1, [], self.cron.uid, ('', 'plone')))
        self.assertEquals(self.portal.result, [1])
        transaction.commit()

        #
        # same with logs
        #
        txt = "context.result.append(context.result[-1]+1); return 'warn'"
        self.portal._getOb(self.cron.name.encode('ascii')).write(txt)
        transaction.commit()
        ret = runJob(self.portal, self.cron)
        self.assertEquals(
            ret,
            (2, [u'warn'], self.cron.uid, ('', 'plone')))
        self.assertEquals(self.portal.result, [1, 2])
        self.assertEquals(Crontab.load().by_name('testjobrunnercron_path')[0].logs[0].status, 2)
        self.assertEquals(Crontab.load().by_name('testjobrunnercron_path')[0].logs[0].messages, [u'warn'])
        transaction.commit()

        #
        # register an adapter with trivial code
        # which raise a failure
        #
        txt = "raise Exception('foo')"
        self.portal._getOb(self.cron.name.encode('ascii')).write(txt)
        transaction.commit()
        ret = runJob(self.portal, self.cron)
        self.assertEquals(
            ret,
            (0, [u'foo'], self.cron.uid, ('', 'plone')))
        transaction.commit()
        self.assertEquals(Crontab.load().by_name('testjobrunnercron_path')[0].logs[0].status, 0)
        self.assertEquals(Crontab.load().by_name('testjobrunnercron_path')[0].logs[0].messages, [u'foo'])

        #
        # add a script to a folder
        #
        txt = "context.result.append(context.result[-1]+1)"
        ps = self._newPS(txt, {'name_context': 'context'})
        self.portal['test-folder']['test_in_folder'] = ps
        self.cron.name = u'test-folder/test_in_folder'
        self.cron.save()
        ret = runJob(self.portal, self.cron)
        transaction.commit()
        self.assertEquals(
            ret,
            (1, [], self.cron.uid, ('', 'plone')))
        self.assertEquals(self.portal.result, [1, 2, 3])
        transaction.commit()
        self.assertEquals(Crontab.load().by_name('test-folder/test_in_folder')[0].logs[0].status, 1)



def test_suite():
    return unittest.defaultTestLoader.loadTestsFromName(__name__)

