import time
import datetime
import unittest
import pytz

from zope.annotation.interfaces import IAttributeAnnotatable, IAnnotations
from zope.component import getUtility
from zope.event import notify
from zope import interface
from zope.lifecycleevent import ObjectModifiedEvent
import transaction
from zc.async.testing import set_now, wait_for_result, wait_for_start

from zc.async import interfaces as zai
from plone.app.async.interfaces import IAsyncService
from plone.app.async.interfaces import QueueReady
from zope.annotation.interfaces import IAttributeAnnotatable, IAnnotations

from collective.cron.tests import base
from collective.cron import interfaces as i
from collective.cron.interfaces import RESULTS_FOLDER
from collective.cron.adapters import (
    manager,
)

from collective.cron import crontab
_finish = True
_runned = []
def test_job(*args, **kwargs): # pragma: no cover  
    time.sleep(2)
    _runned.append(datetime.datetime.now())


class ManagerTest(base.IntegrationTestCase):
    def setUp(self):
        base.IntegrationTestCase.setUp(self)
        self.cqueue = self.cron_manager.queue
        self.ctqueue = self.crontab_manager.queue
        _runned = []
        _finish = False
        self.crontab.save()
        [self.queue.remove(j) for j in self.queue]
        transaction.commit()

    def tearDown(self):
        base.IntegrationTestCase.tearDown(self)
        _runned = []
        _finish = True
        self.crontab.save()
        [self.queue.remove(j) for j in self.queue]
        transaction.commit()

    def make_simpleOne(self, job_infos=None):
        if not job_infos:
            job_infos = self.cron_manager.get_job_infos()
        job = self.async.queueJobWithDelay(
            None,
            job_infos['begin_after'],
            job_infos['job'],
            job_infos['context'],
            *job_infos['args'],
            **job_infos['kwargs']
        )
        return job, job_infos

    def test_cron_get_job_infos(self):
        infos = self.cron_manager.get_job_infos(None,None,None,'foo', 'bar')
        infos2 = self.cron_manager.get_job_infos(datetime.datetime(2008,1,1),
                                                job=test_job)
        self.assertEquals(infos['kwargs'], {})
        self.assertEquals(infos['args'], (self.cron, 'foo', 'bar'))
        self.assertEquals(infos['begin_after'], None)
        self.assertEquals(infos['job'], crontab.runJob)
        self.assertEquals(infos['context'], self.portal)
        self.assertEquals(infos2['kwargs'], {})
        self.assertEquals(infos2['args'], ())
        self.assertEquals(infos2['begin_after'], datetime.datetime(2008, 1, 1, 0, 0))
        self.assertEquals(infos2['job'], test_job)
        self.assertEquals(infos2['context'], self.portal)

    def test_cron_register_job(self):
        transaction.commit()
        now = pytz.UTC.localize(datetime.datetime(2008,1,4))
        set_now(now)
        transaction.commit()
        ba = pytz.UTC.localize(datetime.datetime(2008,1,4))
        r = self.cron_manager.register_job(begin_after = ba)
        self.assertTrue(r)
        # force a new run which will replace our cron job
        # as it will be runned sooner
        r = self.cron_manager.register_job(force=True)
        self.assertEquals(len(self.queue), 1)
        self.assertEquals(self.queue[0].begin_after, ba)
        self.cron_manager.remove_jobs()
        self.assertEquals(len(self.queue), 0)
        # if we deactivate the crontab or the cron
        # we will not have any job queued
        self.cron.activated = False
        r = self.cron_manager.register_job()
        self.assertEquals(len(self.queue), 0)
        self.assertTrue(r == False)
        self.assertEquals(len(self.queue), 0)
        self.cron.activated = True
        self.crontab.activated = False
        r = self.cron_manager.register_job()
        self.assertTrue(r == False)
        self.assertEquals(len(self.queue), 0) 
        # first resiter a job
        # then register a job with a smaller datetime delay
        self.crontab.activated = True
        r = self.cron_manager.register_job()
        self.cron.periodicity = u'1 23 * * *'
        r = self.cron_manager.register_job()
        self.cron.periodicity = u'1 22 * * *'
        r = self.cron_manager.register_job()
        job3 = self.queue[-1]
        self.assertTrue(self.cron.next, job3.begin_after)
        [self.queue.remove(j) for j in self.queue]

    def test_cron_register_or_remove(self):
        transaction.commit()
        now = pytz.UTC.localize(datetime.datetime(2008,1,4))
        set_now(now)
        self.crontab.activated = self.cron.activated = True
        transaction.commit()
        ret = self.cron_manager.register_or_remove()
        job = self.queue[-1]
        self.assertTrue(self.queue[0] is job)
        self.cron.activated = False
        self.assertTrue(ret[0])
        ret = self.cron_manager.register_or_remove()
        self.assertEquals(len(self.queue), 0)
        self.assertTrue(not ret[0])
        self.cron.activated = True
        ret = self.cron_manager.register_or_remove()
        self.assertTrue(ret[0])
        job = self.queue[-1]
        self.assertTrue(self.queue[0] is job)
        self.cron.crontab.activated = False
        ret = self.cron_manager.register_or_remove()
        self.assertTrue(not ret[0])
        self.assertEquals(len(self.queue), 0)

    def test_cron_remove_jobs(self):
        transaction.commit()
        job_infos = self.cron_manager.get_job_infos(
            job = test_job,
        )
        job1, job_infos1 = self.make_simpleOne()
        job, job_infos = self.make_simpleOne(job_infos)
        self.assertEquals(len(self.queue), 2)
        self.cron_manager.remove_jobs(job_infos)
        self.assertEquals(len(self.queue), 1)
        self.queue.remove(job1)
        self.assertEquals(len(self.queue), 0)

    def test_crontab_is_job_to_be_removed(self):
        transaction.commit()
        self.cron_manager.register_job()
        job = self.queue[-1]
        infos = self.ctqueue.get_job_infos_from_job(job)
        self.assertFalse(
            self.crontab_manager.is_job_to_be_removed(infos)
        )
        uid = self.cron.uid
        self.cron.uid = u'foobar'
        self.assertTrue(
            self.crontab_manager.is_job_to_be_removed(infos)
        )
        self.cron.uid = uid
        infos['args'][4] = None
        self.assertFalse(
            self.crontab_manager.is_job_to_be_removed(infos)
        )             

    def test_crontab_synchronize_crontab_with_queue(self):
        transaction.commit()
        jbi = self.cron_manager.get_job_infos(job = test_job)
        # register a job which is not a cron and must not be removed
        # when we synchronize
        jb, jbi = self.make_simpleOne(jbi)
        self.assertFalse(
            self.crontab_manager.is_job_to_be_removed(
                self.ctqueue.get_job_infos_from_job(jb)
            )
        )
        # job will be deleted from the cron, must be wiped
        cr1 = crontab.Cron.load(self.cron.dump())
        self.crontab.add_cron(cr1)
        #
        cr2 = crontab.Cron.load(self.cron.dump())
        self.crontab.add_cron(cr2)
        cr3 = crontab.Cron.load(self.cron.dump())
        self.crontab.add_cron(cr3)
        cr4 = crontab.Cron.load(self.cron.dump())
        self.crontab.add_cron(cr4) 
        # first add to the queue an invalid cron
        # in the sense that it will be in the queue
        # but not anymore in the crontab
        manager.CronManager(self.portal, cr1).register_job()
        job1 = self.queue[-1]
        cr1_uid = cr1.uid
        del self.crontab.crons[cr1.uid]
        cr2.uid = u"foofoobar"
        cr3.uid = u"foobar"
        self.assertTrue(
            self.crontab_manager.is_job_to_be_removed(
                self.ctqueue.get_job_infos_from_job(job1)
            )
        )
        # job2 is registered manually
        manager.CronManager(self.portal, cr2).register_job()
        job2 = self.queue[-1]
        # job4 will be registered automaticly via the manager
        # but not enabled
        cr4.activated = False
        # job3 will be registered automaticly via the manager
        jobs = self.crontab_manager.synchronize_crontab_with_queue()
        self.assertTrue(len(jobs['deleted']), 1)
        self.assertEquals(jobs['deleted'][0]['args'][5].uid, cr1_uid)
        self.assertEquals(len(jobs['jobs']), 4)
        self.assertEquals(jobs['jobs'][0]['activated'], True)
        self.assertEquals(jobs['jobs'][1]['activated'], True)
        self.assertEquals(jobs['jobs'][2]['activated'], True)
        self.assertEquals(jobs['jobs'][3]['activated'], False)
        self.assertEquals(jobs['jobs'][0]['cron'], self.cron)
        self.assertEquals(jobs['jobs'][1]['cron'], cr2)
        self.assertEquals(jobs['jobs'][2]['cron'], cr3)
        self.assertEquals(jobs['jobs'][3]['cron'], cr4)
        self.assertTrue(len(self.queue), 5)
        [self.queue.remove(j) for j in self.queue]


def test_suite():
    return unittest.defaultTestLoader.loadTestsFromName(__name__)

