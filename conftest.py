import logging
import os
import pytest
import sys

log_level = os.getenv('TEST_LOG_LEVEL', 'INFO').upper()
log_levels = ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL', 'EXCEPTION')
assert log_level in log_levels, \
    '{} is not a valid log level. Use one of: {}'.format(log_level,
                                                         ', '.join(log_levels))
# write everything to stdout due to the following circumstances:
# - shakedown uses print() aka stdout
# - teamcity splits out stdout vs stderr into separate outputs, we'd want them combined
logging.basicConfig(
        format='[%(asctime)s|%(name)s|%(levelname)s]: %(message)s',
        level=log_level,
        stream=sys.stdout)


def pytest_addoption(parser):
    #Required for all tests.
    parser.addoption('--pinned-hostname', action='store', type=str,
                     help='agent host to pin storage volumes to', required=True)
   
    #Needed for scale-testing, missing values will prompt scale test to error out.
    parser.addoption('--datadog-api-key', action='store', type=str, default=None,
                     help='datadog metrics api key')
    parser.addoption('--datadog-plugin-hostname', action='store', default=None,
                     type=str, help='hostname reported to datadog metrics service')

    #Default value for host-volume, can be overriden.
    parser.addoption('--pinned-host-volume', action='store', type=str, default='/tmp/jenkins',
                     help='storage volume location for jenkins data. ')

    #Default values and arguments for load testing.
    parser.addoption('--masters', action='store', default=1, type=int,
                     help='Number of Jenkins masters to launch.')
    parser.addoption('--jobs', action='store', default=1, type=int,
                     help='Number of test jobs to launch.')
    parser.addoption('--single-use', action='store_true',
                     help='Use Mesos Single-Use agents')
    parser.addoption('--run-delay', action='store', default=1,
                     type=int, help='Run job every X minutes.')
    parser.addoption('--cpu-quota', action='store', default=0.0,
                     type=float, help='CPU quota to set. 0.0 to set no'
                                      ' quota.')
    parser.addoption('--work-duration', action='store', default=600,
                     type=int, help='Duration, in seconds, for the '
                                    'workload to last (sleep).')
    parser.addoption('--mom', action='store', default='',
                     help='Marathon on Marathon instance name.')
    parser.addoption('--external-volume', action='store_true',
                     help='Use rexray external volumes.')
    parser.addoption('--scenario', action='store', default='sleep',
                     help='Test scenario to run (sleep, buildmarathon) '
                          '(default: sleep).')
    parser.addoption('--min', action='store', default=-1,
                     help='min jenkins index to start from'
                          '(default: -1).')
    parser.addoption('--max', action='store', default=-1,
                     help='max jenkins index to end at'
                          '(default: -1).')
    parser.addoption('--batch-size', action='store', default=1,
                     help='batch size to deploy jenkins masters in'
                          '(default: 1).')

@pytest.fixture
def master_count(request) -> int:
    return int(request.config.getoption('--masters'))

@pytest.fixture
def job_count(request) -> int:
    return int(request.config.getoption('--jobs'))

@pytest.fixture
def single_use(request) -> bool:
    return bool(request.config.getoption('--single-use'))

@pytest.fixture
def run_delay(request) -> int:
    return int(request.config.getoption('--run-delay'))

@pytest.fixture
def cpu_quota(request) -> float:
    return float(request.config.getoption('--cpu-quota'))

@pytest.fixture
def work_duration(request) -> int:
    return int(request.config.getoption('--work-duration'))

@pytest.fixture
def mom(request) -> str:
    return request.config.getoption('--mom')

@pytest.fixture
def scenario(request) -> str:
    return request.config.getoption('--scenario')

@pytest.fixture
def external_volume(request) -> bool:
    return bool(request.config.getoption('--external-volume'))

@pytest.fixture
def min_index(request) -> int:
    return int(request.config.getoption('--min'))

@pytest.fixture
def max_index(request) -> int:
    return int(request.config.getoption('--max'))

@pytest.fixture
def batch_size(request) -> int:
    return int(request.config.getoption('--batch-size'))

@pytest.fixture
def pinned_hostname(request) -> str:
    return request.config.getoption('--pinned-hostname')

@pytest.fixture
def pinned_host_volume(request) -> str:
    return request.config.getoption('--pinned-host-volume')

@pytest.fixture
def datadog_api_key(request) -> str:
    return request.config.getoption('--datadog-api-key')

@pytest.fixture
def datadog_plugin_hostname(request) -> str:
    return request.config.getoption('--datadog-plugin-hostname')

