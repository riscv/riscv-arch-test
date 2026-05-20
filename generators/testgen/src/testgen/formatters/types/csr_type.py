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

# Strict native ABI.
csr_config = InstructionTypeConfig(required_params={"rd", "rs1", "rs1val", "rs2", "rs2val"})


def zicsr_acccess_setup(rs2: int) -> str:
    """Helper to initialize CSR or sample 'before' counter value."""
    # Use writable unprivileged extension CSRs if any exist,
    # else use mepc if U is not supported
    # else use instret (which is not writable, but at least can be accessed)
    return (
        "#if defined(F_SUPPORTED)\n"
        f"csrrw x0, fflags, x{rs2}\n"
        "#elif defined(V_SUPPORTED)\n"
        f"csrrw x0, vxsat, x{rs2}\n"
        "#elif !defined(U_SUPPORTED)\n"
        f"csrrw x0, mepc, x{rs2}\n"
        "#elif defined(ZICNTR_SUPPORTED)\n"
        f"csrrs x{rs2}, instret, x0\n"
        "#else\n"
        f"  Error: no CSR known for testing\n"
        "#endif\n"
    )


def zicsr_acccess(instr_name: str, rd: int, rs1: int) -> str:
    """Helper function to determine which CSR to use for testing based on supported extensions."""
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

    forbidden = {params.rd, params.rs1, params.rs2}
    allocated = []
    scratch_reg = None

    try:
        allocated = test_data.int_regs.get_registers(len(forbidden) + 1)
        
        for reg in allocated:
            if reg not in forbidden:
                scratch_reg = reg
                break
        
        if scratch_reg is None:
            raise RuntimeError("Allocator returned non-unique registers violating contract.")

        setup = [
            load_int_reg("rs1", params.rs1, params.rs1val, test_data),
            load_int_reg("temp reg", params.rs2, params.rs2val, test_data),
            "// Initialize CSR with random value or capture 'before' sample",
            zicsr_acccess_setup(params.rs2),
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
            "// 1. Validate 'rd' (architectural return) against 'before' sample using safe dynamic scratch",
            f"sub x{scratch_reg}, x{params.rd}, x{params.rs2}",
            f"sltiu x{scratch_reg}, x{scratch_reg}, 0x000007FF",
            write_sigupd(scratch_reg, test_data, "int"),     
            "// 2. Validate 'after' counter state (safe to clobber rs2 now)",
            f"csrrs x{scratch_reg}, instret, x0",
            f"sub x{scratch_reg}, x{scratch_reg}, x{params.rs2}",
            f"sltiu x{params.rs2}, x{scratch_reg}, 0x000007FF",
            write_sigupd(params.rs2, test_data, "int"),
            "#else",
            "  Error: no CSR known for testing",
            "#endif",
        ]
        return (setup, test, check)

    finally:
        if allocated:
            test_data.int_regs.return_registers(allocated)
