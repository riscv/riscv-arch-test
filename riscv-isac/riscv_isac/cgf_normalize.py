# See LICENSE.incore for details
from math import *
import pprint
import riscv_isac.utils as utils
import itertools
import random
import copy
from riscv_isac.fp_dataset import *

import time

def twos(val,bits):
    '''
    Finds the twos complement of the number
    :param val: input to be complemented
    :param bits: size of the input

    :type val: str or int
    :type bits: int

    :result: two's complement version of the input

    '''
    if isinstance(val,str):
        if '0x' in val:
            val = int(val,16)
        else:
            val = int(val,2)
    if (val & (1 << (bits - 1))) != 0:
        val = val - (1 << bits)
    return val

def simd_val_comb(xlen, bit_width, signed=True):
    '''
    This function returns coverpoints for operands rs1 and rs2 holding SIMD values. A set of coverpoints will be produced for each SIMD element.

    :param xlen: size of the integer registers
    :param bit_width: size of each SIMD element
    :param signed: whether the SIMD elements are signed or unsigned

    :type xlen: int
    :type bit_width: int
    :type signed: bool
    '''

    fmt = {8: 'b', 16: 'h', 32: 'w', 64: 'd'}
    sz = fmt[bit_width]
    var_num = xlen//bit_width
    coverpoints = []
    for i in range(var_num):
        var1 = f'rs1_{sz}{i}_val'
        var2 = f'rs2_{sz}{i}_val'
        if (signed):
            coverpoints += [(f'{var1} > 0 and {var2} > 0','simd_val_comb')]
            coverpoints += [(f'{var1} > 0 and {var2} < 0','simd_val_comb')]
            coverpoints += [(f'{var1} < 0 and {var2} < 0','simd_val_comb')]
            coverpoints += [(f'{var1} < 0 and {var2} > 0','simd_val_comb')]
            coverpoints += [(f'{var1} == {var2}','simd_val_comb')]
            coverpoints += [(f'{var1} != {var2}','simd_val_comb')]
        else:
            coverpoints += [(f'{var1} == {var2} and {var1} > 0 and {var2} > 0','simd_val_comb')]
            coverpoints += [(f'{var1} != {var2} and {var1} > 0 and {var2} > 0','simd_val_comb')]

    return coverpoints

def simd_base_val(rs, xlen, bit_width, signed=True):
    '''
    This function returns datasets for an operand holding SIMD values. One set of data will be produced for each SIMD element.

    :param rs: operand name: "rs1" or "rs2"
    :param xlen: size of the integer registers
    :param bit_width: size of each SIMD element
    :param signed: whether the SIMD elements are signed or unsigned

    :type rs: str
    :type xlen: int
    :type bit_width: int
    :type signed: bool
    '''

    fmt = {8: 'b', 16: 'h', 32: 'w', 64: 'd'}

    sz = fmt[bit_width]
    var_num = xlen//bit_width
    sign_val = [(-2**(bit_width-1)), -1, 0, 1, int((2**(bit_width-1)-1))]
    usign_val = [0, 1, 2**bit_width-2, 2**bit_width-1]
    coverpoints = []
    for i in range(var_num):
        var = f'{rs}_{sz}{i}_val'
        if (signed):
            for val in sign_val:
                coverpoints += [(f'{var} == {val}', 'signed_min_max_middle')]
            coverpoints += walking_ones(var, bit_width, True)
            coverpoints += walking_zeros(var, bit_width, True)
            coverpoints += alternate(var, bit_width, True)
        else:
            for val in usign_val:
                coverpoints += [(f'{var} == {val}','unsigned_min_max_middle')]
            coverpoints += walking_ones(var, bit_width, False)
            coverpoints += walking_zeros(var, bit_width, False)
            coverpoints += alternate(var, bit_width, False)
    return coverpoints

def simd_imm_val(imm, bit_width):
    '''
    This function returns coverpoints for unsigned immediate operands, between 0 .. ((2**bit_width)-1)

    :param imm: name of the immediate operand.
    :param bit_width: bit width of the immediate operand

    :type imm: str
    :type bit_width: int
    '''
    usign_val = 2**bit_width
    coverpoints = []
    for i in range(usign_val):
        coverpoints += [(f'{imm} == {i}','simd_imm_val')]
    return coverpoints

def sp_vals(bit_width,signed):
    if signed:
        conv_func = lambda x: twos(x,bit_width)
        sqrt_min = int(-sqrt(2**(bit_width-1)))
        sqrt_max = int(sqrt((2**(bit_width-1)-1)))
    else:
        sqrt_min = 0
        sqrt_max = int(sqrt((2**bit_width)-1))
        conv_func = lambda x: (int(x,16) if '0x' in x else int(x,2)) if isinstance(x,str) else x
    dataset = [3, "0x"+"".join(["5"]*int(bit_width/4)), "0x"+"".join(["a"]*int(bit_width/4)), 5, "0x"+"".join(["3"]*int(bit_width/4)), "0x"+"".join(["6"]*int(bit_width/4))]
    dataset = list(map(conv_func,dataset)) + [int(sqrt(abs(conv_func("0x8"+"".join(["0"]*int((bit_width/4)-1)))))*(-1 if signed else 1))] + [sqrt_min,sqrt_max]
    return dataset + [x - 1 if x>0 else 0 for x in dataset] + [x+1 for x in dataset]

def bitmanip_dataset(bit_width,var_lst=["rs1_val","rs2_val"],signed=True):
    '''
    Functions creates coverpoints for bitmanip instructions with following patterns
    0x3, 0xc, 0x5,0xa,0x6,0x9,0 each of the pattern exenteding for bit_width
    for 32 bit
    0x33333333,0xcccccccc,0x55555555, 0xaaaaaaaaa,0x66666666,0x99999999
    for 64 bit
    0x3333333333333333,0xcccccccccccccccc,0x5555555555555555, 0xaaaaaaaaaaaaaaaaa,
    0x6666666666666666,0x9999999999999999
     - +1 and -1 variants of the above pattern


     :param bit_width: Integer defining the size of the input
     :param sign: Boolen value specifying whether the dataset should be interpreted as signed numbers or not.
     :type sign: bool
     :type bit_width: int
     :return: dictionary of coverpoints
    '''

    datasets = []
    coverpoints = []
    if signed:
        conv_func = lambda x: twos(x,bit_width)
    else:
        conv_func = lambda x: (int(x,16) if '0x' in x else int(x,2)) if isinstance(x,str) else x
# dataset for 0x5, 0xa, 0x3, 0xc, 0x6, 0x9 patterns
    dataset = ["0x"+"".join(["5"]*int(bit_width/4)), "0x"+"".join(["a"]*int(bit_width/4)), "0x"+"".join(["3"]*int(bit_width/4)), "0x"+"".join(["c"]*int(bit_width/4)),"0x"+"".join(["6"]*int(bit_width/4)),"0x"+"".join(["9"]*int(bit_width/4))]
    dataset = list(map(conv_func,dataset))

# dataset0 is  for 0,1 and 0xf pattern. 0xf pattern is added instead of -1 so that code for checking coverpoints in coverage.py
# is kept simple.

    dataset0 = [0,1,"0x"+"".join(["f"]*int(bit_width/4))]
    dataset0 = list(map(conv_func,dataset0))
    dataset = dataset +  [x - 1 for x in dataset] + [x+1 for x in dataset] + dataset0
    for var in var_lst:
        datasets.append(dataset)
    dataset = itertools.product(*datasets)
    for entry in dataset:
        coverpoints.append(' and '.join([var_lst[i]+"=="+str(entry[i]) for i in range(len(var_lst))]))
    return [(coverpoint,"Bitmanip Dataset") for coverpoint in coverpoints]



def sp_dataset(bit_width,var_lst=["rs1_val","rs2_val"],signed=True):
    coverpoints = []
    datasets = []
    var_names = []
    for var in var_lst:
        if isinstance(var,tuple) or isinstance(var,list):
            if len(var) == 3:
                var_sgn = var[2]
            else:
                var_sgn = signed
            var_names.append(var[0])
            datasets.append(sp_vals(int(var[1]),var_sgn))
        else:
            var_names.append(var)
            datasets.append(sp_vals(bit_width,signed))
    dataset = itertools.product(*datasets)
    for entry in dataset:
        coverpoints.append(' and '.join([var_names[i]+"=="+str(entry[i]) for i in range(len(var_names))]))
    return [(coverpoint,"Special Dataset") for coverpoint in coverpoints]

def walking_ones(var, size, signed=True, fltr_func=None, scale_func=None):
    '''
    This function converts an abstract walking-ones function into individual
    coverpoints that can be used by ISAC. The unrolling of the function accounts
    of the size, sign-bit, filters and scales. The unrolled coverpoints will
    contain a pattern a single one trickling down from LSB to MSB. The final
    coverpoints can vary depending on the filtering and scaling functions

    :param var: input variable that needs to be assigned the coverpoints
    :param size: size of the bit-vector to generate walking-1s
    :param signed: when true indicates that the unrolled points be treated as signed integers.
    :param fltr_func: a lambda function which defines a filtering routine to keep only a certain values from the unrolled coverpoints
    :param scale_func: a lambda function which defines the scaling that should be applied to the unrolled coverpoints that have been generated.

    :type var: str
    :type size: int
    :type signed: bool
    :type fltr_func: function
    :type scale_func: function
    :result: dictionary of unrolled filtered and scaled coverpoints
    '''
    if not signed:
        dataset = [1 << exp for exp in range(size)]
    else:
        dataset = [twos(1 << exp,size) for exp in range(size)]
    if scale_func:
        dataset = [scale_func(x) for x in dataset]
    if fltr_func:
        dataset = filter(fltr_func,dataset)
    coverpoints =[]
    for d in dataset:
        coverpoints.append((var + ' == ' + str(d),'Walking Ones: '+str(hex(d))))
    return coverpoints

def walking_zeros(var, size,signed=True, fltr_func=None, scale_func=None):
    '''
    This function converts an abstract walking-zeros function into individual
    coverpoints that can be used by ISAC. The unrolling of the function accounts
    of the size, sign-bit, filters and scales. The unrolled coverpoints will
    contain a pattern a single zero trickling down from LSB to MSB. The final
    coverpoints can vary depending on the filtering and scaling functions

    :param var: input variable that needs to be assigned the coverpoints
    :param size: size of the bit-vector to generate walking-1s
    :param signed: when true indicates that the unrolled points be treated as signed integers.
    :param fltr_func: a lambda function which defines a filtering routine to keep only a certain values from the unrolled coverpoints
    :param scale_func: a lambda function which defines the scaling that should be applied to the unrolled coverpoints that have been generated.

    :type var: str
    :type size: int
    :type signed: bool
    :type fltr_func: function
    :type scale_func: function
    :result: dictionary of unrolled filtered and scaled coverpoints
    '''
    mask = 2**size -1
    if not signed:
        dataset = [(1 << exp)^mask for exp in range(size)]
    else:
        dataset = [twos((1 << exp)^mask,size) for exp in range(size)]
    if scale_func:
        dataset = [scale_func(x) for x in dataset]
    if fltr_func:
        dataset = filter(fltr_func,dataset)
    coverpoints =[]
    for d in dataset:
        coverpoints.append((var + ' == ' + str(d),'Walking Zeros: '+str(hex(d))))
    return coverpoints

def byte_count(xlen, variables=['rs1_val','rs2_val','imm_val'], overlap = "N"):
    '''
    Test pattern 1: SBox Testing
    This uses the byte-count pattern described above.
    Generate a 256-byte sequence 0..255 and pack the sequence into 32-bit words.
    Each word in the sequence is the rs2 input. The rs1 input is set to zero so we do not alter the SBox output value.
    For each input word, generate 4 instructions, with bs=0..3.
    This will mean that every possible SBox input pattern is tested.

    :param xlen: size of the bit-vector to generate byte-count pattern
    :param variables: list of string variables indicating the operands
    :param overlap: Set "Y" to test byte-count pattern on lower word of the xlen-bit vector, else set "N".

    :type xlen: int
    :type variables: List[str]
    :type overlap: str

    '''
    rs1 = 0
    rs2 = []
    coverpoints = []
    hex_str = ""
    i=0
    cvpt = ""
    max = 255
    if overlap == "Y":
    	max += xlen/16
    while(i<=max):
    	hex_str = "{:02x}".format(i % 256) + hex_str
    	if((len(hex_str)/2)%(xlen/8) == 0):
    		rs2.append('0x'+hex_str)
    		hex_str = ""
    		if(overlap == "Y"):
    			i=int(i-(xlen/16))
    	i=i+1

    if xlen == 32:
    	for i in range(len(rs2)):
    		for j in range(4):
    			coverpoints.append(variables[0] +' == '+ str(rs1) +' and '+ variables[1] +' == '+ rs2[i] + ' and '+ variables[2] +' == '+ str(j) + ' #nosat')
    else:
    	if variables[1] == "rs2_val":
    		for i in range(len(rs2)):
    			if((i+1)%2==0):
    				y = rs2[i-1]
    				x = rs2[i]
    			else:
    				x = rs2[i]
    				y = rs2[i+1]
    			cvpt = variables[0] +' == '+ x +' and '+ variables[1] +' == '+ y
    			if len(variables)==3:
    				if variables[2] == "imm_val":
    					for j in range(4):
    						coverpoints.append(cvpt+' and imm_val == '+ str(j) + ' #nosat')
    			else:
    				coverpoints.append(cvpt + ' #nosat')
    			cvpt = ""
    	elif variables[1] == "imm_val":
    		for i in range(len(rs2)):
    			coverpoints.append(variables[0] +' == '+ rs2[i] +' and '+ variables[1] +' == 0xA' + ' #nosat')
    return [(coverpoint,"Byte Count") for coverpoint in coverpoints]

