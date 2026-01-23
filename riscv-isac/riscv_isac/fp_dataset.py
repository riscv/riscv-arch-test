from riscv_isac.log import logger
import itertools
import struct
import random
import sys
import math
from ordered_set import OrderedSet
from decimal import *

# Prasanna
hzero       = ['0x0000', '0x8000']
hminsubnorm = ['0x0001', '0x8001']
hsubnorm    = ['0x0002', '0x8002', '0x03FE', '0x83FE', '0x02AA', '0x82AA']
hmaxsubnorm = ['0x03FF', '0x83FF']
hminnorm    = ['0x0400', '0x8400']
hnorm       = ['0x0401', '0x8401', '0x0455', '0x8455', '0x04AA', '0x84AA', '0x5400', '0xD400', '0x2800', '0xA800']
hmaxnorm    = ['0x7BFF', '0xFBFF']
hinfinity   = ['0x7C00', '0xFC00']
hdefaultnan = ['0x7E00', '0xFE00']
hqnan       = ['0x7E01', '0xFE01', '0x7E55', '0xFE55']
hsnan       = ['0x7C01', '0xFC01', '0x7D55', '0xFD55']
hone        = ['0x3C00', '0xBC00']

fzero       = ['0x00000000', '0x80000000']
fminsubnorm = ['0x00000001', '0x80000001']
fsubnorm    = ['0x00000002', '0x80000002', '0x007FFFFE', '0x807FFFFE', '0x00555555', '0x80555555']
fmaxsubnorm = ['0x007FFFFF', '0x807FFFFF']
fminnorm    = ['0x00800000', '0x80800000']
fnorm       = ['0x00800001', '0x80800001', '0x00855555', '0x80855555', '0x008AAAAA', '0x808AAAAA', '0x55000000', '0xD5000000', '0x2A000000', '0xAA000000']
fmaxnorm    = ['0x7F7FFFFF', '0xFF7FFFFF']
finfinity   = ['0x7F800000', '0xFF800000']
fdefaultnan = ['0x7FC00000', '0xFFC00000']
fqnan       = ['0x7FC00001', '0xFFC00001', '0x7FC55555', '0xFFC55555']
fsnan       = ['0x7F800001', '0xFF800001', '0x7FAAAAAA', '0xFFAAAAAA']
fone        = ['0x3F800000', '0xBF800000']

dzero       = ['0x0000000000000000', '0x8000000000000000']
dminsubnorm = ['0x0000000000000001', '0x8000000000000001']
dsubnorm    = ['0x0000000000000002', '0x8000000000000002','0x0008000000000000', '0x0008000000000002', '0x0001000000000000', '0x8001000000000000','0x8001000000000003','0x8001000000000007']
dmaxsubnorm = ['0x000FFFFFFFFFFFFF', '0x800FFFFFFFFFFFFF']
dminnorm    = ['0x0010000000000000', '0x8010000000000000']
dnorm       = ['0x0010000000000002', '0x8010000000000002', '0x0011000000000000', '0x8011000000000000', '0x0018000000000000', '0x8018000000000000','0x8018000000000005','0x8018000000000007']
dmaxnorm    = ['0x7FEFFFFFFFFFFFFF', '0xFFEFFFFFFFFFFFFF']
dinfinity   = ['0x7FF0000000000000', '0xFFF0000000000000']
ddefaultnan = ['0x7FF8000000000000', '0xFFF8000000000000']
dqnan       = ['0x7FF8000000000001', '0xFFF8000000000001', '0x7FFC000000000001', '0xFFFC000000000001']
dsnan       = ['0x7FF0000000000001', '0xFFF0000000000001', '0x7FF4AAAAAAAAAAAA', '0xFFF4AAAAAAAAAAAA']
done        = ['0x3FF0000000000000', '0xBF80000000000000']

rounding_modes = ['0','1','2','3','4']

sanitise_cvpt = lambda rm,x,iflen,flen,c,inxFlg: x + ' fcsr == '+hex(rm<<5) + ' and rm_val == 7 ' \
                + ('' if iflen >= flen or inxFlg else ''.join([' and rs'+str(x)+'_nan_prefix == 0x' \
                + 'f'*int((flen-iflen)/4) for x in range(1,c+1)]))

sanitise_norm = lambda rm,x,iflen,flen,c,inxFlg: x + ' fcsr == 0'\
                + ('' if iflen >= flen or inxFlg else ''.join([' and rs'+str(x)+'_nan_prefix == 0x' \
                + 'f'*int((flen-iflen)/4) for x in range(1,c+1)]))

sanitise_norm_nopref = lambda rm,x,iflen,flen,c,inxFlg: x + ' fcsr == 0'
sanitise_nopref = lambda rm,x,iflen,flen,c,inxFlg: x + ' fcsr == 0 and rm_val == 7'

get_sanitise_func = lambda opcode: sanitise_norm if any(x in opcode for x in [
        'fsgnj','fle','flt','feq','fclass','flw','fsw','fld','fsd','fmin','fmax']) else \
    (sanitise_norm_nopref if any(x in opcode for x in ['fmv', 'fcvt.d.w', 'fcvt.d.wu','fcvt.d.s']) else \
    (sanitise_nopref if any(opcode.endswith(x) for x in ['.l', '.w', '.lu', '.wu']) else \
    sanitise_cvpt))

def num_explain(flen,num):
    num_dict = {
        tuple(hzero) 		: 'hzero',
        tuple(hminsubnorm) 	: 'hminsubnorm',
        tuple(hsubnorm) 	: 'hsubnorm',
        tuple(hmaxsubnorm) 	: 'hmaxsubnorm',
        tuple(hminnorm) 	: 'hminnorm',
        tuple(hnorm) 		: 'hnorm',
        tuple(hmaxnorm) 	: 'hmaxnorm',
        tuple(hinfinity) 	: 'hinfinity',
        tuple(hdefaultnan) 	: 'hdefaultnan',
        tuple(hqnan) 		: 'hqnan',
        tuple(hsnan) 		: 'hsnan',
        tuple(hone) 		: 'hone',
        tuple(fzero)         : 'fzero',
        tuple(fminsubnorm)     : 'fminsubnorm',
        tuple(fsubnorm)     : 'fsubnorm',
        tuple(fmaxsubnorm)     : 'fmaxsubnorm',
        tuple(fminnorm)     : 'fminnorm',
        tuple(fnorm)         : 'fnorm',
        tuple(fmaxnorm)     : 'fmaxnorm',
        tuple(finfinity)     : 'finfinity',
        tuple(fdefaultnan)     : 'fdefaultnan',
        tuple(fqnan)         : 'fqnan',
        tuple(fsnan)         : 'fsnan',
        tuple(fone)         : 'fone',
        tuple(dzero)         : 'dzero',
        tuple(dminsubnorm)     : 'dminsubnorm',
        tuple(dsubnorm)     : 'dsubnorm',
        tuple(dmaxsubnorm)     : 'dmaxsubnorm',
        tuple(dminnorm)     : 'dminnorm',
        tuple(dnorm)         : 'dnorm',
        tuple(dmaxnorm)     : 'dmaxnorm',
        tuple(dinfinity)     : 'dinfinity',
        tuple(ddefaultnan)     : 'ddefaultnan',
        tuple(dqnan)         : 'dqnan',
        tuple(dsnan)         : 'dsnan',
        tuple(done)         : 'done'
    }
    num_list = list(num_dict.items())
    for i in range(len(num_list)):
        if(('0x'+num[2:].upper()) in num_list[i][0]):
            return(num_list[i][1])

    if flen == 16:
        e_sz = 5	# exponent size
        m_sz = 10	# mantissa size
    elif flen == 32:
        e_sz = 8
        m_sz = 23
    else:
        e_sz = 11
        m_sz = 52
    bin_val = bin(int('1'+num[2:],16))[3:]
    sgn = bin_val[0]
    exp = bin_val[1:e_sz+1]
    man = bin_val[e_sz+1:]

    if(int(exp,2)!=0):
        return('hnorm' if flen == 16 else 'fnorm' if flen==32 else 'dnorm')
    else:
        return('hsubnorm' if flen == 16 else 'fsubnorm' if flen==32 else 'dsubnorm')
       

def extract_fields(flen, hexstr, postfix):
    if flen == 16:
        e_sz = 5	# exponent size
        m_sz = 10	# mantissa size
    elif flen == 32:
        e_sz = 8
        m_sz = 23
    else:
        e_sz = 11
        m_sz = 52
    bin_val = bin(int('1'+hexstr[2:],16))[3:]
    sgn = bin_val[0]
    exp = bin_val[1:e_sz+1]
    man = bin_val[e_sz+1:]
    if flen == 16:
        string = 'fs'+postfix+' == '+str(sgn) +\
		 ' and fe'+postfix+' == '+'0x'+str(hex(int('1000'+exp,2))[3:]) +\
		 ' and fm'+postfix+' == '+'0x'+str(hex(int('100'+man,2))[3:])    #Adds buffer bits to convert to hex
    elif flen == 32:
        string = 'fs'+postfix+' == '+str(sgn) +\
                 ' and fe'+postfix+' == '+'0x'+str(hex(int('1'+exp,2))[3:]) +\
                 ' and fm'+postfix+' == '+'0x'+str(hex(int('10'+man,2))[3:])
    elif flen == 64:
        string = 'fs'+postfix+' == '+str(sgn) +\
                 ' and fe'+postfix+' == '+'0x'+str(hex(int('10'+exp,2))[3:]) +\
                 ' and fm'+postfix+' == '+'0x'+str(hex(int('1'+man,2))[3:])

    return string

def fields_dec_converter(flen, hexstr):                            # IEEE-754 Hex -> Decimal Converter
    if flen == 16:
        e_sz = 5	# exponent size
        m_sz = 10
    elif flen == 32:
        e_sz = 8
        m_sz = 23
    elif flen == 64:
        e_sz = 11
        m_sz = 52
    bin_val = bin(int('1'+hexstr[2:],16))[3:]
    sgn = bin_val[0]
    exp = bin_val[1:e_sz+1]
    man = bin_val[e_sz+1:]

    num=''
    if(int(sgn)==1):
        sign = '-'
    elif(int(sgn)==0):
        sign = '+'

    exp_str = '*pow(2,'

    if(flen == 16):
        if((int(exp,2)-15)<-14):
            conv_num = 0.0
            exp_str+= str(-14)+')'
        elif((int(exp,2)-15)>=-14):
           conv_num = 1.0
           exp_str+= str(int(exp,2)-15)+')'
    elif(flen == 32):
        if((int(exp,2)-127)<-126):
            conv_num = 0.0
            exp_str+= str(-126)+')'
        elif((int(exp,2)-127)>=-126):
            conv_num = 1.0
            exp_str+= str(int(exp,2)-127)+')'
    elif(flen == 64):
        if((int(exp,2)-1023)<-1022):
            conv_num = 0.0
            exp_str+= str(-1022)+')'
        elif((int(exp,2)-1023)>=-1022):
            conv_num = 1.0
            exp_str+= str(int(exp,2)-1023)+')'
    for i in range(len(man)):
        conv_num+= (1/(pow(2,i+1)))*int(man[i])

    num = sign + str(conv_num) + exp_str
    if(flen == 16):
        if(eval(num) > 6e-8 or eval(num) < -6e-8):
            return eval(num)
        else:
            return eval(sign+'6e-8')
    elif(flen == 32):
        if(eval(num) > 1e-45 or eval(num)<-1e-45):
            return(eval(num))
        else:
            return(eval(sign+'1e-45'))
    elif(flen == 64):
        return(eval(num))

def floatingPoint_tohex(flen,float_no):   
                        # Decimal -> IEEE-754 Hex Converter

    if (flen==16):
        if(str(float_no)=='-inf'):
            return(hinfinity[1])
        elif(str(float_no)=='inf'):
            return(hinfinity[0])
    elif(flen==32):
        if(str(float_no)=='-inf'):
            return(finfinity[1])
        elif(str(float_no)=='inf'):
            return(finfinity[0])
    elif(flen==64):
        if(str(float_no)=='-inf'):
            return(dinfinity[1])
        elif(str(float_no)=='inf'):
            return(dinfinity[0])

    float_no=float.hex(float_no)
    num="N"

    a=float.fromhex(float_no)

    sign=0
    if(a<0 or str(a)[0]=='-'):
        sign=1
    nor=float.hex(a)                                    # Normalized Number

    if(flen==16):
        if(int(nor.split("p")[1])<-14):						# Checking Underflow of Exponent
            exp_bin=('0'*5)							# Exponent of Subnormal numbers
            exp_sn=int(nor.split("p")[1])
            num="SN"
        elif(int(nor.split("p")[1])>15):						# Checking Overflow of Exponent
            if(sign==0):
                return "0x7BFF"						# Most Positive Value
            else:
                return "0xFBFF"						# Most Negative Value
        else:										# Converting Exponent to 8-Bit Binary
            exp=int(nor.split("p")[1])+15
            exp_bin=('0'*(5-(len(bin(exp))-2)))+bin(exp)[2:]
    elif(flen==32):
        if(int(nor.split("p")[1])<-126):                        # Checking Underflow of Exponent
            exp_bin=('0'*8)                            # Exponent of Subnormal numbers
            exp_sn=int(nor.split("p")[1])
            num="SN"
        elif(int(nor.split("p")[1])>127):                        # Checking Overflow of Exponent
            if(sign==0):
                return "0x7f7fffff"                        # Most Positive Value
            else:
                return "0xff7fffff"                        # Most Negative Value
        else:                                        # Converting Exponent to 8-Bit Binary
            exp=int(nor.split("p")[1])+127
            exp_bin=('0'*(8-(len(bin(exp))-2)))+bin(exp)[2:]
    elif(flen==64):
        check_sn = nor.split("p")[0].split(".")[0]
        if(int(check_sn[len(check_sn)-1])==0):                    # Checking Underflow of Exponent
            exp_bin=('0'*11)                            # Exponent of Subnormal numbers
            exp_sn=int(nor.split("p")[1])
            num="SN"
        elif(int(nor.split("p")[1])>1023):                        # Checking Overflow of Exponent
            if(sign==0):
                return "0x7FEFFFFFFFFFFFFF"                    # Most Positive Value
            else:
                return "0xFFEFFFFFFFFFFFFF"                    # Most Negative Value
        else:                                        # Converting Exponent to 8-Bit Binary
            exp=int(nor.split("p")[1])+1023
            exp_bin=('0'*(11-(len(bin(exp))-2)))+bin(exp)[2:]

    if(num=="SN"):
        if(sign==0):
            mant="0x"+float_no.split("p")[0][4:]
        else:
            mant="0x"+float_no.split("p")[0][5:]
    else:
        if(sign==0):
            mant="0x"+nor.split("p")[0][4:]
        else:
            mant="0x"+nor.split("p")[0][5:]

    if(flen==16):
        mant_bin=bin(int('1'+mant[2:],16))[3:]
        if(num == "SN"):
            mant_bin='1'+bin(int('1'+mant[2:],16))[3:]
            while(exp_sn!=-15):
                exp_sn+=1
                mant_bin = '0'+mant_bin
        binary="0b"
        binary=binary+str(sign)+exp_bin+mant_bin[0:10]
        hex_tp=hex(int(binary,2))
        hex_tp=hex_tp.replace('0x','0x'+'0'*(4-(len(hex_tp)-2)))

    elif(flen==32):
        mant_bin=bin(int('1'+mant[2:],16))[3:]
        if(num == "SN"):
            mant_bin='1'+bin(int('1'+mant[2:],16))[3:]
            while(exp_sn!=-127):
                exp_sn+=1
                mant_bin = '0'+mant_bin
        binary="0b"
        binary=binary+str(sign)+exp_bin+mant_bin[0:23]
        hex_tp=hex(int(binary,2))
        hex_tp=hex_tp.replace('0x','0x'+'0'*(8-(len(hex_tp)-2)))
    elif(flen==64):
        mant_bin=bin(int('1'+mant[2:],16))[3:]
        if(num == "SN"):
            mant_bin=bin(int('1'+mant[2:],16))[3:]
        binary="0b"
        binary=binary+str(sign)+exp_bin+mant_bin[0:52]
        hex_tp=hex(int(binary,2))
        hex_tp=hex_tp.replace('0x','0x'+'0'*(16-(len(hex_tp)-2)))

    return(hex_tp)

def unique_cpts(x):
    d = {}
    for i in range(len(x)):                            # Returning a List Of Unique Coverpoints
        if(d.get(x[i],"None") == "None"):
            d[x[i]] = 1
        else:
            d[x[i]]+=1
    return(list(d.keys()))

def comments_parser(coverpoints):
    cvpts = []
    for coverpoint in coverpoints:
        cvpt = coverpoint.split("#")[0]
        comment = coverpoint.split("#")[1]
        cvpts.append((cvpt+ " #nosat",comment))
    return cvpts

def sgn_prefix(iflen,flen,inxFlag,c,cvpt):
    sp=''
    if(flen >iflen  and inxFlag):
        for x in range(1,c+1):
            if 'fs'+str(x)+' == 1' in cvpt:
                sp += ' and rs'+str(x)+'_sgn_prefix == 0x'+'f'*int((flen-iflen)/4)
            else:
                sp += ' and rs'+str(x)+'_sgn_prefix == 0x'+'0'*int((flen-iflen)/4)
    return sp

def ibm_b1(flen, iflen, opcode, ops, inxFlg=False):
    '''
    IBM Model B1 Definition:
        Test all combinations of floating-point basic types, positive and negative, for
        each of the inputs. The basic types are Zero, One, MinSubNorm, SubNorm,
        MaxSubNorm, MinNorm, Norm, MaxNorm, Infinity, DefaultNaN, QNaN, and
        SNaN.

    :param iflen: Size of the floating point source operands for the instruction
    :param flen: Size of the floating point registers
    :param opcode: Opcode for which the coverpoints are to be generated
    :param ops: No. of Operands taken by the opcode

    :type iflen: int
    :type flen: int
    :type opcode: str
    :type ops: int

    Abstract Dataset Description:
        Operands =>
        [Zero, One, MinSubNorm, SubNorm, MaxSubNorm, MinNorm, Norm, MaxNorm, Infinity, DefaultNaN, QNaN, SNaN]

    Implementation:
        - Dependent on the value of iflen, a predefined dataset of floating point values are added.
        - Using the itertools package, an iterative multiplication is performed with two lists to create an exhaustive combination of all the operand values.
        - The operand values are then passed into the extract_fields function to get individual fields in a floating point number (sign, exponent and mantissa).
        - Coverpoints are then appended with the respective rounding mode for that particular opcode.

    '''
    sanitise = get_sanitise_func(opcode)
    if iflen == 16:
        basic_types = hzero + hminsubnorm + [hsubnorm[0], hsubnorm[3]] +\
            hmaxsubnorm + hminnorm + [hnorm[0], hnorm[3]] + hmaxnorm + \
            hinfinity + hdefaultnan + [hqnan[0], hqnan[3]] + \
            [hsnan[0], hsnan[3]] + hone

    elif iflen == 32:
        basic_types = fzero + fminsubnorm + [fsubnorm[0], fsubnorm[3]] +\
            fmaxsubnorm + fminnorm + [fnorm[0], fnorm[3]] + fmaxnorm + \
            finfinity + fdefaultnan + [fqnan[0], fqnan[3]] + \
            [fsnan[0], fsnan[3]] + fone
    elif iflen == 64:
        basic_types = dzero + dminsubnorm + [dsubnorm[0], dsubnorm[1]] +\
            dmaxsubnorm + dminnorm + [dnorm[0], dnorm[1]] + dmaxnorm + \
            dinfinity + ddefaultnan + [dqnan[0], dqnan[1]] + \
            [dsnan[0], dsnan[1]] + done
    else:
        logger.error('Invalid iflen value!')
        sys.exit(1)

    # the following creates a cross product for ops number of variables
    b1_comb = list(itertools.product(*ops*[basic_types]))
    coverpoints = []
    for c in b1_comb:
        cvpt = ""
        for x in range(1, ops+1):
#            cvpt += 'rs'+str(x)+'_val=='+str(c[x-1]) # uncomment this if you want rs1_val instead of individual fields
            cvpt += (extract_fields(iflen,c[x-1],str(x))) + " and "
        if opcode.split('.')[0] in ["fadd","fsub","fmul","fdiv","fsqrt","fmadd","fnmadd","fmsub","fnmsub","fcvt","fmv"]:
            cvpt = sanitise(0,cvpt,iflen,flen,ops,inxFlg)
        elif opcode.split('.')[0] in \
        ["fclass","flt","fmax","fsgnjn","fmin","fsgnj","feq","flw","fsw","fsgnjx","fld","fle"]:
            cvpt = sanitise(0,cvpt,iflen,flen,ops,inxFlg)
        cvpt += sgn_prefix(iflen,flen,inxFlg,ops,cvpt)
        cvpt += ' # '
        for y in range(1, ops+1):
            cvpt += 'rs'+str(y)+'_val=='
            cvpt += num_explain(iflen, c[y-1]) + '(' + str(c[y-1]) + ')'
            if(y != ops):
                cvpt += " and "
        coverpoints.append(cvpt)
        

    mess='Generated'+ (' '*(5-len(str(len(coverpoints)))))+ str(len(coverpoints)) +' '+ \
    (str(16) if iflen == 16 else str(32) if iflen == 32 else str(64)) + '-bit coverpoints using Model B1 for '+opcode+' !'
    logger.debug(mess)
    coverpoints = comments_parser(coverpoints)

    return coverpoints

def ibm_b2(flen, iflen, opcode, ops, inxFlg=False, int_val = 100, seed = -1):
    '''
    IBM Model B2 Definition:
            This model tests final results that are very close, measured in Hamming
            distance, to the specified boundary values. Each boundary value is taken as a
            base value, and the model enumerates over small deviations from the base, by
            flipping one bit of the significand.


    :param iflen: Size of the floating point source operands
    :param flen: Size of the floating point registers
    :param opcode: Opcode for which the coverpoints are to be generated
    :param ops: No. of Operands taken by the opcode
    :param int_val: Number to define the range in which the random value is to be generated.  (Predefined to 100)
    :param seed: Initial seed value of the random library. (Predefined to -1. Actual value is set with respect to the opcode calling the function)

    :type iflen: int
    :type flen: int
    :type opcode: str
    :type ops: int
    :type int_val: int
    :param seed: int

    Abstract Dataset Description:
            Final Results = [Zero, One, MinSubNorm, MaxSubNorm, MinNorm, MaxNorm]
            Operand1 {operation} Operand2 = Final Results

    Implementation:
            - Hamming distance is calculated using an xor operation between a number in the dataset and a number generated using walking ones operation.
            - A random operand value for one of the operands is assigned and based on the result and operation under consideration, the next operand is calculated.
            - These operand values are treated as decimal numbers until their derivation after which they are converted into their respective IEEE754 hexadecimal floating point formats using the “floatingPoint_tohex” function.
            - The operand values are then passed into the extract_fields function to get individual fields in a floating point number (sign, exponent and mantissa).
            - Coverpoints are then appended with the respective rounding mode for that particular opcode.

    '''
    sanitise = get_sanitise_func(opcode)
    if iflen == 16:
        flip_types = hzero + hone + hminsubnorm + hmaxsubnorm + hminnorm + hmaxnorm
        b = '0x0010'
        e_sz= 5
        m_sz = 10
    elif iflen == 32:
        flip_types = fzero + fone + fminsubnorm + fmaxsubnorm + fminnorm + fmaxnorm
        b = '0x00000010'
        e_sz=8
        m_sz = 23
    elif iflen == 64:
        flip_types = dzero + done + dminsubnorm + dmaxsubnorm + dminnorm + dmaxnorm
        b = '0x0000000000000010'
        e_sz=11
        m_sz = 52

    result = []
    b2_comb = []
    opcode = opcode.split('.')[0]

    if seed == -1:
        if opcode in 'fadd':
            random.seed(0)
        elif opcode in 'fsub':
            random.seed(1)
        elif opcode in 'fmul':
            random.seed(2)
        elif opcode in 'fdiv':
            random.seed(3)
        elif opcode in 'fsqrt':
            random.seed(4)
        elif opcode in 'fmadd':
            random.seed(5)
        elif opcode in 'fnmadd':
            random.seed(6)
        elif opcode in 'fmsub':
            random.seed(7)
        elif opcode in 'fnmsub':
            random.seed(8)
    else:
        random.seed(seed)

    for i in range(len(flip_types)):
        k=1
        if iflen == 16:
            for j in range(1, 11):
                result.append(['0x'+hex(eval(bin(int('1'+flip_types[i][2:], 16))) ^ eval('0b'+'{:015b}'.format(k)))[3:],' | Result = '+num_explain(iflen, '0x'+str(hex(eval(bin(int('1'+flip_types[i][2:], 16))))[3:]))+'(0x'+str(hex(eval(bin(int('1'+flip_types[i][2:], 16))))[3:])+')^'+str('0x'+hex(eval('0b'+'1'+'{:024b}'.format(k)))[3:])])
                k=k*2
        else:
            for j in range (1,24):
                #print('{:010b}'.format(k))
                result.append(['0x'+hex(eval(bin(int('1'+flip_types[i][2:], 16))) ^ eval('0b'+'{:023b}'.format(k)))[3:],' | Result = '+num_explain(iflen, '0x'+str(hex(eval(bin(int('1'+flip_types[i][2:], 16))))[3:]))+'(0x'+str(hex(eval(bin(int('1'+flip_types[i][2:], 16))))[3:])+')^'+str('0x'+hex(eval('0b'+'1'+'{:024b}'.format(k)))[3:])])
                k=k*2

    for i in range(len(result)):
        bin_val = bin(int('1'+result[i][0][2:],16))[3:]
        rsgn = bin_val[0]
        rexp = bin_val[1:e_sz+1]
        rman = bin_val[e_sz+1:]
        rs1_exp = rs3_exp = rexp
        rs1_bin = bin(random.randrange(1,int_val))
        rs3_bin = bin(random.randrange(1,int_val))
        rs1_bin = ('0b0'+rexp+('0'*(m_sz-(len(rs1_bin)-2)))+rs1_bin[2:])
        rs3_bin = ('0b0'+rexp+('0'*(m_sz-(len(rs3_bin)-2)))+rs3_bin[2:])
        rs1 = fields_dec_converter(iflen,'0x'+hex(int('1'+rs1_bin[2:],2))[3:])
        rs3 = fields_dec_converter(iflen,'0x'+hex(int('1'+rs3_bin[2:],2))[3:])
        if opcode in 'fadd':
            rs2 = fields_dec_converter(iflen,result[i][0]) - rs1
        elif opcode in 'fsub':
            rs2 = rs1 - fields_dec_converter(iflen,result[i][0])
        elif opcode in 'fmul':
            rs2 = fields_dec_converter(iflen,result[i][0])/rs1
        elif opcode in 'fdiv':
            if fields_dec_converter(iflen,result[i][0]) != 0:
                rs2 = rs1/fields_dec_converter(iflen,result[i][0])
        elif opcode in 'fsqrt':
            rs2 = fields_dec_converter(iflen,result[i][0])*fields_dec_converter(iflen,result[i][0])
        elif opcode in 'fmadd':
            rs2 = (fields_dec_converter(iflen,result[i][0]) - rs3)/rs1
        elif opcode in 'fnmadd':
            rs2 = (rs3 - fields_dec_converter(iflen,result[i][0]))/rs1
        elif opcode in 'fmsub':
            rs2 = (fields_dec_converter(iflen,result[i][0]) + rs3)/rs1
        elif opcode in 'fnmsub':
            rs2 = -1*(rs3 + fields_dec_converter(iflen,result[i][0]))/rs1

        if(iflen==16):		# Checks for inf values
            m = float('inf') if rs2 > fields_dec_converter(16, hmaxnorm[0]) \
			else float('-inf') if rs2 < fields_dec_converter(16, hmaxnorm[1]) \
			else rs2
        elif(iflen==32):
            m = struct.unpack('f', struct.pack('f', rs2))[0]
        elif(iflen==64):
            m = rs2

        if opcode in ['fadd','fsub','fmul','fdiv']:
            b2_comb.append((floatingPoint_tohex(iflen,rs1),floatingPoint_tohex(iflen,m)))
        elif opcode in 'fsqrt':
            b2_comb.append((floatingPoint_tohex(iflen,m),))
        elif opcode in ['fmadd','fnmadd','fmsub','fnmsub']:
            b2_comb.append((floatingPoint_tohex(iflen,rs1),floatingPoint_tohex(iflen,m),floatingPoint_tohex(iflen,rs3)))
    
    coverpoints = []
    k=0
    for c in b2_comb:
        cvpt = ""
        for x in range(1, ops+1):
#            cvpt += 'rs'+str(x)+'_val=='+str(c[x-1]) # uncomment this if you want rs1_val instead of individual fields
            cvpt += (extract_fields(iflen,c[x-1],str(x)))
            cvpt += " and "
        cvpt = sanitise(0,cvpt,iflen,flen,ops,inxFlg)
        if inxFlg == True:
            cvpt += sgn_prefix(iflen,flen,inxFlg,ops,cvpt)
        else:
            cvpt += ' # '
        cvpt += ' # '
        for y in range(1, ops+1):
            cvpt += 'rs'+str(y)+'_val=='
            cvpt += num_explain(iflen, c[y-1]) + '(' + str(c[y-1]) + ')'
            if(y != ops):
                cvpt += " and "
        cvpt += result[k][1]
        coverpoints.append(cvpt)
        k=k+1

    mess='Generated'+ (' '*(5-len(str(len(coverpoints)))))+ str(len(coverpoints)) +' '+ \
    (str(16) if iflen == 16 else str(32) if iflen == 32 else str(64)) + '-bit coverpoints using Model B2 for '+opcode+' !'
    logger.debug(mess)
    coverpoints = comments_parser(coverpoints)

    return coverpoints

def ibm_b3(flen,iflen, opcode, ops, inxFlg=False, seed=-1):
    '''
    IBM Model B3 Definition:
            This model tests all combinations of the sign, significand’s LSB, guard bit & sticky bit of the intermediate result.

    :param iflen: Size of the floating source operands for the operation
    :param flen: Size of the floating point registers
    :param opcode: Opcode for which the coverpoints are to be generated
    :param ops: No. of Operands taken by the opcode
    :param seed: Initial seed value of the random library. (Predefined to -1. Actual value is set with respect to the opcode calling the function)

    :type iflen: int
    :type flen: int
    :type opcode: str
    :type ops: int
    :param seed: int

    Abstract Dataset Description:
            Intermediate Result is chosen at random
            Intermediate Result = [All possible combinations of Sign, LSB, Guard and Sticky are taken]
            Operand1 {operation} Operand2 = Intermediate Results

    Implementation:
            - The Sticky bit is 1 if there were non-zero digits to the right of the guard digit, hence the lsb list is subjected to that condition.
            - Float_val [ a list of numbers ] extracted from the fields_dec_converter is checked for the LSB. If it is a negative number, then the list ieee754_num is appended with splitting the p character and first 10 characters in the 0th split + ‘p’ + other part of the split. “p” specifies the maximum available number in python and used in 64 bit architecture. If we require a digit more than thea number, then we represent it using a string because an int
            - Now the ir_dataset is initialized and since the ieee754_num list has the same element twice [ first is just the number and second is with sign ], hence we loop that array, considering only multiples of 2 elements from it. If the sign is ‘-’, then then the index is updated with 1 else if it is ‘+’, then it is updated with 0 complying with the IEEE standards.
            - The operand values are then passed into the extract_fields function to get individual fields in a floating point number (sign, exponent and mantissa).
            - Coverpoints are then appended with all rounding modes for that particular opcode.

    '''
    sanitise = get_sanitise_func(opcode)
    opcode = opcode.split('.')[0]
    getcontext().prec = 40

    if seed == -1:
        if opcode in 'fadd':
            random.seed(0)
        elif opcode in 'fsub':
            random.seed(1)
        elif opcode in 'fmul':
            random.seed(2)
        elif opcode in 'fdiv':
            random.seed(3)
        elif opcode in 'fsqrt':
            random.seed(4)
        elif opcode in 'fmadd':
            random.seed(5)
        elif opcode in 'fnmadd':
            random.seed(6)
        elif opcode in 'fmsub':
            random.seed(7)
        elif opcode in 'fnmsub':
            random.seed(8)
    else:
        random.seed(seed)

    if iflen == 16:
        ieee754_maxnorm = float.hex(fields_dec_converter(16, hmaxnorm[0]))
        maxnum = float.fromhex(ieee754_maxnorm)
        ieee754_num = []
        lsb = []
        for i in hsubnorm+hnorm:
            if int(i[-1],16)%2 == 1:
                lsb.append('1')
                lsb.append('1')
            else:
                lsb.append('0')
                lsb.append('0')
            float_val = float.hex(fields_dec_converter(16,i))
            if float_val[0] != '-':
                ieee754_num.append(float_val)
                ieee754_num.append('-'+float_val)
            else:
                ieee754_num.append(float_val)
                ieee754_num.append(float_val[1:])
        ir_dataset = []
        for k in range(len(ieee754_num)):
            for i in range(2,16,2):
                grs = '{:04b}'.format(i)
                if ieee754_num[k][0] == '-': sign = '1'
                else: sign = '0'
                ir_dataset.append([ieee754_num[k].split('p')[0]+str(i)+'p'+ieee754_num[k].split('p')[1],' | Guard = '+grs[0]+' Sticky = '+grs[2]+' Sign = '+sign+' LSB = '+lsb[k]])
        for i in range(len(ir_dataset)):
            ir_dataset[i][0] = float.fromhex(ir_dataset[i][0])
    elif iflen == 32:
        ieee754_maxnorm = '0x1.7fffffp+127'
        maxnum = float.fromhex(ieee754_maxnorm)
        ieee754_num = []
        lsb = []
        for i in fsubnorm+fnorm:
            if int(i[-1],16)%2 == 1:
                lsb.append('1')
                lsb.append('1')
            else:
                lsb.append('0')
                lsb.append('0')
            float_val = float.hex(fields_dec_converter(32,i))
            if float_val[0] != '-':
                ieee754_num.append(float_val.split('p')[0][0:10]+'p'+float_val.split('p')[1])
                ieee754_num.append('-'+float_val.split('p')[0][0:10]+'p'+float_val.split('p')[1])
            else:
                ieee754_num.append(float_val.split('p')[0][0:11]+'p'+float_val.split('p')[1])
                ieee754_num.append(float_val.split('p')[0][1:11]+'p'+float_val.split('p')[1])

        ir_dataset = []
        for k in range(len(ieee754_num)):
            for i in range(2,16,2):
                grs = '{:04b}'.format(i)
                if ieee754_num[k][0] == '-': sign = '1'
                else: sign = '0'
                ir_dataset.append([ieee754_num[k].split('p')[0]+str(i)+'p'+ieee754_num[k].split('p')[1],' | Guard = '+grs[0]+' Sticky = '+grs[2]+' Sign = '+sign+' LSB = '+lsb[k]])

        for i in range(len(ir_dataset)):
            ir_dataset[i][0] = float.fromhex(ir_dataset[i][0])

    elif iflen == 64:
        maxdec = '1.7976931348623157e+308'
        maxnum = float.fromhex('0x1.fffffffffffffp+1023')
        ieee754_num = []
        lsb = []
        for i in dsubnorm+dnorm:
            if int(i[-1],16)%2 == 1:
                lsb.append('1')
                lsb.append('1')
            else:
                lsb.append('0')
                lsb.append('0')
            float_val = str(fields_dec_converter(64,i))
            if float_val[0] != '-':
                ieee754_num.append(float_val)
                ieee754_num.append('-'+float_val)
            else:
                ieee754_num.append(float_val)
                ieee754_num.append(float_val[1:])

        ir_dataset = []
        for k in range(len(ieee754_num)):
            for i in range(2,16,2):
                grs = '{:04b}'.format(i)
                if ieee754_num[k][0] == '-': sign = '1'
                else: sign = '0'
                ir_dataset.append([str(Decimal(ieee754_num[k].split('e')[0])+Decimal(pow(i*16,-14)))+'e'+ieee754_num[k].split('e')[1],' | Guard = '+grs[0]+' Sticky = '+grs[2]+' Sign = '+sign+' LSB = '+lsb[k]])

    b3_comb = []

    for i in range(len(ir_dataset)):
        rs1 = random.uniform(1,maxnum)
        rs3 = random.uniform(1,maxnum)
        if opcode in 'fadd':
            if iflen == 32 or iflen == 16:
                rs2 = ir_dataset[i][0] - rs1
            elif iflen == 64:
                rs2 = Decimal(ir_dataset[i][0]) - Decimal(rs1)
        elif opcode in 'fsub':
            if iflen == 32 or iflen == 16:
                rs2 = rs1 - ir_dataset[i][0]
            elif iflen == 64:
                rs2 = Decimal(rs1) - Decimal(ir_dataset[i][0])
        elif opcode in 'fmul':
            if iflen == 32 or iflen == 16:
                rs2 = ir_dataset[i][0]/rs1
            elif iflen == 64:
                rs2 = Decimal(ir_dataset[i][0])/Decimal(rs1)
        elif opcode in 'fdiv':
            if iflen == 32 or iflen == 16:
                rs2 = rs1/ir_dataset[i][0]
            elif iflen == 64:
                rs2 = Decimal(rs1)/Decimal(ir_dataset[i][0])
        elif opcode in 'fsqrt':
            if iflen == 32 or iflen == 16:
                rs2 = ir_dataset[i][0]*ir_dataset[i][0]
            elif iflen == 64:
                rs2 = Decimal(ir_dataset[i][0])*Decimal(ir_dataset[i][0])
        elif opcode in 'fmadd':
            if iflen == 32 or iflen == 16:
                rs2 = (ir_dataset[i][0] - rs3)/rs1
            elif iflen == 64:
                rs2 = (Decimal(ir_dataset[i][0]) - Decimal(rs3))/Decimal(rs1)
        elif opcode in 'fnmadd':
            if iflen == 32 or iflen == 16:
                rs2 = (rs3 - ir_dataset[i][0])/rs1
            elif iflen == 64:
                rs2 = (Decimal(rs3) - Decimal(ir_dataset[i][0]))/Decimal(rs1)
        elif opcode in 'fmsub':
            if iflen == 32 or iflen == 16:
                rs2 = (ir_dataset[i][0] + rs3)/rs1
            elif iflen == 64:
                rs2 = (Decimal(ir_dataset[i][0]) + Decimal(rs3))/Decimal(rs1)
        elif opcode in 'fnmsub':
            if iflen == 32 or iflen == 16:
                rs2 = -1*(rs3 + ir_dataset[i][0])/rs1
            elif iflen == 64:
                rs2 = -1*(Decimal(rs3) + Decimal(ir_dataset[i][0]))/Decimal(rs1)

        if(iflen==16):
            m = lambda rsx: float('inf') if rsx > fields_dec_converter(16, hmaxnorm[0]) \
            else float('-inf') if rsx < fields_dec_converter(16, hmaxnorm[1]) \
            else rsx
            x1 = m(rs1)
            x2 = m(rs2)
            x3 = m(rs3)
        elif(iflen==32):
            x1 = struct.unpack('f', struct.pack('f', rs1))[0]
            x2 = struct.unpack('f', struct.pack('f', rs2))[0]
            x3 = struct.unpack('f', struct.pack('f', rs3))[0]
        elif(iflen==64):
            x1 = rs1
            x2 = rs2
            x3 = rs3

        if opcode in ['fadd','fsub','fmul','fdiv']:
            b3_comb.append((floatingPoint_tohex(iflen,float(rs1)),floatingPoint_tohex(iflen,float(rs2))))
        elif opcode in 'fsqrt':
            b3_comb.append((floatingPoint_tohex(iflen,float(rs2)),))
        elif opcode in ['fmadd','fnmadd','fmsub','fnmsub']:
            b3_comb.append((floatingPoint_tohex(iflen,float(rs1)),floatingPoint_tohex(iflen,float(rs2)),floatingPoint_tohex(iflen,float(rs3))))

    coverpoints = []
    k = 0
    for c in b3_comb:
        for rm in range(5):
            cvpt = ""
            for x in range(1, ops+1):
