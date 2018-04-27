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
def test_100_jobs(job_count, single_use, xmin):
    sdk_install.install(config.PACKAGE_NAME,
                        config.SERVICE_NAME,
                        0,
                        wait_for_deployment=False)

    job_name = 'generator-job'
    agent_label = sdk_utils.random_string()
    job_rand = sdk_utils.random_string()
    log.info("su type: {}".format(type(single_use)))
    single_use_str = '100'
    if not single_use or (
            type(single_use) == str and single_use.lower() == 'false'
    ):
        single_use_str = '0'

    r = jenkins_remote_access.add_slave_info(agent_label)
    assert r.status_code == 200, 'Got {} when trying to post MesosSlaveInfo'.format(
            r.status_code)
    assert agent_label in r.text, 'Label {} missing from {}'.format(agent_label,
                                                                    r.text)
    seed_config_xml = jenkins._get_job_fixture('gen-job.xml')
    seed_config_str = ElementTree.tostring(
            seed_config_xml.getroot(),
            encoding='utf8',
            method='xml')
    jenkins.create_seed_job(config.SERVICE_NAME, job_name, seed_config_str)

    log.info("Launching {} jobs every {} minutes with single-use set to: {}."
             .format(job_count, xmin, single_use))
    jenkins.run_job(config.SERVICE_NAME,
                    job_name,
                    **{'JOBCOUNT':   str(job_count),
                       'SINGLE_USE': single_use_str,
                       'EVERY_XMIN': str(xmin)})


@pytest.mark.scalecleanup
def test_cleanup_scale():
    log.info("Removing all jobs.")
    jenkins_remote_access.delete_all_jobs()
    log.info("Uninstalling {}.".format(config.SERVICE_NAME))
    sdk_install.uninstall(config.PACKAGE_NAME, config.SERVICE_NAME)