def uniform_random(N=10, seed=9, variables=['rs1_val','rs2_val','imm_val'], size=[32,32,2]):
    '''
    Test pattern 2: Uniform Random
    Generate uniform random values for rs1, rs2 and bs.
    Let register values be un-constrained: 0..31.
    Repeat N times for each instruction until sufficient coverage is reached.

    :param N: Number of random combinations to be generated
    :param seed: intial seed value of the random library
    :param variables: list of string variables indicating the operands
    :param size: list of bit-sizes of each variable defined in variables.

    :type N: int
    :type seed: int
    :type variables: List[str]
    :type size: List[int]

    '''
    random.seed(seed)

    coverpoints = []
    while N!= 0:
    	random_vals = []
    	for v in range(len(variables)):
    		val = random.randint(0,2**int(size[v])-1)
    		random_vals.append(variables[v] + \
    		' == {0:#0{1}x}'.format(val,int(size[v]/4)+2))
    	coverpoints.append((" and ".join(random_vals) + " #nosat",\
                "Uniform Random "+str(N)))
    	N = N-1

    return coverpoints

def leading_ones(xlen, var = ['rs1_val','rs2_val'], sizes = [32,32], seed = 10):
    '''
    For each variable in var, generate a random input value, and set the most-significant i bits.
    See the other rs input and set a random value.

    :param xlen: size of the bit-vector to generate leading-1s
    :param var: list of string variables indicating the operands
    :param sizes: list of sizes of the variables in var
    :param seed: intial seed value of the random library

    :type xlen: int
    :type var: List[str]
    :type sizes: List[int]
    :type seed: int
    '''
    random.seed(seed)
    coverpoints = []
    for i in range(0,len(var)):
        curr_var = var[i]
        curr_sz = sizes[i]
        default = 2**curr_sz-1
        for sz in range(0,curr_sz+1):
           cvpt = ''
           val = (default << sz) & default
           setval = (1 << sz-1) ^ default if sz!=0 else default
           val = (val | random.randrange(1,2**curr_sz)) & default & setval
           cvpt += curr_var + ' == 0x{0:0{1}X}'.format(val,int(ceil(curr_sz/4)))
           cmnt = '{1} Leading ones for {0}. Other operands are random'.\
                   format(curr_var, curr_sz-sz)
           for othervars in range(0,len(var)):
               if othervars != i:
                   otherval = random.randrange(0,2**sizes[othervars])
                   cvpt += ' and ' + var[othervars] + ' == 0x{0:0{1}X}'.format(otherval,int(ceil(sizes[othervars]/4)))
           coverpoints.append((cvpt+ " #nosat", cmnt))
    return coverpoints

