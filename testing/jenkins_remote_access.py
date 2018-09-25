#!/usr/bin/env python3

import logging
import jenkins
from string import Template
import time

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG, format="%(message)s")


IMPORTS = """
import org.jenkinsci.plugins.mesos.MesosCloud;
import org.jenkinsci.plugins.mesos.MesosSlaveInfo;
import org.apache.mesos.Protos;
import hudson.slaves.NodeProperty;
import jenkins.model.*
import org.jenkinsci.plugins.mesos.MesosSlaveInfo.URI;
import hudson.tasks.*;
import com.cloudbees.hudson.plugins.folder.Folder;
"""

DOCKER_CONTAINER = """
def containerInfo = new MesosSlaveInfo.ContainerInfo(
                "DOCKER",
                "$dockerImage",
                true,
                false,
                false,
                true,
                "wrapper.sh",
                new LinkedList<MesosSlaveInfo.Volume>(),
                new LinkedList<MesosSlaveInfo.Parameter>(),
                Protos.ContainerInfo.DockerInfo.Network.BRIDGE.name(),
                new LinkedList<MesosSlaveInfo.PortMapping>(),
                new LinkedList<MesosSlaveInfo.NetworkInfo>()
)
"""

MESOS_SLAVE_INFO_OBJECT = """
def additionalURIs = new LinkedList<URI>()
additionalURIs.add(new URI("file:///etc/docker/docker.tar.gz", false, true))

def mesosSlaveInfo = new MesosSlaveInfo(
        "$labelString",
        $mode,
        "$slaveCpus",
        "$slaveMem",
        "$minExecutors",
        "$maxExecutors",
        "$executorCpus",
        "$diskNeeded",
        "$executorMem",
        "$remoteFSRoot",
        "$idleTerminationMinutes",
        "$slaveAttributes",
        "$jvmArgs",
        "$jnlpArgs",
        "$defaultSlave",
        $containerInfo,
        new LinkedList<URI>(),
        new LinkedList<? extends NodeProperty<?>>()
)
"""

MESOS_SLAVE_INFO_ADD = """
MesosCloud cloud = MesosCloud.get();
cloud.getSlaveInfos().add(mesosSlaveInfo)
cloud.getSlaveInfos().each {
        t ->
            println("Label : " + t.getLabelString())
}
"""

MESOS_SLAVE_INFO_REMOVE = """
MesosCloud cloud = MesosCloud.get();
Iterator<MesosSlaveInfo> it = cloud.getSlaveInfos().iterator()
while(it.hasNext()) {
    MesosSlaveInfo msi = it.next();
    if (msi.getLabelString().equals("$labelString")){
        it.remove()
    }
}
cloud.getSlaveInfos().each {
        t ->
            println("Label : " + t.getLabelString())
}
"""

DELETE_ALL_JOBS = """
Jenkins.instance.items.each { job -> job.delete() }
"""

JENKINS_JOB_FAILURES = """
def activeJobs = hudson.model.Hudson.instance.items.findAll{job -> !(job instanceof Folder) && job.isBuildable()}
println("successjobs = " +activeJobs.size())
def failedRuns = activeJobs.findAll{job -> job.lastBuild != null && !(job.lastBuild.isBuilding()) && job.lastBuild.result == hudson.model.Result.FAILURE}
println("failedjobs = " +failedRuns.size())
BUILD_STRING = "Build step 'Execute shell' marked build as failure"

failedRuns.each{ item ->
    println "Failed Job Name: ${item.name}"
    item.lastBuild.getLog().eachLine { line ->
        if (line =~ /$BUILD_STRING/) {
            println "error: $line"
        }
    }
}
"""

CREDENTIAL_CHANGE = """
import com.cloudbees.plugins.credentials.impl.UsernamePasswordCredentialsImpl

MesosCloud cloud = MesosCloud.get();

def changePassword = { new_username, new_password ->
    def c = cloud.credentials

    if ( c ) {
        def credentials_store = Jenkins.instance.getExtensionList(
            'com.cloudbees.plugins.credentials.SystemCredentialsProvider'
            )[0].getStore()

        def result = credentials_store.updateCredentials(
            com.cloudbees.plugins.credentials.domains.Domain.global(),
            c,
            new UsernamePasswordCredentialsImpl(c.scope, c.id, c.description, new_username, new_password)
            )

        if (result) {
            println "changed jenkins creds"
        } else {
            println "failed to change jenkins creds"
        }
    } else {
      println "could not find credential for jenkins"
    }
}

changePassword('$userName', 'abcdefg')

cloud.restartMesos()
"""


CREDENTIAL_CHANGE = """
import com.cloudbees.plugins.credentials.impl.UsernamePasswordCredentialsImpl

MesosCloud cloud = MesosCloud.get();

def changePassword = { new_username, new_password ->
    def c = cloud.credentials

    if ( c ) {
        def credentials_store = Jenkins.instance.getExtensionList(
            'com.cloudbees.plugins.credentials.SystemCredentialsProvider'
            )[0].getStore()

        def result = credentials_store.updateCredentials(
            com.cloudbees.plugins.credentials.domains.Domain.global(),
            c,
            new UsernamePasswordCredentialsImpl(c.scope, c.id, c.description, new_username, new_password)
            )

        if (result) {
            println "changed jenkins creds"
        } else {
            println "failed to change jenkins creds"
        }
    } else {
      println "could not find credential for jenkins"
    }
}

changePassword('$userName', 'abcdefg')

cloud.restartMesos()
"""

