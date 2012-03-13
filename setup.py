import os, sys

from setuptools import setup, find_packages

version = u'1.0'

def read(*rnames):
    return open(
        os.path.join('.', *rnames)
    ).read()

long_description = "\n\n".join(
    [read('README.txt'),
     read('CHANGES.txt'),
     read('docs', 'INSTALL.txt'),
     read('docs', 'HISTORY.txt'),
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
    install_requires=[
        'collective.autopermission',
        'collective.testcaselayer',
        'croniter',
        'five.grok',
        'lxml',
        'mocker',
        'plone.app.async',
        'plone.app.dexterity',
        'pytz',
        # -*- Extra requirements: -*-
    ],
    entry_points="""
    # -*- Entry points: -*-
    """,
)
# vim:set ft=python:
