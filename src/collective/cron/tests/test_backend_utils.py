#!/usr/bin/env python
# -*- coding: utf-8 -*- 
import copy
import os
import unittest
from collective.cron.tests import base
from collective.cron import interfaces as i
import datetime

class Mock(object):

    def get_absolute_url(self):
        return "nohost://here"

class BackendTest(base.TestCase):
    def test_log(self):
        g = self.g
        now = datetime.datetime(2011, 2, 7, 21, 58, 14, 884758)
        i.ICCRONUtils(g).log(now, errors=[u'foo'])
        res = g.getResults()[0].getObject()
        self.assertEquals(
            [getattr(res, aaa)
             for aaa in ('date', 'status', 'errors')],
            [now, u'OK', [u'foo']]
        )
        self.assertEquals(g.getLastRun(), now)
        self.assertEquals(g.getLastStatus(), 'OK')
        self.assertEquals(g.getLastErrors(), [u'foo'])
        self.assertEquals(
            res,
            g['--results--'][g['--results--'].objectIds()[0]]
        )

def test_suite():
    return unittest.defaultTestLoader.loadTestsFromName(__name__)

