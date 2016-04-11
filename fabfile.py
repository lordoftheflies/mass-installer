import os
from fabric.api import *
from fabric.contrib.console import *
import json


class EdgeService:
    def __init__(
            self,
            name,
            description,
            daemon,
            daemon_args,
            user,
            work_dir='/opt/${NAME}',
            group='$USER',
            pidfile='/etc/init.d/$NAME',
            path='/sbin:/usr/sbin:/bin:/usr/bin',
            log_path='${WORK_DIR}/log',
            start_level='99',
            stop_level='01',
            password='qwe123',
            scriptname='/etc/init.d/$NAME'
    ):
        self.name = name
        self.path = path
        self.description = description
        self.daemon = daemon
        self.daemon_args = daemon_args
        self.work_dir = work_dir
        self.user = user
        self.group = group
        self.pidfile = pidfile
        self.log_path = log_path
        self.start_level = start_level
        self.stop_level = stop_level
        self.password = password
        self.scriptname = scriptname

    def generateLsbScript(self, templateLocation, destionationLocation):
        if os.path.isfile(templateLocation) is False:
            print ("Source template is not exist.")
        else:
            local('cp ' + templateLocation + ' ' + destionationLocation + '/' + self.name)

            s = open(destionationLocation + '/' + self.name).read()
            s = s.replace('<service_path>', self.path)
            s = s.replace('<service_name>', self.name)
            s = s.replace('<service_description>', self.description)
            s = s.replace('<service_daemon>', self.daemon)
            s = s.replace('<service_daemon_args>', self.daemon_args)
            s = s.replace('<service_work_dir>', self.work_dir)
            s = s.replace('<service_owner>', self.user)
            s = s.replace('<space_owner>', self.group)
            s = s.replace('<service_pidfile>', self.pidfile)
            s = s.replace('<service_scriptname>', self.scriptname)
            s = s.replace('<service_log_path>', self.log_path)

            f = open(destionationLocation + '/' + self.name, 'w')
            f.write(s)
            f.close()

        print ("Linux boot service generated: " + destionationLocation)


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

        run('cd ..')
        run('rm -r ./tmp')

        with settings(warn_only=True):
            sudo('reboot')

        # if result.failed and not confirm("Tests failed. Continue anyway?"):
        #     abort("Aborting at user request.")

        print("HOSTNAME CHANGED FROM " + original + " TO " + new + ".")


def install_service(scriptfile, application, start_level, stop_level):
    print ("INSTALL LSB SERVICE " + scriptfile + " FOR APPLICATION " + application)

    run('mkdir -p ./tmp')
    run('cd ./tmp')

    put(scriptfile, "tmp/" + application)

    run('cd ./tmp/' + application)
    run('chmod a+x ' + scriptfile)
    sudo('cp ./' + scriptfile + ' /etc/init.d/' + scriptfile)

    sudo('update-rc.d -f ' + scriptfile + ' remove')
    sudo('update-rc.d ' + scriptfile + ' defaults ' + start_level + ' ' + stop_level)

    with settings(warn_only=True):
        sudo('systemctl daemon-reload')


def deploy_application(template, config):
    print ("START DEPLOYING APPLICTION ")

    try:
        with open(config) as data_file:
            app = json.load(data_file)

            local('mkdir -p ./tmp')
            local('cd ./tmp')

            service = EdgeService(
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
            ).generateLsbScript(templateLocation=template, destionationLocation='./tmp')

            # install_service(
            #     scriptfile='./tmp/' + service.name,
            #     application=service.name,
            #     start_level=service.start_level,
            #     stop_level=service.stop_level
            # )
    except Exception as error:
        print ("COULD NOT READ " + config)
        print "IOError:", error


def create_space(user, group, home):
    print ("CREATE SPACE FOR APPLICATION")