#                        cvpt += 'rs'+str(x)+'_val=='+str(c[x-1]) # uncomment this if you want rs1_val instead of individual fields
                cvpt += (extract_fields(iflen,c[x-1],str(x)))
                cvpt += " and "
            # cvpt += 'rm_val == '+str(rm)
            cvpt =  sanitise(rm,cvpt,iflen,flen,ops,inxFlg)
            if inxFlg == True:
                cvpt += sgn_prefix(iflen,flen,inxFlg,ops,cvpt)
            else:
                cvpt += ' # '            
            cvpt += ' # '
            for y in range(1, ops+1):
                cvpt += 'rs'+str(y)+'_val=='
                cvpt += num_explain(iflen, c[y-1]) + '(' + str(c[y-1]) + ')'
                if(y != ops):
                    cvpt += " and "
            cvpt += ir_dataset[k][1]
            coverpoints.append(cvpt)
        k=k+1

    mess='Generated'+ (' '*(5-len(str(len(coverpoints)))))+ str(len(coverpoints)) +' '+ \
    (str(16) if iflen == 16 else str(32) if iflen == 32 else str(64)) + '-bit coverpoints using Model B3 for '+opcode+' !'
    logger.debug(mess)
    coverpoints = comments_parser(coverpoints)

    return coverpoints

def ibm_b4(flen, iflen, opcode, ops, inxFlg=False, seed=-1):
    '''
    IBM Model B4 Definition:
            This model creates a test-case for each of the following constraints on the
            intermediate results:

            1. All the numbers in the range [+MaxNorm – 3 ulp, +MaxNorm + 3 ulp]
            2. All the numbers in the range [-MaxNorm - 3 ulp, -MaxNorm + 3 ulp]
            3. A random number that is larger than +MaxNorm + 3 ulp
            4. A random number that is smaller than -MaxNorm – 3 ulp
            5. One number for every exponent in the range [MaxNorm.exp - 3, MaxNorm.exp + 3] for positive and negative numbers

    :param flen: Size of the floating point registers
    :param iflen: Size of the floating point source operands for the operation
    :param opcode: Opcode for which the coverpoints are to be generated
    :param ops: No. of Operands taken by the opcode
    :param seed: Initial seed value of the random library. (Predefined to -1. Actual value is set with respect to the opcode calling the function)

    :type iflen: int
    :type flen: int
    :type opcode: str
    :type ops: int
    :param seed: int

    Abstract Dataset Description:
            Intermediate Results = [[MaxNorm-3 ulp, MaxNorm+3 ulp], [-MaxNorm-3 ulp, -MaxNorm+3 ulp], Random Num > MaxNorm+3 ulp, Random Num < -MaxNorm-3 ulp, [MaxNorm.exp-3, MaxNorm.exp+3]]
            Operand1 {operation} Operand2 = Intermediate Results

    Implementation:
            - The intermediate results dataset is populated in accordance with the abstract dataset defined above.
            - Intermediate results can be out of the range of what is representable in the specified format; they should only be viewed numerically. Inorder to represent numbers that went out of range of the maximum representable number in python, the “Decimal” module was utilized.
            - These operand values are treated as decimal numbers until their derivation after which they are converted into their respective IEEE754 hexadecimal floating point formats using the “floatingPoint_tohex” function.

    '''
    sanitise = get_sanitise_func(opcode)
    opcode = opcode.split('.')[0]
    getcontext().prec = 40

    if seed == -1:
        if opcode in 'fadd':
            random.seed(0)
        elif opcode in 'fsub':
            random.seed(1)
        elif opcode in 'fmul':
            random.seed(2)
        elif opcode in 'fdiv':
            random.seed(3)
        elif opcode in 'fsqrt':
            random.seed(4)
        elif opcode in 'fmadd':
            random.seed(5)
        elif opcode in 'fnmadd':
            random.seed(6)
        elif opcode in 'fmsub':
            random.seed(7)
        elif opcode in 'fnmsub':
            random.seed(8)
    else:
        random.seed(seed)

    if iflen == 16:
        ieee754_maxnorm_p = float.hex(fields_dec_converter(16, hmaxnorm[0]))
        ieee754_maxnorm_n = float.hex(fields_dec_converter(16, hmaxnorm[1]))
        maxnum = float.fromhex(ieee754_maxnorm_p)
        ir_dataset = []
        for i in range(2,16,2):
            grs = '{:04b}'.format(i)
            ir_dataset.append([ieee754_maxnorm_p.split('p')[0]+str(i)+'p'+ieee754_maxnorm_p.split('p')[1],' | Guard = '+grs[0]+' Round = '+grs[1]+' Sticky = '+grs[2]+' --> Maxnorm + '+str(int(grs[0:3],2))+' ulp'])
            ir_dataset.append([ieee754_maxnorm_n.split('p')[0]+str(i)+'p'+ieee754_maxnorm_n.split('p')[1],' | Guard = '+grs[0]+' Round = '+grs[1]+' Sticky = '+grs[2]+' --> Maxnorm - '+str(int(grs[0:3],2))+' ulp'])
        for i in range(-3,4):
            ir_dataset.append([ieee754_maxnorm_p.split('p')[0]+'p'+str(15+i),' | Exponent = '+str(15+i)+' Number = +ve'])
            ir_dataset.append([ieee754_maxnorm_n.split('p')[0]+'p'+str(15+i),' | Exponent = '+str(15+i)+' Number = -ve'])
        for i in range(len(ir_dataset)):
            ir_dataset[i][0] = float.fromhex(ir_dataset[i][0])
    elif iflen == 32:
        ieee754_maxnorm_p = '0x1.7fffffp+127'
        ieee754_maxnorm_n = '0x1.7ffffep+127'
        maxnum = float.fromhex(ieee754_maxnorm_p)
        ir_dataset = []
        for i in range(2,16,2):
            grs = '{:04b}'.format(i)
            ir_dataset.append([ieee754_maxnorm_p.split('p')[0]+str(i)+'p'+ieee754_maxnorm_p.split('p')[1],' | Guard = '+grs[0]+' Round = '+grs[1]+' Sticky = '+grs[2]+' --> Maxnorm + '+str(int(grs[0:3],2))+' ulp'])
            ir_dataset.append([ieee754_maxnorm_n.split('p')[0]+str(i)+'p'+ieee754_maxnorm_n.split('p')[1],' | Guard = '+grs[0]+' Round = '+grs[1]+' Sticky = '+grs[2]+' --> Maxnorm - '+str(int(grs[0:3],2))+' ulp'])
        for i in range(-3,4):
            ir_dataset.append([ieee754_maxnorm_p.split('p')[0]+'p'+str(127+i),' | Exponent = '+str(127+i)+' Number = +ve'])
            ir_dataset.append(['-'+ieee754_maxnorm_n.split('p')[0]+'p'+str(127+i),' | Exponent = '+str(127+i)+' Number = -ve'])
        for i in range(len(ir_dataset)):
            ir_dataset[i][0] = float.fromhex(ir_dataset[i][0])
    elif iflen == 64:
        maxnum = float.fromhex('0x1.fffffffffffffp+1023')
        maxdec_p = str(maxnum)
        maxdec_n = str(float.fromhex('0x1.ffffffffffffep+1023'))
        ir_dataset = []
        for i in range(2,16,2):
            grs = '{:04b}'.format(i)
            ir_dataset.append([str(Decimal(maxdec_p.split('e')[0])+Decimal(pow(i*16,-14)))+'e'+maxdec_p.split('e')[1],' | Guard = '+grs[0]+' Round = '+grs[1]+' Sticky = '+grs[2]+' --> Maxnorm + '+str(int(grs[0:3],2))+' ulp'])
            ir_dataset.append([str(Decimal(maxdec_n.split('e')[0])+Decimal(pow(i*16,-14)))+'e'+maxdec_n.split('e')[1],' | Guard = '+grs[0]+' Round = '+grs[1]+' Sticky = '+grs[2]+' --> Maxnorm - '+str(int(grs[0:3],2))+' ulp'])
        for i in range(-3,4):
            ir_dataset.append([str(random.uniform(1,maxnum)).split('e')[0]+'e'+str(int(math.log(pow(2,1023+i),10))),' | Exponent = '+str(1023+i)+' Number = +ve'])
            ir_dataset.append([str(-1*random.uniform(1,maxnum)).split('e')[0]+'e'+str(int(math.log(pow(2,1023+i),10))),' | Exponent = '+str(1023+i)+' Number = -ve'])

    b4_comb = []

    for i in range(len(ir_dataset)):
        rs1 = random.uniform(1,maxnum)
        rs3 = random.uniform(1,maxnum)
        if opcode in 'fadd':
            if iflen == 32 or iflen == 16:
                rs2 = ir_dataset[i][0] - rs1
            elif iflen == 64:
                rs2 = Decimal(ir_dataset[i][0]) - Decimal(rs1)
        elif opcode in 'fsub':
            if iflen == 32 or iflen == 16:
                rs2 = rs1 - ir_dataset[i][0]
            elif iflen == 64:
                rs2 = Decimal(rs1) - Decimal(ir_dataset[i][0])
        elif opcode in 'fmul':
            if iflen == 32 or iflen == 16:
                rs2 = ir_dataset[i][0]/rs1
            elif iflen == 64:
                rs2 = Decimal(ir_dataset[i][0])/Decimal(rs1)
        elif opcode in 'fdiv':
            if iflen == 32 or iflen == 16:
                rs2 = rs1/ir_dataset[i][0]
            elif iflen == 64:
                rs2 = Decimal(rs1)/Decimal(ir_dataset[i][0])
        elif opcode in 'fsqrt':
            if iflen == 32 or iflen == 16:
                rs2 = ir_dataset[i][0]*ir_dataset[i][0]
            elif iflen == 64:
                rs2 = Decimal(ir_dataset[i][0])*Decimal(ir_dataset[i][0])
        elif opcode in 'fmadd':
            if iflen == 32 or iflen == 16:
                rs2 = (ir_dataset[i][0] - rs3)/rs1
            elif iflen == 64:
                rs2 = (Decimal(ir_dataset[i][0]) - Decimal(rs3))/Decimal(rs1)
        elif opcode in 'fnmadd':
            if iflen == 32 or iflen == 16:
                rs2 = (rs3 - ir_dataset[i][0])/rs1
            elif iflen == 64:
                rs2 = (Decimal(rs3) - Decimal(ir_dataset[i][0]))/Decimal(rs1)
        elif opcode in 'fmsub':
            if iflen == 32 or iflen == 16:
                rs2 = (ir_dataset[i][0] + rs3)/rs1
            elif iflen == 64:
                rs2 = (Decimal(ir_dataset[i][0]) + Decimal(rs3))/Decimal(rs1)
        elif opcode in 'fnmsub':
            if iflen == 32 or iflen == 16:
                rs2 = -1*(rs3 + ir_dataset[i][0])/rs1
            elif iflen == 64:
                rs2 = -1*(Decimal(rs3) + Decimal(ir_dataset[i][0]))/Decimal(rs1)

        if(iflen==16):
            m = lambda rsx: float('inf') if rsx > fields_dec_converter(16, hmaxnorm[0]) \
            else float('-inf') if rsx < fields_dec_converter(16, hmaxnorm[1]) \
            else rsx
            x1 = m(rs1)
            x2 = m(rs2)
            x3 = m(rs3)
        elif(iflen==32):
            x1 = struct.unpack('f', struct.pack('f', rs1))[0]
            x2 = struct.unpack('f', struct.pack('f', rs2))[0]
            x3 = struct.unpack('f', struct.pack('f', rs3))[0]
        elif(iflen==64):
            x1 = rs1
            x2 = rs2
            x3 = rs3

        if opcode in ['fadd','fsub','fmul','fdiv']:
            b4_comb.append((floatingPoint_tohex(iflen,float(rs1)),floatingPoint_tohex(iflen,float(rs2))))
        elif opcode in 'fsqrt':
            b4_comb.append((floatingPoint_tohex(iflen,float(rs2)),))
        elif opcode in ['fmadd','fnmadd','fmsub','fnmsub']:
            b4_comb.append((floatingPoint_tohex(iflen,float(rs1)),floatingPoint_tohex(iflen,float(rs2)),floatingPoint_tohex(iflen,float(rs3))))

    coverpoints = []
    k = 0
    for c in b4_comb:
        for rm in range(5):
            cvpt = ""
            for x in range(1, ops+1):
#                        cvpt += 'rs'+str(x)+'_val=='+str(c[x-1]) # uncomment this if you want rs1_val instead of individual fields
                cvpt += (extract_fields(iflen,c[x-1],str(x)))
                cvpt += " and "
            # cvpt += 'rm_val == '+str(rm)
            cvpt = sanitise(rm,cvpt,iflen,flen,ops,inxFlg)
            if inxFlg == True:
                cvpt += sgn_prefix(iflen,flen,inxFlg,ops,cvpt)
            else:
                cvpt += ' # '
            cvpt += ' # '
            for y in range(1, ops+1):
                cvpt += 'rs'+str(y)+'_val=='
                cvpt += num_explain(iflen, c[y-1]) + '(' + str(c[y-1]) + ')'
                if(y != ops):
                    cvpt += " and "
            cvpt += ir_dataset[k][1]
            coverpoints.append(cvpt)
        k=k+1

    mess='Generated'+ (' '*(5-len(str(len(coverpoints)))))+ str(len(coverpoints)) +' '+ \
    (str(16) if iflen == 16 else str(32) if iflen == 32 else str(64)) + '-bit coverpoints using Model B4 for '+opcode+' !'
    logger.debug(mess)
    coverpoints = comments_parser(coverpoints)

    return coverpoints

def ibm_b5(flen, iflen, opcode, ops, inxFlg=False, seed=-1):
    '''
    IBM Model B5 Definition:
            This model creates a test-case for each of the following constraints on the intermediate results:
            1. All the numbers in the range [+MinSubNorm – 3 ulp, +MinSubNorm + 3 ulp]
            2. All the numbers in the range [-MinSubNorm - 3 ulp, -MinSubNorm + 3 ulp]
            3. All the numbers in the range [MinNorm – 3 ulp, MinNorm + 3 ulp]
            4. All the numbers in the range [-MinSubNorm - 3 ulp, -MinSubNorm + 3 ulp]
            5. All the numbers in the range [MinNorm – 3 ulp, MinNorm + 3 ulp]
            6. All the numbers in the range [-MinNorm - 3 ulp, -MinNorm + 3 ulp]
            7. A random number in the range (0, MinSubNorm)
            8. A random number in the range (-MinSubNorm, -0)
            9. One number for every exponent in the range [MinNorm.exp, MinNorm.exp + 5]

    :param iflen: Size of the floating point source operands for the operation
    :param flen: Size of the floating point registers
    :param opcode: Opcode for which the coverpoints are to be generated
    :param ops: No. of Operands taken by the opcode
    :param seed: Initial seed value of the random library. (Predefined to -1. Actual value is set with respect to the opcode calling the function)

    :type iflen: int
    :type flen: int
    :type opcode: str
    :type ops: int
    :param seed: int

    Abstract Dataset Description:
            Intermediate Results = [+MinSubNorm – 3 ulp, +MinSubNorm + 3 ulp],  [-MinSubNorm - 3 ulp, -MinSubNorm + 3 ulp] , [MinNorm – 3 ulp, MinNorm + 3 ulp] , [-MinNorm - 3 ulp, -MinNorm + 3 ulp] , Random Num in (0, MinSubNorm), Random Num in (-MinSubNorm, -0), One Num for every exp in [MinNorm.exp, MinNorm.exp + 5]]
            Operand1 {operation} Operand2 = Intermediate Results

    Implementation:
            - The intermediate results dataset is populated in accordance with the abstract dataset defined above.
            - Intermediate results can be out of the range of what is representable in the specified format; they should only be viewed numerically. Inorder to represent numbers that went out of range of the maximum representable number in python, the “Decimal” module was utilized.
            - These operand values are treated as decimal numbers until their derivation after which they are converted into their respective IEEE754 hexadecimal floating point formats using the “floatingPoint_tohex” function.
            - Coverpoints are then appended with all rounding modes for that particular opcode.

    '''
    sanitise = get_sanitise_func(opcode)

    opcode = opcode.split('.')[0]
    getcontext().prec = 40
    if iflen == 16:
        ieee754_maxnorm = float.hex(fields_dec_converter(16, hmaxnorm[0]))
        maxnum = float.fromhex(ieee754_maxnorm)
        ieee754_minsubnorm = float.hex(fields_dec_converter(16, hminsubnorm[0]))
        ir_dataset = []
        for i in range(0,16,2):
            grs = '{:04b}'.format(i)
            ir_dataset.append([ieee754_minsubnorm.split('p')[0]+str(i)+'p'+ieee754_minsubnorm.split('p')[1],' | Guard = '+grs[0]+' Round = '+grs[1]+' Sticky = '+grs[2]+' --> Minsubnorm + '+str(int(grs[0:3],2))+' ulp'])
        ieee754_minnorm = '0x1.000000p-14'
        for i in range(0,16,2):
            grs = '{:04b}'.format(i)
            ir_dataset.append([ieee754_minnorm.split('p')[0]+str(i)+'p'+ieee754_minnorm.split('p')[1],' | Guard = '+grs[0]+' Round = '+grs[1]+' Sticky = '+grs[2]+' --> Minnorm + '+str(int(grs[0:3],2))+' ulp'])
        minnorm_Exp = ['0x1.000000p-14','0x1.000000p-13','0x1.000000p-12','0x1.000000p-11','0x1.000000p-10','0x1.000000p-9']
        for i in minnorm_Exp:
            ir_dataset.append([i,' | Exponent = MinNorm.exp + '+str(14+int(i.split('p')[1]))])
        n = len(ir_dataset)
        for i in range(n):
            ir_dataset[i][0] = float.fromhex(ir_dataset[i][0])
            ir_dataset.append([-1*ir_dataset[i][0],ir_dataset[i][1]])
    elif iflen == 32:
        ieee754_maxnorm = '0x1.7fffffp+127'
        maxnum = float.fromhex(ieee754_maxnorm)
        ieee754_minsubnorm = '0x0.000001p-126'
        ir_dataset = []
        for i in range(0,16,2):
            grs = '{:04b}'.format(i)
            ir_dataset.append([ieee754_minsubnorm.split('p')[0]+str(i)+'p'+ieee754_minsubnorm.split('p')[1],' | Guard = '+grs[0]+' Round = '+grs[1]+' Sticky = '+grs[2]+' --> Minsubnorm + '+str(int(grs[0:3],2))+' ulp'])
        ieee754_minnorm = '0x1.000000p-126'
        for i in range(0,16,2):
            grs = '{:04b}'.format(i)
            ir_dataset.append([ieee754_minnorm.split('p')[0]+str(i)+'p'+ieee754_minnorm.split('p')[1],' | Guard = '+grs[0]+' Round = '+grs[1]+' Sticky = '+grs[2]+' --> Minnorm + '+str(int(grs[0:3],2))+' ulp'])
        minnorm_Exp = ['0x1.000000p-126','0x1.000000p-125','0x1.000000p-124','0x1.000000p-123','0x1.000000p-122','0x1.000000p-121']
        for i in minnorm_Exp:
            ir_dataset.append([i,' | Exponent = MinNorm.exp + '+str(126+int(i.split('p')[1]))])
        n = len(ir_dataset)
        for i in range(n):
            ir_dataset[i][0] = float.fromhex(ir_dataset[i][0])
            ir_dataset.append([-1*ir_dataset[i][0],ir_dataset[i][1]])

    elif iflen == 64:
        maxdec = '1.7976931348623157e+308'
        maxnum = float.fromhex('0x1.fffffffffffffp+1023')
        minsubdec = '5e-324'
        ir_dataset = []
        for i in range(2,16,2):
            grs = '{:04b}'.format(i)
            ir_dataset.append([str(Decimal(minsubdec.split('e')[0])+Decimal(pow(i*16,-14)))+'e'+minsubdec.split('e')[1],' | Guard = '+grs[0]+' Round = '+grs[1]+' Sticky = '+grs[2]+' --> Minsubnorm + '+str(int(grs[0:3],2))+' ulp'])
        minnormdec = '2.2250738585072014e-308'
        ir_dataset.append([minsubdec, ' | Guard = 0 Round = 0 Sticky = 0 --> Minsubnorm + 0 ulp'])
        ir_dataset.append([minnormdec,' | Guard = 0 Round = 0 Sticky = 0 --> Minnorm + 0 ulp'])
        for i in range(2,16,2):
            grs = '{:04b}'.format(i)
            ir_dataset.append([str(Decimal(minnormdec.split('e')[0])+Decimal(pow(i*16,-14)))+'e'+minnormdec.split('e')[1],' | Guard = '+grs[0]+' Round = '+grs[1]+' Sticky = '+grs[2]+' --> Minnorm + '+str(int(grs[0:3],2))+' ulp'])
        minnorm_Exp = ['4.450147717014403e-308','8.900295434028806e-308','1.780059086805761e-307','3.560118173611522e-307','7.120236347223044e-307']

        k = 1
        for i in minnorm_Exp:
            ir_dataset.append([i,' | Exponent = MinNorm.exp + '+str(k)])
            k += 1
        n = len(ir_dataset)
        for i in range(n):
            ir_dataset.append(['-'+ir_dataset[i][0],ir_dataset[i][1]])

    if seed == -1:
        if opcode in 'fadd':
            random.seed(0)
        elif opcode in 'fsub':
            random.seed(1)
        elif opcode in 'fmul':
            random.seed(2)
        elif opcode in 'fdiv':
            random.seed(3)
        elif opcode in 'fsqrt':
            random.seed(4)
        elif opcode in 'fmadd':
            random.seed(5)
        elif opcode in 'fnmadd':
            random.seed(6)
        elif opcode in 'fmsub':
            random.seed(7)
        elif opcode in 'fnmsub':
            random.seed(8)
    else:
        random.seed(seed)

    b5_comb = []

    for i in range(len(ir_dataset)):
        rs1 = random.uniform(1,maxnum)
        rs3 = random.uniform(1,maxnum)
        if opcode in 'fadd':
            if iflen == 32 or iflen == 16:
                rs2 = ir_dataset[i][0] - rs1
            elif iflen == 64:
                rs2 = Decimal(ir_dataset[i][0]) - Decimal(rs1)
        elif opcode in 'fsub':
            if iflen == 32 or iflen == 16:
                rs2 = rs1 - ir_dataset[i][0]
            elif iflen == 64:
                rs2 = Decimal(rs1) - Decimal(ir_dataset[i][0])
        elif opcode in 'fmul':
            if iflen == 32 or iflen == 16:
                rs2 = ir_dataset[i][0]/rs1
            elif iflen == 64:
                rs2 = Decimal(ir_dataset[i][0])/Decimal(rs1)
        elif opcode in 'fdiv':
            if iflen == 32 or iflen == 16:
                rs2 = rs1/ir_dataset[i][0]
            elif iflen == 64:
                rs2 = Decimal(rs1)/Decimal(ir_dataset[i][0])
        elif opcode in 'fsqrt':
            if iflen == 32 or iflen == 16:
                rs2 = ir_dataset[i][0]*ir_dataset[i][0]
            elif iflen == 64:
                rs2 = Decimal(ir_dataset[i][0])*Decimal(ir_dataset[i][0])
        elif opcode in 'fmadd':
            if iflen == 32 or iflen == 16:
                rs2 = (ir_dataset[i][0] - rs3)/rs1
            elif iflen == 64:
                rs2 = (Decimal(ir_dataset[i][0]) - Decimal(rs3))/Decimal(rs1)
        elif opcode in 'fnmadd':
            if iflen == 32 or iflen == 16:
                rs2 = (rs3 - ir_dataset[i][0])/rs1
            elif iflen == 64:
                rs2 = (Decimal(rs3) - Decimal(ir_dataset[i][0]))/Decimal(rs1)
        elif opcode in 'fmsub':
            if iflen == 32 or iflen == 16:
                rs2 = (ir_dataset[i][0] + rs3)/rs1
            elif iflen == 64:
                rs2 = (Decimal(ir_dataset[i][0]) + Decimal(rs3))/Decimal(rs1)
        elif opcode in 'fnmsub':
            if iflen == 32 or iflen == 16:
                rs2 = -1*(rs3 + ir_dataset[i][0])/rs1
            elif iflen == 64:
                rs2 = -1*(Decimal(rs3) + Decimal(ir_dataset[i][0]))/Decimal(rs1)

        if(iflen==16):
            m = lambda rsx: float('inf') if rsx > fields_dec_converter(16, hmaxnorm[0]) \
            else float('-inf') if rsx < fields_dec_converter(16, hmaxnorm[1]) \
            else rsx
            x1 = m(rs1)
            x2 = m(rs2)
            x3 = m(rs3)
        elif(iflen==32):
            x1 = struct.unpack('f', struct.pack('f', rs1))[0]
            x2 = struct.unpack('f', struct.pack('f', rs2))[0]
            x3 = struct.unpack('f', struct.pack('f', rs3))[0]
        elif(iflen==64):
            x1 = rs1
            x2 = rs2
            x3 = rs3

        if opcode in ['fadd','fsub','fmul','fdiv']:
            b5_comb.append((floatingPoint_tohex(iflen,float(rs1)),floatingPoint_tohex(iflen,float(rs2))))
        elif opcode in 'fsqrt':
            b5_comb.append((floatingPoint_tohex(iflen,float(rs2)),))
        elif opcode in ['fmadd','fnmadd','fmsub','fnmsub']:
            b5_comb.append((floatingPoint_tohex(iflen,float(rs1)),floatingPoint_tohex(iflen,float(rs2)),floatingPoint_tohex(iflen,float(rs3))))

    coverpoints = []
    k = 0
    for c in b5_comb:
        for rm in range(5):
            cvpt = ""
            for x in range(1, ops+1):
#                        cvpt += 'rs'+str(x)+'_val=='+str(c[x-1]) # uncomment this if you want rs1_val instead of individual fields
                cvpt += (extract_fields(iflen,c[x-1],str(x)))
                cvpt += " and "
            # cvpt += 'rm_val == '+str(rm)
            cvpt =  sanitise(rm,cvpt,iflen,flen,ops,inxFlg)
            if inxFlg == True:
                cvpt += sgn_prefix(iflen,flen,inxFlg,ops,cvpt)
            else:
                cvpt += ' # '
            cvpt += ' # '
            for y in range(1, ops+1):
                cvpt += 'rs'+str(y)+'_val=='
                cvpt += num_explain(iflen, c[y-1]) + '(' + str(c[y-1]) + ')'
                if(y != ops):
                    cvpt += " and "
            cvpt += ir_dataset[k][1]
            coverpoints.append(cvpt)
        k=k+1

    mess='Generated'+ (' '*(5-len(str(len(coverpoints)))))+ str(len(coverpoints)) +' '+ \
    (str(16) if iflen == 16 else str(32) if iflen == 32 else str(64)) + '-bit coverpoints using Model B5 for '+opcode+' !'
    logger.debug(mess)
    coverpoints = comments_parser(coverpoints)

    return coverpoints

