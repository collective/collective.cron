import unittest2 as unittest
import datetime
from pytz import UTC, timezone
from collective.cron.tests import base
from collective.cron.utils import (
    su_plone,
    asbool,
    NoSuchUserError,
    to_utc,
)


from collective.cron import interfaces as i


from zope import interface as zi
from zope import schema as zc

class FooIf(zi.Interface):
    foo = zc.Bool(title=u'foo', default=False)

class Foo(i.ConstrainedObject):
    zi.implements(FooIf)
    
    def __init__(self, foo):
        self.foo = foo

class InterfaceTest(base.SimpleTestCase):
    def test_is_json_dict(self):
        self.assertTrue(i.is_json_dict([]))
        self.assertTrue(i.is_json_dict({}))
        self.assertTrue(i.is_json_dict(""))
        self.assertTrue(i.is_json_dict(None))
        self.assertTrue(i.is_json_dict('{"1":"2"}'))
        self.assertRaises(i.Invalid, i.is_json_dict, "foo")
        self.assertRaises(i.Invalid, i.is_json_dict, "[foo]")
        self.assertRaises(Exception, i.is_json_dict, '["foo"]')

    def test_if_cronformat(self):
        self.assertTrue(i.cronFormatValidator(None))
        self.assertTrue(i.cronFormatValidator(''))
        self.assertTrue(i.cronFormatValidator('1 * * * *'))
        self.assertRaises(i.CronFormatError , i.cronFormatValidator, '1 foo')

    def test_constrainedobject(self):
        foo = Foo('alpha')
        foo1 = Foo(True)
        self.assertRaises(zc.ValidationError, foo.verify)
        self.assertTrue(foo1.verify() is None) 

def test_suite():
    return unittest.defaultTestLoader.loadTestsFromName(__name__)

