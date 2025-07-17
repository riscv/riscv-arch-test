import struct

instrs_sig_mutable = ['auipc','jal','jalr']
instrs_sig_update = ['sh','sb','sw','sd','c.fsw','c.sw','c.sd','c.swsp','c.sdsp','fsw','fsd',\
        'c.fsw','c.fsd','c.fswsp','c.fsdsp']
instrs_no_reg_tracking = ['beq','bne','blt','bge','bltu','bgeu','fence','c.j','c.jal','c.jalr',\
        'c.jr','c.beqz','c.bnez', 'c.ebreak'] + instrs_sig_update
instrs_fcsr_affected = ['fmadd.s','fmsub.s','fnmsub.s','fnmadd.s','fadd.s','fsub.s','fmul.s','fdiv.s',\
        'fsqrt.s','fmin.s','fmax.s','fcvt.w.s','fcvt.wu.s','feq.s','flt.s',\
        'fle.s','fcvt.s.w','fcvt.s.wu','fcvt.l.s','fcvt.lu.s','fcvt.s.l',\
        'fcvt.s.lu', 'fmadd.d','fmsub.d','fnmsub.d','fnmadd.d','fadd.d','fsub.d',\
        'fmul.d','fdiv.d','fsqrt.d','fmin.d','fmax.d','fcvt.s.d','fcvt.d.s',\
        'feq.d','flt.d','fle.d','fcvt.w.d','fcvt.wu.d','fcvt.l.d','fcvt.lu.d',\
        'fcvt.d.l','fcvt.d.lu']
unsgn_rs1 = ['sw','sd','sh','sb','ld','lw','lwu','lh','lhu','lb', 'lbu','flw','fld','fsw','fsd','flh','fsh',\
        'bgeu', 'bltu', 'sltiu', 'sltu','c.lw','c.lhu','c.lh','c.ld','c.lwsp','c.ldsp',\
        'c.sw','c.sd','c.swsp','c.sdsp','c.fsw','mulhu','divu','remu','divuw',\
        'remuw','aes64ds','aes64dsm','aes64es','aes64esm','aes64ks2',\
        'sha256sum0','sha256sum1','sha256sig0','sha256sig1','sha512sig0',\
        'sha512sum1r','sha512sum0r','sha512sig1l','sha512sig0l','sha512sig1h','sha512sig0h',\
        'sha512sig1','sha512sum0','sha512sum1','sm3p0','sm3p1','aes64im',\
        'sm4ed','sm4ks','ror','rol','rori','rorw','rolw','roriw','clmul','clmulh','clmulr',\
        'andn','orn','xnor','pack','packh','packu','packuw','packw',\
        'xperm.n','xperm.b','grevi','aes64ks1i', 'shfli', 'unshfli', \
        'cbo.clean', 'cbo.flush', 'cbo.inval', 'cbo.zero', 'prefetch.i','prefetch.r','prefetch.w', \
        'aes32esmi', 'aes32esi', 'aes32dsmi', 'aes32dsi','bclr','bext','binv',\
        'bset','zext.h','sext.h','sext.b','zext.b','zext.w','minu','maxu','orc.b','add.uw','sh1add.uw',\
        'sh2add.uw','sh3add.uw','slli.uw','clz','clzw','ctz','ctzw','cpop','cpopw','rev8',\
        'bclri','bexti','binvi','bseti','xperm4','xperm8','zip','unzip','gorci','fcvt.d.wu','fcvt.s.wu','fcvt.d.lu','fcvt.s.lu','c.flwsp','c.fldsp','c.flw','c.fld'\
        'c.not', 'c.sext.b','c.sext.h','c.zext.b','c.zext.h','c.zext.w','sc.w','lr.w','sc.d','lr.d']
unsgn_rs2 = ['bgeu', 'bltu', 'sltiu', 'sltu', 'sll', 'srl', 'sra', 'sraw', 'mulhu',\
        'mulhsu','divu','remu','divuw','remuw','aes64ds','aes64dsm','aes64es',\
        'aes64esm','aes64ks2','sm4ed','sm4ks','ror','rol','rorw','rolw','clmul',\
        'clmulh','clmulr','andn','orn','xnor','pack','packh','packu','packuw','packw',\
        'xperm.n','xperm.b', 'aes32esmi', 'aes32esi', 'aes32dsmi', 'aes32dsi',\
        'sha512sum1r','sha512sum0r','sha512sig1l','sha512sig1h','sha512sig0l','sha512sig0h','fsw',\
        'bclr','bext','binv','bset','minu','maxu','add.uw','sh1add.uw','sh2add.uw','sh3add.uw','sc.w', 'sc.d']
