##################################
# sc_type.py
#
# jcarlin@hmc.edu Dec 2025
# SPDX-License-Identifier: Apache-2.0
##################################

from testgen.asm.helpers import load_int_reg, write_sigupd
from testgen.data.params import InstructionParams
from testgen.data.state import TestData
from testgen.formatters.registry import InstructionTypeConfig, add_instruction_formatter

sc_config = InstructionTypeConfig(
    required_params={"rd", "rs1", "rs2", "rs2val", "temp_reg", "temp_val"}, imm_bits=12, imm_signed=True
)

SC_RETRY_LIMIT = 100


def sc_canary(rs1: int, rs2: int, temp_reg: int, offset: int = 0) -> list[str]:
    """Fill the XLEN word at offset(rs1) with ~rs2.

    Every bit an SC of rs2 writes then changes, so a dropped store or one to another address fails
    the readback. The complement is taken at run time because rs2 may hold an address.
    """
    return [
        f"xori x{temp_reg}, x{rs2}, -1 # canary = ~rs2, so the SC changes every bit it writes",
        f"SREG x{temp_reg}, {offset}(x{rs1}) # fill SC target with canary",
    ]


def sc_retry_loop(
    sc_insn: str,
    lr_insn: str,
    test_data: TestData,
    *,
    rd: int,
    rs1: int,
    rs2: int,
    rs2val: int,
    temp_reg: int,
) -> tuple[list[str], list[str], list[str]]:
    """Return (setup, test, check) for an SC that must succeed, in a bounded LR/SC retry loop.

    An SC may fail spuriously, so the SC is retried up to SC_RETRY_LIMIT times.
    - rd = rs1 or rs2: the failing SC overwrites that operand with the failure code, so a copy of rd's
      initial value is made before the loop and restored at the top of every iteration. The loop stays
      within the constrained LR/SC form (at most 16 base-I instructions).
    - rd = x0: the SC reports no status, so success is detected by the canary having changed. That puts
      a load in the loop, which leaves the constrained form but is still bounded.
    The testcase label goes between setup (which ends with the LR) and test (the SC).
    """
    label = test_data.current_testcase_label
    retry_label = f"{label}_retry"
    success_label = f"{label}_success"
    extra_reg = None
    setup = [
        load_int_reg("rs2", rs2, rs2val, test_data),
        f"LA(x{rs1}, scratch) # rs1 = base address",
        *sc_canary(rs1, rs2, temp_reg),
    ]
    loop_head = []
    if rd != 0 and rd in (rs1, rs2):
        extra_reg = test_data.int_regs.get_register(exclude_regs=[0, rd, rs1, rs2, temp_reg])
        setup.append(f"addi x{extra_reg}, x{rd}, 0 # save rd's initial value; a failing SC overwrites it")
        loop_head.append(f"addi x{rd}, x{extra_reg}, 0 # restore the operand in rd before each attempt")
    setup.extend(
        [
            f"LI(x{temp_reg}, {SC_RETRY_LIMIT}) # retry counter for LR/SC loop",
            f"{retry_label}:",
            *loop_head,
            f"{lr_insn} x0, (x{rs1}) # establish reservation",
        ]
    )
    test = [f"{sc_insn} x{rd}, x{rs2}, (x{rs1}) # perform operation"]
    if rd == 0:
        extra_reg = test_data.int_regs.get_register(exclude_regs=[0, rs1, rs2, temp_reg])
        check = [
            f"LREG x{extra_reg}, 0(x{rs1}) # rd = x0 gives no status: check whether the canary changed",
            f"xori x{extra_reg}, x{extra_reg}, -1 # ~memory = rs2 only if memory still holds the canary",
            f"bne x{extra_reg}, x{rs2}, {success_label} # SC wrote memory, skip retry",
        ]
    else:
        check = [f"beqz x{rd}, {success_label} # SC succeeded, skip retry"]
    check.extend(
        [
            f"addi x{temp_reg}, x{temp_reg}, -1 # decrement retry count",
            f"bnez x{temp_reg}, {retry_label} # retry LR/SC if not exhausted",
            f"{success_label}:",
            write_sigupd(rd, test_data),
            f"LA(x{rs1}, scratch) # reload base address",
            f"LREG x{temp_reg}, 0(x{rs1}) # load stored value",
            write_sigupd(temp_reg, test_data),
        ]
    )
    if extra_reg is not None:
        test_data.int_regs.return_register(extra_reg)
    return (setup, test, check)


@add_instruction_formatter("SC", sc_config)
def format_sc_type(
    instr_name: str, test_data: TestData, params: InstructionParams
) -> tuple[list[str], list[str], list[str]]:
    """Format SC-type instruction."""
    assert params.rs1 is not None and params.rd is not None, "rs1 and rd must be provided for SC-type instructions"
    assert params.rs2 is not None and params.rs2val is not None, (
        "rs2 and rs2val must be provided for SC-type instructions"
    )
    assert params.temp_reg is not None, "temp_reg must be provided for SC-type instructions"

    # Ensure rs1 is not x0 (base address)
    if params.rs1 == 0:
        test_data.int_regs.return_register(params.rs1)
        params.rs1 = test_data.int_regs.get_register(exclude_regs=[0])

    lr_insn = "lr.w" if instr_name.endswith(".w") else "lr.d"
    return sc_retry_loop(
        instr_name,
        lr_insn,
        test_data,
        rd=params.rd,
        rs1=params.rs1,
        rs2=params.rs2,
        rs2val=params.rs2val,
        temp_reg=params.temp_reg,
    )


# SC.W conditionally writes a word in rs2 to the address in rs1: the SC.W succeeds only if
# the reservation is still valid and the reservation set contains the bytes being written.
# If the SC.W succeeds, the instruction writes the word in rs2 to memory, and it writes zero to rd.
# If the SC.W fails, the instruction does not write to memory, and it writes a nonzero value to rd.
