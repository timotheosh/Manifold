# encoding: utf-8

'''manifold

An SMF service manifest creation tool.
'''

__author__ = 'Chris Miles'
__copyright__ = '(c) Chris Miles 2008. All rights reserved.'
__license__ = 'GPL http://www.gnu.org/licenses/gpl.txt'
__id__ = '$Id: manifold.py 7 2009-03-24 09:10:48Z miles.chris $'
__url__ = '$URL: https://manifold.googlecode.com/svn/trunk/manifold/manifold.py $'


# ---- Imports ----

# - Python Modules -
import logging
import os
import optparse
import sys

# - Genshi Modules -
from genshi.template import MarkupTemplate

# - Project Modules -
from release import version


# ---- Genshi Templates ----

MANIFEST_TEMPLATE = """<?xml version="1.0"?>
<!DOCTYPE service_bundle SYSTEM "/usr/share/lib/xml/dtd/service_bundle.dtd.1">
<!--
        Created by Manifold
-->

<service_bundle type='manifest' name='${service_name}' xmlns:py='http://genshi.edgewall.org/'>

    <service
            name='${service_category}/${service_name}'
            type='service'
            version='${service_version}'>

        <create_default_instance py:if="not multi_instance" enabled='${instance_enabled}' />
        
        <single_instance py:if="not multi_instance" />

        <dependency py:if="depends_on_network"
                name='network'
                grouping='require_all'
                restart_on='error'
                type='service'>
            <service_fmri value='svc:/milestone/network:default'/>
        </dependency>

        <dependency py:if="depends_on_filesystem"
                name='filesystem'
                grouping='require_all'
                restart_on='error'
                type='service'>
            <service_fmri value='svc:/system/filesystem/local'/>
        </dependency>


        <instance py:if="multi_instance" name='${instance_name}' enabled='${instance_enabled}'>
            <!--! This part used for a multi instance service. -->

            <method_context>
                <method_credential py:if="method_credential_user and method_credential_group" user='${method_credential_user}' group='${method_credential_group}' />
            </method_context>

            <exec_method
                    type='method'
                    name='start'
                    exec='${exec_method_start}'
                    timeout_seconds='60' />

            <exec_method
                    type='method'
                    name='stop'
                    exec='${exec_method_stop}'
                    timeout_seconds='60' />

            <property_group name='startd' type='framework'>
                <propval py:if="startd_model=='wait'" name='duration' type='astring' value='child' />
                <propval py:if="startd_model=='transient'" name='duration' type='astring' value='transient' />
                <propval py:if="startd_model=='contract'" name='duration' type='astring' value='contract' />
                <propval name='ignore_error' type='astring' value='core,signal' />
            </property_group>

            <property_group name='application' type='application'>
                <propval py:if="config_file" name='config_file' type='astring' value='${config_file}' />
            </property_group>

        </instance>
        
        <a_single_instance py:if="not multi_instance" py:strip="True">
        <!--! This part used for a single instance only service. -->
        <method_context>
            <method_credential py:if="method_credential_user and method_credential_group" user='${method_credential_user}' group='${method_credential_group}' />
        </method_context>

        <exec_method
                type='method'
                name='start'
                exec='${exec_method_start}'
                timeout_seconds='60' />

        <exec_method
                type='method'
                name='stop'
                exec='${exec_method_stop}'
                timeout_seconds='60' />

        <property_group name='startd' type='framework'>
            <propval py:if="startd_model=='wait'" name='duration' type='astring' value='child' />
            <propval py:if="startd_model=='transient'" name='duration' type='astring' value='transient' />
            <propval py:if="startd_model=='contract'" name='duration' type='astring' value='contract' />
            <propval name='ignore_error' type='astring' value='core,signal' />
        </property_group>

        <property_group name='application' type='application'>
            <propval py:if="config_file" name='config_file' type='astring' value='${config_file}' />
        </property_group>
        </a_single_instance>
        
        <stability value='Evolving' />

        <template>
            <common_name>
                <loctext xml:lang='C'>
                    ${common_name}
                </loctext>
            </common_name>
        </template>

    </service>

</service_bundle>
"""



