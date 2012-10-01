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

from collective.cron.testing import (
    COLLECTIVE_CRON_SIMPLE,
    COLLECTIVE_CRON_FIXTURE as UNIT_TESTING,
    COLLECTIVE_CRON_INTEGRATION_TESTING as INTEGRATION_TESTING,
    COLLECTIVE_CRON_FUNCTIONAL_TESTING as FUNCTIONAL_TESTING,
    COLLECTIVE_CRON_SELENIUM_TESTING as SELENIUM_TESTING,
)

from plone.app.async.tests import base
from plone.testing.z2 import Browser


class TestCase(base.AsyncTestCase):
    layer = UNIT_TESTING
    def setUp(self):
        super(TestCase, self).setUp()
        setUpDatetime()
        self.setRoles(['CollectiveCron'])
        self.queue = self.layer['queue']
        set_now(datetime.datetime(2008, 1, 1, 1, 1, tzinfo=pytz.UTC))
        transaction.commit()

    def tearDown(self):
        noecho = [self.queue.remove(j)
                  for j in self.queue]
        tearDownDatetime()
        super(TestCase, self).tearDown()

class SimpleTestCase(TestCase):
    layer = COLLECTIVE_CRON_SIMPLE
    def setUp(self):
        setUpDatetime()
        set_now(datetime.datetime(2008, 1, 1, 1, 1, tzinfo=pytz.UTC))

    def tearDown(self):
        tearDownDatetime()

class IntegrationTestCase(TestCase):
    """Integration base TestCase."""
    layer = INTEGRATION_TESTING
    def setUp(self):
        TestCase.setUp(self)
        self.crontab = self.layer['crontab']
        self.cron = self.layer['cron']
        self.crontab_manager = self.layer['crontab_manager']
        self.cron_manager = self.layer['cron_manager']
        self.cron_utils = self.layer['cron_utils']

class FunctionalTestCase(IntegrationTestCase):
    """Functionnal base TestCase."""
    layer = FUNCTIONAL_TESTING

class SeleniumTestCase(TestCase):
    """Functionnal base TestCase."""
    layer = SELENIUM_TESTING
# vim:set et sts=4 ts=4 tw=80:
