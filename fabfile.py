import os
from fabric.api import *
from fabric.contrib.console import *
import json
from crypt import crypt
import time

from remote import RemoteWorkspace
from local import LocalWorkspace
from local import Distribution
from remote import Machine

class LsbService:
    def __init__(
            self,
            name,
            description,
            daemon,
            daemon_args,
            user,
            identifier='name',
            work_dir='/opt/${NAME}',
            group='$USER',
            pidfile='/etc/init.d/$NAME',
            path='/sbin:/usr/sbin:/bin:/usr/bin',
            log_path='${WORK_DIR}/log',
            scriptname='/etc/init.d/$NAME',
            keys=[
                '<service_path>',
                '<service_name>',
                '<service_description>',
                '<service_daemon>',
                '<service_daemon_args>',
                '<service_work_dir>',
                '<service_owner>',
                '<space_owner>',
                '<service_pidfile>',
                '<service_scriptname>',
                '<service_log_path>']
    ):
        self['service_name'] = name
        self['service_path'] = path
        self['service_description'] = description
        self['service_daemon'] = daemon
        self['service_daemon_args'] = daemon_args
        self['service_work_dir'] = work_dir
        self['service_owner'] = user
        self['space_owner'] = group
        self['service_pidfile'] = pidfile
        self['service_log_path'] = log_path
        self['service_scriptname'] = scriptname
        self.keys = keys

    def generateLsbScript(self, templateLocation, space=LocalWorkspace()):
            local('cp ' + space.templatePath(templateLocation) + ' ' + space.workDir + '/' + self[self.identifier])

            s = open(space.workDir + '/' + self[self.identifier]).read()
            for key in self.keys:
                s = s.replace('<%s>' % (key), self[key])

                f = open(space.workDir + '/' + self[self.identifier], 'w')
            f.write(s)
            f.close()

            print ("LINUX BOOT SERVICE GENERATED: " + space.workDir + '/' + self[self.identifier])

def host_type():
    run('uname -s')


def host_name():
    run('hostname')


def change_hostname(original, new, user, group):
    print("TRYING CHANGE HOSTNAME FROM " + original + " TO " + new + " ...")

    if original == new:
        print ("ORIGINAL AND NEW HOSTNAME IS THE SAME NO OPERATION NEEDED")
    else:
        run('mkdir -p ./tmp')
        run('cd ./tmp')

        sudo('cp /etc/hostname ./tmp/hostname.bak')
        sudo('cp /etc/hosts ./tmp/hosts.bak')

        sudo('chown -R ' + user + ':' + group + ' ./*')

        run('sed \'s/' + original + '/' + new + '/g\' ./tmp/hostname.bak > ./tmp/hostname')
        run('sed \'s/' + original + '/' + new + '/g\' ./tmp/hosts.bak > ./tmp/hosts')

        sudo('cp ./tmp/hostname /etc/hostname')
        sudo('cp ./tmp/hosts /etc/hosts')

        sudo('hostname ' + new)

        with settings(warn_only=True):
            sudo('reboot')

        # if result.failed and not confirm("Tests failed. Continue anyway?"):
        #     abort("Aborting at user request.")

        print("HOSTNAME CHANGED FROM " + original + " TO " + new + ".")


def install_service(scriptfile, application, start_level, stop_level):
    print ("INSTALL LSB SERVICE " + scriptfile + " FOR APPLICATION " + application)
    run('mkdir -p ~/tmp')
    put(scriptfile, '~/tmp/' + application + '/' + application)

    run('chmod u+x ' + "~/tmp/" + application + "/" + application)

    sudo('mv ' + scriptfile + '/' + application + ' /etc/init.d/' + application)

    sudo('update-rc.d -f ' + application + ' remove')
    sudo('update-rc.d ' + application + ' defaults ' + start_level + ' ' + stop_level)

    with settings(warn_only=True):
        sudo('systemctl daemon-reload')
    run('rm -r ./tmp')

def create_space(user, group, application, password):
    print ("CREATE SPACE FOR APPLICATION")

    with settings(warn_only=True):
        sudo(
            'echo y | echo "" | echo "" | echo "" | echo "" | echo ' + user + ' | echo ' + password + ' | echo ' + password + ' | adduser ' + user)
    with settings(warn_only=True):
        crypted_password = crypt(password, 'salt')
        sudo('usermod --password %s %s' % (crypted_password, user), pty=False)
    with settings(warn_only=True):
        sudo('addgroup ' + group)
    with settings(warn_only=True):
        sudo('adduser ' + user + ' ' + group)
    with settings(warn_only=True):
        sudo('mkdir -p /opt/' + application)
        sudo('usermod -m -d /opt/' + application + ' -m ' + user)

    # with settings(warn_only=True):
    #     sudo('mkdir -p /opt/' + application)
    with settings(warn_only=True):
        sudo('chown -R ' + user + ':' + group + ' /opt/' + application)

def install_linux_packages(dependency):
    sudo('apt-get install ' + dependency)

def install_python_modules(dependency):
    sudo('pip install ' + dependency)

def deploy_application(template, dist, config):
    print ("START DEPLOYING APPLICTION ")

    try:
        with open(config) as data_file:
            app = json.load(data_file)

            local('mkdir -p ./tmp')
            local('cd ./tmp')

            service = Machine(
                name=app['service_name'],
                description=app['service_description'],
                daemon=app['service_daemon'],
                daemon_args=app['service_daemon_args'],
                user=app['service_owner'],
                group=app['space_owner'],
                password=app['password'],
                work_dir=app['work_dir'],
                pidfile=app['pidfile'],
                scriptname=app['service_scriptname'],
                path=app['path'],
                log_path=app['log_path'],
                start_level=app['start_level'],
                stop_level=app['stop_level'],
            )

            service.printProperties()

            service.generateLsbScript(templateLocation=template, destionationLocation='./tmp')

            with settings(warn_only=True):
                run('rm -r ./tmp')
            run('mkdir -p ~/tmp')
            run('mkdir -p ~/tmp/' + service.name)

            create_space(service.user, service.group, service.name, service.password)

            install_service(
                scriptfile='./tmp/' + service.name,
                application=service.name,
                start_level=service.start_level,
                stop_level=service.stop_level
            )

            put(dist + '/*', './tmp/' + service.name)

            sudo('cp ./tmp/' + service.name + '/* /opt/' + service.name + '/')


            sudo('mkdir -p /opt/' + service.name + '/log')
            sudo('echo "Output log created ' + time.strftime(
                "%H:%M:%S") + '" >> /opt/' + service.name + '/log/' + service.name + '.out')
            sudo('echo "Error log created ' + time.strftime(
                "%H:%M:%S") + '" >> /opt/' + service.name+ '/log/' + service.name + '.err')

            sudo('chown -R ' + service.user + ':' + service.group + ' /opt/' + service.name + '/')


            # run('cd ..')


            run('rm -r ./tmp')

    except Exception as error:
        print ("COULD NOT READ " + config)
        print "IOError:", error
