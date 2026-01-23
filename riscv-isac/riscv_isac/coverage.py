
# See LICENSE.incore for details
# See LICENSE.iitm for details

from itertools import islice
from threading import local

import ruamel
from ruamel.yaml import YAML
import riscv_isac.utils as utils
from riscv_isac.constants import *
from riscv_isac.log import logger
from collections import Counter
import sys
from riscv_isac.utils import yaml
from riscv_isac.cgf_normalize import *
import riscv_isac.fp_dataset as fmt
import struct
import pytablewriter
import importlib
import pluggy
import riscv_isac.plugins as plugins
from riscv_isac.plugins.specification import *
import math
from itertools import islice
import multiprocessing as mp
from collections.abc import MutableMapping
import re

instrs_csr_mov = ['csrrw','csrrs','csrrc','csrrwi','csrrsi','csrrci']

csr_reg_num_to_str = {
    3857: 'mvendorid',
    3858: 'marchid',
    3859: 'mimpid',
    3860: 'mhartid',
    768: 'mstatus',
    769: 'misa',
    770: 'medeleg',
    771: 'mideleg',
    772: 'mie',
    773: 'mtvec',
    774: 'mcounteren',
    784: 'mstatush',
    832: 'mscratch',
    833: 'mepc',
    834: 'mcause',
    835: 'mtval',
    836: 'mip',
    928: 'pmpcfg0',
    929: 'pmpcfg1',
    930: 'pmpcfg2',
    931: 'pmpcfg3',
    2816: 'mcycle',
    2818: 'minstret',
    2944: 'mcycleh',
    2946: 'minstreth',
    800: 'mcountinhibit',
    1952: 'tselect',
    1953: 'tdata1',
    1954: 'tdata2',
    1955: 'tdata3',
    1968: 'dcsr',
    1969: 'dpc',
    1970: 'dscratch0',
    1971: 'dscratch1',
    256: 'sstatus',
    258:'sedeleg',
    259: 'sideleg',
    260: 'sie',
    261: 'stvec',
    262: 'scounteren',
    320: 'sscratch',
    321: 'sepc',
    322: 'scause',
    323: 'stval',
    324: 'sip',
    384: 'satp',
    9: 'vxsat',
    1: 'fflags',
    2: 'frm',
    3: 'fcsr',
    944: 'pmpaddr0',
    945: 'pmpaddr1',
    946: 'pmpaddr2',
    947: 'pmpaddr3',
    948: 'pmpaddr4',
    949: 'pmpaddr5',
    950: 'pmpaddr6',
    951: 'pmpaddr7',
    952: 'pmpaddr8',
    953: 'pmpaddr9',
    954: 'pmpaddr10',
    955: 'pmpaddr11',
    956: 'pmpaddr12',
    957: 'pmpaddr13',
    958: 'pmpaddr14',
    959: 'pmpaddr15',
    960: 'pmpaddr16',
    961: 'pmpaddr17',
    962: 'pmpaddr18',
    963: 'pmpaddr19',
    964: 'pmpaddr20',
    965: 'pmpaddr21',
    966: 'pmpaddr22',
    967: 'pmpaddr23',
    968: 'pmpaddr24',
    969: 'pmpaddr25',
    970: 'pmpaddr26',
    971: 'pmpaddr27',
    972: 'pmpaddr28',
    973: 'pmpaddr29',
    974: 'pmpaddr30',
    975: 'pmpaddr31',
    976: 'pmpaddr32',
    977: 'pmpaddr33',
    978: 'pmpaddr34',
    979: 'pmpaddr35',
    980: 'pmpaddr36',
    981: 'pmpaddr37',
    982: 'pmpaddr38',
    983: 'pmpaddr39',
    984: 'pmpaddr40',
    985: 'pmpaddr41',
    986: 'pmpaddr42',
    987: 'pmpaddr43',
    988: 'pmpaddr44',
    989: 'pmpaddr45',
    990: 'pmpaddr46',
    991: 'pmpaddr47',
    992: 'pmpaddr48',
    993: 'pmpaddr49',
    994: 'pmpaddr50',
    995: 'pmpaddr51',
    996: 'pmpaddr52',
    997: 'pmpaddr53',
    998: 'pmpaddr54',
    999: 'pmpaddr55',
    1000: 'pmpaddr56',
    1001: 'pmpaddr57',
    1002: 'pmpaddr58',
    1003: 'pmpaddr59',
    1004: 'pmpaddr60',
    1005: 'pmpaddr61',
    1006: 'pmpaddr62',
    1007: 'pmpaddr63',
    928: 'pmpcfg0',
    929: 'pmpcfg1',
    930: 'pmpcfg2',
    931: 'pmpcfg3',
    932: 'pmpcfg4',
    933: 'pmpcfg5',
    934: 'pmpcfg6',
    935: 'pmpcfg7',
    936: 'pmpcfg8',
    937: 'pmpcfg9',
    938: 'pmpcfg10',
    939: 'pmpcfg11',
    940: 'pmpcfg12',
    941: 'pmpcfg13',
    942: 'pmpcfg14',
    943: 'pmpcfg15',
    266: 'senvcfg',
    778: 'menvcfg',
    1863: 'mseccfg'
}

