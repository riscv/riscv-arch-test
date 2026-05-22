##################################
# csri_type.py
#
# jcarlin@hmc.edu Oct 2025
# SPDX-License-Identifier: Apache-2.0
##################################

from testgen.asm.helpers import load_int_reg, write_sigupd
from testgen.data.params import InstructionParams
from testgen.data.state import TestData
from testgen.formatters.registry import InstructionTypeConfig, add_instruction_formatter

csri_config = InstructionTypeConfig(
    required_params={"rd", "rs2", "rs2val", "immval"}, 
    imm_bits=5, 
    imm_signed=False
)

def zicsr_acccessi(instr_name: str, rd: int, immval: int) -> str:
    """Helper function to determine which CSR to use for testing based on supported extensions."""
    # Use writable unprivileged extension CSRs if any exist,
    # else use mepc if U is not supported
    # else use instret (which is not writable, but at least can be accessed)
    return (
        "#if defined(F_SUPPORTED)\n"
        f"{instr_name} x{rd}, fflags, {immval}\n"
        "#elif defined(V_SUPPORTED)\n"
        f"{instr_name} x{rd}, vxsat, {immval}\n"
        "#elif !defined(U_SUPPORTED)\n"
        f"{instr_name} x{rd}, mepc, {immval}\n"
        "#elif defined(ZICNTR_SUPPORTED)\n"
        f"{instr_name} x{rd}, instret, {immval}\n"
        "#else\n"
        f"  #error no CSR known for testing\n"
        "#endif\n"
    )

@add_instruction_formatter("CSRI", csri_config)
def format_csri_type(
    instr_name: str, test_data: TestData, params: InstructionParams
) -> tuple[list[str], list[str], list[str]]:
    """Format CSRI-type instruction."""
    assert params.rs2 is not None and params.rs2val is not None
    assert params.immval is not None
    assert params.rd is not None

    allocated = []
    
    try:
        allocated = test_data.int_regs.get_registers(1)
        scratch_reg = allocated[0]
        # Dedicated scratch register used for instret delta calculation.

        setup = [
            load_int_reg("temp reg", params.rs2, params.rs2val, test_data),
        ]
        test = [
            "// perform operation",
            zicsr_acccessi(instr_name, params.rd, params.immval),
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
        if allocated:
            test_data.int_regs.return_registers(allocated)
