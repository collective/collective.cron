#!/usr/bin/env python
# -*- coding: utf-8 -*-
__docformat__ = 'restructuredtext en'

try:
    from kss.core import kssaction
    from plone.app.kss.plonekssview import PloneKSSView # pragma: no cover  
except ImportError: # pragma: no cover  
    class PloneKSSView:
        pass
    def kssaction(fun):
        return fun

class NullFormValidation(PloneKSSView):
    """Disable inline validation.

XXX: This horrible hack should only be a temporary solution until
we find a way to make plone.z3c.form calculate and use the form
name correctly.
"""

    @kssaction
    def validate_input(self, *args):
        return # pragma: no cover  
# vim:set et sts=4 ts=4 tw=80: 