# ---- Classes ----

class CONFIG_BASE(object):
    def __init__(self, name, require_value=False, default=None, description=None, example=None, accepted_values=None):
        self.name = name
        self.require_value = require_value
        self.default = default
        self.description = description
        self.example = example
        self.accepted_values = accepted_values
    
    def prompt(self):
        raise NotImplemented()
    
    def ask(self, config):
        raise NotImplemented()
    

class CONFIG_STR(CONFIG_BASE):
    def prompt(self):
        if self.description:
            s = self.description
        else:
            s = "Enter value for %s" %self.name
        if self.example:
            s += " (example: %s)" %self.example
        if self.default:
            s += " [%s] "% self.default
        else:
            s += " [] "
        return s
    
    def ask(self, config):
        r = None
        while r is None or (self.require_value and not r):
            r = raw_input(self.prompt()).strip()
            if not r and self.default is not None:
                r = self.default
            elif self.accepted_values and r not in self.accepted_values:
                print "Sorry, you must enter one of: " + ', '.join(['"%s"'%s for s in self.accepted_values])
                r = None
        if not r:
            r = None
        return r
    

class CONFIG_BOOL(CONFIG_BASE):
    def prompt(self):
        if self.description:
            s = self.description
        else:
            s = "%s" %self.name
        s += " (yes/no)"
        if self.default is not None:
            if self.default:
                default = "yes"
            else:
                default = "no"
            s += " [%s]"% default
        s += " ? "
        return s
    
    def ask(self, config):
        answers = dict(
            yes = True,
            ye = True,
            y = True,
            no = False,
            n = False
        )
        r = None
        while not r in answers.keys() and r != '':
            r = raw_input(self.prompt()).strip().lower()
        
        if r:
            r = answers[r]
        elif self.default is not None:
            r = self.default
        
        if r:
            r = 'true'
        else:
            r = 'false'
        
        return r
    

class CONFIG_IF(CONFIG_BASE):
    def __init__(self, *args, **kwargs):
        self.questions = kwargs.get('questions', [])
        del kwargs['questions']
        super(CONFIG_IF, self).__init__(*args, **kwargs)
    
    def prompt(self):
        if self.description:
            s = self.description
        else:
            s = "%s" %self.name
        s += " (yes/no)"
        if self.default is not None:
            if self.default:
                default = "yes"
            else:
                default = "no"
            s += " [%s]"% default
        s += " ? "
        return s
    
    def ask(self, config):
        answers = dict(
            yes = True,
            ye = True,
            y = True,
            no = False,
            n = False
        )
        r = None
        while not r in answers.keys() and r != '':
            r = raw_input(self.prompt()).strip().lower()
        
        if r:
            r = answers[r]
        elif self.default is not None:
            r = self.default
        
        if r:
            # if answer to this question is "yes" then ask user extra questions
            config.update(ask_user(self.questions))
        return r
    


# ---- Functions ----

def ask_user(service_questions):
    response = {}
    
    for q in service_questions:
        print
        response[q.name] = q.ask(response)
    return response


