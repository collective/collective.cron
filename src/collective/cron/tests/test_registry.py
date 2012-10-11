import datetime
import pytz
import unittest2 as unittest
from pprint import pprint, pformat

from zope.schema.interfaces import RequiredMissing, ConstraintNotSatisfied
from zope import schema, component

from collective.cron.tests import base
from collective.cron import crontab, utils
from collective.cron import interfaces as i
from collective.cron.adapters import registry, utils as autils
import os
J = os.path.join


class RegistryTest(base.IntegrationTestCase):
    def setUp(self):
        base.IntegrationTestCase.setUp(self)
        self.crontab.manager.cronsettings.crontab = []
        self.crontab.manager.cronsettings.activated = True

    def tearDown(self):
        base.IntegrationTestCase.tearDown(self)
        self.crontab.manager.cronsettings.crontab = []
        self.crontab.manager.cronsettings.activated = True

    def test_registry_objects_crontab_load_from_settings(self):
        self.crontab.manager.cronsettings.crontab = [u'foo']
        self.assertRaises(i.InvalidCrontab, crontab.Crontab.load, 'foo')
        self.crontab.manager.cronsettings.crontab = [u'[]']
        cr = crontab.Crontab.load()
        self.assertEquals(len(cr.crons), 0)

    def test_registry_objects_cron_save(self):
        crt = self.makeOne()
        dmp = crt.dump()
        sv = crt.save()
        self.assertTrue(
            crt.manager.crontab[0].startswith('{"')
        )
        # writing a little in the registered crontab
        crt.manager.crontab.append('{foo:bar}')
        llen = len(crt.manager.crontab)
        old_data = crt.dump()
        # edit one of the crons & save it back
        cron = crt.by_uid("1")
        cron.name = u"i_have_changed"
        crondata = cron.dump()
        cron.save()
        lllen = len(crt.manager.crontab)
        self.assertEquals(
            crontab.json.loads(crt.manager.crontab[0])['name'],
            crondata["name"])
        self.assertEquals(llen, lllen)
        crondata["uid"] = "notyet"
        crondata["name"] = "i_have_changed2"
        cron = crontab.Cron.load(crondata, crt)
        cron.save()
        llllen = len(crt.manager.crontab)
        self.assertEquals(
            crontab.json.loads(crt.manager.crontab[-1])['name'],
            crondata["name"])
        self.assertEquals(llen+1, llllen)

    def test_registry_objects_cron_delete(self):
        crt = self.makeOne()
        dmp = crt.dump()
        crondata = crt.by(uid="1")[0].dump()
        crondata["uid"] = "notyet"
        crondata["name"] = "i_have_changed2"
        cron = crontab.Cron.load(crondata, crt)
        sv = crt.save()
        llen = len(crt.manager.crontab)
        self.assertTrue("2" in crt.crons)
        self.assertTrue("notyet" in crt.crons)
        del crt.crons["2"]
        del crt.crons["notyet"]
        sv = crt.save()
        lllen = len(crt.manager.crontab)
        self.assertEquals(llen-2, lllen)
        self.assertTrue(not "2" in crt.crons)
        self.assertTrue(not "notyet" in crt.crons)

    def test_registry_objects_crontab__readonly_p(self):
        crt = self.makeOne()
        self.assertFalse(crt.read_only)
        self.assertFalse(crt.manager.read_only)
        crt.read_only = True
        self.assertTrue(crt.read_only)
        crt.manager.read_only
        self.assertTrue(crt.manager.read_only)

        crro = crontab.Crontab.load(read_only=True)
        self.assertTrue(crro.read_only)
        self.assertTrue(crro.manager.read_only)
        cr = crontab.Crontab.load(read_only=False)
        self.assertFalse(cr.read_only)
        self.assertFalse(cr.manager.read_only)

    def test_registry_objects_crontab__readonly_v_o(self):
        cr = crontab.Crontab(read_only=False)
        crro = crontab.Crontab(read_only=True)
        cron2 = self.makeOne().crons["1"]
        crro.add_cron(cron2)
        self.assertTrue(crro.activated)
        crro.activated = False
        self.assertEqual(len(crro.crons), 1)
        self.assertEqual(crro.manager.cronsettings.crontab, [])
        crro.save()
        self.assertTrue(crro.manager.cronsettings.activated)
        self.assertEqual(len(crro.crons), 1)
        self.assertEqual(len(crro.manager.cronsettings.crontab), 0)

    def test_registry_objects_crontab__readonly_v_w(self):
        cr = crontab.Crontab(read_only=False)
        cron1 = self.makeOne().crons["1"]
        cr.add_cron(cron1)
        self.assertTrue(cr.activated)
        cr.activated = False
        self.assertEqual(len(cr.crons), 1)
        self.assertEqual(cr.manager.cronsettings.crontab, [])
        cr.save()
        self.assertFalse( cr.manager.cronsettings.activated)
        self.assertEqual(len(cr.crons), 1)
        self.assertEqual(len(cr.manager.cronsettings.crontab), 1)
        cr.activated = False
        cr.save()

    def test_registry_pasync_crontabdeleted_must_delete_job(self):
        oldvalue = self.crontab.manager.cronsettings.crontab
        job, job_infos = self.make_job(self.cron_manager.get_job_infos())
        self.assertEquals(len(self.queue), 1)
        olduid = self.cron.uid
        del self.crontab.crons[self.cron.uid]
        # ,fire the delete event
        self.crontab.save()
        self.assertEquals(len(self.queue), 0)
        self.crontab.add_cron(self.cron)
        # refire an event re registering the job
        self.crontab.save()
        self.assertEquals(len(self.queue), 1)
        self.assertEquals(olduid, self.cron.uid)
        self.assertEquals(oldvalue, self.crontab.manager.cronsettings.crontab)

    def make_job(self, job_infos=None): # pragma: no cover 
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

    def makeOne(self): # pragma: no cover 
        logs = [
            {"date":"2008-01-01 1:1:1",
              "status":1,
              "messages":[u'2']},
            {"date":"2008-01-01 1:1:1",
             "status":1,
              "messages":[u'2']},
        ]
        env = {'foo': 'bar'}
        data = {
            "uid":"1",
            "name":"1",
            "periodicity": "1 * * * *",
            "activated": "1",
            "logs": logs,
            "environ": env,
        }
        data2 = data.copy()
        data2["uid"] = data2["id"] = "2"
        data3 = data.copy()
        data3["uid"] = None
        data3["name"] = "byuid"
        data4 = data.copy()
        data4["uid"] = 4
        data5 = data4.copy()
        data5["name"] = "foo"
        crt = [crontab.json.dumps(data), # test json loading
               crontab.Cron.load(data2),  # test from a running cron instance
               data3,
               data4,  # test with 4 and 5 the uid overwrite
               data5,
               'broken cron', # must not failed, just be skipped
              ]
        obj = crontab.Crontab.load(crt)
        return obj

def test__suite(): # pragma: no cover
    return unittest.defaultTestLoader.loadTestsFromName(__name__)