class cross():

    BASE_REG_DICT = { 'x'+str(i) : 'x'+str(i) for i in range(32)}

    def __init__(self,label,coverpoint,xlen,flen,addr_pairs,sig_addrs,window_size,inxFlg):

        self.label = label
        self.coverpoint = coverpoint
        self.xlen = xlen
        self.flen = flen
        self.addr_pairs = addr_pairs
        self.sig_addrs = sig_addrs
        self.window_size = window_size

        self.arch_state = archState(xlen,flen,inxFlg)
        self.csr_regfile = csr_registers(xlen)
        self.iptw_dict = {}
        self.mem_vals = {}
        self.stats = statistics(xlen, flen)

        self.result = 0
        self.queue = []

        self.tracked_regs = OrderedSet()
        self.instr_addr_of_tracked_reg = {} # tracked_reg: instr_addr of instr which triggered its tracking
        self.instr_stat_meta_at_addr = {} # start_instr_addr: [is_ucovpt, num_exp, num_obs, num_rem, covpts_hit, code_seq, store_addresses, store_vals]

        ## Extract relevant information from coverpt
        self.data = self.coverpoint.split('::')
        self.ops = self.data[0].replace(' ', '')[1:-1].split(':')
        self.assign_lst = self.data[1].replace(' ', '')[1:-1].split(':')
        self.cond_lst = self.data[2].lstrip().rstrip()[1:-1].split(':')

        if len(self.ops) > window_size:
            logger.error(f'Size of opcode list greater than the window size in the cross_comb coverpoint: {coverpoint}')

    def process(self, instr):
        if len(self.ops) > self.window_size:
            return
        self.queue.append(instr)
        if len(self.queue) >= len(self.ops):
            self.compute_cross_cov()

    def finish_up(self):
        if len(self.ops) > self.window_size:
            return
        for i in range(len(self.queue)):
            self.compute()

        # update stats one last time for remaining elements
        for key_instr_addr in list(self.instr_stat_meta_at_addr.keys()):
            stat_meta = self.instr_stat_meta_at_addr[key_instr_addr]
            if stat_meta[0]: # is_ucovpt
                if stat_meta[2] == stat_meta[1]: # num_observed == num_expected
                    # update STAT1 with (store_addresses, store_vals, covpt, code_seq)
                    self.stats.stat1.append((stat_meta[6], stat_meta[7], stat_meta[4], stat_meta[5]))
                elif stat_meta[2] < stat_meta[1]: # num_observed < num_expected
                    # update STAT3 with code sequence
                    self.stats.stat3.append('\n'.join(stat_meta[5]))
            else: # not is_ucovpt
                if stat_meta[2] > 0: # num_observed > 0
                    # update STAT2
                    _log = 'Op without unique coverpoint updates Signature\n'

                    _log += ' -- Code Sequence:\n'
                    for op in stat_meta[5]:
                        _log += '      ' + op + '\n'

                    _log += ' -- Signature Addresses:\n'
                    for store_address, store_val in zip(stat_meta[6], stat_meta[7]):
                        _log += '      Address: {0} Data: {1}\n'.format(
                                str(hex(store_address)), store_val)

                    _log += ' -- Redundant Coverpoints hit by the op\n'
                    for c in stat_meta[4]:
                        _log += '      - ' + str(c) + '\n'

                    logger.warn(_log)
                    self.stats.stat2.append(_log + '\n\n')

            del self.instr_stat_meta_at_addr[key_instr_addr]

    def compute_cross_cov(self):
        '''
        Check whether the cross coverage coverpoint was hit or not and update the metric
        Also perform tracking for generating the data propagation report
        '''
        hit_covpt = False
        regs_to_track = OrderedSet()

        for index in range(len(self.ops)):
            instr = self.queue[index]
            instr_name = instr.instr_name
            if self.addr_pairs:
                if not (any([instr.instr_addr >= saddr and instr.instr_addr < eaddr for saddr,eaddr in self.addr_pairs])):
                    break

            rd = None
            rs1 = None
            rs2 = None
            rs3 = None
            imm = None
            zimm = None
            csr = None
            shamt = None
            succ = None
            pred = None
            rl = None
            aq = None
            rm = None

            if instr.rd is not None:
                rd = instr.rd[1] + str(instr.rd[0])
            if instr.rs1 is not None:
                rs1 = instr.rs1[1] + str(instr.rs1[0])
            if instr.rs2 is not None:
                rs2 = instr.rs2[1] + str(instr.rs2[0])
            if instr.rs3 is not None:
                rs3 = instr.rs3[1] + str(instr.rs3[0])
            if instr.imm is not None:
                imm = int(instr.imm)
            if instr.zimm is not None:
                zimm = int(instr.zimm)
            if instr.csr is not None:
                csr = instr.csr
            if instr.shamt is not None:
                shamt = int(instr.shamt)
            if instr.succ is not None:
                succ = int(instr.succ)
            if instr.pred is not None:
                pred = int(instr.pred)
            if instr.rl is not None:
                rl = int(instr.rl)
            if instr.aq is not None:
                aq = int(instr.aq)
            if instr.rm is not None:
                rm = int(instr.rm)

            if self.ops[index].find('?') == -1:
                # Handle instruction tuple
                if self.ops[index].find('(') != -1:
                    check_lst = self.ops[index].replace('(', '').replace(')', '').split(',')
                else:
                    check_lst = [self.ops[index]]
                if (instr_name not in check_lst):
                    break

                # get changes to track due to this instr
                regs_to_track_immutable, regs_to_track_mutable, instrs_to_track = instr.get_elements_to_track(self.xlen)
                regs_to_track.update(regs_to_track_immutable)

            if self.cond_lst[index].find('?') == -1:
                if(eval(self.cond_lst[index], locals(), cross.BASE_REG_DICT)):
                    if(index==len(self.ops)-1):
                        self.result = self.result + 1
                        hit_covpt = True
                else:
                    break

            if self.assign_lst[index].find('?') == -1:
                exec(self.assign_lst[index], locals(), cross.BASE_REG_DICT)

        if hit_covpt:
            self.stats.cov_pt_sig += [self.coverpoint]

            start_instr = self.queue[0]
            hit_uniq_covpt = self.result == 1
            num_exp = len(regs_to_track)

            for reg in regs_to_track:
                if reg in self.tracked_regs:
                    stat_meta = self.instr_stat_meta_at_addr[self.instr_addr_of_tracked_reg[reg]]
                    stat_meta[3] -= 1
                    self.tracked_regs.remove(reg)
                    del self.instr_addr_of_tracked_reg[reg]

                self.tracked_regs.add(reg)
                self.instr_addr_of_tracked_reg[reg] = start_instr.instr_addr

            self.instr_stat_meta_at_addr[start_instr.instr_addr] = [hit_uniq_covpt, num_exp, 0, num_exp, [self.coverpoint], [], [], []]

            for i in range(len(self.ops)):
                self.compute(True)
        else:
            self.compute()

    def compute(self, is_part_of_covpt=False):
        instr = self.queue.pop(0)

        mnemonic = instr.mnemonic

        # check if instruction lies within the valid region of interest
        if self.addr_pairs:
            if any([instr.instr_addr >= saddr and instr.instr_addr < eaddr for saddr,eaddr in self.addr_pairs]):
                enable = True
            else:
                enable = False

        instr_vars = {}
        instr.evaluate_instr_vars(self.xlen, self.flen, self.arch_state, self.csr_regfile, instr_vars)

        if enable:
            # check for changes in tracked registers
            if not is_part_of_covpt:
                changed_regs = instr.get_changed_regs(self.arch_state, self.csr_regfile)
                for reg in changed_regs:
                    if reg in self.tracked_regs:
                        stat_meta = self.instr_stat_meta_at_addr[self.instr_addr_of_tracked_reg[reg]]
                        stat_meta[3] -= 1
                        self.tracked_regs.remove(reg)
                        del self.instr_addr_of_tracked_reg[reg]

            # update code_seq
            if self.instr_stat_meta_at_addr:
                if mnemonic is not None:
                    self.stats.code_seq.append('[' + str(hex(instr.instr_addr)) + ']:' + mnemonic)
                else:
                    self.stats.code_seq.append('[' + str(hex(instr.instr_addr)) + ']:' + instr.instr_name)

            for key_instr_addr, stat_meta in self.instr_stat_meta_at_addr.items():
                if mnemonic is not None:
                    stat_meta[5].append('[' + str(hex(instr.instr_addr)) + ']:' + mnemonic)
                else:
                    stat_meta[5].append('[' + str(hex(instr.instr_addr)) + ']:' + instr.instr_name)

        # handle signature update
        if instr.is_sig_update() and self.sig_addrs:
            store_address = instr_vars['rs1_val'] + instr_vars['imm_val']
            store_val = '0x'+arch_state.x_rf[instr.rs2[0]]
            for start, end in self.sig_addrs:
                if store_address >= start and store_address <= end:
                    logger.debug('Signature update : ' + str(hex(store_address)))

                    rs2 = instr_vars['rs2']
                    if rs2 in self.tracked_regs:
                        stat_meta = self.instr_stat_meta_at_addr[self.instr_addr_of_tracked_reg[rs2]]
                        stat_meta[2] += 1 # increase num observed
                        stat_meta[3] -= 1 # decrease num remaining
                        stat_meta[6].append(store_address) # add to store_addresses
                        stat_meta[7].append(store_val) # add to store_vals
                        self.stats.last_meta = [store_address, store_val, stat_meta[4], stat_meta[5]]
                        self.tracked_regs.remove(rs2)
                        del self.instr_addr_of_tracked_reg[rs2]
                    else:
                        if len(self.stats.last_meta):
                            _log = 'Last Coverpoint : ' + str(self.stats.last_meta[2]) + '\n'
                            _log += 'Last Code Sequence : \n\t-' + '\n\t-'.join(self.stats.last_meta[3]) + '\n'
                            _log += 'Current Store : [{0}] : {1} -- Store: [{2}]:{3}\n'.format(\
                                str(hex(instr.instr_addr)), mnemonic,
                                str(hex(store_address)),
                                store_val)
                            logger.error(_log)
                            self.stats.stat4.append(_log + '\n\n')

                    self.stats.code_seq = []

        # update stats
        for key_instr_addr in list(self.instr_stat_meta_at_addr.keys()):
            stat_meta = self.instr_stat_meta_at_addr[key_instr_addr]
            if stat_meta[3] == 0: # num_remaining == 0
                if stat_meta[0]: # is_ucovpt
                    if stat_meta[2] == stat_meta[1]: # num_observed == num_expected
                        # update STAT1 with (store_addresses, store_vals, covpt, code_seq)
                        self.stats.stat1.append((stat_meta[6], stat_meta[7], stat_meta[4], stat_meta[5]))
                    elif stat_meta[2] < stat_meta[1]: # num_observed < num_expected
                        # update STAT3 with code sequence
                        self.stats.stat3.append('\n'.join(stat_meta[5]))
                else: # not is_ucovpt
                    if stat_meta[2] > 0: # num_observed > 0
                        # update STAT2
                        _log = 'Op without unique coverpoint updates Signature\n'

                        _log += ' -- Code Sequence:\n'
                        for op in stat_meta[5]:
                            _log += '      ' + op + '\n'

                        _log += ' -- Signature Addresses:\n'
                        for store_address, store_val in zip(stat_meta[6], stat_meta[7]):
                            _log += '      Address: {0} Data: {1}\n'.format(
                                    str(hex(store_address)), store_val)

                        _log += ' -- Redundant Coverpoints hit by the op\n'
                        for c in stat_meta[4]:
                            _log += '      - ' + str(c) + '\n'

                        logger.warn(_log)
                        self.stats.stat2.append(_log + '\n\n')

                del self.instr_stat_meta_at_addr[key_instr_addr]

            instr.update_arch_state(self.arch_state, self.csr_regfile, self.mem_vals)

    def get_metric(self):
        return self.result

    def get_stats(self):
        return self.stats


