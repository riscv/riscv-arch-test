# See LICENSE.incore for details
import re
import functools

from riscv_ctg.log import logger
from riscv_ctg.constants import *

import tokenize as tkn
from io import BytesIO

OPS = ['not', 'and', 'or']
OP_PRIORITY = {
    'not': -1,
    'and': -2,
    'or' : -3,
}

CSR_REGS = ['mvendorid', 'marchid', 'mimpid', 'mhartid', 'mstatus', 'misa', 'medeleg', 'mideleg', 'mie', 'mtvec', 'mcounteren', 'mscratch', 'mepc', 'mcause', 'mtval', 'mip', 'pmpcfg0', 'pmpcfg1', 'pmpcfg2', 'pmpcfg3', 'mcycle', 'minstret', 'mcycleh', 'minstreth', 'mcountinhibit', 'tselect', 'tdata1', 'tdata2', 'tdata3', 'dcsr', 'dpc', 'dscratch0', 'dscratch1', 'sstatus', 'sedeleg', 'sideleg', 'sie', 'stvec', 'scounteren', 'sscratch', 'sepc', 'scause', 'stval', 'sip', 'satp', 'vxsat', 'fflags', 'frm', 'fcsr', 'CSR_SRMCFG']
csr_regs_capture_group = f'({"|".join(CSR_REGS)})'
csr_regs_with_modifiers_capture_group = r'(write|old) *\( *"' + csr_regs_capture_group + r'" *\)'

csr_comb_covpt_regex_strings = [
    csr_regs_capture_group + r' *& *([^ ].*)== *([^ ].*)', # regular
    r'\( *' + csr_regs_capture_group + r' *(>>|<<) *([^ ].*)\) *& *([^ ].*)== *([^ ].*)', # with bitshifts only
    csr_regs_with_modifiers_capture_group + r' *& *([^ ].*)== *([^ ].*)', # with modifiers only
    r'\( *' + csr_regs_with_modifiers_capture_group + r' *(>>|<<) *([^ ].*)\) *& *([^ ].*)== *([^ ].*)', # with bitshifts and modifiers
]

csr_comb_covpt_regexes = [re.compile(regex_string) for regex_string in csr_comb_covpt_regex_strings]

def tokenize(s):
    result = []
    g = tkn.tokenize(BytesIO(s.encode('utf-8')).readline)
    for tok_num, tok_val, _, _, _ in g:
        if tok_num in [tkn.ENCODING, tkn.NEWLINE, tkn.ENDMARKER]:
            continue
        result.append((tok_num, tok_val))
    return result

def untokenize(tokens):
    return tkn.untokenize(tokens)

# a dummy class acting as an interface for boolean expressions
class BooleanExpression:
    def SAT(self):
        # returns the complete list of solutions for this expression's satisfiability
        # a single solution is a tuple of two lists:
        #  - the literals in the first list must evaluate to true
        #  - the literals in the second list must evaluate to false
        raise Exception("not implemented")

    def __str__(self):
        raise Exception("not implemented")

class NotExpression(BooleanExpression):
    def __init__(self, operand):
        self.operand = operand

    def SAT(self):
        return [(operand_f, operand_t) for operand_t, operand_f in self.operand.SAT()]

    def __str__(self):
        return f'not ({str(self.operand)})'

class AndExpression(BooleanExpression):
    def __init__(self, lhs, rhs):
        self.lhs = lhs
        self.rhs = rhs

    def SAT(self):
        return [(lhs_t + rhs_t, lhs_f + rhs_f) for lhs_t, lhs_f in self.lhs.SAT() for rhs_t, rhs_f in self.rhs.SAT()]

    def __str__(self):
        return f'({str(self.lhs)}) and ({str(self.rhs)})'

class OrExpression(BooleanExpression):
    def __init__(self, lhs, rhs):
        self.lhs = lhs
        self.rhs = rhs

    def SAT(self):
        lhs_SAT = self.lhs.SAT()
        rhs_SAT = self.rhs.SAT()

        sols = []
        for lhs_t, lhs_f in lhs_SAT:
            for rhs_t, rhs_f in rhs_SAT:
                sols.extend([
                    (lhs_t + rhs_f, lhs_f + rhs_t),
                    (lhs_f + rhs_t, lhs_t + rhs_f),
                    (lhs_t + rhs_t, lhs_f + rhs_f),
                ])

        return sols

    def __str__(self):
        return f'({str(self.lhs)}) or ({str(self.rhs)})'

