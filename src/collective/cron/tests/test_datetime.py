import datetime
import pytz
import unittest2 as unittest
from pprint import pprint, pformat

from zope.schema.interfaces import RequiredMissing, ConstraintNotSatisfied
from zope import schema, component

from collective.cron.tests import base
from collective.cron import crontab, utils
from collective.cron import interfaces as i
from collective.cron.adapters import registry
import os
J = os.path.join

from collective.cron import testing
import pytz


counter = 0

class DTtest(base.SimpleTestCase):
    def setUp(self):
        base.SimpleTestCase.setUp(self)
        testing.setUpDatetime()

    def tearDown(self):
        base.SimpleTestCase.tearDown(self)
        testing.tearDownDatetime()

    def test_dt_datetime(self):
        paris = pytz.timezone('Europe/Paris')
        ny = pytz.timezone('America/New_York')
        utc = pytz.timezone('UTC')
        ldt = datetime.datetime.now()
        udt = utils.to_tz(ldt, utc)
        ndt = utils.to_tz(ldt, ny)
        pdt = utils.to_tz(ldt, paris)
        self.assertTrue(
            (udt.replace(tzinfo=None) - pdt.replace(tzinfo=None)
            ).total_seconds()  / 3600 == -2)
        self.assertTrue(
            (udt.replace(tzinfo=None) - ndt.replace(tzinfo=None)
            ).total_seconds()  / 3600 == 4)
        self.assertTrue(utils.to_tz(ndt, ny) == ndt)
        self.assertTrue(utils.to_tz(ndt, paris) == pdt)
        self.assertTrue(utils.to_tz(ndt, utc) == udt)
        self.assertTrue(utils.to_tz(pdt, ny) == ndt)
        self.assertTrue(utils.to_tz(pdt, paris) == pdt)
        self.assertTrue(utils.to_tz(pdt, utc) == udt)
        self.assertTrue(utils.to_tz(udt, ny) == ndt)
        self.assertTrue(utils.to_tz(udt, paris) == pdt)
        self.assertTrue(utils.to_tz(udt, utc) == udt)

    def test_utcnow(self):
        now = datetime.datetime.now()
        utcnow = now.utcnow()
        putcnow = datetime.datetime.now(pytz.UTC)
        self.assertTrue(
             utcnow - putcnow.replace(tzinfo=None) < datetime.timedelta(seconds=60)
        )

def test__suite(): # pragma: no cover
    return unittest.defaultTestLoader.loadTestsFromName(__name__)


