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


counter = 0

class PatchedCrontabRegistryAdapter(registry.CrontabRegistryManager): # pragma: no cover
    _crontab = None
    _activated = True
    def __init__(self, context):
        from collective.cron.tests import test_cron
        test_cron.counter += 1
        old = getattr(context, '_testcrontabmanager', None)
        self.context = context
        self.read_only = getattr(self.context,
                                 'read_only', True)
        if old:
            self.crontab = old.crontab
            self.activated = old.activated
            self.read_only = old.read_only
        setattr(context, '_testcrontabmanager', self)

    @property
    def cronsettings(self):
        return self
    def _get_crontab(self):
        if self._crontab is None:
            self._crontab = []
        return self._crontab
    def _set_crontab(self, value):
        self._crontab = value
    def _get_activated(self):
        return self._activated
    def _set_activated(self, value):
        self._activated = value
    crontab = property(_get_crontab, _set_crontab)
    activated = property(_get_activated, _set_activated)

class Crontest(base.SimpleTestCase):
    def setUp(self):
        base.SimpleTestCase.setUp(self)
        component.getGlobalSiteManager().registerAdapter(
            PatchedCrontabRegistryAdapter, (i.ICrontab,))

    def tearDown(self):
        base.SimpleTestCase.tearDown(self)
        component.getGlobalSiteManager().unregisterAdapter(
            PatchedCrontabRegistryAdapter, (i.ICrontab,))

    def test_objects_log_load(self):
        tests= [
            ([{"date":"foodate","status":1,"messages":2}],
             None),
            ('', None),
            (None, None),
        ]
        for o, d in tests:
            self.assertEqual(
                crontab.Log.load(o), d, o)
        l = crontab.Log.load(
            {"date":"2008-01-01 1:1:1",
             "status":1,
             "messages":u'2'})
        self.assertEqual(
            l.date,
            datetime.datetime(2008, 1, 1, 1, 1, 1))
        self.assertEqual(l.status, 1)
        self.assertEqual(l.messages, [u'2'])
        l = crontab.Log.load(
            {"date":"2008-01-01 1:1:1",
              "status":1,
              "messages":[u'2']})
        self.assertEqual(
            l.date,
            datetime.datetime(2008, 1, 1, 1, 1, 1))
        self.assertEqual(l.status, 1)
        self.assertEqual(l.messages, ['2'])
        self.assertRaises(
            schema.ValidationError,
            crontab.Log.load,
            {"date":"2008-01-01 1:1:1",
              "status":666,
              "messages":[u'2']}
        )
        l = crontab.Log.load(
            {"date":"2008-01-01 1:1:1",
              "status":1,
              "messages":['2']})
        self.assertEquals(l.messages, [u'2'])

    def test_objects_crontab_load_from_settings(self):
        PatchedCrontabRegistryAdapter._crontab = [u'foo']
        self.assertRaises(i.InvalidCrontab, crontab.Crontab.load, 'foo')
        PatchedCrontabRegistryAdapter._crontab = [u'[]']
        cr = crontab.Crontab.load()
        self.assertEquals(len(cr.crons), 0)
        PatchedCrontabRegistryAdapter._crontab = None

    def test_objects_crontab_name(self):
        tests= [
            ([] , None),
            ('', None),
            (None, None),
        ]
        for o, d in tests:
            self.assertEqual(
                crontab.Log.load(o), d, o)
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
        data3 = data.copy()
        data3["uid"] = "3"
        data3["name"] = data2["uid"] = data2["name"] = "2"
        crt = [data, data2, data3]
        obj = crontab.Crontab.load(crt)
        crons1 = obj.by_name("1")
        crons2 = obj.by_name("2")
        self.assertEqual(len(crons1), 1)
        self.assertEqual(len(crons2), 2)
        self.assertEqual(crons1[0].uid, "1")
        self.assertEqual(crons2[0].uid, "2")
        self.assertEqual(crons2[1].uid, "3")

    def test_objects_crontab_by(self):
        crt = self.makeOne()
        crons2 = crt.by(name="2", activated=True)
        self.assertEqual(len(crons2), 0)
        crons2 = crt.by(name="1", activated=True)
        self.assertEqual(len(crons2), 2)
        crons2 = crt.by(name="1", activated=False)
        self.assertEqual(len(crons2), 0)

    def test_objects_crontab_load(self):
        tests= [
            ([] , None),
            ('', None),
            (None, None),
        ]
        for o, d in tests:
            self.assertEqual(
                crontab.Log.load(o), d, o)
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
        self.assertEqual(obj.read_only, False)
        self.assertEqual(obj.activated, True)
        self.assertEqual(len(obj.crons), len(crt) - 2)
        self.assertEquals(obj.crons["2"], crt[1])
        self.assertEquals(obj.crons["4"].name, "foo")
        self.assertEquals(obj.crons["1"].name,
                          crontab.json.loads(crt[0])['name'])
        self.assertEquals(
            len(obj.by_name("byuid")[0].uid), 32)

    def test_objects_cron_load(self):
        tests= [
            ([] , None),
            ('', None),
            (None, None),
        ]
        for o, d in tests:
            self.assertEqual(
                crontab.Log.load(o), d, o)
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
        obj = crontab.Cron.load(data)
        self.assertEqual(obj.uid, "1")
        self.assertEqual(obj.name, "1")
        self.assertEqual(obj.periodicity, u"1 * * * *")
        self.assertEqual(obj.activated, True)
        self.assertTrue(obj.environ == env)
        sdata = data.copy()
        sdata['periodicity'] = u'fault'
        self.assertRaises(i.CronFormatError,
                          crontab.Cron.load, sdata)
        sdata = data.copy()
        sdata['environ'] = u'fault'
        self.assertRaises(schema.ValidationError,
                          crontab.Cron.load, sdata)
        sdata = data.copy()
        sdata['activated'] = False
        obj = crontab.Cron.load(sdata)
        self.assertEqual(obj.activated, False)

        sdata = data.copy()
        sdata['uid'] = None
        obj = crontab.Cron.load(sdata)
        self.assertEqual(len(obj.uid), 32)

        # test load logs from log instances
        sdata['logs'] = obj.logs
        obj2 = crontab.Cron.load(sdata)
        self.assertEqual(
            [a for a in obj.logs],
            [a for a in obj2.logs])

        # test link between crontab is done during load
        cr = crontab.Crontab()
        cr.add_cron(obj)
        self.assertEqual(
            cr.by_uid(obj.uid), obj)

        # try to load a cron with same uid inside the same
        # crontab will not result in an uid switch.
        # this can be used to replace a cron inside a crontab
        dmp = obj.dump()
        obj2 = crontab.Cron.load(dmp, obj.crontab)
        self.assertEquals(obj2.uid, dmp['uid'])
        self.assertEqual(
            obj.crontab.by_uid(obj2.uid), obj2)

        # on the contrario, adding via add_cron = switch
        dmp = obj.dump()
        obj3 = crontab.Cron.load(dmp)
        obj.crontab.add_cron(obj3)
        self.assertNotEquals(obj3.uid, dmp['uid'])
        self.assertEqual(
            obj.crontab.by_uid(obj3.uid), obj3)

    def test_objects_cron_next(self):
        data = {
            "uid":"1",
            "name":"1",
            "periodicity": "5 * * * *",
            "activated": "1",
            "logs": [],
            "environ": {},
        }
        dt = datetime.datetime.now()
        obj = crontab.Cron.load(data)
        ldt = utils.to_utc(dt)
        ndt = obj.next
        self.assertEqual(
            repr(ndt), 'datetime.datetime(2008, 1, 1, 0, 5, tzinfo=<UTC>)'
        )
        obj.periodicity = u"6 * * * *"
        ndt = obj.next
        self.assertEqual(
            repr(ndt), 'datetime.datetime(2008, 1, 1, 0, 6, tzinfo=<UTC>)'
        )
        self.assertRaises(i.CronFormatError,
                          setattr, obj, 'periodicity', u"broken stuff")
        #ndt = obj.next
        #self.assertEqual(ndt, None)

    def test_objects_log_repr(self):
        fdata = {"date":"2008-01-01 1:1:1",
                 "status":1,
                 "messages":u'2'}
        data = fdata.copy()
        l = crontab.Log.load(data)
        self.assertEqual(repr(l), 'log: 2008-01-01 01:01:01/OK+')
        data = fdata.copy()
        del data['messages']
        l = crontab.Log.load(data)
        self.assertEqual(repr(l), 'log: 2008-01-01 01:01:01/OK')
        self.assertRaises(ConstraintNotSatisfied, setattr, l, 'status', 'foo')
        self.assertRaises(RequiredMissing, setattr, l, 'status', None)
        self.assertRaises(RequiredMissing, setattr, l, 'date', None)
        #self.assertEqual(repr(l), 'log: 2008-01-01 01:01:01')
        #self.assertEqual(repr(l), 'log:')

    def test_objects_cron_repr(self):
        fdata = {
            "uid":"xxYYzz",
            "name":"1",
            "periodicity": "5 * * * *",
            "activated": "1",
            "logs": [
                {"date":"2008-01-01 1:1:1",
                  "status":1,
                  "messages":[u'2']},
                {"date":"2008-01-01 1:1:1",
                 "status":1,
                  "messages":[u'2']},
            ],
            "environ": {"foo":"bar"},
        }
        data = fdata.copy()
        del data["logs"]
        del data["environ"]
        obj = crontab.Cron.load(data)
        self.assertEqual(repr(obj), 'cron: 1/xxYYzz [ON:2008-01-01 00:05:00]')
        obj.activated = False
        self.assertEqual(repr(obj), 'cron: 1/xxYYzz [OFF]')
        obj = crontab.Cron.load(fdata)
        self.assertEqual(repr(obj),
                         "cron: 1/xxYYzz "
                         "[ON:2008-01-01 00:05:00] "
                         "(2 logs) "
                         "{'foo': 'bar'}")


    def test_objects_cron_last(self):
        fdata = {
            "uid":"xxYYzz",
            "name":"1",
            "periodicity": "5 * * * *",
            "activated": "1",
            "logs": [
                {"date":"2008-01-01 2:1:1",
                  "status":1,
                  "messages":[u'2']},
                {"date":"2008-01-01 1:1:1",
                 "status":1,
                  "messages":[u'2']},
            ],
            "environ": {"foo":"bar"},
        }
        data = fdata.copy()
        del data["logs"]
        obj = crontab.Cron.load(data)
        self.assertEqual(obj.last, None)
        self.assertEqual(obj.last_date, None)
        self.assertEqual(obj.slast, '')
        self.assertEqual(obj.last_messages, [])
        self.assertEqual(obj.last_status, None)
        data = fdata.copy()
        obj = crontab.Cron.load(data)
        self.assertTrue(isinstance(obj.last, crontab.Log))
        self.assertEqual(obj.slast, '2008-01-01 01:01:01')
        self.assertEqual(obj.last_date, datetime.datetime(2008, 1, 1, 1, 1, 1))
        self.assertEqual(obj.last_messages, [u'2'])
        self.assertEqual(obj.last_status, 1)

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

    def test_objects_load_frominstances(self):
        crt = self.makeOne()
        log = crt.crons["1"].logs[0]
        cron = crt.crons["1"]
        self.assertEquals(cron, crontab.Cron.load(cron))
        self.assertEquals(log, crontab.Log.load(log))
        self.assertEquals(crt, crontab.Crontab.load(crt))

    def test_objects_dump(self):
        crt = self.makeOne()
        cron = crt.crons["1"]
        log = cron.logs[0]
        ldp = log.dump()
        self.assertEquals(
            ldp,
            {"date": "2008-01-01 01:01:01",
             "status": 1,
             "messages": ["2"]}
        )
        cdp = cron.dump()
        self.assertEquals(
            cdp,
            {'logs': [
                {'date': '2008-01-01 01:01:01',
                 'status': 1,
                 'messages': [u'2']},
                {'date': '2008-01-01 01:01:01',
                 'status': 1,
                 'messages': [u'2']}],
                'periodicity': u'1 * * * *',
                'activated': True,
                'name': u'1',
                'environ': {u'foo': u'bar'},
                'uid': u'1',
                'user': None,
            }
        )
        crdp = crt.dump()
        self.assertEquals(len(crdp), 4)
        self.assertEquals(crdp[0], cdp)

    def test_objects_cron_changeuid(self):
        crt = self.makeOne()
        cron = crt.crons["1"]
        uid = cron.uid
        cron.change_uid()
        self.assertNotEquals(uid, cron.uid)

    def test_objects_save(self):
        crt = self.makeOne()
        dmp = crt.dump()
        sv = crt.save()
        self.assertTrue(
            crt.manager.crontab[0].startswith('{"')
        )

    def test_objects_cron_save(self):
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

    def test_objects_cron_delete(self):
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

    def test_objects_crontab_addcron(self):
        crt = self.makeOne()
        dmp = crt.crons["1"].dump()
        lcron = len(crt.crons)
        cron = crontab.Cron.load(dmp)
        uid = cron.uid
        crt.add_cron(cron)
        llcron = len(crt.crons)
        self.assertNotEquals(cron.uid, uid)
        self.assertEquals(lcron+1, llcron)

    def test_objects_reload(self):
        crt = self.makeOne()
        dmp = crt.dump()
        crt.save()
        ncron = crontab.Crontab.load(crt.crons)
        self.assertTrue(dmp == ncron.dump())

    def test_objects_log___eq__(self):
        crt = self.makeOne()
        log = crt.crons["1"].logs[0]
        otherlog = crontab.Log.load(log.dump())
        #
        self.assertEquals(log, otherlog)
        #
        otherlog.date = datetime.datetime(2008,4,4)
        self.assertNotEquals(log, otherlog)
        otherlog.date = log.date
        #
        otherlog.messages = [u'foo', u'bar']
        self.assertNotEquals(log, otherlog)
        otherlog.messages = log.messages
        #
        otherlog.status = 2
        self.assertNotEquals(log, otherlog)
        otherlog.status = log.status

    def test_objects_cron___eq__(self):
        crt = self.makeOne()
        cron = crt.crons["1"]
        othercron = crontab.Cron.load(
            cron.dump(),
            cron.crontab
        )
        othercron.uid = cron.uid

        #
        self.assertEquals(cron, othercron)
        #
        othercron.uid = u"foobarnotequal"
        self.assertNotEquals(cron, othercron)
        othercron.uid = cron.uid
        #
        othercron.name = u"foobarnotequal"
        self.assertNotEquals(cron, othercron)
        othercron.name = cron.name
        #
        othercron.activated = not cron.activated
        self.assertNotEquals(cron, othercron)
        othercron.activated = cron.activated
        #
        othercron.periodicity = u"2 2 2 2 2 2"
        self.assertNotEquals(cron, othercron)
        othercron.periodicity = cron.periodicity
        #
        othercron.logs = [crontab.Log(
            date=datetime.datetime(2009,4,4),
            status = 0,
            messages=[u"foo", u"bar"],
        )]
        self.assertNotEquals(cron, othercron)
        othercron.logs = [crontab.Log.load(l)
                          for l in cron.logs ]
        self.assertEquals(cron, othercron)
        othercron.logs = cron.logs
        #
        othercron.environ = {666:777}
        self.assertNotEquals(cron, othercron)
        othercron.environ = cron.environ
        #
        othercron.crontab = crontab.Crontab()
        self.assertNotEquals(cron, othercron)
        othercron.crontab = cron.crontab

    def test_objects_crontab__readonly_p(self):
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

    def test_objects_crontab__readonly_v_o(self):
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

    def test_objects_crontab__readonly_v_w(self):
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

    def test_objects_crontab___eq__(self):
        crt = self.makeOne()
        othercrt = crontab.Crontab.load(crt.dump())
        #
        self.assertEquals(crt, othercrt)
        #
        othercrt.activated = not crt.activated
        self.assertNotEquals(crt, othercrt)
        othercrt.activated = crt.activated
        #
        othercrt.activated = not crt.activated
        self.assertNotEquals(crt, othercrt)
        othercrt.activated = crt.activated
        #
        othercrt.crons["1"].name = u"foo"
        self.assertNotEquals(crt, othercrt)
        othercrt.crons = crt.crons
        #
        othercrt.crons = {}
        self.assertNotEquals(crt, othercrt)
        othercrt.crons = crt.crons

    def test_different_crontabs(self):
        crt = self.makeOne()
        cron = crt.crons["1"]
        cr1 = crontab.Crontab()
        sdata = cron.dump()
        del sdata['name']
        del sdata['uid']
        cron11 = crontab.Cron(crontab=cr1, uid=u"111", name=u"111", **sdata)
        cron12 = crontab.Cron(crontab=cr1, uid=u"222", name=u"222", **sdata)
        cron13 = crontab.Cron(crontab=cr1, uid=u"333", name=u"333", **sdata)
        cron14 = crontab.Cron(crontab=cr1, uid=u"444", name=u"444", **sdata)
        cron15 = crontab.Cron(crontab=cr1, uid=u"555", name=u"555", **sdata)
        #
        cr2 = crontab.Crontab()
        cron21 = crontab.Cron(crontab=cr2, **cron11.dump())
        cron22 = crontab.Cron(crontab=cr2, **cron12.dump())
        cron23 = crontab.Cron(crontab=cr2, **cron13.dump())
        cron24 = crontab.Cron(crontab=cr2, **cron14.dump())
        cron25 = crontab.Cron(crontab=cr2, **cron15.dump())
        #
        cr3 = crontab.Crontab()
        cron31 = crontab.Cron(crontab=cr3, **cron11.dump())
        cron32 = crontab.Cron(crontab=cr3, **cron12.dump())
        cron35 = crontab.Cron(crontab=cr3, **cron15.dump())
        #
        cr4 = crontab.Crontab()
        cron21 = crontab.Cron(crontab=cr4, **cron12.dump())
        cron22 = crontab.Cron(crontab=cr4, **cron11.dump())
        cron23 = crontab.Cron(crontab=cr4, **cron13.dump())
        cron24 = crontab.Cron(crontab=cr4, **cron14.dump())
        cron25 = crontab.Cron(crontab=cr4, **cron15.dump())
        #

        self.assertEquals(cr1, cr2)
        cron23.name = u'foo'
        self.assertNotEquals(cr1, cr2)
        self.assertNotEquals(cr1, cr3)
        self.assertNotEquals(cr1, cr4)

def test__suite(): # pragma: no cover
    return unittest.defaultTestLoader.loadTestsFromName(__name__)


