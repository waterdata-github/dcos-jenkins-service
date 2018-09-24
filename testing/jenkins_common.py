import logging
import time
from threading import Thread, Lock
from typing import List, Set
from xml.etree import ElementTree

import config
import jenkins
import pytest
import sdk_dcos
import sdk_marathon
import sdk_quota
import sdk_security
import sdk_utils
import shakedown
import json

from sdk_dcos import DCOS_SECURITY

log = logging.getLogger(__name__)

LOCK = Lock()
ACCOUNTS = {}

TIMINGS = {"deployments": {}, "serviceaccounts": {}}

SHARED_ROLE = "jenkins-role"
DOCKER_IMAGE="mesosphere/jenkins-dind:0.6.0-alpine"

def setup_quota(role, cpus):
    current_quotas = sdk_quota.list_quotas()
    if "infos" not in current_quotas:
        _set_quota(role, cpus)
        return

    match = False
    for quota in current_quotas["infos"]:
        if quota["role"] == role:
            match = True
            break

    if match:
        sdk_quota.remove_quota(role)
    _set_quota(role, cpus)


def _set_quota(role, cpus):
    sdk_quota.create_quota(role, cpus=cpus)


def create_service_accounts(service_name, security=None):
    if security == DCOS_SECURITY.strict:
        try:
            start = time.time()
            log.info("Creating service accounts for '{}'"
                     .format(service_name))
            sa_name = "{}-principal".format(service_name)
            sa_secret = "jenkins-{}-secret".format(service_name)
            sdk_security.create_service_account(
                    sa_name, sa_secret, service_name)

            sdk_security.grant_permissions(
                    'root', '*', sa_name)

            sdk_security.grant_permissions(
                    'root', SHARED_ROLE, sa_name)
            end = time.time()
            ACCOUNTS[service_name] = {}
            ACCOUNTS[service_name]["sa_name"] = sa_name 
            ACCOUNTS[service_name]["sa_secret"] = sa_secret
            
            TIMINGS["serviceaccounts"][service_name] = end - start
        except Exception as e:
            log.warning("Error encountered while creating service account: {}".format(e))
            raise e


def install_jenkins(service_name,
                     client=None,
                     security=None,
                     **kwargs):
    """Install Jenkins service.

    Args:
        service_name: Service Name or Marathon ID (same thing)
        client: Marathon client connection
        external_volume: Enable external volumes
    """
    def _wait_for_deployment(app_id, client):
        with LOCK:
            res = len(client.get_deployments(app_id)) == 0
        return res

    try:
        if security == DCOS_SECURITY.strict:
            kwargs['strict_settings'] = {
                'secret_name':  ACCOUNTS[service_name]["sa_secret"],
                'mesos_principal': ACCOUNTS[service_name]["sa_name"],
            }
            kwargs['service_user'] = 'root'

        pinned_hostname = kwargs['pinned_hostname']
        pinned_host_volume = kwargs['pinned_host_volume']
        
        log.info("Installing jenkins '{}' on host '{}' at host-volume '{}'".
                format(service_name, pinned_hostname, pinned_host_volume))
        jenkins.install(service_name,
                        client,
                        role=SHARED_ROLE,
                        fn=_wait_for_deployment,
                        **kwargs)
    except Exception as e:
        log.warning("Error encountered while installing Jenkins: {}".format(e))
        raise e


def install_jenkins_datadog_metrics_plugin(service_name,
                                            datadog_plugin_hostname,
                                            datadog_api_key):
    """Install Jenkins DataDog Metrics Plugin.

    Args:
        service_name: Service Name or Marathon ID (same thing)
        datadog_plugin_hostname: Hostname reported to DataDog Metrics service
        datadog_api_key: API Key for DataDog Metrics
    """
    try:
        log.info("Installing jenkins datadog metrics plugins '{}'".format(service_name))
        jenkins.install_datadog_metrics_plugin(service_name, datadog_plugin_hostname, datadog_api_key)  
    except Exception as e:
        log.warning("Error encountered while installing Jenkins DataDog Metrics Plugin: {}".format(e))
        raise e


def cleanup_jenkins_install(service_name, **kwargs):
    """Delete all jobs and uninstall Jenkins instance.

    Args:
        service_name: Service name or Marathon ID
    """
    if service_name.startswith('/'):
        service_name = service_name[1:]
    try:
        log.info("Removing all jobs on {}.".format(service_name))
        jenkins.delete_all_jobs(service_name, retry=False)
    finally:
        log.info("Uninstalling {}.".format(service_name))
        jenkins.uninstall(service_name,
                          package_name=config.PACKAGE_NAME,
                          **kwargs)


def create_jobs(service_name, **kwargs):
    """Create jobs on deployed Jenkins instances.

    All functionality around creating jobs should go here.

    Args:
        service_name: Jenkins instance name
    """
    m_label = _create_executor_configuration(service_name)
    _launch_jobs(service_name, label=m_label, **kwargs)


def _create_executor_configuration(service_name: str) -> str:
    """Create a new Mesos Slave Info configuration with a random name.

    Args:
        service_name: Jenkins instance to add the label

    Returns: Random name of the new config created.

    """
    mesos_label = "mesos"
    jenkins.create_mesos_slave_node(mesos_label,
                                    service_name=service_name,
                                    dockerImage=DOCKER_IMAGE,
                                    executorCpus=0.3,
                                    executorMem=1800,
                                    idleTerminationMinutes=1,
                                    timeout_seconds=600)
    return mesos_label


def _launch_jobs(service_name: str,
                 jobs: int = 1,
                 single: bool = False,
                 delay: int = 3,
                 duration: int = 600,
                 label: str = None,
                 scenario: str = None):
    """Create configured number of jobs with given config on Jenkins
    instance identified by `service_name`.

    Args:
        service_name: Jenkins service name
        jobs: Number of jobs to create and run
        single: Single Use Mesos agent on (true) or off
        delay: A job should run every X minute(s)
        duration: Time, in seconds, for the job to sleep
        label: Mesos label for jobs to use
    """
    job_name = 'generator-job'
    single_use_str = '100' if single else '0'

    seed_config_xml = jenkins._get_job_fixture('gen-job.xml')
    seed_config_str = ElementTree.tostring(
            seed_config_xml.getroot(),
            encoding='utf8',
            method='xml')
    jenkins.create_seed_job(service_name, job_name, seed_config_str)
    log.info(
            "Launching {} jobs every {} minutes with single-use "
            "({}).".format(jobs, delay, single))

    jenkins.run_job(service_name,
                    job_name,
                    timeout_seconds=600,
                    **{'JOBCOUNT':       str(jobs),
                       'AGENT_LABEL':    label,
                       'SINGLE_USE':     single_use_str,
                       'EVERY_XMIN':     str(delay),
                       'SLEEP_DURATION': str(duration),
                       'SCENARIO':       scenario})