def leading_zeros(xlen, var = ['rs1_val','rs2_val'], sizes = [32,32], seed = 11):
    '''
    For each rs register input, generate a random XLEN input value, and clear the most-significant i bits.
    See the other rs input, pick a random value.

    :param xlen: size of the bit-vector to generate leading-0s
    :param var: list of string variables indicating the operands
    :param sizes: list of sizes of the variables in var
    :param seed: intial seed value of the random library

    :type xlen: int
    :type var: List[str]
    :type sizes: List[int]
    :type seed: int

    '''
    random.seed(seed)
    coverpoints = []
    for i in range(0,len(var)):
        curr_var = var[i]
        curr_sz = sizes[i]
        default = 2**curr_sz-1
        for sz in range(0,curr_sz+1):
           cvpt = ''
           val = (1 << sz)-1 & default
           setval = 1 << (sz-1) if sz!=0 else 0
           val = (val & random.randrange(1,2**curr_sz)) & default | setval
           cvpt += curr_var + ' == 0x{0:0{1}X}'.format(val,int(ceil(curr_sz/4)))
           cmnt = '{1} Leading zeros for {0}. Other operands are random'.\
                   format(curr_var, curr_sz-sz)
           for othervars in range(0,len(var)):
               if othervars != i:
                   otherval = random.randrange(0,2**sizes[othervars])
                   cvpt += ' and ' + var[othervars] + ' == 0x{0:0{1}X}'.format(otherval,int(ceil(sizes[othervars]/4)))
           coverpoints.append((cvpt+ " #nosat",cmnt))
    return coverpoints


def trailing_zeros(xlen, var = ['rs1_val','rs2_val'], sizes = [32,32], seed = 12):
    '''
    For each rs register input, generate a random XLEN input value, and clear the least-significant i bits.
    See the other rs input, pick a random value.

    :param xlen: size of the bit-vector to generate trailing-0s
    :param var: list of string variables indicating the operands
    :param sizes: list of sizes of the variables in var
    :param seed: intial seed value of the random library

    :type xlen: int
    :type var: List[str]
    :type sizes: List[int]
    :type seed: int

    '''
    random.seed(seed)
    coverpoints = []
    for i in range(0,len(var)):
        curr_var = var[i]
        curr_sz = sizes[i]
        default = 2**curr_sz-1
        for sz in range(0,curr_sz+1):
           cvpt = ''
           val = (default << sz) & default
           setval = (1 << sz) & default
           val = (val & (random.randrange(1,2**curr_sz)<<sz)) & default
           val = val | setval
           cvpt += curr_var + ' == 0x{0:0{1}X}'.format(val,int(ceil(curr_sz/4)))
           cmnt = '{1} Trailing zeros for {0}. Other operands are random'.\
                   format(curr_var, sz)
           for othervars in range(0,len(var)):
               if othervars != i:
                   otherval = random.randrange(0,2**sizes[othervars])
                   cvpt += ' and ' + var[othervars] + ' == 0x{0:0{1}X}'.format(otherval,int(ceil(sizes[othervars]/4)))
           coverpoints.append((cvpt+ " #nosat",cmnt))
    return coverpoints

def trailing_ones(xlen, var = ['rs1_val','rs2_val'], sizes = [32,32], seed = 13):
    '''
    For each rs register input, generate a random XLEN input value, and set the least-significant i bits.
    See the other rs input, pick a random value.

    :param xlen: size of the bit-vector to generate trailing-1s
    :param var: list of string variables indicating the operands
    :param sizes: list of sizes of the variables in var
    :param seed: intial seed value of the random library

    :type xlen: int
    :type var: List[str]
    :type sizes: List[int]
    :type seed: int

    '''
    random.seed(seed)
    coverpoints = []
    for i in range(0,len(var)):
        curr_var = var[i]
        curr_sz = sizes[i]
        default = (2**curr_sz)-1
        for sz in range(0,curr_sz+1):
           cvpt = ''
           val = random.randrange(1,(2**curr_sz))
           setval = (1<<(curr_sz-sz)) ^ (default)
           val = val | (default>> sz)
           val = val & setval
           cvpt += curr_var + ' == 0x{0:0{1}X}'.format(val,int(ceil(curr_sz/4)))
           cmnt = '{1} Trailing ones for {0}. Other operands are random'.\
                   format(curr_var, curr_sz-sz)
           for othervars in range(0,len(var)):
               if othervars != i:
                   otherval = random.randrange(0,2**sizes[othervars])
                   cvpt += ' and ' + var[othervars] + ' == 0x{0:0{1}X}'.format(otherval,int(ceil(sizes[othervars]/4)))
           coverpoints.append((cvpt+ " #nosat",cmnt))
    return coverpoints


