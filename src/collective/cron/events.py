#!/usr/bin/env python
# -*- coding: utf-8 -*-
from zope.interface import implements
from zope.component.interfaces import ObjectEvent
from collective.cron import interfaces as i
class BackendFinnishedJobEvent(ObjectEvent):
    implements(i.IBackendFinnishedJobEvent)
    def __init__(self, object, status):
        ObjectEvent.__init__(self, object)
        self.status = status 

class ServerRestartEvent(ObjectEvent):
    implements(i.IServerRestartEvent)
    def __init__(self, object):
        ObjectEvent.__init__(self, object)

# vim:set et sts=4 ts=4 tw=80:
