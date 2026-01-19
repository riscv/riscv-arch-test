# See LICENSE.incore for details
import random
from collections import defaultdict
from constraint import *
import re
from riscv_ctg.constants import *
from riscv_ctg.log import logger
from riscv_ctg.helpers import *
from riscv_isac.InstructionObject import instructionObject
import time
from math import *
import struct
import sys
import itertools
import re

# F
one_operand_finstructions = ["fsqrt.s","fmv.x.w","fcvt.wu.s","fcvt.w.s","fclass.s","fcvt.l.s","fcvt.lu.s","fcvt.s.l","fcvt.s.lu"]
two_operand_finstructions = ["fadd.s","fsub.s","fmul.s","fdiv.s","fmax.s","fmin.s","feq.s","flt.s","fle.s","fsgnj.s","fsgnjn.s","fsgnjx.s"]
three_operand_finstructions = ["fmadd.s","fmsub.s","fnmadd.s","fnmsub.s"]
# Zfa/F:
one_operand_finstructions += ["fround.s", "froundnx.s", "fcvtmod.w.d","fmvh.x.d"]
two_operand_finstructions += ["fmaxm.s", "fminm.s", "fmvp.d.x", "fleq.s", "fltq.s"]

# D
one_operand_dinstructions = ["fsqrt.d","fclass.d","fcvt.w.d","fcvt.wu.d","fcvt.d.w","fcvt.d.wu","fcvt.d.s","fcvt.s.d"]
two_operand_dinstructions = ["fadd.d","fsub.d","fmul.d","fdiv.d","fmax.d","fmin.d","feq.d","flt.d","fle.d","fsgnj.d","fsgnjn.d","fsgnjx.d"]
three_operand_dinstructions = ["fmadd.d","fmsub.d","fnmadd.d","fnmsub.d"]

# H
one_operand_hinstructions = ["fsqrt.h","fclass.h","fcvt.w.h","fcvt.wu.h","fcvt.h.w","fcvt.h.wu","fcvt.h.l","fcvt.h.lu","fcvt.l.h","fcvt.d.h","fcvt.h.d","fcvt.s.h","fcvt.s.h"]
two_operand_hinstructions = ["fadd.h","fsub.h","fmul.h","fdiv.h","fmax.h","fmin.h","feq.h","flt.h","fle.h","fsgnj.h","fsgnjn.h","fsgnjx.h"]
three_operand_hinstructions = ["fmadd.h","fmsub.h","fnmadd.h","fnmsub.h"]

# Zfa/D:
one_operand_dinstructions += ["fround.d", "froundnx.d"]
two_operand_dinstructions += ["fmaxm.d", "fminm.d", "fleq.d", "fltq.d"]


def is_fp_instruction(insn):
    '''
    Takes an instruction string (e.g. 'fadd.s') and returns True if it is a FP instruction.
    The function is compatible with all existing and future RISC-V ISA extensions.

    :param insn: String representing an instruction (e.g. 'fadd.s', 'lw')
    '''
    return type(insn) == str and insn.lower()[0] == 'f'


from riscv_ctg.dsp_function import *

twos_xlen = lambda x: twos(x,xlen)

def toint(x: str):
    if '0x' in x:
        return int(x,16)
    else:
        return int(x)

def get_rm(opcode):
    insns = ['fsgnj','fle','flt','feq','fclass','fmv','flw','fsw','fld','fsd','fmin','fmax',
             'fcvt.d.s', 'fcvt.d.w','fcvt.d.wu']
    insns += ['fminm', 'fmaxm']
    if any([x in opcode for x in insns]):
        return []
    else:
        return ['rm_val']

OPS = {
    'rformat': ['rs1', 'rs2', 'rd'],
    'r4format': ['rs1', 'rs2', 'rs3', 'rd'],
    'iformat': ['rs1', 'rd'],
    'sformat': ['rs1', 'rs2'],
    'bsformat': ['rs1', 'rs2', 'rd'],
    'bformat': ['rs1', 'rs2'],
    'uformat': ['rd'],
    'jformat': ['rd'],
    'crformat': ['rs1', 'rs2'],
    'cmvformat': ['rd', 'rs2'],
    'ciformat': ['rd'],
    'cssformat': ['rs2'],
    'ciwformat': ['rd'],
    'clformat': ['rs1', 'rd'],
    'csformat': ['rs1', 'rs2'],
    'caformat': ['rs1', 'rs2'],
    'cuformat': ['rs1'],
    'cbformat': ['rs1'],
    'clbformat': ['rs1','rd'],
    'clhformat': ['rs1','rd'],
    'csbformat': ['rs1','rs2'],
    'cshformat': ['rs1','rs2'],
    'cjformat': [],
    'ckformat': ['rs1'],
    'kformat': ['rs1','rd'],
    'ckformat': ['rs1'],
    # 'frformat': ['rs1', 'rs2', 'rd'],
    'fsrformat': ['rs1', 'rd'],
    # 'fr4format': ['rs1', 'rs2', 'rs3', 'rd'],
    'pbrrformat': ['rs1', 'rs2', 'rd'],
    'phrrformat': ['rs1', 'rs2', 'rd'],
    'pbrformat': ['rs1', 'rd'],
    'phrformat': ['rs1', 'rd'],
    'pbriformat': ['rs1', 'rd'],
    'phriformat': ['rs1', 'rd'],
    'psbrrformat': ['rs1', 'rs2', 'rd'],
    'pshrrformat': ['rs1', 'rs2', 'rd'],
    'pwrrformat': ['rs1', 'rs2', 'rd'],
    'pwriformat': ['rs1', 'rd'],
    'pwrformat': ['rs1', 'rd'],
    'pswrrformat': ['rs1', 'rs2', 'rd'],
    'pwhrrformat': ['rs1', 'rs2', 'rd'],
    'pphrrformat': ['rs1', 'rs2', 'rd'],
    'ppbrrformat': ['rs1', 'rs2', 'rd'],
    'prrformat': ['rs1', 'rs2', 'rd'],
    'prrrformat': ['rs1', 'rs2', 'rs3', 'rd'],
    'dcasrformat': ['rs1', 'rs2', 'rd']
}
''' Dictionary mapping instruction formats to operands used by those formats '''

