from Products.Five import zcml
from Products.Five import fiveconfigure

from Testing import ZopeTestCase as ztc
import transaction
from OFS.Folder import Folder

from Products.PloneTestCase import PloneTestCase as ptc
from collective.testcaselayer.ptc import BasePTCLayer, ptc_layer

from plone.app.async.testing import AsyncLayer, async_layer

TESTED_PRODUCTS = ()

class Layer(AsyncLayer):
    """Layer to setup the policy site"""
    class Session(dict):
        def set(self, key, value):
            self[key] = value

    def afterSetUp(self):
        """Set up the additional products required for the collective.cron) site policy.
        until the setup of the Plone site testing layer.
        """
        for product in TESTED_PRODUCTS:
            ztc.installProduct(product)

        # ------------------------------------------------------------------------------------
        # Import all our python modules required by our packages
        # ------------------------------------------------------------------------------------
    #with_ploneproduct_dexterity
        import plone.app.dexterity
        self.loadZCML('configure.zcml', package=plone.app.dexterity)
    #with_ploneproduct_pz3cform
        import five.grok
        self.loadZCML('configure.zcml', package=five.grok)
        import plone.app.z3cform
        self.loadZCML('configure.zcml', package=plone.app.z3cform)
        import plone.directives.form
        self.loadZCML('configure.zcml', package=plone.directives.form)
        import plone.z3cform
        self.loadZCML('configure.zcml', package=plone.z3cform)
        # ------------------------------------------------------------------------------------
        # - Load the python packages that are registered as Zope2 Products via Five
        #   which can't happen until we have loaded the package ZCML.
        # ------------------------------------------------------------------------------------

        # ------------------------------------------------------------------------------------
        # Load our own policy
        # ------------------------------------------------------------------------------------
        ztc.installPackage('collective.cron')
        import collective.cron
        self.loadZCML('configure.zcml', package=collective.cron)
        self.loadZCML('test.zcml', package=collective.cron)
        self.addProfile('collective.cron:default')
        self.addProfile('collective.cron:test')

        # ------------------------------------------------------------------------------------
        # support for sessions without invalidreferences if using zeo temp storage
        # ------------------------------------------------------------------------------------
        self.app.REQUEST['SESSION'] = self.Session()
        if not hasattr(self.app, 'temp_folder'):
            tf = Folder('temp_folder')
            self.app._setObject('temp_folder', tf)
            transaction.commit()
        ztc.utils.setupCoreSessions(self.app)

layer = Layer(bases=[async_layer])
