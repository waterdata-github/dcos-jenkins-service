import logging
from xml.etree import ElementTree

import config
import jenkins
import jenkins_remote_access
import pytest
import sdk_install
import sdk_utils

log = logging.getLogger(__name__)


@pytest.mark.scale
def test_scaling_load(master_count,
                      job_count,
                      single_use,
                      xmin):
    """Launch a load test scenario. This does not verify the results
    of the test, but does ensure the instances and jobs were created.

    Args:
        master_count: Number of Jenkins masters or instances
        job_count: Number of Jobs on each Jenkins master
        single_use: Mesos Single-Use Agent on (true) or off (false)
        xmin: Jobs should run every X minute(s)
    """
    masters = [("jenkins{}".format(sdk_utils.random_string()), 50000 + i)
               for i in range(0, int(master_count))]
    # launch Jenkins services
    for jen_conf in masters:
        jenkins.install(jen_conf[0], jen_conf[1])
    # now try to launch jobs
    for jen_conf in masters:
        launch_jobs(jen_conf[0], job_count, single_use, xmin)


@pytest.mark.scalecleanup
def test_cleanup_scale():
    log.info("Removing all jobs.")
    jenkins_remote_access.delete_all_jobs()
    log.info("Uninstalling {}.".format(config.SERVICE_NAME))
    sdk_install.uninstall(config.PACKAGE_NAME, config.SERVICE_NAME)


def launch_jobs(service_name, job_count, single_use, xmin):
    """Create configured number of jobs with given config on Jenkins
    instance identified by `service_name`.

    Args:
        service_name: Jenkins service name
        job_count: Number of jobs to create and run
        single_use: Single Use Mesos agent on (true) or off
        xmin: A job should run every X minute(s)

    """
    job_name = 'generator-job'

    mesosLabel = "mesos{}".format(sdk_utils.random_string())
    jenkins_remote_access.add_slave_info(mesosLabel,
                                         service_name=service_name)

    single_use_str = '100'
    if not single_use or (
            type(single_use) == str and single_use.lower() == 'false'
    ):
        single_use_str = '0'

    seed_config_xml = jenkins._get_job_fixture('gen-job.xml')
    seed_config_str = ElementTree.tostring(
            seed_config_xml.getroot(),
            encoding='utf8',
            method='xml')
    jenkins.create_seed_job(service_name, job_name, seed_config_str)
    log.info(
            "Launching {} jobs every {} minutes with single-use set to: {}."
                .format(job_count, xmin, single_use))
    jenkins.run_job(service_name,
                    job_name,
                    **{'JOBCOUNT':    str(job_count),
                       'AGENT_LABEL': mesosLabel,
                       'SINGLE_USE':  single_use_str,
                       'EVERY_XMIN':  str(xmin)})
