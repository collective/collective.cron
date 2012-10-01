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
from plone.app.async import interfaces as pai
from plone.app.async.interfaces import IAsyncService
from plone.app.async.service import _executeAsUser
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
def test_job(*args, **kwargs):
    time.sleep(2)
    _runned.append(datetime.datetime.now())


class QueueTest(base.IntegrationTestCase):
    def setUp(self):
        base.IntegrationTestCase.setUp(self)
        self.cqueue = self.layer['cron_queue']
        self.marker = self.cqueue.marker
        self.cron_manager = self.layer['cron_manager']
        _runned = []
        _finish = False
        [self.queue.remove(j) for j in self.queue]

    def tearDown(self):
        base.IntegrationTestCase.tearDown(self)
        _runned = []
        _finish = True
        [self.queue.remove(j) for j in self.queue]
        for uid in self.crontab.crons.keys():
            if not uid == self.cron.uid:
                del self.crontab.crons[uid]

    def make_simpleOne(self, job_infos=None):
        if not job_infos:
            job_infos = self.cqueue.get_job_infos()
        job = self.async.queueJobWithDelay(
            None,
            job_infos['begin_after'],
            job_infos['job'],
            job_infos['context'],
            *job_infos['args'],
            **job_infos['kwargs']
        )
        return job, job_infos

    def test_pasync_queue_properties(self):
        self.assertTrue(self.cqueue.job is crontab.runJob)
        self.assertTrue(pai.IAsyncService.providedBy(self.cqueue.service))
        self.assertTrue(zai.IQueue.providedBy(self.cqueue.queue))
        self.assertTrue(isinstance(self.cqueue.jobs, list))

    def test_pasync_queue_register_job(self):
        self.assertTrue(self.cqueue.register_job(
            {'begin_after':None,
             'job': test_job,
             'context': self.folder,
             'args':tuple(),
             'kwargs':{}
            }
        ))
        self.assertEquals(len(self.cqueue.queue), 1)
        noecho = [self.cqueue.queue.remove(j) for j in self.cqueue.queue]
        self.assertEquals(len(self.cqueue.queue), 0)

    def test_pasync_queue_remove_job(self):
        self.assertTrue(self.cqueue.register_job(
            {'begin_after':None,
             'job': test_job,
             'context': self.folder,
             'args':tuple(),
             'kwargs':{}
            }
        ))
        self.assertEquals(len(self.cqueue.queue), 1)
        job = [j for j in self.cqueue.queue][0]
        self.cqueue.remove(job)
        self.assertEquals(len(self.cqueue.queue), 0)

    def test_pasync_queue_get_job_infos(self):
        infos = self.cqueue.get_job_infos()
        infos2 = self.cqueue.get_job_infos(datetime.datetime(2008,1,1),
                                           job=test_job)
        self.assertEquals(infos['kwargs'], {})
        self.assertEquals(infos['args'], ())
        self.assertEquals(infos['begin_after'], None)
        self.assertEquals(infos['job'], manager.runJob)
        self.assertEquals(infos['context'], self.portal)
        self.assertEquals(infos2['kwargs'], {})
        self.assertEquals(infos2['args'], ())
        self.assertEquals(infos2['begin_after'], datetime.datetime(2008, 1, 1, 0, 0))
        self.assertEquals(infos2['job'], test_job)
        self.assertEquals(infos2['context'], self.portal)

    def test_pasync_queue_get_job_present(self):
        # a job without begin_after, first of all
        job, job_infos = self.make_simpleOne()
        job1 = self.cqueue.get_job_present(job_infos)
        self.assertTrue(job is job1)
        self.queue.remove(job)
        job1 = self.cqueue.get_job_present(job_infos)
        self.assertTrue(job1 is None)

    def test_pasync_queue_compare_job(self):
        # a job without begin_after, first of all
        job, job_infos = self.make_simpleOne(self.cron_manager.get_job_infos())
        self.assertTrue(self.cqueue.compare_job(job, job_infos))
        #
        job1_infos = job_infos.copy()
        job1_infos['begin_after'] = datetime.datetime(2009,1,1)
        self.assertFalse(self.cqueue.compare_job(job, job1_infos))
        #
        job1_infos = job_infos.copy()
        job1_infos['kwargs'] = {1:2}
        self.assertFalse(self.cqueue.compare_job(job, job1_infos))
        #
        job1_infos = job_infos.copy()
        job1_infos['job'] = 'foo'
        self.assertFalse(self.cqueue.compare_job(job, job1_infos))
        #
        job1_infos = job_infos.copy()
        job1_infos['context'] = self.folder
        self.assertFalse(self.cqueue.compare_job(job, job1_infos))
        #
        job1_infos = job_infos.copy()
        job1_infos['context'] = self.folder
        self.assertFalse(self.cqueue.compare_job(job, job1_infos))
        #
        job1_infos = job_infos.copy()
        othercron = crontab.Cron.load(
            job1_infos['args'][0].dump()
        )
        self.cron.crontab.add_cron(othercron)
        othercron.uid = job1_infos['args'][0].uid
        job1_infos['args'] = (othercron,)
        self.assertTrue(self.cqueue.compare_job(job, job1_infos))
        #
        self.queue.remove(job)

    def test_pasync_queue_is_job_present(self):
        # a job without begin_after, first of all
        job, job_infos = self.make_simpleOne()
        self.assertTrue(self.cqueue.is_job_present())
        self.queue.remove(job)
        self.assertFalse(self.cqueue.is_job_present())

    def test_pasync_queue_get_job_status(self):
        job, job_infos = self.make_simpleOne()
        self.assertTrue(
            self.cqueue.get_job_status()
            == zai.PENDING
        )
        job_infos['args'] = ('foo',)
        self.assertTrue(
            self.cqueue.get_job_status(
                job_infos)
            is None
        )

    def test_pasync_queue_is_job_pending_running_and_finished(self):
        transaction.commit()
        job_infos = self.cqueue.get_job_infos(
            job = test_job,
        )
        job, job_infos = self.make_simpleOne(job_infos)
        self.assertTrue(
            self.cqueue.is_job_pending(job_infos)
        )                                
        self.assertFalse(
            self.cqueue.is_job_running(job_infos)
        )
        transaction.commit()
        wait_for_start(job)
        self.assertTrue(
            self.cqueue.is_job_running(job_infos)
        )
        wait_for_result(job)
        self.assertTrue(
            self.cqueue.is_job_finished(job_infos)
        )
        fjob = self.cqueue.get_job_present(job_infos)
        # run another job and verify that the related one is
        # this job and not the first run
        now = (datetime.datetime.now() +
               datetime.timedelta(minutes=5))
        set_now(now)
        transaction.commit()
        job1_infos = self.cqueue.get_job_infos(
            job = test_job,
        )
        job1, job1_infos = self.make_simpleOne(job1_infos)
        self.assertFalse(
            self.cqueue.is_job_running(job1_infos)
        )
        transaction.commit()
        wait_for_start(job1)
        self.assertTrue(
            self.cqueue.is_job_running(job1_infos)
        )
        wait_for_result(job1)
        self.assertTrue(
            self.cqueue.is_job_finished(job1_infos)
        )
        # we cant determine which was first anyway, those are the same job
        ffjob = self.cqueue.get_job_in_agents(job_infos)
        sjob  = self.cqueue.get_job_in_agents(job1_infos)
        self.assertTrue(ffjob.key == sjob.key)
        self.assertTrue(job1.key == sjob.key)

    def test_pasync_queue_remove_jobs(self):
        transaction.commit()
        job_infos = self.cqueue.get_job_infos(
            job = test_job,
        )
        job1, job_infos1 = self.make_simpleOne()
        job, job_infos = self.make_simpleOne(job_infos)
        self.assertEquals(len(self.queue), 2)
        self.cqueue.remove_jobs(job_infos)
        self.assertEquals(len(self.queue), 1)
        self.queue.remove(job1)
        self.assertEquals(len(self.queue), 0)

    def test_pasync_queue_cleanup_before_job(self):
        old_now = datetime.datetime.now()
        job, job_infos = self.make_simpleOne(self.cqueue.get_job_infos())
        self.assertEquals(len(self.queue), 1)
        self.cqueue.cleanup_before_job(job_infos)
        self.assertEquals(len(self.queue), 1)
        self.cqueue.cleanup_before_job(job_infos, force=True)
        self.assertEquals(len(self.queue), 0)
        job, job_infos = self.make_simpleOne(self.cqueue.get_job_infos())
        self.assertEquals(len(self.queue), 1)
        dt = job.begin_after
        dt_minus_5 = dt - datetime.timedelta(minutes=5)
        dt_plus_5 = dt + datetime.timedelta(minutes=5)
        job_infos['begin_after'] = dt_minus_5
        self.cqueue.cleanup_before_job(job_infos, force=True)
        self.assertEquals(len(self.queue), 0)
        job, job_infos = self.make_simpleOne(self.cqueue.get_job_infos())
        set_now(dt_plus_5)
        job_infos['begin_after'] = dt
        self.cqueue.cleanup_before_job(job_infos, force=True)
        self.assertEquals(len(self.queue), 0)
        job_infos = self.cron_manager.get_job_infos()
        job, job_infos = self.make_simpleOne(job_infos)
        cron = job.args[5]
        ncron = crontab.Cron(**cron.dump())
        self.cqueue.cleanup_before_job(job_infos)
        self.assertEquals(len(self.queue), 1)  
        ncron.name = u'othercron'
        job_infos['args'] = [ncron]
        self.cqueue.cleanup_before_job(job_infos)
        self.assertEquals(len(self.queue), 0) 
        set_now(old_now)

    def test_pasync_queue_get_job_infos_from_queue(self):
        self.assertEquals(self.cqueue.get_job_infos_from_queue(), [])
        job1_infos = self.cqueue.get_job_infos(job = test_job)
        job1, job_infos1 = self.make_simpleOne(job1_infos)
        job2_infos = self.cqueue.get_job_infos(job =_executeAsUser)
        job2, job_infos2 = self.make_simpleOne(job2_infos)
        job3_infos = self.cqueue.get_job_infos()
        job3, job_infos3 = self.make_simpleOne(job3_infos)
        infos = self.cqueue.get_job_infos_from_queue()
        self.assertEquals(infos[0]['job'], _executeAsUser)
        self.assertFalse(infos[0]['begin_after'] is None)
        self.assertEquals(infos[0]['kwargs'], {})
        self.assertEquals(infos[0]['context'], self.portal)
        self.assertEquals(len(infos[0]['args']), 5)
        self.assertEquals(infos[1]['job'], _executeAsUser)
        self.assertFalse(infos[1]['begin_after'] is None)
        self.assertEquals(infos[1]['kwargs'], {})
        self.assertEquals(infos[1]['context'], self.portal)
        self.assertEquals(len(infos[1]['args']), 5)
        self.assertEquals(infos[2]['job'], _executeAsUser)
        self.assertFalse(infos[2]['begin_after'] is None)
        self.assertEquals(infos[2]['kwargs'], {})
        self.assertEquals(infos[2]['context'], self.portal)
        self.queue.remove(job1)
        self.queue.remove(job2)
        self.queue.remove(job3)

    def test_pasync_startup_relaunch(self):
        """Test the startup event which needs to relaunch
        all jobs which are actived"""
        old_now = datetime.datetime.now()
        nextR = datetime.datetime(2008, 1, 1, 3, 1)
        set_now(pytz.UTC.localize(nextR))
        self.assertTrue(self.marker.marked)
        self.crontab.save()
        [self.queue.remove(j) for j in self.queue]
        e = QueueReady(self.queue)
        self.assertEquals(len(self.queue), 0)
        notify(e)
        dt1 = datetime.datetime(2008, 1, 1, 15, 0)
        set_now(pytz.UTC.localize(dt1))
        transaction.commit()
        e = QueueReady(self.queue)
        notify(e)
        dt2 = datetime.datetime(2008, 1, 1, 17, 0)
        set_now(pytz.UTC.localize(dt2))
        transaction.commit()
        notify(e)
        transaction.commit()
        self.assertEquals(len(self.queue), 1)
        [self.queue.remove(j) for j in self.queue]
        set_now(old_now)
        transaction.commit()

def test_suite():
    return unittest.defaultTestLoader.loadTestsFromName(__name__)