def ibm_b6(flen, iflen, opcode, ops, inxFlg=False, seed=-1):
    '''
    IBM Model B6 Definition:
            This model tests intermediate results in the space between –MinSubNorm and
            +MinSubNorm. For each of the following ranges, we select 8 random test cases,
            one for every combination of the LSB, guard bit, and sticky bit.

            1. -MinSubNorm < intermediate < -MinSubNorm / 2
            2. -MinSubNorm / 2 <= intermediate < 0
            3. 0 < intermediate <= +MinSubNorm / 2
            4. +MinSubNorm / 2 < intermediate < +MinSubNorm

    :param iflen: Size of the floating point source operands for the operation
    :param flen: Size of the floating point registers
    :param opcode: Opcode for which the coverpoints are to be generated
    :param ops: No. of Operands taken by the opcode
    :param seed: Initial seed value of the random library. (Predefined to -1. Actual value is set with respect to the opcode calling the function)

    :type iflen: int
    :type flen: int
    :type opcode: str
    :type ops: int
    :param seed: int

    Abstract Dataset Description:
            Intermediate Results = [Random number ∈ (-MinSubNorm, -MinSubNorm/2), Random number ∈ (-MinSubNorm/2, 0), Random number ∈ (0, +MinSubNorm/2), Random number ∈ (+MinSubNorm/2, +MinSubNorm)]
            {All 8 combinations of guard, round and sticky bit are tested for every number}
            Operand1 {operation} Operand2 = Intermediate Results

    Implementation:
            - The intermediate results dataset is populated in accordance with the abstract dataset defined above.
            - Intermediate results can be out of the range of what is representable in the specified format; they should only be viewed numerically. Inorder to represent numbers that went out of range of the maximum representable number in python, the “Decimal” module was utilized.
            - These operand values are treated as decimal numbers until their derivation after which they are converted into their respective IEEE754 hexadecimal floating point formats using the “floatingPoint_tohex” function.
            - The operand values are then passed into the extract_fields function to get individual fields in a floating point number (sign, exponent and mantissa).
            - Coverpoints are then appended with all rounding modes for that particular opcode.

    '''
    sanitise = get_sanitise_func(opcode)
    opcode = opcode.split('.')[0]
    getcontext().prec = 40

    if seed == -1:
        if opcode in 'fmul':
            random.seed(0)
        elif opcode in 'fdiv':
            random.seed(1)
        elif opcode in 'fmadd':
            random.seed(2)
        elif opcode in 'fnmadd':
            random.seed(3)
        elif opcode in 'fmsub':
            random.seed(4)
        elif opcode in 'fnmsub':
            random.seed(5)
    else:
        random.seed(seed)

    if iflen == 16:
        ir_dataset = []
        ieee754_minsubnorm_n = float.hex(fields_dec_converter(16, hminsubnorm[1]))
        minnum = float.fromhex(ieee754_minsubnorm_n)
        r=str(random.uniform(minnum,minnum/2))
        for i in range(2,16,2):
            grs = '{:04b}'.format(i)
            print("+"*20)
            print(str(Decimal(r.split('e')[0])))
            print(i)
            print(i*16,-7)
            print(pow(i*16, -7))
            print("="*20)
            for p in range(8):
                print(Decimal(pow(i*16,-1*p)))
            print("="*20)
            print(Decimal(pow(i*16,-2)))
            print(r.split('e')[1])
            print(str(Decimal(r.split('e')[0])+Decimal(pow(i*4,-2))))
            ir_dataset.append([str(Decimal(r.split('e')[0])+Decimal(pow(i*4,-4)))+'e'+r.split('e')[1],' | Guard = '+grs[0]+' Round = '+grs[1]+' Sticky = '+grs[2]+' --> IR ∈ (-MinSubNorm, -MinSubNorm / 2)'])
        r=str(random.uniform(minnum/2,0))
        for i in range(2,16,2):
            grs = '{:04b}'.format(i)
            ir_dataset.append([str(Decimal(r.split('e')[0])+Decimal(pow(i*4,-4)))+'e'+r.split('e')[1],' | Guard = '+grs[0]+' Round = '+grs[1]+' Sticky = '+grs[2]+' --> IR ∈ (-MinSubNorm / 2, 0)'])
        r=str(random.uniform(0,	(minnum/2)))
        for i in range(2,16,2):
            grs = '{:04b}'.format(i)
            ir_dataset.append([str(Decimal(r.split('e')[0])+Decimal(pow(i*4,-4)))+'e'+r.split('e')[1],' | Guard = '+grs[0]+' Round = '+grs[1]+' Sticky = '+grs[2]+' --> IR ∈ (0, +MinSubNorm / 2)'])
        r=str(random.uniform(abs(minnum/2),abs(minnum)))
        for i in range(2,16,2):
            grs = '{:04b}'.format(i)
            ir_dataset.append([str(Decimal(r.split('e')[0])+Decimal(pow(i*16,-14))),' | Guard = '+grs[0]+' Round = '+grs[1]+' Sticky = '+grs[2]+' --> IR ∈ (+MinSubNorm / 2, +MinSubNorm)'])
    elif iflen == 32:
        ir_dataset = []
        ieee754_minsubnorm_n = '-0x0.000001p-127'
        minnum = float.fromhex(ieee754_minsubnorm_n)
        r=str(random.uniform(minnum,minnum/2))
        for i in range(2,16,2):
            grs = '{:04b}'.format(i)
            ir_dataset.append([str(Decimal(r.split('e')[0])+Decimal(pow(i*16,-7)))+'e'+r.split('e')[1],' | Guard = '+grs[0]+' Round = '+grs[1]+' Sticky = '+grs[2]+' --> IR ∈ (-MinSubNorm, -MinSubNorm / 2)'])
        r=str(random.uniform(minnum/2,0))
        for i in range(2,16,2):
            grs = '{:04b}'.format(i)
            ir_dataset.append([str(Decimal(r.split('e')[0])+Decimal(pow(i*16,-7)))+'e'+r.split('e')[1],' | Guard = '+grs[0]+' Round = '+grs[1]+' Sticky = '+grs[2]+' --> IR ∈ (-MinSubNorm / 2, 0)'])
        r=str(random.uniform(0,abs(minnum/2)))
        for i in range(2,16,2):
            grs = '{:04b}'.format(i)
            ir_dataset.append([str(Decimal(r.split('e')[0])+Decimal(pow(i*16,-7)))+'e'+r.split('e')[1],' | Guard = '+grs[0]+' Round = '+grs[1]+' Sticky = '+grs[2]+' --> IR ∈ (0, +MinSubNorm / 2)'])
        r=str(random.uniform(abs(minnum/2),abs(minnum)))
        for i in range(2,16,2):
            grs = '{:04b}'.format(i)
            ir_dataset.append([str(Decimal(r.split('e')[0])+Decimal(pow(i*16,-7)))+'e'+r.split('e')[1],' | Guard = '+grs[0]+' Round = '+grs[1]+' Sticky = '+grs[2]+' --> IR ∈ (+MinSubNorm / 2, +MinSubNorm)'])
    elif iflen == 64:
        ir_dataset = []
        ieee754_minsubnorm_n = '-0x0.0000000000001p-1022'
        minnum = float.fromhex(ieee754_minsubnorm_n)
        r=str("{:.2e}".format(random.uniform(minnum,minnum/2)))
        for i in range(2,16,2):
            grs = '{:04b}'.format(i)
            ir_dataset.append([str(Decimal(r.split('e')[0])+Decimal(pow(i*16,-14))),' | Guard = '+grs[0]+' Round = '+grs[1]+' Sticky = '+grs[2]+' --> IR ∈ (-MinSubNorm, -MinSubNorm / 2)'])
        r=str("{:.2e}".format(random.uniform(minnum/2,0)))
        for i in range(2,16,2):
            grs = '{:04b}'.format(i)
            ir_dataset.append([str(Decimal(r.split('e')[0])+Decimal(pow(i*16,-14))),' | Guard = '+grs[0]+' Round = '+grs[1]+' Sticky = '+grs[2]+' --> IR ∈ (-MinSubNorm / 2, 0)'])
        r=str("{:.2e}".format(random.uniform(0,abs(minnum/2))))
        for i in range(2,16,2):
            grs = '{:04b}'.format(i)
            ir_dataset.append([str(Decimal(r.split('e')[0])+Decimal(pow(i*16,-14))),' | Guard = '+grs[0]+' Round = '+grs[1]+' Sticky = '+grs[2]+' --> IR ∈ (0, +MinSubNorm / 2)'])
        r=str("{:.2e}".format(random.uniform(abs(minnum/2),abs(minnum))))
        for i in range(2,16,2):
            grs = '{:04b}'.format(i)
            ir_dataset.append([str(Decimal(r.split('e')[0])+Decimal(pow(i*16,-14))),' | Guard = '+grs[0]+' Round = '+grs[1]+' Sticky = '+grs[2]+' --> IR ∈ (+MinSubNorm / 2, +MinSubNorm)'])

    b6_comb = []

    for i in range(len(ir_dataset)):
        rs1 = random.uniform(0,1e-30)
        rs3 = random.uniform(0,1e-30)

        if opcode in 'fmul':
                rs2 = Decimal(ir_dataset[i][0])/Decimal(rs1)
        elif opcode in 'fdiv':
                rs2 = Decimal(rs1)/Decimal(ir_dataset[i][0])
        elif opcode in 'fmadd':
                rs2 = (Decimal(ir_dataset[i][0]) - Decimal(rs3))/Decimal(rs1)
        elif opcode in 'fnmadd':
                rs2 = (Decimal(rs3) - Decimal(ir_dataset[i][0]))/Decimal(rs1)
        elif opcode in 'fmsub':
                rs2 = (Decimal(ir_dataset[i][0]) + Decimal(rs3))/Decimal(rs1)
        elif opcode in 'fnmsub':
                rs2 = -1*(Decimal(rs3) + Decimal(ir_dataset[i][0]))/Decimal(rs1)

        if(iflen==16):
            m = lambda rsx: float('inf') if rsx > fields_dec_converter(16, hmaxnorm[0]) \
            else float('-inf') if rsx < fields_dec_converter(16, hmaxnorm[1]) \
            else rsx
            x1 = m(rs1)
            x2 = m(rs2)
            x3 = m(rs3)
        elif(iflen==32):
            x1 = struct.unpack('f', struct.pack('f', rs1))[0]
            x2 = struct.unpack('f', struct.pack('f', rs2))[0]
            x3 = struct.unpack('f', struct.pack('f', rs3))[0]
        elif(iflen==64):
            x1 = rs1
            x2 = rs2
            x3 = rs3

        if opcode in ['fmul','fdiv']:
            b6_comb.append((floatingPoint_tohex(iflen,float(rs1)),floatingPoint_tohex(iflen,float(rs2))))
        elif opcode in ['fmadd','fnmadd','fmsub','fnmsub']:
            b6_comb.append((floatingPoint_tohex(iflen,float(rs1)),floatingPoint_tohex(iflen,float(rs2)),floatingPoint_tohex(iflen,float(rs3))))

    #print(*b6_comb,sep='\n')
    coverpoints = []
    k=0

    for c in b6_comb:
        for rm in range(5):
            cvpt = ""
            for x in range(1, ops+1):
#                        cvpt += 'rs'+str(x)+'_val=='+str(c[x-1]) # uncomment this if you want rs1_val instead of individual fields
                cvpt += (extract_fields(iflen,c[x-1],str(x)))
                cvpt += " and "
            cvpt =  sanitise(rm,cvpt,iflen,flen,ops,inxFlg)
            # cvpt += 'rm_val == '+str(rm)
            if inxFlg == True:
                cvpt += sgn_prefix(iflen,flen,inxFlg,ops,cvpt)
            else:
                cvpt += ' # '
            cvpt += ' # '
            for y in range(1, ops+1):
                cvpt += 'rs'+str(y)+'_val=='
                cvpt += num_explain(iflen, c[y-1]) + '(' + str(c[y-1]) + ')'
                if(y != ops):
                    cvpt += " and "
            cvpt += ir_dataset[k][1]
            coverpoints.append(cvpt)
        k=k+1

    mess='Generated'+ (' '*(5-len(str(len(coverpoints)))))+ str(len(coverpoints)) +' '+ \
    (str(16) if iflen == 16 else str(32) if iflen == 32 else str(64)) + '-bit coverpoints using Model B6 for '+opcode+' !'
    logger.debug(mess)
    coverpoints = comments_parser(coverpoints)

    return coverpoints

def ibm_b7(flen, iflen, opcode, ops, inxFlg=False, seed=-1):
    '''
    IBM Model B7 Definition:
            This model checks that the sticky bit is calculated correctly in each of the following cases (for every possible combination in the table). The Guard bit should always be 0, and the sign positive, so that miscalculation of the sticky bit will alter the final result.
            Mask in Extra bits

            .. code-block::

                1000...000
                0100...000
                …
                0000...010
                0000...001
                0000000000

    :param flen: Size of the floating point registers
    :param iflen: Size of the floating point source operands for the operation
    :param opcode: Opcode for which the coverpoints are to be generated
    :param ops: No. of Operands taken by the opcode
    :param seed: Initial seed value of the random library. (Predefined to -1. Actual value is set with respect to the opcode calling the function)

    :type iflen: int
    :type flen: int
    :type opcode: str
    :type ops: int
    :param seed: int

    Abstract Dataset Description:
            Intermediate Results = [ieee754_maxnorm, maxnum, maxdec, maxnum]
            {It assures the calculation of sticky bit for every possible combination in the table}
            Operand1 {operation} Operand2 = Intermediate Results

    Implementation:
            - The Sticky bit is calculated in each case. The guard bit here is always assumed to be zero and the sign is positive, so that miscalculation of the sticky bit will alter the final result.
            - In the intermediate result dataset, the elements are appended as elements before the character ‘p’ and then the binary equivalent of ‘010’ + pow(2,i).
            - Finally on the extra bits, it is masked with the comment created in the previous point. All the first character of each element is converted to its floating point equivalent in a loop
            - The operand values are then passed into the extract_fields function to get individual fields in a floating point number (sign, exponent and mantissa).
            - Coverpoints are then appended with all rounding modes for that particular opcode.

    '''
   
    sanitise = get_sanitise_func(opcode)
    opcode = opcode.split('.')[0]
    getcontext().prec = 60
    if iflen == 16:
        ieee754_maxnorm = float.hex(fields_dec_converter(16, hmaxnorm[0]))
        maxnum = float.fromhex(ieee754_maxnorm)
        ieee754_num = []
        for i in hsubnorm+hnorm:
            float_val = float.hex(fields_dec_converter(16,i))
            if float_val[0] != '-':
                ieee754_num.append(float_val.split('p')[0][0:7]+'p'+float_val.split('p')[1])
        ir_dataset = []
        for k in range(len(ieee754_num)):
            for i in range(0,7):
                comment = (7-i)*'0' + '1' + i*'0'
                ir_dataset.append([ieee754_num[k].split('p')[0]+hex(int('010'+'{:08b}'.format(pow(2,i)),2))[2:]+'p'+ieee754_num[k].split('p')[1],' | Mask on extra bits ---> ' + comment])
        n = len(ir_dataset)
        for i in range(n):
            ir_dataset[i][0] = float.fromhex(ir_dataset[i][0])
    elif iflen == 32:
        ieee754_maxnorm = '0x1.7fffffp+127'
        maxnum = float.fromhex(ieee754_maxnorm)
        ieee754_num = []
        for i in fsubnorm+fnorm:
            float_val = float.hex(fields_dec_converter(32,i))
            if float_val[0] != '-':
                ieee754_num.append(float_val.split('p')[0][0:10]+'p'+float_val.split('p')[1])
        ir_dataset = []
        for k in range(len(ieee754_num)):
            for i in range(0,20):
                comment = (20-i)*'0' + '1' + i*'0'
                ir_dataset.append([ieee754_num[k].split('p')[0]+hex(int('010'+'{:021b}'.format(pow(2,i)),2))[2:]+'p'+ieee754_num[k].split('p')[1],' | Mask on extra bits ---> ' + comment])
        n = len(ir_dataset)
        for i in range(n):
            ir_dataset[i][0] = float.fromhex(ir_dataset[i][0])

    elif iflen == 64:
        maxdec = '1.7976931348623157e+308'
        maxnum = float.fromhex('0x1.fffffffffffffp+1023')
        ieee754_num = []
        for i in dsubnorm+dnorm:
            float_val = fields_dec_converter(64,i)
            if float_val > 0:
                ieee754_num.append(str(float_val))

        ir_dataset = []
        for l in range(len(ieee754_num)):
            for k in range(1,13):
                for i in range(4):
                    comment = (k*(i+1))*'0' + '1' + (51-(k*(i+1)))*'0'
                    ir_dataset.append([str(Decimal(ieee754_num[l].split('e')[0])+Decimal(pow(16,-14))+Decimal(pow(pow(2,3-i)*16,-14-k)))+'e'+ieee754_num[l].split('e')[1],' | Mask on extra bits ---> ' + comment])

    if seed == -1:
        if opcode in 'fadd':
            random.seed(0)
        elif opcode in 'fsub':
            random.seed(1)
        elif opcode in 'fmul':
            random.seed(2)
        elif opcode in 'fdiv':
            random.seed(3)
        elif opcode in 'fsqrt':
            random.seed(4)
        elif opcode in 'fmadd':
            random.seed(5)
        elif opcode in 'fnmadd':
            random.seed(6)
        elif opcode in 'fmsub':
            random.seed(7)
        elif opcode in 'fnmsub':
            random.seed(8)
    else:
        random.seed(seed)

    b7_comb = []

    for i in range(len(ir_dataset)):
        rs1 = random.uniform(1,maxnum)
        rs3 = random.uniform(1,maxnum)
        if opcode in 'fadd':
            if iflen == 32 or iflen == 16:
                rs2 = ir_dataset[i][0] - rs1
            elif iflen == 64:
                rs2 = Decimal(ir_dataset[i][0]) - Decimal(rs1)
        elif opcode in 'fsub':
            if iflen == 32 or iflen == 16:
                rs2 = rs1 - ir_dataset[i][0]
            elif iflen == 64:
                rs2 = Decimal(rs1) - Decimal(ir_dataset[i][0])
        elif opcode in 'fmul':
            if iflen == 32 or iflen == 16:
                rs2 = ir_dataset[i][0]/rs1
            elif iflen == 64:
                rs2 = Decimal(ir_dataset[i][0])/Decimal(rs1)
        elif opcode in 'fdiv':
            if iflen == 32 or iflen == 16:
                rs2 = rs1/ir_dataset[i][0]
            elif iflen == 64:
                rs2 = Decimal(rs1)/Decimal(ir_dataset[i][0])
        elif opcode in 'fsqrt':
            if iflen == 32 or iflen == 16:
                rs2 = ir_dataset[i][0]*ir_dataset[i][0]
            elif iflen == 64:
                rs2 = Decimal(ir_dataset[i][0])*Decimal(ir_dataset[i][0])
        elif opcode in 'fmadd':
            if iflen == 32 or iflen == 16:
                rs2 = (ir_dataset[i][0] - rs3)/rs1
            elif iflen == 64:
                rs2 = (Decimal(ir_dataset[i][0]) - Decimal(rs3))/Decimal(rs1)
        elif opcode in 'fnmadd':
            if iflen == 32 or iflen == 16:
                rs2 = (rs3 - ir_dataset[i][0])/rs1
            elif iflen == 64:
                rs2 = (Decimal(rs3) - Decimal(ir_dataset[i][0]))/Decimal(rs1)
        elif opcode in 'fmsub':
            if iflen == 32 or iflen == 16:
                rs2 = (ir_dataset[i][0] + rs3)/rs1
            elif iflen == 64:
                rs2 = (Decimal(ir_dataset[i][0]) + Decimal(rs3))/Decimal(rs1)
        elif opcode in 'fnmsub':
            if iflen == 32 or iflen == 16:
                rs2 = -1*(rs3 + ir_dataset[i][0])/rs1
            elif iflen == 64:
                rs2 = -1*(Decimal(rs3) + Decimal(ir_dataset[i][0]))/Decimal(rs1)

        if(iflen==16):
            m = lambda rsx: float('inf') if rsx > fields_dec_converter(16, hmaxnorm[0]) \
            else float('-inf') if rsx < fields_dec_converter(16, hmaxnorm[1]) \
            else rsx
            x1 = m(rs1)
            x2 = m(rs2)
            x3 = m(rs3)
        elif(iflen==32):
            x1 = struct.unpack('f', struct.pack('f', rs1))[0]
            x2 = struct.unpack('f', struct.pack('f', rs2))[0]
            x3 = struct.unpack('f', struct.pack('f', rs3))[0]
        elif(iflen==64):
            x1 = rs1
            x2 = rs2
            x3 = rs3

        if opcode in ['fadd','fsub','fmul','fdiv']:
            b7_comb.append((floatingPoint_tohex(iflen,float(rs1)),floatingPoint_tohex(iflen,float(rs2))))
        elif opcode in 'fsqrt':
            b7_comb.append((floatingPoint_tohex(iflen,float(rs2)),))
        elif opcode in ['fmadd','fnmadd','fmsub','fnmsub']:
            b7_comb.append((floatingPoint_tohex(iflen,float(rs1)),floatingPoint_tohex(iflen,float(rs2)),floatingPoint_tohex(iflen,float(rs3))))

    coverpoints = []
    k = 0
    for c in b7_comb:
        cvpt = ""
        for x in range(1, ops+1):
#                       cvpt += 'rs'+str(x)+'_val=='+str(c[x-1]) # uncomment this if you want rs1_val instead of individual fields
            cvpt += (extract_fields(iflen,c[x-1],str(x)))
            cvpt += " and "
        # cvpt += 'rm_val == 3'
        cvpt = sanitise(3,cvpt,iflen,flen,ops,inxFlg)
        if inxFlg == True:
            cvpt += sgn_prefix(iflen,flen,inxFlg,ops,cvpt)
        else:
            cvpt += ' # '
        cvpt += ' # '
        for y in range(1, ops+1):
            cvpt += 'rs'+str(y)+'_val=='
            cvpt += num_explain(iflen, c[y-1]) + '(' + str(c[y-1]) + ')'
            if(y != ops):
                cvpt += " and "
        cvpt += ir_dataset[k][1]
        coverpoints.append(cvpt)
        k=k+1

    mess='Generated'+ (' '*(5-len(str(len(coverpoints)))))+ str(len(coverpoints)) +' '+ \
    (str(16) if iflen == 16 else str(32) if iflen == 32 else str(64)) + '-bit coverpoints using Model B7 for '+opcode+' !'
    logger.debug(mess)
    coverpoints = comments_parser(coverpoints)

    return coverpoints

def ibm_b8(flen, iflen, opcode, ops, inxFlg=False, seed=-1):
    '''
    IBM Model B8 Definition:
            This model targets numbers that are on the edge of a rounding boundary. These boundaries may vary depending on the rounding mode. These numbers include floating-point numbers and midpoints between floating-point numbers. In order to target the vicinity of these numbers, we test the following constraints on the extra bits of the intermediate result:

            1. All values of extra-bits in the range [000...00001, 000...00011]
            2. All values of extra-bits in the range [111...11100, 111...11111]

            For each value selected above, test all the combinations on the LSB of the significand, the guard bit, and the sticky bit (if the number of extra bits is not finite).

    :param iflen: Size of the floating point source operands for the operation
    :param flen: Size of the floating point registers
    :param opcode: Opcode for which the coverpoints are to be generated
    :param ops: No. of Operands taken by the opcode
    :param seed: Initial seed value of the random library. (Predefined to -1. Actual value is set with respect to the opcode calling the function)

    :type iflen: int
    :type flen: int
    :type opcode: str
    :type ops: int
    :param seed: int

    Abstract Dataset Description:
            Intermediate Results = [For every Subnormal and Normal number, 8 combinations of guard, round and sticky bit are appended, along with 6 combinations(3 positive, 3 negative) of the mask on extra bits]
            Operand1 {operation} Operand2 = Intermediate Results

    Implementation:
            - The intermediate results dataset is populated in accordance with the abstract dataset defined above. The coverpoints can be increased by increasing the dataset of normal and subnormal numbers.
            - Intermediate results can be out of the range of what is representable in the specified format; they should only be viewed numerically. Inorder to represent numbers that went out of range of the maximum representable number in python, the “Decimal” module was utilized.
            - These operand values are treated as decimal numbers until their derivation after which they are converted into their respective IEEE754 hexadecimal floating point formats using the “floatingPoint_tohex” function.
            - The operand values are then passed into the extract_fields function to get individual fields in a floating point number (sign, exponent and mantissa).
            - Coverpoints are then appended with all rounding modes for that particular opcode.

    '''
    sanitise = get_sanitise_func(opcode)
    opcode = opcode.split('.')[0]
    getcontext().prec = 60
    if iflen == 16:
        ieee754_maxnorm = float.hex(fields_dec_converter(16, hmaxnorm[0]))
        maxnum = float.fromhex(ieee754_maxnorm)
        ieee754_num = []
        for i in hsubnorm+hnorm:
            float_val = float.hex(fields_dec_converter(16,i))
            if float_val[0] != '-':
                ieee754_num.append(float_val.split('p')[0][0:7]+'p'+float_val.split('p')[1])
        ir_dataset = []
		# print(*ieee754_num, sep = '\n')
        for k in range(len(ieee754_num)):
            for i in range(1,4):
                for j in range(1,8):
                    grs = '{:03b}'.format(j)
                    ir_dataset.append([ieee754_num[k].split('p')[0]+hex(int('{:03b}'.format(j)+19*'0'+'{:02b}'.format(i),2))[2:]+'p'+ieee754_num[k].split('p')[1],' | Guard = '+grs[0]+' Round = '+grs[1]+' Sticky = '+grs[2]+' --> Mask On Extra Bits: '+19*'0'+'{:02b}'.format(i)])
                    ir_dataset.append([ieee754_num[k].split('p')[0]+hex(int('{:03b}'.format(j)+19*'1'+'{:02b}'.format(i),2))[2:]+'p'+ieee754_num[k].split('p')[1],' | Guard = '+grs[0]+' Round = '+grs[1]+' Sticky = '+grs[2]+' --> Mask On Extra Bits: '+19*'1'+'{:02b}'.format(i)])
                    print(ir_dataset[-2])
                    print(ir_dataset[-1])
        n = len(ir_dataset)
        for i in range(n):
            ir_dataset[i][0] = float.fromhex(ir_dataset[i][0])
    elif iflen == 32:
        ieee754_maxnorm = '0x1.7fffffp+127'
        maxnum = float.fromhex(ieee754_maxnorm)
        ieee754_num = []
        for i in fsubnorm+fnorm:
            float_val = float.hex(fields_dec_converter(32,i))
            if float_val[0] != '-':
                ieee754_num.append(float_val.split('p')[0][0:10]+'p'+float_val.split('p')[1])
        ir_dataset = []
        # print(*ieee754_num, sep = '\n')
        for k in range(len(ieee754_num)):
            for i in range(1,4):
                for j in range(1,8):
                    grs = '{:03b}'.format(j)
                    ir_dataset.append([ieee754_num[k].split('p')[0]+hex(int('{:03b}'.format(j)+19*'0'+'{:02b}'.format(i),2))[2:]+'p'+ieee754_num[k].split('p')[1],' | Guard = '+grs[0]+' Round = '+grs[1]+' Sticky = '+grs[2]+' --> Mask On Extra Bits: '+19*'0'+'{:02b}'.format(i)])
                    ir_dataset.append([ieee754_num[k].split('p')[0]+hex(int('{:03b}'.format(j)+19*'1'+'{:02b}'.format(i),2))[2:]+'p'+ieee754_num[k].split('p')[1],' | Guard = '+grs[0]+' Round = '+grs[1]+' Sticky = '+grs[2]+' --> Mask On Extra Bits: '+19*'1'+'{:02b}'.format(i)])
        n = len(ir_dataset)
        for i in range(n):
            ir_dataset[i][0] = float.fromhex(ir_dataset[i][0])

    elif iflen == 64:
        maxdec = '1.7976931348623157e+308'
        maxnum = float.fromhex('0x1.fffffffffffffp+1023')
        ieee754_num = []
        for i in dsubnorm+dnorm:
            float_val = float.hex(fields_dec_converter(64,i))
            if float_val[0] != '-':
                ieee754_num.append(float_val.split('p')[0][0:17]+'p'+float_val.split('p')[1])
        ir_dataset = []
        for k in range(len(ieee754_num)):
            for i in range(1,4):
                for j in range(1,8):
                    grs = '{:03b}'.format(j)
                    ir_dataset.append([ieee754_num[k].split('p')[0]+hex(int('010'+19*'0'+'{:02b}'.format(i),2))[2:]+'p'+ieee754_num[k].split('p')[1],' | Guard = '+grs[0]+' Round = '+grs[1]+' Sticky = '+grs[2]+' --> Mask On Extra Bits: '+19*'0'+'{:02b}'.format(i)])
                    ir_dataset.append([ieee754_num[k].split('p')[0]+hex(int('010'+19*'1'+'{:02b}'.format(i),2))[2:]+'p'+ieee754_num[k].split('p')[1],' | Guard = '+grs[0]+' Round = '+grs[1]+' Sticky = '+grs[2]+' --> Mask On Extra Bits: '+19*'1'+'{:02b}'.format(i)])
        n = len(ir_dataset)
        for i in range(n):
            ir_dataset[i][0] = float.fromhex(ir_dataset[i][0])

    if seed == -1:
        if opcode in 'fadd':
            random.seed(0)
        elif opcode in 'fsub':
            random.seed(1)
        elif opcode in 'fmul':
            random.seed(2)
        elif opcode in 'fdiv':
            random.seed(3)
        elif opcode in 'fsqrt':
            random.seed(4)
        elif opcode in 'fmadd':
            random.seed(5)
        elif opcode in 'fnmadd':
            random.seed(6)
        elif opcode in 'fmsub':
            random.seed(7)
        elif opcode in 'fnmsub':
            random.seed(8)
    else:
        random.seed(seed)

    b8_comb = []

    for i in range(len(ir_dataset)):
        rs1 = random.uniform(1,ir_dataset[i][0])
        rs3 = random.uniform(1,ir_dataset[i][0])
        if opcode in 'fadd':
            if iflen == 32 or iflen == 16:
                rs2 = ir_dataset[i][0] - rs1
            elif iflen == 64:
                rs2 = Decimal(ir_dataset[i][0]) - Decimal(rs1)
        elif opcode in 'fsub':
            if iflen == 32 or iflen == 16:
                rs2 = rs1 - ir_dataset[i][0]
            elif iflen == 64:
                rs2 = Decimal(rs1) - Decimal(ir_dataset[i][0])
        elif opcode in 'fmul':
            if iflen == 32 or iflen == 16:
                rs2 = ir_dataset[i][0]/rs1
            elif iflen == 64:
                rs2 = Decimal(ir_dataset[i][0])/Decimal(rs1)
        elif opcode in 'fdiv':
            if iflen == 32 or iflen == 16:
                rs2 = rs1/ir_dataset[i][0]
            elif iflen == 64:
                rs2 = Decimal(rs1)/Decimal(ir_dataset[i][0])
        elif opcode in 'fsqrt':
            if iflen == 32 or iflen == 16:
                rs2 = ir_dataset[i][0]*ir_dataset[i][0]
            elif iflen == 64:
                rs2 = Decimal(ir_dataset[i][0])*Decimal(ir_dataset[i][0])
        elif opcode in 'fmadd':
            if iflen == 32 or iflen == 16:
                rs2 = (ir_dataset[i][0] - rs3)/rs1
            elif iflen == 64:
                rs2 = (Decimal(ir_dataset[i][0]) - Decimal(rs3))/Decimal(rs1)
        elif opcode in 'fnmadd':
            if iflen == 32 or iflen == 16:
                rs2 = (rs3 - ir_dataset[i][0])/rs1
            elif iflen == 64:
                rs2 = (Decimal(rs3) - Decimal(ir_dataset[i][0]))/Decimal(rs1)
        elif opcode in 'fmsub':
            if iflen == 32 or iflen == 16:
                rs2 = (ir_dataset[i][0] + rs3)/rs1
            elif iflen == 64:
                rs2 = (Decimal(ir_dataset[i][0]) + Decimal(rs3))/Decimal(rs1)
        elif opcode in 'fnmsub':
            if iflen == 32 or iflen == 16:
                rs2 = -1*(rs3 + ir_dataset[i][0])/rs1
            elif iflen == 64:
                rs2 = -1*(Decimal(rs3) + Decimal(ir_dataset[i][0]))/Decimal(rs1)

        if(iflen==16):
            m = lambda rsx: float('inf') if rsx > fields_dec_converter(16, hmaxnorm[0]) \
            else float('-inf') if rsx < fields_dec_converter(16, hmaxnorm[1]) \
            else rsx
            x1 = m(rs1)
            x2 = m(rs2)
            x3 = m(rs3)
        elif(iflen==32):
            x1 = struct.unpack('f', struct.pack('f', rs1))[0]
            x2 = struct.unpack('f', struct.pack('f', rs2))[0]
            x3 = struct.unpack('f', struct.pack('f', rs3))[0]
        elif(iflen==64):
            x1 = rs1
            x2 = rs2
            x3 = rs3

        if opcode in ['fadd','fsub','fmul','fdiv']:
            b8_comb.append((floatingPoint_tohex(iflen,float(rs1)),floatingPoint_tohex(iflen,float(rs2))))
        elif opcode in 'fsqrt':
            b8_comb.append((floatingPoint_tohex(iflen,float(rs2)),))
        elif opcode in ['fmadd','fnmadd','fmsub','fnmsub']:
            b8_comb.append((floatingPoint_tohex(iflen,float(rs1)),floatingPoint_tohex(iflen,float(rs2)),floatingPoint_tohex(iflen,float(rs3))))

    coverpoints = []
    k=0
    for c in b8_comb:
        for rm in range(5):
            cvpt = ""
            for x in range(1, ops+1):
#                        cvpt += 'rs'+str(x)+'_val=='+str(c[x-1]) # uncomment this if you want rs1_val instead of individual fields
                cvpt += (extract_fields(iflen,c[x-1],str(x)))
                cvpt += " and "
            cvpt =  sanitise(rm,cvpt,iflen,flen,ops,inxFlg)
            # cvpt += 'rm_val == '+str(rm)
            if inxFlg == True:
                cvpt += sgn_prefix(iflen,flen,inxFlg,ops,cvpt)
            else:
                cvpt += ' # '
            cvpt += ' # '
            for y in range(1, ops+1):
                cvpt += 'rs'+str(y)+'_val=='
                cvpt += num_explain(iflen, c[y-1]) + '(' + str(c[y-1]) + ')'
                if(y != ops):
                    cvpt += " and "
            cvpt += ir_dataset[k][1]
            coverpoints.append(cvpt)
        k=k+1

    mess='Generated'+ (' '*(5-len(str(len(coverpoints)))))+ str(len(coverpoints)) +' '+ \
    (str(16) if iflen == 16 else str(32) if iflen == 32 else str(64)) + '-bit coverpoints using Model B8 for '+opcode+' !'
    logger.debug(mess)
    coverpoints = comments_parser(coverpoints)

    return coverpoints

def ibm_b9(flen, iflen, opcode, ops, inxFlg=False):
    '''
    IBM Model B9 Definition:
            This model tests special patterns in the significands of the input operands. Each
            of the input operands should contain one of the following patterns (each
            sequence can be of length 0 up to the number of bits in the significand – the
            more interesting cases will be chosen).

            1. A sequence of leading zeroes
            2. A sequence of leading ones
            3. A sequence of trailing zeroes
            4. A sequence of trailing ones
            5. A small number of 1s as compared to 0s
            6. A small number of 0s as compared to 1s
            7. A "checkerboard" pattern (for example 00110011... or 011011011...)
            8. Long sequences of 1s
            9. Long sequences of 0s

    :param iflen: Size of the floating point source operands for the operation
    :param flen: Size of the floating point registers
    :param opcode: Opcode for which the coverpoints are to be generated
    :param ops: No. of Operands taken by the opcode

    :type iflen: int
    :type flen: int
    :type opcode: str
    :type ops: int

    Abstract Dataset Description:
            Operand1, Operand2 ∈ [A sequence of leading zeroes, A sequence of leading ones, A sequence of trailing zeroes, A sequence of trailing ones, A small number of 1s as compared to 0s, A small number of 0s as compared to 1s, A "checkerboard" pattern (for example 00110011... or 011011011...), Long sequences of 1s, Long sequences of 0s]

    Implementation:
            - The rs1 array is appended with the elements of flip types and then for each iteration, the respective sign, mantissa and exponent is computed.
            - A nested loop is initialized, assuming the rs1 mantissa as the base number and rs2 sign and rs2 exponent is obtained directly from the rs1 sign and rs1 exponent. Rs2 mantissa is calculated by adding the iteration number in the beginning of rs1 mantissa. This is done respectively for each repeating pattern.
            - The operand values are then passed into the extract_fields function to get individual fields in a floating point number (sign, exponent and mantissa).
            - Coverpoints are then appended with all rounding modes for that particular opcode.

    '''
    sanitise = get_sanitise_func(opcode)
    opcode = opcode.split('.')[0]
    if iflen == 16:
        flip_types = hzero + hone + hminsubnorm + hmaxsubnorm + hminnorm + hmaxnorm
        e_sz=5
    elif iflen == 32:
        flip_types = fzero + fone + fminsubnorm + fmaxsubnorm + fminnorm + fmaxnorm
        e_sz=8
    elif iflen == 64:
        flip_types = dzero + done + dminsubnorm + dmaxsubnorm + dminnorm + dmaxnorm
        e_sz=11

    rs1 = []
    b9_comb = []
    comment = []
    if ops == 2:
        for i in range(len(flip_types)):
            rs1.append(flip_types[i])
        for i in range(len(rs1)):
            bin_val = bin(int('1'+rs1[i][2:],16))[3:]
            rs1_sgn = bin_val[0]
            rs1_exp = bin_val[1:e_sz+1]
            rs1_man = bin_val[e_sz+1:]

            for j in range(len(rs1_man)):
                rs2_sgn = rs1_sgn
                rs2_exp = rs1_exp
                rs2_man = '0'*j + rs1_man[j:]                        # Leading 0s
                rs2 = fields_dec_converter(32,'0x'+hex(int('1'+rs2_sgn+rs2_exp+rs2_man,2))[3:])
                b9_comb.append((rs1[i],floatingPoint_tohex(iflen,rs2)))
                comment.append(' | Leading zeroes ---> rs2_man = '+rs2_man)
                b9_comb.append((floatingPoint_tohex(iflen,rs2),rs1[i]))
                comment.append(' | Leading zeroes ---> rs1_man = '+rs2_man)

                rs2_man = '1'*j + '0'*(len(rs1_man)-j)                        # Leading 1s
                rs2 = fields_dec_converter(32,'0x'+hex(int('1'+rs2_sgn+rs2_exp+rs2_man,2))[3:])
                b9_comb.append((rs1[i],floatingPoint_tohex(iflen,rs2)))
                comment.append(' | Leading ones ---> rs2_man = '+rs2_man)
                b9_comb.append((floatingPoint_tohex(iflen,rs2),rs1[i]))
                comment.append(' | Leading ones ---> rs1_man = '+rs2_man)

                rs2_man = rs1_man[0:j] + '0'*(len(rs1_man)-j)        # Trailing 0s
                rs2 = fields_dec_converter(32,'0x'+hex(int('1'+rs2_sgn+rs2_exp+rs2_man,2))[3:])
                b9_comb.append((rs1[i],floatingPoint_tohex(iflen,rs2)))
                comment.append(' | Trailing zeroes ---> rs2_man = '+rs2_man)
                b9_comb.append((floatingPoint_tohex(iflen,rs2),rs1[i]))
                comment.append(' | Trailing zeroes ---> rs1_man = '+rs2_man)

                rs2_man = '0'*j + '1'*(len(rs1_man)-j)        # Trailing 1s
                rs2 = fields_dec_converter(32,'0x'+hex(int('1'+rs2_sgn+rs2_exp+rs2_man,2))[3:])
                b9_comb.append((rs1[i],floatingPoint_tohex(iflen,rs2)))
                comment.append(' | Trailing ones ---> rs2_man = '+rs2_man)
                b9_comb.append((floatingPoint_tohex(iflen,rs2),rs1[i]))
                comment.append(' | Trailing ones ---> rs1_man = '+rs2_man)

            for j in range(len(rs1_man)-math.ceil(0.1*len(rs1_man)),len(rs1_man)):
                rs2_sgn = rs1_sgn
                rs2_exp = rs1_exp
                rs2_man = '1'*j + '0'*(len(rs1_man)-j)                        # Long sequence of 1s
                rs2 = fields_dec_converter(32,'0x'+hex(int('1'+rs2_sgn+rs2_exp+rs2_man,2))[3:])
                b9_comb.append((rs1[i],floatingPoint_tohex(iflen,rs2)))
                comment.append(' | Long sequence of ones ---> rs2_man = '+rs2_man)
                b9_comb.append((floatingPoint_tohex(iflen,rs2),rs1[i]))
                comment.append(' | Long sequence of ones ---> rs1_man = '+rs2_man)

                rs2_man = '0'*j + '1'*(len(rs1_man)-j)                        # Long sequence of 0s
                rs2 = fields_dec_converter(32,'0x'+hex(int('1'+rs2_sgn+rs2_exp+rs2_man,2))[3:])
                b9_comb.append((rs1[i],floatingPoint_tohex(iflen,rs2)))
                comment.append(' | Long sequence of zeroes ---> rs2_man = '+rs2_man)
                b9_comb.append((floatingPoint_tohex(iflen,rs2),rs1[i]))
                comment.append(' | Long sequence of zeroes ---> rs1_man = '+rs2_man)

            chkrbrd = ['011','110','0011','1100','0111','1000','010','101','0110','1001']
            for j in chkrbrd:
                rs2_sgn = rs1_sgn
                rs2_exp = rs1_exp
                rs2_man = j
                for k in range(math.ceil(len(rs1_man)/len(j))):
                    rs2_man += j
                rs2_man = rs2_man[0:iflen-e_sz-1]
                rs2 = fields_dec_converter(32,'0x'+hex(int('1'+rs2_sgn+rs2_exp+rs2_man,2))[3:])
                b9_comb.append((rs1[i],floatingPoint_tohex(iflen,rs2)))
                comment.append(' | Checkerboard pattern ---> rs2_man = '+rs2_man)
                b9_comb.append((floatingPoint_tohex(iflen,rs2),rs1[i]))
                comment.append(' | Checkerboard pattern ---> rs1_man = '+rs2_man)

    else:
        for i in range(len(flip_types)):
            rs1.append(flip_types[i])
        for i in range(len(rs1)):
            bin_val = bin(int('1'+rs1[i][2:],16))[3:]
            rs1_sgn = bin_val[0]
            rs1_exp = bin_val[1:e_sz+1]
            rs1_man = bin_val[e_sz+1:]

            if rs1_sgn != '1':
                for j in range(len(rs1_man)):
                    rs2_sgn = rs1_sgn
                    rs2_exp = rs1_exp
                    rs2_man = '0'*j + rs1_man[j:]                        # Leading 0s
                    rs2 = fields_dec_converter(32,'0x'+hex(int('1'+rs2_sgn+rs2_exp+rs2_man,2))[3:])
                    b9_comb.append((floatingPoint_tohex(iflen,rs2),))
                    comment.append(' | Leading zeroes ---> rs1_man = '+rs2_man)

                    rs2_man = '1'*j + '0'*(len(rs1_man)-j)                        # Leading 1s
                    rs2 = fields_dec_converter(32,'0x'+hex(int('1'+rs2_sgn+rs2_exp+rs2_man,2))[3:])
                    b9_comb.append((floatingPoint_tohex(iflen,rs2),))
                    comment.append(' | Leading ones ---> rs1_man = '+rs2_man)

                    rs2_man = rs1_man[0:j] + '0'*(len(rs1_man)-j)        # Trailing 0s
                    rs2 = fields_dec_converter(32,'0x'+hex(int('1'+rs2_sgn+rs2_exp+rs2_man,2))[3:])
                    b9_comb.append((floatingPoint_tohex(iflen,rs2),))
                    comment.append(' | Trailing zeroes ---> rs1_man = '+rs2_man)

                    rs2_man = '0'*j + '1'*(len(rs1_man)-j)        # Trailing 1s
                    rs2 = fields_dec_converter(32,'0x'+hex(int('1'+rs2_sgn+rs2_exp+rs2_man,2))[3:])
                    b9_comb.append((floatingPoint_tohex(iflen,rs2),))
                    comment.append(' | Trailing ones ---> rs1_man = '+rs2_man)
        rs1_sgn = '0'
        for j in range(iflen-e_sz-1-math.ceil(0.1*(iflen-e_sz-1)), iflen-e_sz-1):
            rs2_sgn = rs1_sgn
            rs2_exp = rs1_exp
            rs2_man = '1'*j + '0'*(len(rs1_man)-j)                        # Long sequence of 1s
            rs2 = fields_dec_converter(32,'0x'+hex(int('1'+rs2_sgn+rs2_exp+rs2_man,2))[3:])
            b9_comb.append((floatingPoint_tohex(iflen,rs2),))
            comment.append(' | Long sequence of ones ---> rs1_man = '+rs2_man)

            rs2_man = '0'*j + '1'*(len(rs1_man)-j)                        # Long sequence of 0s
            rs2 = fields_dec_converter(32,'0x'+hex(int('1'+rs2_sgn+rs2_exp+rs2_man,2))[3:])
            b9_comb.append((floatingPoint_tohex(iflen,rs2),))
            comment.append(' | Long sequence of zeroes ---> rs1_man = '+rs2_man)

        chkrbrd = ['011','110','0011','1100','0111','1000','010','101','0110','1001']
        for j in chkrbrd:
            rs2_sgn = rs1_sgn
            rs2_exp = rs1_exp
            rs2_man = j
            for k in range(math.ceil(len(rs1_man)/len(j))):
                rs2_man += j
            rs2_man = rs2_man[0:iflen-e_sz-1]
            rs2 = fields_dec_converter(32,'0x'+hex(int('1'+rs2_sgn+rs2_exp+rs2_man,2))[3:])
            b9_comb.append((floatingPoint_tohex(iflen,rs2),))
            comment.append(' | Checkerboard pattern ---> rs1_man = '+rs2_man)

    coverpoints = []
    k = 0
    for c in b9_comb:
        cvpt = ""
        for x in range(1, ops+1):
#                    cvpt += 'rs'+str(x)+'_val=='+str(c[x-1]) # uncomment this if you want rs1_val instead of individual fields
            cvpt += (extract_fields(iflen,c[x-1],str(x)))
            cvpt += " and "
        # cvpt += 'rm_val == 0'
        cvpt = sanitise(0,cvpt,iflen,flen,ops,inxFlg)
        if inxFlg == True:
            cvpt += sgn_prefix(iflen,flen,inxFlg,ops,cvpt)
        else:
            cvpt += ' # '
        cvpt += ' # '
        for y in range(1, ops+1):
            cvpt += 'rs'+str(y)+'_val=='
            cvpt += num_explain(iflen, c[y-1]) + '(' + str(c[y-1]) + ')'
            if(y != ops):
                cvpt += " and "
        cvpt += comment[k]
        coverpoints.append(cvpt)
        k += 1

    mess='Generated'+ (' '*(5-len(str(len(coverpoints)))))+ str(len(coverpoints)) +' '+ \
    (str(16) if iflen == 16 else str(32) if iflen == 32 else str(64)) + '-bit coverpoints using Model B9 for '+opcode+' !'
    logger.debug(mess)
    coverpoints = comments_parser(coverpoints)

    return coverpoints

def ibm_b10(flen, iflen, opcode, ops, inxFlg=False, N=-1, seed=-1):
    '''
    IBM Model B10 Definition:
            This model tests every possible value for a shift between the input operands.
            1.  A value smaller than -(p + 4)
            2. All the values in the range [-(p + 4) , (p + 4)]
            3. A value larger than (p + 4)

    :param iflen: Size of the floating point source operands for the operation
    :param flen: Size of the floating point registers
    :param opcode: Opcode for which the coverpoints are to be generated
    :param ops: No. of Operands taken by the opcode
    :param N: No. of sets of coverpoints to be generated. (Predefined to -1. Set to 2)
    :param seed: Initial seed value of the random library. (Predefined to -1. Actual value is set with respect to the opcode calling the function)

    :type iflen: int
    :type flen: int
    :type opcode: str
    :type ops: int
    :type N: int
    :param seed: int

    Abstract Dataset Description:
            Operand1 = [Random Number]
            Operand2 = [A value smaller than -(op1.exp+4), All values in the range [-(op1.exp+4), (op1.exp+4)], A value larger than +(op1.exp+4)]

    Implementation:
            - The exponent values of operand 1 and operand 2 obey the shift defined above. The mantissa value is randomly chosen and appended with the exponent derived.
            - Simultaneously, we convert these numbers into their corresponding IEEE754 floating point formats.
            - These operand values are then passed into the extract_fields function to get individual fields in a floating point number (sign, exponent and mantissa).
            - Coverpoints are then appended with rounding mode ‘0’ for that particular opcode.

    '''
    sanitise = get_sanitise_func(opcode)
    opcode = opcode.split('.')[0]

    if iflen == 16:
        ieee754_maxnorm = float.hex(fields_dec_converter(16, hmaxnorm[0]))
        maxnum = float.fromhex(ieee754_maxnorm)
        exp_max = 31
    elif iflen == 32:
        ieee754_maxnorm = '0x1.7fffffp+127'
        maxnum = float.fromhex(ieee754_maxnorm)
        exp_max = 255
    elif iflen == 64:
        maxdec = '1.7976931348623157e+308'
        maxnum = float.fromhex('0x1.fffffffffffffp+1023')
        exp_max = 1023

    if N == -1:
        N = 2

    if seed == -1:
        if opcode in 'fadd':
            random.seed(0)
        elif opcode in 'fsub':
            random.seed(1)
    else:
        random.seed(seed)

    b10_comb = []
    comment = []
    for i in range(1,N):
        rs1 = random.uniform(1,maxnum/1000)
        rs2 = random.uniform(1,maxnum/1000)
        rs1_exp = str(rs1).split('e')[1]

        rs2_exp = -1*random.randrange(int(math.log(pow(10,int(rs1_exp)),2))+4, exp_max)
        rs2_num = str(rs2).split('e')[0] + 'e' + str(int(math.log(pow(2,int(rs2_exp)),10)))
        b10_comb.append((floatingPoint_tohex(iflen,float(rs1)),floatingPoint_tohex(iflen,float(rs2_num))))
        comment.append(' | Exponent = '+ str(rs2_exp) + ' --> A value smaller than -(p + 4)')

        for j in range(-(int(math.log(pow(10,int(rs1_exp)),2))+4),+(int(math.log(pow(10,int(rs1_exp)),2))+4)):
            rs2_num = str(rs2).split('e')[0] + 'e' + str(int(math.log(pow(2,int(j)),10)))
            b10_comb.append((floatingPoint_tohex(iflen,float(rs1)),floatingPoint_tohex(iflen,float(rs2_num))))
            comment.append(' | Exponent = '+ str(j) + ' --> Values in the range [-(p + 4) , (p + 4)]')

        rs2_exp = random.randrange(int(math.log(pow(10,int(rs1_exp)),2))+4, exp_max)
        rs2_num = str(rs2).split('e')[0] + 'e' + str(int(math.log(pow(2,int(rs2_exp)),10)))
        b10_comb.append((floatingPoint_tohex(iflen,float(rs1)),floatingPoint_tohex(iflen,float(rs2_num))))
        comment.append(' | Exponent = '+ str(rs2_exp) + ' --> A value larger than (p + 4)')

    coverpoints = []
    k = 0
    for c in b10_comb:
        cvpt = ""
        for x in range(1, ops+1):
#                    cvpt += 'rs'+str(x)+'_val=='+str(c[x-1]) # uncomment this if you want rs1_val instead of individual fields
            cvpt += (extract_fields(iflen,c[x-1],str(x)))
            cvpt += " and "
        cvpt = sanitise(0,cvpt,iflen,flen,ops,inxFlg)
        # cvpt += 'rm_val == 0'
        if inxFlg == True:
            cvpt += sgn_prefix(iflen,flen,inxFlg,ops,cvpt)
        else:
            cvpt += ' # '
        cvpt += ' # '
        for y in range(1, ops+1):
            cvpt += 'rs'+str(y)+'_val=='
            cvpt += num_explain(iflen, c[y-1]) + '(' + str(c[y-1]) + ')'
            if(y != ops):
                cvpt += " and "
        cvpt += comment[k]
        coverpoints.append(cvpt)
        k += 1

    mess='Generated'+ (' '*(5-len(str(len(coverpoints)))))+ str(len(coverpoints)) +' '+ \
    (str(16) if iflen == 16 else str(32) if iflen == 32 else str(64)) + '-bit coverpoints using Model B10 for '+opcode+' !'
    logger.debug(mess)
    coverpoints = comments_parser(coverpoints)

    return coverpoints

def ibm_b11(flen, iflen, opcode, ops, inxFlg=False, N=-1, seed=-1):
    '''
    IBM Model B11 Definition:
            In this model we test the combination of different shift values between the
            inputs, with special patterns in the significands of the inputs.
            Significands of Input1 and Input2: as in model (B9) "Special Significands on
            Inputs"

            Shift: as in model (B10) "Shift - Add"
            We test both effective operations: addition and subtraction.

    :param iflen: Size of the floating point source operands for the operation
    :param flen: Size of the floating point registers
    :param opcode: Opcode for which the coverpoints are to be generated
    :param ops: No. of Operands taken by the opcode
    :param seed: Initial seed value of the random library. (Predefined to -1. Actual value is set with respect to the opcode calling the function)

    :type iflen: int
    :type flen: int
    :type opcode: str
    :type ops: int
    :param seed: int

    Abstract Dataset Description:
            Operand1, Operand2 ∈ Abstract Dataset in B9 + Abstract Dataset in B10

    Implementation:
            - A culmination of the techniques used in the implementations of Model B9 and Model B10 are used to form the dataset.
            - The operand values are then passed into the extract_fields function to get individual fields in a floating point number (sign, exponent and mantissa).
            - Coverpoints are then appended with all rounding modes for that particular opcode.

    '''
    sanitise = get_sanitise_func(opcode)
    opcode = opcode.split('.')[0]

    if iflen == 16:
        flip_types = hzero + hone + hminsubnorm + hmaxsubnorm + hminnorm + hmaxnorm
        e_sz=5
        exp_max = 255
    elif iflen == 32:
        flip_types = fzero + fone + fminsubnorm + fmaxsubnorm + fminnorm + fmaxnorm
        e_sz=8
        exp_max = 255
    elif iflen == 64:
        flip_types = dzero + done + dminsubnorm + dmaxsubnorm + dminnorm + dmaxnorm
        e_sz=11
        exp_max = 1023

    if seed == -1:
        if opcode in 'fadd':
            random.seed(0)
        elif opcode in 'fsub':
            random.seed(1)
    else:
        random.seed(seed)

    rs1 = []
    b11_comb = []
    comment = []
    if ops == 2:
        for i in range(len(flip_types)):
            rs1.append(flip_types[i])
        for i in range(len(rs1)):
            bin_val = bin(int('1'+rs1[i][2:],16))[3:]
            rs1_sgn = bin_val[0]
            rs1_exp = bin_val[1:e_sz+1]
            rs1_man = bin_val[e_sz+1:]

            if int(rs1_exp,2) < 4: rs2_exp = -127
            else : rs2_exp = random.randrange(-127,int(rs1_exp,2)-131)
            comment_str = ' | Exponent = '+ str(rs2_exp) + ' --> A value smaller than (p - 4)'
            rs2_exp += 127
            if iflen == 16:  rs2_exp = '{:05b}'.format(rs2_exp)
            elif iflen == 32: rs2_exp = '{:08b}'.format(rs2_exp)
            elif iflen == 64: rs2_exp = '{:011b}'.format(rs2_exp)
            for j in range(len(rs1_man)):
                rs2_sgn = rs1_sgn
                rs2_man = '0'*j + rs1_man[j:]                        # Leading 0s
                rs2 = fields_dec_converter(iflen,'0x'+hex(int('1'+rs2_sgn+rs2_exp+rs2_man,2))[3:])
                b11_comb.append((rs1[i],floatingPoint_tohex(iflen,rs2)))
                comment.append(comment_str + ' | Leading zeroes ---> rs2_man = '+rs2_man)
                b11_comb.append((floatingPoint_tohex(iflen,rs2),rs1[i]))
                comment.append(comment_str + ' | Leading zeroes ---> rs1_man = '+rs2_man)

                rs2_man = '1'*j + '0'*(len(rs1_man)-j)                        # Leading 1s
                rs2 = fields_dec_converter(iflen,'0x'+hex(int('1'+rs2_sgn+rs2_exp+rs2_man,2))[3:])
                b11_comb.append((rs1[i],floatingPoint_tohex(iflen,rs2)))
                comment.append(comment_str + ' | Leading ones ---> rs2_man = '+rs2_man)
                b11_comb.append((floatingPoint_tohex(iflen,rs2),rs1[i]))
                comment.append(comment_str + ' | Leading ones ---> rs1_man = '+rs2_man)

                rs2_man = rs1_man[0:j] + '0'*(len(rs1_man)-j)        # Trailing 0s
                rs2 = fields_dec_converter(iflen,'0x'+hex(int('1'+rs2_sgn+rs2_exp+rs2_man,2))[3:])
                b11_comb.append((rs1[i],floatingPoint_tohex(iflen,rs2)))
                comment.append(comment_str + ' | Trailing zeroes ---> rs2_man = '+rs2_man)
                b11_comb.append((floatingPoint_tohex(iflen,rs2),rs1[i]))
                comment.append(comment_str + ' | Trailing zeroes ---> rs1_man = '+rs2_man)

                rs2_man = '0'*j + '1'*(len(rs1_man)-j)        # Trailing 1s
                rs2 = fields_dec_converter(iflen,'0x'+hex(int('1'+rs2_sgn+rs2_exp+rs2_man,2))[3:])
                b11_comb.append((rs1[i],floatingPoint_tohex(iflen,rs2)))
                comment.append(comment_str + ' | Trailing ones ---> rs2_man = '+rs2_man)
                b11_comb.append((floatingPoint_tohex(iflen,rs2),rs1[i]))
                comment.append(comment_str + ' | Trailing ones ---> rs1_man = '+rs2_man)

            for j in range(len(rs1_man)-math.ceil(0.1*len(rs1_man)),len(rs1_man)):
                rs2_sgn = rs1_sgn
                rs2_exp = rs1_exp
                rs2_man = '1'*j + '0'*(len(rs1_man)-j)                        # Long sequence of 1s
                rs2 = fields_dec_converter(iflen,'0x'+hex(int('1'+rs2_sgn+rs2_exp+rs2_man,2))[3:])
                b11_comb.append((rs1[i],floatingPoint_tohex(iflen,rs2)))
                comment.append(comment_str + ' | Long sequence of ones ---> rs2_man = '+rs2_man)
                b11_comb.append((floatingPoint_tohex(iflen,rs2),rs1[i]))
                comment.append(comment_str + ' | Long sequence of ones ---> rs1_man = '+rs2_man)

                rs2_man = '0'*j + '1'*(len(rs1_man)-j)                        # Long sequence of 0s
                rs2 = fields_dec_converter(iflen,'0x'+hex(int('1'+rs2_sgn+rs2_exp+rs2_man,2))[3:])
                b11_comb.append((rs1[i],floatingPoint_tohex(iflen,rs2)))
                comment.append(comment_str + ' | Long sequence of zeroes ---> rs2_man = '+rs2_man)
                b11_comb.append((floatingPoint_tohex(iflen,rs2),rs1[i]))
                comment.append(comment_str + ' | Long sequence of zeroes ---> rs1_man = '+rs2_man)

            chkrbrd = ['011','110','0011','1100','0111','1000','010','101','0110','1001']
            for j in chkrbrd:
                rs2_sgn = rs1_sgn
                rs2_exp = rs1_exp
                rs2_man = j
                for k in range(math.ceil(len(rs1_man)/len(j))):
                    rs2_man += j
                rs2_man = rs2_man[0:iflen-e_sz-1]
                rs2 = fields_dec_converter(iflen,'0x'+hex(int('1'+rs2_sgn+rs2_exp+rs2_man,2))[3:])
                b11_comb.append((rs1[i],floatingPoint_tohex(iflen,rs2)))
                comment.append(comment_str + ' | Checkerboard pattern ---> rs2_man = '+rs2_man)
                b11_comb.append((floatingPoint_tohex(iflen,rs2),rs1[i]))
                comment.append(comment_str + ' | Checkerboard pattern ---> rs1_man = '+rs2_man)

            if int(rs1_exp,2) >= 250: rs2_exp = 127
            else : rs2_exp = random.randrange(int(rs1_exp,2)-123,127)
            comment_str = ' | Exponent = '+ str(rs2_exp) + ' --> A value greater than (p + 4)'
            rs2_exp += 127
            if iflen == 16:  rs2_exp = '{:05b}'.format(rs2_exp)
            elif iflen == 32: rs2_exp = '{:08b}'.format(rs2_exp)
            elif iflen == 64: rs2_exp = '{:011b}'.format(rs2_exp)
            for j in range(len(rs1_man)):
                rs2_sgn = rs1_sgn
                rs2_man = '0'*j + rs1_man[j:]                        # Leading 0s
                rs2 = fields_dec_converter(iflen,'0x'+hex(int('1'+rs2_sgn+rs2_exp+rs2_man,2))[3:])
                b11_comb.append((rs1[i],floatingPoint_tohex(iflen,rs2)))
                comment.append(comment_str + ' | Leading zeroes ---> rs2_man = '+rs2_man)
                b11_comb.append((floatingPoint_tohex(iflen,rs2),rs1[i]))
                comment.append(comment_str + ' | Leading zeroes ---> rs1_man = '+rs2_man)

                rs2_man = '1'*j + '0'*(len(rs1_man)-j)                        # Leading 1s
                rs2 = fields_dec_converter(iflen,'0x'+hex(int('1'+rs2_sgn+rs2_exp+rs2_man,2))[3:])
                b11_comb.append((rs1[i],floatingPoint_tohex(iflen,rs2)))
                comment.append(comment_str + ' | Leading ones ---> rs2_man = '+rs2_man)
                b11_comb.append((floatingPoint_tohex(iflen,rs2),rs1[i]))
                comment.append(comment_str + ' | Leading ones ---> rs1_man = '+rs2_man)

                rs2_man = rs1_man[0:j] + '0'*(len(rs1_man)-j)        # Trailing 0s
                rs2 = fields_dec_converter(iflen,'0x'+hex(int('1'+rs2_sgn+rs2_exp+rs2_man,2))[3:])
                b11_comb.append((rs1[i],floatingPoint_tohex(iflen,rs2)))
                comment.append(comment_str + ' | Trailing zeroes ---> rs2_man = '+rs2_man)
                b11_comb.append((floatingPoint_tohex(iflen,rs2),rs1[i]))
                comment.append(comment_str + ' | Trailing zeroes ---> rs1_man = '+rs2_man)

                rs2_man = '0'*j + '1'*(len(rs1_man)-j)        # Trailing 1s
                rs2 = fields_dec_converter(iflen,'0x'+hex(int('1'+rs2_sgn+rs2_exp+rs2_man,2))[3:])
                b11_comb.append((rs1[i],floatingPoint_tohex(iflen,rs2)))
                comment.append(comment_str + ' | Trailing ones ---> rs2_man = '+rs2_man)
                b11_comb.append((floatingPoint_tohex(iflen,rs2),rs1[i]))
                comment.append(comment_str + ' | Trailing ones ---> rs1_man = '+rs2_man)

            for j in range(len(rs1_man)-math.ceil(0.1*len(rs1_man)),len(rs1_man)):
                rs2_sgn = rs1_sgn
                rs2_exp = rs1_exp
                rs2_man = '1'*j + '0'*(len(rs1_man)-j)                        # Long sequence of 1s
                rs2 = fields_dec_converter(iflen,'0x'+hex(int('1'+rs2_sgn+rs2_exp+rs2_man,2))[3:])
                b11_comb.append((rs1[i],floatingPoint_tohex(iflen,rs2)))
                comment.append(comment_str + ' | Long sequence of ones ---> rs2_man = '+rs2_man)
                b11_comb.append((floatingPoint_tohex(iflen,rs2),rs1[i]))
                comment.append(comment_str + ' | Long sequence of ones ---> rs1_man = '+rs2_man)

                rs2_man = '0'*j + '1'*(len(rs1_man)-j)                        # Long sequence of 0s
                rs2 = fields_dec_converter(iflen,'0x'+hex(int('1'+rs2_sgn+rs2_exp+rs2_man,2))[3:])
                b11_comb.append((rs1[i],floatingPoint_tohex(iflen,rs2)))
                comment.append(comment_str + ' | Long sequence of zeroes ---> rs2_man = '+rs2_man)
                b11_comb.append((floatingPoint_tohex(iflen,rs2),rs1[i]))
                comment.append(comment_str + ' | Long sequence of zeroes ---> rs1_man = '+rs2_man)

            chkrbrd = ['011','110','0011','1100','0111','1000','010','101','0110','1001']
            for j in chkrbrd:
                rs2_sgn = rs1_sgn
                rs2_exp = rs1_exp
                rs2_man = j
                for k in range(math.ceil(len(rs1_man)/len(j))):
                    rs2_man += j
                rs2_man = rs2_man[0:iflen-e_sz-1]
                rs2 = fields_dec_converter(iflen,'0x'+hex(int('1'+rs2_sgn+rs2_exp+rs2_man,2))[3:])
                b11_comb.append((rs1[i],floatingPoint_tohex(iflen,rs2)))
                comment.append(comment_str + ' | Checkerboard pattern ---> rs2_man = '+rs2_man)
                b11_comb.append((floatingPoint_tohex(iflen,rs2),rs1[i]))
                comment.append(comment_str + ' | Checkerboard pattern ---> rs1_man = '+rs2_man)

            ul = int(rs1_exp,2)-123
            ll = int(rs1_exp,2)-131
            if int(rs1_exp,2) >= 250: ul = 127
            if int(rs1_exp,2) < 4: ll = -127
            for expval in range (ll, ul):
                rs2_exp = expval
                comment_str = ' | Exponent = '+ str(rs2_exp) + ' --> Values in the range (p - 4) to (p + 4)'
                rs2_exp += 127
                if iflen == 16:  rs2_exp = '{:05b}'.format(rs2_exp)
                elif iflen == 32: rs2_exp = '{:08b}'.format(rs2_exp)
                elif iflen == 64: rs2_exp = '{:011b}'.format(rs2_exp)
                for j in range(len(rs1_man)):
                    rs2_sgn = rs1_sgn
                    rs2_man = '0'*j + rs1_man[j:]                        # Leading 0s
                    rs2 = fields_dec_converter(iflen,'0x'+hex(int('1'+rs2_sgn+rs2_exp+rs2_man,2))[3:])
                    b11_comb.append((rs1[i],floatingPoint_tohex(iflen,rs2)))
                    comment.append(comment_str + ' | Leading zeroes ---> rs2_man = '+rs2_man)
                    b11_comb.append((floatingPoint_tohex(iflen,rs2),rs1[i]))
                    comment.append(comment_str + ' | Leading zeroes ---> rs1_man = '+rs2_man)

                    rs2_man = '1'*j + '0'*(len(rs1_man)-j)                        # Leading 1s
                    rs2 = fields_dec_converter(iflen,'0x'+hex(int('1'+rs2_sgn+rs2_exp+rs2_man,2))[3:])
                    b11_comb.append((rs1[i],floatingPoint_tohex(iflen,rs2)))
                    comment.append(comment_str + ' | Leading ones ---> rs2_man = '+rs2_man)
                    b11_comb.append((floatingPoint_tohex(iflen,rs2),rs1[i]))
                    comment.append(comment_str + ' | Leading ones ---> rs1_man = '+rs2_man)

                    rs2_man = rs1_man[0:j] + '0'*(len(rs1_man)-j)        # Trailing 0s
                    rs2 = fields_dec_converter(iflen,'0x'+hex(int('1'+rs2_sgn+rs2_exp+rs2_man,2))[3:])
                    b11_comb.append((rs1[i],floatingPoint_tohex(iflen,rs2)))
                    comment.append(comment_str + ' | Trailing zeroes ---> rs2_man = '+rs2_man)
                    b11_comb.append((floatingPoint_tohex(iflen,rs2),rs1[i]))
                    comment.append(comment_str + ' | Trailing zeroes ---> rs1_man = '+rs2_man)

                    rs2_man = '0'*j + '1'*(len(rs1_man)-j)        # Trailing 1s
                    rs2 = fields_dec_converter(iflen,'0x'+hex(int('1'+rs2_sgn+rs2_exp+rs2_man,2))[3:])
                    b11_comb.append((rs1[i],floatingPoint_tohex(iflen,rs2)))
                    comment.append(comment_str + ' | Trailing ones ---> rs2_man = '+rs2_man)
                    b11_comb.append((floatingPoint_tohex(iflen,rs2),rs1[i]))
                    comment.append(comment_str + ' | Trailing ones ---> rs1_man = '+rs2_man)

                for j in range(len(rs1_man)-math.ceil(0.1*len(rs1_man)),len(rs1_man)):
                    rs2_sgn = rs1_sgn
                    rs2_exp = rs1_exp
                    rs2_man = '1'*j + '0'*(len(rs1_man)-j)                        # Long sequence of 1s
                    rs2 = fields_dec_converter(iflen,'0x'+hex(int('1'+rs2_sgn+rs2_exp+rs2_man,2))[3:])
                    b11_comb.append((rs1[i],floatingPoint_tohex(iflen,rs2)))
                    comment.append(comment_str + ' | Long sequence of ones ---> rs2_man = '+rs2_man)
                    b11_comb.append((floatingPoint_tohex(iflen,rs2),rs1[i]))
                    comment.append(comment_str + ' | Long sequence of ones ---> rs1_man = '+rs2_man)

                    rs2_man = '0'*j + '1'*(len(rs1_man)-j)                        # Long sequence of 0s
                    rs2 = fields_dec_converter(iflen,'0x'+hex(int('1'+rs2_sgn+rs2_exp+rs2_man,2))[3:])
                    b11_comb.append((rs1[i],floatingPoint_tohex(iflen,rs2)))
                    comment.append(comment_str + ' | Long sequence of zeroes ---> rs2_man = '+rs2_man)
                    b11_comb.append((floatingPoint_tohex(iflen,rs2),rs1[i]))
                    comment.append(comment_str + ' | Long sequence of zeroes ---> rs1_man = '+rs2_man)

                chkrbrd = ['011','110','0011','1100','0111','1000','010','101','0110','1001']
                for j in chkrbrd:
                    rs2_sgn = rs1_sgn
                    rs2_exp = rs1_exp
                    rs2_man = j
                    for k in range(math.ceil(len(rs1_man)/len(j))):
                        rs2_man += j
                    rs2_man = rs2_man[0:iflen-e_sz-1]
                    rs2 = fields_dec_converter(iflen,'0x'+hex(int('1'+rs2_sgn+rs2_exp+rs2_man,2))[3:])
                    b11_comb.append((rs1[i],floatingPoint_tohex(iflen,rs2)))
                    comment.append(comment_str + ' | Checkerboard pattern ---> rs2_man = '+rs2_man)
                    b11_comb.append((floatingPoint_tohex(iflen,rs2),rs1[i]))
                    comment.append(comment_str + ' | Checkerboard pattern ---> rs1_man = '+rs2_man)

    coverpoints = []
    k = 0
    for c in b11_comb:
        cvpt = ""
        for x in range(1, ops+1):
#                    cvpt += 'rs'+str(x)+'_val=='+str(c[x-1]) # uncomment this if you want rs1_val instead of individual fields
            cvpt += (extract_fields(iflen,c[x-1],str(x)))
            cvpt += " and "
        # cvpt += 'rm_val == 0'
        cvpt = sanitise(0,cvpt,iflen,flen,ops,inxFlg)
        if inxFlg == True:
            cvpt += sgn_prefix(iflen,flen,inxFlg,ops,cvpt)
        else:
            cvpt += ' # '
        cvpt += ' # '
        for y in range(1, ops+1):
            cvpt += 'rs'+str(y)+'_val=='
            cvpt += num_explain(iflen, c[y-1]) + '(' + str(c[y-1]) + ')'
            if(y != ops):
                cvpt += " and "
        cvpt += comment[k]
        coverpoints.append(cvpt)
        k += 1

    mess='Generated'+ (' '*(5-len(str(len(coverpoints)))))+ str(len(coverpoints)) +' '+ \
    (str(16) if iflen == 16 else str(32) if iflen == 32 else str(64)) + '-bit coverpoints using Model B11 for '+opcode+' !'
    logger.debug(mess)
    coverpoints = comments_parser(coverpoints)

    return coverpoints

def ibm_b12(flen, iflen, opcode, ops, inxFlg=False, seed=-1):
    '''
    IBM Model B12 Definition:
            This model tests every possible value for cancellation.
            For the difference between the exponent of the intermediate result and the
            maximum between the exponents of the inputs, test all values in the range:
            [-p, +1].

    :param iflen: Size of the floating point source operands for the operation
    :param flen: Size of the floating point registers
    :param opcode: Opcode for which the coverpoints are to be generated
    :param ops: No. of Operands taken by the opcode
    :param seed: Initial seed value of the random library. (Predefined to -1. Actual value is set with respect to the opcode calling the function)

    :type iflen: int
    :type flen: int
    :type opcode: str
    :type ops: int
    :param seed: int

    Abstract Dataset Description:
            Intermediate Result - Operand.Exp ∈ [-p, +1]
            Operand1 {operation} Operand2 = Intermediate Results

    Implementation:
            - The exponent values of operand 1 and operand 2 obey the shift defined above. The mantissa value is randomly chosen and appended with the exponent derived.
            - Simultaneously, we convert these numbers into their corresponding IEEE754 floating point formats.
            - These operand values are then passed into the extract_fields function to get individual fields in a floating point number (sign, exponent and mantissa).
            - Coverpoints are then appended with rounding mode ‘0’ for that particular opcode.

    '''
    sanitise = get_sanitise_func(opcode)

    opcode = opcode.split('.')[0]
    getcontext().prec = 40
    if iflen == 16:
        ieee754_maxnorm = float.hex(fields_dec_converter(16, hmaxnorm[0]))
        maxnum = float.fromhex(ieee754_maxnorm)
        ieee754_minsubnorm = float.hex(fields_dec_converter(16, hminsubnorm[0]))
        minsubnorm = float.fromhex(ieee754_minsubnorm)
        ieee754_maxsubnorm = float.hex(fields_dec_converter(16, hmaxsubnorm[0]))
        maxsubnorm = float.fromhex(ieee754_maxsubnorm)
    elif iflen == 32:
        ieee754_maxnorm = '0x1.7fffffp+127'
        maxnum = float.fromhex(ieee754_maxnorm)
        ieee754_minsubnorm = '0x0.000001p-126'
        minsubnorm = float.fromhex(ieee754_minsubnorm)
        ieee754_maxsubnorm = '0x0.7fffffp-126'
        maxsubnorm = float.fromhex(ieee754_maxsubnorm)

    elif iflen == 64:
        ieee754_maxnorm = '0x1.fffffffffffffp+1023'
        maxnum = float.fromhex(ieee754_maxnorm)
        ieee754_minsubnorm = '0x0.0000000000001p-1022'
        minsubnorm = float.fromhex(ieee754_minsubnorm)
        ieee754_maxsubnorm = '0x0.fffffffffffffp-1022'
        maxsubnorm = float.fromhex(ieee754_maxsubnorm)

    if seed == -1:
        if opcode in 'fadd':
            random.seed(0)
        elif opcode in 'fsub':
            random.seed(1)
    else:
        random.seed(seed)

    b12_comb = []

    for i in range(50):
        if opcode in 'fadd': rs1 = -1*random.uniform(minsubnorm,maxnum)
        elif opcode in 'fsub': rs1 = random.uniform(minsubnorm,maxnum)
        ir = random.uniform(1,maxnum)
        if opcode in 'fadd':
            if iflen == 16 or iflen == 32:
                rs2 = ir - rs1
            elif iflen == 64:
                rs2 = Decimal(ir) - Decimal(rs1)
        elif opcode in 'fsub':
            if iflen == 16 or iflen == 32:
                rs2 = rs1 - ir
            elif iflen == 64:
                rs2 = Decimal(rs1) - Decimal(ir)

        if(iflen==16):
            m = lambda rsx: float('inf') if rsx > fields_dec_converter(16, hmaxnorm[0]) \
            else float('-inf') if rsx < fields_dec_converter(16, hmaxnorm[1]) \
            else rsx
            x1 = m(rs1)
            x2 = m(rs2)
        elif(iflen==32):
            x1 = struct.unpack('f', struct.pack('f', rs1))[0]
            x2 = struct.unpack('f', struct.pack('f', rs2))[0]
        elif(iflen==64):
            x1 = rs1
            x2 = rs2

        if opcode in ['fadd','fsub']:
            b12_comb.append((floatingPoint_tohex(iflen,float(rs1)),floatingPoint_tohex(iflen,float(rs2))))

    coverpoints = []
    comment = ' | Add: Cancellation'
    for c in b12_comb:
        cvpt = ""
        for x in range(1, ops+1):
#                    cvpt += 'rs'+str(x)+'_val=='+str(c[x-1]) # uncomment this if you want rs1_val instead of individual fields
            cvpt += (extract_fields(iflen,c[x-1],str(x)))
            cvpt += " and "
        cvpt = sanitise(0,cvpt,iflen,flen,ops,inxFlg)
        # cvpt += 'rm_val == 0'
        if inxFlg == True:
            cvpt += sgn_prefix(iflen,flen,inxFlg,ops,cvpt)
        else:
            cvpt += ' # '
        cvpt += ' # '
        for y in range(1, 3):
            cvpt += 'rs'+str(y)+'_val=='
            cvpt += num_explain(iflen, c[y-1]) + '(' + str(c[y-1]) + ')'
            if(y != ops):
                cvpt += " and "
        cvpt += comment
        coverpoints.append(cvpt)

    mess='Generated'+ (' '*(5-len(str(len(coverpoints)))))+ str(len(coverpoints)) +' '+ \
    (str(16) if iflen == 16 else str(32) if iflen == 32 else str(64)) + '-bit coverpoints using Model B12 for '+opcode+' !'
    logger.debug(mess)
    coverpoints = comments_parser(coverpoints)

    return coverpoints

def ibm_b13(flen, iflen, opcode, ops, inxFlg=False, seed=-1):
    '''
    IBM Model B13 Definition:
            This model tests all combinations of cancellation values as in model (B12), with
            all possible unbiased exponent values of subnormal results.

    :param iflen: Size of the floating point source operands for the operation
    :param flen: Size of the floating point registers
    :param opcode: Opcode for which the coverpoints are to be generated
    :param ops: No. of Operands taken by the opcode
    :param seed: Initial seed value of the random library. (Predefined to -1. Actual value is set with respect to the opcode calling the function)

    :type iflen: int
    :type flen: int
    :type opcode: str
    :type ops: int
    :param seed: int

    Abstract Dataset Description:
            Intermediate Result - Operand.Exp ∈ [-p, +1] (The exponent for the intermediate result is chosen such that it is a subnormal number)
            Operand1 {operation} Operand2 = Intermediate Results

    Implementation:
            - The implementation procedure for Model B12 is repeated with a revised exponent range as defined above.
            - The operand values are then passed into the extract_fields function to get individual fields in a floating point number (sign, exponent and mantissa).
            - Coverpoints are then appended with all rounding modes for that particular opcode.

    '''
    sanitise = get_sanitise_func(opcode)

    opcode = opcode.split('.')[0]
    getcontext().prec = 40
    if iflen == 16:
        ieee754_maxnorm = float.hex(fields_dec_converter(16, hmaxnorm[0]))
        maxnum = float.fromhex(ieee754_maxnorm)
        ieee754_minsubnorm = float.hex(fields_dec_converter(16, hminsubnorm[0]))
        minsubnorm = float.fromhex(ieee754_minsubnorm)
        ieee754_maxsubnorm = float.hex(fields_dec_converter(16, hmaxsubnorm[0]))
        maxsubnorm = float.fromhex(ieee754_maxsubnorm)
    elif iflen == 32:
        ieee754_maxnorm = '0x1.7fffffp+127'
        maxnum = float.fromhex(ieee754_maxnorm)
        ieee754_minsubnorm = '0x0.000001p-126'
        minsubnorm = float.fromhex(ieee754_minsubnorm)
        ieee754_maxsubnorm = '0x0.7fffffp-126'
        maxsubnorm = float.fromhex(ieee754_maxsubnorm)

    elif iflen == 64:
        ieee754_maxnorm = '0x1.fffffffffffffp+1023'
        maxnum = float.fromhex(ieee754_maxnorm)
        ieee754_minsubnorm = '0x0.0000000000001p-1022'
        minsubnorm = float.fromhex(ieee754_minsubnorm)
        ieee754_maxsubnorm = '0x0.fffffffffffffp-1022'
        maxsubnorm = float.fromhex(ieee754_maxsubnorm)

    if seed == -1:
        if opcode in 'fadd':
            random.seed(0)
        elif opcode in 'fsub':
            random.seed(1)
    else:
        random.seed(seed)

    b13_comb = []

    for i in range(200):
        rs1 = random.uniform(minsubnorm,maxnum)
        ir = random.uniform(minsubnorm,maxsubnorm)
        if opcode in 'fadd':
            if iflen == 32 or iflen == 16:
                rs2 = ir - rs1
            elif iflen == 64:
                rs2 = Decimal(ir) - Decimal(rs1)
        elif opcode in 'fsub':
            if iflen == 32 or iflen == 16:
                rs2 = rs1 - ir
            elif iflen == 64:
                rs2 = Decimal(rs1) - Decimal(ir)

        if(iflen==16):
            m = lambda rsx: float('inf') if rsx > fields_dec_converter(16, hmaxnorm[0]) \
            else float('-inf') if rsx < fields_dec_converter(16, hmaxnorm[1]) \
            else rsx
            x1 = m(rs1)
            x2 = m(rs2)
        elif(iflen==32):
            x1 = struct.unpack('f', struct.pack('f', rs1))[0]
            x2 = struct.unpack('f', struct.pack('f', rs2))[0]
        elif(iflen==64):
            x1 = rs1
            x2 = rs2

        if opcode in ['fadd','fsub']:
            b13_comb.append((floatingPoint_tohex(iflen,float(rs1)),floatingPoint_tohex(iflen,float(rs2))))

    coverpoints = []
    comment = ' | Add: Cancellation ---> Subnormal result'
    for c in b13_comb:
        cvpt = ""
        for x in range(1, 3):
#                    cvpt += 'rs'+str(x)+'_val=='+str(c[x-1]) # uncomment this if you want rs1_val instead of individual fields
            cvpt += (extract_fields(iflen,c[x-1],str(x)))
            cvpt += " and "
        cvpt = sanitise(0,cvpt,iflen,flen,ops,inxFlg)
        # cvpt += 'rm_val == 0'
        if inxFlg == True:
            cvpt += sgn_prefix(iflen,flen,inxFlg,ops,cvpt)
        else:
            cvpt += ' # '
        cvpt += ' # '
        for y in range(1, ops+1):
            cvpt += 'rs'+str(y)+'_val=='
            cvpt += num_explain(iflen, c[y-1]) + '(' + str(c[y-1]) + ')'
            if(y != ops):
                cvpt += " and "
        cvpt += comment
        coverpoints.append(cvpt)

    mess='Generated'+ (' '*(5-len(str(len(coverpoints)))))+ str(len(coverpoints)) +' '+ \
    (str(16) if iflen == 16 else str(32) if iflen == 32 else str(64)) + '-bit coverpoints using Model B13 for '+opcode+' !'
    logger.debug(mess)
    coverpoints = comments_parser(coverpoints)

    return coverpoints

def ibm_b14(flen, iflen, opcode, ops, inxFlg=False, N=-1, seed=-1):
    '''
    IBM Model B14 Definition:
            This model tests every possible value for a shift between the addends of the multiply-add operation.
            For the difference between the unbiased exponent of the addend and the
            unbiased exponent of the result of the multiplication, test the following values:

            1. A value smaller than -(2* p + 1)
            2. All the values in the range [-(2*p +1), (p +1) ]
            3. A value larger than (p + 1)

            We test both effective operations: addition and subtraction. The end values tested are selected to be greater by one than the largest possible shift in which
            the smaller addend may affect the result.

    :param iflen: Size of the floating point source operands for the operation
    :param flen: Size of the floating point registers
    :param opcode: Opcode for which the coverpoints are to be generated
    :param ops: No. of Operands taken by the opcode
    :param N: No. of sets of coverpoints to be generated. (Predefined to -1. Set to 2)
    :param seed: Initial seed value of the random library. (Predefined to -1. Actual value is set with respect to the opcode calling the function)

    :type iflen: int
    :type flen: int
    :type opcode: str
    :type ops: int
    :type N: int
    :param seed: int

    Abstract Dataset Description:
            Shift between the addends of the multiply-add operation = [ A value smaller than -(2* p + 1), All the values in the range [-(2*p +1), (p +1), A value larger than (p + 1) ] → Condition 1
            Operand 1, 2 = Random
            Operand 3 = Condition 1

    Implementation:
            - The shift between the two addends are constrained by the conditions mentioned in the dataset above.
            - Operands 1 and 2 are randomly obtained. But Operand 3 is obtained by ensuring the shift conditions.
            - Once the dataset is formed, these operand values are then passed into the extract_fields function to get individual fields in a floating point number (sign, exponent and mantissa).
            - Coverpoints are then appended with rounding mode ‘0’ for that particular opcode.

    '''
    sanitise = get_sanitise_func(opcode)
    opcode = opcode.split('.')[0]

    if iflen == 16:
        ieee754_maxnorm = float.hex(fields_dec_converter(16, hmaxnorm[0]))
        maxnum = float.fromhex(ieee754_maxnorm)
        exp_max = 15
        mant_bits = 10
        limnum = maxnum
    elif iflen == 32:
        ieee754_maxnorm = '0x1.7fffffp+127'
        maxnum = float.fromhex(ieee754_maxnorm)
        exp_max = 127
        mant_bits = 23
        limnum = maxnum

    elif iflen == 64:
        maxdec = '1.7976931348623157e+308'
        maxnum = float.fromhex('0x1.fffffffffffffp+1023')
        exp_max = 1022
        ieee754_limnum = '0x1.fffffffffffffp+507'
        mant_bits = 52
        limnum = float.fromhex(ieee754_limnum)

    if N == -1:
        N = 2

    if seed == -1:
        if opcode in 'fmadd':
            random.seed(0)
        elif opcode in 'fmsub':
            random.seed(1)
        elif opcode in 'fnmadd':
            random.seed(2)
        elif opcode in 'fnmsub':
            random.seed(3)
    else:
        random.seed(seed)

    b14_comb = []
    comment = []
    for i in range(1,N):
        rs1 =random.uniform(1,limnum)
        rs2 =random.uniform(1,limnum)
        rs3 =random.uniform(1,limnum)
       # mul_exp = int(str("{:e}".format(rs1*rs2)).split('e')[1]) #uncomment it if iflen =16 
        mul_exp = int(str(rs1*rs2).split('e')[1])
        mul_exp = int(math.log(pow(2,int(mul_exp)),10))

        if mul_exp-((2*mant_bits)+1) > -1*exp_max:
            rs3_exp = random.randrange(-1*exp_max,mul_exp-((2*mant_bits)+1))
            rs3_num = float.hex(float(str(rs3).split('e')[0])).split('p')[0]+'p'+str(int(float.hex(float(str(rs3).split('e')[0])).split('p')[1])+rs3_exp)
            rs3_num = float.fromhex(rs3_num)
            b14_comb.append((floatingPoint_tohex(iflen,float(rs1)),floatingPoint_tohex(iflen,float(rs2)),floatingPoint_tohex(iflen,float(rs3_num))))
            comment.append(' | Multiplicand Exponent = '+str(mul_exp)+', Addend exponent = '+ str(int(float.hex(float(str(rs3).split('e')[0])).split('p')[1])+rs3_exp) + ' --> Difference smaller than -(2*p + 1)')

        if mul_exp-((2*mant_bits)+1) < -1*exp_max: exp1 = -1*exp_max
        else: exp1 = mul_exp-((2*mant_bits)+1)
        if mul_exp+mant_bits+1 > exp_max: exp2 = exp_max
        else: exp2 = mul_exp+mant_bits+1
        for j in range(exp1, exp2):
            rs3_num = float.hex(float(str(rs3).split('e')[0])).split('p')[0]+'p'+str(int(float.hex(float(str(rs3).split('e')[0])).split('p')[1])+j)
            rs3_num = float.fromhex(rs3_num)
            b14_comb.append((floatingPoint_tohex(iflen,float(rs1)),floatingPoint_tohex(iflen,float(rs2)),floatingPoint_tohex(iflen,float(rs3_num))))
            comment.append(' | Multiplicand Exponent = '+str(mul_exp)+', Addend exponent = '+ str(int(float.hex(float(str(rs3).split('e')[0])).split('p')[1])+j) + ' --> Values in the range [-(2*p + 1) , (p + 1)]')

        rs3_exp = random.randrange(exp2, exp_max)
        rs3_num = float.hex(float(str(rs3).split('e')[0])).split('p')[0]+'p'+str(int(float.hex(float(str(rs3).split('e')[0])).split('p')[1])+rs3_exp)
        rs3_num = float.fromhex(rs3_num)
        b14_comb.append((floatingPoint_tohex(iflen,float(rs1)),floatingPoint_tohex(iflen,float(rs2)),floatingPoint_tohex(iflen,float(rs3_num))))
        comment.append(' | Multiplicand Exponent = '+str(mul_exp)+', Addend exponent = '+ str(int(float.hex(float(str(rs3).split('e')[0])).split('p')[1])+rs3_exp) + ' --> A value larger than (p + 1)')

    coverpoints = []
    k = 0
    for c in b14_comb:
        cvpt = ""
        for x in range(1, 4):
#                    cvpt += 'rs'+str(x)+'_val=='+str(c[x-1]) # uncomment this if you want rs1_val instead of individual fields
            cvpt += (extract_fields(iflen,c[x-1],str(x)))
            cvpt += " and "
        # cvpt += 'rm_val == 0'
        cvpt = sanitise(0,cvpt,iflen,flen,ops,inxFlg)
        if inxFlg == True:
            cvpt += sgn_prefix(iflen,flen,inxFlg,ops,cvpt)
        else:
            cvpt += ' # '
        cvpt += ' # '
        for y in range(1, 4):
            cvpt += 'rs'+str(y)+'_val=='
            cvpt += num_explain(iflen, c[y-1]) + '(' + str(c[y-1]) + ')'
            if(y != ops):
                cvpt += " and "
        cvpt += comment[k]
        coverpoints.append(cvpt)
        k += 1

    mess='Generated'+ (' '*(5-len(str(len(coverpoints)))))+ str(len(coverpoints)) +' '+ \
    (str(16) if iflen == 16 else str(32) if iflen == 32 else str(64)) + '-bit coverpoints using Model B14 for '+opcode+' !'
    logger.debug(mess)
    coverpoints = comments_parser(coverpoints)

    return coverpoints

def ibm_b15(flen, iflen, opcode, ops, inxFlg=False, N=-1, seed=-1):
    '''
    IBM Model B15 Definition:
            In this model we test the combination of different shift values between the
            addends, with special patterns in the significands of the addends.
            For the significand of the addend and for the multiplication result we take the
            cases defined in model (B9) "Special Significands on Inputs"
            For the shift we take the cases defined in model (B14) "Shift – multiply-add".

    :param iflen: Size of the floating point source operands for the operation
    :param flen: Size of the floating point registers
    :param opcode: Opcode for which the coverpoints are to be generated
    :param ops: No. of Operands taken by the opcode
    :param seed: Initial seed value of the random library. (Predefined to -1. Actual value is set with respect to the opcode calling the function)

    :type iflen: int
    :type flen: int
    :type opcode: str
    :type ops: int
    :param seed: int

    Abstract Dataset Description:
            Operand 1, 2 = Random
            Operand 3 ∈ Abstract Dataset in B9 + Abstract Dataset in B14

    Implementation:
            - Here the condition is imposed that if the value of the ops variable is 3, then each of the elements in the flip types is iterated and split into their respective sign, mantissa and exponent part.
            - A mul variable is initialized and parsed to the field_dec_converter for each rs1 value in the list. Next the loop is run for the mantissa parts generated for rs1 values, where it is checked for certain patterns like the leading 0’s, leading 1’s, trailing 0’s and trailing 1’s.
            - The checkerboard list is declared with the probable sequences for rs2. Here the sign and exponent are extracted from the rs1 values. Mantissa part is derived from the checkerboard list. Consecutively, if the iflen value differs, then the range available varies.
            - The operand values are then passed into the extract_fields function to get individual fields in a floating point number (sign, exponent and mantissa).
            - Coverpoints are then appended with rounding mode “0” for that particular opcode.

    '''
    sanitise = get_sanitise_func(opcode)
    opcode = opcode.split('.')[0]

    if iflen == 16:
        flip_types = hzero + hone + hminsubnorm + hmaxsubnorm + hminnorm + hmaxnorm
        e_sz = 5
        exp_max = 15
        ieee754_maxnorm = float.hex(fields_dec_converter(16, hmaxnorm[0]))
        maxnum = float.fromhex(ieee754_maxnorm)
        mant_bits = 10
        limnum = maxnum
    elif iflen == 32:
        flip_types = fzero + fone + fminsubnorm + fmaxsubnorm + fminnorm + fmaxnorm
        e_sz=8
        exp_max = 255
        ieee754_maxnorm = '0x1.7fffffp+127'
        maxnum = float.fromhex(ieee754_maxnorm)
        exp_max = 127
        mant_bits = 23
        limnum = maxnum
    elif iflen == 64:
        flip_types = dzero + done + dminsubnorm + dmaxsubnorm + dminnorm + dmaxnorm
        e_sz=11
        exp_max = 1023
        maxdec = '1.7976931348623157e+308'
        maxnum = float.fromhex('0x1.fffffffffffffp+1023')
        exp_max = 1022
        ieee754_limnum = '0x1.fffffffffffffp+507'
        mant_bits = 52
        limnum = float.fromhex(ieee754_limnum)

    if seed == -1:
        if opcode in 'fmadd':
            random.seed(0)
        elif opcode in 'fnmadd':
            random.seed(1)
        elif opcode in 'fmsub':
            random.seed(2)
        elif opcode in 'fnmsub':
            random.seed(3)
    else:
        random.seed(seed)

    rs1 = []
    b15_comb = []
    comment = []
    if ops == 3:
        for i in range(len(flip_types)):
            rs1.append(flip_types[i])
        for i in range(len(rs1)):
            bin_val = bin(int('1'+rs1[i][2:],16))[3:]
            rs1_sgn = bin_val[0]
            rs1_exp = bin_val[1:e_sz+1]
            rs1_man = bin_val[e_sz+1:]

            if iflen == 16:
                if int(rs1_exp,2) < 33: rs2_exp = 0
                else : rs2_exp = random.randrange(0,int(rs1_exp,2)-33)
                comment_str = ' | Exponent = '+ str(rs2_exp-15) + ' --> Difference smaller than -(2p + 1)'
                rs2_exp = '{:05b}'.format(rs2_exp)  
            elif iflen == 32:
                if int(rs1_exp,2) < 65: rs2_exp = 0
                else : rs2_exp = random.randrange(0,int(rs1_exp,2)-65)
                comment_str = ' | Exponent = '+ str(rs2_exp-127) + ' --> Difference smaller than -(2p + 1)'
                rs2_exp = '{:08b}'.format(rs2_exp)
            elif iflen == 64:
                if int(rs1_exp,2) < 129: rs2_exp = 0
                else : rs2_exp = random.randrange(0,int(rs1_exp,2)-129)
                comment_str = ' | Exponent = '+ str(rs2_exp-1023) + ' --> Difference smaller than -(2p + 1)'
                rs2_exp = '{:011b}'.format(rs2_exp)
            mul = fields_dec_converter(iflen,rs1[i])
            rs1_act = random.uniform(1,limnum)
            rs2_act = mul/rs1_act
            for j in range(len(rs1_man)):
                rs2_sgn = rs1_sgn
                rs2_man = '0'*j + rs1_man[j:]                        # Leading 0s
                rs2 = fields_dec_converter(iflen,'0x'+hex(int('1'+rs2_sgn+rs2_exp+rs2_man,2))[3:])
                b15_comb.append((floatingPoint_tohex(iflen,float(rs1_act)),floatingPoint_tohex(iflen,float(rs2_act)),floatingPoint_tohex(iflen,float(rs2))))
                comment.append(comment_str + ' | Leading zeroes ---> rs3_man = '+rs2_man)

                rs2_man = '1'*j + '0'*(len(rs1_man)-j)                        # Leading 1s
                rs2 = fields_dec_converter(iflen,'0x'+hex(int('1'+rs2_sgn+rs2_exp+rs2_man,2))[3:])
                b15_comb.append((floatingPoint_tohex(iflen,float(rs1_act)),floatingPoint_tohex(iflen,float(rs2_act)),floatingPoint_tohex(iflen,float(rs2))))
                comment.append(comment_str + ' | Leading ones ---> rs3_man = '+rs2_man)

                rs2_man = rs1_man[0:j] + '0'*(len(rs1_man)-j)        # Trailing 0s
                rs2 = fields_dec_converter(iflen,'0x'+hex(int('1'+rs2_sgn+rs2_exp+rs2_man,2))[3:])
                b15_comb.append((floatingPoint_tohex(iflen,float(rs1_act)),floatingPoint_tohex(iflen,float(rs2_act)),floatingPoint_tohex(iflen,float(rs2))))
                comment.append(comment_str + ' | Trailing zeroes ---> rs3_man = '+rs2_man)

                rs2_man = '0'*j + '1'*(len(rs1_man)-j)        # Trailing 1s
                rs2 = fields_dec_converter(iflen,'0x'+hex(int('1'+rs2_sgn+rs2_exp+rs2_man,2))[3:])
                b15_comb.append((floatingPoint_tohex(iflen,float(rs1_act)),floatingPoint_tohex(iflen,float(rs2_act)),floatingPoint_tohex(iflen,float(rs2))))
                comment.append(comment_str + ' | Trailing ones ---> rs3_man = '+rs2_man)

            for j in range(len(rs1_man)-math.ceil(0.1*len(rs1_man)),len(rs1_man)):
                rs2_sgn = rs1_sgn
                rs2_exp = rs1_exp
                rs2_man = '1'*j + '0'*(len(rs1_man)-j)                        # Long sequence of 1s
                rs2 = fields_dec_converter(iflen,'0x'+hex(int('1'+rs2_sgn+rs2_exp+rs2_man,2))[3:])
                b15_comb.append((floatingPoint_tohex(iflen,float(rs1_act)),floatingPoint_tohex(iflen,float(rs2_act)),floatingPoint_tohex(iflen,float(rs2))))
                comment.append(comment_str + ' | Long sequence of ones ---> rs3_man = '+rs2_man)

                rs2_man = '0'*j + '1'*(len(rs1_man)-j)                        # Long sequence of 0s
                rs2 = fields_dec_converter(iflen,'0x'+hex(int('1'+rs2_sgn+rs2_exp+rs2_man,2))[3:])
                b15_comb.append((floatingPoint_tohex(iflen,float(rs1_act)),floatingPoint_tohex(iflen,float(rs2_act)),floatingPoint_tohex(iflen,float(rs2))))
                comment.append(comment_str + ' | Long sequence of zeroes ---> rs3_man = '+rs2_man)

            chkrbrd = ['011','110','0011','1100','0111','1000','010','101','0110','1001']
            for j in chkrbrd:
                rs2_sgn = rs1_sgn
                rs2_exp = rs1_exp
                rs2_man = j
                for k in range(math.ceil(len(rs1_man)/len(j))):
                    rs2_man += j
                rs2_man = rs2_man[0:iflen-e_sz-1]
                rs2 = fields_dec_converter(iflen,'0x'+hex(int('1'+rs2_sgn+rs2_exp+rs2_man,2))[3:])
                b15_comb.append((floatingPoint_tohex(iflen,float(rs1_act)),floatingPoint_tohex(iflen,float(rs2_act)),floatingPoint_tohex(iflen,float(rs2))))
                comment.append(comment_str + ' | Checkerboard pattern ---> rs3_man = '+rs2_man)

            
            if iflen == 16:
                if int(rs1_exp,2) > 46: rs2_exp = 63
                else : rs2_exp = random.randrange(int(rs1_exp,2)+17, 63)
                comment_str = ' | Exponent = '+ str(rs2_exp-15) + ' --> Difference greater than (p + 1)'
                rs2_exp = '{:05b}'.format(rs2_exp)
            elif iflen == 32:
                if int(rs1_exp,2) > 222: rs2_exp = 255
                else : rs2_exp = random.randrange(int(rs1_exp,2)+33, 255)
                comment_str = ' | Exponent = '+ str(rs2_exp-127) + ' --> Difference greater than (p + 1)'
                rs2_exp = '{:08b}'.format(rs2_exp)
            elif iflen == 64:
                if int(rs1_exp,2) > 958: rs2_exp = 1023
                else : rs2_exp = random.randrange(int(rs1_exp,2)+65, 1023)
                comment_str = ' | Exponent = '+ str(rs2_exp-1023) + ' --> Difference greater than (p + 1)'
                rs2_exp = '{:011b}'.format(rs2_exp)
            mul = fields_dec_converter(iflen,rs1[i])
            rs1_act = random.uniform(1,limnum)
            rs2_act = mul/rs1_act
            for j in range(len(rs1_man)):
                rs2_sgn = rs1_sgn
                rs2_man = '0'*j + rs1_man[j:]                        # Leading 0s
                rs2 = fields_dec_converter(iflen,'0x'+hex(int('1'+rs2_sgn+rs2_exp+rs2_man,2))[3:])
                b15_comb.append((floatingPoint_tohex(iflen,float(rs1_act)),floatingPoint_tohex(iflen,float(rs2_act)),floatingPoint_tohex(iflen,float(rs2))))
                comment.append(comment_str + ' | Leading zeroes ---> rs3_man = '+rs2_man)

                rs2_man = '1'*j + '0'*(len(rs1_man)-j)                        # Leading 1s
                rs2 = fields_dec_converter(iflen,'0x'+hex(int('1'+rs2_sgn+rs2_exp+rs2_man,2))[3:])
                b15_comb.append((floatingPoint_tohex(iflen,float(rs1_act)),floatingPoint_tohex(iflen,float(rs2_act)),floatingPoint_tohex(iflen,float(rs2))))
                comment.append(comment_str + ' | Leading ones ---> rs3_man = '+rs2_man)

                rs2_man = rs1_man[0:j] + '0'*(len(rs1_man)-j)        # Trailing 0s
                rs2 = fields_dec_converter(iflen,'0x'+hex(int('1'+rs2_sgn+rs2_exp+rs2_man,2))[3:])
                b15_comb.append((floatingPoint_tohex(iflen,float(rs1_act)),floatingPoint_tohex(iflen,float(rs2_act)),floatingPoint_tohex(iflen,float(rs2))))
                comment.append(comment_str + ' | Trailing zeroes ---> rs3_man = '+rs2_man)

                rs2_man = '0'*j + '1'*(len(rs1_man)-j)        # Trailing 1s
                rs2 = fields_dec_converter(iflen,'0x'+hex(int('1'+rs2_sgn+rs2_exp+rs2_man,2))[3:])
                b15_comb.append((floatingPoint_tohex(iflen,float(rs1_act)),floatingPoint_tohex(iflen,float(rs2_act)),floatingPoint_tohex(iflen,float(rs2))))
                comment.append(comment_str + ' | Trailing ones ---> rs3_man = '+rs2_man)

            for j in range(len(rs1_man)-math.ceil(0.1*len(rs1_man)),len(rs1_man)):
                rs2_sgn = rs1_sgn
                rs2_exp = rs1_exp
                rs2_man = '1'*j + '0'*(len(rs1_man)-j)                        # Long sequence of 1s
                rs2 = fields_dec_converter(iflen,'0x'+hex(int('1'+rs2_sgn+rs2_exp+rs2_man,2))[3:])
                b15_comb.append((floatingPoint_tohex(iflen,float(rs1_act)),floatingPoint_tohex(iflen,float(rs2_act)),floatingPoint_tohex(iflen,float(rs2))))
                comment.append(comment_str + ' | Long sequence of ones ---> rs3_man = '+rs2_man)

                rs2_man = '0'*j + '1'*(len(rs1_man)-j)                        # Long sequence of 0s
                rs2 = fields_dec_converter(iflen,'0x'+hex(int('1'+rs2_sgn+rs2_exp+rs2_man,2))[3:])
                b15_comb.append((floatingPoint_tohex(iflen,float(rs1_act)),floatingPoint_tohex(iflen,float(rs2_act)),floatingPoint_tohex(iflen,float(rs2))))
                comment.append(comment_str + ' | Long sequence of zeroes ---> rs3_man = '+rs2_man)

            chkrbrd = ['011','110','0011','1100','0111','1000','010','101','0110','1001']
            for j in chkrbrd:
                rs2_sgn = rs1_sgn
                rs2_exp = rs1_exp
                rs2_man = j
                for k in range(math.ceil(len(rs1_man)/len(j))):
                    rs2_man += j
                rs2_man = rs2_man[0:iflen-e_sz-1]
                rs2 = fields_dec_converter(iflen,'0x'+hex(int('1'+rs2_sgn+rs2_exp+rs2_man,2))[3:])
                b15_comb.append((floatingPoint_tohex(iflen,float(rs1_act)),floatingPoint_tohex(iflen,float(rs2_act)),floatingPoint_tohex(iflen,float(rs2))))
                comment.append(comment_str + ' | Checkerboard pattern ---> rs3_man = '+rs2_man)

            if iflen == 16:
                ul = int(rs1_exp,2)+17
                ll = int(rs1_exp,2)-33
                if int(rs1_exp,2) >= 46: ul = 63
                if int(rs1_exp,2) < 33: ll = 0
            elif iflen == 32:
                ul = int(rs1_exp,2)+33
                ll = int(rs1_exp,2)-65
                if int(rs1_exp,2) >= 222: ul = 255
                if int(rs1_exp,2) < 65: ll = 0
            elif iflen == 64:
                ul = int(rs1_exp,2)+65
                ll = int(rs1_exp,2)-129
                if int(rs1_exp,2) >= 958: ul = 1023
                if int(rs1_exp,2) < 129: ll = 0
            for expval in range (ll, ul):
                rs2_exp = expval
                
                if iflen == 16:
                    comment_str = ' | Exponent = '+ str(rs2_exp-15) + ' --> Difference between -(2p+1) and (p+1)'
                    rs2_exp = '{:05b}'.format(rs2_exp)
                elif iflen == 32:
                    comment_str = ' | Exponent = '+ str(rs2_exp-127) + ' --> Difference between -(2p+1) and (p+1)'
                    rs2_exp = '{:08b}'.format(rs2_exp)
                elif iflen == 64:
                    comment_str = ' | Exponent = '+ str(rs2_exp-1023) + ' --> Difference between -(2p+1) and (p+1)'
                    rs2_exp = '{:011b}'.format(rs2_exp)
                mul = fields_dec_converter(iflen,rs1[i])
                rs1_act = random.uniform(1,limnum)
                rs2_act = mul/rs1_act

                for j in range(len(rs1_man)):
                    rs2_sgn = rs1_sgn
                    rs2_man = '0'*j + rs1_man[j:]                        # Leading 0s
                    rs2 = fields_dec_converter(iflen,'0x'+hex(int('1'+rs2_sgn+rs2_exp+rs2_man,2))[3:])
                    b15_comb.append((floatingPoint_tohex(iflen,float(rs1_act)),floatingPoint_tohex(iflen,float(rs2_act)),floatingPoint_tohex(iflen,float(rs2))))
                    comment.append(comment_str + ' | Leading zeroes ---> rs3_man = '+rs2_man)

                    rs2_man = '1'*j + '0'*(len(rs1_man)-j)                        # Leading 1s
                    rs2 = fields_dec_converter(iflen,'0x'+hex(int('1'+rs2_sgn+rs2_exp+rs2_man,2))[3:])
                    b15_comb.append((floatingPoint_tohex(iflen,float(rs1_act)),floatingPoint_tohex(iflen,float(rs2_act)),floatingPoint_tohex(iflen,float(rs2))))
                    comment.append(comment_str + ' | Leading ones ---> rs3_man = '+rs2_man)

                    rs2_man = rs1_man[0:j] + '0'*(len(rs1_man)-j)        # Trailing 0s
                    rs2 = fields_dec_converter(iflen,'0x'+hex(int('1'+rs2_sgn+rs2_exp+rs2_man,2))[3:])
                    b15_comb.append((floatingPoint_tohex(iflen,float(rs1_act)),floatingPoint_tohex(iflen,float(rs2_act)),floatingPoint_tohex(iflen,float(rs2))))
                    comment.append(comment_str + ' | Trailing zeroes ---> rs3_man = '+rs2_man)

                    rs2_man = '0'*j + '1'*(len(rs1_man)-j)        # Trailing 1s
                    rs2 = fields_dec_converter(iflen,'0x'+hex(int('1'+rs2_sgn+rs2_exp+rs2_man,2))[3:])
                    b15_comb.append((floatingPoint_tohex(iflen,float(rs1_act)),floatingPoint_tohex(iflen,float(rs2_act)),floatingPoint_tohex(iflen,float(rs2))))
                    comment.append(comment_str + ' | Trailing ones ---> rs3_man = '+rs2_man)

                for j in range(len(rs1_man)-math.ceil(0.1*len(rs1_man)),len(rs1_man)):
                    rs2_sgn = rs1_sgn
                    rs2_exp = rs1_exp
                    rs2_man = '1'*j + '0'*(len(rs1_man)-j)                        # Long sequence of 1s
                    rs2 = fields_dec_converter(iflen,'0x'+hex(int('1'+rs2_sgn+rs2_exp+rs2_man,2))[3:])
                    b15_comb.append((floatingPoint_tohex(iflen,float(rs1_act)),floatingPoint_tohex(iflen,float(rs2_act)),floatingPoint_tohex(iflen,float(rs2))))
                    comment.append(comment_str + ' | Long sequence of ones ---> rs3_man = '+rs2_man)

                    rs2_man = '0'*j + '1'*(len(rs1_man)-j)                        # Long sequence of 0s
                    rs2 = fields_dec_converter(iflen,'0x'+hex(int('1'+rs2_sgn+rs2_exp+rs2_man,2))[3:])
                    b15_comb.append((floatingPoint_tohex(iflen,float(rs1_act)),floatingPoint_tohex(iflen,float(rs2_act)),floatingPoint_tohex(iflen,float(rs2))))
                    comment.append(comment_str + ' | Long sequence of zeroes ---> rs3_man = '+rs2_man)

                chkrbrd = ['011','110','0011','1100','0111','1000','010','101','0110','1001']
                for j in chkrbrd:
                    rs2_sgn = rs1_sgn
                    rs2_exp = rs1_exp
                    rs2_man = j
                    for k in range(math.ceil(len(rs1_man)/len(j))):
                        rs2_man += j
                    rs2_man = rs2_man[0:iflen-e_sz-1]
                    rs2 = fields_dec_converter(iflen,'0x'+hex(int('1'+rs2_sgn+rs2_exp+rs2_man,2))[3:])
                    b15_comb.append((floatingPoint_tohex(iflen,float(rs1_act)),floatingPoint_tohex(iflen,float(rs2_act)),floatingPoint_tohex(iflen,float(rs2))))
                    comment.append(comment_str + ' | Checkerboard pattern ---> rs3_man = '+rs2_man)

    coverpoints = []
    k = 0
    for c in b15_comb:
        cvpt = ""
        for x in range(1, 4):
#                    cvpt += 'rs'+str(x)+'_val=='+str(c[x-1]) # uncomment this if you want rs1_val instead of individual fields
            cvpt += (extract_fields(iflen,c[x-1],str(x)))
            cvpt += " and "
        # cvpt += 'rm_val == 0'
        cvpt = sanitise(0,cvpt,iflen,flen,ops,inxFlg)
        if inxFlg == True:
            cvpt += sgn_prefix(iflen,flen,inxFlg,ops,cvpt)
        else:
            cvpt += ' # '
        cvpt += ' # '
        for y in range(1, ops+1):
            cvpt += 'rs'+str(y)+'_val=='
            cvpt += num_explain(iflen, c[y-1]) + '(' + str(c[y-1]) + ')'
            if(y != ops):
                cvpt += " and "
        cvpt += comment[k]
        coverpoints.append(cvpt)
        k += 1

    mess='Generated'+ (' '*(5-len(str(len(coverpoints)))))+ str(len(coverpoints)) +' '+ \
    (str(16) if iflen == 16 else str(32) if iflen == 32 else str(64)) + '-bit coverpoints using Model B15 for '+opcode+' !'
    logger.debug(mess)
    coverpoints = comments_parser(coverpoints)

    return coverpoints

def ibm_b16(flen, iflen, opcode, ops, inxFlg=False, seed=-1):
    '''
    IBM Model B16 Definition:
            This model tests every possible value for cancellation.
            For the difference between the exponent of the intermediate result and the
            maximum between the exponents of the addend and the multiplication result,
            test all values in the range:
            [-(2 * p + 1), 1].

    :param iflen: Size of the floating point source operands for the operation
    :param flen: Size of the floating point registers
    :param opcode: Opcode for which the coverpoints are to be generated
    :param ops: No. of Operands taken by the opcode
    :param seed: Initial seed value of the random library. (Predefined to -1. Actual value is set with respect to the opcode calling the function)

    :type iflen: int
    :type flen: int
    :type opcode: str
    :type ops: int
    :param seed: int

    Abstract Dataset Description:
            Intermediate Result.exp - max(addend.exp, multiplication result.exp) ∈ [-(2 * p + 1), 1] → Condition 1
            Operand 1 {operation 1} Operand 2 {operation 2} Operand 3 = Condition 1

    Implementation:
            - Random values of operands 1 and 2 are obtained from the random library.
            - Since the objective of the test is to cancel the operands among each other constrained by the above condition, the intermediate result is calculated by the multiplication of operand 1 and 2.
            - The operand values are then passed into the extract_fields function to get individual fields in a floating point number (sign, exponent and mantissa).
            - Coverpoints are then appended with rounding mode “0” for that particular opcode.

    '''
    sanitise = get_sanitise_func(opcode)

    opcode = opcode.split('.')[0]
    getcontext().prec = 40
    if iflen == 16:
        ieee754_maxnorm = float.hex(fields_dec_converter(16, hmaxnorm[0]))
        maxnum = float.fromhex(ieee754_maxnorm)
        ieee754_minsubnorm = float.hex(fields_dec_converter(16, hminsubnorm[0]))
        minsubnorm = float.fromhex(ieee754_minsubnorm)
        ieee754_maxsubnorm = float.hex(fields_dec_converter(16, hmaxsubnorm[0]))
        maxsubnorm = float.fromhex(ieee754_maxsubnorm)
        limnum =  maxnum
    elif iflen == 32:
        ieee754_maxnorm = '0x1.7fffffp+127'
        maxnum = float.fromhex(ieee754_maxnorm)
        ieee754_minsubnorm = '0x0.000001p-126'
        minsubnorm = float.fromhex(ieee754_minsubnorm)
        ieee754_maxsubnorm = '0x0.7fffffp-126'
        maxsubnorm = float.fromhex(ieee754_maxsubnorm)
        limnum = maxnum

    elif iflen == 64:
        ieee754_maxnorm = '0x1.fffffffffffffp+1023'
        maxnum = float.fromhex(ieee754_maxnorm)
        ieee754_minsubnorm = '0x0.0000000000001p-1022'
        minsubnorm = float.fromhex(ieee754_minsubnorm)
        ieee754_maxsubnorm = '0x0.fffffffffffffp-1022'
        maxsubnorm = float.fromhex(ieee754_maxsubnorm)
        ieee754_limnum = '0x1.fffffffffffffp+507'
        limnum = float.fromhex(ieee754_limnum)

    if seed == -1:
        if opcode in 'fmadd':
            random.seed(0)
        elif opcode in 'fmsub':
            random.seed(1)
        elif opcode in 'fnmadd':
            random.seed(2)
        elif opcode in 'fnmsub':
            random.seed(3)
    else:
        random.seed(seed)

    b17_comb = []

    for i in range(200):
        rs1 = random.uniform(minsubnorm,limnum)
        rs2 = random.uniform(minsubnorm,limnum)
        ir = random.uniform(minsubnorm,rs1*rs2)

        if opcode in 'fmadd':
            if iflen == 32 or iflen == 16:
                rs3 = ir - rs1*rs2
            elif iflen == 64:
                rs3 = Decimal(ir) - Decimal(rs1)*Decimal(rs2)
        elif opcode in 'fnmadd':
            if iflen == 32 or iflen == 16:
                rs3 = -1*rs1*rs2 - ir
            elif iflen == 64:
                rs3 = -1*Decimal(rs1)*Decimal(rs2) - Decimal(ir)
        elif opcode in 'fmsub':
            if iflen == 32 or iflen == 16:
                rs3 = rs1*rs2 - ir
            elif iflen == 64:
                rs3 = Decimal(rs1)*Decimal(rs2) - Decimal(ir)
        elif opcode in 'fnmsub':
            if iflen == 32 or iflen == 16:
                rs3 = ir + rs1*rs2
            elif iflen == 64:
                rs3 = Decimal(ir) + Decimal(rs1)*Decimal(rs2)

        if(iflen==16):
            m = lambda rsx: float('inf') if rsx > fields_dec_converter(16, hmaxnorm[0]) \
            else float('-inf') if rsx < fields_dec_converter(16, hmaxnorm[1]) \
            else rsx
            x1 = m(rs1)
            x2 = m(rs2)
            x3 = m(rs3)
        elif(iflen==32):
            x1 = struct.unpack('f', struct.pack('f', rs1))[0]
            x2 = struct.unpack('f', struct.pack('f', rs2))[0]
        elif(iflen==64):
            x1 = rs1
            x2 = rs2

        result = []
        if opcode in ['fmadd','fmsub','fnmadd','fnmsub']:
            b17_comb.append((floatingPoint_tohex(iflen,float(rs1)),floatingPoint_tohex(iflen,float(rs2)),floatingPoint_tohex(iflen,float(rs3))))

    coverpoints = []
    comment = ' | Multiply-Add: Cancellation'
    for c in b17_comb:
        cvpt = ""
        for x in range(1, 4):
#                    cvpt += 'rs'+str(x)+'_val=='+str(c[x-1]) # uncomment this if you want rs1_val instead of individual fields
            cvpt += (extract_fields(iflen,c[x-1],str(x)))
            cvpt += " and "
        # cvpt += 'rm_val == 0'
        cvpt = sanitise(0,cvpt,iflen,flen,ops,inxFlg)
        if inxFlg == True:
            cvpt += sgn_prefix(iflen,flen,inxFlg,ops,cvpt)
        else:
            cvpt += ' # '
        cvpt += ' # '
        for y in range(1, ops+1):
            cvpt += 'rs'+str(y)+'_val=='
            cvpt += num_explain(iflen, c[y-1]) + '(' + str(c[y-1]) + ')'
            if(y != ops):
                cvpt += " and "
        cvpt += comment
        coverpoints.append(cvpt)

    mess='Generated'+ (' '*(5-len(str(len(coverpoints)))))+ str(len(coverpoints)) +' '+ \
    (str(16) if iflen == 16 else str(32) if iflen == 32 else str(64)) + '-bit coverpoints using Model B16 for '+opcode+' !'
    logger.debug(mess)
    coverpoints = comments_parser(coverpoints)

    return coverpoints

def ibm_b17(flen, iflen, opcode, ops, inxFlg=False, seed=-1):
    '''
    IBM Model B17 Definition:
            This model tests all combinations of cancellation values as in model (B16), with
            all possible unbiased exponent values of subnormal results.

    :param iflen: Size of the floating point source operands for the operation
    :param flen: Size of the floating point registers
    :param opcode: Opcode for which the coverpoints are to be generated
    :param ops: No. of Operands taken by the opcode
    :param seed: Initial seed value of the random library. (Predefined to -1. Actual value is set with respect to the opcode calling the function)

    :type iflen: int
    :type flen: int
    :type opcode: str
    :type ops: int
    :param seed: int

    Abstract Dataset Description:
            Intermediate Result.exp - max(addend.exp, multiplication result.exp) ∈ [-(2 * p + 1), 1] → Condition 1 (Exponents are subnormal)
            Operand 1 {operation 1} Operand 2 {operation 2} Operand 3 = Condition 1

    Implementation:
            - It functions the same as model B16 with calculating the additional unbiased exponent values of subnormal results.
            - Operands 1 and 2 are randomly initialized in the range and the subsequent operator value is found.
            - The operand values are then passed into the extract_fields function to get individual fields in a floating point number (sign, exponent and mantissa).
            - Coverpoints are then appended with rounding mode “0” for that particular opcode.

    '''
    sanitise = get_sanitise_func(opcode)

    opcode = opcode.split('.')[0]
    getcontext().prec = 40
    if iflen == 16:
        ieee754_maxnorm = float.hex(fields_dec_converter(16, hmaxnorm[0]))
        maxnum = float.fromhex(ieee754_maxnorm)
        ieee754_minsubnorm = float.hex(fields_dec_converter(16, hminsubnorm[0]))
        minsubnorm = float.fromhex(ieee754_minsubnorm)
        ieee754_maxsubnorm = float.hex(fields_dec_converter(16, hmaxsubnorm[0]))
        maxsubnorm = float.fromhex(ieee754_maxsubnorm)
        limnum = maxnum
    elif iflen == 32:
        ieee754_maxnorm = '0x1.7fffffp+127'
        maxnum = float.fromhex(ieee754_maxnorm)
        ieee754_minsubnorm = '0x0.000001p-126'
        minsubnorm = float.fromhex(ieee754_minsubnorm)
        ieee754_maxsubnorm = '0x0.7fffffp-126'
        maxsubnorm = float.fromhex(ieee754_maxsubnorm)
        limnum = maxnum

    elif iflen == 64:
        ieee754_maxnorm = '0x1.fffffffffffffp+1023'
        maxnum = float.fromhex(ieee754_maxnorm)
        ieee754_minsubnorm = '0x0.0000000000001p-1022'
        minsubnorm = float.fromhex(ieee754_minsubnorm)
        ieee754_maxsubnorm = '0x0.fffffffffffffp-1022'
        maxsubnorm = float.fromhex(ieee754_maxsubnorm)
        ieee754_limnum = '0x1.fffffffffffffp+507'
        limnum = float.fromhex(ieee754_limnum)

    if seed == -1:
        if opcode in 'fmadd':
            random.seed(0)
        elif opcode in 'fmsub':
            random.seed(1)
        elif opcode in 'fnmadd':
            random.seed(2)
        elif opcode in 'fnmsub':
            random.seed(3)
    else:
        random.seed(seed)

    b17_comb = []

    for i in range(200):
        rs1 = random.uniform(minsubnorm,limnum)
        rs2 = random.uniform(minsubnorm,limnum)
        ir = random.uniform(minsubnorm,maxsubnorm)
        if ir > rs1*rs2: ir = random.uniform(minsubnorm,rs1*rs2)

        if opcode in 'fmadd':
            if iflen == 32 or iflen == 16:
                rs3 = ir - rs1*rs2
            elif iflen == 64:
                rs3 = Decimal(ir) - Decimal(rs1)*Decimal(rs2)
        elif opcode in 'fnmadd':
            if iflen == 32 or iflen == 16:
                rs3 = -1*rs1*rs2 - ir
            elif iflen == 64:
                rs3 = -1*Decimal(rs1)*Decimal(rs2) - Decimal(ir)
        elif opcode in 'fmsub':
            if iflen == 32 or iflen == 16:
                rs3 = rs1*rs2 - ir
            elif iflen == 64:
                rs3 = Decimal(rs1)*Decimal(rs2) - Decimal(ir)
        elif opcode in 'fnmsub':
            if iflen == 32 or iflen == 16:
                rs3 = ir + rs1*rs2
            elif iflen == 64:
                rs3 = Decimal(ir) + Decimal(rs1)*Decimal(rs2)

        if(iflen==16):
            m = lambda rsx: float('inf') if rsx > fields_dec_converter(16, hmaxnorm[0]) \
            else float('-inf') if rsx < fields_dec_converter(16, hmaxnorm[1]) \
            else rsx
            x1 = m(rs1)
            x2 = m(rs2)
            x3 = m(rs3)
        elif(iflen==32):
            x1 = struct.unpack('f', struct.pack('f', rs1))[0]
            x2 = struct.unpack('f', struct.pack('f', rs2))[0]
        elif(iflen==64):
            x1 = rs1
            x2 = rs2

        result = []
        if opcode in ['fmadd','fmsub','fnmadd','fnmsub']:
            b17_comb.append((floatingPoint_tohex(iflen,float(rs1)),floatingPoint_tohex(iflen,float(rs2)),floatingPoint_tohex(iflen,float(rs3))))

    coverpoints = []
    comment = ' | Multiply-Add: Cancellation ---> Subnormal result '
    for c in b17_comb:
        cvpt = ""
        for x in range(1, 4):
#                    cvpt += 'rs'+str(x)+'_val=='+str(c[x-1]) # uncomment this if you want rs1_val instead of individual fields
            cvpt += (extract_fields(iflen,c[x-1],str(x)))
            cvpt += " and "
        cvpt = sanitise(0,cvpt,iflen,flen,ops,inxFlg)
        # cvpt += 'rm_val == 0'
        if inxFlg == True:
            cvpt += sgn_prefix(iflen,flen,inxFlg,ops,cvpt)
        else:
            cvpt += ' # '
        cvpt += ' # '
        for y in range(1, ops+1):
            cvpt += 'rs'+str(y)+'_val=='
            cvpt += num_explain(iflen, c[y-1]) + '(' + str(c[y-1]) + ')'
            if(y != ops):
                cvpt += " and "
        cvpt += comment
        coverpoints.append(cvpt)

    mess='Generated'+ (' '*(5-len(str(len(coverpoints)))))+ str(len(coverpoints)) +' '+ \
    (str(16) if iflen == 16 else str(32) if iflen == 32 else str(64)) + '-bit coverpoints using Model B17 for '+opcode+' !'
    logger.debug(mess)
    coverpoints = comments_parser(coverpoints)

    return coverpoints

def ibm_b18(flen, iflen, opcode, ops, inxFlg=False, seed=-1):
    '''
    IBM Model B18 Definition:
            This model checks different cases where the multiplication causes some event
            in the product while the addition cancels this event.

            1. Product: Enumerate all options for LSB, Guard and Sticky bit.  Intermediate Result: Exact (Guard and Sticky are zero).
            2. Product: Take overflow values from (B4) "Overflow".  Intermediate Result: No overflow
            3. Product: Take underflow values from model (B5) "Underflow".  Intermediate Result: No underflow

    :param iflen: Size of the floating point source operands for the operation
    :param flen: Size of the floating point registers
    :param opcode: Opcode for which the coverpoints are to be generated
    :param ops: No. of Operands taken by the opcode
    :param seed: Initial seed value of the random library. (Predefined to -1. Actual value is set with respect to the opcode calling the function)

    :type iflen: int
    :type flen: int
    :type opcode: str
    :type ops: int
    :param seed: int

    Implementation:
            - Firstly, cancellation using the B3 model as base is performed.
            - Next model is the replica of the B4 model which takes into account the overflow of value for guard, round and sticky bits
            - The final model is obtained from the B5 model and different operations are done for underflow in decimal format.
            - The operand values are calculated using the intermediate results dataset and then passed into the extract_fields function to get individual fields in a floating point number (sign, exponent and mantissa).
            - Coverpoints are then appended with rounding mode “0” for that particular opcode.

    '''
    sanitise = get_sanitise_func(opcode)
    opcode = opcode.split('.')[0]
    getcontext().prec = 40

    if seed == -1:
        if opcode in 'fmadd':
            random.seed(0)
        elif opcode in 'fnmadd':
            random.seed(1)
        elif opcode in 'fmsub':
            random.seed(2)
        elif opcode in 'fnmsub':
            random.seed(3)
    else:
        random.seed(seed)

    # Cancellation of B3
    if iflen == 16:
        ieee754_maxnorm = float.hex(fields_dec_converter(16, hmaxnorm[0]))
        maxnum = float.fromhex(ieee754_maxnorm)
        ieee754_num = []
        lsb = []
        for i in fsubnorm+fnorm:
            if int(i[-1],16)%2 == 1:
                lsb.append('1')
                lsb.append('1')
            else:
                lsb.append('0')
                lsb.append('0')
            float_val = float.hex(fields_dec_converter(16,i))
            if float_val[0] != '-':
                ieee754_num.append(float_val)
                ieee754_num.append('-'+float_val)
            else:
                ieee754_num.append(float_val)
                ieee754_num.append(float_val[1:])
        ir_dataset = []
        for k in range(len(ieee754_num)):
            for i in range(2,16,2):
                grs = '{:04b}'.format(i)
                if ieee754_num[k][0] == '-': sign = '1'
                else: sign = '0'
                ir_dataset.append([ieee754_num[k].split('p')[0]+str(i)+'p'+ieee754_num[k].split('p')[1],' | Guard = '+grs[0]+' Sticky = '+grs[2]+' Sign = '+sign+' LSB = '+lsb[k]])
        for i in range(len(ir_dataset)):
            ir_dataset[i][0] = float.fromhex(ir_dataset[i][0])
    elif iflen == 32:
        ieee754_maxnorm = '0x1.7fffffp+127'
        maxnum = float.fromhex(ieee754_maxnorm)
        ieee754_num = []
        lsb = []
        for i in fsubnorm+fnorm:
            if int(i[-1],16)%2 == 1:
                lsb.append('1')
                lsb.append('1')
            else:
                lsb.append('0')
                lsb.append('0')
            float_val = float.hex(fields_dec_converter(32,i))
            if float_val[0] != '-':
                ieee754_num.append(float_val.split('p')[0][0:10]+'p'+float_val.split('p')[1])
                ieee754_num.append('-'+float_val.split('p')[0][0:10]+'p'+float_val.split('p')[1])
            else:
                ieee754_num.append(float_val.split('p')[0][0:11]+'p'+float_val.split('p')[1])
                ieee754_num.append(float_val.split('p')[0][1:11]+'p'+float_val.split('p')[1])

        ir_dataset = []
        for k in range(len(ieee754_num)):
            for i in range(2,16,2):
                grs = '{:04b}'.format(i)
                if ieee754_num[k][0] == '-': sign = '1'
                else: sign = '0'
                ir_dataset.append([ieee754_num[k].split('p')[0]+str(i)+'p'+ieee754_num[k].split('p')[1],' | Guard = '+grs[0]+' Sticky = '+grs[2]+' Sign = '+sign+' LSB = '+lsb[k] + ': Multiply add - Guard & Sticky Cancellation'])

        for i in range(len(ir_dataset)):
            ir_dataset[i][0] = float.fromhex(ir_dataset[i][0])

    elif iflen == 64:
        maxdec = '1.7976931348623157e+308'
        maxnum = float.fromhex('0x1.fffffffffffffp+1023')
        ieee754_num = []
        lsb = []
        for i in dsubnorm+dnorm:
            if int(i[-1],16)%2 == 1:
                lsb.append('1')
                lsb.append('1')
            else:
                lsb.append('0')
                lsb.append('0')
            float_val = str(fields_dec_converter(64,i))
            if float_val[0] != '-':
                ieee754_num.append(float_val)
                ieee754_num.append('-'+float_val)
            else:
                ieee754_num.append(float_val)
                ieee754_num.append(float_val[1:])

        ir_dataset = []
        for k in range(len(ieee754_num)):
            for i in range(2,16,2):
                grs = '{:04b}'.format(i)
                if ieee754_num[k][0] == '-': sign = '1'
                else: sign = '0'
                ir_dataset.append([str(Decimal(ieee754_num[k].split('e')[0])+Decimal(pow(i*16,-14)))+'e'+ieee754_num[k].split('e')[1],' | Guard = '+grs[0]+' Sticky = '+grs[2]+' Sign = '+sign+' LSB = '+lsb[k] + ': Multiply add - Guard & Sticky Cancellation'])

    b18_comb = []

    for i in range(len(ir_dataset)):
        rs1 = random.uniform(1,maxnum)
        res = '0x1.7ffff0p+100'
        res = float.fromhex(res)
        if opcode in 'fmadd':
            if iflen == 32 or iflen == 16:
                rs2 = ir_dataset[i][0]/rs1
                rs3 = res - ir_dataset[i][0]
            elif iflen == 64:
                rs2 = Decimal(ir_dataset[i][0])/Decimal(rs1)
                rs3 = Decimal(res) - Decimal(ir_dataset[i][0])
        elif opcode in 'fnmadd':
            if iflen == 32 or iflen == 16:
                rs2 = -1*ir_dataset[i][0]/rs1
                rs3 = -1*res + ir_dataset[i][0]
            elif iflen == 64:
                rs2 = -1*Decimal(ir_dataset[i][0])/Decimal(rs1)
                rs3 = -1*Decimal(res) - Decimal(ir_dataset[i][0])
        elif opcode in 'fmsub':
            if iflen == 32 or iflen == 16:
                rs2 = ir_dataset[i][0]/rs1
                rs3 = ir_dataset[i][0] - res
            elif iflen == 64:
                rs2 = Decimal(ir_dataset[i][0])/Decimal(rs1)
                rs3 = Decimal(ir_dataset[i][0]) - Decimal(res)
        elif opcode in 'fnmsub':
            if iflen == 32 or iflen == 16:
                rs2 = -1*ir_dataset[i][0]/rs1
                rs3 = res - ir_dataset[i][0]
            elif iflen == 64:
                rs2 = -1*Decimal(ir_dataset[i][0])/Decimal(rs1)
                rs3 = Decimal(res) - Decimal(ir_dataset[i][0])

        if(iflen==16):
            m = lambda rsx: float('inf') if rsx > fields_dec_converter(16, hmaxnorm[0]) \
            else float('-inf') if rsx < fields_dec_converter(16, hmaxnorm[1]) \
            else rsx
            x1 = m(rs1)
            x2 = m(rs2)
            x3 = m(rs3)
        elif(iflen==32):
            x1 = struct.unpack('f', struct.pack('f', rs1))[0]
            x2 = struct.unpack('f', struct.pack('f', rs2))[0]
            x3 = struct.unpack('f', struct.pack('f', rs3))[0]
        elif(iflen==64):
            x1 = rs1
            x2 = rs2
            x3 = rs3

        if opcode in ['fmadd','fnmadd','fmsub','fnmsub']:
            b18_comb.append((floatingPoint_tohex(iflen,float(rs1)),floatingPoint_tohex(iflen,float(rs2)),floatingPoint_tohex(iflen,float(rs3))))
    ir_dataset1 = ir_dataset

        # Cancellation of B4
    if iflen == 16:
        ieee754_maxnorm_p = float.hex(fields_dec_converter(16, hmaxnorm[0]))
        ieee754_maxnorm_n = float.hex(fields_dec_converter(16, hmaxnorm[1]))
        maxnum = float.fromhex(ieee754_maxnorm_p)
        ir_dataset = []
        for i in range(2,16,2):
            grs = '{:04b}'.format(i)
            ir_dataset.append([ieee754_maxnorm_p.split('p')[0]+str(i)+'p'+ieee754_maxnorm_p.split('p')[1],' | Guard = '+grs[0]+' Round = '+grs[1]+' Sticky = '+grs[2]+' --> Maxnorm + '+str(int(grs[0:3],2))+' ulp'])
            ir_dataset.append([ieee754_maxnorm_n.split('p')[0]+str(i)+'p'+ieee754_maxnorm_n.split('p')[1],' | Guard = '+grs[0]+' Round = '+grs[1]+' Sticky = '+grs[2]+' --> Maxnorm - '+str(int(grs[0:3],2))+' ulp'])
        for i in range(-3,4):
            ir_dataset.append([ieee754_maxnorm_p.split('p')[0]+'p'+str(15+i),' | Exponent = '+str(15+i)+' Number = +ve'])
            ir_dataset.append([ieee754_maxnorm_n.split('p')[0]+'p'+str(15+i),' | Exponent = '+str(15+i)+' Number = -ve'])
        for i in range(len(ir_dataset)):
            ir_dataset[i][0] = float.fromhex(ir_dataset[i][0])
    elif iflen == 32:
        ieee754_maxnorm_p = '0x1.7fffffp+127'
        ieee754_maxnorm_n = '0x1.7ffffep+127'
        maxnum = float.fromhex(ieee754_maxnorm_p)
        ir_dataset = []
        for i in range(2,16,2):
            grs = '{:04b}'.format(i)
            ir_dataset.append([ieee754_maxnorm_p.split('p')[0]+str(i)+'p'+ieee754_maxnorm_p.split('p')[1],' | Guard = '+grs[0]+' Round = '+grs[1]+' Sticky = '+grs[2]+' --> Maxnorm + '+str(int(grs[0:3],2))+' ulp' + ': Multiply add - Overflow Cancellation'])
            ir_dataset.append([ieee754_maxnorm_n.split('p')[0]+str(i)+'p'+ieee754_maxnorm_n.split('p')[1],' | Guard = '+grs[0]+' Round = '+grs[1]+' Sticky = '+grs[2]+' --> Maxnorm - '+str(int(grs[0:3],2))+' ulp' + ': Multiply add - Overflow Cancellation'])
        for i in range(len(ir_dataset)):
            ir_dataset[i][0] = float.fromhex(ir_dataset[i][0])
    elif iflen == 64:
        maxnum = float.fromhex('0x1.fffffffffffffp+1023')
        maxdec_p = str(maxnum)
        maxdec_n = str(float.fromhex('0x1.ffffffffffffep+1023'))
        ir_dataset = []
        for i in range(2,16,2):
            grs = '{:04b}'.format(i)
            ir_dataset.append([str(Decimal(maxdec_p.split('e')[0])+Decimal(pow(i*16,-14)))+'e'+maxdec_p.split('e')[1],' | Guard = '+grs[0]+' Round = '+grs[1]+' Sticky = '+grs[2]+' --> Maxnorm + '+str(int(grs[0:3],2))+' ulp' + ': Multiply add - Overflow Cancellation'])
            ir_dataset.append([str(Decimal(maxdec_n.split('e')[0])+Decimal(pow(i*16,-14)))+'e'+maxdec_n.split('e')[1],' | Guard = '+grs[0]+' Round = '+grs[1]+' Sticky = '+grs[2]+' --> Maxnorm - '+str(int(grs[0:3],2))+' ulp' + ': Multiply add - Overflow Cancellation'])

    for i in range(len(ir_dataset)):
        rs1 = random.uniform(1,maxnum)
        res = '0x1.7ffff0p+100'
        res = float.fromhex(res)
        if opcode in 'fmadd':
            if iflen == 32 or iflen == 16:
                rs2 = ir_dataset[i][0]/rs1
                rs3 = res - ir_dataset[i][0]
            elif iflen == 64:
                rs2 = Decimal(ir_dataset[i][0])/Decimal(rs1)
                rs3 = Decimal(res) - Decimal(ir_dataset[i][0])
        elif opcode in 'fnmadd':
            if iflen == 32 or iflen == 16:
                rs2 = -1*ir_dataset[i][0]/rs1
                rs3 = -1*res + ir_dataset[i][0]
            elif iflen == 64:
                rs2 = -1*Decimal(ir_dataset[i][0])/Decimal(rs1)
                rs3 = -1*Decimal(res) - Decimal(ir_dataset[i][0])
        elif opcode in 'fmsub':
            if iflen == 32 or iflen == 16:
                rs2 = ir_dataset[i][0]/rs1
                rs3 = ir_dataset[i][0] - res
            elif iflen == 64:
                rs2 = Decimal(ir_dataset[i][0])/Decimal(rs1)
                rs3 = Decimal(ir_dataset[i][0]) - Decimal(res)
        elif opcode in 'fnmsub':
            if iflen == 32 or iflen == 16:
                rs2 = -1*ir_dataset[i][0]/rs1
                rs3 = res - ir_dataset[i][0]
            elif iflen == 64:
                rs2 = -1*Decimal(ir_dataset[i][0])/Decimal(rs1)
                rs3 = Decimal(res) - Decimal(ir_dataset[i][0])

        if(iflen==16):
            m = lambda rsx: float('inf') if rsx > fields_dec_converter(16, hmaxnorm[0]) \
            else float('-inf') if rsx < fields_dec_converter(16, hmaxnorm[1]) \
            else rsx
            x1 = m(rs1)
            x2 = m(rs2)
            x3 = m(rs3)
        elif(iflen==32):
            x1 = struct.unpack('f', struct.pack('f', rs1))[0]
            x2 = struct.unpack('f', struct.pack('f', rs2))[0]
            x3 = struct.unpack('f', struct.pack('f', rs3))[0]
        elif(iflen==64):
            x1 = rs1
            x2 = rs2
            x3 = rs3

        if opcode in ['fmadd','fnmadd','fmsub','fnmsub']:
            b18_comb.append((floatingPoint_tohex(iflen,float(rs1)),floatingPoint_tohex(iflen,float(rs2)),floatingPoint_tohex(iflen,float(rs3))))
    ir_dataset2 = ir_dataset

    # Cancellation of B5
    if iflen == 16:
        ieee754_maxnorm = float.hex(fields_dec_converter(16, hmaxnorm[0]))
        maxnum = float.fromhex(ieee754_maxnorm)
        ieee754_minsubnorm = float.hex(fields_dec_converter(16, hminsubnorm[0]))
        ir_dataset = []
        for i in range(0,16,2):
            grs = '{:04b}'.format(i)
            ir_dataset.append([ieee754_minsubnorm.split('p')[0]+str(i)+'p'+ieee754_minsubnorm.split('p')[1],' | Guard = '+grs[0]+' Round = '+grs[1]+' Sticky = '+grs[2]+' --> Minsubnorm + '+str(int(grs[0:3],2))+' ulp'])
        ieee754_minnorm = '0x1.000000p-14'
        for i in range(0,16,2):
            grs = '{:04b}'.format(i)
            ir_dataset.append([ieee754_minnorm.split('p')[0]+str(i)+'p'+ieee754_minnorm.split('p')[1],' | Guard = '+grs[0]+' Round = '+grs[1]+' Sticky = '+grs[2]+' --> Minnorm + '+str(int(grs[0:3],2))+' ulp'])
        n = len(ir_dataset)
        for i in range(n):
            ir_dataset[i][0] = float.fromhex(ir_dataset[i][0])
            ir_dataset.append([-1*ir_dataset[i][0],ir_dataset[i][1]])
    elif iflen == 32:
        ieee754_maxnorm = '0x1.7fffffp+127'
        maxnum = float.fromhex(ieee754_maxnorm)
        ieee754_minsubnorm = '0x0.000001p-126'
        ir_dataset = []
        for i in range(0,16,2):
            grs = '{:04b}'.format(i)
            ir_dataset.append([ieee754_minsubnorm.split('p')[0]+str(i)+'p'+ieee754_minsubnorm.split('p')[1],' | Guard = '+grs[0]+' Round = '+grs[1]+' Sticky = '+grs[2]+' --> Minsubnorm + '+str(int(grs[0:3],2))+' ulp' + ': Multiply add - Underflow Cancellation'])
        ieee754_minnorm = '0x1.000000p-126'
        for i in range(0,16,2):
            grs = '{:04b}'.format(i)
            ir_dataset.append([ieee754_minnorm.split('p')[0]+str(i)+'p'+ieee754_minnorm.split('p')[1],' | Guard = '+grs[0]+' Round = '+grs[1]+' Sticky = '+grs[2]+' --> Minnorm + '+str(int(grs[0:3],2))+' ulp' + ': Multiply add - Underflow Cancellation'])
        n = len(ir_dataset)
        for i in range(n):
            ir_dataset[i][0] = float.fromhex(ir_dataset[i][0])
            ir_dataset.append([-1*ir_dataset[i][0],ir_dataset[i][1]])

    elif iflen == 64:
        maxdec = '1.7976931348623157e+308'
        maxnum = float.fromhex('0x1.fffffffffffffp+1023')
        minsubdec = '5e-324'
        ir_dataset = []
        for i in range(2,16,2):
            grs = '{:04b}'.format(i)
            ir_dataset.append([str(Decimal(minsubdec.split('e')[0])+Decimal(pow(i*16,-14)))+'e'+minsubdec.split('e')[1],' | Guard = '+grs[0]+' Round = '+grs[1]+' Sticky = '+grs[2]+' --> Minsubnorm + '+str(int(grs[0:3],2))+' ulp' + ': Multiply add - Underflow Cancellation'])
        minnormdec = '2.2250738585072014e-308'
        ir_dataset.append([minsubdec, ' | Guard = 0 Round = 0 Sticky = 0 --> Minsubnorm + 0 ulp'])
        ir_dataset.append([minnormdec,' | Guard = 0 Round = 0 Sticky = 0 --> Minnorm + 0 ulp'])
        for i in range(2,16,2):
            grs = '{:04b}'.format(i)
            ir_dataset.append([str(Decimal(minnormdec.split('e')[0])+Decimal(pow(i*16,-14)))+'e'+minnormdec.split('e')[1],' | Guard = '+grs[0]+' Round = '+grs[1]+' Sticky = '+grs[2]+' --> Minnorm + '+str(int(grs[0:3],2))+' ulp' + ': Multiply add - Underflow Cancellation'])
        n = len(ir_dataset)
        for i in range(n):
            ir_dataset.append(['-'+ir_dataset[i][0],ir_dataset[i][1]])

    for i in range(len(ir_dataset)):
        rs1 = random.uniform(1,maxnum)
        res = '0x1.7ffff0p+100'
        res = float.fromhex(res)
        if opcode in 'fmadd':
            if iflen == 32 or iflen == 16:
                rs2 = ir_dataset[i][0]/rs1
                rs3 = res - ir_dataset[i][0]
            elif iflen == 64:
                rs2 = Decimal(ir_dataset[i][0])/Decimal(rs1)
                rs3 = Decimal(res) - Decimal(ir_dataset[i][0])
        elif opcode in 'fnmadd':
            if iflen == 32 or iflen == 16:
                rs2 = -1*ir_dataset[i][0]/rs1
                rs3 = -1*res + ir_dataset[i][0]
            elif iflen == 64:
                rs2 = -1*Decimal(ir_dataset[i][0])/Decimal(rs1)
                rs3 = -1*Decimal(res) - Decimal(ir_dataset[i][0])
        elif opcode in 'fmsub':
            if iflen == 32 or iflen == 16:
                rs2 = ir_dataset[i][0]/rs1
                rs3 = ir_dataset[i][0] - res
            elif iflen == 64:
                rs2 = Decimal(ir_dataset[i][0])/Decimal(rs1)
                rs3 = Decimal(ir_dataset[i][0]) - Decimal(res)
        elif opcode in 'fnmsub':
            if iflen == 32 or iflen == 16:
                rs2 = -1*ir_dataset[i][0]/rs1
                rs3 = res - ir_dataset[i][0]
            elif iflen == 64:
                rs2 = -1*Decimal(ir_dataset[i][0])/Decimal(rs1)
                rs3 = Decimal(res) - Decimal(ir_dataset[i][0])

        if(iflen==16):
            m = lambda rsx: float('inf') if rsx > fields_dec_converter(16, hmaxnorm[0]) \
            else float('-inf') if rsx < fields_dec_converter(16, hmaxnorm[1]) \
            else rsx
            x1 = m(rs1)
            x2 = m(rs2)
            x3 = m(rs3)
        elif(iflen==32):
            x1 = struct.unpack('f', struct.pack('f', rs1))[0]
            x2 = struct.unpack('f', struct.pack('f', rs2))[0]
            x3 = struct.unpack('f', struct.pack('f', rs3))[0]
        elif(iflen==64):
            x1 = rs1
            x2 = rs2
            x3 = rs3

        if opcode in ['fmadd','fnmadd','fmsub','fnmsub']:
            b18_comb.append((floatingPoint_tohex(iflen,float(rs1)),floatingPoint_tohex(iflen,float(rs2)),floatingPoint_tohex(iflen,float(rs3))))
    ir_dataset3 = ir_dataset

    ir_dataset = ir_dataset1 + ir_dataset2 + ir_dataset3
    coverpoints = []
    k = 0
    for c in b18_comb:
        cvpt = ""
        for x in range(1, ops+1):