INSTALL_DATADOG = """
import jenkins.model.*
import java.util.logging.Logger
def logger = Logger.getLogger("")
def installed = false
def initialized = false
def pluginParameter="Datadog"
def plugins = pluginParameter.split()
logger.info("" + plugins)
def instance = Jenkins.getInstance()
def pm = instance.getPluginManager()
def uc = instance.getUpdateCenter()
plugins.each {
  logger.info("Checking " + it)
  if (!pm.getPlugin(it)) {
    logger.info("Looking UpdateCenter for " + it)
    if (!initialized) {
      uc.updateAllSites()
      initialized = true
    }
    def plugin = uc.getPlugin(it)
    if (plugin) {
      logger.info("Installing " + it)
    	def installFuture = plugin.deploy()
      while(!installFuture.isDone()) {
        logger.info("Waiting for plugin install: " + it)
        sleep(3000)
      }
      installed = true
    }
  }
}
if (installed) {
  logger.info("Plugins installed, initializing a restart!")
  instance.save()
  instance.restart()
}
"""

CONFIGURE_DATADOG = """
import jenkins.model.*
import org.datadog.jenkins.plugins.datadog.DatadogBuildListener

def j = Jenkins.getInstance()
def d = j.getDescriptor("org.datadog.jenkins.plugins.datadog.DatadogBuildListener")
d.setHostname('$hostname')
d.setTagNode(true)
d.setApiKey('$apikey')
d.save()
"""


def add_slave_info(
        labelString,
        service_name,
        dockerImage="mesosphere/jenkins-dind:0.7.0-ubuntu",
        slaveCpus="0.1",
        slaveMem="256",
        minExecutors="1",
        maxExecutors="1",
        executorCpus="0.4",
        diskNeeded="0.0",
        executorMem="512",
        mode="Node.Mode.NORMAL",
        remoteFSRoot="jenkins",
        idleTerminationMinutes="5",
        slaveAttributes="",
        jvmArgs="-Xms16m -XX:+UseConcMarkSweepGC -Djava.net.preferIPv4Stack=true",
        jnlpArgs="-noReconnect",
        defaultSlave="false",
        **kwargs
):
    slaveInfo = Template(MESOS_SLAVE_INFO_OBJECT).substitute({
         "labelString": labelString,
         "mode": mode,
         "slaveCpus": slaveCpus,
         "slaveMem": slaveMem,
         "minExecutors": minExecutors,
         "maxExecutors": maxExecutors,
         "executorCpus": executorCpus,
         "diskNeeded": diskNeeded,
         "executorMem": executorMem,
         "remoteFSRoot": remoteFSRoot,
         "idleTerminationMinutes": idleTerminationMinutes,
         "slaveAttributes": slaveAttributes,
         "jvmArgs": jvmArgs,
         "jnlpArgs": jnlpArgs,
         "defaultSlave": defaultSlave,
         "containerInfo": "containerInfo",
    })

    containerInfo = Template(DOCKER_CONTAINER).substitute({
        "dockerImage": dockerImage,
    })

    return make_post(
        containerInfo +
        slaveInfo +
        MESOS_SLAVE_INFO_ADD,
        service_name,
        **kwargs,
    )


def remove_slave_info(labelString, service_name):
    return make_post(
        Template(MESOS_SLAVE_INFO_REMOVE).substitute(
            {
                'labelString': labelString
            }
        ),
        service_name
    )


def delete_all_jobs(**kwargs):
    return make_post(DELETE_ALL_JOBS, **kwargs)


def get_job_failures(service_name):
    return make_post(JENKINS_JOB_FAILURES, service_name)


def change_mesos_creds(mesos_username, service_name):
    return make_post(
        Template(CREDENTIAL_CHANGE).substitute(
            {
                'userName': mesos_username,
            }
        ),
        service_name)


def change_mesos_creds(mesos_username, service_name):
    return make_post(
        Template(CREDENTIAL_CHANGE).substitute(
            {
                'userName': mesos_username,
            }
        ),
        service_name)

def install_datadog_plugin(service_name):
    ret = make_post(
        Template(INSTALL_DATADOG).substitute(
            {
            }
        ),
        service_name)
    # we're restarting Jenkins, so we sleep after the post to make sure Jenkins is up.
    # TODO: this might be flaky, come up with a better test to see if Jenkins is up.
    time.sleep(60)
    return ret

def configure_datadog_plugin(jenkins_hostname, datadog_api_key, service_name):
    return make_post(
        Template(CONFIGURE_DATADOG).substitute(
            {
                'hostname': jenkins_hostname,
                'apikey': datadog_api_key,
            }
        ),
        service_name)

def make_post(
        post_body,
        service_name,
        **kwargs
):
    """
    :rtype: requests.Response
    """
    body = IMPORTS + post_body
    log.info('\nMaking request : ========\n{}\n========\n'.format(body))
    '''
    Note: To run locally:
    curl -i -H "Authorization:token=$(dcos config show core.dcos_acs_token)" \
         -k --data-urlencode "script=$(< <path-to-above-script-file>)" \
         https://<dcos-cluster>/service/jenkins/scriptText'
    '''
    import sdk_cmd
    return sdk_cmd.service_request(
        'POST',
        service_name,
        'scriptText',
        log_args=False,
        data={'script': body},
        **kwargs,
    )
