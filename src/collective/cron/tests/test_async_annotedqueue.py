import time
import datetime
import unittest
import pytz

from zope.component import getUtility
from zope.event import notify
from zope import interface
import transaction
from zc.async.testing import set_now, wait_for_result, wait_for_start

from zc.async import interfaces as zai
from plone.app.async.interfaces import IAsyncService
from plone.app.async.interfaces import QueueReady
from zope.annotation.interfaces import IAttributeAnnotatable, IAnnotations

from collective.cron.tests import base
from collective.cron import interfaces as i


class AQueueTest(base.IntegrationTestCase):
    def setUp(self):
        base.IntegrationTestCase.setUp(self)
        self.marker = self.layer['crontab_marker']
        self.aqueue = i.IAnnotedQueue(self.marker.queue)
        [self.queue.remove(j) for j in self.queue]

    def tearDown(self):
        base.IntegrationTestCase.tearDown(self)
        [self.queue.remove(j) for j in self.queue]

    def test_pasync_queue_annotations(self):
        self.assertEquals(self.aqueue.annotations,
                          {'plone': [('unnamed', '/plone')]})

def test_suite():
    return unittest.defaultTestLoader.loadTestsFromName(__name__)

