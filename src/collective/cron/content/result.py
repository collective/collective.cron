#!/usr/bin/env python
# -*- coding: utf-8 -*-
# POSSIBILITY OF SUCH DAMAGE.
__docformat__ = 'restructuredtext en'

from zope.interface import implements
from five import grok

from plone.directives import dexterity
from plone.dexterity.content import Container
from collective.cron import interfaces as i

class Result(Container):
    implements(i.IResult)
# vim:set et sts=4 ts=4 tw=80:                               
