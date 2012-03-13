#!/usr/bin/env python
# -*- coding: utf-8 -*-
__docformat__ = 'restructuredtext en'

"""
Backend test implementation
"""
from zope.interface import implements

from five import grok

from collective.cron.content import backend as b
from collective.cron import interfaces as i

class ISomeScrap(i.IBackend):
    """Gandi scrapping container interface"""

class SomeScrap(b.Backend):
    implements(ISomeScrap)

class SomeJobRunner(grok.Adapter):
    grok.context(ISomeScrap)
    grok.provides(i.IJobRunner)

    def get_the_stuff_done(self):
        errors = []
        return errors

    def run(self):
        """run the job."""
        errors = []
        errors.extend(self.get_the_stuff_done())
        # doesnt return bare exeception, just picklable strings
        errors = [u"%s" % repr(e) for e in errors]
        return errors

class SomeScrapGetAdapter(grok.Adapter):
    grok.implements(i.IBackendTitleCompl)
    grok.context(ISomeScrap)
    def getTitleCompl(self):
        return "im the title!"

# vim:set et sts=4 ts=4 tw=80:
