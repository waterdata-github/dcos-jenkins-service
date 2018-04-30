import logging
from xml.etree import ElementTree

import config
import jenkins
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
        service_name = jen_conf[0]

        mesos_label = _create_random_label(service_name)
        _launch_jobs(service_name, job_count, single_use, xmin, mesos_label)


@pytest.mark.scalecleanup
def test_cleanup_scale():
    log.info("Removing all jobs.")
    jenkins.delete_all_jobs()
    log.info("Uninstalling {}.".format(config.SERVICE_NAME))
    sdk_install.uninstall(config.PACKAGE_NAME, config.SERVICE_NAME)


def _create_random_label(service_name):
    """Create a new Mesos Slave Info configuration with a random name.

    Args:
        service_name: Jenkins instance to add the label

    Returns: Random name of the new config created.

    """
    mesos_label = "mesos{}".format(sdk_utils.random_string())
    jenkins.create_mesos_slave_node(mesos_label,
                                    service_name=service_name)
    return mesos_label


def _launch_jobs(service_name, job_count, single_use, xmin, agent_label):
    """Create configured number of jobs with given config on Jenkins
    instance identified by `service_name`.

    Args:
        service_name: Jenkins service name
        job_count: Number of jobs to create and run
        single_use: Single Use Mesos agent on (true) or off
        xmin: A job should run every X minute(s)

    """
    job_name = 'generator-job'

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
                       'AGENT_LABEL': agent_label,
                       'SINGLE_USE':  single_use_str,
                       'EVERY_XMIN':  str(xmin)})