VALS = {
    'rformat': "['rs1_val', 'rs2_val'] + ((get_rm(opcode)+['fcsr']) if is_fext else []) + \
        ([] if not is_nan_box else ['rs{0}_nan_prefix'.format(x) for x in range(1,3)]) + \
        (['rs{0}_sgn_prefix'.format(x) for x in range(1,3)] if is_sgn_extd else [])",
    'r4format': "['rs1_val', 'rs2_val', 'rs3_val'] + (['rm_val','fcsr'] if is_fext else []) + \
        ([] if not is_nan_box else ['rs{0}_nan_prefix'.format(x) for x in range(1,4)]) + \
        (['rs{0}_sgn_prefix'.format(x) for x in range(1,4)] if is_sgn_extd else [])",
    'iformat': "['rs1_val', 'imm_val'] + ([] if not is_fext else ['fcsr'])",
    'sformat': "['rs1_val', 'rs2_val', 'imm_val'] + ([] if not is_fext else ['fcsr'])",
    'bsformat': "['rs1_val', 'rs2_val', 'imm_val']",
    'bformat': "['rs1_val', 'rs2_val', 'imm_val']",
    'uformat': "['imm_val']",
    'jformat': "['imm_val']",
    'crformat': "['rs1_val', 'rs2_val']",
    'cmvformat': "['rs2_val']",
    'ciformat': "['rs1_val', 'imm_val']",
    'cssformat': "['rs2_val', 'imm_val']",
    'ciwformat': "['imm_val']",
    'clformat': "['rs1_val', 'imm_val', 'fcsr']",
    'cuformat': "['rs1_val']",
    'clbformat': "['rs1_val','imm_val']",
    'clhformat': "['rs1_val','imm_val']",
    'csbformat': "['rs1_val','rs2_val','imm_val']",
    'cshformat': "['rs1_val','rs2_val','imm_val']",
    'csformat': "['rs1_val', 'rs2_val', 'imm_val']",
    'caformat': "['rs1_val', 'rs2_val']",
    'cbformat': "['rs1_val', 'imm_val']",
    'cjformat': "['imm_val']",
    'ckformat': "['rs1_val']",
    'kformat': "['rs1_val']",
    'ckformat': "['rs1_val']",
    # 'frformat': "['rs1_val', 'rs2_val', 'rm_val', 'fcsr']",
    'fsrformat': "['rs1_val','fcsr'] + get_rm(opcode) + \
        ([] if not is_nan_box else ['rs1_nan_prefix']) + \
        (['rs1_sgn_prefix'] if is_sgn_extd else [])",
    # 'fr4format': "['rs1_val', 'rs2_val', 'rs3_val', 'rm_val', 'fcsr']",
    'pbrrformat': 'simd_val_vars("rs1", xlen, 8) + simd_val_vars("rs2", xlen, 8)',
    'phrrformat': 'simd_val_vars("rs1", xlen, 16) + simd_val_vars("rs2", xlen, 16)',
    'pbrformat': 'simd_val_vars("rs1", xlen, 8)',
    'phrformat': 'simd_val_vars("rs1", xlen, 16)',
    'pbriformat': 'simd_val_vars("rs1", xlen, 8) + ["imm_val"]',
    'phriformat': 'simd_val_vars("rs1", xlen, 16) + ["imm_val"]',
    'psbrrformat': 'simd_val_vars("rs1", xlen, 8) + ["rs2_val"]',
    'pshrrformat': 'simd_val_vars("rs1", xlen, 16) + ["rs2_val"]',
    'pwrrformat': 'simd_val_vars("rs1", xlen, 32) + simd_val_vars("rs2", xlen, 32)',
    'pwriformat': 'simd_val_vars("rs1", xlen, 32) + ["imm_val"]',
    'pwrformat': 'simd_val_vars("rs1", xlen, 32)',
    'pswrrformat': 'simd_val_vars("rs1", xlen, 32) + ["rs2_val"]',
    'pwhrrformat': 'simd_val_vars("rs1", xlen, 32) + simd_val_vars("rs2", xlen, 16)',
    'pphrrformat': '["rs1_val"] + simd_val_vars("rs2", xlen, 16)',
    'ppbrrformat': '["rs1_val"] + simd_val_vars("rs2", xlen, 8)',
    'prrformat': '["rs1_val", "rs2_val"]',
    'prrrformat': "['rs1_val', 'rs2_val' , 'rs3_val']",
    'dcasrformat': '["rs1_val", "rs2_val"]'
}
''' Dictionary mapping instruction formats to operand value variables used by those formats '''




def isInt(s):
    '''
    Utility function to check if the variable is an int type. Returns False if
    not.
    '''
    try:
        int(s)
        return True
    except ValueError:
        return False

def get_default_registers(ops, datasets):
    problem = Problem()
    not_x0 = lambda x: x not in ['x0']

    for op in ops:
        dataset = datasets[op]
        # problem.addVariable(op,list(random.sample(dataset, len(dataset))))
        problem.addVariable(op,dataset)
        problem.addConstraint(not_x0,tuple([op]))
    if len(ops) > 1:
        cond = " and ".join(["!=".join(x) for x in itertools.combinations(ops,2) if x[0]!=x[1]])
    else:
        cond = 'True'
    def unique_constraint(*args):
        for var,val in zip(ops,args):
            locals()[var] = val
        return eval(cond)
    problem.addConstraint(unique_constraint,tuple(ops))
    solution = None
    count = 0
    while solution is None and count < 5:
        solution = problem.getSolution()
        count += 1
    if count == 5:
        return []
    else:
        return solution

