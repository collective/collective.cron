"""
Launching all doctests in the tests directory using:

    - the base layer in testing.py

"""
# GLOBALS avalaible in doctests
# IMPORT/DEFINE objects there or inside ./user_globals.py (better)
# globals from the testing product are also available.
# example:
# from for import bar
# and in your doctests, you can do:
# >>> bar.something
from collective.cron.tests.globals import *
from collective.cron.testing import (
    COLLECTIVE_CRON_FUNCTIONAL_TESTING as FUNCTIONAL_TESTING,
#    COLLECTIVE_CRON_TFUNCTIONAL_TESTING as TFUNCTIONAL_TESTING,
)
import unittest2 as unittest
import glob
import os
import logging
import doctest
from plone.testing import layered

optionflags = (doctest.ELLIPSIS | doctest.NORMALIZE_WHITESPACE)

def test_suite():
    """."""
    logger = logging.getLogger('collective.cron.tests')
    cwd = os.path.dirname(__file__)
    files = []
    try:
        files = []
        for e in ['*rst', '*txt']:
            for d in [cwd, 
                      os.path.dirname(cwd)]:
                files += glob.glob(os.path.join(d, e))
    except Exception,e: # pragma: no cover 
        logger.warn('No doctests for collective.cron')
    suite = unittest.TestSuite()
    globs = globals()
    for s in files:
        layer = FUNCTIONAL_TESTING
        #if 'timed_' in s:
        #    layer = FUNCTIONAL_TESTING
        suite.addTests([
            layered(
                doctest.DocFileSuite(
                    s, 
                    globs = globs,
                    module_relative=False,
                    optionflags=optionflags,         
                ),
                layer=layer,
            ),
        ])
    return suite
    
# vim:set ft=python:

