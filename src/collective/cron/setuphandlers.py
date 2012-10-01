import logging
from zope.component import getMultiAdapter
from Products.CMFCore.utils import getToolByName
from collective.cron import interfaces
from collective.cron import crontab

from StringIO import StringIO

def setupVarious(context):

    # Ordinarily, GenericSetup handlers check for the existence of XML files.
    # Here, we are not parsing an XML file, but we use this text file as a
    # flag to check that we actually meant for this import step to be run.
    # The file is found in profiles/default.

    if context.readDataFile('collectivecron_various.txt') is None:
        return
    # if the queue is not marked, initialize the crontab !
    portal = getToolByName(
        context.getSite(), 'portal_url').getPortalObject()
    # initialiing manager will in turn intialize any
    # queue manager who is in charge for initializing
    # needed stuff for async jobs
    crt = crontab.Crontab.load()
    marker = getMultiAdapter(
        (portal, crt),
        interfaces.ICrontabManager
    )
    crt.save()

def setupCrons(context): # pragma: no cover
    logger = logging.getLogger('collective.cron.exportCrons')

    # Ordinarily, GenericSetup handlers check for the existence of XML files.
    # Here, we are not parsing an XML file, but we use this text file as a
    # flag to check that we actually meant for this import step to be run.
    # The file is found in profiles/default.

    xml = context.readDataFile('crons.xml')
    if xml is None:
        return
    # if the queue is not marked, initialize the crontab !
    portal = getToolByName(
        context.getSite(), 'portal_url').getPortalObject()
    # initialiing manager will in turn intialize any
    # queue manager who is in charge for initializing
    # needed stuff for async jobs
    crt = crontab.Crontab.load()
    exportimporter = getMultiAdapter(
        (portal, crt),
        interfaces.IExportImporter
    )
    exportimporter.do_import(xml)
    logger.info("crontab imported")

def exportCrons(context): # pragma: no cover
    # if the queue is not marked, initialize the crontab !
    logger = logging.getLogger('collective.cron.exportCrons')
    portal = getToolByName(
        context.getSite(), 'portal_url').getPortalObject()
    output = StringIO
    try:
        crt = crontab.Crontab.load()
    except:
        return
    exportimporter = getMultiAdapter(
        (portal, crt),
        interfaces.IExportImporter
    )
    result = exportimporter.do_export()
    context.writeDataFile("crons.xml", result, "txt/xml")
    logger.info("crontab exported" )

# Add additional setup code here