class csr_registers(MutableMapping):
    '''
    Defines the architectural state of CSR Register file.
    '''

    def __init__ (self, xlen):
        '''
        Class constructor

        :param xlen: max XLEN value of the RISC-V device

        :type xlen: int

        Currently defines the CSR register files the
        width of which is defined by the xlen parameter. These are
        implemented as an array holding the hexadecimal representations of the
        values as string. These can be accessed by both integer addresses as well as string names

        '''

        if(xlen==32):
            self.csr = ['00000000']*4096
            self.csr[int('301',16)] = '40000000' # misa
        else:
            self.csr = ['0000000000000000']*4096
            self.csr[int('301',16)] = '8000000000000000' # misa

        # M-Mode CSRs
        self.csr[int('F11',16)] = '00000000' # mvendorid
        self.csr[int('306',16)] = '00000000' # mcounteren
        self.csr[int('B00',16)] = '0000000000000000' # mcycle
        self.csr[int('B02',16)] = '0000000000000000' # minstret
        for i in range(29): # mphcounter 3-31, 3h-31h
            self.csr[int('B03',16)+i] = '0000000000000000'
            self.csr[int('B83',16)+i] = '00000000'
        self.csr[int('320',16)] = '00000000' # mcounterinhibit
        self.csr[int('B80',16)] = '00000000' # mcycleh
        self.csr[int('B82',16)] = '00000000' # minstreth
        self.csr[int('001',16)] = '00000000'
        self.csr[int('002',16)] = '00000000'
        self.csr[int('003',16)] = '00000000'
        self.csr[int('310',16)] = '00000000'

        ## mtime, mtimecmp => 64 bits, platform defined memory mapping

        # S-Mode CSRs
        self.csr[int('106',16)] = '00000000' # scounteren

        self.csr_regs={
            "mvendorid":int('F11',16),
            "marchid":int('F12',16),
            "mimpid":int('F13',16),
            "mhartid":int('F14',16),
            "mstatus":int('300',16),
            "misa":int('301',16),
            "medeleg":int('302',16),
            "mideleg":int('303',16),
            "mie":int('304',16),
            "mtvec":int('305',16),
            "mcounteren":int('306',16),
            "mstatush":int('310',16),
            "mscratch":int('340',16),
            "mepc":int('341',16),
            "mcause":int('342',16),
            "mtval":int('343',16),
            "mip":int('344',16),
            "pmpcfg0":int('3A0',16),
            "pmpcfg1":int('3A1',16),
            "pmpcfg2":int('3A2',16),
            "pmpcfg3":int('3A3',16),
            "pmpcfg4":int('3A4',16),
            "pmpcfg5":int('3A5',16),
            "pmpcfg6":int('3A6',16),
            "pmpcfg7":int('3A7',16),
            "pmpcfg8":int('3A8',16),
            "pmpcfg9":int('3A9',16),
            "pmpcfg10":int('3AA',16),
            "pmpcfg11":int('3AB',16),
            "pmpcfg12":int('3AC',16),
            "pmpcfg13":int('3AD',16),
            "pmpcfg14":int('3AE',16),
            "pmpcfg15":int('3AF',16),
            "mcycle":int('B00',16),
            "minstret":int('B02',16),
            "mcycleh":int('B80',16),
            "minstreth":int('B82',16),
            "mcountinhibit":int('320',16),
            "tselect":int('7A0',16),
            "tdata1":int('7A1',16),
            "tdata2":int('7A2',16),
            "tdata3":int('7A3',16),
            "dcsr":int('7B0',16),
            "dpc":int('7B1',16),
            "dscratch0":int('7B2',16),
            "dscratch1":int('7B3',16),
            "sstatus": int('100',16),
            "sedeleg": int('102',16),
            "sideleg": int('103',16),
            "sie": int('104',16),
            "stvec": int('105',16),
            "scounteren": int('106',16),
            "sscratch": int('140',16),
            "sepc": int('141',16),
            "scause": int('142',16),
            "stval": int('143',16),
            "sip": int('144',16),
            "satp": int('180',16),
            "vxsat": int('009',16),
            "fflags":int('1',16),
            "frm":int('2',16),
            "fcsr":int('3',16),
            "menvcfg":int('30A', 16),
            "senvcfg":int('10A', 16),
            "mseccfg":int('747', 16)
        }
        for i in range(16):
            self.csr_regs["pmpaddr"+str(i)] = int('3B0',16)+i
        for i in range(3,32):
            self.csr_regs["mhpmcounter"+str(i)] = int('B03',16) + (i-3)
            self.csr_regs["mhpmcounter"+str(i)+"h"] = int('B83',16) + (i-3)
            self.csr_regs["mhpmevent"+str(i)] = int('323',16) + (i-3)

    def __setitem__ (self,key,value):

        if(isinstance(key, str)):
            self.csr[self.csr_regs[key]] = value
        else:
            self.csr[key] = value

    def __iter__(self):
        for entry in self.csr_regs.keys():
            yield (entry,self.csr_regs[entry],self.csr[self.csr_regs[entry]])

    def __len__(self):
        return len(self.csr)

    def __delitem__(self,key):
        pass

    def __getitem__ (self,key):
        if(isinstance(key, str)):
            return self.csr[self.csr_regs[key]]
        else:
            return self.csr[key]

class archState:
    '''
    Defines the architectural state of the RISC-V device.
    '''

    def __init__ (self, xlen, flen,inxFlg):
        '''
        Class constructor

        :param xlen: max XLEN value of the RISC-V device
        :param flen: max FLEN value of the RISC-V device

        :type xlen: int
        :type flen: int

        Currently defines the integer and floating point register files the
        width of which is defined by the xlen and flen parameters. These are
        implemented as an array holding the hexadecimal representations of the
        values as string.

        The program counter is also defined as an int.

        '''

        if xlen == 32:
            self.x_rf = ['00000000']*32
        else:
            self.x_rf = ['0000000000000000']*32

        if flen == 16:
            self.f_rf = ['0000']*32
            self.fcsr = 0
        elif flen == 32:
            self.f_rf = ['00000000']*32

        else:
            self.f_rf = ['0000000000000000']*32
        self.pc = 0
        self.flen = flen
        self.inxFlg = inxFlg

class statistics:
    '''
    Class for holding statistics used for Data propagation report
    '''

    def __init__(self, xlen, flen):
        '''
        This class maintains a collection of arrays which are useful in
        calculating the following set of statistics:

        - STAT1 : Number of instructions that hit unique coverpoints and update the signature.
        - STAT2 : Number of instructions that hit covepoints which are not unique but still update the signature
        - STAT3 : Number of instructions that hit a unique coverpoint but do not update signature
        - STAT4 : Number of multiple signature updates for the same coverpoint
        - STAT5 : Number of times the signature was overwritten
        '''

        self.xlen = xlen
        self.flen = flen

        self.stat1 = []
        self.stat2 = []
        self.stat3 = []
        self.stat4 = []
        self.stat5 = []
        self.code_seq = []
        self.cov_pt_sig = []
        self.last_meta = []

    def __add__(self, o):
        temp = statistics(self.xlen, self.flen)
        temp.stat1 = self.stat1 + o.stat1
        temp.stat2 = self.stat2 + o.stat2
        temp.stat3 = self.stat3 + o.stat3
        temp.stat4 = self.stat4 + o.stat4
        temp.stat5 = self.stat5 + o.stat5

        temp.code_seq = self.code_seq + o.code_seq
        temp.cov_pt_sig = self.cov_pt_sig + o.cov_pt_sig
        temp.last_meta = self.last_meta + o.last_meta

        return temp

def pretty_print_yaml(yaml_obj):
    res = ''''''
    for line in utils.dump_yaml(yaml_obj, indent=5, block_seq_indent=3).splitlines(True):
        res += line
    return res

def pretty_print_regfile(regfile):
    res = ""
    for index in range(0, 32, 4):
        print('x'+str(index) +   ' : ' + regfile[index] + '\t' +\
              'x'+str(index+1) + ' : ' + regfile[index+1] + '\t' + \
              'x'+str(index+2) + ' : ' + regfile[index+2] + '\t' + \
              'x'+str(index+3) + ' : ' + regfile[index+3] + '\t' )
    print('\n\n')

def gen_report(cgf, detailed):
    '''
    Function to convert a CGF to a string report. A detailed report includes the individual coverpoints and the corresponding values of the same

    :param cgf: an input CGF dictionary
    :param detailed: boolean value indicating a detailed report must be generated.

    :type cgf: dict
    :type detailed: bool

    :return: string holding the final report
    '''
    temp = cgf.copy()
    for cov_labels, value in cgf.items():
        if cov_labels != 'datasets':
            total_uncovered = 0
            total_categories = 0
            for categories in value:
                if categories not in ['cond','config','ignore', 'base_op', 'p_op_cond']:
                    for coverpoints, coverage in value[categories].items():
                        if coverage == 0:
                            total_uncovered += 1
                    total_categories += len(value[categories])
            for categories in value:
                if categories not in ['cond','config','ignore', 'base_op', 'p_op_cond']:
                    uncovered = 0
                    for coverpoints, coverage in value[categories].items():
                        if coverage == 0:
                            uncovered += 1
                    percentage_covered = str((len(value[categories]) - uncovered)/len(value[categories]))
                    node_level_str =  '  ' + categories + ':\n'
                    node_level_str += '    coverage: ' + \
                            str(len(value[categories]) - uncovered) + \
                            '/' + str(len(value[categories]))
                    temp[cov_labels][categories]['coverage'] = '{0}/{1}'.format(\
                        str(len(value[categories]) - uncovered),\
                        str(len(value[categories])))
            temp[cov_labels]['total_coverage'] = '{0}/{1}'.format(\
                    str(total_categories-total_uncovered),\
                    str(total_categories))
    return dict(temp)

