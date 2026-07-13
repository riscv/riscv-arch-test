##################################
# csr_type.py
#
# jcarlin@hmc.edu Oct 2025
# SPDX-License-Identifier: Apache-2.0
##################################

from testgen.asm.helpers import load_int_reg, write_sigupd
from testgen.data.params import InstructionParams
from testgen.data.state import TestData
from testgen.formatters.registry import InstructionTypeConfig, add_instruction_formatter

csr_config = InstructionTypeConfig(required_params={"rd", "rs1", "rs1val", "rs2", "rs2val"})


def zicsr_acccess(instr_name: str, rd: int, rs1: int) -> str:
    """Helper function to determine which CSR to use for testing based on supported extensions."""
    # Use writable unprivileged extension CSRs if any exist,
    # else use mepc if U is not supported
    # else use instret (which is not writable, but at least can be accessed)

    # instret requires special treatment because it is not writable, and the value is not initialized
    if instr_name in ["csrrw", "csrrwi"] or rs1 == 0 or rd == 0:
        instret_access = f"li x{rd}, 0 # avoid write to read-only instret, or inconsistent result with rs1 or rd = 0"
    else:
        instret_access = (
            f"{instr_name} x{rs1}, instret, x0\n"
            f"{instr_name} x{rd}, instret, x0\n"
            f"sub x{rd}, x{rd}, x{rs1}  # check that instret value has incremented\n"
        )

    return (
        "#if defined(F_SUPPORTED)\n"
        f"{instr_name} x{rd}, fflags, x{rs1}\n"
        "#elif defined(V_SUPPORTED)\n"
        f"{instr_name} x{rd}, vxsat, x{rs1}\n"
        "#elif !defined(U_SUPPORTED)\n"
        f"{instr_name} x{rd}, mepc, x{rs1}\n"
        "#elif defined(ZICNTR_SUPPORTED)\n"
        f"{instret_access}\n"
        "#else\n"
        f"  #error no CSR known for testing\n"
        "#endif\n"
    )


@add_instruction_formatter("CSR", csr_config)
def format_csr_type(
    instr_name: str, test_data: TestData, params: InstructionParams
) -> tuple[list[str], list[str], list[str]]:
    """Format CSR-type instruction."""
    assert params.rs1 is not None and params.rs1val is not None
    assert params.rs2 is not None and params.rs2val is not None
    assert params.rd is not None
    setup = [
        load_int_reg("rs1", params.rs1, params.rs1val, test_data),
        load_int_reg("temp reg", params.rs2, params.rs2val, test_data),
        "// Initialize CSR with random value",
        "// Pick most suitable CSR to test based on supported extensions",
        zicsr_acccess("csrrw", 0, params.rs2),
    ]
    test = [
        "// perform operation",
        zicsr_acccess(instr_name, params.rd, params.rs1),
    ]
    check = [
        write_sigupd(params.rd, test_data, "int"),
        "// read back CSR to check updated value",
        zicsr_acccess("csrrs", params.rs2, 0),
        write_sigupd(params.rs2, test_data, "int"),
    ]
    return (setup, test, check)