class LiteralExpression(BooleanExpression):
    def __init__(self, val):
        self.val = val

    def SAT(self):
        return [([self.val], [])]

    def __str__(self):
        return str(self.val)

# This function parses coverpoints for the CSR-combination node
# The coverpoints are assumed of the form: multiple condition clauses combined with and's and or's
# A coverpoint condition clause is assumed of the form: 'csr_reg & mask == val' or '(csr_reg >> shift) & mask == val'
def parse_csr_covpt(covpt):
    toks = tokenize(covpt)

    bracket_depth = 0
    clause_depths = []
    for tok_num, tok_val in toks:
        if tok_val == '(':
            bracket_depth += 1
        elif tok_val == ')':
            bracket_depth -= 1
        elif tok_val == '==':
            clause_depths.append(bracket_depth)

    bracket_depth = 0
    operator_stack = []
    clause_stack = []
    clause_index = 0
    current_clause = []
    current_clause_depth = clause_depths[clause_index]
    for tok_num, tok_val in toks:
        if tok_val == '(':
            bracket_depth += 1

            if bracket_depth > current_clause_depth:
                current_clause.append((tok_num, tok_val))
            else:
                operator_stack.append('(')
        elif tok_val == ')':
            bracket_depth -= 1

            if current_clause:
                if bracket_depth < current_clause_depth:
                    clause_stack.append(LiteralExpression(untokenize(current_clause)))
                    while operator_stack[-1] != '(':
                        op = operator_stack.pop()
                        if op == 'not':
                            operand = clause_stack.pop()
                            clause_stack.append(NotExpression(operand))
                        else:
                            rhs = clause_stack.pop()
                            lhs = clause_stack.pop()
                            clause_stack.append(AndExpression(lhs, rhs) if op == 'and' else OrExpression(lhs, rhs))
                    operator_stack.pop()

                    current_clause = []
                    clause_index += 1
                    if (clause_index >= len(clause_depths)):
                        break
                    current_clause_depth = clause_depths[clause_index]
                else:
                    current_clause.append((tok_num, tok_val))
            else:
                while operator_stack[-1] != '(':
                    op = operator_stack.pop()
                    if op == 'not':
                        operand = clause_stack.pop()
                        clause_stack.append(NotExpression(operand))
                    else:
                        rhs = clause_stack.pop()
                        lhs = clause_stack.pop()
                        clause_stack.append(AndExpression(lhs, rhs) if op == 'and' else OrExpression(lhs, rhs))
                operator_stack.pop()
        elif tok_val in OPS:
            if current_clause:
                clause_stack.append(LiteralExpression(untokenize(current_clause)))
                current_clause = []
                clause_index += 1
                current_clause_depth = clause_depths[clause_index]

            # prioritize not over and over or
            while len(operator_stack) > 0 and operator_stack[-1] in OPS and OP_PRIORITY[operator_stack[-1]] > OP_PRIORITY[tok_val]:
                op = operator_stack.pop()
                if op == 'not':
                    operand = clause_stack.pop()
                    clause_stack.append(NotExpression(operand))
                else:
                    rhs = clause_stack.pop()
                    lhs = clause_stack.pop()
                    clause_stack.append(AndExpression(lhs, rhs) if op == 'and' else OrExpression(lhs, rhs))

            operator_stack.append(tok_val)
        else:
            current_clause.append((tok_num, tok_val))

    if current_clause:
        clause_stack.append(LiteralExpression(untokenize(current_clause)))

    while len(operator_stack) > 0:
        op = operator_stack.pop()
        if op == 'not':
            operand = clause_stack.pop()
            clause_stack.append(NotExpression(operand))
        else:
            rhs = clause_stack.pop()
            lhs = clause_stack.pop()
            clause_stack.append(AndExpression(lhs, rhs) if op == 'and' else OrExpression(lhs, rhs))

    bool_expr = clause_stack.pop()
    return bool_expr

