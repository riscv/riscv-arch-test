import os
import re
import shutil
import subprocess
import shlex
import logging
import random
import string
from string import Template
import distutils

import riscof.utils as utils
from riscof.pluginTemplate import pluginTemplate
import riscof.constants as constants
from riscv_isac.isac import isac

logger = logging.getLogger()

class sail_cSim(pluginTemplate):
    __model__ = "sail_c_simulator"
    __version__ = "0.5.0"

    docker_cmd = 'docker run -w /work -v{0}:/work -a stdout -a stderr --init {1} {2}'

    def __init__(self, *args, **kwargs):
        sclass = super().__init__(*args, **kwargs)

        config = kwargs.get('config')
        if config is None:
            logger.error("Config node for sail_cSim missing.")
            raise SystemExit
        self.num_jobs = str(config['jobs'] if 'jobs' in config else 1)
        self.docker = bool(config['docker']) if 'docker' in config else False
        self.docker_img = str(config['image']) if 'image' in config else 'riscv_compliance'
        self.pluginpath = os.path.abspath(config['pluginpath'])
        path = config['PATH'] if 'PATH' in config else ""


        self.sail_exe = { '32' : os.path.join(path,"riscv_sim_rv32d"),
                '64' : os.path.join(path,"riscv_sim_rv64d")}
        self.isa_spec = os.path.abspath(config['ispec']) if 'ispec' in config else ''
        self.platform_spec = os.path.abspath(config['pspec']) if 'ispec' in config else ''
        self.make = config['make'] if 'make' in config else 'make'
        logger.debug("SAIL CSim plugin initialised using the following configuration.")
        for entry in config:
            logger.debug(entry+' : '+config[entry])
        return sclass

    def initialise(self, suite, work_dir, archtest_env):
        self.suite = suite
        self.work_dir = work_dir
        self.objdump_cmd = 'riscv{1}-unknown-elf-objdump -D {0} > {2};'
        self.archtest_env = archtest_env
        compile_cmd = 'riscv{1}-unknown-elf-gcc -march={0} \
         -static -mcmodel=medany -fvisibility=hidden -nostdlib -nostartfiles'

        if not self.docker:
            compile_cmd += ' -T '+self.pluginpath+'/env/link.ld\
                -I '+self.pluginpath+'/env/\
                -I ' + archtest_env
        else:
            compile_cmd += ' -T /work/sail_work/env/link.ld\
                -I /work/sail_work/env/\
                -I /work/test/includes'
        self.compile_cmd = compile_cmd

    def build(self, isa_yaml, platform_yaml):
        ispec = utils.load_yaml(isa_yaml)['hart0']
        self.xlen = ('64' if 64 in ispec['supported_xlen'] else '32')
        self.isa = 'rv' + self.xlen
        if "64I" in ispec["ISA"]:
            self.compile_cmd = self.compile_cmd+' -mabi='+'lp64 '
        elif "32I" in ispec["ISA"]:
            self.compile_cmd = self.compile_cmd+' -mabi='+'ilp32 '
        elif "32E" in ispec["ISA"]:
            self.compile_cmd = self.compile_cmd+' -mabi='+'ilp32e '
        if "I" in ispec["ISA"]:
            self.isa += 'i'
        if "E" in ispec["ISA"]:
            self.isa += 'e'
        if "M" in ispec["ISA"]:
            self.isa += 'm'
        if "A" in ispec["ISA"]:
            self.isa += 'a'
        if "C" in ispec["ISA"]:
            self.isa += 'c'
        if "F" in ispec["ISA"]:
            self.isa += 'f'
        if "D" in ispec["ISA"]:
            self.isa += 'd'
        objdump = "riscv{0}-unknown-elf-objdump".format(self.xlen)
        if not self.docker:
            if shutil.which(objdump) is None:
                logger.error(objdump+": executable not found. Please check environment setup.")
                raise SystemExit
            compiler = "riscv{0}-unknown-elf-gcc".format(self.xlen)
            if shutil.which(compiler) is None:
                logger.error(compiler+": executable not found. Please check environment setup.")
                raise SystemExit
            if shutil.which(self.sail_exe[self.xlen]) is None:
                logger.error(self.sail_exe[self.xlen]+ ": executable not found. Please check environment setup.")
                raise SystemExit
            if shutil.which(self.make) is None:
                logger.error(self.make+": executable not found. Please check environment setup.")
                raise SystemExit
        else:
            os.mkdir(os.path.join(self.work_dir,"sail_work"))
            os.mkdir(os.path.join(self.work_dir,"test"))
            self.test_dir = os.path.join(self.work_dir,"test")
            distutils.dir_util.copy_tree(self.archtest_env,os.path.join(self.test_dir,"includes"))
            distutils.dir_util.copy_tree(
                    os.path.join(self.pluginpath,"env"),
                    os.path.join(self.work_dir,"sail_work/env"))

    def runTests(self, testList, cgf_file=None, header_file= None):
        if os.path.exists(self.work_dir+ "/Makefile." + self.name[:-1]):
            os.remove(self.work_dir+ "/Makefile." + self.name[:-1])
        make = utils.makeUtil(makefilePath=os.path.join(self.work_dir, "Makefile." + self.name[:-1]))
        make.makeCommand = self.make + ' -j' + self.num_jobs
        for file in testList:
            testentry = testList[file]
            test = testentry['test_path']
            test_dir = testentry['work_dir']
            test_name = test.rsplit('/',1)[1][:-2]

            elf = 'ref.elf'

            execute = "@cd "+testentry['work_dir']+";"

            cmd = self.compile_cmd.format(testentry['isa'].lower(), self.xlen) + ' ' + test + ' -o ' + elf
            compile_cmd = cmd + ' -D' + " -D".join(testentry['macros'])
            execute+=compile_cmd+";"

            execute += self.objdump_cmd.format(elf, self.xlen, 'ref.disass')
            sig_file = os.path.join(test_dir, self.name[:-1] + ".signature")

            execute += self.sail_exe[self.xlen] + '  -i -v --trace=step  --pmp-count=16 --pmp-grain=0  --test-signature={0} {1} > {2}.log 2>&1;'.format(sig_file, elf, test_name)

            cov_str = ' '
            for label in testentry['coverage_labels']:
                cov_str+=' -l '+label

            cgf_mac = ' '
            header_file_flag = ' '
            if header_file is not None:
                header_file_flag = f' -h {header_file} '
                cgf_mac += ' -cm common '
                for macro in testentry['mac']:
                    cgf_mac+=' -cm '+macro

            if cgf_file is not None:
                coverage_cmd = 'riscv_isac --verbose info coverage -d \
                        -t {0}.log --parser-name c_sail -o coverage.rpt  \
                        --sig-label begin_signature  end_signature \
                        --test-label rvtest_code_begin rvtest_code_end \
                        -e ref.elf -c {1} -x{2} {3} {4} {5};'.format(\
                        test_name, ' -c '.join(cgf_file), self.xlen, cov_str, header_file_flag, cgf_mac)
            else:
                coverage_cmd = ''


            execute+=coverage_cmd

            make.add_target(execute)
        make.execute_all(self.work_dir)
