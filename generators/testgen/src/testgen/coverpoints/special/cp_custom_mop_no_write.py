##################################
# cp_custom_mop_no_write.py
#
# David_Harris@hmc.edu 10 September 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""cp_custom_mop_no_write coverpoint generator."""

from testgen.asm.helpers import load_int_reg, write_sigupd
from testgen.coverpoints.registry import add_coverpoint_generator
from testgen.data.random import random_int
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk

# C.MOP.n occupies the reserved encoding of c.lui x{n}, 0, so x{n} is the register a
# mis-decoding implementation would write.
MOP_REGS = {f"c.mop.{n}": n for n in range(1, 16, 2)}


@add_coverpoint_generator("cp_custom_mop_no_write")
def make_custom_mop_no_write(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    """Seed registers, execute c.mop.n, and check that no register was written."""
    if instr_name not in MOP_REGS:
        raise ValueError(f"cp_custom_mop_no_write generator only supports c.mop.n instructions, got {instr_name}")
    mop_reg = MOP_REGS[instr_name]

    tc = test_data.begin_test_chunk()

    asm_setup = test_data.int_regs.consume_registers([mop_reg])
    other_regs = test_data.int_regs.get_registers(2, exclude_regs=[0])
    regs = [mop_reg, *other_regs]

    if asm_setup:
        tc.code.append(asm_setup)
    tc.code.append(
        f"# cp_custom_mop_no_write: {instr_name} must not write x{mop_reg} "
        f"(the c.lui x{mop_reg}, 0 encoding it reuses) or any other register"
    )
    for reg in regs:
        tc.code.append(load_int_reg(f"x{reg}", reg, random_int(bits=test_data.xlen), test_data))
    tc.code.append(f"{instr_name} # must not write any register")

    for reg in regs:
        tc.code.extend(
            [
                test_data.add_testcase(f"x{reg}", coverpoint),
                write_sigupd(reg, test_data),
                "",
            ]
        )

    test_data.int_regs.return_registers(regs)

    return [test_data.end_test_chunk()]
