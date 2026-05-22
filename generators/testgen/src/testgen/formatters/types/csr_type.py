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
    return (
        "#if defined(F_SUPPORTED)\n"
        f"{instr_name} x{rd}, fflags, x{rs1}\n"
        "#elif defined(V_SUPPORTED)\n"
        f"{instr_name} x{rd}, vxsat, x{rs1}\n"
        "#elif !defined(U_SUPPORTED)\n"
        f"{instr_name} x{rd}, mepc, x{rs1}\n"
        "#elif defined(ZICNTR_SUPPORTED)\n"
        f"{instr_name} x{rd}, instret, x{rs1}\n"
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

    scratch_reg = test_data.int_regs.get_register()
    
    try:
        setup = [
            load_int_reg("rs1", params.rs1, params.rs1val, test_data),
            load_int_reg("temp reg", params.rs2, params.rs2val, test_data),
        ]
        test = [
            "// perform operation",
            zicsr_acccess(instr_name, params.rd, params.rs1),
        ]
        check = [
            "#if defined(F_SUPPORTED)",
            write_sigupd(params.rd, test_data, "int"),
            "// read back CSR to check updated value",
            f"csrrs x{params.rs2}, fflags, x0",
            write_sigupd(params.rs2, test_data, "int"),
            "#elif defined(V_SUPPORTED)",
            write_sigupd(params.rd, test_data, "int"),
            "// read back CSR to check updated value",
            f"csrrs x{params.rs2}, vxsat, x0",
            write_sigupd(params.rs2, test_data, "int"),
            "#elif !defined(U_SUPPORTED)",
            write_sigupd(params.rd, test_data, "int"),
            "// read back CSR to check updated value",
            f"csrrs x{params.rs2}, mepc, x0",
            write_sigupd(params.rs2, test_data, "int"),
            "#elif defined(ZICNTR_SUPPORTED)",
            write_sigupd(params.rd, test_data, "int"),
            "// read instret twice and record the difference to prove it ticks",
            f"csrrs x{scratch_reg}, instret, x0",
            f"csrrs x{params.rs2}, instret, x0",
            f"sub x{scratch_reg}, x{params.rs2}, x{scratch_reg}",
            write_sigupd(scratch_reg, test_data, "int"),     
            "#else",
            "#error no CSR known for testing",
            "#endif",
        ]
        return (setup, test, check)

    finally:
        test_data.int_regs.return_register(scratch_reg)
