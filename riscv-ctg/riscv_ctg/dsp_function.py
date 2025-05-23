def simd_val_vars(operand, xlen, bit_width):
    '''
    This function generates the operand value variables for SIMD elements of the given operand.

    :param operand: a string indicating the name of the desired operand.
    :param xlen: an integer indicating the XLEN value to be used.
    :param bit_width: an integer indicating the element bit width for the current SIMD format.

    :type operand: str
    :type xlen: int
    :type bit_width: int
    :return: a list containing the element value variables for the given operand.
    '''
    val_list = []
    nelms = xlen // bit_width
    if bit_width == 8:
        sz = "b"
    elif bit_width == 16:
        sz = "h"
    elif bit_width == 32:
        sz = "w"
    else:
        sz = "d"
    for i in range(nelms):
        val_list += [f"{operand}_{sz}{i}_val"]
    return val_list

def get_fmt_sz(bit_width):
    if bit_width == 8:
        fmt = f"#02x"
    elif bit_width == 16:
        fmt = f"#04x"
    elif bit_width == 32:
        fmt = f"#08x"
    else:
        fmt = f"#016x"
    if bit_width == 8:
        sz = "b"
    elif bit_width == 16:
        sz = "h"
    elif bit_width == 32:
        sz = "w"
    else:
        sz = "d"

    return fmt, sz

def gen_fmt(bit_width):
    '''
    This function generate fmt string by bit_width.

    :param bit_width: an integer indicating the element bit width of the current RVP instruction.

    :type bit_width: int
    '''

    if bit_width == 8:
        fmt = f"#02x"
    elif bit_width == 16:
        fmt = f"#04x"
    elif bit_width == 32:
        fmt = f"#08x"
    else:
        fmt = f"#016x"
    return fmt

def gen_sz(bit_width):
    '''
    This function generate size string by bit_width.

    :param bit_width: an integer indicating the element bit width of the current RVP instruction.

    :type bit_width: int
    '''

    if bit_width == 8:
        sz = "b"
    elif bit_width == 16:
        sz = "h"
    elif bit_width == 32:
        sz = "w"
    else:
        sz = "d"
    return sz

