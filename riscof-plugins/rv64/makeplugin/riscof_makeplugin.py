import os
import re
import shutil
import subprocess
import shlex
import logging
import random
import string
from string import Template

import riscof.utils as utils
from riscof.pluginTemplate import pluginTemplate
import riscof.constants as constants
from riscv_isac.isac import isac

logger = logging.getLogger()

var_regex = r"^([a-zA-Z0-9_]+)[ ]*[?]?=(.*)$"
# The abi string to be passed to the compiler. The format adheres to the mabi
# argument of GCC. To change how this string is derived, change this function.
def mabi(isa):
    isa = isa.lower()
    abi = 'lp64' if '64' in isa else 'ilp32'
    if 'd' in isa:
        abi += 'd'
    elif 'f' in isa:
        abi += 'f'
    return abi
def getmakevars(arg):
    with open(arg,"r") as fp:
        lines = [line.strip() for line in fp.readlines()]
        lines = '\n'.join(lines)
        lines = lines.replace("\\\n"," ")
        larr = lines.split("\n")
        ret_dict = {}
        for entry in larr:
            x = re.sub("((\\t)+)",lambda x:" ",entry)
            x = re.sub("((  )+)",lambda x:" ",entry)
            match = re.match(var_regex,x)
            if match:
                key = match.group(1)
                val = match.group(2)
                ret_dict[key] = val
        return ret_dict

class makeplugin(pluginTemplate):
    # The target name and version info printed in the reports. These variables can be defined here
    # statically or dynamically extracted from other sources.
    __model__ = "makeplugin"
    __version__ = "0.0.1"

    def __init__(self, *args, **kwargs):
        sclass = super().__init__(*args, **kwargs)

        # Get the node for the plugin in the config.ini file. This is extracted by riscof and only
        # the node relevant to the plugin is passed.
        config = kwargs.get('config')

        # Extract all information from the nodes. If any required values are missing, an error and a
        # system exit is raised.
        if 'makefiles' not in config:
            logger.error("Path to the Makefiles not specified for "+self.__model__)
            raise SystemExit
        if 'ispec' not in config or 'pspec' not in config:
            logger.error("Path to the input YAML files not specified for "+self.__model__)
            raise SystemExit
        # Paths to the Makefile.include files. Mandatory to be provided
        self.makefiles = [os.path.abspath(path) for path in config['makefiles'].split(",")]
        # Number of jobs to launch in parallel
        self.num_jobs = str(config['jobs'] if 'jobs' in config else 1)
        # Path to the directory in which this file is present
        self.pluginpath = os.path.dirname(__file__)
        # Path to the input ISA yaml as per riscv-config format.
        self.isa_spec = os.path.abspath(config['ispec']) if 'ispec' in config else ''
        # Path to the input platform yaml as per riscv-config format.
        self.platform_spec = os.path.abspath(config['pspec']) if 'ispec' in config else ''
        self.make = config['make'] if 'make' in config else 'make'
        return sclass

    def initialise(self, suite, work_dir, archtest_env):
        # Store the path to the suite.
        self.suite = suite
        # Store the path to the root level work directory.
        self.work_dir = work_dir
        # Store the path to the folder which contains the header files for the tests.
        self.archtest_env = archtest_env

    def build(self, isa_yaml, platform_yaml):
        # Extract the configuration of hart0 from isa yaml to figure out the configuration of the
        # hart being tested.
        ispec = utils.load_yaml(isa_yaml)['hart0']
        # Resolve xlen value from the isa yaml
        self.xlen = ('64' if 64 in ispec['supported_xlen'] else '32')
        # Store the ISA of the target.
        self.isa = ispec["ISA"]
        self.var_dict = {}
        # Extract all variables from the makefiles
        for fpath in self.makefiles:
            self.var_dict.update(getmakevars(fpath))
        # The path where the Makefile is created
        self.makefilepath = os.path.join(self.work_dir, "Makefile." + self.name[:-1])
        with open(self.makefilepath,"w") as fp:
            # The path to the target directory, i.e the directory where this python file is
            # present. This variable is written out to the makefile so that other variables can use
            # this value.
            fp.write("TARGET_DIR = "+self.pluginpath+"\n")
            # Write out all values except the COMPILE_TARGET and RUN_TARGET commands
            for entry in self.var_dict.keys():
                if not entry.endswith("_TARGET"):
                    fp.write(entry+" = "+self.var_dict[entry]+"\n")
                else:
                    self.var_dict[entry] = Template(self.var_dict[entry])


    def runTests(self, testList,cgf_file=None):
        # Initialise the Make Utility from riscof with the output path for the Makefile
        make = utils.makeUtil(makefilePath=self.makefilepath)
        # Modify the make command based on the input values in the config file.
        make.makeCommand = self.make + ' -j' + self.num_jobs
        # Iterate over all the entries in the test list
        for entry in testList:
            # Extract the entry from the testlist
            testentry = testList[entry]
            # Extract the path to the assembly test file from the test list entry
            test = testentry['test_path']
            # Extract the path to the work directory for the test.
            test_dir = testentry['work_dir']
            # Macros to be defined are added in the GCC command format
            # -D <macro_name>=<macro_value>
            # Change this if the toolchain uses a different format
            macros = ' -D' + " -D".join(testentry['macros'])
            # Variables accessible in the *_TARGET commands
            # Add more variables below if you wish to use these variables in the *_TARGET commands.
            substitute = {
                # The path to the target directory, i.e the directory where this python file is
                # present
                'target_dir': self.pluginpath,
                # Path to the test assembly file
                'asm': test,
                # Path to the work directory
                'work_dir': testentry['work_dir'],
                # Name of the Test. Can be used to name files in the work directory.
                'test_name': test.rsplit('/',1)[1][:-2],
                # The path to the env folder containing the header files for the suite. This path
                # should be passed as an include path in the compile commands.
                'include': self.archtest_env,
                # The isa string to be passed to the compiler. The format adheres to the march
                # argument of GCC
                'march': testentry['isa'].lower(),
                # The abi string to be passed to the compiler. The format adheres to the mabi
                # argument of GCC. To change how this string is derived, change function on line 21.
                'mabi': mabi(testentry['isa']),
                # The ISA string present in the input yaml. Can be used to set the ISA of the target
                'target_isa': self.isa,
                # Name of the generated binary file. Can be custom.
                'test_bin': 'ref.elf',
                # Name of the signature file. Note the name of the file should be in the same
                # particular format and inside the test work directory.
                'signature_file': os.path.join(test_dir, self.name[:-1] + ".signature"),
                # The string which specifies all the macros to be defined for the test. As computed
                # in line 108.
                'macros': macros
            }

            # Construct the command for the test and add a target in the makefile. The format of the
            # command is as follows:
            # cd <work_directory>;substitute(COMPILE_TARGET);substitute(RUN_TARGET);
            # The RUN_TARGET is optional and can be skipped if the same is not defined in the input
            # makefile
            execute = "@cd "+testentry['work_dir']+";"

            compile_cmd = self.var_dict['COMPILE_TARGET'].safe_substitute(substitute)
            execute+=compile_cmd+";"
            if 'RUN_TARGET' in self.var_dict:
                run_cmd = self.var_dict['RUN_TARGET'].safe_substitute(substitute)
                execute+=run_cmd+";"
            # Add target in the makefile for the test
            make.add_target(execute,)
        # Execute all targets.
        make.execute_all(self.work_dir)