def generate_service_config():
    service_questions = [
        CONFIG_STR(
            'service_category',
            require_value=True,
            default='site',
            description='The service category',
            example="'site' or '/application/database'"
        ),
        CONFIG_STR(
            'service_name',
            require_value=True,
            description="""The name of the service, which follows the service category
  """,
            example="'myapp'"
        ),
        CONFIG_STR(
            'service_version',
            require_value=True,
            description="The version of the service manifest",
            default='1',
            example="'1'"
        ),
        CONFIG_STR(
            'common_name',
            require_value=False,
            description="""The human readable name of the service
  """,
            example="'My service.'"
        ),
        CONFIG_IF(
            'multi_instance',
            description="Can this service run multiple instances",
            default=False,
            questions=[
                CONFIG_STR('instance_name', require_value=True, default='default', example="default")
            ]
        ),
        CONFIG_STR(
            'config_file',
            require_value=False,
            description="""Full path to a config file; leave blank if no config file
  required""",
            example="'/etc/myservice.conf'"
        ),
        CONFIG_STR(
            'exec_method_start',
            require_value=True,
            description="""The full command to start the service; may contain
  '%{config_file}' to substitute the configuration file
  """,
            example="'/usr/bin/myservice %{config_file}'"
        ),
        CONFIG_STR(
            'exec_method_stop',
            require_value=True,
            default = ':kill',
            description="""The full command to stop the service; may specify ':kill' to let
  SMF kill the service processes automatically
  """,
            example="""'/usr/bin/myservice_ctl stop' or ':kill' to let SMF kill
  the service processes automatically"""
        ),
        CONFIG_STR(
            'startd_model',
            require_value=True,
            default = 'wait',
            description="""Choose a process management model:
  'wait'      : long-running process that runs in the foreground (default)
  'contract'  : long-running process that daemonizes or forks itself
                (i.e. start command returns immediately)
  'transient' : short-lived process, performs an action and ends quickly
  """,
            # example="",
            accepted_values = ('wait', 'contract', 'transient'),
        ),
        CONFIG_BOOL(
            'depends_on_network',
            description="Does this service depend on the network being ready",
            default=True
        ),
        CONFIG_BOOL(
            'depends_on_filesystem',
            description="Does this service depend on the local filesystems being ready",
            default=True
        ),
        CONFIG_BOOL(
            'instance_enabled',
            default=False,
            description="Should the service be enabled by default"
        ),
        CONFIG_STR(
            'method_credential_user',
            require_value=False,
            description="""The user to change to when executing the
  start/stop/refresh methods""",
            example="'webservd'"
        ),
        CONFIG_STR(
            'method_credential_group',
            require_value=False,
            description="""The group to change to when executing the
  start/stop/refresh methods""",
            example="'webservd'"
        ),
    ]
    
    service_config = ask_user(service_questions)
    logging.debug(service_config)
    
    return service_config


def create_manifest(outfp, service_config):
    tmpl = MarkupTemplate(MANIFEST_TEMPLATE)
    xml = tmpl.generate(**service_config).render('xml', strip_whitespace=False)
    outfp.write(xml)



def main(argv=None):
    if argv is None:
        argv = sys.argv
    
    # define usage and version messages
    usageMsg = "usage: %s [options] output.xml" % sys.argv[0]
    versionMsg = """%s %s""" % (os.path.basename(argv[0]), version)
    description = """Create an SMF service manifest file.  The resulting
XML file can be validated and imported into SMF using the 'svccfg' command.
For example, "svccfg validate myservice.xml", "svccfg -v import myservice.xml".
"""

    # get a parser object and define our options
    parser = optparse.OptionParser(usage=usageMsg, version=versionMsg, description=description)
    
    # Switches
    parser.add_option('-v', '--verbose', dest='verbose',
        action='store_true', default=False,
        help="verbose output")
    parser.add_option('-d', '--debug', dest='debug',
        action='store_true', default=False,
        help="debugging output (very verbose)")
    
    # Parse options & arguments
    (options, args) = parser.parse_args()
    
    if len(args) < 1:
        parser.error("Output file must be specified.")
    if len(args) > 1:
        parser.error("Only one output file can be specified.")
    
    if options.verbose:
        loglevel = logging.INFO
    elif options.debug:
        loglevel = logging.DEBUG
    else:
        loglevel = logging.WARNING
    
    logging.basicConfig(
        level=loglevel,
        # format='%(asctime)s %(levelname)s %(message)s',
        format='%(message)s',
    )
    
    output_filename = args[0]
    output = open(output_filename, 'w')
    
    service_config = generate_service_config()
    
    create_manifest(output, service_config)
    
    output.close()
    
    print "\nManifest written to %s" %output_filename
    print 'You can validate the XML file with "svccfg validate %s"' %output_filename
    print 'And create the SMF service with "svccfg import %s"' %output_filename
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