def concat_simd_data(instr_dict, xlen, _bit_width):
    '''
    This function concatenates all element of a SIMD register into a single value in the hex format.

    :param instr_dict: a dict holding metadata and operand data for the current instruction.
    :param xlen: an integer indicating the XLEN value to be used.
    :param bit_width: an integer or string of integer pair indicating the element bit width of rs1/rs2 of the current RVP instruction.

    :type instr_dict: dict
    :type xlen: int
    :type bit_width: int
    '''
    if type(_bit_width)==str:
        _bit_width = eval(_bit_width)

    if type(_bit_width)==tuple:
        bit_width1, bit_width2 = _bit_width
    else:
        bit_width1, bit_width2 = _bit_width, _bit_width

    for instr in instr_dict:
        if 'rs1' in instr:
            twocompl_offset = 1<<bit_width1
            fmt, sz= get_fmt_sz(bit_width1)
            if 'rs1_val' in instr:  # single element value
                rs1_val = int(instr['rs1_val'])
                if rs1_val < 0:
                    rs1_val = rs1_val + twocompl_offset
                instr['rs1_val'] = format(rs1_val, f"#0x")
            else:   # concatenates all element of a SIMD register into a single value
                rs1_val = 0
                for i in range(xlen//bit_width1):
                    val_var = f"rs1_{sz}{i}_val"
                    val = int(instr[val_var])
                    if val < 0:
                        val = val + twocompl_offset
                    rs1_val += val << (i*bit_width1)
                instr['rs1_val'] = format(rs1_val, f"#0{xlen//4}x")
        if 'rs2' in instr:
            # bit_width1 == bit_width2 except for instructions with pwhrrformat.
            # but even for pwhrrformat, the values are aligned to bit_width1 instead of bit_width2.
            twocompl_offset = 1<<bit_width2
            fmt, sz= get_fmt_sz(bit_width2)

            if 'rs2_val' in instr:  # single element value
                rs2_val = int(instr['rs2_val'])
                if rs2_val < 0:
                    rs2_val = rs2_val + twocompl_offset
                instr['rs2_val'] = format(rs2_val, f"#0x")
            else:   # concatenates all element of a SIMD register into a single value
                rs2_val = 0
                for i in range(xlen//bit_width2):
                    val_var = f"rs2_{sz}{i}_val"
                    val = int(instr[val_var])
                    if val < 0:
                        val = val + twocompl_offset
                    rs2_val += val << (i*bit_width2)
                instr['rs2_val'] = format(rs2_val, f"#0{xlen//4}x")
        if 'imm_val' in instr:
            imm_val = int(instr['imm_val'])
            instr['imm_val'] = format(imm_val, f"#0x")

def incr_reg_num(reg):
    name = reg[0]
    num = int(reg[1:])
    num = num + 1
    return name + str(num)

def gen_pair_reg_data(instr_dict, xlen, _bit_width, p64_profile):
    '''
    This function generate high registers for paired register operands, rs1_hi, rs2_hi and rd_hi depending on the specification of the p64_profile string.
    It also generate the corresponding values rs1_val_hi, rs2_val_hi.

    :param instr_dict: a dict holding metadata and operand data for the current instruction.
    :param xlen: an integer indicating the XLEN value to be used.
    :param bit_width: an integer or string of integer pair indicating the element bit width of rs1/rs2 of the current RVP instruction.
    :param p64_profile: a string of 3 chars indicating the type of operands (pair/non-pair) of the current RVP instruction. (rd, rs1 and rs2)

    :type instr_dict: dict
    :type xlen: int
    :type bit_width: int
    :type p64_profile: string

    '''
    if type(_bit_width)==str:
        _bit_width = eval(_bit_width)

    if type(_bit_width)==tuple:
        bit_width1, bit_width2 = _bit_width
    else:
        bit_width1, bit_width2 = _bit_width, _bit_width

    if xlen == 32:
        rs1_width = 64 if len(p64_profile) >= 3 and p64_profile[1]=='p' else xlen
        rs2_width = 64 if len(p64_profile) >= 3 and p64_profile[2]=='p' else xlen
        rd_width  = 64 if len(p64_profile) >= 3 and p64_profile[0]=='p' else xlen
    else:
        rs1_width = 128 if len(p64_profile) >= 3 and p64_profile[1]=='p' else xlen
        rs2_width = 128 if len(p64_profile) >= 3 and p64_profile[2]=='p' else xlen
        rd_width  = 128 if len(p64_profile) >= 3 and p64_profile[0]=='p' else xlen

    for instr in instr_dict:
        if 'rs1' in instr:
            twocompl_offset = 1<<bit_width1
            fmt, sz= get_fmt_sz(bit_width1)

            if 'rs1_val' in instr:
                rs1_val = int(instr['rs1_val'])
                if rs1_val < 0:
                    rs1_val = rs1_val + twocompl_offset
            else:
                rs1_val = 0
                for i in range(rs1_width//bit_width1):
                    val_var = f"rs1_{sz}{i}_val"
                    val = int(instr[val_var])
                    if val < 0:
                        val = val + twocompl_offset
                    rs1_val += val << (i*bit_width1)
            if rs1_width > xlen:
                instr['rs1_val'] = format(0xffffffff & rs1_val, f"#0{2+xlen//4}x")
                instr['rs1_val_hi'] = format(0xffffffff & (rs1_val>>32), f"#0{2+xlen//4}x")
                instr['rs1_hi'] = incr_reg_num(instr['rs1'])
            else:
                instr['rs1_val'] = format(rs1_val, f"#0{2+xlen//4}x")
            if rs1_width == 64 and (len(p64_profile) >= 3):
                instr['rs1_val64'] = format(rs1_val, f"#018x")

        if 'rs2' in instr:
            twocompl_offset = 1<<bit_width2
            fmt, sz= get_fmt_sz(bit_width2)

            if 'rs2_val' in instr:  # single element value
                rs2_val = int(instr['rs2_val'])
                if rs2_val < 0:
                    rs2_val = rs2_val + twocompl_offset
            else: # concatenates all element of a SIMD register into a single value
                rs2_val = 0
                for i in range(rs2_width//bit_width2):
                    val_var = f"rs2_{sz}{i}_val"
                    val = int(instr[val_var])
                    if val < 0:
                        val = val + twocompl_offset
                    rs2_val += val << (i*bit_width2)
            if rs2_width > xlen:
                instr['rs2_val'] = format(0xffffffff & rs2_val, f"#0{2+xlen//4}x")
                instr['rs2_val_hi'] = format(0xffffffff & (rs2_val>>32), f"#0{2+xlen//4}x")
                instr['rs2_hi'] = incr_reg_num(instr['rs2'])
            else:
                instr['rs2_val'] = format(rs2_val, f"#0{2+xlen//4}x")
            if rs2_width == 64 and (len(p64_profile) >= 3):
                instr['rs2_val64'] = format(rs2_val, f"#018x")

        if 'rd' in instr and rd_width > xlen:
            instr['rd_hi'] = incr_reg_num(instr['rd'])

        if 'imm_val' in instr:
            imm_val = int(instr['imm_val'])
            instr['imm_val'] = format(imm_val, f"#0x")