# This function extracts the csr register, the field mask, the field value and the csr register modifier (if present) from the coverpoint clause
# The coverpoint clause is assumed of the format: 'csr_reg & mask == val' or '(csr_reg >> shift) & mask == val'
# Modifiers `old()` and `write()` are also allowed on the `csr_reg`s. Example: `old("csr_reg") & mask == val`
# csr_reg must be a valid csr register; mask and val are allowed to be valid python expressions
def get_csr_mask_val_modifier(clause, instr_dict={}):
    clause = clause.strip()
    for i, regex in enumerate(csr_comb_covpt_regexes):
        regex_match = regex.match(clause)
        if regex_match is not None:
            if i == 0: # regular covpt
                csr_reg, mask_expr, val_expr = regex_match.groups()
                mask = eval(mask_expr, {}, instr_dict)
                val = eval(val_expr, {}, instr_dict)
                return csr_reg, mask, val, None
            elif i == 1: # with bitshifts only
                csr_reg, shift_op, shift_expr, mask_expr, val_expr = regex_match.groups()
                shift = eval(shift_expr, {}, instr_dict)
                mask = eval(mask_expr, {}, instr_dict)
                val = eval(val_expr, {}, instr_dict)
                if shift_op == '>>':
                    mask = mask << shift
                    val = val << shift
                else:
                    mask = mask >> shift
                    val = val >> shift
                return csr_reg, mask, val, None
            elif i == 2: # with modifiers only
                mod, csr_reg, mask_expr, val_expr = regex_match.groups()
                mask = eval(mask_expr, {}, instr_dict)
                val = eval(val_expr, {}, instr_dict)
                return csr_reg, mask, val, mod
            elif i == 3: # with both modifiers and bitshifts
                mod, csr_reg, shift_op, shift_expr, mask_expr, val_expr = regex_match.groups()
                shift = eval(shift_expr, {}, instr_dict)
                mask = eval(mask_expr, {}, instr_dict)
                val = eval(val_expr, {}, instr_dict)
                if shift_op == '>>':
                    mask = mask << shift
                    val = val << shift
                else:
                    mask = mask >> shift
                    val = val >> shift
                return csr_reg, mask, val, mod
    return None, None, None, None