#                    cvpt += 'rs'+str(x)+'_val=='+str(c[x-1]) # uncomment this if you want rs1_val instead of individual fields
            cvpt += (extract_fields(iflen,c[x-1],str(x)))
            cvpt += " and "
        # cvpt += 'rm_val == 0'
        cvpt = sanitise(0,cvpt,iflen,flen,ops,inxFlg)
        if inxFlg == True:
            cvpt += sgn_prefix(iflen,flen,inxFlg,ops,cvpt)
        else:
            cvpt += ' # '
        cvpt += ' # '
        for y in range(1, ops+1):
            cvpt += 'rs'+str(y)+'_val=='
            cvpt += num_explain(iflen, c[y-1]) + '(' + str(c[y-1]) + ')'
            if(y != ops):
                cvpt += " and "
        cvpt += ir_dataset[k][1]
        coverpoints.append(cvpt)
        k=k+1

    mess='Generated'+ (' '*(5-len(str(len(coverpoints)))))+ str(len(coverpoints)) +' '+ \
    (str(16) if iflen == 16 else str(32) if iflen == 32 else str(64)) + '-bit coverpoints using Model B18 for '+opcode+' !'
    logger.debug(mess)
    coverpoints = comments_parser(coverpoints)

    return coverpoints

def ibm_b19(flen, iflen, opcode, ops, inxFlg=False, seed=-1):
    '''
    IBM Model B19 Definition:
            This model checks various possible differences between the two inputs.
            A test-case will be created for each combination of the following  table::

                First input    Second input    Difference between exponents    Difference between significands
                +Normal        +Normal         >0                              >0
                -Normal        -Normal         =0                              =0
                +SubNormal     +SubNormal      <0                              <0
                -SubNormal     -SubNormal
                0              0

    :param iflen: Size of the floating point source operands for the operation
    :param flen: Size of the floating point registers
    :param opcode: Opcode for which the coverpoints are to be generated
    :param ops: No. of Operands taken by the opcode
    :param seed: Initial seed value of the random library. (Predefined to -1. Actual value is set with respect to the opcode calling the function)

    :type iflen: int
    :type flen: int
    :type opcode: str
    :type ops: int
    :param seed: int

    Abstract Dataset Description:
            Operand1 {operation} Operand2  = Derived from the table above

    Implementation:
            - Normal (positive and negative), subnormal (positive and negative) arrays are randomly initialized within their respectively declared ranges.
            - The difference between exponents and significands are formed as per the conditions in the table.
            - All possible combinations of the table are used in creating the test-cases.
            - The operand values are then passed into the extract_fields function to get individual fields in a floating point number (sign, exponent and mantissa).
            - Coverpoints are then appended with all rounding modes for that particular opcode.

    '''
    sanitise = get_sanitise_func(opcode)

    opcode = opcode.split('.')[0]
    getcontext().prec = 40
    if iflen == 16:
        ieee754_maxnorm = float.hex(fields_dec_converter(16, hmaxnorm[0]))
        maxnum = float.fromhex(ieee754_maxnorm)
        ieee754_minsubnorm = float.hex(fields_dec_converter(16, hminsubnorm[0]))
        minsubnorm = float.fromhex(ieee754_minsubnorm)
        ieee754_maxsubnorm = float.hex(fields_dec_converter(16, hmaxsubnorm[0]))
        maxsubnorm = float.fromhex(ieee754_maxsubnorm)
        limnum = maxnum

    elif iflen == 32:
        ieee754_maxnorm = '0x1.7fffffp+127'
        maxnum = float.fromhex(ieee754_maxnorm)
        ieee754_minsubnorm = '0x0.000001p-126'
        minsubnorm = float.fromhex(ieee754_minsubnorm)
        ieee754_maxsubnorm = '0x0.7fffffp-126'
        maxsubnorm = float.fromhex(ieee754_maxsubnorm)
        limnum = maxnum

    elif iflen == 64:
        ieee754_maxnorm = '0x1.fffffffffffffp+1023'
        maxnum = float.fromhex(ieee754_maxnorm)
        ieee754_minsubnorm = '0x0.0000000000001p-1022'
        minsubnorm = float.fromhex(ieee754_minsubnorm)
        ieee754_maxsubnorm = '0x0.fffffffffffffp-1022'
        maxsubnorm = float.fromhex(ieee754_maxsubnorm)
        ieee754_limnum = '0x1.fffffffffffffp+507'
        limnum = float.fromhex(ieee754_limnum)

    if seed == -1:
        if opcode in 'fmin':
            random.seed(0)
        elif opcode in 'fmax':
            random.seed(1)
        elif opcode in 'flt':
            random.seed(2)
        elif opcode in 'feq':
            random.seed(3)
        elif opcode in 'fle':
            random.seed(3)
    else:
        random.seed(seed)

    b19_comb = []
    comment = []
    normal = []
    normal_neg = []
    sub_normal = []
    sub_normal_neg = []
    zero = [[0e0,'Zero']]
    for i in range(5):
        #normal.append(["{:e}".format(random.uniform(1,maxnum)),'Normal'])
        #normal_neg.append(["{:e}".format(random.uniform(-1*maxnum,-1)),'-Normal'])
        normal.append([random.uniform(1,maxnum),'Normal'])
        normal_neg.append([random.uniform(-1*maxnum,-1),'-Normal'])
        sub_normal.append([random.uniform(minsubnorm,maxsubnorm),'Subnormal'])
        sub_normal_neg.append([random.uniform(-1*maxsubnorm,-1*minsubnorm),'-Subnormal'])

    all_num = normal + normal_neg + sub_normal + sub_normal_neg + zero
    for i in all_num:
        for j in all_num:
            if i[0] != 0:
                i_sig = str(i[0]).split('e')[0]
                i_exp = str(i[0]).split('e')[1]
            else:
                i_sig = '0'
                i_exp = '0'
            if j[0] != 0:
                j_sig = str(j[0]).split('e')[0]
                j_exp = str(j[0]).split('e')[1]
            else:
                j_sig = '0'
                j_exp = '0'
            if float(i_sig) >= float(j_sig): sig_sign = '>='
            else: sig_sign = '<'
            if float(i_exp) >= float(j_exp): exp_sign = '>='
            else: exp_sign = '<'
            rs1 = float(i_sig+'e'+i_exp)
            rs2 = float(j_sig+'e'+j_exp)
            b19_comb.append((floatingPoint_tohex(iflen,float(rs1)),floatingPoint_tohex(iflen,float(rs2))))
            comment.append(' | rs1 --> ' + i[1] + ', rs2 --> ' + j[1] + ', rs1_sigificand ' + sig_sign + ' rs2_significand' + ', rs1_exp ' + exp_sign + ' rs2_exp')
            rs1 = float(i_sig+'e'+j_exp)
            rs2 = float(j_sig+'e'+i_exp)
            b19_comb.append((floatingPoint_tohex(iflen,float(rs1)),floatingPoint_tohex(iflen,float(rs2))))
            comment.append(' | rs1 --> ' + j[1] + ', rs2 --> ' + i[1] + ', rs1_sigificand ' + sig_sign + ' rs2_significand' + ', rs2_exp ' + exp_sign + ' rs1_exp')
            rs1 = float(j_sig+'e'+i_exp)
            rs2 = float(i_sig+'e'+j_exp)
            b19_comb.append((floatingPoint_tohex(iflen,float(rs1)),floatingPoint_tohex(iflen,float(rs2))))
            comment.append(' | rs1 --> ' + j[1] + ', rs2 --> ' + i[1] + ', rs2_sigificand ' + sig_sign + ' rs1_significand' + ', rs1_exp ' + exp_sign + ' rs2_exp')
            rs1 = float(i_sig+'e'+j_exp)
            rs2 = float(j_sig+'e'+j_exp)
            b19_comb.append((floatingPoint_tohex(iflen,float(rs1)),floatingPoint_tohex(iflen,float(rs2))))
            comment.append(' | rs1 --> ' + j[1] + ', rs2 --> ' + j[1] + ', rs1_sigificand ' + sig_sign + ' rs2_significand' + ', rs1_exp = rs2_exp')
            rs1 = float(i_sig+'e'+i_exp)
            rs2 = float(i_sig+'e'+j_exp)
            b19_comb.append((floatingPoint_tohex(iflen,float(rs1)),floatingPoint_tohex(iflen,float(rs2))))
            comment.append(' | rs1 --> ' + i[1] + ', rs2 --> ' + j[1] + ', rs1_sigificand = rs2_significand' + ', rs1_exp ' + exp_sign + ' rs2_exp')
            rs1 = float(i_sig+'e'+i_exp)
            rs2 = float(i_sig+'e'+i_exp)
            b19_comb.append((floatingPoint_tohex(iflen,float(rs1)),floatingPoint_tohex(iflen,float(rs2))))
            comment.append(' | rs1 --> ' + i[1] + ', rs2 --> ' + i[1] + ', rs1_sigificand = rs2_significand, rs1_exp = rs2_exp')

    coverpoints = []
    k = 0
    for c in b19_comb:
        cvpt = ""
        for x in range(1, 3):
#                    cvpt += 'rs'+str(x)+'_val=='+str(c[x-1]) # uncomment this if you want rs1_val instead of individual fields
            cvpt += (extract_fields(iflen,c[x-1],str(x)))
            cvpt += " and "
        if opcode in ["fadd","fsub","fmul","fdiv","fsqrt","fmadd","fnmadd","fmsub","fnmsub","fcvt","fmv"]:
            cvpt =  sanitise(0,cvpt,iflen,flen,ops,inxFlg)
           # cvpt += 'rm_val == 0'
        elif opcode in ["fclass","flt","fmax","fsgnjn","fle","fmin","fsgnj","feq",
                    "flw","fsw","fsgnjx","fld","fsd"]:
            cvpt =  sanitise(0,cvpt,iflen,flen,ops,inxFlg)
            #cvpt += 'rm_val == 1'
        # elif opcode in []:
            # cvpt = sanitise(2,cvpt,iflen,flen)
            # cvpt += 'rm_val == 2'
        if inxFlg == True:
            cvpt += sgn_prefix(iflen,flen,inxFlg,ops,cvpt)
        else:
            cvpt += ' # '
        cvpt += ' # '
        for y in range(1, ops+1):
            cvpt += 'rs'+str(y)+'_val=='
            cvpt += num_explain(iflen, c[y-1]) + '(' + str(c[y-1]) + ')'
            if(y != ops):
                cvpt += " and "
        cvpt += comment[k]
        coverpoints.append(cvpt)
        k += 1

    mess='Generated'+ (' '*(5-len(str(len(coverpoints)))))+ str(len(coverpoints)) +' '+ \
    (str(16) if iflen == 16 else str(32) if iflen == 32 else str(64)) + '-bit coverpoints using Model B19 for '+opcode+' !'
    logger.debug(mess)
    coverpoints = comments_parser(coverpoints)

    return coverpoints

def ibm_b20(flen, iflen, opcode, ops, inxFlg=False, seed=-1):
    '''
    IBM Model B20 Definition:
            This model will create test-cases such that the significand of the intermediate results will cover each of the following patterns:

            Mask on the intermediate result significand (excluding the leading “1” )

            .. code-block::

                xxx...xxx10
                xxx...xx100
                xxx...x1000
                …
                xx1...00000
                x10...00000
                100...00000
                000...00000

            The sticky bit of the intermediate result should always be 0. In case of the remainder operation, we will look at the result of the division in order to find the interesting test-cases.
            Operation: Divide, Square-root.

    :param iflen: Size of the floating point source operands for the operation
    :param flen: Size of the floating point registers
    :param opcode: Opcode for which the coverpoints are to be generated
    :param ops: No. of Operands taken by the opcode
    :param seed: Initial seed value of the random library. (Predefined to -1. Actual value is set with respect to the opcode calling the function)

    :type iflen: int
    :type flen: int
    :type opcode: str
    :type ops: int
    :param seed: int

    Abstract Dataset Description:
            Intermediate Results = [Random bits are taken initially to form xxx...xxx10. The pattern described above is then formed]
            Operand1 {operation} Operand2 = Intermediate Results

    Implementation:
            - A loop is initiated where random bits are obtained for which the subsequent sign, exponent is calculated for the intermediate value and stored in the ir_dataset.
            - Operand 1 (rs1) is randomly initialized in the range (1, limnum) and the subsequent operator value is found.
            - The operand values are then passed into the extract_fields function to get individual fields in a floating point number (sign, exponent and mantissa).
            - Coverpoints are then appended with all rounding modes for that particular opcode.

    '''
    sanitise = get_sanitise_func(opcode)
    opcode = opcode.split('.')[0]
    getcontext().prec = 60

    if seed == -1:
        if opcode in 'fdiv':
            random.seed(1)
        elif opcode in 'fsqrt':
            random.seed(2)
    else:
        random.seed(seed)

    if iflen == 16:
        ieee754_maxnorm = float.hex(fields_dec_converter(16, hmaxnorm[0]))
        maxnum = float.fromhex(ieee754_maxnorm)
        ieee754_minsubnorm = float.hex(fields_dec_converter(16, hminsubnorm[0]))
        minsubnorm = float.fromhex(ieee754_minsubnorm)
        ieee754_maxsubnorm = float.hex(fields_dec_converter(16, hmaxsubnorm[0]))
        maxsubnorm = float.fromhex(ieee754_maxsubnorm)
        limnum = maxnum
        ir_dataset = []
        for i in range(1,8,1):
            for k in range(5):
                bits = random.getrandbits(i)
                bits = bin(bits)[2:]
                front_zero = i-len(bits)
                bits = '0'*front_zero + bits
                trailing_zero = 9-i
                sig = bits+'1'+'0'*trailing_zero
                exp = random.getrandbits(5)
                exp = '{:05b}'.format(exp)
                
                sgn = random.getrandbits(1)
                sgn = '{:01b}'.format(sgn)
                
                ir_bin = ('0b'+sgn+exp+sig)
                ir = fields_dec_converter(flen,'0x'+hex(int('1'+ir_bin[2:],2))[3:])
                ir_dataset.append([ir, ' | Intermediate result significand: ' + sig + '  Pattern: ' + 'X'*i + '1' + '0'*trailing_zero])
        
        sig = '1'+'0'*9
        exp = random.getrandbits(5)
        exp = '{:05b}'.format(exp)
        sgn = random.getrandbits(1)
        sgn = '{:01b}'.format(sgn)
        ir_bin = ('0b'+sgn+exp+sig)
        ir = fields_dec_converter(flen,'0x'+hex(int('1'+ir_bin[2:],2))[3:])
        ir_dataset.append([ir, 'Intermediate result significand: '+ sig + '  Pattern: ' + '1' + '0'*22])
        
        sig = '0'*10
        exp = random.getrandbits(5)
        exp = '{:05b}'.format(exp)
        sgn = random.getrandbits(1)
        sgn = '{:01b}'.format(sgn)
        ir_bin = ('0b'+sgn+exp+sig)
        ir = fields_dec_converter(flen,'0x'+hex(int('1'+ir_bin[2:],2))[3:])
        ir_dataset.append([ir, 'Intermediate result significand: '+ sig + '  Pattern: ' + '0' + '0'*22])
    elif iflen == 32:
        ieee754_maxnorm = '0x1.7fffffp+127'
        maxnum = float.fromhex(ieee754_maxnorm)
        ieee754_minsubnorm = '0x0.000001p-126'
        minsubnorm = float.fromhex(ieee754_minsubnorm)
        ieee754_maxsubnorm = '0x0.7fffffp-126'
        maxsubnorm = float.fromhex(ieee754_maxsubnorm)
        limnum = maxnum
        ir_dataset = []
        for i in range(1,21,1):
            for k in range(5):
                bits = random.getrandbits(i)
                bits = bin(bits)[2:]
                front_zero = i-len(bits)
                bits = '0'*front_zero + bits
                trailing_zero = 22-i
                sig = bits+'1'+'0'*trailing_zero

                exp = random.getrandbits(8)
                exp = '{:08b}'.format(exp)

                sgn = random.getrandbits(1)
                sgn = '{:01b}'.format(sgn)

                ir_bin = ('0b'+sgn+exp+sig)
                ir = fields_dec_converter(iflen,'0x'+hex(int('1'+ir_bin[2:],2))[3:])
                ir_dataset.append([ir, ' | Intermediate result significand: ' + sig + '  Pattern: ' + 'X'*i + '1' + '0'*trailing_zero])

        sig = '1'+'0'*22
        exp = random.getrandbits(8)
        exp = '{:08b}'.format(exp)
        sgn = random.getrandbits(1)
        sgn = '{:01b}'.format(sgn)
        ir_bin = ('0b'+sgn+exp+sig)
        ir = fields_dec_converter(iflen,'0x'+hex(int('1'+ir_bin[2:],2))[3:])
        ir_dataset.append([ir, 'Intermediate result significand: '+ sig + '  Pattern: ' + '1' + '0'*22])

        sig = '0'*23
        exp = random.getrandbits(8)
        exp = '{:08b}'.format(exp)
        sgn = random.getrandbits(1)
        sgn = '{:01b}'.format(sgn)
        ir_bin = ('0b'+sgn+exp+sig)
        ir = fields_dec_converter(iflen,'0x'+hex(int('1'+ir_bin[2:],2))[3:])
        ir_dataset.append([ir, 'Intermediate result significand: '+ sig + '  Pattern: ' + '0' + '0'*22])

    elif iflen == 64:
        ieee754_maxnorm = '0x1.fffffffffffffp+1023'
        maxnum = float.fromhex(ieee754_maxnorm)
        ieee754_minsubnorm = '0x0.0000000000001p-1022'
        minsubnorm = float.fromhex(ieee754_minsubnorm)
        ieee754_maxsubnorm = '0x0.fffffffffffffp-1022'
        maxsubnorm = float.fromhex(ieee754_maxsubnorm)
        ieee754_limnum = '0x1.fffffffffffffp+507'
        limnum = float.fromhex(ieee754_limnum)
        ieee754_num = []
        ir_dataset = []
        for i in range(1,50,1):
            for k in range(5):
                bits = random.getrandbits(i)
                bits = bin(bits)[2:]
                front_zero = i-len(bits)
                bits = '0'*front_zero + bits
                trailing_zero = 51-i
                sig = bits+'1'+'0'*trailing_zero

                exp = random.getrandbits(11)
                exp = '{:011b}'.format(exp)

                sgn = random.getrandbits(1)
                sgn = '{:01b}'.format(sgn)

                ir_bin = ('0b'+sgn+exp+sig)
                ir = fields_dec_converter(iflen,'0x'+hex(int('1'+ir_bin[2:],2))[3:])
                ir_dataset.append([ir, ' | Intermediate result significand: ' + sig + '  Pattern: ' + 'X'*i + '1' + '0'*trailing_zero])

        sig = '1'+'0'*51
        exp = random.getrandbits(8)
        exp = '{:08b}'.format(exp)
        sgn = random.getrandbits(1)
        sgn = '{:01b}'.format(sgn)
        ir_bin = ('0b'+sgn+exp+sig)
        ir = fields_dec_converter(iflen,'0x'+hex(int('1'+ir_bin[2:],2))[3:])
        ir_dataset.append([ir, 'Intermediate result significand: '+ sig + '  Pattern: ' + '1' + '0'*51])

        sig = '0'*52
        exp = random.getrandbits(8)
        exp = '{:08b}'.format(exp)
        sgn = random.getrandbits(1)
        sgn = '{:01b}'.format(sgn)
        ir_bin = ('0b'+sgn+exp+sig)
        ir = fields_dec_converter(iflen,'0x'+hex(int('1'+ir_bin[2:],2))[3:])
        ir_dataset.append([ir, 'Intermediate result significand: ' + sig + '  Pattern: ' + '0' + '0'*52])

    b8_comb = []
    for i in range(len(ir_dataset)):
        rs1 = random.uniform(1, limnum)
        if opcode in 'fdiv':
            if iflen == 32 or iflen == 16:
                rs2 = rs1/ir_dataset[i][0]
            elif iflen == 64:
                rs2 = Decimal(rs1)/Decimal(ir_dataset[i][0])
        elif opcode in 'fsqrt':
            if iflen == 32 or iflen == 16:
                rs2 = ir_dataset[i][0]*ir_dataset[i][0]
            elif iflen == 64:
                rs2 = Decimal(ir_dataset[i][0])*Decimal(ir_dataset[i][0])

        if(iflen==16):
            m = lambda rsx: float('inf') if rsx > fields_dec_converter(16, hmaxnorm[0]) \
            else float('-inf') if rsx < fields_dec_converter(16, hmaxnorm[1]) \
            else rsx
            x1 = m(rs1)
            x2 = m(rs2)
        elif(iflen==32):
            x1 = struct.unpack('f', struct.pack('f', rs1))[0]
            x2 = struct.unpack('f', struct.pack('f', rs2))[0]
        elif(iflen==64):
            x1 = rs1
            x2 = rs2

        if opcode in ['fdiv']:
            b8_comb.append((floatingPoint_tohex(iflen,float(rs1)),floatingPoint_tohex(iflen,float(rs2))))
        elif opcode in 'fsqrt':
            b8_comb.append((floatingPoint_tohex(iflen,float(rs2)),))

    coverpoints = []
    k=0
    for c in b8_comb:
        cvpt = ""
        for x in range(1, ops+1):
#                    cvpt += 'rs'+str(x)+'_val=='+str(c[x-1]) # uncomment this if you want rs1_val instead of individual fields
            cvpt += (extract_fields(iflen,c[x-1],str(x)))
            cvpt += " and "
        cvpt = sanitise(0,cvpt,iflen,flen,ops,inxFlg)
        # cvpt += 'rm_val == 0'
        if inxFlg == True:
            cvpt += sgn_prefix(iflen,flen,inxFlg,ops,cvpt)
        else:
            cvpt += ' # '
        cvpt += ' # '
        for y in range(1, ops+1):
            cvpt += 'rs'+str(y)+'_val=='
            cvpt += num_explain(iflen, c[y-1]) + '(' + str(c[y-1]) + ')'
            if(y != ops):
                cvpt += " and "
        cvpt += ir_dataset[k][1]
        coverpoints.append(cvpt)
        k=k+1

    mess='Generated'+ (' '*(5-len(str(len(coverpoints)))))+ str(len(coverpoints)) +' '+ \
    (str(16) if iflen == 16 else str(32) if iflen == 32 else str(64)) + '-bit coverpoints using Model B20 for '+opcode+' !'
    logger.debug(mess)
    coverpoints = comments_parser(coverpoints)

    return coverpoints

def ibm_b21(flen, iflen, opcode, ops, inxFlg=False):
    '''
    IBM Model B21 Definition:
            This model will test the Divide By Zero exception flag. For the operations divide and remainder, a test case will be created for each of the possible combinations from the following table:

            First Operand : 0, Random non-zero number, Infinity, NaN
            Second Operand : 0, Random non-zero number, Infinity, NaN

            Operation: Divide, Remainder

    :param iflen: Size of the floating point source operands for the operation
    :param flen: Size of the floating point registers
    :param opcode: Opcode for which the coverpoints are to be generated
    :param ops: No. of Operands taken by the opcode

    :type iflen: int
    :type flen: int
    :type opcode: str
    :type ops: int

    Abstract Dataset Description:
            Final Results = [ Zero, Subnorm, Norm, Infinity, DefaultNaN, QNaN, SNaN ]

    Implementation:
            - The basic_types dataset is accumulated with the combinations of the abstract dataset description.
            - Using python’s package itertools, a permutation of all possible combinations as a pair is computed for basic_types dataset..
            - The operand values are then passed into the extract_fields function to get individual fields in a floating point number (sign, exponent and mantissa).
            - Coverpoints are then appended with all rounding modes for that particular opcode.
    '''
    sanitise = get_sanitise_func(opcode)
    if iflen == 16:
        basic_types = hzero + hsubnorm + hnorm +\
            hinfinity + hdefaultnan + [hqnan[0], hqnan[-1]] + \
                [hsnan[0], hsnan[-1]]
    elif iflen == 32:
        basic_types = fzero + fsubnorm + fnorm + finfinity + fdefaultnan + [fqnan[0], fqnan[3]] + \
                [fsnan[0], fsnan[3]]
    elif iflen == 64:
        basic_types = dzero + dsubnorm + dnorm +\
            dinfinity + ddefaultnan + [dqnan[0], dqnan[1]] + \
            [dsnan[0], dsnan[1]]
    else:
        logger.error('Invalid iflen value!')
        sys.exit(1)

    # the following creates a cross product for ops number of variables
    b21_comb = list(itertools.product(*ops*[basic_types]))
    coverpoints = []
    for c in b21_comb:
        cvpt = ""
        for x in range(1, ops+1):
#            cvpt += 'rs'+str(x)+'_val=='+str(c[x-1]) # uncomment this if you want rs1_val instead of individual fields
            cvpt += (extract_fields(iflen,c[x-1],str(x)))
            cvpt += " and "
        if opcode.split('.')[0] in ["fdiv"]:
            cvpt =  sanitise(0,cvpt,iflen,flen,ops,inxFlg)
        if inxFlg == True:
            cvpt += sgn_prefix(iflen,flen,inxFlg,ops,cvpt)
        else:
            cvpt += ' # '
        cvpt += ' # '
        for y in range(1, ops+1):
            cvpt += 'rs'+str(y)+'_val=='
            cvpt += num_explain(iflen, c[y-1]) + '(' + str(c[y-1]) + ')'
            if(y != ops):
                cvpt += " and "
        coverpoints.append(cvpt)

    mess='Generated'+ (' '*(5-len(str(len(coverpoints)))))+ str(len(coverpoints)) +' '+ \
    (str(16) if iflen == 16 else str(32) if iflen == 32 else str(64)) + '-bit coverpoints using Model B21 for '+opcode+' !'
    logger.debug(mess)
    coverpoints = comments_parser(coverpoints)

    return coverpoints