class Generator():
    '''
    A generator class to generate RISC-V assembly tests for a given instruction
    format, opcode and a set of coverpoints.

    :param fmt: the RISC-V instruction format type to be used for the test generation.
    :param opnode: dictionary node from the attributes YAML that is to be used in the test generation.
    :param opcode: name of the instruction opcode.
    :param randomization: a boolean variable indicating if the random constraint solvers must be employed.
    :param xl: an integer indicating the XLEN value to be used.
    :param base_isa_str: The base isa to be used for the tests. One of [rv32e,rv32i,rv64i]

    :type fmt: str
    :type opnode: dict
    :type opcode: str
    :type randomization: bool
    :type xl: int
    :type base_isa_str: str
    '''
    def __init__(self,fmt,opnode,opcode,randomization, xl, fl, ifl ,base_isa_str,inxFlag):
        '''
        This is a Constructor function which initializes various class variables
        depending on the arguments.

        The function also creates a dictionary of datasets for each operand. The
        dictionary basically indicates what registers from the register file are to be used
        when generating solutions for coverpoints. The datasets are limited to
        to reduce the time taken by solvers to arrive at a solution.

        A similar dictionary is created for the values to be used by the operand
        registers.

        '''
        global xlen
        global flen
        global iflen
        global base_isa
        xlen = xl
        flen = fl
        iflen = ifl
        base_isa = base_isa_str


        is_nan_box = False
        is_fext = any(['F' in x or 'D' in x or 'Zfh' in x or 'Zfinx' in x  or 'Zcf' in x or 'Zcd' in x or 'Zhinx' in x or 'Zdinx' in x for x in opnode['isa']])
        is_sgn_extd = True if (inxFlag and iflen <xlen) else False

        if is_fext:
            if fl>ifl:
                is_int_src = any([opcode.endswith(x) for x in ['.x','.w','.l','.wu','.lu']])
                is_nan_box = not is_int_src and is_sgn_extd

        self.xlen = xl
        self.flen = fl
        self.iflen = ifl
        self.base_isa = base_isa_str
        self.fmt = fmt
        self.opcode = opcode
        self.op_vars = OPS[fmt]
        self.val_vars = eval(VALS[fmt])
        self.is_fext = is_fext
        self.is_nan_box = is_nan_box
        self.inxFlag = inxFlag
        self.is_sgn_extd = is_sgn_extd

        if opcode in ['sw', 'sh', 'sb', 'lw', 'lhu', 'lh', 'lb', 'lbu', 'ld', 'lwu', 'sd',"jal","beq","bge","bgeu","blt","bltu","bne","jalr","c.jalr","c.jr","flw","fsw","fld","fsd","flh","fsh","c.lbu","c.lhu","c.lh","c.sb","c.sh","c.flw","c.fld","c.flwsp","c.fswsp","c.fldsp","c.fsdsp"]:
            self.val_vars = self.val_vars + ['ea_align']
        self.template = opnode['template']
        self.opnode = opnode
        # self.stride = opnode['stride']
        if 'operation' in opnode:
            self.operation = opnode['operation']
        else:
            self.operation = None
        datasets = {}
        i=10
        for entry in self.op_vars:
            key = entry+"_op_data"
            if key in opnode:
                datasets[entry] = eval(opnode[key])
            else:
                datasets[entry] = ['x'+str(i)]
                i+=1
        for entry in self.val_vars:
            key = entry+"_data"
            if key in opnode:
                datasets[entry] = eval(opnode[key])
            else:
                logger.warning("{0} not defined for {1}. Defaulting to [0].".format(key,self.opcode))
                datasets[entry] = [0]

        self.datasets = datasets
        self.random=randomization
        self.default_regs = get_default_registers(self.op_vars, self.datasets)

    def opcomb(self, cgf):
        '''
        This function finds the solutions for the various operand combinations
        defined by the coverpoints in the CGF under the "op_comb" node of the
        covergroup.

        Depending on the registers chosen in the datasets, a contraint is created
        to ensure that all those registers occur atleast once in the respective
        operand/destination location in the instruction. These contraints are
        then supplied to the solver for solutions
        
        If randomization is enabled we use the ``MinConflictsSolver`` solver to
        find solutions.

        If harcoded registers are given in the cgf file, then for the conditions other
        than the first one, there will be No Solution. To solve that problem, some code
        is written which will find the required register in the condition and generate the
        solution normally.
        
        :param cgf: a covergroup in cgf format containing the set of coverpoints to be satisfied.

        :type cgf: dict

        :return: a dictionary of solutions for the various operand combinations specified in the CGF file.
        '''
        logger.debug(self.opcode + ' : Generating OpComb')
        solutions = []
        op_conds = {}
        opcomb_value = cgf.get("op_comb")
        op_comb = OrderedSet(opcomb_value or [])
        for op in self.op_vars:
            op_conds[op] = OrderedSet(cgf.get(op, []))
        individual = False
        nodiff = False
        construct_constraint = lambda val: (lambda x: bool(x in val))
        while any([len(op_conds[x])!=0 for x in op_conds]+[len(op_comb)!=0]):
            cond_str = ''
            cond_vars = []
            solver = MinConflictsSolver() if self.random else None
            problem = Problem(solver)

            done = False
            for var in self.op_vars:
                problem.addVariable(var, list(self.datasets[var]))
                if op_conds[var] and not(individual and done):
                    cond_vars.append(var)
                    problem.addConstraint(construct_constraint(op_conds[var]),tuple([var]))
                    done = True
            if op_comb:
                cond = op_comb.pop()
                cond_str += cond+", "
                def comb_constraint(*args):
                    for var,val in zip(self.op_vars,args):
                        locals()[var] = val
                    return eval(cond)
                problem.addConstraint(comb_constraint,tuple(self.op_vars))
            elif not nodiff:
                problem.addConstraint(AllDifferentConstraint())
            count = 0
            solution = problem.getSolution()
            while solution is None and count < 5:
                if opcomb_value:
                    for i in opcomb_value:
                        opcomb_match = re.search(r'x\d{1,2}', i)
                        if opcomb_match is not None:
                            pattern = r'(?:rs1|rs2|rd) == "(x\d+)"'
                            matches = re.findall(pattern, cond)
                            if not matches or any(int(match[1:]) > 31 for match in matches):
                                result = None
                            else:
                                result = matches
                                for match in result:
                                    op_conds['rs1'].add(match)
                                    op_conds['rs2'].add(match)
                                    op_conds['rd'].add(match)
                                op_comb.add(cond)
                                break
                solution = problem.getSolution()
                count = count + 1

            if solution is None:
                if individual:
                    if nodiff:
                        logger.warn(self.opcode + " : Cannot find solution for Op combination")
                        break
                    else:
                        nodiff = True
                else:
                    individual = True
                continue
            op_tuple = []
            for key in self.op_vars:
                op_tuple.append(solution[key])
                op_conds[key].discard(solution[key])

            def eval_func(cond):
                for var,val in zip(self.op_vars,op_tuple):
                    locals()[var] = val
                return eval(cond)
            sat_set = OrderedSet(filter(eval_func,op_comb))
            cond_str += ", ".join([var+"=="+solution[var] for var in cond_vars]+list(sat_set))
            op_tuple.append(cond_str)
            problem.reset()
            solutions.append( tuple(op_tuple) )

        return solutions

    def valcomb(self, cgf):
        '''
        This function finds the solutions for the various value combinations
        defined by the coverpoints in the CGF under the "val_comb" node of the
        covergroup.

        The constraints here are quite simply taken as `eval` strings from the CGF val_comb
        nodes itself.

        If randomization is enabled we use the ``MinConflictsSolver`` solver to
        find solutions.

        :param cgf: a covergroup in cgf format containing the set of coverpoints to be satisfied.

        :type cgf: dict

        :return: a dictionary of solutions for the various value combinations specified in the CGF file.
        '''
        logger.debug(self.opcode + ' : Generating ValComb')
        if 'val_comb' not in cgf:
            return []
        val_comb = []

        conds = list(cgf['val_comb'].keys())
        inds = OrderedSet(range(len(conds)))
        merge = True
        if 'fcvt' in self.opcode or 'fmv' in self.opcode:
            if self.opcode.split(".")[-1] in ['x','w','wu','l','lu']:
                merge = "fmv.x.w" in self.opcode
        while inds:
            req_val_comb = conds[inds.pop()]
            if("#nosat" in req_val_comb):
                d={}
                soln = []
                req_val_comb_minus_comm = req_val_comb.split("#")[0]
                x = req_val_comb_minus_comm.split(" and ")

                if self.is_fext:
	                # fs + fe + fm -> Combiner Script
                    try:
                        d = merge_fields_f(self.val_vars,req_val_comb,self.flen,self.iflen,merge,self.inxFlag)
                    except ExtractException as e:
                        logger.warning("Valcomb skip: "+str(e))
                        continue
                else:
                    for i in self.val_vars:
                        for j in x:
                            if i in j:
                                if(d.get(i,"None") == "None"):
                                    d[i] = j.split("==")[1]
                                else:
                                    logger.error("Invalid Coverpoint: More than one value of "+ i +" found!")
                                    sys.exit(1)
                if(OrderedSet(d.keys()) != OrderedSet(self.val_vars)):
                    logger.warning(
                        "Valcomb skip: Cannot bypass SAT Solver for partially defined coverpoints!"\
                                + str(req_val_comb))
                    continue
                for y in self.val_vars:
                    soln.append(d[y])

                soln.append(req_val_comb_minus_comm)
                val_tuple = soln
            else:
                if self.random:
                    problem = Problem(MinConflictsSolver())
                else:
                    problem = Problem()

                for var in self.val_vars:
                    dataset = self.datasets[var]
                    if var not in req_val_comb:
                        dataset = dataset[:1]
                    problem.addVariable(var, dataset)

                def condition(*argv):
                    for var,val in zip(self.val_vars,argv):
                        locals()[var]=val
                    return eval(req_val_comb)

                problem.addConstraint(condition,tuple(self.val_vars))
                # if boundconstraint:
                #     problem.addConstraint(boundconstraint,tuple(['rs1_val', 'imm_val']))
                solution = problem.getSolution()
                count = 0
                while (solution is None and count < 5):
                    solution = problem.getSolution()
                    count+=1
                if solution is None:
                    logger.warn(self.opcode + " : Cannot find solution for Val condition "+str(req_val_comb))
                    continue
                val_tuple = []
                for i,key in enumerate(self.val_vars):
                    val_tuple.append(solution[key])

                def eval_func(cond):
                    for var,val in zip(self.val_vars,val_tuple):
                        locals()[var] = val
                    return eval(cond)
                sat_set=OrderedSet(filter(lambda x: eval_func(conds[x]),inds))
                inds = inds - sat_set
                val_tuple.append(req_val_comb+', '+', '.join([conds[i] for i in sat_set]))
                problem.reset()
            val_comb.append( tuple(val_tuple) )
        return val_comb

    def __jfmt_instr__(self,op=None,val=None):
        cond_str = ''
        if op:
            cond_str += op[-1]+', '
        if val:
            cond_str += val[-1]
        instr = {'inst':self.opcode,'index':'0', 'comment':cond_str}
        labelize = lambda x: (str((-x)%2**21),'1b') if x < 0 else (str((x%2**21)),'3f')
        if op:
            for var,reg in zip(self.op_vars,op):
                instr[var] = str(reg)
        else:
            for i,var in enumerate(self.op_vars):
                if self.opcode[0] == 'f' and 'fence' not in self.opcode:
                    if self.opnode[var+'_op_data'][2] == 'f':
                        instr[var] = 'f'+str(i+10)
                    else:
                        instr[var] = 'x'+str(i+10)
                else:
                    instr[var] = 'x'+str(i+10)
        if val:
            for i,var in enumerate(self.val_vars):
                if var == "imm_val":
                    instr[var],instr['label'] = labelize(val[i])
                else:
                    instr[var] = str(val[i])
        else:
            for var in self.val_vars:
                if var == "imm_val":
                    instr[var],instr['label'] = '0', '3f'
                else:
                    instr[var] = '0'
        return instr

    def __bfmt_instr__(self,op=None,val=None):
        cond_str = ''
        if op:
            cond_str += op[-1]+', '
        if val:
            cond_str += val[-1]
        instr = {'inst':self.opcode,'index':'0', 'comment':cond_str}


        labelize = lambda x: (str((-x)%2048),'1b') if x < 0 else (str((x%2048)),'3f')

        if op:
            for var,reg in zip(self.op_vars,op):
                instr[var] = str(reg)
        else:
            for i,var in enumerate(self.op_vars):
                instr[var] = 'x'+str(i+10)
        if val:
            for i,var in enumerate(self.val_vars):
                if var == "imm_val":
                    instr[var],instr['label'] = labelize(val[i])
                else:
                    instr[var] = str(val[i])
        else:
            for var in self.val_vars:
                if var == "imm_val":
                    instr[var],instr['label'] = '0', '3f'
                else:
                    instr[var] = '0'
        return instr

    def __cb_instr__(self,op=None,val=None):
        cond_str = ''
        if op:
            cond_str += op[-1]+', '
        if val:
            cond_str += val[-1]
        instr = {'inst':self.opcode,'index':'0', 'comment':cond_str}


        labelize = lambda x: (str((-x)%257),'1b') if x < 0 else (str((x%257)),'3f')

        if op:
            for var,reg in zip(self.op_vars,op):
                instr[var] = str(reg)
        else:
            for i,var in enumerate(self.op_vars):
                instr[var] = 'x'+str(i+10)
        if val:
            for i,var in enumerate(self.val_vars):
                if var == "imm_val":
                    instr[var],instr['label'] = labelize(val[i])
                else:
                    instr[var] = str(val[i])
        else:
            for var in self.val_vars:
                if var == "imm_val":
                    instr[var],instr['label'] = '0', '3f'
                else:
                    instr[var] = '0'
        return instr

    def __cj_instr__(self,op=None,val=None):
        cond_str = ''
        if op:
            cond_str += op[-1]+', '
        if val:
            cond_str += val[-1]
        instr = {'inst':self.opcode,'index':'0', 'comment':cond_str}


        labelize = lambda x: (str((-x)%2048),'1b') if x < 0 else (str((x%2048)),'3f')

        if op:
            for var,reg in zip(self.op_vars,op):
                instr[var] = str(reg)
        else:
            for i,var in enumerate(self.op_vars):
                instr[var] = 'x'+str(i+10)
        if val:
            for i,var in enumerate(self.val_vars):
                if var == "imm_val":
                    instr[var],instr['label'] = labelize(val[i])
                else:
                    instr[var] = str(val[i])
        else:
            for var in self.val_vars:
                if var == "imm_val":
                    instr[var],instr['label'] = '0', '3f'
                else:
                    instr[var] = '0'
        instr['rs2'] = 'x1'
        return instr

    def __clui_instr__(self,op=None,val=None):
        cond_str = ''
        if op:
            cond_str += op[-1]+', '
        if val:
            cond_str += val[-1]
        instr = {'inst':self.opcode,'index':'0', 'comment':cond_str}

        if op:
            for var,reg in zip(self.op_vars,op):
                instr[var] = str(reg)
        else:
            for i,var in enumerate(self.op_vars):
                instr[var] = 'x'+str(i+10)
        if val:
            for i,var in enumerate(self.val_vars):
                if var == "imm_val":
                    instr[var] = str(val[i]) if val[i] < 32 else str(val[i]+1048512)
                else:
                    instr[var] = str(val[i])
        else:
            for var in self.val_vars:
                if var == "imm_val":
                    instr[var] = '16'
                else:
                    instr[var] = '0'
        return instr

    def __cmemsp_instr__(self, op=None, val=None):
        cond_str = ''
        if op:
            cond_str += op[-1]+', '
        if val:
            cond_str += val[-1]
        instr = {'inst':self.opcode,'index':'0', 'comment':cond_str}
        if op:
            for var,reg in zip(self.op_vars,op):
                instr[var] = str(reg)
        else:
            for i,var in enumerate(self.op_vars):
                instr[var] = 'x'+str(i+10)
        if val:
            for i,var in enumerate(self.val_vars):
                instr[var] = str(val[i])
        else:
            for var in self.val_vars:
                instr[var] = str(self.datasets[var][0])
        instr['rs1'] = 'x2'
        return instr

    def __instr__(self, op=None, val=None):
        cond_str = ''
        if op:
            cond_str += op[-1]+', '
        if val:
            cond_str += val[-1]
        instr = {'inst':self.opcode,'index':'0', 'comment':cond_str}
        if op:
            for var,reg in zip(self.op_vars,op):
                instr[var] = str(reg)
        else:
            for i,var in enumerate(self.op_vars):
                instr[var]=self.default_regs[var]
        if val:
            for i,var in enumerate(self.val_vars):
                instr[var] = str(val[i])
        else:
            for var in self.val_vars:
                instr[var] = str(self.datasets[var][0])
        return instr

    def __fext_instr__(self,op=None,val=None):
        rm_dict = {
                0: 'rne',
                1: 'rtz',
                2: 'rdn',
                3: 'rup',
                4: 'rmm',
                7: 'dyn'}
        cond_str = ''
        if op:
            cond_str += op[-1]+','
        if val:
            cond_str += val[-1]
        instr = {'inst':self.opcode,'comment':cond_str,'index':'0'}
        if op:
            for var,reg in zip(self.op_vars,op):
                instr[var] = str(reg)
        else:
            for i,var in enumerate(self.op_vars):
                instr[var]=self.default_regs[var]
        if val:
            for i,var in enumerate(self.val_vars):
                if var == 'rm_val':
                    instr[var] = str(rm_dict[val[i]])
                else:
                    instr[var] = str(val[i])
        else:
            for var in self.val_vars:
                if var == 'rm_val':
                    instr[var] = 'dyn'
                else:
                    instr[var] = str(self.datasets[var][0])
        return instr

    def gen_inst(self,op_comb, val_comb, cgf):
        '''
        This function combines the op_comb and val_comb solution dictionaries
        to create a complete set of arguments of the instruction.

        Depending on the instruction opcode other subfunctions are called to
        create the final merged dictionary of op_comb and val_comb.

        Note however, that using the integer register x0 as either source or
        destination does not contribute to the coverage. Hence the respective
        val_combs are repeated again with non-x0 registers.

        :param op_comb: list containing the operand combination solutions
        :param val_comb: list containing the value combination solutions
        :param cgf: a covergroup in cgf format containing the set of coverpoints to be satisfied.

        :type cgf: dict
        :type op_comb: list
        :type val_comb: list

        :return: list of dictionaries containing the various values necessary for the macro.
        '''
        instr_dict = []
        cont = []
        if len(op_comb) < len(val_comb):
            op_comb = list(op_comb) + [[]] * (len(val_comb) - len(op_comb))
        elif len(val_comb) < len(op_comb):
            val_comb = list(val_comb) + [[self.datasets[var][0] for var in self.val_vars] + [""]] * (len(op_comb) - len(val_comb))

        x = dict([(y,x) for x,y in enumerate(self.val_vars)])

        ind_dict = {}
        for ind,var in enumerate(self.op_vars):
            if var+"_val" in x:
                ind_dict[ind] = x[var+"_val"]

        for op,val_soln in zip(op_comb,val_comb):
            val = [x for x in val_soln]
            if any([x=='x0' for x in op]) or not (len(op) == len(OrderedSet(op))):
                cont.append(val_soln)
                op_inds = list(ind_dict.keys())
                for i,x in enumerate(op_inds):
                    if op[x] == 'x0':
                        val[ind_dict[x]] = 0
                    for y in op_inds[i:]:
                        if op[y] == op[x]:
                            val[ind_dict[y]] = val[ind_dict[x]]
            if self.is_fext and  self.opcode in ['c.flwsp','c.fswsp','c.fldsp','c.fsdsp']:
                if any([x == 'x2' for x in op]):
                    cont.append(val)
                instr_dict.append(self.__cmemsp_instr__(op,val))
            elif self.is_fext:
                instr_dict.append(self.__fext_instr__(op,val))
            elif self.opcode == 'c.lui':
                instr_dict.append(self.__clui_instr__(op,val))
            elif self.opcode in ['c.beqz', 'c.bnez']:
                instr_dict.append(self.__cb_instr__(op,val))
            elif self.opcode in ['c.lwsp', 'c.swsp', 'c.ldsp', 'c.sdsp','c.flwsp','c.fswsp','c.fldsp','c.fsdsp']:
                if any([x == 'x2' for x in op]):
                    cont.append(val)
                instr_dict.append(self.__cmemsp_instr__(op,val))
            elif self.fmt == 'bformat' or self.opcode in ['c.j']:
                instr_dict.append(self.__bfmt_instr__(op,val))
            elif self.opcode in ['c.jal', 'c.jalr']:
                instr_dict.append(self.__cj_instr__(op,val))
            elif self.fmt == 'jformat' or self.fmt == 'cjformat':
                instr_dict.append(self.__jfmt_instr__(op,val))
            else:
                instr_dict.append(self.__instr__(op,val))
        op = None
        for val in cont:
            if self.is_fext:
                instr_dict.append(self.__fext_instr__(op,val))
            elif self.opcode == 'c.lui':
                instr_dict.append(self.__clui_instr__(op,val))
            elif self.opcode in ['c.beqz', 'c.bnez','c.lbu','c.lhu','c.lh','c.sb','c.sh']:
                instr_dict.append(self.__cb_instr__(op,val))
            elif self.opcode in ['c.lwsp', 'c.swsp', 'c.ldsp', 'c.sdsp','c.fsdsp','c.fswsp']:
                instr_dict.append(self.__cmemsp_instr__(op,val))
            elif self.fmt == 'bformat' or self.opcode in ['c.j']:
                instr_dict.append(self.__bfmt_instr__(op,val))
            elif self.opcode in ['c.jal', 'c.jalr']:
                instr_dict.append(self.__cj_instr__(op,val))
            elif self.fmt == 'jformat':
                instr_dict.append(self.__jfmt_instr__(op,val))
            else:
                instr_dict.append(self.__instr__(op,val))

        hits = defaultdict(lambda:OrderedSet([]))
        final_instr = []

        rm_dict = {
                'rne': 0,
                'rtz': 1,
                'rdn': 2,
                'rup': 3,
                'rmm': 4,
                'dyn': 7}

        def eval_inst_coverage(coverpoints,instr):
            cover_hits = {}
            var_dict = {}
            for key in self.val_vars:
                if key == 'imm_val':
                    if self.fmt in ['jformat','bformat'] or instr['inst'] in \
                        ['c.beqz','c.bnez','c.jal','c.j','c.jalr']:
                        var_dict['imm_val'] = \
                            (-1 if instr['label'] == '1b' else 1) * toint(instr['imm_val'])
                    else:
                        var_dict['imm_val'] = toint(instr['imm_val'])
                elif key == 'rm_val':
                    var_dict['rm_val'] = rm_dict[instr['rm_val']]
                else:
                    var_dict[key] = toint(instr[key])
            for key in self.op_vars:
                var_dict[key] = instr[key]


            instr_obj = instructionObject(None, instr['inst'], None)
            ext_specific_vars = instr_obj.evaluate_instr_var("ext_specific_vars", {**var_dict, 'flen': self.flen, 'iflen': self.iflen, 'inxFlag': self.inxFlag, 'xlen': self.xlen}, None, {'fcsr': hex(var_dict.get('fcsr', 0))})
            insn = instr['inst']
            # instructionObject() has an outdated list of instructions.
            # Let's make it support all FP instructions until this is fixed.
            # See https://github.com/riscv-software-src/riscv-isac/issues/69
            if (is_fp_instruction(insn)):
                insn = "fadd.s"
            instr_obj = instructionObject(None, insn, None)
            ext_specific_vars = instr_obj.evaluate_instr_var("ext_specific_vars", {**var_dict, 'flen': self.flen, 'iflen': self.iflen, 'inxFlag': self.inxFlag, 'xlen': self.xlen}, None, {'fcsr': hex(var_dict.get('fcsr', 0))})

            if ext_specific_vars is not None:
                var_dict.update(ext_specific_vars)

            if 'val_comb' in coverpoints:
                valcomb_hits = OrderedSet([])
                for coverpoint in coverpoints['val_comb']:
                    if eval(coverpoint,globals(),var_dict):
                        valcomb_hits.add(coverpoint)
                cover_hits['val_comb']=valcomb_hits
            if 'op_comb' in coverpoints:
                opcomb_hits = OrderedSet([])
                for coverpoint in coverpoints['op_comb']:
                    if eval(coverpoint,globals(),var_dict):
                        opcomb_hits.add(coverpoint)
                cover_hits['op_comb']=opcomb_hits
            if 'rs1' in coverpoints:
                if var_dict['rs1'] in coverpoints['rs1']:
                    cover_hits['rs1'] = OrderedSet([var_dict['rs1']])
            if 'rs2' in coverpoints:
                if var_dict['rs2'] in coverpoints['rs2']:
                    cover_hits['rs2'] = OrderedSet([var_dict['rs2']])
            if 'rs3' in coverpoints:
                if var_dict['rs3'] in coverpoints['rs3']:
                    cover_hits['rs3'] = OrderedSet([var_dict['rs3']])
            if 'rd' in coverpoints:
                if var_dict['rd'] in coverpoints['rd']:
                    cover_hits['rd'] = OrderedSet([var_dict['rd']])
            return cover_hits
        i = 0

        for instr in instr_dict:
            unique = False
            skip_val = False
            if instr['inst'] in cgf['mnemonics']:
                if 'rs1' in instr and 'rs2' in instr:
                    if instr['rs1'] == instr['rs2']:
                        skip_val = True
                if 'rs1' in instr:
                    if instr['rs1'] == 'x0' or instr['rs1'] == 'f0':
                        skip_val = True
                if 'rs2' in instr:
                    if instr['rs2'] == 'x0' or instr['rs2'] == 'f0':
                        skip_val = True
                if 'rd' in instr:
                    if instr['rd'] == 'x0' or instr['rd'] == 'f0':
                        skip_val = True
                cover_hits = eval_inst_coverage(cgf,instr)
                for entry in cover_hits:
                    if entry=='val_comb' and skip_val:
                       continue
                    over = hits[entry] & cover_hits[entry]
                    if over != cover_hits[entry]:
                        unique = unique or True
                    hits[entry] |= cover_hits[entry]
                if unique:
                    final_instr.append(instr)
                else:
                    i+=1

        if any('IP' in isa for isa in self.opnode['isa']):
            if 'p64_profile' in self.opnode:
                gen_pair_reg_data(final_instr, self.xlen, self.opnode['bit_width'], self.opnode['p64_profile'])
            elif 'bit_width' in self.opnode:
                concat_simd_data(final_instr, self.xlen, self.opnode['bit_width'])


        '''
        Zacas introduces double xlen cas operations that need paired source and destination registers
        '''
        if any('Zacas' in isa for isa in self.opnode['isa']):
            if 'dcas_profile' in self.opnode:
                gen_pair_reg_data(final_instr, self.xlen, self.opnode['bit_width'], self.opnode['dcas_profile'])

        return final_instr

    def valreg(self,instr_dict):
        '''
        This function is responsible for identifying which register can be used to store addresses
        to load values from memory.

        This register is calculated by traversing the dictionary of solutions
        created so far and removing all the registers which are used as either
        operands or destination. When 3 or less registers are pending, one of
        those registers is used as signature pointer for all the solutions
        traversed so far.

        Along with the register the offset is also assigned in this function.
        The offset is incremented by the amount specified in the template node bytes always.

        Care is taken to never use 'x0' as signature pointer.
        :param instr_dict: list of dictionaries containing the various values necessary for the macro
        :type instr_dict: list
        :return: list of dictionaries containing the various values necessary for the macro
        '''
        # TODO: Move flagreg allocation to separate function. Preferable to club all anxilliary
        # register allocations to a generalised function and club both swreg and valreg to it too.
        if 'val' in self.opnode:
            paired_regs=0
            if self.xlen == 32 and 'p64_profile' in self.opnode:
                p64_profile = self.opnode['p64_profile']
                paired_regs = self.opnode['p64_profile'].count('p')
            if 'dcas_profile' in self.opnode:
                dcas_profile = self.opnode['dcas_profile']
                paired_regs = self.opnode['dcas_profile'].count('p')

            regset = e_regset if 'e' in self.base_isa else default_regset
            total_instr = len(instr_dict)
            available_reg = regset.copy()
            available_reg.remove('x0')
            count = 0
            assigned = 0
            offset = 0
            stride = self.opnode['val']['stride']
            num_vars = len(self.op_vars)-1 if 'rd' in self.op_vars else len(self.op_vars)
            suffix = self.opnode['val']['sz']
            if flen in self.opnode:
                FLEN = max(self.opnode['flen'])
            else:
                FLEN = 0
            XLEN = max(self.opnode['xlen'])
            SIGALIGN = max(XLEN,FLEN)/8
            stride_sz = eval(suffix)
            template = Template(eval(self.opnode['val']['val_template']))
            width = self.iflen if self.is_fext else self.flen
            for instr in instr_dict:
                if 'rs1' in instr and instr['rs1'] in available_reg:
                    available_reg.remove(instr['rs1'])
                if 'rs2' in instr and instr['rs2'] in available_reg:
                    available_reg.remove(instr['rs2'])
                if 'rd' in instr and instr['rd'] in available_reg:
                    available_reg.remove(instr['rd'])
                if 'rs1_hi' in instr and instr['rs1_hi'] in available_reg:
                    available_reg.remove(instr['rs1_hi'])
                if 'rs2_hi' in instr and instr['rs2_hi'] in available_reg:
                    available_reg.remove(instr['rs2_hi'])
                if 'rd_hi' in instr and instr['rd_hi'] in available_reg:
                    available_reg.remove(instr['rd_hi'])
                if 'swreg' in instr and instr['swreg'] in available_reg:
                    available_reg.remove(instr['swreg'])
                if 'testreg' in instr and instr['testreg'] in available_reg:
                    available_reg.remove(instr['testreg'])
                if len(available_reg) <= 3+len(self.op_vars)+paired_regs:
                    curr_reg = available_reg[0]
                    offset = 0
                    for i in range(assigned, count+1):
                        if 'valaddr_reg' not in instr_dict[i]:
                            instr_dict[i]['valaddr_reg'] = curr_reg
                            instr_dict[i]['val_offset'] = str(offset) + '*' + suffix
                            offset += stride
                            if offset*stride_sz > 2047:
                                offset = 0
                            assigned += 1
                            instr_dict[i]['val_section'] = []
                            for j in range(1,num_vars+1):
                                dval = ()
                                if self.is_nan_box:
                                    dval = nan_box(instr_dict[i]['rs{0}_nan_prefix'.format(j)],
                                            instr_dict[i]['rs{0}_val'.format(j)],self.flen,self.iflen)
                                if self.is_sgn_extd:
                                    dval = sgn_extd(instr_dict[i]['rs{0}_sgn_prefix'.format(j)],
                                            instr_dict[i]['rs{0}_val'.format(j)],self.flen,self.iflen)
                                else:
                                    dval = (instr_dict[i]['rs{0}_val'.format(j)],width)
                                if self.is_fext:
                                    instr_dict[i]['flagreg'] = available_reg[1]
                                hex_dval = hex(int(dval[0]))
                                instr_dict[i]['val_section'].append(
                                        template.substitute(val=hex_dval,width=dval[1]))
                                instr_dict[i]['load_instr'] = self.opnode['val']['load_instr']
                    available_reg = regset.copy()
                    available_reg.remove('x0')
                count += 1
            if assigned != total_instr and len(available_reg) != 0:
                curr_reg = available_reg[0]
                offset = 0
                for i in range(len(instr_dict)):
                    if 'valaddr_reg' not in instr_dict[i]:
                        instr_dict[i]['valaddr_reg'] = curr_reg
                        instr_dict[i]['val_offset'] = str(offset) + '*' + suffix
                        offset += stride
                        if offset*stride_sz > 2047:
                            offset = 0
                        assigned += 1
                        instr_dict[i]['val_section'] = []
                        for j in range(1,num_vars+1):
                            dval = ()
                            if self.is_nan_box:
                                dval = nan_box(instr_dict[i]['rs{0}_nan_prefix'.format(j)],
                                        instr_dict[i]['rs{0}_val'.format(j)],self.flen,self.iflen)
                            else:
                                dval = (instr_dict[i]['rs{0}_val'.format(j)],width)
                            if self.is_fext:
                                instr_dict[i]['flagreg'] = available_reg[1]
                            hex_dval = hex(int(dval[0]))
                            instr_dict[i]['val_section'].append(
                                    template.substitute(hex_dval,width=dval[1]))
                            instr_dict[i]['load_instr'] = self.opnode['val']['load_instr']
            return instr_dict
        else:
            return instr_dict



    def swreg(self, instr_dict):
        '''
        This function is responsible for identifying which register can be used
        as a signature pointer for each instruction.

        This register is calculated by traversing the dictionary of solutions
        created so far and removing all the registers which are used as either
        operands or destination. When 3 or less registers are pending, one of
        those registers is used as signature pointer for all the solutions
        traversed so far.

        Along with the register the offset is also assigned in this function.
        The offset is incremented by the amount specified in the template node bytes always.

        Care is taken to never use 'x0' as signature pointer.
        :param instr_dict: list of dictionaries containing the various values necessary for the macro
        :type instr_dict: list
        :return: list of dictionaries containing the various values necessary for the macro
        '''
        # TODO: Clean this up and merge it with the code below to generalise adding val bases to
        # generic macro templates.

        paired_regs=0
        if self.xlen == 32 and 'p64_profile' in self.opnode:
            p64_profile = self.opnode['p64_profile']
            paired_regs = self.opnode['p64_profile'].count('p')
        if 'dcas_profile' in self.opnode:
            dcas_profile = self.opnode['dcas_profile']
            paired_regs = self.opnode['dcas_profile'].count('p')

        regset = e_regset if 'e' in self.base_isa else default_regset
        total_instr = len(instr_dict)
        available_reg = regset.copy()
        available_reg.remove('x0')
        count = 0
        assigned = 0
        offset = 0
        stride = self.opnode['sig']['stride']
        suffix = self.opnode['sig']['sz']
        if flen in self.opnode:
            FLEN = max(self.opnode['flen'])
        else:
            FLEN = 0
        XLEN = max(self.opnode['xlen'])
        SIGALIGN = max(XLEN,FLEN)/8
        stride_sz = eval(suffix)
        for instr in instr_dict:
            if 'rs1' in instr and instr['rs1'] in available_reg:
                available_reg.remove(instr['rs1'])
            if 'rs2' in instr and instr['rs2'] in available_reg:
                available_reg.remove(instr['rs2'])
            if 'rd' in instr and instr['rd'] in available_reg:
                available_reg.remove(instr['rd'])
            if 'rs1_hi' in instr and instr['rs1_hi'] in available_reg:
                available_reg.remove(instr['rs1_hi'])
            if 'rs2_hi' in instr and instr['rs2_hi'] in available_reg:
                available_reg.remove(instr['rs2_hi'])
            if 'rd_hi' in instr and instr['rd_hi'] in available_reg:
                available_reg.remove(instr['rd_hi'])
            if 'testreg' in instr and instr['testreg'] in available_reg:
                available_reg.remove(instr['testreg'])

            if len(available_reg) <= 2+len(self.op_vars)+paired_regs:
                curr_swreg = available_reg[0]
                offset = 0
                for i in range(assigned, count+1):
                    if 'swreg' not in instr_dict[i]:
                        instr_dict[i]['offset'] = str(offset) + '*' + suffix
                        offset += stride
                        if offset*stride_sz > 2047:
                            offset = 0
                        instr_dict[i]['swreg'] = curr_swreg
                        assigned += 1
                available_reg = regset.copy()
                available_reg.remove('x0')
            count += 1
        if assigned != total_instr and len(available_reg) != 0:
            curr_swreg = available_reg[0]
            offset = 0
            for i in range(len(instr_dict)):
                if 'swreg' not in instr_dict[i]:
                    instr_dict[i]['offset'] = str(offset) + '*' + suffix
                    offset += stride
                    if offset*stride_sz > 2047:
                        offset = 0
                    instr_dict[i]['swreg'] = curr_swreg
        return instr_dict

    def testreg(self, instr_dict):
        '''
        This function is responsible for identifying which register can be used
        as a test register for each instruction.

        This register is calculated by traversing the dictionary of solutions
        created so far and removing all the registers which are used as either
        operands or destination or signature. When 3 or less registers are pending, one of
        those registers is used as test register for all the solutions
        traversed so far.

        Care is taken to never use 'x0' as test register.
        :param instr_dict: list of dictionaries containing the various values necessary for the macro
        :type instr_dict: list
        :return: list of dictionaries containing the various values necessary for the macro
        '''
        regset = e_regset if 'e' in self.base_isa else default_regset
        total_instr = len(instr_dict)
        available_reg = regset.copy()
        available_reg.remove('x0')
        count = 0
        assigned = 0

        paired_regs=0
        if self.xlen == 32 and 'p64_profile' in self.opnode:
            p64_profile = self.opnode['p64_profile']
            paired_regs = p64_profile.count('p')
        if 'dcas_profile' in self.opnode:
            dcas_profile = self.opnode['dcas_profile']
            paired_regs = dcas_profile.count('p')

        for instr in instr_dict:
            if 'rs1' in instr and instr['rs1'] in available_reg:
                available_reg.remove(instr['rs1'])
                if 'rs1_hi' in instr and instr['rs1_hi'] in available_reg:
                    available_reg.remove(instr['rs1_hi'])
            if 'rs2' in instr and instr['rs2'] in available_reg:
                available_reg.remove(instr['rs2'])
                if 'rs2_hi' in instr and instr['rs2_hi'] in available_reg:
                    available_reg.remove(instr['rs2_hi'])
            if 'rd' in instr and instr['rd'] in available_reg:
                available_reg.remove(instr['rd'])
                if 'rd_hi' in instr and instr['rd_hi'] in available_reg:
                    available_reg.remove(instr['rd_hi'])
            if 'swreg' in instr and instr['swreg'] in available_reg:
                available_reg.remove(instr['swreg'])

            if len(available_reg) <= 2+len(self.op_vars)+paired_regs:
                curr_testreg = available_reg[0]
                for i in range(assigned, count+1):
                    if 'testreg' not in instr_dict[i]:
                        instr_dict[i]['testreg'] = curr_testreg
                        assigned += 1
                available_reg = regset.copy()
                available_reg.remove('x0')
            count += 1
        if assigned != total_instr and len(available_reg) != 0:
            curr_testreg = available_reg[0]
            for i in range(len(instr_dict)):
                if 'testreg' not in instr_dict[i]:
                    instr_dict[i]['testreg'] = curr_testreg
        return instr_dict

    def correct_val(self,instr_dict):
        '''
        this function is responsible for assigning the correct-vals for all instructions.
        The correctvals are calculated based on the `operation` field of the node
        in the attributes YAML. If the operation field is empty, then a value of
        0 is assigned to the correctval.
        :param instr_dict: list of dictionaries containing the various values necessary for the macro
        :type instr_dict: list
        :return: list of dictionaries containing the various values necessary for the macro
        '''
        if self.opcode[0] == 'f' and 'fence' not in self.opcode:
            for i in range(len(instr_dict)):
                instr_dict[i]['correctval'] = '0'
            return instr_dict
        if self.xlen == 32 and 'p64_profile' in self.opnode:
            p64_profile = self.opnode['p64_profile']
            if len(p64_profile) >= 3 and p64_profile[0]=='p':
                for i in range(len(instr_dict)):
                    instr_dict[i]['correctval_hi'] = '0'
        if 'dcas_profile' in self.opnode:
            dcas_profile = self.opnode['dcas_profile']
            if len(dcas_profile) >= 3 and dcas_profile[0]=='p':
                for i in range(len(instr_dict)):
                    instr_dict[i]['correctval_hi'] = '0'
        if self.fmt in ['caformat','crformat']:
            normalise = lambda x,y: 0 if y['rs1']=='x0' else x
        else:
            normalise = (lambda x,y: x) if 'rd' not in self.op_vars else (lambda x,y: 0 if y['rd']=='x0' else x)
        if self.operation:
            for i in range(len(instr_dict)):
                for var in self.val_vars:
                    locals()[var]=toint(instr_dict[i][var])
                correctval = eval(self.operation)
                instr_dict[i]['correctval'] = str(normalise(correctval,instr_dict[i]))
        else:
            for i in range(len(instr_dict)):
                instr_dict[i]['correctval'] = '0x' + '0'.zfill(int(self.xlen/4))
        return instr_dict

    def reformat_instr(self, instr_dict):
        '''
        This function basically sanitizes the integer values to a readable
        hex values
        :param instr_dict: list of dictionaries containing the various values necessary for the macro
        :type instr_dict: list
        :return: list of dictionaries containing the various values necessary for the macro
        '''
        if any('IP' in isa for isa in self.opnode['isa']):
            # instr_dict is already in the desired format for instructions that perform SIMD operations, or Zpsfoperand instructions in RV32.
            if 'bit_width' in self.opnode or (self.xlen == 32 and 'p64_profile' in self.opnode):
                return instr_dict
        if any('Zacas' in isa for isa in self.opnode['isa']):
            # instr_dict is already in the desired format for Zacas dcas instructions
            if 'bit_width' in self.opnode or 'dcas_profile' in self.opnode:
                return instr_dict
        
        # Fix all K instructions to be unsigned to output unsigned hex values into the test. Its
        # only a cosmetic difference and has no impact on coverage
        is_unsigned = any('IZk' in isa for isa in self.opnode['isa'])

        for i in range(len(instr_dict)):
            for field in instr_dict[i]:
                if xlen == 32:
                    if instr_dict[i]['inst'] in ['sltu', 'sltiu', 'bgeu', 'bltu'] or is_unsigned:
                        size = '>I'
                    else:
                        size = '>i'
                else:
                    if instr_dict[i]['inst'] in ['sltu', 'sltiu', 'bgeu', 'bltu'] or is_unsigned:
                        size = '>Q'
                    else:
                        size = '>q'
                if 'val' in field and field != 'correctval' and field != 'valaddr_reg' and \
                    field != 'val_section' and field != 'val_offset' and field != 'rm_val':
                    value = (instr_dict[i][field]).strip()
                    #print(value)
                    if '0x' in value:
                        value = '0x' + value[2:].zfill(int(self.xlen/4))
                        value = struct.unpack(size, bytes.fromhex(value[2:]))[0]
                    else:
                        value = int(value)
