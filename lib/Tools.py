#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

import PerfKit
import Rally
import Shaker
import logging
import os
import subprocess
import yaml
import re
from pykwalify import core as pykwalify_core
from pykwalify import errors as pykwalify_errors


class Tools(object):

    def __init__(self, config=None):
        self.logger = logging.getLogger('browbeat.Tools')
        self.config = config
        return None

    # Run command, return stdout as result
    def run_cmd(self, cmd):
        self.logger.debug("Running command : %s" % cmd)
        process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()
        if len(stderr) > 0:
            return None
        else:
            return stdout.strip()

    # Find Command on host
    def find_cmd(self, cmd):
        _cmd = "which %s" % cmd
        self.logger.debug('Find Command : Command : %s' % _cmd)
        command = self.run_cmd(_cmd)
        if command is None:
            self.logger.error("Unable to find %s" % cmd)
            raise Exception("Unable to find command : '%s'" % cmd)
            return False
        else:
            return command.strip()

    def create_run_dir(self, results_dir, run):
        try:
            os.makedirs("%s/run-%s" % (results_dir, run))
            return "%s/run-%s" % (results_dir, run)
        except OSError:
            return False

    # Create directory for results
    def create_results_dir(self, results_dir, timestamp, service, scenario):
        the_directory = "{}/{}/{}/{}".format(results_dir,
                                             timestamp, service, scenario)
        if not os.path.isdir(the_directory):
            try:
                os.makedirs(the_directory)
            except OSError as err:
                self.logger.error(
                    "Error creating the results directory: {}".format(err))
                return False
        return the_directory

    def _load_config(self, path, validate=True):
        try:
            stream = open(path, 'r')
        except IOError:
            self.logger.error(
                "Configuration file {} passed is missing".format(path))
            exit(1)
        config = yaml.load(stream)
        stream.close()
        self.config = config
        if validate:
            self.validate_yaml()
        return config

    def validate_yaml(self):
        self.logger.info(
            "Validating the configuration file passed by the user")
        stream = open("lib/validate.yaml", 'r')
        schema = yaml.load(stream)
        check = pykwalify_core.Core(
            source_data=self.config, schema_data=schema)
        try:
            check.validate(raise_exception=True)
            self.logger.info("Validation successful")
        except pykwalify_errors.SchemaError as e:
            self.logger.error("Schema Validation failed")
            raise Exception('File does not conform to schema: {}'.format(e))

    def _run_workload_provider(self, provider):
        self.logger = logging.getLogger('browbeat')
        if provider == "perfkit":
            perfkit = PerfKit.PerfKit(self.config)
            perfkit.start_workloads()
        elif provider == "rally":
            rally = Rally.Rally(self.config)
            rally.start_workloads()
        elif provider == "shaker":
            shaker = Shaker.Shaker(self.config)
            shaker.run_shaker()
        else:
            self.logger.error("Unknown workload provider: {}".format(provider))

    def check_metadata(self):
        meta = self.config['elasticsearch']['metadata_files']
        for _meta in meta:
            if not os.path.isfile(_meta['file']):
                self.logger.error(
                    "Metadata file {} is not present".format(_meta['file']))
                return False
        return True

    def gather_metadata(self):
        os.putenv("ANSIBLE_SSH_ARGS",
                  " -F {}".format(self.config['ansible']['ssh_config']))
        ansible_cmd = \
            'ansible-playbook -i {} {}' \
            .format(self.config['ansible']['hosts'], self.config['ansible']['metadata'])
        self.run_cmd(ansible_cmd)
        if not self.check_metadata():
            self.logger.warning("Metadata could not be gathered")
            return False
        else:
            self.logger.info("Metadata about cloud has been gathered")
            return True

    def post_process(self, cli):
        workloads = {}
        workloads['shaker'] = re.compile("shaker")
        workloads['perfkit'] = re.compile("perfkit")
        workloads['rally'] = re.compile("(?!perfkit)|(?!shaker)")
        """ Iterate through dir structure """
        results = {}
        if os.path.isdir(cli.path):
            for dirname, dirnames, files in os.walk(cli.path):
                self.logger.info("Inspecting : %s" % dirname)
                results[dirname] = files
        else:
            self.logger.error("Path does not exist")
            return False

        """ Capture per-workload results """
        workload_results = {}
        json = re.compile("\.json")
        if len(results) > 0:
            for path in results:
                for regex in workloads:
                    if re.findall(workloads[regex], path):
                        if regex not in workload_results:
                            workload_results[regex] = []
                        for file in results[path]:
                            if (re.findall(json, file) and
                                    'result_index-es' not in file):
                                workload_results[regex].append(
                                    "{}/{}".format(path, file))
        else:
            self.logger.error("Results are empty")
            return False

        """ Iterate through each workload result, generate ES JSON """
        if len(workload_results) > 0:
            for workload in workload_results:
                if workload is "rally":
                    rally = Rally.Rally(self.config)
                    for file in workload_results[workload]:
                        errors, results = rally.file_to_json(file)
                if workload is "shaker":
                    # Stub for Shaker.
                    continue
                if workload is "perfkit":
                    # Stub for PerfKit.
                    continue
