import logging
import pytest
import uuid

import config
import jenkins
import time

@pytest.mark.scale
def test_create_10_jobs():
    for x in range(0, 9):
        #create 10 Hello world jobs executing every minute
        test_job_name = 'test-job-{}'.format(uuid.uuid4())
        jenkins.create_job(config.SERVICE_NAME, test_job_name)

@pytest.mark.scale
def test_create_10_jobs_custom_command():
    for x in (0, 9):
        #create 10 jobs with custom command executing every minute
        test_job_name = 'test-job-{}'.format(uuid.uuid4())
        jenkins.create_job(config.SERVICE_NAME, test_job_name, "echo \"test command\";")


@pytest.mark.scale
def test_create_10_jobs_custom_schedule():
    for x in range(0, 9):
        #create 10 jobs with custom command executing every 5 minute
        test_job_name = 'test-job-{}'.format(uuid.uuid4())
        jenkins.create_job(config.SERVICE_NAME, test_job_name, schedule_frequency_in_min=5)

@pytest.mark.scale
def test_create_100_jobs():
    for x in range(0, 99):
        #create 100 Helloworld jobs
        test_job_name = 'test-job-{}'.format(uuid.uuid4())
        jenkins.create_job(config.SERVICE_NAME, test_job_name)




    