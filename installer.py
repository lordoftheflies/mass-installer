#!/bin/python
import ConfigParser
import json
import pxssh
import pexpect
from pprint import pprint
import os
import shutil
import argparse

import sys

INSTALL_DEPENDENCIES_SH = "install-dependencies.sh"

INSTALLER_LOG_FILE_IN_EDGE = "installer-lordoftheflies.txt"

SETUP_ENVIRONMENT_SH = "setup-environment.sh"


class Distribution:
    def __init__(self, templateDirectory, distributionDirectory):
        self.templateDirectory = templateDirectory
        self.distributionDirectory = distributionDirectory

    def make(self, edges, applications, dependencies):
        for edge in edges:
            environment = SetupEnvironment(self.templateDirectory, self.distributionDirectory + "/" + edge['name'])
            for app in applications:
                environment.initialize(app)
                deployment = SetupDeployment(self.templateDirectory, self.distributionDirectory + "/" + edge['name'])
                deployment.generateLsbService(app)
                deployment.generateSetupScript(app)

            environment.generateInstallDependenciesScript(dependencies)


class MassDeployer:
    def __init__(self, administrator, password):
        self.s = None
        self.user = administrator
        self.password = password

    def copy(self, edge, sourceDire):
        print ("Try copy deployments of " + edge['name'] + " to " + edge['address'])

        try:

            var_child = pexpect.spawn(command='scp -rp %s %s@%s:%s' % (
            sourceDire + "/" + edge['name'] + "/", self.user, edge['address'], "~/"), timeout=30)
            print 'COMMAND: scp -rp %s %s@%s:%s' % (sourceDire, self.user, edge['address'], "~/")

            # make sure in the above command that username and hostname are according to your server
            # var_child = pexpect.spawn(command=var_command, timeout=30)
            i = var_child.expect(['assword:', r"yes/no"], timeout=30)
            if i == 0:
                var_child.sendline(self.password)
            elif i == 1:
                var_child.sendline("yes")
                var_child.expect("assword:", timeout=30)
                var_child.sendline(self.password)
            data = var_child.read()
            print data
            var_child.close()


        except Exception as e:
            print ("Could not deploy " + edge['name'] + " to " + edge['address'])

    def run(self, edge):
        print ("Try copy deployments of " + edge['name'] + " to " + edge['address'])

        try:

            var_child = pexpect.spawn(command='ssh %s@%s' % (self.user, edge['address']), timeout=30)
            print 'COMMAND: ssh %s@%s' % (self.user, edge['address'])

            # data = var_child.read()
            # print data


            # make sure in the above command that username and hostname are according to your server
            # var_child = pexpect.spawn(command=var_command, timeout=30)
            i = var_child.expect(['%s@%s\'s password:' % (self.user, edge['address'])], timeout=30)
            if i == 0:
                var_child.sendline(self.password)
            elif i == 1:
                var_child.sendline("yes")
                var_child.expect("assword:", timeout=30)
                var_child.sendline(self.password)

            # data = var_child.read()
            # print data
            i = var_child.expect(['$'], timeout=30)
            if i == 0:
                command = 'cd ' + edge['name']
                print 'COMMAND: ' + command
                var_child.sendline(command)
            # data = var_child.read()
            # print command + " -> " + data

            i = var_child.expect(['$'], timeout=30)
            if i == 0:
                command = "sudo sh ./" + INSTALL_DEPENDENCIES_SH + " >> install-dependencies.log"
                print 'COMMAND: ' + command
                var_child.sendline(command)
                i = var_child.expect(["[sudo] password for " + self.user + ":"], timeout=30)
                if i == 0:
                    var_child.sendline(self.password)

            data = var_child.read_nonblocking()
            print command + " -> " + data

            var_child.close()


        except Exception as e:
            print ("Could not deploy " + edge['name'] + " to " + edge['address'])


