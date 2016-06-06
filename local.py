from fabric.api import *
import os


class LocalWorkspace:
    def __init__(self, workDir='./tmp', templateDir='./templates'):
        self.workDir = workDir
        self.templateDir = templateDir
        # Create temporary directory for install workspace.
        local('mkdir -p ' + self.workDir)

    def __del__(self):
        # Cleanup install workspace.
        local('rm -r ' + self.workDir)

    def templatePath(self, template):
        dir_template = self.workDir + '/' + template
        if os.path.isfile(dir_template) is False:
            print ("Source template is not exist in the working directory.")
        else:
            return dir_template


class Distribution:
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
        self.identifier = identifier
        if (self.identifier is None):
            self.identifier = name
        self.keys = keys

    def printProperties(self):
        print ("=====================================================================")
        print ("Service name:           " + self.name)
        print ("Service path:           " + self.path)
        print ("Service description:    " + self.description)
        print ("Daemon:                 " + self.daemon)
        print ("Daemon arguments:       " + self.daemon_args)
        print ("Working directory:      " + self.work_dir)
        print ("Owner:                  " + self.user)
        print ("Group:                  " + self.group)
        print ("Pidfile:                " + self.pidfile)
        print ("Log path:               " + self.log_path)
        print ("Service start-level:    " + self.start_level)
        print ("Service stop-level:     " + self.stop_level)
        print ("Owner password:         " + self.password)
        print ("Script name:            " + self.scriptname)
        print ("=====================================================================")

    def generateLsbScript(self, templateLocation, space=LocalWorkspace()):
            local('cp ' + space.templatePath(templateLocation) + ' ' + space.workDir + '/' + self[self.identifier])

            s = open(space.workDir + '/' + self[self.identifier]).read()
            for key in self.keys:
                s = s.replace('<%s>' % (key), self[key])

                f = open(space.workDir + '/' + self[self.identifier], 'w')
            f.write(s)
            f.close()

            print ("LINUX BOOT SERVICE GENERATED: " + space.workDir + '/' + self[self.identifier])