class GeneratorCSRComb():
    '''
    A class to generate RISC-V assembly tests for CSR-combination coverpoints.
    '''

    def __init__(self, base_isa, xlen, randomize):
        self.base_isa = base_isa + "_Zicsr"
        self.xlen = xlen
        self.randomize = randomize

    def csr_comb(self, cgf_node):
        logger.debug('Generating tests for csr_comb')
        if 'csr_comb' in cgf_node:
            csr_comb = OrderedSet(cgf_node['csr_comb'])
        else:
            return

        temp_regs = ['x30', 'x31']
        dest_reg = 'x29'

        instr_dict = []
        offset = 0

        for covpt in csr_comb:
            try:
                bool_expr = parse_csr_covpt(covpt)
                sols = bool_expr.SAT()
            except:
                logger.error(f'Invalid csr_comb coverpoint: {covpt}')
                continue

            for sol, _ in sols:
                reg_mask_val_mod_dict = {} # maps a csr_reg to the 6-tuple [mask, val, write_mask, write_val, old_mask, old_val]
                reg_with_mod = None
                for clause in sol:
                    csr_reg, mask, val, mod = get_csr_mask_val_modifier(clause, {'xlen': self.xlen})

                    if csr_reg is None:
                        logger.error(f'Skipping invalid csr_comb coverpoint condition clause: {clause}')
                        continue
                    if mod is not None:
                        if reg_with_mod is None: reg_with_mod = csr_reg
                        elif reg_with_mod != csr_reg:
                            logger.error(f'Skipping invalid csr_comb solution with modifiers on more than one registers for the coverpoint: {covpt}')
                            continue

                    if not csr_reg in reg_mask_val_mod_dict:
                        if mod == 'old':
                            reg_mask_val_mod_dict[csr_reg] = [0, 0, 0, 0, mask, val]
                        elif mod == 'write':
                            reg_mask_val_mod_dict[csr_reg] = [0, 0, mask, val, 0, 0]
                        else:
                            reg_mask_val_mod_dict[csr_reg] = [mask, val, 0, 0, 0, 0]
                    else:
                        if mod == 'old':
                            reg_mask_val_mod_dict[csr_reg][4] |= mask
                            reg_mask_val_mod_dict[csr_reg][5] |= val
                        elif mod == 'write':
                            reg_mask_val_mod_dict[csr_reg][2] |= mask
                            reg_mask_val_mod_dict[csr_reg][3] |= val
                        else:
                            reg_mask_val_mod_dict[csr_reg][0] |= mask
                            reg_mask_val_mod_dict[csr_reg][1] |= val

                reg_mask_val_arr = list(reg_mask_val_mod_dict.items())
                reg_mask_val_arr.sort(key=functools.cmp_to_key(lambda x, y: 1 if x[0] == reg_with_mod else -1)) # put the register with modifier at the end

                instr_dict_csr_writes = []
                instr_dict_csr_restores = []
                uniq_csr_regs = []
                restore_reg = 1
                for csr_reg, mask_val in reg_mask_val_arr:
                    mask, val, write_mask, write_val, old_mask, old_val = mask_val
                    if old_mask != 0:
                        instr_dict_csr_writes.append({
                            'csr_reg': csr_reg, 'mask': hex(old_mask), 'val': hex(old_val), 'restore_reg':  f'x{restore_reg}',
                            'temp_reg1': temp_regs[0], 'temp_reg2': temp_regs[1]
                        })
                        instr_dict_csr_restores.append({
                            'csr_reg': csr_reg, 'restore_reg': f'x{restore_reg}'
                        })
                        restore_reg += 1

                    if write_mask != 0:
                        instr_dict_csr_writes.append({
                            'csr_reg': csr_reg, 'mask': hex(write_mask), 'val': hex(write_val), 'restore_reg':  f'x{restore_reg}',
                            'temp_reg1': temp_regs[0], 'temp_reg2': temp_regs[1]
                        })
                        instr_dict_csr_restores.append({
                            'csr_reg': csr_reg, 'restore_reg': f'x{restore_reg}'
                        })
                        restore_reg += 1
                    elif mask != 0:
                        instr_dict_csr_writes.append({
                            'csr_reg': csr_reg, 'mask': hex(mask), 'val': hex(val), 'restore_reg':  f'x{restore_reg}',
                            'temp_reg1': temp_regs[0], 'temp_reg2': temp_regs[1]
                        })
                        instr_dict_csr_restores.append({
                            'csr_reg': csr_reg, 'restore_reg': f'x{restore_reg}'
                        })
                        restore_reg += 1

                    if csr_reg not in uniq_csr_regs:
                        uniq_csr_regs.append(csr_reg)

                instr_dict_csr_restores.reverse()

                instr_dict_csr_read_and_sig_upds = []
                for csr_reg in uniq_csr_regs:
                    instr_dict_csr_read_and_sig_upds.append({
                        'csr_reg': csr_reg, 'dest_reg': dest_reg, 'offset': offset
                    })
                    offset += (self.xlen >> 3)

                instr_dict.append((instr_dict_csr_writes, instr_dict_csr_read_and_sig_upds, instr_dict_csr_restores))

        return instr_dict

    def write_test(self, fprefix, cgf_node, usage_str, cov_label, instr_dict):
        base_reg = 'x28'

        code = [""]
        data = [".align 4","rvtest_data:",".word 0xbabecafe", \
                ".word 0xabecafeb", ".word 0xbecafeba", ".word 0xecafebab"]
        sig = [""]

        sig_label = f"signature_{base_reg}_0"
        sig.append(signode_template.safe_substitute(label = sig_label, n = len(instr_dict), sz = '(XLEN/32)'))
        code.append(f"RVTEST_SIGBASE({base_reg}, {sig_label})\n")

        for i, instr in enumerate(instr_dict):
            csr_writes, csr_read_sig_upds, csr_restores = instr

            for j, csr_write in enumerate(csr_writes):
                code.extend([
                    f"\ninst_{i}_csr_write_{j}:",
                    csr_reg_write_to_field_template.safe_substitute({
                        'base_reg': base_reg, **csr_write
                    })
                ])

            for j, csr_read_sig_upd in enumerate(csr_read_sig_upds):
                code.extend([
                    f"\ninst_{i}_csr_read_sig_upd_{j}:",
                    csr_reg_read_and_sig_upd_template.safe_substitute({
                        'base_reg': base_reg, **csr_read_sig_upd
                    })
                ])

            for j, csr_restore in enumerate(csr_restores):
                code.extend([
                    f"\ninst_{i}_csr_restore_{j}:",
                    csr_reg_restore_template.safe_substitute({
                        'base_reg': base_reg, **csr_restore
                    })
                ])

        case_str = ''.join([case_template.safe_substitute(xlen = self.xlen, num = i, cov_label = cov_label) for i, cond in enumerate(cgf_node.get('config', []))])
        test_str = part_template.safe_substitute(case_str = case_str, code = '\n'.join(code))
        fname = fprefix + '_csr-comb.S'
        logger.debug("Writing Test to %s", str(fname))
        with open(fname, 'w') as fp:
            fp.write(usage_str + csr_comb_test_template.safe_substitute(
                isa = self.base_isa.upper(), # how to get the extensions?
                test = test_str,
                data = '\n'.join(data),
                sig = '\n'.join(sig),
                label = cov_label
            ))