def alternate(var, size, signed=True, fltr_func=None,scale_func=None):
    '''
    This function converts an abstract alternate function into individual
    coverpoints that can be used by ISAC. The unrolling of the function accounts
    of the size, sign-bit, filters and scales. The unrolled coverpoints will
    contain a pattern of alternating 1s and 0s. The final
    coverpoints can vary depending on the filtering and scaling functions

    :param var: input variable that needs to be assigned the coverpoints
    :param size: size of the bit-vector to generate walking-1s
    :param signed: when true indicates that the unrolled points be treated as signed integers.
    :param fltr_func: a lambda function which defines a filtering routine to keep only a certain values from the unrolled coverpoints
    :param scale_func: a lambda function which defines the scaling that should be applied to the unrolled coverpoints that have been generated.

    :type var: str
    :type size: int
    :type signed: bool
    :type fltr_func: function
    :type scale_func: function

    :result: dictionary of unrolled filtered and scaled coverpoints
    '''
    t1 =( '' if size%2 == 0 else '1') + ''.join(['01']*int(size/2))
    t2 =( '' if size%2 == 0 else '0') + ''.join(['10']*int(size/2))
    if not signed:
        dataset = [int(t1,2),int(t2,2)]
    else:
        dataset = [twos(t1,size),twos(t2,size)]
    if scale_func:
        dataset = [scale_func(x) for x in dataset]
    if fltr_func:
        dataset = filter(fltr_func,dataset)
    coverpoints =[]
    for d in dataset:
        coverpoints.append((var + ' == ' + str(d),'Alternate: '+str(hex(d))))
    return coverpoints
    #coverpoints = [var + ' == ' + str(d) for d in dataset]
    #return [(coverpoint,"Alternate") for coverpoint in coverpoints]


def expand_cgf(cgf_files, xlen,flen, log_redundant=False):
    '''
    This function will replace all the abstract functions with their unrolled
    coverpoints. It replaces node

    :param cgf_files: list of yaml file paths which together define the coverpoints
    :param xlen: XLEN of the DUT/Configuration
    :param flen: FLEN of the DUT/Configuration

    :type cgf: list
    :type xlen: int
    :type flen: int
    '''
    cgf = utils.load_cgf(cgf_files)
    for labels, cats in cgf.items():
        if labels != 'datasets':
            # If 'opcode' found, rename it to 'mnemonics'
            if 'opcode' in cats:
                logger.warning("Deprecated node used: 'opcode'. Use 'mnemonics' instead")

                temp = cgf[labels]['opcode']
                del cgf[labels]['opcode']
                cgf[labels].insert(1, 'mnemonics', temp)

                if 'base_op' in cats:
                    if 'p_op_cond' not in cats:
                        logger.error(f'p_op_cond node not found in {labels} label.')

                    if len(cgf[labels]['mnemonics'].keys()) > 1:
                        logger.error(f'Multiple instruction mnemonics found when base_op label defined in {labels} label.')

            # Substitute instruction aliases with equivalent tuple of instructions
            if 'cross_comb' in cats:
                temp = cats['cross_comb']

                for covp, covge in dict(temp).items():
                    data = covp.split('::')
                    ops = data[0].replace(' ', '')[1:-1].split(':')
                    # Substitute with tuple of instructions
                    for i in range(len(ops)):
                        exp_alias = utils.import_instr_alias(ops[i])
                        if exp_alias != None:
                            ops[i] = tuple(exp_alias).__str__().replace("'", '').replace(" ", '')

                    data[0] = '[' + ':'.join(ops) + ']'
                    data = '::'.join(data)
                    del temp[covp]
                    temp[data] = covge

                cgf[labels].insert(1, 'cross_comb', temp)

            l = len(cats.items())
            i = 0
            for label,node in cats.items():
                if isinstance(node,dict):
                    if 'abstract_comb' in node:
                        temp = node['abstract_comb']
                        del node['abstract_comb']
                        for coverpoints, coverage in temp.items():
                            i = 0
                            try:
                                exp_cp = eval(coverpoints)
                            except Exception as e:
                                logger.error("Error evaluating abstract comb: "+(coverpoints)\
                                        +" in "+labels+": "+str(e) )
                            else:
                                for cp,comment in exp_cp:
                                    if log_redundant and cp in cgf[labels][label]:
                                        logger.warn(f'Redundant coverpoint during normalization: {cp}')

                                    # PyYAML has catastrophic performance adding comments
                                    # so only do it for the first 100 entries.
                                    if i < 100:
                                        cgf[labels][label].yaml_add_eol_comment(comment, key=cp)
                                    else:
                                        cgf[labels][label][cp] = coverage

                                    i += 1
    return dict(cgf)