def merge_files(files,i,k):
    '''
    Merges files from i to n where n is len(files) or i+k

    Arguments:

    files: List of dictionaries to be merged
    i : beginning index to merge files on a given core
    k : number of files to be merged

    '''

    temp = files[i]
    n = min(len(files),i+k)
    for logs_cov in files[i+1:n]:
        for cov_labels, value in logs_cov.items():
            if cov_labels not in temp:
                temp[cov_labels] = value
                continue
            for categories in value:
                if categories not in ['cond','config','ignore','total_coverage','coverage']:
                    if categories not in temp[cov_labels]:
                        temp[cov_labels][categories] = value[categories]
                        continue
                    for coverpoints, coverage in value[categories].items():
                        if coverpoints not in temp[cov_labels][categories]:
                            temp[cov_labels][categories][coverpoints] = coverage
                        else:
                            temp[cov_labels][categories][coverpoints] += coverage
    return temp

def merge_fn(files, cgf, p):

    '''
    Each core is assigned ceil(n/k) processes where n is len(files)
    '''


    pool_work = mp.Pool(processes = p)
    while(len(files)>1):
        n = len(files)
        max_process = math.ceil(n/p)
        if(max_process==1):
            max_process = 2
        files = pool_work.starmap_async(merge_files,[(files,i,max_process) for i in range(0,n,max_process)])
        files = files.get()
    pool_work.close()
    pool_work.join()

    return files[0]


def merge_coverage(inp_files, cgf, detailed, p=1):
    '''
    This function merges values of multiple CGF files and return a single cgf
    file. This can be treated analogous to how coverage files are merged
    traditionally.

    :param inp_files: an array of input CGF file names which need to be merged.
    :param cgf: a cgf against which coverpoints need to be checked for.
    :param detailed: a boolean value indicating if a detailed report needs to be generated
    :param p: Number of worker processes (>=1)

    :type inp_files: [str]
    :type cgf: dict
    :type detailed: bool
    :type p: int

    :return: a string contain the final report of the merge.
    '''
    files = []
    for logs in inp_files:
        files.append(utils.load_yaml_file(logs))

    temp = merge_fn(files,cgf,p)
    for cov_labels, value in temp.items():
        for categories in value:
            if categories not in ['cond','config','ignore','total_coverage','coverage', 'base_op', 'p_op_cond']:
                for coverpoints, coverage in value[categories].items():
                    if coverpoints in cgf[cov_labels][categories]:
                        cgf[cov_labels][categories][coverpoints] += coverage

    return gen_report(cgf, detailed)

def twos_complement(val,bits):
    if (val & (1 << (bits - 1))) != 0:
        val = val - (1 << bits)
    return val

