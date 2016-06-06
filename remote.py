from fabric.api import *
from crypt import crypt


class RemoteWorkspace:
    def __init__(self, workDir='~/tmp', distDir='~/opt'):
        self.workDir = workDir
        self.distDir = distDir
        # Create temporary directory for install workspace.
        run('mkdir -p ' + self.workDir)

    def __del__(self):
        # Cleanup install workspace.
        run('rm -r ' + self.workDir)


class Machine:
    def __init__(self, hostname):
        self.hostname = hostname

    def install_linux_packages(dependency):
        sudo('apt-get install ' + dependency)

    def install_python_modules(dependency):
        sudo('pip install ' + dependency)

    def host_type(self):
        run('uname -s')

    def host_name(self):
        run('hostname')

    def change_hostname(self, new, user, group, space=RemoteWorkspace()):
        print("TRYING CHANGE HOSTNAME FROM " + self.hostname + " TO " + new + " ...")

        if self.hostname == new:
            print ("ORIGINAL AND NEW HOSTNAME IS THE SAME NO OPERATION NEEDED")
        else:
            sudo('cp /etc/hostname ' + space.workDir + '/hostname.bak')
            sudo('cp /etc/hosts ' + space.workDir + '/hosts.bak')

            sudo('chown -R ' + user + ':' + group + ' ./*')

            run(
                'sed \'s/' + self.hostname + '/' + new + '/g\' ' + space.workDir + '/hostname.bak > ' + space.workDir + '/hostname')
            run(
                'sed \'s/' + self.hostname + '/' + new + '/g\' ' + space.workDir + '/hosts.bak > ' + space.workDir + '/hosts')

            sudo('cp ' + space.workDir + '/hostname /etc/hostname')
            sudo('cp ' + space.workDir + '/hosts /etc/hosts')

            sudo('hostname ' + new)

            self.hostname = new
            # if result.failed and not confirm("Tests failed. Continue anyway?"):
            #     abort("Aborting at user request.")

            print("HOSTNAME WILL CHANGE AFTER REBOOT" + self.hostname + " TO " + new + ".")

    def create_space(self, user, group, application, password, space=RemoteWorkspace()):
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
            sudo('mkdir -p ' + space.distDir + '/' + application)
            sudo('usermod -m -d ' + space.distDir + '/' + application + ' -m ' + user)

        # with settings(warn_only=True):
        #     sudo('mkdir -p /opt/' + application)
        with settings(warn_only=True):
            sudo('chown -R ' + user + ':' + group + ' ' + space.distDir + '/' + application)

    def install_service(self, scriptfile, application, start_level, stop_level, space=RemoteWorkspace()):
        print ("INSTALL LSB SERVICE " + scriptfile + " FOR APPLICATION " + application)

        run('chmod u+x ' + space.workDir + '/' + scriptfile)

        sudo('mv ' + space.workDir + '/' + scriptfile + ' /etc/init.d/' + application)

        sudo('update-rc.d -f ' + application + ' remove')
        sudo('update-rc.d ' + application + ' defaults ' + start_level + ' ' + stop_level)

    def reboot(self):
        with settings(warn_only=True):
            sudo('reboot')