f_instrs_pref = ['fadd', 'fclass', 'fcvt', 'fdiv', 'feq', 'fld', 'fle', 'flt', 'flw', 'fmadd',\
        'fmax', 'fmin', 'fmsub', 'fmul', 'fmv', 'fnmadd', 'fnmsub', 'fsd', 'fsgnj', 'fsqrt',\
        'fsub', 'fsw']
unsgn_rd = ['lr.w','sc.w','lr.d','sc.d']


instr_var_evaluator_funcs = {} # dictionary for holding registered evaluator funcs
def evaluator_func(instr_var_name, cond):
    '''
    This is a parametrized decorator for registering the evaluator funcs used for
    evaluating an instruction variable (instruction variables are used in the
    evaluation of coverpoints).

    :param instr_var_name: Name of the instruction variable
    :param cond: A boolean lambda function evaluating to True if the decorated function needs to be selected for the evaluation of the instruction variable
    '''
    def evaluator_func_registration_decorator(func):
        if instr_var_name in instr_var_evaluator_funcs:
            instr_var_evaluator_funcs[instr_var_name].append((cond, func))
        else:
            instr_var_evaluator_funcs[instr_var_name] = [(cond, func)]
        return func
    return evaluator_func_registration_decorator


''' Instruction Object '''
class instructionObject():
    '''
        Instruction object class
    '''
    def __init__(
        self,
        instr,
        instr_name,
        instr_addr,
        rd = None,
        rs1 = None,
        rs2 = None,
        rs3 = None,
        imm = None,
        zimm = None,
        csr = None,
        shamt = None,
        succ = None,
        pred = None,
        rl = None,
        aq = None,
        rm = None,
        reg_commit = None,
        csr_commit = None,
        mnemonic = None,
        mode = None,
        vm_addr_dict = None,
        mem_val =  None,
        trap_dict = None,
        inxFlag = None,
        is_sgn_extd = None,
        mip_updated_val = None
    ):

        '''
            Constructor.
            :param instr_name: name of instruction as accepted by a standard RISC-V assembler
            :param instr_addr: pc value of the instruction
            :param rd: tuple containing the register index and registerfile (x or f) that will be updated by this instruction
            :param rs1: typle containing the register index and registerfilr ( x or f) that will be used as the first source operand.
            :param rs2: typle containing the register index and registerfilr ( x or f) that will be used as the second source operand.
            :param rs3: typle containing the register index and registerfilr ( x or f) that will be used as the third source operand.
            :param imm: immediate value, if any, used by the instruction
            :param csr: csr index, if any, used by the instruction
            :param shamt: shift amount, if any, used by the instruction
        '''
        self.instr = instr
        self.instr_name = instr_name
        self.instr_addr = instr_addr
        self.rd = rd
        self.rs1 = rs1
        self.rs2 = rs2
        self.rs3 = rs3
        self.imm = imm
        self.zimm = zimm
        self.csr = csr
        self.shamt = shamt
        self.succ = succ
        self.pred = pred
        self.rl = rl
        self.aq = aq
        self.rm = rm
        self.reg_commit = reg_commit
        self.csr_commit = csr_commit
        self.mnemonic = mnemonic
        self.is_rvp = False
        self.inxFlg = inxFlag
        self.rs1_nregs = 1
        self.rs2_nregs = 1
        self.rs3_nregs = 1
        self.rd_nregs = 1
        self.mode = mode
        self.vm_addr_dict = vm_addr_dict
        self.matches_for_options = None
        self.mem_val = mem_val
        self.trap_dict = trap_dict
        self.mip_updated_val = mip_updated_val

    def is_sig_update(self):
        return self.instr_name in instrs_sig_update


    def evaluate_instr_vars(self, xlen, flen, arch_state, csr_regfile, instr_vars):
        '''
        This function populates the provided instr_vars dictionary
        with the necessary fields to evaluate the coverpoints.

        :param xlen: Max xlen of the trace
        :param flen: Max flen of the trace
        :param arch_state: Architectural state
        :param csr_regfile: Architectural state of CSR register files
        :param instr_vars: Dictionary to be populated by the evaluated instruction variables
        '''

        instr_vars['xlen'] = xlen
        instr_vars['flen'] = flen
        instr_vars['mode'] = self.mode
        instr_vars['mnemonic'] = self.instr_name

        instr_vars['iflen'] = flen
        if self.instr_name.endswith(".s") or self.instr_name in {'fmv.x.w', 'flw', 'fsw'}:
            instr_vars['iflen'] = 32
        elif self.instr_name.endswith(".d"):
            instr_vars['iflen'] = 64
        elif self.instr_name.endswith(".h"):
            instr_vars['iflen'] = 16
        

        # capture the operands
        if self.rs1 is not None:
            instr_vars['rs1'] = self.rs1[1] + str(self.rs1[0])
        if self.rs2 is not None:
            instr_vars['rs2'] = self.rs2[1] + str(self.rs2[0])
        if self.rs3 is not None:
            instr_vars['rs3'] = self.rs3[1] + str(self.rs3[0])
        if self.rd is not None:
            instr_vars['rd'] = self.rd[1] + str(self.rd[0])
        if self.imm is not None:
            instr_vars['imm_val'] = self.imm
        if self.shamt is not None:
            instr_vars['imm_val'] = self.shamt
        if self.rl is not None:
            instr_vars['rl'] = self.rl
        if self.aq is not None:
            instr_vars['aq'] = self.aq

        imm_val = instr_vars.get('imm_val', None)

        #update the variable for the length of the load or store:
        if self.instr_name in ['ld','lw','lb','lh','sd','sw','sb','sh']:
            if self.instr_name in ['ld','sd']:
                instr_vars['access_len'] = 8
            if self.instr_name in ['lw','sw']:
                instr_vars['access_len'] = 4
            if self.instr_name in ['lh','sh']:
                instr_vars['access_len'] = 2
            if self.instr_name in ['lb','sb']:
                instr_vars['access_len'] = 1
        else:
            instr_vars['access_len'] = None

        #Update the values for the trap registers
        self.trap_registers_update(instr_vars,self.trap_dict)

        #Update the value of MIP as soon as the hart updates it.
        if self.mip_updated_val is not None:
            if isinstance(csr_regfile['mip'], str):
                csr_regfile['mip'] = int(csr_regfile['mip'], 16) | self.mip_updated_val
            else:
                csr_regfile['mip'] = csr_regfile['mip'] | self.mip_updated_val

        # capture the register operand values
        rs1_val = self.evaluate_instr_var("rs1_val", instr_vars, arch_state)
        rs2_val = self.evaluate_instr_var("rs2_val", instr_vars, arch_state)
        rs3_val = self.evaluate_instr_var("rs3_val", instr_vars, arch_state)
        rd_val  = self.evaluate_instr_var("rd_val", instr_vars, arch_state)

        ea_align = None
        # the ea_align variable is used by the eval statements of the
        # coverpoints for conditional ops and memory ops
        if self.instr_name in ['jal','bge','bgeu','blt','bltu','beq','bne']:
            ea_align = (self.instr_addr+(imm_val<<1)) % 4
        if self.instr_name == "jalr":
            ea_align = (rs1_val + imm_val) % 4
        if self.instr_name in ['fsh','flh']:
            ea_align = (rs1_val + imm_val) % 2
        if self.instr_name in ['sw','sh','sb','lw','lhu','lh','lb','lbu','lwu','flw','fsw']:
            ea_align = (rs1_val + imm_val) % 4
        if self.instr_name in ['ld','sd','fld','fsd']:
            ea_align = (rs1_val + imm_val) % 8

        instr_vars.update({
            'rs1_val': rs1_val,
            'rs2_val': rs2_val,
            'rs3_val': rs3_val,
            'rd_val' : rd_val,
            'rm_val': self.rm,
            'ea_align': ea_align,
        })

        # derived instruction variables specific to an extension
        ext_specific_vars = self.evaluate_instr_var("ext_specific_vars", instr_vars, arch_state, csr_regfile)
        if ext_specific_vars is not None:
            instr_vars.update(ext_specific_vars)


    def get_elements_to_track(self, xlen):
        '''
        This function returns the elements to track to aid in monitoring signature updates and related statistics.
        The returned value is a tuple of three elements:

        - The first element is a list of registers to track whose values cannot be modified before storing
        - The second element is a list of registers to track whose value can be modified prior to storing
        - The third element is a list of instructions to track for signature updates other than those of tracked registers (mostly used for branch instructions)
        '''
        regs_to_track_immutable = []
        regs_to_track_mutable = []
        instrs_to_track = []

        if self.instr_name in instrs_no_reg_tracking:
            store_instrs = []
            if self.is_sig_update():
                store_instrs = [self.instr_name]
            else:
                if self.instr_name.startswith("c."):
                    store_instrs = ['sd','c.sdsp'] if xlen == 64 else ['sw','c.swsp']
                else:
                    store_instrs = ['sd'] if xlen == 64 else ['sw']
            instrs_to_track.append(store_instrs)
        elif self.instr_name in instrs_sig_mutable:
            if self.rd is not None:
                reg = self.rd[1] + str(self.rd[0])
                regs_to_track_mutable.append(reg)
        else:
            if self.rd is not None:
                reg = self.rd[1] + str(self.rd[0])
                regs_to_track_immutable.append(reg)

            if self.instr_name in instrs_fcsr_affected:
                regs_to_track_immutable.append('fcsr')

            if self.csr_commit is not None:
                for commit in self.csr_commit:
                    if commit[0] == "CSR":
                        csr_reg = commit[1]
                        if csr_reg not in regs_to_track_immutable:
                            regs_to_track_immutable.append(csr_reg)

        return (regs_to_track_immutable, regs_to_track_mutable, instrs_to_track)


    def get_changed_regs(self, arch_state, csr_regfile):
        '''
        This function returns a list of registers whose value will be changed as
        a result of executing this instruction.

        :param csr_regfile: Architectural state of CSR register files
        :param instr_vars: Dictionary to be populated by the evaluated instruction variables
        '''
        changed_regs = []

        if self.reg_commit is not None:
            reg = self.reg_commit[0] + self.reg_commit[1]

            prev_value = None
            if self.reg_commit[0] == 'x':
                prev_value = arch_state.x_rf[int(self.reg_commit[1])]
            elif self.reg_commit[0] == 'f':
                prev_value = arch_state.f_rf[int(self.reg_commit[1])]

            if prev_value != str(self.reg_commit[2][2:]): # this is a string check, but should we do an exact number check?
                changed_regs.append(reg)

        if self.csr_commit is not None:
            for commit in self.csr_commit:
                if commit[0] == "CSR":
                    csr_reg = commit[1]

                    if csr_regfile[csr_reg] != str(commit[3][2:]):
                        changed_regs.append(csr_reg)

        return changed_regs


    def update_arch_state(self, arch_state, csr_regfile, mem_vals):
        '''
        This function updates the arch state and csr regfiles
        with the effect of this instruction.

        :param csr_regfile: Architectural state of CSR register files
        :param instr_vars: Dictionary to be populated by the evaluated instruction variables
        :param mem_vals: Dictionary to be populated for the memory values
        '''
        arch_state.pc = self.instr_addr

        commitvalue = self.reg_commit
        if commitvalue is not None and len(self.rd) >= 1:
            if self.rd[1] == 'x':
                arch_state.x_rf[int(commitvalue[1])] =  str(commitvalue[2][2:])
            elif self.rd[1] == 'f':
                arch_state.f_rf[int(commitvalue[1])] =  str(commitvalue[2][2:])

        csr_commit = self.csr_commit
        if csr_commit is not None:
            for commit in csr_commit:
                if (commit[0] == "CSR"):
                    csr_regfile[commit[1]] = str(commit[3][2:])

        mem_val = self.mem_val
        if mem_val is not None:
            mem_vals[int(mem_val[0][0], 16)] = int(mem_val[0][1], 16)

    def evaluate_instr_var(self, instr_var_name, *args):
        '''
        This function selects and invokes the appropriate function for evaluating
        the given instruction variable by running the condition lambda functions
        of the registered evaluator functions.

        :param instr_var_name: Name of the instruction variable
        '''
        for cond, func in instr_var_evaluator_funcs.get(instr_var_name, []):
            if cond(
                instr_name = self.instr_name,
                rs1 = self.rs1,
                rs2 = self.rs2,
                rs3 = self.rs3,
                rd  = self.rd,
                is_rvp = self.is_rvp,
                inxFlag = self.inxFlg
            ): # could just instr_name suffice?
                return func(self, *args)

        return None

    def ptw_update(self,instr_vars):
        '''
        This function calculates the virtual, physical address of instruction,
        data and also the page table walk addresses 
        for the data.

        :param instr_vars : dictionary to be populated by the evaluated address variables
                            in case when the virtual memory is mentioned under the config
                            label.
        '''
        match = ['VM']
        if instr_vars['xlen'] == 32:
            if ((instr_vars['satp']) >> 31) == 1:
                match.append('SV32')
            else:
                match.append(0)
        elif instr_vars['xlen'] == 64:
            if ((instr_vars['satp']) >> 60) == 8:
                match.append('SV39')
            elif ((instr_vars['satp']) >> 60) == 9:
                match.append('SV48')
            elif ((instr_vars['satp']) >> 60) == 10:
                match.append('SV57')
            else:
                match.append(0)
        if match[0] == 'VM' and match[1] in ['SV32', 'SV39', 'SV48', 'SV57']:
            instr_vars['depa'] = self.vm_addr_dict['depa']
            instr_vars['ieva'] = self.vm_addr_dict['ieva']
            instr_vars['iepa'] = self.vm_addr_dict['iepa']
            instr_vars['ieva_align'] = self.vm_addr_dict['ieva_align']
            instr_vars['iepa_align'] = self.vm_addr_dict['iepa_align']
            instr_vars['depa_align'] = self.vm_addr_dict['depa_align']
            format_max_len_mapping = {'SV32': 2, 'SV39': 3, 'SV48': 4, 'SV57': 5}
            max_len = format_max_len_mapping.get(match[1],0)
            size = len(self.vm_addr_dict['dptw_list'])
            instr_vars['len_dptw'] = size
            remain = max_len
            length = max_len - size - 1
            for i in range(size):
                instr_vars[f'dptw{max_len-1}a'] = int(self.vm_addr_dict['dptw_list'][i][0], 16)
                instr_vars[f'dptw{max_len-1}cont'] = int(self.vm_addr_dict['dptw_list'][i][1], 16)
                max_len = max_len -1
            for i in range(length, -1, -1):
                instr_vars[f'dptw{i}cont'] = None
                instr_vars[f'dptw{i}a'] = None
            for i in range(remain, 5):
                instr_vars[f'dptw{i}cont'] = None
                instr_vars[f'dptw{i}a'] = None
        else:
            instr_vars['depa'] = None
            instr_vars['ieva'] = None
            instr_vars['iepa'] = None
            instr_vars['ieva_align'] = None
            instr_vars['iepa_align'] = None
            instr_vars['depa_align'] = None
            instr_vars['len_dptw']   = None
            for i in range(0, 5):
                instr_vars[f'dptw{i}a'] = None
                instr_vars[f'dptw{i}cont'] = None
        return None

    def iptw_update(self, instr_vars, iptw_dict):
        '''
        This function page table walk addresses 
        for the data.

        :param instr_vars: Dictionary holding the values of current instruction state.

        :param iptw_dict : dictionary that contains the current instruction's
                            page table walk addresses.
        '''
        match = ['VM']
        if instr_vars['xlen'] == 32:
            if ((instr_vars['satp']) >> 31) == 1:
                match.append('SV32')
            else:
                match.append(0)
        elif instr_vars['xlen'] == 64:
            if ((instr_vars['satp']) >> 60) == 8:
                match.append('SV39')
            elif ((instr_vars['satp']) >> 60) == 9:
                match.append('SV48')
            elif ((instr_vars['satp']) >> 60) == 10:
                match.append('SV57')
            else:
                match.append(0)
        if (len(self.vm_addr_dict['iptw_list'])) != 0:
            if match[0] == 'VM' and match[1] in ['SV32', 'SV39', 'SV48', 'SV57']:
                format_max_len_mapping = {'SV32': 2, 'SV39': 3, 'SV48': 4, 'SV57': 5}
                max_len = format_max_len_mapping.get(match[1],0)
                size = len(self.vm_addr_dict['iptw_list'])
                iptw_dict['len_iptw'] = size
                remain = max_len
                length = max_len - size - 1
                for i in range(size):
                    iptw_dict[f'iptw{max_len-1}a'] = int(self.vm_addr_dict['iptw_list'][i][0], 16)
                    iptw_dict[f'iptw{max_len-1}cont'] = int(self.vm_addr_dict['iptw_list'][i][1], 16)
                    max_len = max_len -1
                for i in range(length, -1, -1):
                    iptw_dict[f'iptw{i}a'] = None
                    iptw_dict[f'iptw{i}cont'] = None
                for i in range(remain, 5):
                    iptw_dict[f'iptw{i}a'] = None
                    iptw_dict[f'iptw{i}cont'] = None
            else:
                for i in range(0, 5):
                    iptw_dict[f'iptw{i}a'] = None
                    iptw_dict[f'iptw{i}cont'] = None
                iptw_dict['len_iptw'] = 0
        elif self.mode == 'M':
            for i in range(0, 5):
                iptw_dict[f'iptw{i}a'] = None
                iptw_dict[f'iptw{i}cont'] = None
            iptw_dict['len_iptw'] = 0

        return None
    
    def trap_registers_update(self, instr_vars, trap_dict):
        '''
        This function updates the registers related to traps
        in the log.
        : param instr_vars: Dictionary holding the values of current instruction state
        : param trap_dict : Values for the trap registers for current instruction 
        '''

        instr_vars['mode_change']   = trap_dict['mode_change']
        instr_vars['call_type']     = trap_dict['call_type']

        mcause_interrupt = {32: 0x80000000, 64: 0x8000000000000000}

        if trap_dict["mode_change"] is not None:
            #update the registers depending upon the mode change
            if trap_dict["mode_change"].split()[2] == "M":
                instr_vars['mcause']      = trap_dict['exc_num']
                instr_vars['mtval']       = trap_dict['tval']
                #only update on the initialization
                if "scause" not in instr_vars:
                    instr_vars['scause']      = None
                    instr_vars['stval']       = None

            elif trap_dict["mode_change"].split()[2] == "S":
                instr_vars['scause']      = trap_dict['exc_num']
                instr_vars['stval']       = trap_dict['tval']
                #only update on the initialization
                if "mcause" not in instr_vars:
                    instr_vars['mcause']      = None
                    instr_vars['mtval']       = None
        
        #Handle interrupt Case
        # TODO: update the interrupt case for delegation !
        elif trap_dict["mode_change"] is None and trap_dict['call_type'] == "interrupt":
                #upper most bit should be 1 in case of interrupt
                instr_vars['mcause'] = mcause_interrupt[instr_vars['xlen']] | int(trap_dict['exc_num'], 16)
                instr_vars['mtval']       = trap_dict['tval']
                #only update on the initialization
                if "scause" not in instr_vars:
                    instr_vars['scause']      = None
                    instr_vars['stval']       = None

        else:
                #initialize them to None for the first time in the instr_vars
                #reset them to None in case the mode change is ret
                instr_vars['mcause']      = None
                instr_vars['mtval']       = None
                instr_vars['scause']      = None
                instr_vars['stval']       = None

        return None

    '''
    Evaluator funcs for rs1_val

    :param arch_state: Architectural state
    :param instr_vars: Dictionary of instruction variables already evaluated
    '''
    @evaluator_func("rs1_val", lambda **params: params['instr_name'] in unsgn_rs1 and params['rs1'] is not None)
    def evaluate_rs1_val_unsgn(self, instr_vars, arch_state):
        return self.evaluate_reg_val_unsgn(self.rs1[0], instr_vars['xlen'], arch_state)


    @evaluator_func("rs1_val", lambda **params: params['is_rvp'] and params['rs1'] is not None)
    def evaluate_rs1_val_p_ext(self, instr_vars, arch_state):
        return self.evaluate_reg_val_p_ext(self.rs1[0], self.rs1_nregs, arch_state)

   
    @evaluator_func("rs1_val", lambda **params: not params['instr_name'] in unsgn_rs1 and not params['is_rvp'] and params['rs1'] is not None and params['rs1'][1] == 'x' and not params['inxFlag'])
    def evaluate_rs1_val_sgn(self, instr_vars, arch_state):
        return self.evaluate_reg_val_sgn(self.rs1[0], instr_vars['xlen'], arch_state)

    @evaluator_func("rs1_val", lambda **params: not params['instr_name'] in unsgn_rs1 and not params['is_rvp'] and params['rs1'] is not None and (params['rs1'][1] == 'f' or params['inxFlag']))
    def evaluate_rs1_val_fsgn(self, instr_vars, arch_state):
        return self.evaluate_reg_val_zdinx32_ext(self.rs1[0], self.rs1_nregs,instr_vars['flen'],instr_vars['xlen'],arch_state)
        
    @evaluator_func("rs1_val", lambda **params: not params['instr_name'] in unsgn_rs1 and not params['is_rvp'] and params['rs1'] is not None and (params['rs1'][1] == 'f' or params['inxFlag']))
    def evaluate_rs1_val_fsgn(self, instr_vars, arch_state):
        return self.evaluate_reg_val_fsgn(self.rs1[0], instr_vars['flen'], instr_vars['xlen'],arch_state)
   

    '''
    Evaluator funcs for rs2_val

    :param arch_state: Architectural state
    :param instr_vars: Dictionary of instruction variables already evaluated
    '''
    @evaluator_func("rs2_val", lambda **params: params['instr_name'] in unsgn_rs2 and params['rs2'] is not None)
    def evaluate_rs2_val_unsgn(self, instr_vars, arch_state):
        return self.evaluate_reg_val_unsgn(self.rs2[0], instr_vars['xlen'], arch_state)


    @evaluator_func("rs2_val", lambda **params: params['is_rvp'] and params['rs2'] is not None)
    def evaluate_rs2_val_p_ext(self, instr_vars, arch_state):
        return self.evaluate_reg_val_p_ext(self.rs2[0], self.rs2_nregs, arch_state)


    @evaluator_func("rs2_val", lambda **params: not params['instr_name'] in unsgn_rs2 and not params['is_rvp'] and params['rs2'] is not None and params['rs2'][1] == 'x'  and not params['inxFlag'])
    def evaluate_rs2_val_sgn(self, instr_vars, arch_state):
        return self.evaluate_reg_val_sgn(self.rs2[0], instr_vars['xlen'], arch_state)


    @evaluator_func("rs2_val", lambda **params: params['is_rvp'] and params['rs2'] is not None)
    def evaluate_rs2_val_fsgn(self, instr_vars, arch_state):
        return self.evaluate_reg_val_zdinx32_ext(self.rs2[0],instr_vars['flen'], instr_vars['xlen'], self.rs2_nregs, arch_state)
        
    @evaluator_func("rs2_val", lambda **params: not params['instr_name'] in unsgn_rs2 and not params['is_rvp'] and params['rs2'] is not None and (params['rs2'][1] == 'f' or params['inxFlag']))
    def evaluate_rs2_val_fsgn(self, instr_vars, arch_state):
        return self.evaluate_reg_val_fsgn(self.rs2[0], instr_vars['flen'], instr_vars['xlen'], arch_state)


   
    
    '''
    Evaluator funcs for rs3_val

    :param arch_state: Architectural state
    :param instr_vars: Dictionary of instruction variables already evaluated
    '''
    @evaluator_func("rs3_val", lambda **params: params['rs3'] is not None and (params['rs3'][1] == 'f' or params['inxFlag']))
    def evaluate_rs3_val_fsgn(self, instr_vars, arch_state):
        return self.evaluate_reg_val_fsgn(self.rs3[0], instr_vars['flen'], instr_vars['xlen'], arch_state)


    '''
    Evaluator funcs for rd_val

    :param arch_state: Architectural state
    :param instr_vars: Dictionary of instruction variables already evaluated
    '''
    @evaluator_func("rd_val", lambda **params: params['instr_name'] in unsgn_rd and params['rd'] is not None)
    def evaluate_rd_val_unsgn(self, instr_vars, arch_state):
        return self.evaluate_reg_val_unsgn(self.rd[0], instr_vars['xlen'], arch_state)

    @evaluator_func("rd_val", lambda **params: not params['instr_name'] in unsgn_rd and params['rd'] is not None  and params['rd'][1] == 'x')
    def evaluate_rd_val_sgn(self, instr_vars, arch_state):
        return self.evaluate_reg_val_sgn(self.rd[0], instr_vars['xlen'], arch_state)


    '''
    Evaluator funcs for extension specific variables

    :param instr_vars: Dictionary of instruction variables already evaluated
    :param arch_state: Architectural state
    :param csr_regfile: Architectural state of CSR register files
    '''
    @evaluator_func("ext_specific_vars", lambda **params: any([params['instr_name'].startswith(pref) for pref in f_instrs_pref]))
    def evaluate_f_ext_sem(self, instr_vars, arch_state, csr_regfile):
        f_ext_vars = {}

        f_ext_vars['fcsr'] = int(csr_regfile['fcsr'], 16)
        
        if 'rs1' in instr_vars and instr_vars['rs1'] is not None and (instr_vars['rs1'].startswith('f') or instr_vars['inxFlag']):
            self.evaluate_reg_sem_f_ext(instr_vars['rs1_val'], instr_vars['flen'], instr_vars['iflen'], "1", f_ext_vars, instr_vars['inxFlag'], instr_vars['xlen'])
        if 'rs2' in instr_vars and instr_vars['rs2'] is not None and (instr_vars['rs2'].startswith('f') or instr_vars['inxFlag']):
            self.evaluate_reg_sem_f_ext(instr_vars['rs2_val'], instr_vars['flen'], instr_vars['iflen'], "2", f_ext_vars, instr_vars['inxFlag'], instr_vars['xlen'])
        if 'rs3' in instr_vars and instr_vars['rs3'] is not None and (instr_vars['rs3'].startswith('f') or instr_vars['inxFlag']):
            self.evaluate_reg_sem_f_ext(instr_vars['rs3_val'], instr_vars['flen'], instr_vars['iflen'], "3", f_ext_vars, instr_vars['inxFlag'], instr_vars['xlen'])
        return f_ext_vars


    '''
    Helper functions for unpacking register values and derived fields
    '''
    def evaluate_reg_val_unsgn(self, reg_idx, xlen, arch_state):
        unsgn_sz = '>I' if xlen == 32 else '>Q'
        return struct.unpack(unsgn_sz, bytes.fromhex(arch_state.x_rf[reg_idx]))[0]


    def evaluate_reg_val_sgn(self, reg_idx, xlen, arch_state):
        sgn_sz = '>i' if xlen == 32 else '>q'
        return struct.unpack(sgn_sz, bytes.fromhex(arch_state.x_rf[reg_idx]))[0]
        



    def evaluate_reg_val_fsgn(self, reg_idx, flen, xlen, arch_state):
        fsgn_sz = '>Q' if flen == 64 else '>I'  
        if self.inxFlg:
            return struct.unpack(fsgn_sz, bytes.fromhex(arch_state.x_rf[reg_idx]))[0]
        
        else:
            return struct.unpack(fsgn_sz, bytes.fromhex(arch_state.f_rf[reg_idx]))[0]

    def evaluate_reg_val_p_ext(self, reg_idx, nregs, arch_state):
        reg_val = self.evaluate_reg_val_unsgn(reg_idx, arch_state)
        if nregs == 2:
            reg_hi_val = self.evaluate_reg_val_unsgn(reg_idx+1, arch_state)
            reg_val = (reg_hi_val << 32) | reg_val
        return reg_val
    
    def evaluate_reg_val_zdinx32_ext(self, reg_idx, nregs, flen,arch_state,xlen):
        reg_val = self.evaluate_reg_val_fsgn(reg_idx,flen,arch_state,xlen)
        if nregs == 2:
            reg_hi_val = self.evaluate_reg_val_fsgn(reg_idx+1,flen,arch_state,xlen)
            reg_val = (reg_hi_val << 32) | reg_val
        return reg_val
        
    def sign_extend(self, value, e_bits, v_bits ):
        return bin(value | ((1<<e_bits) - (1<<v_bits)))
    
    def twos_comp(val, bits):
        """compute the 2's complement of int value val"""
        if (val & (1 << (bits - 1))) != 0: 
            val = val - (1 << bits)        # compute negative value
        return val                         # return positive value as is

    def apndSgnBit(bin_val,sgn_bit):
        new_bin = list(bin_val)
        new_bin[0] = sgn_bit
        final_bin = ''.join(new_bin)
        return final_bin


    
    def evaluate_reg_sem_f_ext(self, reg_val, flen, iflen, postfix, f_ext_vars, inxFlag, xlen):
        '''
        This function expands reg_val and defines the respective sign, exponent and mantissa components
        '''
        if reg_val is None:
            return
        

        if iflen == 16:
            e_sz = 5
            m_sz = 10
        elif iflen == 32:
            e_sz = 8
            m_sz = 23
        else:
            e_sz = 11
            m_sz = 52
        bin_val = ('{:0'+str(flen)+'b}').format(reg_val) 
        

        if flen > iflen:
            if inxFlag and iflen == 16:
                if bin_val[16] == '1' :
                   sgnd_bin_val = bin(reg_val &((1<<flen)-1) | ((1<<flen) - (1<<iflen)))[2:] 
                   f_ext_vars['rs'+postfix+'_sgn_prefix'] = int(sgnd_bin_val[0:iflen],2)
                else:
                   f_ext_vars['rs'+postfix+'_sgn_prefix'] = int(0x0)
            elif inxFlag and iflen == 32:
                if bin_val[32] == '1' :
                   sgnd_bin_val = bin(reg_val &((1<<flen)-1) | ((1<<flen) - (1<<iflen)))[2:] 
                   f_ext_vars['rs'+postfix+'_sgn_prefix'] = int(sgnd_bin_val[0:iflen],2)
                else:
                   f_ext_vars['rs'+postfix+'_sgn_prefix'] = int(0x0)
            else:
                bin_val =bin(reg_val &((1<<flen)-1) | ((1<<flen) - (1<<iflen)))[2:]
            f_ext_vars['rs'+postfix+'_nan_prefix'] =  int(bin_val[0:iflen],2)
            bin_val = bin_val[flen-iflen:]
       

        f_ext_vars['fs'+postfix] = int(bin_val[0], 2)
        f_ext_vars['fe'+postfix] = int(bin_val[1:e_sz+1], 2)
        f_ext_vars['fm'+postfix] = int(bin_val[e_sz+1:], 2)


    def __str__(self):
        line = 'instr: '+ str(self.instr)+ ' addr: '+ str(hex(self.instr_addr)) +' instr_name: '+ str(self.instr_name)
        if self.rd:
            line+= ' rd: '+ str(self.rd)
        if self.rs1:
            line+= ' rs1: '+ str(self.rs1)
        if self.rs2:
            line+= ' rs2: '+ str(self.rs2)
        if self.rs3:
            line+= ' rs3: '+ str(self.rs3)
        if self.csr:
            line+= ' csr: '+ str(self.csr)
        if self.imm:
            line+= ' imm: '+ str(self.imm)
        if self.zimm:
            line+= ' zimm: '+ str(self.zimm)
        if self.shamt:
            line+= ' shamt: '+ str(self.shamt)
        if self.succ:
            line+= ' succ: '+ str(self.succ)
        if self.pred:
            line+= ' pred: '+ str(self.pred)
        if self.rl:
            line+= ' rl: '+ str(self.rl)
        if self.aq:
            line+= ' aq: '+ str(self.aq)
        if self.rm:
            line+= ' rm: '+ str(self.rm)
        if self.reg_commit:
            line+= ' reg_commit: '+ str(self.reg_commit)
        if self.csr_commit:
            line+= ' csr_commit: '+ str(self.csr_commit)
        if self.mnemonic:
            line+= ' mnemonic: '+ str(self.mnemonic)
        return line