def simd_val_unpack(val_comb, op_width, op_name, val, local_dict):
    '''
    This function unpacks `val` into its simd elements.

    :param val_comb: val_comb from the cgf dictionary
    :param op_name: name of the operand (rs1/rs2)
    :param val: operand value
    :param local_dict: locals() of the calling context

    '''
    simd_size = op_width
    simd_sgn = False
    for coverpoints in val_comb:
        if f"{op_name}_b0_val" in coverpoints:
            simd_size = 8
        if f"{op_name}_h0_val" in coverpoints:
            simd_size = 16
        if f"{op_name}_w0_val" in coverpoints:
            simd_size = 32
        if op_name in coverpoints:
            if any([s in coverpoints for s in ["<", "== -", "== (-"]]):
                simd_sgn = True

    fmt = {8: 'b', 16: 'h', 32: 'w', 64: 'd'}
    sz = fmt[simd_size]

    if simd_size > op_width:
        return

    elm_urange = 1<<simd_size
    elm_mask = elm_urange-1
    elm_msb_mask = (1<<(simd_size-1))
    for i in range(op_width//simd_size):
        elm_val = (val >> (i*simd_size)) & elm_mask
        if simd_sgn and (elm_val & elm_msb_mask) != 0:
            elm_val = elm_val - elm_urange
        local_dict[f"{op_name}_{sz}{i}_val"]=elm_val
    if simd_size == op_width:
        local_dict[f"{op_name}_val"]=elm_val

def compute_per_line(queue, event, cgf_queue, stats_queue, cgf, xlen, flen, addr_pairs, sig_addrs, stats, arch_state, csr_regfile, iptw_dict, mem_vals, no_count, elf):
    '''
    This function checks if the current instruction under scrutiny matches a
    particular coverpoint of interest. If so, it updates the coverpoints and
    returns the same.

    :param queue: A queue thread to push instructionObject
    :param event: Event object to signal completion of decoding
    :param cgf_queue: A queue thread to push updated cgf
    :param stats_queue: A queue thread to push updated `stats` object

    :param cgf: a cgf against which coverpoints need to be checked for.
    :param xlen: Max xlen of the trace
    :param flen: Max flen of the trace
    :param addr_pairs: pairs of start and end addresses for which the coverage needs to be updated
    :param sig_addrs: pairs of start and end addresses for which signature update needs to be checked
    :param stats: `stats` object
    :param csr_regfile: Architectural state of CSR register file
    :param result_count:

    :type queue: class`multiprocessing.Queue`
    :type event: class`multiprocessing.Event`
    :type cgf_queue: class`multiprocessing.Queue`
    :type stats_queue: class`multiprocessing.Queue`
    :type instr: :class:`instructionObject`
    :type cgf: dict
    :type xlen: int
    :type flen: int
    :type addr_pairs: (int, int)
    :type sig_addrs: (int, int)
    :type stats: class `statistics`
    :type csr_regfile: class `csr_registers`
    :type result_count: int
    '''

    # List to hold hit coverpoints
    hit_covpts = []
    rcgf = copy.deepcopy(cgf)
    inxFlg = arch_state.inxFlg

    # Set of elements to monitor for tracking signature updates
    tracked_regs_immutable = OrderedSet()
    tracked_regs_mutable = OrderedSet()
    tracked_instrs = [] # list of tuples of the type (list_instr_names, triggering_instr_addr)

    instr_stat_meta_at_addr = {} # Maps an address to the stat metadata of the instruction present at that address [is_ucovpt, num_exp, num_obs, num_rem, covpts_hit, code_seq, store_addresses, store_vals]
    instr_addr_of_tracked_reg = {} # Maps a tracked register to the address of instruction which triggered its tracking

    # Enter the loop only when Event is not set or when the
    # instruction object queue is not empty
    while (event.is_set() == False) or (queue.empty() == False):

        # If there are instructions in queue, compute coverage
        if queue.empty() is False:

            instr = queue.get_nowait()

            # if instruction is empty then return
            if instr is None:
                return cgf

            mnemonic = instr.mnemonic

            # check if instruction lies within the valid region of interest
            if addr_pairs:
                if any([instr.instr_addr >= saddr and instr.instr_addr < eaddr for saddr,eaddr in addr_pairs]):
                    enable = True
                else:
                    enable = False
            else:
                enable=True

            instr_vars = {}
            instr_vars['inxFlag'] = instr.inxFlg

            #csr regfile track for the previous instruction(old_csr_regfile)
            old_csr_regfile = {}
            for i in csr_regfile.csr_regs:
                if isinstance(csr_regfile[i], str):
                    old_csr_regfile[i] = int(csr_regfile[i],16)
                else:
                    old_csr_regfile[i] = csr_regfile[i]

            def old_fn_csr_comb_covpt(csr_reg):
                return old_csr_regfile[csr_reg]

            #update instr_vars using updated arch state and updated csr_regfile
            instr.evaluate_instr_vars(xlen, flen, arch_state, csr_regfile, instr_vars)
            #update the arch state and csr_regfile for the current instruction
            instr.update_arch_state(arch_state, csr_regfile, mem_vals)

            #update the state of trap registers in csr_reg file using instr_vars
            # if instr_vars["mode_change"] is not None:  #change the state only on the instruction
            csr_regfile["mcause"] = instr_vars["mcause"]
            csr_regfile["scause"] = instr_vars["scause"]
            csr_regfile["mtval"]  = instr_vars["mtval"]
            csr_regfile["stval"]  = instr_vars["stval"]

            if 'rs1' in instr_vars:
                rs1 = instr_vars['rs1']
            if 'rs2' in instr_vars:
                rs2 = instr_vars['rs2']
            if 'rs3' in instr_vars:
                rs3 = instr_vars['rs3']
            if 'rd' in instr_vars:
                is_rd_valid = True
                rd = instr_vars['rd']
            else:
                is_rd_valid = False

            for i in csr_regfile.csr_regs:
                if isinstance(csr_regfile[i], str):
                    instr_vars[i] = int(csr_regfile[i],16)
                else:
                    instr_vars[i] = csr_regfile[i]
            instr.iptw_update(instr_vars, iptw_dict)
            instr.ptw_update(instr_vars)

            for i in iptw_dict:
                instr_vars[i] = (iptw_dict[i])

            csr_write_vals = {}
            if instr.csr_commit is not None:
                for commit in instr.csr_commit:
                    if commit[0] == "CSR" and commit[3]:
                        csr_write_vals[commit[1]] = int(commit[3],16)
            def write_fn_csr_comb_covpt(csr_reg):
                if csr_reg in csr_write_vals:
                    return csr_write_vals[csr_reg]
                else:
                    return int(csr_regfile[csr_reg],16)

            def check_label_address(label):
                return utils.collect_label_address(elf, label)

            def get_mem_val(addr, bytes):
                if addr in mem_vals:
                    return mem_vals.get(addr)
                else:
                    mem_val = utils.get_value_at_location(elf_path = elf, location = addr, bytes = bytes)
                    if mem_val is not None:
                        mem_vals[addr] = mem_val
                        return mem_val
                    else:
                        return None

            def get_pte(pa, pte_addr, pgtb_addr):
                if instr_vars['xlen'] == 64:
                    pte_size = 8
                elif instr_vars['xlen'] == 32:
                    pte_size = 4
                if (pgtb_addr >> 12) == (pte_addr >> 12):
                    if ((pa >> 12) == (get_mem_val(pte_addr, pte_size) >> 10)):
                        return get_mem_val(pte_addr, pte_size)
                    else:
                        return None
                else:
                    return None

            def get_pte_prop(prop_name, pte_addr):
                """
                Function to check specific permissions of a PTE.

                :param prop_name: string containing properties to check.
                                Uppercase letters mean the bits should be set.
                                Lowercase letters mean the bits should NOT be set.
                                Example: "uAdW" checks U and D bits are NOT set,
                                        while A and W bits are set.
                :param pte_addr: PTE address to examine (int or hex).
                :return: 1 if conditions are met, 0 otherwise.
                """
                if pte_addr is None:
                    return 0
                
                bitmask_dict = {
                    'V': 0x01, 'R': 0x02, 'W': 0x04, 'X': 0x08,
                    'U': 0x10, 'G': 0x20, 'A': 0x40, 'D': 0x80
                }

                # Get permission bits from PTE address
                pte_per = pte_addr & 0x3FF

                # Check each property in prop_name
                for char in prop_name:
                    # Check if uppercase character should be set or lowercase should NOT be set
                    bitmask = bitmask_dict.get(char.upper())
                    if bitmask is None:
                        return 0  # If unrecognized character, then return overall zero prematurely.

                    if (char.isupper() and not (pte_per & bitmask)) or (char.islower() and (pte_per & bitmask)):
                        return 0

                return 1


            def pmp_rgn_chk(req_addr, access_len, pmp_config, pmp_addr, prev_pmp_addr = None):
                """
                Function to check whether the requested address is inside the required setup pmpaddr entry.

                :param req_addr: value for the requested addrress (int or hex).
                :param access_len: For instance, 1 for lb, 2 for lh and ...
                :param pmp_config: Selected PMP Configuration for that region. i.e., TOR, NA4, NAPOT
                :param pmp_addr: pmpaddr csr value to examine (int or hex).
                :param prev_pmp_addr: prev pmpaddr csr value to examine required in case of TOR (int or hex).

                :return: True if conditions are met, False otherwise.
                """

                #Skip the not required cases.
                if pmp_addr is None or access_len is None:
                    return False

                #Implementation credits: Sail RISC-V Golden Reference Model.
                if pmp_config == "NAPOT":
                    mask = pmp_addr ^ (pmp_addr + 1)
                    lo = pmp_addr & (~(mask))
                    length = mask + 1
                    #requested address is above the minimum and below the maximum + access_len.
                    #Here, we are giving relaxation of access_len + max because we have to verify cases
                    #in which we are crossing the boundary as well upto the access len (for instance, 8 Bytes in case of ld).
                    return (req_addr) >= (lo*4) and (req_addr + access_len) < (((lo + length)*4) + access_len)

                elif pmp_config == "TOR":
                    if prev_pmp_addr is None:
                        raise ValueError("The 'prev_pmp_addr' argument is required when 'TOR' is selected.")
                    else:
                        return (req_addr) >= prev_pmp_addr*4 and (req_addr + access_len) < (pmp_addr*4 + access_len)

                elif pmp_config == "NA4":
                    return (req_addr) >= pmp_addr and (req_addr + access_len) < (pmp_addr*4 + 4) + access_len

                elif pmp_config == "OFF":
                    return False
                else:
                    raise ValueError("PMP Config is not selected properly. Select b/w NA4, NAPOT, TOR only")

            globals()['get_addr'] = check_label_address
            globals()['old_csr_val'] = old_fn_csr_comb_covpt
            globals()['get_mem_val'] = get_mem_val
            globals()['get_pte'] = get_pte
            globals()['get_pte_prop'] = get_pte_prop
            globals()['pmp_rgn_chk'] = pmp_rgn_chk

            if enable :
                ucovpt = []
                covpt = []
                csr_covpt = []

                for cov_labels,value in cgf.items():
                    if cov_labels != 'datasets':
                        if 'mnemonics' in value:

                            req_node = 'mnemonics'
                            is_found = False

                            # Check if there is a base opcode
                            if 'base_op' in value:
                                # If base-op is the current instruction name, check for the p_op_cond node
                                # If conditions satisfy, the instruction is equivalent to the mnemonic
                                if instr.instr_name == value['base_op']:

                                    conds = value['p_op_cond']
                                    # Construct and evaluate conditions
                                    is_found = True
                                    if not eval(conds, globals(), instr_vars):
                                        is_found = False

                                    mnemonic = list(value[req_node].keys())
                                    mnemonic = mnemonic[0]

                                    # Update hit statistics of the mnemonic
                                    if is_found:
                                        if value[req_node][mnemonic] == 0:
                                            ucovpt.append('mnemonic : ' + mnemonic)
                                        covpt.append('mnemonic : ' + mnemonic)
                                        value[req_node][mnemonic] += 1
                                        rcgf[cov_labels][req_node][mnemonic] += 1

                            if instr.instr_name in value[req_node] or is_found:
                                # If mnemonic not detected via base-op
                                if not is_found:
                                    if value[req_node][instr.instr_name] == 0:
                                        ucovpt.append('mnemonic : ' + instr.instr_name)
                                    covpt.append('mnemonic : ' + instr.instr_name)
                                    value[req_node][instr.instr_name] += 1
                                    rcgf[cov_labels][req_node][instr.instr_name] += 1

                                if 'rs1' in value and rs1 in value['rs1']:
                                    if value['rs1'][rs1] == 0:
                                        ucovpt.append('rs1 : ' + rs1)
                                        if no_count:
                                            hit_covpts.append((cov_labels, 'rs1', rs1))
                                    covpt.append('rs1 : ' + rs1)
                                    value['rs1'][rs1] += 1

                                if 'rs2' in value and rs2 in value['rs2']:
                                    if value['rs2'][rs2] == 0:
                                        ucovpt.append('rs2 : ' + rs2)
                                        if no_count:
                                            hit_covpts.append((cov_labels, 'rs2', rs2))
                                    covpt.append('rs2 : ' + rs2)
                                    value['rs2'][rs2] += 1

                                if 'rd' in value and is_rd_valid and rd in value['rd']:
                                    if value['rd'][rd] == 0:
                                        ucovpt.append('rd : ' + rd)
                                        if no_count:
                                            hit_covpts.append((cov_labels, 'rd', rd))
                                    covpt.append('rd : ' + rd)
                                    value['rd'][rd] += 1

                                if 'rs3' in value and rs3 in value['rs3']:
                                    if value['rs3'][rs3] == 0:
                                        ucovpt.append('rs3 : ' + rs3)
                                        if no_count:
                                            hit_covpts.append((cov_labels, 'rs3', rs3))
                                    covpt.append('rs3 : ' + rs3)
                                    value['rs3'][rs3] += 1

                                if 'op_comb' in value and len(value['op_comb']) != 0 :
                                    for coverpoints in value['op_comb']:
                                        if eval(coverpoints, globals(), instr_vars):
                                            if cgf[cov_labels]['op_comb'][coverpoints] == 0:
                                                ucovpt.append(str(coverpoints))
                                                if no_count:
                                                    hit_covpts.append((cov_labels, 'op_comb', coverpoints))
                                            covpt.append(str(coverpoints))
                                            cgf[cov_labels]['op_comb'][coverpoints] += 1

                                if 'val_comb' in value and len(value['val_comb']) != 0:
                                    lcls={}
                                    if instr.is_rvp and "rs1" in value:
                                        op_width = 64 if instr.rs1_nregs == 2 else xlen
                                        simd_val_unpack(value['val_comb'], op_width, "rs1", instr_vars['rs1_val'], lcls)
                                    if instr.is_rvp and "rs2" in value:
                                        op_width = 64 if instr.rs2_nregs == 2 else xlen
                                        simd_val_unpack(value['val_comb'], op_width, "rs2", instr_vars['rs2_val'], lcls)
                                    instr_vars.update(lcls)
                                    for coverpoints in value['val_comb']:
                                        if eval(coverpoints, globals(), instr_vars):
                                            if cgf[cov_labels]['val_comb'][coverpoints] == 0:
                                                ucovpt.append(str(coverpoints))
                                                if no_count:
                                                    hit_covpts.append((cov_labels, 'val_comb', coverpoints))
                                            covpt.append(str(coverpoints))
                                            cgf[cov_labels]['val_comb'][coverpoints] += 1
                                if 'abstract_comb' in value \
                                        and len(value['abstract_comb']) != 0 :
                                    for coverpoints in value['abstract_comb']:
                                        if eval(coverpoints, globals(), instr_vars):
                                            if cgf[cov_labels]['abstract_comb'][coverpoints] == 0:
                                                ucovpt.append(str(coverpoints))
                                                if no_count:
                                                    hit_covpts.append((cov_labels, 'abstract_comb', coverpoints))
                                            covpt.append(str(coverpoints))
                                            cgf[cov_labels]['abstract_comb'][coverpoints] += 1

                                if 'csr_comb' in value and len(value['csr_comb']) != 0:
                                    if instr.csr_commit:
                                        is_csr_commit = False
                                        for commit in instr.csr_commit:
                                            if commit[0] == "CSR":
                                                is_csr_commit = True
                                                break
                                        if is_csr_commit:
                                            for coverpoints in value['csr_comb']:
                                                def get_key_from_value(dictionary, target_value):
                                                    for key, value in dictionary.items():
                                                        if value == target_value:
                                                            return key
                                                    return None
                                                #check the old_csr_value only for the register of interest
                                                pattern_csr = r'old_csr_val\("([^"]+)"\)'
                                                match = re.search(pattern_csr, coverpoints)
                                                if match:
                                                    required_csr = match.group(1)
                                                    key = get_key_from_value(csr_reg_num_to_str, required_csr)
                                                    if (instr.csr != key):
                                                        continue
                                                if eval(
                                                    coverpoints,
                                                    {
                                                        "__builtins__":None,
                                                        "old_csr_val": old_fn_csr_comb_covpt,
                                                        "write": write_fn_csr_comb_covpt,
                                                        "get_addr": check_label_address,
                                                        "get_mem_val":get_mem_val,
                                                        "get_pte":get_pte,
                                                        "get_pte_prop": get_pte_prop
                                                    },
                                                    instr_vars
                                                ):
                                                    if cgf[cov_labels]['csr_comb'][coverpoints] == 0:
                                                        ucovpt.append(str(coverpoints))
                                                        if no_count:
                                                            hit_covpts.append((cov_labels, 'csr_comb', coverpoints))
                                                    covpt.append(str(coverpoints))
                                                    csr_covpt.append(str(coverpoints))
                                                    cgf[cov_labels]['csr_comb'][coverpoints] += 1

                        elif 'opcode' not in value:
                            if 'csr_comb' in value and len(value['csr_comb']) != 0:
                                if instr.csr_commit:
                                    is_csr_commit = False
                                    for commit in instr.csr_commit:
                                        if commit[0] == "CSR":
                                            is_csr_commit = True
                                            break
                                    if is_csr_commit:
                                        for coverpoints in value['csr_comb']:
                                            if eval(
                                                coverpoints,
                                                {
                                                    "__builtins__":None,
                                                    "old_csr_val": old_fn_csr_comb_covpt,
                                                    "write": write_fn_csr_comb_covpt,
                                                    "get_addr": check_label_address,
                                                    "get_mem_val":get_mem_val,
                                                    "get_pte":get_pte,
                                                    "get_pte_prop": get_pte_prop
                                                },
                                                instr_vars
                                            ):
                                                if cgf[cov_labels]['csr_comb'][coverpoints] == 0:
                                                    ucovpt.append(str(coverpoints))
                                                    if no_count:
                                                        hit_covpts.append((cov_labels, 'csr_comb', coverpoints))
                                                covpt.append(str(coverpoints))
                                                csr_covpt.append(str(coverpoints))
                                                cgf[cov_labels]['csr_comb'][coverpoints] += 1

                hit_any_covpt = len(covpt) > 0
                hit_uniq_covpt = len(ucovpt) > 0
                hit_csr_covpt = len(csr_covpt) > 0

                if hit_csr_covpt:
                    stats.cov_pt_sig += covpt

                    csr_regs_involved_in_covpt = OrderedSet()
                    for covpt in csr_covpt:
                        for reg in csr_reg_num_to_str.values():
                            if reg in covpt:
                                csr_regs_involved_in_covpt.add(reg)

                    num_exp = 0
                    for reg in csr_regs_involved_in_covpt:
                        if reg in tracked_regs_immutable or reg in tracked_regs_mutable:
                            stat_meta = instr_stat_meta_at_addr[instr_addr_of_tracked_reg[reg]]
                            stat_meta[3] -= 1 # decrease num remaining
                            tracked_regs_immutable.discard(reg)
                            tracked_regs_mutable.discard(reg)
                            del instr_addr_of_tracked_reg[reg]

                        num_exp += 1
                        instr_addr_of_tracked_reg[reg] = instr.instr_addr
                        tracked_regs_immutable.add(reg)

                    instr_stat_meta_at_addr[instr.instr_addr] = [hit_uniq_covpt, num_exp, 0, num_exp, csr_covpt, [], [], []]
                elif hit_any_covpt:
                    stats.cov_pt_sig += covpt

                    if len(tracked_instrs) > 0:
                        for list_instrs, triggering_instr_addr in tracked_instrs:
                            stat_meta = instr_stat_meta_at_addr[triggering_instr_addr]
                            stat_meta[3] -= 1 # decrease num remaining
                        tracked_instrs = []

                    num_exp = 0 # expected number of signature updates for this instruction

                    regs_to_track_immutable, regs_to_track_mutable, instrs_to_track = instr.get_elements_to_track(xlen)

                    # update tracked elements
                    for reg in regs_to_track_immutable:
                        if reg in tracked_regs_immutable or reg in tracked_regs_mutable:
                            stat_meta = instr_stat_meta_at_addr[instr_addr_of_tracked_reg[reg]]
                            stat_meta[3] -= 1 # decrease num remaining
                            tracked_regs_immutable.discard(reg)
                            tracked_regs_mutable.discard(reg)
                            del instr_addr_of_tracked_reg[reg]

                        num_exp += 1
                        instr_addr_of_tracked_reg[reg] = instr.instr_addr
                        tracked_regs_immutable.add(reg)

                    for reg in regs_to_track_mutable:
                        if reg in tracked_regs_immutable or reg in tracked_regs_mutable:
                            stat_meta = instr_stat_meta_at_addr[instr_addr_of_tracked_reg[reg]]
                            stat_meta[3] -= 1
                            tracked_regs_immutable.discard(reg)
                            tracked_regs_mutable.discard(reg)
                            del instr_addr_of_tracked_reg[reg]

                        num_exp += 1
                        instr_addr_of_tracked_reg[reg] = instr.instr_addr
                        tracked_regs_mutable.add(reg)

                    for instrs in instrs_to_track:
                        num_exp += 1
                        tracked_instrs.append((instrs, instr.instr_addr))

                    instr_stat_meta_at_addr[instr.instr_addr] = [hit_uniq_covpt, num_exp, 0, num_exp, ucovpt if hit_uniq_covpt else covpt, [], [], []]
                else:
                    changed_regs = instr.get_changed_regs(arch_state, csr_regfile)

                    if instr.instr_name in instrs_csr_mov and csr_reg_num_to_str[instr.csr] in tracked_regs_immutable: # handle csr movs separately
                        csr_reg = csr_reg_num_to_str[instr.csr]

                        if not is_rd_valid:
                            if csr_reg in changed_regs: # csr register overwritten without propagating into signature
                                stat_meta = instr_stat_meta_at_addr[instr_addr_of_tracked_reg[csr_reg]]
                                stat_meta[3] -= 1
                                tracked_regs_immutable.remove(csr_reg)
                                del instr_addr_of_tracked_reg[csr_reg]
                        else:
                            if (rd in tracked_regs_immutable or rd in tracked_regs_mutable) and rd != 'x0':
                                stat_meta = instr_stat_meta_at_addr[instr_addr_of_tracked_reg[rd]]
                                stat_meta[3] -= 1
                                tracked_regs_immutable.discard(rd)
                                tracked_regs_mutable.discard(rd)
                                del instr_addr_of_tracked_reg[rd]

                            tracked_regs_immutable.remove(csr_reg)
                            tracked_regs_immutable.add(rd)
                            instr_addr_of_tracked_reg[rd] = instr_addr_of_tracked_reg[csr_reg]
                            del instr_addr_of_tracked_reg[csr_reg]
                    else: # check for changes in tracked registers
                        for reg in changed_regs:
                            if reg in tracked_regs_immutable:
                                stat_meta = instr_stat_meta_at_addr[instr_addr_of_tracked_reg[reg]]
                                stat_meta[3] -= 1
                                tracked_regs_immutable.remove(reg)
                                del instr_addr_of_tracked_reg[reg]

                # update code_seq
                if instr_stat_meta_at_addr:
                    if mnemonic is not None:
                        stats.code_seq.append('[' + str(hex(instr.instr_addr)) + ']:' + mnemonic)
                    else:
                        stats.code_seq.append('[' + str(hex(instr.instr_addr)) + ']:' + instr.instr_name)

                for key_instr_addr, stat_meta in instr_stat_meta_at_addr.items():
                    if mnemonic is not None:
                        stat_meta[5].append('[' + str(hex(instr.instr_addr)) + ']:' + mnemonic)
                    else:
                        stat_meta[5].append('[' + str(hex(instr.instr_addr)) + ']:' + instr.instr_name)

            # handle signature update
            if instr.is_sig_update() and sig_addrs:
                store_address = instr_vars['rs1_val'] + instr_vars['imm_val']
                store_val = '0x'+arch_state.x_rf[instr.rs2[0]]
                for start, end in sig_addrs:
                    if store_address >= start and store_address <= end:
                        logger.debug('Signature update : ' + str(hex(store_address)))
                        stats.stat5.append((store_address, store_val, ucovpt, stats.code_seq))

                        if rs2 in tracked_regs_immutable or rs2 in tracked_regs_mutable:
                            stat_meta = instr_stat_meta_at_addr[instr_addr_of_tracked_reg[rs2]]
                            stat_meta[2] += 1 # increase num observed
                            stat_meta[3] -= 1 # decrease num remaining
                            stat_meta[6].append(store_address) # add to store_addresses
                            stat_meta[7].append(store_val) # add to store_vals
                            stats.last_meta = [store_address, store_val, stat_meta[4], stat_meta[5]]
                            tracked_regs_immutable.discard(rs2)
                            tracked_regs_mutable.discard(rs2)
                            del instr_addr_of_tracked_reg[rs2]
                        elif tracked_instrs and instr.instr_name in tracked_instrs[0][0]:
                            stat_meta = instr_stat_meta_at_addr[tracked_instrs[0][1]]
                            stat_meta[2] += 1
                            stat_meta[3] -= 1
                            stat_meta[6].append(store_address)
                            stat_meta[7].append(store_val)
                            stats.last_meta = [store_address, store_val, stat_meta[4], stat_meta[5]]
                            del tracked_instrs[0]
                        else:
                            if len(stats.last_meta):
                                _log = 'Last Coverpoint : ' + str(stats.last_meta[2]) + '\n'
                                _log += 'Last Code Sequence : \n\t-' + '\n\t-'.join(stats.last_meta[3]) + '\n'
                                _log += 'Current Store : [{0}] : {1} -- Store: [{2}]:{3}\n'.format(\
                                    str(hex(instr.instr_addr)), mnemonic,
                                    str(hex(store_address)),
                                    store_val)
                                logger.error(_log)
                                stats.stat4.append(_log + '\n\n')

                        stats.code_seq = []

            # update stats
            for key_instr_addr in list(instr_stat_meta_at_addr.keys()):
                stat_meta = instr_stat_meta_at_addr[key_instr_addr]
                if stat_meta[3] == 0: # num_remaining == 0
                    if stat_meta[0]: # is_ucovpt
                        if stat_meta[2] == stat_meta[1]: # num_observed == num_expected
                            # update STAT1 with (store_addresses, store_vals, covpt, code_seq)
                            stats.stat1.append((stat_meta[6], stat_meta[7], stat_meta[4], stat_meta[5]))
                        elif stat_meta[2] < stat_meta[1]: # num_observed < num_expected
                            # update STAT3 with code sequence
                            stats.stat3.append('\n'.join(stat_meta[5]))
                    else: # not is_ucovpt
                        if stat_meta[2] > 0: # num_observed > 0
                            # update STAT2
                            _log = 'Op without unique coverpoint updates Signature\n'

                            _log += ' -- Code Sequence:\n'
                            for op in stat_meta[5]:
                                _log += '      ' + op + '\n'

                            _log += ' -- Signature Addresses:\n'
                            for store_address, store_val in zip(stat_meta[6], stat_meta[7]):
                                _log += '      Address: {0} Data: {1}\n'.format(
                                        str(hex(store_address)), store_val)

                            _log += ' -- Redundant Coverpoints hit by the op\n'
                            for c in stat_meta[4]:
                                _log += '      - ' + str(c) + '\n'

                            logger.warn(_log)
                            stats.stat2.append(_log + '\n\n')

                    del instr_stat_meta_at_addr[key_instr_addr]

            # Remove hit coverpoints if no_count is set
            if no_count:
                for covpt in hit_covpts:
                    rcgf[covpt[0]][covpt[1]][covpt[2]] = 1
                    del cgf[covpt[0]][covpt[1]][covpt[2]]
                else:
                    hit_covpts = []
    else:
        # update stats one last time for the remaining elements
        for key_instr_addr in list(instr_stat_meta_at_addr.keys()):
            stat_meta = instr_stat_meta_at_addr[key_instr_addr]
            if stat_meta[0]: # is_ucovpt
                if stat_meta[2] == stat_meta[1]: # num_observed == num_expected
                    # update STAT1 with (store_addresses, store_vals, covpt, code_seq)
                    stats.stat1.append((stat_meta[6], stat_meta[7], stat_meta[4], stat_meta[5]))
                elif stat_meta[2] < stat_meta[1]: # num_observed < num_expected
                    # update STAT3 with code sequence
                    stats.stat3.append('\n'.join(stat_meta[5]))
            else: # not is_ucovpt
                if stat_meta[2] > 0: # num_observed > 0
                    # update STAT2
                    _log = 'Op without unique coverpoint updates Signature\n'

                    _log += ' -- Code Sequence:\n'
                    for op in stat_meta[5]:
                        _log += '      ' + op + '\n'

                    _log += ' -- Signature Addresses:\n'
                    for store_address, store_val in zip(stat_meta[6], stat_meta[7]):
                        _log += '      Address: {0} Data: {1}\n'.format(
                                str(hex(store_address)), store_val)

                    _log += ' -- Redundant Coverpoints hit by the op\n'
                    for c in stat_meta[4]:
                        _log += '      - ' + str(c) + '\n'

                    logger.warn(_log)
                    stats.stat2.append(_log + '\n\n')

            del instr_stat_meta_at_addr[key_instr_addr]

        # if no_count option is set, return rcgf
        # else return cgf
        if not no_count:
            cgf_queue.put_nowait(cgf)
        else:
            cgf_queue.put_nowait(rcgf)

        # Pass statistics back to main process
        stats_queue.put_nowait(stats)
        cgf_queue.close()
        stats_queue.close()

def compute(trace_file, test_name, cgf, parser_name, decoder_name, detailed, xlen, flen, addr_pairs
        , dump, cov_labels, sig_addrs, window_size, inxFlg, elf, no_count=False, procs=1):
    '''Compute the Coverage'''

    global arch_state
    global csr_regfile
    global iptw_dict
    global mem_vals
    global stats
    global cross_cover_queue
    global result_count

    temp = cgf.copy()
    if cov_labels:
        for groups in cgf:
            if groups not in cov_labels:
                del temp[groups]
        cgf = temp

    # If cgf does not have the covergroup pertaining to the cover-label, throw error
    # and exit
    if not cgf:
        logger.err('Covergroup(s) for ' + str(cov_labels) + ' not found')
        sys.exit(1)

    if dump is not None:
        dump_f = open(dump, 'w')
        dump_f.write(utils.dump_yaml(cgf, indent=5, block_seq_indent=3))
        dump_f.close()
        sys.exit(0)

    arch_state = archState(xlen,flen,inxFlg)
    csr_regfile = csr_registers(xlen)
    iptw_dict = {}
    mem_vals = {}
    stats = statistics(xlen, flen)
    cross_cover_queue = []
    result_count = 0

    ## Get coverpoints from cgf
    obj_dict = {} ## (label,coverpoint): object
    for cov_labels,value in cgf.items():
        if cov_labels != 'datasets':
            if 'cross_comb' in value and len(value['cross_comb'])!=0:
                for coverpt in value['cross_comb'].keys():
                    if(isinstance(coverpt,str)):
                        new_obj = cross(cov_labels,coverpt,xlen,flen,addr_pairs,sig_addrs,window_size,inxFlg)
                        obj_dict[(cov_labels,coverpt)] = new_obj


    parser_pm = pluggy.PluginManager("parser")
    parser_pm.add_hookspecs(ParserSpec)
    try:
        parserfile = importlib.import_module(parser_name)
    except ImportError as e:
        logger.error('Error while importing Parser!')
        logger.error(e)
        raise SystemExit
    parserclass = getattr(parserfile, parser_name)
    parser_pm.register(parserclass())
    parser = parser_pm.hook
    parser.setup(trace=trace_file,arch=(xlen,flen))

    decoder_pm = pluggy.PluginManager("decoder")
    decoder_pm.add_hookspecs(DecoderSpec)
    try:
        instructionObjectfile = importlib.import_module(decoder_name)
    except ImportError as e:
        logger.error('Error while importing Decoder!')
        logger.error(e)
        raise SystemExit
    decoderclass = getattr(instructionObjectfile, "disassembler")
    decoder_pm.register(decoderclass())
    decoder = decoder_pm.hook
    decoder.setup(inxFlag=inxFlg, arch="rv"+str(xlen))

    iterator = iter(parser.__iter__()[0])

    # If number of processes to be spawned is more than that available,
    # allot number of processes to be equal to one less than maximum
    available_cores = mp.cpu_count()
    if procs > available_cores:
        procs = available_cores - 1

    # Partiton cgf to chunks
    chunk_len = math.ceil(len(cgf) / procs)
    chunks = [{k:cgf[k] for k in islice(iter(cgf), chunk_len)} for i in range(0, len(cgf), chunk_len)]

    queue_list = []                     # List of queues to pass instructions to daughter processes
    process_list = []                   # List of processes to be spawned
    event_list = []                     # List of Event objects to signal exhaustion of instruction list to daughter processes
    cgf_queue_list = []                 # List of queues to retrieve the updated CGF dictionary from each processes
    stats_queue_list = []               # List of queues to retrieve coverpoint hit statistics from each processes

    # For each chunk of cgf dictionary, spawn a new queue thread to pass instrObj,
    # to retrieve updated cgf, to retrieve statistics. An Event object is appended for
    # each processes spawned. A Process object is appended against every cgf chunk and initialized.
    for i in range(len(chunks)):
        queue_list.append(mp.Queue())
        cgf_queue_list.append(mp.Queue())
        stats_queue_list.append(mp.Queue())
        event_list.append(mp.Event())
        process_list.append(
                        mp.Process(target=compute_per_line,
                                args=(queue_list[i], event_list[i], cgf_queue_list[i], stats_queue_list[i],
                                    chunks[i], xlen, flen, addr_pairs, sig_addrs,
                                    stats,
                                    arch_state,
                                    csr_regfile,
                                    iptw_dict,
                                    mem_vals,
                                    no_count,
                                    elf
                                    )
                            )
                        )

    #Start each processes
    for each in process_list:
        each.start()

    # This loop facilitates parsing, disassembly and generation of instruction objects
    for instrObj_temp in iterator:
        instr = instrObj_temp.instr
        if instr is None:
            continue
        instrObj = (decoder.decode(instrObj_temp = instrObj_temp))[0]

        # Pass instrObjs to queues pertaining to each processes
        for each in queue_list:
            each.put_nowait(instrObj)

        logger.debug(instrObj)
        for (label,coverpt) in obj_dict.keys():
            obj_dict[(label,coverpt)].process(instrObj)



    # Close all instruction queues
    for each in queue_list:
        each.close()
        each.join_thread()

    # Signal each processes that instruction list is over
    for each in event_list:
        each.set()

    # Get the renewed cgfs
    cgf_list = []
    for each in cgf_queue_list:
        cgf_list.append(each.get())
        each.close()
        each.join_thread()

    # Get each stats
    stats_list = []
    for each in stats_queue_list:
        stats_list.append(each.get())
        each.close()
        each.join_thread()

    # Join all processes
    for each in process_list:
        each.join()

    # Merge stats
    for each in stats_list:
        stats = stats + each

    # Merge cgfs
    rcgf = dict()
    for d in cgf_list:
        for key, val in d.items():
            rcgf[key] = val

    ## Check for cross coverage for end instructions
    ## All metric is stored in objects of obj_dict
    for label,coverpt in obj_dict.keys():
        obj_dict[(label,coverpt)].finish_up()

    for label,coverpt in obj_dict.keys():
        stats += obj_dict[(label,coverpt)].get_stats()
        metric = obj_dict[(label,coverpt)].get_metric()
        if(metric!=0):
            rcgf[label]['cross_comb'][coverpt] = metric

    rpt_str = gen_report(rcgf, detailed)
    logger.info('Writing out updated cgf : ' + test_name + '.cgf')
    dump_file = open(test_name+'.cgf', 'w')
    dump_file.write(utils.dump_yaml(rcgf, indent=5, block_seq_indent=3))
    dump_file.close()

    if sig_addrs:
        logger.info('Creating Data Propagation Report : ' + test_name + '.md')
        writer = pytablewriter.MarkdownTableWriter()
        writer.headers = ["s.no","signature", "coverpoints", "code"]
        for cov_labels, value in cgf.items():
            if cov_labels != 'datasets':
              #  rpt_str += cov_labels + ':\n'
                total_uncovered = 0
                total_categories = 0
                for categories in value:
                    if categories not in ['cond','config','ignore', 'total_coverage', 'coverage', 'base_op', 'p_op_cond']:
                        for coverpoints, coverage in value[categories].items():
                            if coverage == 0:
                                total_uncovered += 1
                        total_categories += len(value[categories])

        addr_pairs_hex = []
        for x in addr_pairs:
            _x = (hex(x[0]), hex(x[1]))
            addr_pairs_hex.append(_x)
        sig_addrs_hex = []
        for x in sig_addrs:
            if xlen == 64:
                _x = (hex(x[0]), hex(x[1]), str(int((x[1]-x[0])/8)) + ' dwords')
            else:
                _x = (hex(x[0]), hex(x[1]), str(int((x[1]-x[0])/4)) + ' words')
            sig_addrs_hex.append(_x)

        cov_set = OrderedSet()
        count = 1
        for addrs,vals,cover,code in stats.stat1:
            sig = ''
            for addr, val in zip(addrs, vals):
                sig += '[{0}]<br>{1}'.format(str(hex(addr)), str(val)) + '<br>\n'
            cov = ''
            for c in cover:
                cov += '- ' + str(c) + '<br>\n'
                cov_set.add(c)
            cod = ''
            for i in code:
                cod += str(i) + '<br>\n'

            row = [count, sig, cov, cod]
            writer.value_matrix.append(row)
            count += 1
        f =open(test_name+'.md','w')
        if xlen == 64:
            sig_count = 2*len(stats.stat5)
        else:
            sig_count = len(stats.stat5)

        stat2_log = ''
        for _l in stats.stat2:
            stat2_log += _l + '\n\n'

        stat4_log = ''
        for _l in stats.stat4:
            stat4_log += _l + '\n\n'

        stat3_log = ''
        for _l in stats.stat3:
            stat3_log += _l + '\n\n'

        stat5_log = ''
        sig_set = OrderedSet()
        overwrites = 0
        for addr, val, cover, code in stats.stat5:
            if addr in sig_set:
                stat5_log += ('[{0}]<br>{1}'.format(str(hex(addr)), str(val)))
                stat5_log += code + '\n\n'
                overwrites += 1
                sig_set.add(addr)
                logger.error('Found overwrite in Signature at Addr : ' +
                        str(addr))

        f.write(dpr_template.format(str(xlen),
            str(addr_pairs_hex),
            str(sig_addrs_hex),
            str(cov_labels),
            test_name,
            total_categories,
            len(stats.stat5),
            len(set(stats.cov_pt_sig)),
            len(stats.stat1),
            len(stats.stat2),
            len(stats.stat3),
            len(stats.stat4),
            len(stat5_log),
            stat2_log,
            stat3_log,
            stat4_log,
            stat5_log))
        f.write(writer.dumps())
        f.close()

    return rpt_str

