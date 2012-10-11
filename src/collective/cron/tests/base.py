import pytz
import datetime
import transaction
#from zc.async.testing import set_now, setUpDatetime, tearDownDatetime
from collective.cron.testing import set_now, setUpDatetime, tearDownDatetime
from collective.cron import crontab
from collective.cron.adapters import (
    manager,
    utils as autils,
)

import unittest2 as unittest

from collective.cron import testing as t

from plone.app.async.tests import base
from plone.testing.z2 import Browser


class TestCase(base.AsyncTestCase):
    layer = t.COLLECTIVE_CRON_FIXTURE
    def setUp(self):
        super(TestCase, self).setUp()
        self.setRoles(['CollectiveCron'])
        self.queue = self.layer['queue']
        set_now(datetime.datetime(2008, 1, 1, 1, 1, tzinfo=pytz.UTC))
        transaction.commit()

    def tearDown(self):
        transaction.commit()
        noecho = [self.queue.remove(j) for j in self.queue]
        super(TestCase, self).tearDown()

class SimpleTestCase(TestCase):
    layer = t.COLLECTIVE_CRON_SIMPLE
    def setUp(self):
        pass

    def tearDown(self):
        pass

class IntegrationTestCase(TestCase):
    """Integration base TestCase."""
    layer = t.COLLECTIVE_CRON_INTEGRATION_TESTING
    def setUp(self):
        TestCase.setUp(self)
        self.crontab = self.layer['crontab']
        self.cron = self.layer['cron']
        self.crontab_manager = self.layer['crontab_manager']
        self.cron_manager = self.layer['cron_manager']
        self.cron_utils = self.layer['cron_utils']
        transaction.commit()

class FunctionalTestCase(IntegrationTestCase):
    """Functionnal base TestCase."""
    layer = t.COLLECTIVE_CRON_FUNCTIONAL_TESTING

# vim:set et sts=4 ts=4 tw=80:
