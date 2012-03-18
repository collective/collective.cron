import os, sys

from setuptools import setup, find_packages

version = u'1.0'

def read(*rnames):
    return open(
        os.path.join('.', *rnames)
    ).read()

long_description = "\n\n".join(
    [read('README.rst'),
     read('docs', 'INSTALL.txt'),
     read('docs', 'CHANGES.rst'),
    ]
)

classifiers = [
    "Programming Language :: Python",
    "Topic :: Software Development",]

name = 'collective.cron'
setup(
    name=name,
    namespace_packages=['collective',],
    version=version,
    description='Product that enable cron like jobs based on plone.app.async',
    long_description=long_description,
    classifiers=classifiers,
    keywords='',
    author='kiorky <kiorky@cryptelium.net>',
    author_email='kiorky@cryptelium',
    url='http://pypi.python.org/pypi/%s' % name,
    license='GPL',
    packages=find_packages('src'),
    package_dir = {'': 'src'},
    include_package_data=True,
    extras_require = {
        'test': [
            'collective.testcaselayer',
            'Products.PloneTestCase',
        ],
    },
    install_requires=[
        'collective.autopermission',
        'simplejson', 'demjson', # for zc.async
        'croniter',
        'five.grok',
        'mocker',
        'plone.app.async',
        'plone.app.dexterity',
        'zope.keyreference',
        'pytz',
        'z3c.autoinclude',
        # -*- Extra requirements: -*-
    ],
    entry_points="""
    [z3c.autoinclude.plugin]
    target = plone
    """,
)
# vim:set ft=python:
