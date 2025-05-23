import os, sys

from setuptools import setup, find_packages

version = '2.8.dev0'

def read(*rnames):
    return open(
        os.path.join('.', *rnames)
    ).read()

long_description = "\n\n".join(
    [read('README.rst'),
     read('src', 'collective', 'cron', 'timed_api.rst'),
     read('src', 'collective', 'cron', 'timed_webui.rst'),
     read('src', 'collective', 'cron', 'timed_genericsetup.rst'),
     read('docs', 'CHANGES.rst'),
     read('docs', 'INSTALL.txt'),
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
    description='Product that enable cron like jobs for plone',
    long_description=long_description,
    classifiers=classifiers,
    keywords='',
    author='Makina Corpus <freesoftware@makina-corpus.com>',
    author_email='freesoftware@makina-corpus.com',
    url='http://pypi.python.org/pypi/%s' % name,
    license='GPL',
    packages=find_packages('src'),
    package_dir = {'': 'src'},
    include_package_data=True,
    extras_require = {
        'test': [
            'plone.app.testing',
        ],
    },
    install_requires=[
        'collective.autopermission',
        'simplejson', 
        'croniter',
        'plone.app.async > 1.3',
        'pytz',
        'ordereddict',
        'z3c.autoinclude',
        'setuptools', # Redundant, removes warning
        # -*- Extra requirements: -*-
    ],
    entry_points="""
    [z3c.autoinclude.plugin]
    target = plone
    """,
)
# vim:set ft=python:
