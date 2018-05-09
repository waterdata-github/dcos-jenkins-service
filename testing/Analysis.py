import os
from xml.etree import ElementTree

import sdk_cmd
import sdk_install
import jenkins_remote_access

from shakedown import *

#classes
class JenkinsMasterStat
    __init__(self):
        self.num_jobs_failing = 0
        self.num_jobs_succeeding = 0
        self.job_stat_list = []


class ClusterStat
    __init__(self):
        self.jenkins_master_stat_list = []
        self._top_failing_masters = []
        self._top_failing_job_causes = []
        self.total_failures = []

        def calculate():



#main methoods
def generate_report(top_n_failing_jenkins=4, top_n_failing_causes=1)
    
    cluster_info = calculate_cluster_stats(jenkins_list)

    print("====================Jenkins Error Report=========================================")
    print("total failures:" + cluster_info.total_failures)
    print("top failing agents: " + clister._top_failing_masters)
    print("top failiure causes: " + cluster._top_failing_job_causes)
    orint("==================================================================================")


def calculate_cluster_stats(agent_list[])

    var cluster_stats = ClusterStat()
    for jenkins in jenkins_list
        jenkin_stat = get_and_parse_jobs(jenkins_name)
        cluster_stats.jenkins_master_stat_list.insert(jenkin_stat)


    cluster_stats.calculate()

    return cluster_stats

def get_and_parse_jobs(service_name):
     r = jenkins_remote_access.get_job_failures(service_name)
     return create_jenkins_master_info(r.text)
#helper methods
#def create_job_error(error_line)
#    return JobError()

def create_jenkins_master_info(error_text):
    line_no = 0 
    num_jobs_succeeding = 0
    num_jobs_failing = 0
    failed_job_list = []
    for line in error_text:
        #LINE 1 
        if line_no == 0:
            num_jobs_succeeding = line[-1:]
        else if line_no == 1
            num_jobs_failing = line[-1:]
        else
            failed_job_list.insert(line)

    jenkins_stat = JenkinsMasterStat()
    jenkins_stat.num_jobs_failing = num_jobs_failing
    jenkins_stat.num_jobs_succeeding = num_jobs_succeeding
    jenkins_stat.job_stat_list = failed_job_list




