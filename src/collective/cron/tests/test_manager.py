import datetime
import unittest
import pytz

from zope.annotation.interfaces import IAttributeAnnotatable, IAnnotations
from zope.component import getUtility
from zope.event import notify
from zope import interface
from zope.lifecycleevent import ObjectModifiedEvent
import transaction
from zc.async.testing import set_now, wait_for_result

from plone.app.async.interfaces import IAsyncService
from plone.app.async.interfaces import QueueReady

from collective.cron.tests import base
from collective.cron import interfaces as i
from collective.cron.config import RESULTS_FOLDER

class QueueTest(base.TestCase):
    def test_start(self):
        """test the event propagation procedure
            backend.activated + cron
            -> jobmanager
            -> runjob
            -> IJobRunner(backend).run
            -> on return: IBackendLogger.log
        """
        async, queue, g = self.async, self.queue, self.g
        nextR = datetime.datetime(2008, 1, 1, 3, 1, tzinfo=pytz.UTC)
        nextE = datetime.datetime(2008, 1, 1, 5, 1, tzinfo=pytz.UTC)
        transaction.commit()
        # test that without cron imputed the job cannot be active.
        notify(ObjectModifiedEvent(g))
        set_now(nextR)
        transaction.commit()
        jobs = [a for a in queue]
        self.assertEquals( len(queue), 1)
        wait_for_result(jobs[0], 500)
        result = g[RESULTS_FOLDER][g[RESULTS_FOLDER].objectIds()[0]]
        self.assertEquals(result.status, 'WARN')
        self.assertEquals(result.errors, ['foo'])

    def test_job_present_methods(self):
        """Test the *_present API methods"""
        async, queue, g = self.async, self.queue, self.g
        self.folder.invokeFactory('SomeScrap', 'gg')
        og = self.folder['gg']
        og.user = 'foo'
        og.password = 'bar'
        og.activated = True
        og.periodicity = '%s * * * * *' %','.join([repr(a) for a in  range(0,60)])
        nextR = datetime.datetime(2008, 1, 1, 3, 1, tzinfo=pytz.UTC)
        nextE = datetime.datetime(2008, 1, 1, 5, 1, tzinfo=pytz.UTC)
        # test that without cron imputed the job cannot be active.
        notify(ObjectModifiedEvent(g))
        notify(ObjectModifiedEvent(og))
        set_now(nextR)
        jobs = [a for a in queue]
        transaction.commit()
        self.assertEquals( len(queue), 2)
        m = i.IBackendJobManager(self.g)
        om = i.IBackendJobManager(og)
        self.assertEquals('/'.join(m.get_job_present().args[0]), '/plone/Members/test_user_1_/g')
        self.assertEquals('/'.join(om.get_job_present().args[0]), '/plone/Members/test_user_1_/gg')
        self.assertTrue(om.is_job_present())
        self.assertTrue(m.is_job_present())
        m.remove_jobs()
        self.assertTrue(om.is_job_present())
        self.assertFalse(m.is_job_present())
        om.remove_jobs()
        self.assertFalse(om.is_job_present())
        self.assertFalse(m.is_job_present())
        self.assertTrue(m.get_job_present() is None)
        self.assertTrue(om.get_job_present() is None)

    def test_setup_plonesites(self):
        """After the skin product installation,
        we must have stocked on the queue some infos about the running plonesite around
        """
        async, queue, g = self.async, self.queue, self.g
        nextR = datetime.datetime(2008, 1, 1, 3, 1, tzinfo=pytz.UTC)
        nextE = datetime.datetime(2008, 1, 1, 5, 1, tzinfo=pytz.UTC)
        transaction.commit()
        # test that without cron imputed the job cannot be active.
        notify(ObjectModifiedEvent(g))
        set_now(nextR)
        transaction.commit()
        jobs = [a for a in queue]
        wait_for_result(jobs[0], 500)
        async = getUtility(IAsyncService)
        queue = async.getQueues()['']
        interface.alsoProvides(queue, IAttributeAnnotatable)
        infos = IAnnotations(queue)
        self.assertEquals(
            infos,
            {'pacron.adapters.manager': {'plone': [('unnamed', '/plone')]}}
        )

    def test_startup_relaunch(self):
        """Test the startup event which needs to relaunch all jobs
        on backends which are actived"""
        async, queue, g = self.async, self.queue, self.g
        nextR = datetime.datetime(2008, 1, 1, 3, 1, tzinfo=pytz.UTC)
        notify(ObjectModifiedEvent(g))
        set_now(nextR)
        transaction.commit()
        jobs = [a for a in queue]
        wait_for_result(jobs[0], 500)
        transaction.commit()
        for i in self.queue:
            self.queue.remove(i)
        transaction.commit()
        set_now(datetime.datetime(2008, 1, 1, 13, 0, tzinfo=pytz.UTC))
        transaction.commit()
        e = QueueReady(queue)
        self.assertEquals(len(queue), 0)
        notify(e)
        set_now(datetime.datetime(2008, 1, 1, 15, 0, tzinfo=pytz.UTC))
        transaction.commit()
        e = QueueReady(queue)
        notify(e)
        set_now(datetime.datetime(2008, 1, 1, 17, 0, tzinfo=pytz.UTC))
        transaction.commit()
        notify(e)
        transaction.commit()
        self.assertEquals(len(queue), 1)
        import time
        time.sleep(6)

def test_suite():
    return unittest.defaultTestLoader.loadTestsFromName(__name__)

