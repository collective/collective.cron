#!/usr/bin/env python
# -*- coding: utf-8 -*-
import re
import unittest
import doctest
import os.path

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# UTILITIES AND GLOBBALS SUPPORT / EDIT .user_utils.py or .user.globals.py to overidde
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# if you have plone.reload out there add an helper to use in doctests while programming
# just use preload(module) in pdb :)
# it would be neccessary for you to precise each module to reload, this method is also not recursive.
# eg: (pdb) from foo import bar;preload(bar)
# see utils.py for details

from collective.cron.tests.globals import *
from collective.cron.tests import base

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# ZOPE2 SPEFICIC / EDIT .user_testcase.DocTestCase to overidde
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
DocTestCase = None
from Testing import ZopeTestCase as ztc

doctest_flags = doctest.REPORT_ONLY_FIRST_FAILURE | doctest.NORMALIZE_WHITESPACE | doctest.ELLIPSIS

reflags = re.M|re.U|re.S
def testfilter(patterns,
               filename):
    for pattern in patterns:
        if re.search(pattern, filename, reflags):
            return True
    return False

def test_doctests_suite(directory=__file__,
                        files = None,
                        patterns = None,
                        globs=None,
                        suite=None,
                        testklass=None,
                        doctest_options = doctest_flags,
                        lsetUp=None, ltearDown=None
                       ):
    """A doctest suite launcher.
    You can even launch doctests from others packages with the
    testing setup with embedding this test suite
    You can even add others globals in those tests.
    No need to copy and duplicate this file, it is useless.

      #Example : This snippet will launch all txt doctests in the other package directory
      >>> from collective.cron.tests.test_doctests import test_doctests_suite as ts
      >>> def test_suite():
      ...     globs = globals()
      ...     return ts(__file__, globs)

    directory: where to find files to test
    globs: A dictionnary to setup test globals from.
    directory: directory or filename where to run the tests
    files: files to include
    pattern: pattern for tests inclusion in the suite
    suite: a TestSuite object
    testklass: only useful if you are inside a Zope2 environment, because ztc comes from there.
               Note that in this case, setUp and tearDown are useless.
    Indeed modern application relys more on the setUp and tearDown functions.
    tearDown: tearDown code to run
    setUp: setUp code to run
    """
    _f = None
    if not patterns:
        patterns = ['.txt$']
    if not directory or os.path.isfile(directory):
        directory, _f = os.path.split(os.path.abspath(directory))
    elif os.path.isfile(directory):
        directory = os.path.dirname(directory)
    if not globs: globs={}
    g = globals()
    for key in g: globs.setdefault(key, g[key])
    if not files:
        files = [os.path.join(directory, f)
                 for f in os.listdir(directory)
                 if testfilter(patterns, f)]
    else:
        for i, f in enumerate(files[:]):
            if not os.path.sep in f:
                files[i] = os.path.abspath(os.path.join(directory, f))
            else:
                files[i] = os.path.abspath(f)

    if not suite: suite = unittest.TestSuite()
    if files:
        for test in files:
            ft = None
            if not testklass: testklass=DocTestCase
            ft = ztc.FunctionalDocFileSuite(
                test,
                test_class=testklass,
                optionflags=doctest_options,
                globs=globs,
                module_relative = False,
            )
            if ft: suite.addTest(ft)
    return suite

"""
Launching all doctests in the tests directory using:

    - The test_suite helper from the testing product
    - the base FunctionalTestCase in base.py

################################################################################
# GLOBALS avalaible in doctests
# IMPORT/DEFINE objects there or inside ./user_globals.py (better)
# globals from the testing product are also available.
################################################################################
# example:
# from for import bar
# and in your doctests, you can do:
# >>> bar.something

################################################################################

"""
def test_suite():
    return test_doctests_suite(
        __file__,
        globs=globals(),
        testklass=base.FunctionalTestCase
    )
# vim:set ft=python:
