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


class MarkerTest(base.IntegrationTestCase):
    def setUp(self):
        base.IntegrationTestCase.setUp(self)
        self.marker = self.layer['crontab_marker']
        self.aqueue = i.IAnnotedQueue(self.marker.queue)
        self.marker.mark_crontab_aware()

    def tearDown(self):
        base.IntegrationTestCase.tearDown(self)
        self.marker.mark_crontab_aware()

    def test_pasync_marker_unmark(self):
        self.assertEquals(self.aqueue.annotations,
                          {'plone': ['/plone']})
        self.marker.unmark_crontab_aware()
        self.assertEquals(self.aqueue.annotations,
                          {'plone': []})

    def test_pasync_marker_mark(self):
        self.marker.unmark_crontab_aware()
        self.marker.mark_crontab_aware()
        self.assertEquals(self.aqueue.annotations,
                          {'plone': ['/plone']})

    def test_pasync_marker_key(self):
        self.assertEquals(self.marker.key, '/plone')

    def test_pasync_marker_marked(self):
        self.marker.unmark_crontab_aware()
        self.assertFalse(self.marker.marked)
        self.marker.mark_crontab_aware()
        self.assertTrue(self.marker.marked)

def test_suite():
    return unittest.defaultTestLoader.loadTestsFromName(__name__)

