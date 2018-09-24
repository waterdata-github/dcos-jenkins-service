"""
A way to launch numerous Jenkins masters and jobs with pytest.

Pre-requisites. Have the following environment variables exported with appropriate values:
    * DCOS_CLUSTER_URL
    * DCOS_LOGIN_USERNAME
    * DCOS_LOGIN_PASSWORD

From the CLI, this can be run as follows:
    $ PYTEST_ARGS="--pinned-hostname=10.0.2.108 \
                --pinned-host-volume=/tmp/jenkins-soak \
                --datadog-api-key=<datadog_api_key> \
                --datadog-plugin-hostname=jenkins.soakCLUSTERVERSIONHERE.mesosphe.re" ./test.sh -m soak jenkins
And to clean-up a test run of Jenkins instances:
    $ ./test.sh -m soakcleanup jenkins

This supports the following configuration params:
    * Number of jobs for each master (--jobs); this will be the same
        count on each Jenkins instance. --jobs=10 will create 10 jobs
        on each instance.
    * How often, in minutes, to run a job (--run-delay); this is used
        to create a cron schedule: "*/run-delay * * * *"
    * To enable or disable "Mesos Single-Use Agent"; this is a toggle
        and applies to all jobs equally. (default: False)
    * How long, in seconds, for a job to "work" (sleep)
        (--work-duration)
    * To enable or disable External Volumes (--external-volume);
        this uses rexray (default: False)
    * What test scenario to run (--scenario); supported values:
        - sleep (sleep for --work-duration)
        - buildmarathon (build the open source marathon project)
    * Which hostname to install on. NOTE: Must be Private Node IP! (--pinned-hostname);
        - the Jenkins installation location is tied to storage agents, 
        we need to pin installations to specific agents on service restarts.
        - Must be a private node, else Marathon won't deploy. (i.e musn't have public_ip attribute)
    * Location of host-volume. (--pinned-host-volume=/tmp/jenkins)
    * DataDog API Key (--datadog-api-key)
        - Needed to for the DataDog metrics service.
    * DataDog HostName (--datadog-plugin-hostname)
        - Hostname reported to the DataDog metrics service.
For additional details see conftest.py in the root folder.
"""
import pprint
import logging
import time
from threading import Thread, Lock
from typing import List, Set
from xml.etree import ElementTree

import config
import jenkins
import jenkins_common
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

@pytest.mark.soak
def test_scaling_soak(job_count,
                      single_use: bool,
                      run_delay,
                      work_duration,
                      external_volume: bool,
                      scenario,
                      pinned_hostname,
                      pinned_host_volume,
                      datadog_api_key,
                      datadog_plugin_hostname) -> None:

    """Launch a soak test scenario.

    Configuration, installation and jobs are launched serially.

    Args:
        job_count: Number of Jobs on each Jenkins master
        single_use: Mesos Single-Use Agent on (true) or off (false)
        run_delay: Jobs should run every X minute(s)
        work_duration: Time, in seconds, for generated jobs to sleep
        scenario: Jenkins senarios, one of 'sleep' or 'buildmarathon'
        pinned_hostname: IP address of node to pin Jenkins to.
        pinned_host_volume: Location of temporary storage on specified host.
        datadog_api_key: API required for DataDog metrics service.
        datadog_plugin_hostname: Hostname reported to the DataDog metrics service.
    """
    security_mode = sdk_dcos.get_security_mode()
    
    # create marathon client
    marathon_client = shakedown.marathon.create_client()

    service_name = "jenkins-soak"
    
    # create service accounts
    sdk_security.install_enterprise_cli()

    # create service accounts
    jenkins_common.create_service_accounts(service_name, security=security_mode)

    # launch Jenkins services
    jenkins_common.install_jenkins(service_name,
                                    client=marathon_client,
                                    external_volume=external_volume,
                                    security=security_mode,
                                    pinned_hostname=pinned_hostname,
                                    pinned_host_volume=pinned_host_volume)
   
    # install DataDog metrics plugin
    jenkins_common.install_jenkins_datadog_metrics_plugin(service_name, datadog_plugin_hostname, datadog_api_key)
    
    # the rest of the commands require a running Jenkins instance
    jenkins_common.create_jobs(service_name,
                                jobs=job_count,
                                single=single_use,
                                delay=run_delay,
                                duration=work_duration,
                                scenario=scenario)

@pytest.mark.soakcleanup
def test_cleanup_soak(mom) -> None:
    """Blanket clean-up of jenkins instances on a DC/OS cluster.

    1. Queries Marathon for all apps matching "jenkins" prefix
    2. Delete all jobs on running Jenkins instances
    3. Uninstall all found Jenkins installs
    """
    r = sdk_marathon.filter_apps_by_id('jenkins', mom)
    jenkins_apps = r.json()['apps']
    jenkins_ids = [x['id'] for x in jenkins_apps]

    service_ids = list()
    for service_id in jenkins_ids:
        if service_id.startswith('/'):
            service_id = service_id[1:]
        # skip over '/jenkins' instance - not setup by tests
        if service_id == 'jenkins':
            continue
        service_ids.append(service_id)
  
    # remove each service_id
    for service_id in service_ids:
        jenkins_common.cleanup_jenkins_install(service_id, mom=mom) 