def ibm_b22(flen, iflen, opcode, ops, inxFlg=False, seed=10):
    '''
    IBM Model B22 Definition:
            This model creates test cases for each of the following exponents (unbiased):

            1. Smaller than -3
            2. All the values in the range [-3, integer width+3]
            3. Larger than integer width + 3

            For each exponent two cases will be randomly chosen, positive and negative.

    :param iflen: Size of the floating point source operands for the operation
    :param flen: Size of the floating point registers
    :param opcode: Opcode for which the coverpoints are to be generated
    :param ops: No. of Operands taken by the opcode
    :param seed: Initial seed value of the random library. (Predefined to -1. Actual value is set with respect to the opcode calling the function)

    :type iflen: int
    :type flen: int
    :type opcode: str
    :type ops: int
    :param seed: int

    Abstract Dataset Description:
            Operand1 = [Smaller than -3, All the values in the range [-3, integer width+3], Larger than integer width + 3]

    Implementation:
            - Random bits are calculated and appended to obtain the exponent ranges defined in case 2.
            - To satisfy case 1 and case 3, similar steps are performed outside the loop and hence updated in the loop.
            - The operand values are then passed into the extract_fields function to get individual fields in a floating point number (sign, exponent and mantissa).
            - Coverpoints are then appended with all rounding modes for that particular opcode.

    '''
    sanitise = get_sanitise_func(opcode)

    opcode = opcode.split('.')[0] + '.' + opcode.split('.')[1]
    if opcode[2] == 'h': iflen = 16
    elif opcode[2] == 's': iflen = 32
    elif opcode[2] == 'd': iflen = 64
    getcontext().prec = 40
    xlen = 0

    if opcode in 'fcvt.w':
        xlen = 32
    elif opcode in 'fcvt.l':
        xlen = 64
    elif opcode in 'fcvt.wu':
        xlen = 32
    elif opcode in 'fcvt.lu':
        xlen = 64

    if seed == -1:
        if opcode in 'fcvt.w':
            random.seed(0)
        elif opcode in 'fcvt.l':
            random.seed(1)
        elif opcode in 'fcvt.wu':
            random.seed(2)
        elif opcode in 'fcvt.lu':
            random.seed(3)
    else:
        random.seed(seed)

    b22_comb = []

    if iflen == 16:
        ieee754_maxnorm = float.hex(fields_dec_converter(16, hmaxnorm[0]))
        maxnum = float.fromhex(ieee754_maxnorm)
        ieee754_minsubnorm = float.hex(fields_dec_converter(16, hminsubnorm[0]))
        minsubnorm = float.fromhex(ieee754_minsubnorm)
        ieee754_maxsubnorm = float.hex(fields_dec_converter(16, hmaxsubnorm[0]))
        maxsubnorm = float.fromhex(ieee754_maxsubnorm)
        limnum = maxnum
        op_dataset = []
        for i in range(12,xlen+18,1):
            bits = random.getrandbits(10)
            bits = bin(bits)[2:]
            front_zero = 10-len(bits)
            sig = '0'*front_zero + bits

            exp = i
            exp = '{:05b}'.format(exp)

            sgn = random.getrandbits(1)
            sgn = '{:01b}'.format(sgn)

            ir_bin = ('0b'+sgn+exp+sig)
            op = fields_dec_converter(iflen,'0x'+hex(int('1'+ir_bin[2:],2))[3:])
            op_dataset.append([op, ' | Exponent: ' + str(int(exp,2)-15) + ', Exponent in the range [-3, integer width+3]'])
            b22_comb.append((floatingPoint_tohex(iflen,float(op)),))

        bits = random.getrandbits(10)
        bits = bin(bits)[2:]
        front_zero = 10-len(bits)
        sig = '0'*front_zero + bits
        exp = random.randint(0,124)
        exp = '{:05b}'.format(exp)
        sgn = random.getrandbits(1)
        sgn = '{:01b}'.format(sgn)
        ir_bin = ('0b'+sgn+exp+sig)
        op = fields_dec_converter(iflen,'0x'+hex(int('1'+ir_bin[2:],2))[3:])
        op_dataset.append([op, ' | Exponent: ' + str(int(exp,2)-15) + ', Exponent less than -3'])
        b22_comb.append((floatingPoint_tohex(iflen,float(op)),))
        
        bits = random.getrandbits(10)
        bits = bin(bits)[2:]
        front_zero = 10-len(bits)
        sig = '0'*front_zero + bits
        exp = random.randint(xlen+130,255)
        exp = '{:05b}'.format(exp)
        sgn = random.getrandbits(1)
        sgn = '{:01b}'.format(sgn)
        ir_bin = ('0b'+sgn+exp+sig)
        op = fields_dec_converter(iflen,'0x'+hex(int('1'+ir_bin[2:],2))[3:])
        op_dataset.append([op, ' | Exponent: ' + str(int(exp,2)-15) + ', Exponent greater than (integer width+3)'])
        b22_comb.append((floatingPoint_tohex(iflen,float(op)),))
    elif iflen == 32:
        ieee754_maxnorm = '0x1.7fffffp+127'
        maxnum = float.fromhex(ieee754_maxnorm)
        ieee754_minsubnorm = '0x0.000001p-126'
        minsubnorm = float.fromhex(ieee754_minsubnorm)
        ieee754_maxsubnorm = '0x0.7fffffp-126'
        maxsubnorm = float.fromhex(ieee754_maxsubnorm)
        limnum = maxnum
        op_dataset = []
        for i in range(124,xlen+130,1):
            bits = random.getrandbits(23)
            bits = bin(bits)[2:]
            front_zero = 23-len(bits)
            sig = '0'*front_zero + bits

            exp = i
            exp = '{:08b}'.format(exp)

            sgn = random.getrandbits(1)
            sgn = '{:01b}'.format(sgn)

            ir_bin = ('0b'+sgn+exp+sig)
            op = fields_dec_converter(iflen,'0x'+hex(int('1'+ir_bin[2:],2))[3:])
            op_dataset.append([op, ' | Exponent: ' + str(int(exp,2)-127) + ', Exponent in the range [-3, integer width+3]'])
            b22_comb.append((floatingPoint_tohex(iflen,float(op)),))

        bits = random.getrandbits(23)
        bits = bin(bits)[2:]
        front_zero = 23-len(bits)
        sig = '0'*front_zero + bits
        exp = random.randint(0,124)
        exp = '{:08b}'.format(exp)
        sgn = random.getrandbits(1)
        sgn = '{:01b}'.format(sgn)
        ir_bin = ('0b'+sgn+exp+sig)
        op = fields_dec_converter(iflen,'0x'+hex(int('1'+ir_bin[2:],2))[3:])
        op_dataset.append([op, ' | Exponent: ' + str(int(exp,2)-127) + ', Exponent less than -3'])
        b22_comb.append((floatingPoint_tohex(iflen,float(op)),))

        bits = random.getrandbits(23)
        bits = bin(bits)[2:]
        front_zero = 23-len(bits)
        sig = '0'*front_zero + bits
        exp = random.randint(xlen+130,255)
        exp = '{:08b}'.format(exp)
        sgn = random.getrandbits(1)
        sgn = '{:01b}'.format(sgn)
        ir_bin = ('0b'+sgn+exp+sig)
        op = fields_dec_converter(iflen,'0x'+hex(int('1'+ir_bin[2:],2))[3:])
        op_dataset.append([op, ' | Exponent: ' + str(int(exp,2)-127) + ', Exponent greater than (integer width+3)'])
        b22_comb.append((floatingPoint_tohex(iflen,float(op)),))

    elif iflen == 64:
        ieee754_maxnorm = '0x1.fffffffffffffp+1023'
        maxnum = float.fromhex(ieee754_maxnorm)
        ieee754_minsubnorm = '0x0.0000000000001p-1022'
        minsubnorm = float.fromhex(ieee754_minsubnorm)
        ieee754_maxsubnorm = '0x0.fffffffffffffp-1022'
        maxsubnorm = float.fromhex(ieee754_maxsubnorm)
        ieee754_limnum = '0x1.fffffffffffffp+507'
        limnum = float.fromhex(ieee754_limnum)
        op_dataset = []
        for i in range(1020,xlen+1026,1):
            bits = random.getrandbits(52)
            bits = bin(bits)[2:]
            front_zero = 52-len(bits)
            sig = '0'*front_zero + bits

            exp = i
            exp = '{:011b}'.format(exp)

            sgn = random.getrandbits(1)
            sgn = '{:01b}'.format(sgn)

            ir_bin = ('0b'+sgn+exp+sig)
            op = fields_dec_converter(iflen,'0x'+hex(int('1'+ir_bin[2:],2))[3:])
            op_dataset.append([op, ' | Exponent: ' + str(int(exp,2)-1023) + ', Exponent in the range [-3, integer width+3]'])
            b22_comb.append((floatingPoint_tohex(iflen,float(op)),))

        bits = random.getrandbits(52)
        bits = bin(bits)[2:]
        front_zero = 52-len(bits)
        sig = '0'*front_zero + bits
        exp = random.randint(0,1020)
        exp = '{:011b}'.format(exp)
        sgn = random.getrandbits(1)
        sgn = '{:01b}'.format(sgn)
        ir_bin = ('0b'+sgn+exp+sig)
        op = fields_dec_converter(iflen,'0x'+hex(int('1'+ir_bin[2:],2))[3:])
        op_dataset.append([op, ' | Exponent: ' + str(int(exp,2)-1023) + ', Exponent less than -3'])
        b22_comb.append((floatingPoint_tohex(iflen,float(op)),))

        bits = random.getrandbits(52)
        bits = bin(bits)[2:]
        front_zero = 52-len(bits)
        sig = '0'*front_zero + bits
        exp = random.randint(xlen+1026,2047)
        exp = '{:011b}'.format(exp)
        sgn = random.getrandbits(1)
        sgn = '{:01b}'.format(sgn)
        ir_bin = ('0b'+sgn+exp+sig)
        op = fields_dec_converter(iflen,'0x'+hex(int('1'+ir_bin[2:],2))[3:])
        op_dataset.append([op, ' | Exponent: ' + str(int(exp,2)-1023) + ', Exponent greater than (integer width+3)'])
        b22_comb.append((floatingPoint_tohex(iflen,float(op)),))

    coverpoints = []
    k=0
    for c in b22_comb:
        cvpt = ""
        for x in range(1, 2):
#                    cvpt += 'rs'+str(x)+'_val=='+str(c[x-1]) # uncomment this if you want rs1_val instead of individual fields
            cvpt += (extract_fields(iflen,c[x-1],str(x)))
            cvpt += " and "
        # cvpt += 'rm_val == 0'
        cvpt = sanitise(0,cvpt,iflen,flen,ops,inxFlg)
        if inxFlg == True:
            cvpt += sgn_prefix(iflen,flen,inxFlg,ops,cvpt)
        else:
            cvpt += ' # '
        cvpt += ' # '
        for y in range(1, ops+1):
            cvpt += 'rs'+str(y)+'_val=='
            cvpt += num_explain(iflen, c[y-1]) + '(' + str(c[y-1]) + ')'
            if(y != ops):
                cvpt += " and "
        cvpt += op_dataset[k][1]
        coverpoints.append(cvpt)
        k=k+1

    mess='Generated'+ (' '*(5-len(str(len(coverpoints)))))+ str(len(coverpoints)) +' '+ \
    (str(16) if iflen == 16 else str(32) if iflen == 32 else str(64)) + '-bit coverpoints using Model B22 for '+opcode+' !'
    logger.debug(mess)
    coverpoints = comments_parser(coverpoints)

    return coverpoints

def ibm_b23(flen, iflen, opcode, ops, inxFlg=False):
    '''
    IBM Model B23 Definition:
            This model creates boundary cases for the rounding to integers that might cause Overflow.
            A test case will be created with inputs equal to the maximum integer number in the destination's format (MaxInt), or close to it. In particular, the following FP numbers will be used:

            1. ±MaxInt
            2. ±MaxInt ± 0.01 (¼)
            3. ±MaxInt ± 0.1 (½)
            4. ±MaxInt ± 0.11 (¾)
            5. ±MaxInt ± 1

            Rounding Mode: All

    :param iflen: Size of the floating point source operands for the operation
    :param flen: Size of the floating point registers
    :param opcode: Opcode for which the coverpoints are to be generated
    :param ops: No. of Operands taken by the opcode

    :type iflen: int
    :type flen: int
    :type opcode: str
    :type ops: int

    Abstract Dataset Description:
            Operand 1 = [ MaxInt-4, MaxInt+5 ]

    Implementation:
            - In the range of (-4,5), the dataset array is appended with the hexadecimal equivalent of maxnum plus the iteration number in a string format. The next highest encoding of the hexadecimal value is calculated.
            - This is done with different values of maxnum for iflen=32 or iflen=64.
            - Since this model is meant for floating point conversion instructions, only one operand is expected.
            - The operand values are then passed into the extract_fields function to get individual fields in a floating point number (sign, exponent and mantissa).
            - Coverpoints are then appended with all rounding modes for that particular opcode.

    '''
    sanitise = get_sanitise_func(opcode)

    opcode = opcode.split('.')[0] + '.' + opcode.split('.')[1]

    getcontext().prec = 40

    operations = ['+','-']
    nums = [0,100,200,800,1600]
    dataset = []

    if iflen == 16:
        maxnum = 0x7800

        for i in range(-4,5):
            dataset.append((hex(int(maxnum)+i),"| MaxInt + ({})".format(str(i))))
	
    elif iflen == 32:
        maxnum = 0x4f000000                                        # MaxInt (2**31-1) in IEEE 754 Floating Point Representation

        for i in range(-4,5):
                    dataset.append((hex(int(maxnum)+i),"| MaxInt + ({})".format(str(i))))
    elif iflen == 64:
        maxnum = 0x43e0000000000000

        for i in range(-4,5):
                    dataset.append((hex(int(maxnum)+i),"| MaxInt + ({})".format(str(i))))

    coverpoints = []
    k=0
    for c in dataset:
        for rm in range(0,5):
            cvpt = ""
            for x in range(1, ops+1):
                cvpt += (extract_fields(iflen,c[x-1],str(x)))
                cvpt += " and "
            # cvpt += 'rm_val == '
            if "fmv" in opcode or opcode in "fcvt.d.s":
                cvpt = sanitise(0,cvpt,iflen,flen,ops,inxFlg)
                # cvpt += '0'
            else:
                cvpt = sanitise(rm,cvpt,iflen,flen,ops,inxFlg)
                # cvpt += str(rm)
            if inxFlg == True:
                cvpt += sgn_prefix(iflen,flen,inxFlg,ops,cvpt)
            else:
                cvpt += ' # '
            cvpt += ' # '
            for y in range(1, ops+1):
                cvpt += 'rs'+str(y)+'_val=='
                cvpt += num_explain(iflen, c[y-1]) + '(' + str(c[y-1]) + ')'
                if(y != ops):
                    cvpt += " and "
            cvpt += " "+c[1]
            coverpoints.append(cvpt)
            k=k+1

    mess='Generated'+ (' '*(5-len(str(len(coverpoints)))))+ str(len(coverpoints)) +' '+\
    (str(16) if iflen == 16 else str(32) if iflen == 32 else str(64)) + '-bit coverpoints using Model B23 for '+opcode+' !'
    logger.debug(mess)
    coverpoints = comments_parser(coverpoints)

    return (coverpoints)

def ibm_b24(flen, iflen, opcode, ops, inxFlg=False):
    '''
    IBM Model B24 Definition:
            This model creates boundary cases for rounding to integer that might cause major loss of accuracy.

            A test-case will be created for each of the following inputs:

            1. ±0
            2. ±0 ± 0.01 (¼)
            3. ±0 ± 0.1 (½)
            4. ±0 ± 0.11 (¾)
            5. ±1
            6. ±1 + 0.01 (¼)
            7. ±1 + 0.1 (½)
            8. ±1 + 0.11 (¾)

            Rounding Mode: All

    :param iflen: Size of the floating point source operands for the operation
    :param flen: Size of the floating point registers
    :param opcode: Opcode for which the coverpoints are to be generated
    :param ops: No. of Operands taken by the opcode

    :type iflen: int
    :type flen: int
    :type opcode: str
    :type ops: int

    Abstract Dataset Description:
            Operand 1 = [±0,  ±0 ± 0.01, ±0 ± 0.1, ±0 ± 0.11, ±1, ±1 + 0.01, ±1 + 0.1, ±1 + 0.11]

    Implementation:
            - A nested loop with 4 stages is initiated to iterate each element in minimums, nums, operations1 and operations2 for the two operands. This is done to form the dataset defined above.
            - Depending on the value of iflen, these values are then converted into their respective IEEE 754 hexadecimal values.
            - The operand values are then passed into the extract_fields function to get individual fields in a floating point number (sign, exponent and mantissa).
            - Coverpoints are then appended with all rounding modes for that particular opcode.

    '''
    sanitise = get_sanitise_func(opcode)

    opcode = opcode.split('.')[0] + '.' + opcode.split('.')[1]

    getcontext().prec = 40

    operations = ['+','-']
    nums = [0,0.01,0.1,0.11]
    minnums = [0,1]
    dataset = []

    for minnum in minnums:
        for num in nums:
            for op1 in operations:
                for op2 in operations:
                    dataset.append((eval(op1+str(minnum)+op2+str(num)),op1+str(minnum)+op2+str(num)))

    b24_comb = []

    for data in dataset:
        t = "{:e}".format(data[0])
        b24_comb.append((floatingPoint_tohex(iflen,float(t)),data[1]))

    b24_comb = OrderedSet(b24_comb)

    coverpoints = []
    k=0
    for c in b24_comb:
        for rm in range(0,5):
            cvpt = ""
            for x in range(1, ops+1):
                cvpt += (extract_fields(iflen,c[x-1],str(x)))
                cvpt += " and "
            # cvpt += 'rm_val == '
            if "fmv" in opcode or opcode in "fcvt.d.s":
                cvpt = sanitise(0,cvpt,iflen,flen,ops,inxFlg)
                # cvpt += '0'
            else:
                cvpt = sanitise(rm,cvpt,iflen,flen,ops,inxFlg)
                # cvpt += str(rm)
            if inxFlg == True:
                cvpt += sgn_prefix(iflen,flen,inxFlg,ops,cvpt)
            else:
                cvpt += ' # '
            cvpt += ' # '
            for y in range(1, ops+1):
                cvpt += 'rs'+str(y)+'_val=='
                cvpt += num_explain(iflen, c[y-1]) + '(' + str(c[y-1]) + ')'
                if(y != ops):
                    cvpt += " and "
            cvpt += " | "+c[1]
            coverpoints.append(cvpt)
            k=k+1

    mess='Generated'+ (' '*(5-len(str(len(coverpoints)))))+ str(len(coverpoints)) +' '+\
    (str(16) if iflen == 16 else str(32) if iflen == 32 else str(64)) + '-bit coverpoints using Model B24 for '+opcode+' !'
    logger.debug(mess)
    coverpoints = comments_parser(coverpoints)

    return (coverpoints)

def ibm_b25(flen, iflen, opcode, ops, inxFlg=False, seed=10):
    '''
    IBM Model B25 Definition:
            This model creates a test-case for each of the following inputs(wherever applicable):

            1. ±MaxInt
            2. ±0
            3. ±1
            4. Random number

    :param flen: Size of the floating point registers
    :param iflen: Size of the floating point source operands for the operation
    :param opcode: Opcode for which the coverpoints are to be generated
    :param ops: No. of operands taken by the opcode
    :param seed: Initial seed value of the random library. (Predefined to 10)

    :type iflen: int
    :type flen: int
    :type opcode: str
    :type ops: int
    :param seed: int

    Abstract Dataset Description:
            Operand 1 = [±MaxInt, ±0, ±1, Random number]

    Implementation:
            - The dataset is formed as per the dataset description.
            - rand_num is initialized to a random number in the range (1, maxnum).
            - Since this model is for an integer to floating point conversion instruction, the operands are presented in decimal format.
            - Coverpoints are then appended with all rounding modes for that particular opcode.

    '''
    sanitise = get_sanitise_func(opcode)
    is_unsigned = opcode.endswith("u")
    random.seed(seed)
    getcontext().prec = 40

    operations = ['+','-']
    nums = [0,0.01,0.1,0.11]

    dataset = [(0,"0"),(1,"1")] +( [(-1,"-1")] if not is_unsigned else [])

    bitwidth = iflen if is_unsigned else iflen-1
    maxnum = 2**(bitwidth)-1

    dataset.append((maxnum,"MaxInt"))
    if not is_unsigned:
        dataset.append((-1*maxnum,"-MaxInt"))
    rand_num = int(random.uniform(1,maxnum))
    dataset.append((rand_num,"+ve Random Number"))
    if not is_unsigned:
        dataset.append((-1*rand_num,"-ve Random Number"))

    b25_comb = []

    for data in dataset:
        b25_comb.append((int(data[0]),data[1]))

    coverpoints = []
    k=0
    for c in b25_comb:
        for rm in range(0,5):
            cvpt = ""
            for x in range(1, ops+1):
                cvpt += "rs1_val == "+str(c[x-1])
                cvpt += " and "
            # cvpt += 'rm_val == '
            if "fmv" in opcode or opcode in "fcvt.d.wu":
                cvpt = sanitise(0,cvpt,iflen,flen,ops,inxFlg)
                if inxFlg == True:
                    cvpt += sgn_prefix(iflen,flen,inxFlg,ops,cvpt)
                else:
                    cvpt += ' # '
                # cvpt += str(0)
            else:
                cvpt = sanitise(rm,cvpt,iflen,flen,ops,inxFlg)
                if inxFlg == True:
                    cvpt += sgn_prefix(iflen,flen,inxFlg,ops,cvpt)
                else:
                    cvpt += ' # '
            
                # cvpt += str(rm)
            cvpt += ' # Number = '
            cvpt += c[1]
            coverpoints.append(cvpt)
            k=k+1

    mess='Generated'+ (' '*(5-len(str(len(coverpoints)))))+ str(len(coverpoints)) +' '+\
    (str(32) if iflen == 32 else str(64)) + '-bit coverpoints using Model B25 for '+opcode+' !'
    logger.debug(mess)
    coverpoints = comments_parser(coverpoints)

    return (coverpoints)

def ibm_b26(xlen, opcode, ops, inxFlg=False, seed=10):
    '''
    IBM Model B26 Definition:
            This model creates a test-case for each possible value of the number of significant bits in the input operand (which is an integer). A test is created with an example from each of the following
            ranges: [0], [1], [2,3], [4,7], [8,15], …, [(MaxInt+1)/2, MaxInt]

    :param xlen: Size of the integer registers
    :param opcode: Opcode for which the coverpoints are to be generated
    :param ops: No. of Operands taken by the opcode
    :param seed: Initial seed value of the random library. (Predefined to 10)

    :type xlen: int
    :type opcode: str
    :type ops: int
    :param seed: int

    Abstract Dataset Description:
            Operand 1 = Random number in [0], [1], [2,3], [4,7], [8,15], …, [(MaxInt+1)/2, MaxInt]

    Implementation:
            - A random number is chosen in the ranges defined above.
            - Since this model is for an integer to floating point conversion instruction, the operands are presented in decimal format.
            - Coverpoints are then appended with all rounding modes for that particular opcode.

    '''
    sanitise = get_sanitise_func(opcode)
    random.seed(seed)
    dataset = [(0," # Number in [0]"),(1," # Number in [1]")]

    i = 3
    while(i<=2**(xlen-1)-1):
        rand_num = random.randint(int((i+1)/2),i)
        dataset.append((rand_num," # Random number chosen in the range: ["+str(int((i+1)/2))+", "+str(i)+"]"))
        i = i*2+1

    coverpoints = []
    k=0
    for c in dataset:
        for rm in range(0,5):
            cvpt = ""
            for x in range(1, ops+1):
                cvpt += "rs1_val == "+str(c[x-1])
                cvpt += " and "
            # cvpt += 'rm_val == '
            if "fmv" in opcode or opcode in "fcvt.d.wu":
                cvpt = sanitise(0,cvpt,xlen,xlen,ops,inxFlg)
                
                # cvpt += str(0)
            else:
                cvpt = sanitise(rm,cvpt,xlen,xlen,ops,inxFlg)
                if inxFlg == True:
                    cvpt += sgn_prefix(xlen,inxFlg,ops,cvpt)
                else:
                    cvpt += ' # '
                # cvpt += str(rm)
            cvpt += c[1]
            coverpoints.append(cvpt)
            k=k+1

    mess='Generated'+ (' '*(5-len(str(len(coverpoints)))))+ str(len(coverpoints)) +' '+\
    (str(32) if xlen == 32 else str(64)) + '-bit coverpoints using Model B26 for '+opcode+' !'
    logger.debug(mess)
    coverpoints = comments_parser(coverpoints)

    return coverpoints

def ibm_b27(flen, iflen, opcode, ops, inxFlg=False, seed=10):
    '''
    IBM Model B27 Definition:
            This model tests the conversion of NaNs from a wider format to a narrow one. Each combination from the following table will create one test case (N represents the number of bits in the significand of the destination's format):
            [SNaN, QNaN]

            ==================== ========================================================= =====================
            Value of the operand The N-1 MSB bits of the significand (excluding the first) The rest of the bits
            ==================== ========================================================= =====================
            QNaN         All 0                                                       All 0
            SNan                 Not all 0                                                 Not all 0
            ==================== ========================================================= =====================

    :param iflen: Size of the floating point source operands for the operation
    :param flen: Size of the floating point registers
    :param opcode: Opcode for which the coverpoints are to be generated
    :param ops: No. of Operands taken by the opcode
    :param seed: Initial seed value of the random library. (Predefined to 10)

    :type iflen: int
    :type flen: int
    :type opcode: str
    :type ops: int
    :param seed: int

    Abstract Dataset Description:
            Operand 1 = [ SNaN, QNaN ]

    Implementation:
            - Dataset is the combination of snan and qnan values predefined at random initially.
            - Depending on the value of iflen, these values are then converted into their respective IEEE 754 hexadecimal values.
            - The operand values are then passed into the extract_fields function to get individual fields in a floating point number (sign, exponent and mantissa).
            - Coverpoints are then appended with all rounding modes for that particular opcode.

    '''
    sanitise = get_sanitise_func(opcode)
    opcode = opcode.split('.')[0] + '.' + opcode.split('.')[1]

    if iflen == 16:
        dataset = hsnan + hqnan
    elif iflen == 32:
        dataset = fsnan + fqnan
    elif iflen == 64:
        dataset = dsnan + dqnan

    coverpoints = []
    for c in dataset:
        cvpt = ""
        for x in range(1, ops+1):
            cvpt += (extract_fields(iflen,c,str(x)))
            cvpt += " and "
        # cvpt += 'rm_val == 0'
        cvpt = sanitise(0,cvpt,iflen,flen,ops,inxFlg)
        if inxFlg == True:
            cvpt += sgn_prefix(iflen,flen,inxFlg,ops,cvpt)
        else:
            cvpt += ' # '
        cvpt += ' # '
        for y in range(1, ops+1):
            cvpt += 'rs'+str(y)+'_val=='
            cvpt += num_explain(iflen, c) + '(' + str(c) + ')'
            if(y != ops):
                cvpt += " and "
        coverpoints.append(cvpt)

    mess='Generated'+ (' '*(5-len(str(len(coverpoints)))))+ str(len(coverpoints)) +' '+\
    (str(16) if iflen == 16 else str(32) if iflen == 32 else str(64)) + '-bit coverpoints using Model B27 for '+opcode+' !'
    logger.debug(mess)
    coverpoints = comments_parser(coverpoints)

    return coverpoints

def ibm_b28(flen, iflen, opcode, ops, inxFlg=False, seed=10):
    '''
    IBM Model B28 Definition:
            This model tests the conversion of a floating point number to an integral value, represented in floating-point format. A test case will be created for each of the following inputs:

            1. +0
            2. A random number in the range (+0, +1)
            3. +1
            4. Every value in the range (1.00, 10.11] (1 to 2.75 in jumps of 0.25)
            5. A random number in the range (+1, +1.11..11*2^precision)
            6. +1.11..11*2^precision
            7. +Infinity
            8. NaN
            9. -0
            10. A random number in the range (-1, -0)
            11. -1
            12. Every value in the range [-10.11, -1.00)
            13. A random number in the range (-1.11..11*2^precision , -1)
            14.-1.11..11*2^precision
            15. –Infinity

    :param flen: Size of the floating point registers
    :param iflen: Size of the floating point source operands for the operation
    :param opcode: Opcode for which the coverpoints are to be generated
    :param ops: No. of Operands taken by the opcode
    :param seed: Initial seed value of the random library. (Predefined to 10. Actual value is set with respect to the opcode calling the function)

    :type iflen: int
    :type flen: int
    :type opcode: str
    :type ops: int
    :param seed: int

    Abstract Dataset Description:
            Operand 1 = [ ±0, ±1, ±Infinity, Default NaN, A random number in the range (+0, +1), Every value in the range (1.00, 10.11] (1 to 2.75 in jumps of 0.25), A random number in the range (+1, +1.11..11*2^precision), ±1.11..11*2^precision, A random number in the range (-1, -0), Every value in the range [-10.11, -1.00), A random number in the range (-1.11..11*2^precision , -1) ]

    Implementation:
            - According to the given inputs, all cases are declared and appended to the dataset for iflen=32 and iflen=64.
            - Random numbers are obtained in the respective ranges and for absolute values, it is inherited from the dataset definition.
            - The operand values are then passed into the extract_fields function to get individual fields in a floating point number (sign, exponent and mantissa).
            - Coverpoints are then appended with rounding mode “0” for that particular opcode.

    '''
    sanitise = get_sanitise_func(opcode)
    random.seed(seed)
    opcode = opcode.split('.')[0] + '.' + opcode.split('.')[1]
    dataset = []

    if iflen == 16:
        dataset.append((hzero[0],"+0"))
        dataset.append((floatingPoint_tohex(16,float(random.uniform(0,1))),"A random number in the range (+0, +1)"))
        dataset.append((hone[0],"+1"))
        for i in range(125,300,25):
            dataset.append((floatingPoint_tohex(16, i/100),"Number = "+str(i/100)+" => Number ∈ (1,2.75]"))
        dataset.append((floatingPoint_tohex(16,float(random.uniform(1,2**15-1))),"A random number in the range (+1, +1.11..11*2^precision)"))
        dataset.append((floatingPoint_tohex(16,float(2**15-1)),"MaxInt"))
        dataset.append((hinfinity[0],"+Infinity"))

        dataset.append((hsnan[0],"Signaling NaN"))
        dataset.append((hqnan[0],"Quiet NaN"))

        dataset.append((hzero[1],"-0"))
        dataset.append((floatingPoint_tohex(16,float(random.uniform(-1,0))),"A random number in the range (-1, -0)"))
        dataset.append((hone[1],"-1"))
        for i in range(-275,-100,25):
            dataset.append((floatingPoint_tohex(16, i/100),"Number = "+str(i/100)+" => Number ∈ [-2.75,-1)"))
        dataset.append((floatingPoint_tohex(16,float(random.uniform(-2**15-1,-1))),"A random number in the range (-1.11..11*2^precision, -1)"))
        dataset.append((floatingPoint_tohex(16,float(-2**15-1)),"-MaxInt"))
        dataset.append((hinfinity[1],"-Infinity"))
    elif iflen == 32:
        dataset.append((fzero[0],"+0"))
        dataset.append((floatingPoint_tohex(32,float(random.uniform(0,1))),"A random number in the range (+0, +1)"))
        dataset.append((fone[0],"+1"))
        for i in range(125,300,25):
            dataset.append((floatingPoint_tohex(32, i/100),"Number = "+str(i/100)+" => Number ∈ (1,2.75]"))
        dataset.append((floatingPoint_tohex(32,float(random.uniform(1,2**31-1))),"A random number in the range (+1, +1.11..11*2^precision)"))
        dataset.append((floatingPoint_tohex(32,float(2**31-1)),"MaxInt"))
        dataset.append((finfinity[0],"+Infinity"))

        dataset.append((fsnan[0],"Signaling NaN"))
        dataset.append((fqnan[0],"Quiet NaN"))

        dataset.append((fzero[1],"-0"))
        dataset.append((floatingPoint_tohex(32,float(random.uniform(-1,0))),"A random number in the range (-1, -0)"))
        dataset.append((fone[1],"-1"))
        for i in range(-275,-100,25):
            dataset.append((floatingPoint_tohex(32, i/100),"Number = "+str(i/100)+" => Number ∈ [-2.75,-1)"))
        dataset.append((floatingPoint_tohex(32,float(random.uniform(-2**31-1,-1))),"A random number in the range (-1.11..11*2^precision, -1)"))
        dataset.append((floatingPoint_tohex(32,float(-2**31-1)),"-MaxInt"))
        dataset.append((finfinity[1],"-Infinity"))

    elif iflen == 64:
        dataset.append((dzero[0],"+0"))
        dataset.append((floatingPoint_tohex(64,float(random.uniform(0,1))),"A random number in the range (+0, +1)"))
        dataset.append((done[0],"+1"))
        for i in range(125,300,25):
            dataset.append((floatingPoint_tohex(64, i/100),"Number = "+str(i/100)+" => Number ∈ (1,2.75]"))
        dataset.append((floatingPoint_tohex(64,float(random.uniform(1,2**63-1))),"A random number in the range (+1, +1.11..11*2^precision)"))
        dataset.append((floatingPoint_tohex(64,float(2**63-1)),"MaxInt"))
        dataset.append((dinfinity[0],"+Infinity"))

        dataset.append((dsnan[0],"Signaling NaN"))
        dataset.append((dqnan[0],"Quiet NaN"))

        dataset.append((dzero[1],"-0"))
        dataset.append((floatingPoint_tohex(64,float(random.uniform(-1,0))),"A random number in the range (-1, -0)"))
        dataset.append((done[1],"-1"))
        for i in range(-275,-100,25):
            dataset.append((floatingPoint_tohex(64, i/100),"Number = "+str(i/100)+" => Number ∈ [-2.75,-1)"))
        dataset.append((floatingPoint_tohex(64,float(random.uniform(-2**63-1,-1))),"A random number in the range (-1.11..11*2^precision, -1)"))
        dataset.append((floatingPoint_tohex(64,float(-2**63-1)),"-MaxInt"))
        dataset.append((dinfinity[1],"-Infinity"))

    coverpoints = []
    for c in dataset:
        cvpt = ""
        for x in range(1, ops+1):
            cvpt += (extract_fields(iflen,c[x-1],str(x)))
            cvpt += " and "
        # cvpt += 'rm_val == 0'
        cvpt = sanitise(0,cvpt,iflen,flen,ops,inxFlg)
        if inxFlg == True:
            cvpt += sgn_prefix(iflen,flen,inxFlg,ops,cvpt)
        else:
            cvpt += ' # '
        cvpt += ' # '
        for y in range(1, ops+1):
            cvpt += 'rs'+str(y)+'_val=='
            cvpt += num_explain(iflen, c[y-1]) + '(' + str(c[y-1]) + ')'
            if(y != ops):
                cvpt += " and "
        cvpt += " | "+c[1]
        coverpoints.append(cvpt)

    mess='Generated'+ (' '*(5-len(str(len(coverpoints)))))+ str(len(coverpoints)) +' '+\
    (str(16) if iflen == 16 else str(32) if iflen == 32 else str(64)) + '-bit coverpoints using Model B28 for '+opcode+' !'
    logger.debug(mess)
    coverpoints = comments_parser(coverpoints)

    return coverpoints

def ibm_b29(flen, iflen, opcode, ops, inxFlg=False, seed=10):
    '''
    IBM Model B29 Definition:
            This model checks different cases of rounding of the floating point number. A test will be created for each possible combination of the Sign, LSB, Guard bit and the Sticky bit (16 cases for each operation).

            Rounding Mode: All

    :param flen: Size of the floating point registers
    :param iflen: Size of the floating point source operands for the operation
    :param opcode: Opcode for which the coverpoints are to be generated
    :param ops: No. of Operands taken by the opcode
    :param seed: Initial seed value of the random library. (Predefined to 10)

    :type iflen: int
    :type flen: int
    :type opcode: str
    :type ops: int
    :param seed: int

    Abstract Dataset Description:
            Operand 1 = [All possible combinations of Sign, LSB, Guard and Sticky are taken]

    Implementation:
            - A random mantissa is obtained and is iterated for each sign in each digit in the binary number.
            - The exponent is always maintained at -3, in order to facilitate the shift process that occurs during the actual conversion.
            - The respective hexadecimal values are appended to the dataset along with the respective  Least, Guard and Sticky bit value wherever available.
            - The operand values are then passed into the extract_fields function to get individual fields in a floating point number (sign, exponent and mantissa).
            - Coverpoints are then appended with all rounding modes for that particular opcode.

    '''
    sanitise = get_sanitise_func(opcode)
    random.seed(seed)
    sgns = ["0","1"]
    dataset = []
    if iflen == 16:
        mant = random.getrandbits(7)
        mant = '{:07b}'.format(mant)
        for sgn in sgns:
            for i in range(8):
                LeastGuardSticky = '{:03b}'.format(i)
                hexnum = "0x" + hex(int("1"+sgn + "01100" + mant + LeastGuardSticky,2))[3:]
                dataset.append((hexnum,"Exp = -3; Sign = {}; LSB = {}; Guard = {}; Sticky = {}"\
                    .format(sgn,LeastGuardSticky[0],LeastGuardSticky[1],LeastGuardSticky[2])))
    elif iflen == 32:
        mant = random.getrandbits(20)
        mant = '{:020b}'.format(mant)
        for sgn in sgns:
            for i in range(8):
                LeastGuardSticky = '{:03b}'.format(i)
                hexnum = "0x" + hex(int("1"+sgn + "01111100" + mant + LeastGuardSticky,2))[3:]
                dataset.append((hexnum,"Exp = -3; Sign = {}; LSB = {}; Guard = {}; Sticky = {}"\
                    .format(sgn,LeastGuardSticky[0],LeastGuardSticky[1],LeastGuardSticky[2])))
    elif iflen == 64:
        mant = random.getrandbits(49)
        mant = '{:049b}'.format(mant)
        for sgn in sgns:
            for i in range(8):
                LeastGuardSticky = '{:03b}'.format(i)
                hexnum = "0x" + hex(int("1"+sgn + "01111111100" + mant + LeastGuardSticky,2))[3:]
                dataset.append((hexnum,"Exp = -3; Sign = {}; LSB = {}; Guard = {}; Sticky = {}"\
                    .format(sgn,LeastGuardSticky[0],LeastGuardSticky[1],LeastGuardSticky[2])))

    coverpoints = []
    for c in dataset:
        for rm in range(0,5):
            cvpt = ""
            for x in range(1, ops+1):
                cvpt += (extract_fields(iflen,c[x-1],str(x)))
                cvpt += " and "
            # cvpt += 'rm_val == '
            if "fmv" in opcode or "fcvt.d.s" in opcode:
                cvpt = sanitise(0,cvpt,iflen,flen,ops,inxFlg)
                # cvpt += '0'
            else:
                cvpt = sanitise(rm,cvpt,iflen,flen,ops,inxFlg)
                # cvpt += str(rm)
            if inxFlg == True:
                cvpt += sgn_prefix(iflen,flen,inxFlg,ops,cvpt)
            else:
                cvpt += ' # '
            cvpt += ' # '
            for y in range(1, ops+1):
                cvpt += 'rs'+str(y)+'_val=='
                cvpt += num_explain(iflen, c[y-1]) + '(' + str(c[y-1]) + ')'
                if(y != ops):
                    cvpt += " and "
            cvpt += " | "+c[1]
            coverpoints.append(cvpt)

    mess='Generated'+ (' '*(5-len(str(len(coverpoints)))))+ str(len(coverpoints)) +' '+\
    (str(16) if iflen == 16 else str(32) if iflen == 32 else str(64)) + '-bit coverpoints using Model B29 for '+opcode+' !'
    logger.debug(mess)
    coverpoints = comments_parser(coverpoints)

    return coverpoints