class SetupDeployment:
    def __init__(self, templateDirectory, distributionDirectory):
        self.templateDirectory = templateDirectory
        self.distributionDirectory = distributionDirectory

    def setupVariables(self, app, templateLocation, destionationLocation):
        if os.path.isfile(templateLocation) == False:
            print ("Source template is not exist.")
        else:
            shutil.copy(templateLocation, destionationLocation)
            s = open(destionationLocation).read()
            s = s.replace('<service_name>', app['service_name'])
            if hasattr(app, 'service_descriptions'):
                s = s.replace('<service_description>', app['service_description'])

            s = s.replace('<service_daemon>', app['service_daemon'])
            s = s.replace('<service_daemon_args>', app['service_daemon_args'])
            s = s.replace('<service_owner>', app['service_owner'])
            if hasattr(app, 'space_owner'):
                s = s.replace('<space_owner>', app['space_owner'])
            else:
                s = s.replace('<space_owner>', app['service_owner'])

            f = open(destionationLocation, 'w')
            f.write(s)
            f.close()

        print ("Linux boot service generated: " + destionationLocation)

    def generateLsbService(self, app):
        appDistDir = self.distributionDirectory + "/" + app['service_name']
        self.setupVariables(app, self.templateDirectory + "/start-stop-daemon-template",
                            appDistDir + "/" + app['service_name'])

    def generateSetupScript(self, app):
        appDistDir = self.distributionDirectory + "/" + app['service_name']
        self.setupVariables(app, self.templateDirectory + "/setup-environment.sh",
                            appDistDir + "/" + SETUP_ENVIRONMENT_SH)


class SetupEnvironment:
    def __init__(self, templateDirectory, distributionDirectory):
        self.templateDirectory = templateDirectory
        self.distributionDirectory = distributionDirectory

    def initialize(self, app):
        appDistDir = self.distributionDirectory + "/" + app['service_name']
        os.makedirs(appDistDir)

    def writeOutPythonDependenciesScript(self, f, dependencies):
        f.writelines("# Python depencies installer script\n")
        for dep in dependencies:
            f.writelines("pip install " + dep + "\n")

    def writeOutLinuxDependenciesScript(self, f, dependencies):
        f.writelines("# OS depencies installer script\n")
        for dep in dependencies:
            f.writelines("apt-get install " + dep + "\n")

    def generateInstallDependenciesScript(self, dependencies):
        appDistDir = self.distributionDirectory
        f = open(appDistDir + "/" + INSTALL_DEPENDENCIES_SH, 'w')
        f.writelines("#!/bin/bash\n")
        self.writeOutLinuxDependenciesScript(f, dependencies['linux'])
        self.writeOutPythonDependenciesScript(f, dependencies['python'])
        f.close()


def initialize(systemJsonFilePath):
    with open(systemJsonFilePath) as data_file:
        systemJson = json.load(data_file)
        pprint(systemJson)
        return systemJson


def cleanUp(distDir):
    shutil.rmtree(distDir)
    os.mkdir(distDir)


class RemoteShell:
    def __init__(self, edge, administrator, password):
        self.edge = edge
        self.s = None
        self.user = administrator
        self.password = password

    def login(self):
        try:
            self.s = pxssh.pxssh()
            self.s.login(self.edge.address, self.user, self.password)
        except pxssh.ExceptionPxssh as e:
            print("pxssh failed on login.")
            print(e)

    def logout(self):
        try:
            self.s.logout()
        except pxssh.ExceptionPxssh as e:
            print("pxssh failed on logout.")
            print(e)

    def execute(self, command):
        try:
            self.s.sendline(command)
            print(self.s.before)
            self.s.prompt()
        except pxssh.ExceptionPxssh as e:
            print("pxssh failed execute statement:" + command)
            print(e)

    def executePrivilegized(self, command):
        try:
            self.s.sendline('sudo -s')
            self.s.sendline(self.password)
            self.s.sendline(command)
            print(self.s.before)
            self.s.prompt()
        except pxssh.ExceptionPxssh as e:
            print("pxssh failed execute privilegized statement:" + command)
            print(e)


administratorUserName = "pi"
administratorPassword = "raspberry"

parser = argparse.ArgumentParser(description='Parse installer arguments.')

# Parsing argument from command line (these options prioritized)
parser.add_argument("-s", "--system", help="System install configuration file.", type=str, default="system.json")
parser.add_argument("-v", "--verbose", help="Increase output verbosity", action="store_true")

args = parser.parse_args()

systemDescriptor = initialize(args.system)

print("Install system " + systemDescriptor['name'] + "-" + systemDescriptor['version'])

# Local build directories.
templateDirectory = "./templates"
distributionDirectory = "./dist"

cleanUp(distributionDirectory)

# Execute the distribution process.
distribution = Distribution(templateDirectory, distributionDirectory)
distribution.make(systemDescriptor['edges'], systemDescriptor['applications'], systemDescriptor['dependencies'])

deployer = MassDeployer(systemDescriptor['administrator'], systemDescriptor['password'])
for edge in systemDescriptor['edges']:
    print ("BEGIN REMOTE DISTRIBUTION OF " + edge['name'] + " ========================================================")
    deployer.copy(edge, distributionDirectory)
    deployer.run(edge)
    print ("END REMOTE DISTRIBUTION OF " + edge['name'] + " ==========================================================")