#                    value = '0x' + struct.pack(size,value).hex()
                    #print("test",hex(value))
                    instr_dict[i][field] = hex(value)
        return instr_dict

    def write_test(self, fprefix, node, label, instr_dict, op_node, usage_str,max_inst):
        start = 0
        total = len(instr_dict)
        end = len(instr_dict)
        if max_inst:
           end = max_inst
        else:
            max_inst = total
        i = 1
        while end <= total and start<total:
            fname = fprefix+("-{:02d}.S".format(i))
            logger.debug("Writing Test to "+str(fname))
            self.__write_test__(fname,node,label,instr_dict[start:end], op_node, usage_str)
            start += max_inst
            left = total - end
            i+=1
            if left>=max_inst:
                end += max_inst
            else:
                end = total


    def __write_test__(self, file_name,node,label,instr_dict, op_node, usage_str):
        '''
        This function generates the test using various templates.

        :param file_name: path of the output file
        :param node: a covergroup in cgf format containing the set of coverpoints to be satisfied
        :param label: the label for the covergroup in the input cgf file
        :param instr_dict: list of dictionaries containing the various values necessary for the macro
        :param op_node: dictionary node from the attributes YAML that is to be used in the test generation
        :param usage_str: Banner string for the test

        :type file_name: str
        :type node: dict
        :type label: str
        :type instr_dict: list
        :type op_node: dict
        :type usage_str: str
        '''
        regs = defaultdict(lambda: 0)
        sreg = instr_dict[0]['swreg']
        vreg = None
        code = []
        sign = [""]
        data = [".align 4","rvtest_data:",".word 0xbabecafe", \
                ".word 0xabecafeb", ".word 0xbecafeba", ".word 0xecafebab"]
        stride = self.opnode['sig']['stride']
        if self.is_fext:
            code.append("RVTEST_FP_ENABLE()")

        if any('IP' in isa for isa in self.opnode['isa']):
            code.append("RVTEST_VXSAT_ENABLE()")
        if self.xlen == 32 and 'p64_profile' in self.opnode:
            p64_profile = self.opnode['p64_profile']
        if 'dcas_profile' in self.opnode:
            dcas_profile = self.opnode['dcas_profile']

        n = 0
        is_int_src = any([self.opcode.endswith(x) for x in ['.x','.w','.l','.wu','.lu']]) or self.inxFlag
        src_len = xlen if self.opcode.endswith('.x') else (32 if 'w' in self.opcode else 64)
        sz = 'word' if src_len == 32 else 'dword'
        opcode = instr_dict[0]['inst']
        op_node_isa = ""
        extension = ""
        xlens = [self.xlen] + \
            (list(filter(lambda x: x>self.xlen,self.opnode['xlen'])) if self.is_fext else [])
        for val in xlens:
            rvxlen = "RV"+str(val)
            op_node_isa += ((","  if op_node_isa else "") \
                    + ",".join([rvxlen + isa for isa in op_node['isa']]))
        op_node_isa = op_node_isa.replace("I","E") if 'e' in self.base_isa else op_node_isa
        extension = op_node_isa.replace('I',"").replace('E',"")
        count = 0
        neg_offset = 0
        width = self.iflen if not self.is_nan_box else self.flen
        dset_n = 0
        sig_sz = '(({0})/4)'.format(self.opnode['sig']['sz'])
        cond_prefix = '' if self.is_fext else 'check ISA:=regex(.*{0}.*);'.format(self.xlen)
        for instr in instr_dict:
            switch = False
            res = '\ninst_{0}:'.format(str(count))
            res += Template(op_node['template']).safe_substitute(instr)
            if 'val' in self.opnode:
                if eval(instr['val_offset'],{},
                        {'FLEN':width,'XLEN':self.xlen,'SIGALIGN':max(self.xlen,self.flen)/8}
                        ) == 0 or instr['valaddr_reg'] != vreg:
                    dlabel = 'test_dataset_'+str(dset_n)
                    dset_n += 1
                    data.append(dlabel+":")
                    vreg = instr['valaddr_reg']
                    code.append("RVTEST_VALBASEUPD("+vreg+","+dlabel+")")
                # for i in range(1,num_vars+1):
                #     dval = ()
                #     if self.is_nan_box:
                #         dval = nan_box(instr['rs{0}_nan_prefix'.format(i)],
                #                 instr['rs{0}_val'.format(i)],self.flen,self.iflen)
                #     else:
                #         dval = (instr['rs{0}_val'.format(i)],self.iflen)
                data.extend(instr['val_section'])
            if instr['swreg'] != sreg or eval(instr['offset'],{},
                        {'FLEN':width,'XLEN':self.xlen,'SIGALIGN':max(self.xlen,self.flen)/8}) == 0:
                sign.append(signode_template.substitute(
                    {'n':n,'label':"signature_"+sreg+"_"+str(regs[sreg]),'sz':sig_sz}))
                n = stride
                regs[sreg]+=1
                sreg = instr['swreg']
                code.append("RVTEST_SIGBASE("+sreg+",signature_"+sreg+"_"+str(regs[sreg])+")")
            else:
                n+=stride
            code.append(res)
            count = count + 1
        case_str = ''.join([case_template.safe_substitute(xlen=self.xlen,num=i,cond=cond,cov_label=label) for i,cond in enumerate(node['config'])])
        sign.append(signode_template.substitute({'n':n,
                'label':"signature_"+sreg+"_"+str(regs[sreg]),'sz':sig_sz}))
        test = part_template.safe_substitute(case_str=case_str,code='\n'.join(code))
        sign.append("#ifdef rvtest_mtrap_routine\ntsig_begin_canary:\nCANARY;\n"+signode_template.substitute(
            {'n':64,'label':"mtrap_sigptr",'sz':'XLEN/32'})+"\ntsig_end_canary:\nCANARY;\n#endif\n")
        sign.append("#ifdef rvtest_gpr_save\n"+signode_template.substitute(
            {'n':32,'label':"gpr_save",'sz':'XLEN/32'})+"\n#endif\n")
        with open(file_name,"w") as fd:
            fd.write(usage_str + test_template.safe_substitute(data='\n'.join(data),test=test,sig='\n'.join(sign),isa=op_node_isa,opcode=opcode,extension=extension,label=label))
