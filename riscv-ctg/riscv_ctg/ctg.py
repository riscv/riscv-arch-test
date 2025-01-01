# See LICENSE.incore file for details

import copy
import os,re
import multiprocessing as mp

import time
import shutil
from riscv_ctg.log import logger
import riscv_ctg.utils as utils
import riscv_ctg.constants as const
from riscv_isac.cgf_normalize import expand_cgf
from riscv_ctg.generator import Generator
from riscv_ctg.cross_comb import cross
from riscv_ctg.csr_comb import GeneratorCSRComb
from math import *
from riscv_ctg.__init__ import __version__

def create_test(usage_str, node,label,base_isa,max_inst, op_template, randomize, out_dir, xlen, flen, inxFlag):
    iflen = 0
    if 'mnemonics' not in node and 'csr_comb' not in node:
        logger.warning("Neither mnemonics nor csr_comb node not found in covergroup: " + str(label))
        return
    if 'ignore' in node:
        logger.info("Ignoring :" + str(label))
        if node['ignore']:
            return

    if 'mnemonics' in node:
        # Function to encompass checks and test generation
        def gen_test(op_node, opcode):
            iflen = 0
            if xlen not in op_node['xlen']:
                logger.warning("Skipping {0} since its not supported in current XLEN:".format(opcode))
                return
            if 'flen' in op_node:
                if flen not in op_node['flen']:
                    logger.warning("Skipping {0} since its not supported in current FLEN({1}):".format(\
                            opcode, flen))
                    return
                iflen = min(op_node['flen'])
            fprefix = os.path.join(out_dir,str(label))
            logger.info('Generating Test for :' + str(label) +"-" + opcode)
            formattype  = op_node['formattype']
            gen = Generator(formattype,op_node,opcode,randomize,xlen,flen,iflen,base_isa,inxFlag)
            op_comb = gen.opcomb(node)
            val_comb = gen.valcomb(node)
            instr_dict = gen.correct_val(
                gen.valreg(
                    gen.testreg(
                        gen.swreg(
                            gen.gen_inst(op_comb, val_comb, node)))))
            logger.info("Writing tests for :"+str(label))
            my_dict = gen.reformat_instr(instr_dict)
            gen.write_test(fprefix,node,label,my_dict, op_node, usage_str, max_inst)

        # If base_op defined in covergroup, extract corresponding template
        # else go through the instructions defined in mnemonics label
        op_node = None
        if 'base_op' in node:
            # Extract pseudo and base instructions
            base_op = node['base_op']
            pseudop = list(node['mnemonics'].keys())[0]
            if base_op in op_template and pseudop in op_template:
                op_node = copy.deepcopy(op_template[base_op])
                pseudo_template = op_template[pseudop]

                # Ovewrite/add nodes from pseudoinstruction template in base instruction template
                for key, val in pseudo_template.items():
                    op_node[key] = val

                # Generate tests
                gen_test(op_node, pseudop)
        else:
            for opcode in node['mnemonics']:
                if opcode in op_template:
                    op_node = op_template[opcode]
                    # Generate tests
                    gen_test(op_node, opcode)
                else:
                    logger.warning(str(opcode) + " not found in template file. Skipping")
                    return

        if 'cross_comb' in node:
            fprefix = os.path.join(out_dir,str(label))
            cross_obj = cross(base_isa, xlen, randomize, label)
            cross_instr_dict = cross_obj.cross_comb(node)
            logger.info('Writing cross-comb test')
            cross_obj.write_test(fprefix, node, usage_str, label, cross_instr_dict)

        if op_node is None:
            # Return if there is no corresponding template
            logger.warning("Skipping :" + str(opcode))
            return

    if 'csr_comb' in node:
        fprefix = os.path.join(out_dir,str(label))
        csr_comb_gen = GeneratorCSRComb(base_isa, xlen, randomize)
        csr_comb_instr_dict = csr_comb_gen.csr_comb(node)
        logger.info('Writing tests for csr_comb')
        csr_comb_gen.write_test(fprefix, node, usage_str, label, csr_comb_instr_dict)

def ctg(verbose, out, random ,xlen_arg,flen_arg, cgf_file,num_procs,base_isa, max_inst,inxFlag,filter):
    logger.level(verbose)
    logger.info('****** RISC-V Compliance Test Generator {0} *******'.format(__version__ ))
    logger.info('Copyright (c) 2020, InCore Semiconductors Pvt. Ltd.')
    logger.info('All Rights Reserved.')
    logger.info("Copying env folder to Output directory.")
    current_dir = os.path.dirname(os.path.abspath(__file__))
    env_dir = os.path.join(current_dir, "../../riscv-test-suite/env")
    if not os.path.exists(env_dir):
        shutil.copytree(const.env,env_dir)
    xlen = int(xlen_arg)
    flen = int(flen_arg)
    out_dir = out
    randomize = random
    mytime = time.asctime(time.gmtime(time.time()) ) + ' GMT'
    cgf_argument = ''
    for cf in cgf_file:
        cgf_argument += '//                  --cgf {} \\\n'.format(cf)
    randomize_argument = ''
    if random is True:
        randomize_argument = ' \\\n//                  --randomize'
    usage_str = const.usage.safe_substitute(base_isa=base_isa, \
            cgf=cgf_argument, version = __version__, time=mytime, \
            randomize=randomize_argument,xlen=str(xlen_arg))
    # ---------------------------------
    # IITM Changes
    # This <inxFlag> is introduced to handle the template conflict over float instructions
    # ---------------------------------
    if inxFlag:
        const.template_files.remove([fd for fd in const.template_files if "fd.yaml" in fd][0])
    else:
        const.template_files.remove([fd for fd in const.template_files if "inx.yaml" in fd][0])
    op_template = utils.load_yaml(const.template_files)
    cgf = expand_cgf(cgf_file,xlen,flen)
    pool = mp.Pool(num_procs)

    args_list = []
    for label,node in cgf.items():
        if filter is not None and re.search(filter, label) is None:
            continue
        args_list.append((usage_str, node,label,base_isa,max_inst, op_template,
        randomize, out_dir, xlen, flen, inxFlag))
    results = pool.starmap(create_test, args_list)
    pool.close()
