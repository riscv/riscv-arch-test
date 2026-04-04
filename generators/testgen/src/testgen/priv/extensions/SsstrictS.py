##################################
# priv/extensions/SsstrictS.py
#
# Ssstrict supervisor-mode privileged test generator.
# Tests all CSR encodings and reserved instruction encodings from S-mode.
# Also tests mstatus/sstatus shadow register consistency.
#
# SPDX-License-Identifier: Apache-2.0
##################################

"""SsstrictS privileged test generator — supervisor-mode negative/strict tests."""

from random import randint, seed

from testgen.asm.helpers import comment_banner
from testgen.data.state import TestData
from testgen.priv.extensions.SsstrictSm import _emit_raw_words
from testgen.priv.registry import add_priv_test_generator

# ─────────────────────────────────────────────────────────────────────────────
# CSR address skip set for S-mode
# ─────────────────────────────────────────────────────────────────────────────

# Custom / non-standard CSR ranges + satp to skip in S-mode
_S_CSR_SKIP: frozenset[int] = frozenset(
    list(range(0x5C0, 0x600))    # S-mode custom1
    + list(range(0x6C0, 0x700))  # H-mode custom1
    + list(range(0x9C0, 0xA00))  # S-mode custom2
    + list(range(0xAC0, 0xB00))  # H-mode custom2
    + list(range(0xDC0, 0xE00))  # S-mode custom3
    + list(range(0xEC0, 0xF00))  # H-mode custom3
    + list(range(0x800, 0x900))  # user custom2
    + list(range(0xCC0, 0xD00))  # user custom3
    + [0x180]                    # satp — exclude to avoid enabling virtual memory
)


# ─────────────────────────────────────────────────────────────────────────────
# cp_csrr / cp_csrw_corners / cp_csrcs / cp_shadow_m / cp_shadow_s
# ─────────────────────────────────────────────────────────────────────────────

def _generate_csr_tests_s(test_data: TestData) -> list[str]:
    """Generate CSR access coverpoints from S-mode plus shadow register tests."""
    covergroup = "SsstrictS_scsr_cg"
    lines: list[str] = []

    lines.append(comment_banner(
        "cp_csrr / cp_csrw_corners / cp_csrcs (S-mode)",
        "Read all CSRs, write all-zeros/all-ones, set/clear from S-mode.\n"
        "Skips satp (0x180) and all custom CSR ranges.\n"
        "M-mode/H-mode/debug CSRs should raise illegal-instruction from S-mode.",
    ))

    # Switch to supervisor mode
    lines.extend([
        "",
        "// Switch to supervisor mode for CSR sweep",
        "\tli a0, 1               # ecall code for S-mode",
        "\tecall                  # enter S-mode",
        "",
    ])

    for csr_addr in range(4096):
        if csr_addr in _S_CSR_SKIP:
            continue

        r1 = randint(1, 31)
        r2 = randint(1, 31)
        while r2 == r1:
            r2 = randint(1, 31)
        r3 = randint(1, 31)
        while r3 in (r1, r2):
            r3 = randint(1, 31)

        ih = hex(csr_addr)
        lines.extend([
            f"\n// CSR {ih} (S-mode)",
            f"\t{test_data.add_testcase(f'csrr_{ih}', 'cp_csrr', covergroup)}",
            f"\tcsrr x{r1}, {ih}                  // cp_csrr: read CSR",
            f"\tli x{r2}, -1",
            f"\t{test_data.add_testcase(f'csrw_ones_{ih}', 'cp_csrw_corners', covergroup)}",
            f"\tcsrrw x{r3}, {ih}, x{r2}          // cp_csrw_corners: write all 1s",
            f"\t{test_data.add_testcase(f'csrw_zeros_{ih}', 'cp_csrw_corners', covergroup)}",
            f"\tcsrrw x{r3}, {ih}, x0             // cp_csrw_corners: write all 0s",
            f"\t{test_data.add_testcase(f'csrrs_{ih}', 'cp_csrcs', covergroup)}",
            f"\tcsrrs x{r3}, {ih}, x{r2}          // cp_csrcs: set all bits",
            f"\t{test_data.add_testcase(f'csrrc_{ih}', 'cp_csrcs', covergroup)}",
            f"\tcsrrc x{r3}, {ih}, x{r2}          // cp_csrcs: clear all bits",
            f"\tcsrrw x{r3}, {ih}, x{r1}          // restore CSR",
        ])

    # Return to M-mode for shadow tests
    lines.extend([
        "",
        "// Return to M-mode for shadow register tests",
        "\tli a0, 3               # ecall code for M-mode",
        "\tecall",
        "",
    ])

    # cp_shadow_m: write to mstatus/mie/mip from M-mode
    lines.append(comment_banner(
        "cp_shadow_m",
        "Write all-ones and all-zeros to mstatus/mie/mip from M-mode.\n"
        "Verifies S-mode shadow registers (sstatus/sie/sip) reflect consistent values.",
    ))
    for csr_name in ["mstatus", "mie", "mip"]:
        lines.extend([
            f"\n// cp_shadow_m: {csr_name} from M-mode",
            f"\t{test_data.add_testcase(f'{csr_name}_ones', 'cp_shadow_m', covergroup)}",
            f"\tli t0, -1",
            f"\tcsrrw x0, {csr_name}, t0   // write all-ones to {csr_name}",
            f"\t{test_data.add_testcase(f'{csr_name}_zeros', 'cp_shadow_m', covergroup)}",
            f"\tcsrrw x0, {csr_name}, x0   // write all-zeros to {csr_name}",
        ])

    # Switch to S-mode for shadow S-side tests
    lines.extend([
        "",
        "// Switch to S-mode for shadow S-mode CSR tests",
        "\tli a0, 1",
        "\tecall",
        "",
    ])

    # cp_shadow_s: write to sstatus/sie/sip from S-mode
    lines.append(comment_banner(
        "cp_shadow_s",
        "Write all-ones and all-zeros to sstatus/sie/sip from S-mode.\n"
        "Verifies consistency with M-mode shadow (mstatus/mie/mip).",
    ))
    for csr_name in ["sstatus", "sie", "sip"]:
        lines.extend([
            f"\n// cp_shadow_s: {csr_name} from S-mode",
            f"\t{test_data.add_testcase(f'{csr_name}_ones', 'cp_shadow_s', covergroup)}",
            f"\tli t0, -1",
            f"\tcsrrw x0, {csr_name}, t0   // write all-ones to {csr_name}",
            f"\t{test_data.add_testcase(f'{csr_name}_zeros', 'cp_shadow_s', covergroup)}",
            f"\tcsrrw x0, {csr_name}, x0   // write all-zeros to {csr_name}",
        ])

    # Return to M-mode
    lines.extend([
        "",
        "\tli a0, 3",
        "\tecall                  // return to M-mode",
    ])

    return lines


# ─────────────────────────────────────────────────────────────────────────────
# cp_illegal_instruction — reserved 32-bit encodings from S-mode
# ─────────────────────────────────────────────────────────────────────────────

def _generate_illegal_instr_s(test_data: TestData) -> list[str]:
    """Generate cp_illegal_instruction from S-mode."""
    covergroup = "SsstrictS_instr_cg"
    coverpoint = "cp_illegal_instruction"
    lines: list[str] = []

    lines.append(comment_banner(
        coverpoint + " (S-mode)",
        "Same reserved/illegal encoding sweep as SsstrictSm but executed from S-mode.\n"
        "M-mode-only instructions additionally trap from S-mode.",
    ))

    # Enable FP/V from M-mode before switching
    lines.extend([
        "// Enable FP and Vector from M-mode before switching to S-mode",
        "\tli t0, 1",
        "\tslli t1, t0, 13",
        "\tcsrs mstatus, t1    # mstatus.FS = Initial",
        "\tslli t1, t0, 9",
        "\tcsrs mstatus, t1    # mstatus.VS = Initial",
        "",
        "// Switch to S-mode for instruction encoding sweep",
        "\tli a0, 1",
        "\tecall",
        "",
    ])

    lines.append(f"\t{test_data.add_testcase('illegal_instr_sweep_s', coverpoint, covergroup)}")

    # Core reserved encoding templates — same set as SsstrictSm
    for op_comment, template in [
        ("Reserved opcodes op7",     "RRRRRRRRRRRRRRRRRRRRRRRRR0011111"),
        ("Reserved opcodes op15",    "RRRRRRRRRRRRRRRRRRRRRRRRR0111111"),
        ("Reserved opcodes op21",    "RRRRRRRRRRRRRRRRRRRRRRRRR1010111"),
        ("Reserved opcodes op23",    "RRRRRRRRRRRRRRRRRRRRRRRRR1011111"),
        ("Reserved opcodes op26",    "RRRRRRRRRRRRRRRRRRRRRRRRR1101011"),
        ("Reserved opcodes op29",    "RRRRRRRRRRRRRRRRRRRRRRRRR1110111"),
        ("Reserved opcodes op31",    "RRRRRRRRRRRRRRRRRRRRRRRRR1111111"),
        ("cp_load funct3",           "RRRRRRRRRRRRRRRRREEERRRRR0000011"),
        ("cp_fload funct3",          "RRRRRRRRRRRRRRRRREEERRRRR0000111"),
        ("cp_fence_cbo funct3",      "RRRRRRRRRRRRRRRRREEERRRRR0001111"),
        ("cp_cbo_immediate",         "EEEEEEEEEEEE00000010000000001111"),
        ("cp_cbo_rd",                "00000000000RRRRRR010EEEEE0001111"),
        ("cp_Itype",                 "EEEEEEEEEEEERRRRRE01RRRRR0010011"),
        ("cp_aes64ks1i",             "0011000EEEEERRRRR001RRRRR0010011"),
        ("cp_IWshift",               "EEEEEEERRRRRRRRRRE01RRRRR0011011"),
        ("cp_store funct3",          "RRRRRRRRRRRR00000EEERRRRR0100011"),
        ("cp_fstore funct3",         "RRRRRRRRRRRR00000EEERRRRR0100111"),
        ("cp_atomic_funct3",         "RRRRRRRRRRRR00000EEERRRRR0101111"),
        ("cp_atomic_funct7",         "EEEEERRRRRRR0000001ERRRRR0101111"),
        ("cp_lrsc",                  "00010RREEEEE0000001ERRRRR0101111"),
        ("cp_rtype",                 "EEEEEEERRRRRRRRRREEERRRRR0110011"),
        ("cp_rwtype",                "EEEEEEERRRRRRRRRREEERRRRR0111011"),
        ("cp_ftype",                 "EEEEERRRRRRRRRRRREEERRRRR1010011"),
        ("cp_fsqrt",                 "0101100EEEEERRRRRRRRRRRRR1010011"),
        ("cp_fclass",                "1110000EEEEERRRRR001RRRRR1010011"),
        ("cp_fcvtif",                "1100000EEE00RRRRR000RRRRR1010011"),
        ("cp_fcvtif_fmt",            "11000EE000EERRRRR000RRRRR1010011"),
        ("cp_fcvtfi",                "1101000EEER00RRRR000RRRRR1010011"),
        ("cp_fcvtfi_fmt",            "11010EE000EERRRRR000RRRRR1010011"),
        ("cp_fcvtff",                "0100000EEER00RRRR000RRRRR1010011"),
        ("cp_fcvtff_fmt",            "01000EEEEEEERRRRR000RRRRR1010011"),
        ("cp_fmvif",                 "11100EEEEEEERRRRR000RRRRR1010011"),
        ("cp_fmvfi",                 "11110EEEEEEERRRRR000RRRRR1010011"),
        ("cp_fmvp",                  "10110EERRRRRRRRRR000RRRRR1010011"),
        ("cp_fcvtmodwdfrm",          "110000101000RRRRREEERRRRR1010011"),
        ("cp_branch2",               "RRRRRRRRRRRRRRRRR010RRRRR1100011"),
        ("cp_branch3",               "RRRRRRRRRRRRRRRRR011RRRRR1100011"),
        ("cp_jalr0",                 "RRRRRRRRRRRRRRRRREE1RRRRR1100111"),
        ("cp_jalr1",                 "RRRRRRRRRRRRRRRRR010RRRRR1100111"),
        ("cp_privileged_f3",         "00000000000100000EEE000001110011"),
        ("cp_reserved_fma",          "RRRRRRRRRRRRRRRRREEERRRRR100EE11"),
        ("cp_upperreg_rs1_add",      "0000000000011EEEE000000010110011"),
        ("cp_upperreg_rs2_add",      "00000001EEEE00001000000100110011"),
        ("cp_upperreg_rd_add",       "000000000001000010001EEEE0110011"),
        ("cp_upperreg_rs1_fadd-s",   "0000000000011EEEE000000011010011"),
        ("cp_upperreg_imm_rs1_addi0","0000000000001EEEE000000010010011"),
        ("cp_upperreg_imm_rd_addi0", "000000000000000010001EEEE0010011"),
        ("cp_amocas_odd",            "00101RRRRRRRRRRREEEERRRRE0101111"),
    ]:
        _emit_raw_words(lines, op_comment + " (S-mode)", template)

    # Return to M-mode
    lines.extend(["", "\tli a0, 3", "\tecall   // return to M-mode"])
    return lines


# ─────────────────────────────────────────────────────────────────────────────
# cp_illegal_compressed_instruction — from S-mode
# ─────────────────────────────────────────────────────────────────────────────

def _generate_compressed_instr_s(test_data: TestData) -> list[str]:
    """Generate cp_illegal_compressed_instruction from S-mode."""
    covergroup = "SsstrictS_instr_cg"
    coverpoint = "cp_illegal_compressed_instruction"
    lines: list[str] = []

    lines.append(comment_banner(
        coverpoint + " (S-mode)",
        "Same compressed quadrant sweep as SsstrictSm but executed from S-mode.",
    ))
    lines.extend([
        "\tli a0, 1",
        "\tecall   // enter S-mode",
        "",
    ])
    lines.append(f"\t{test_data.add_testcase('compressed_sweep_s', coverpoint, covergroup)}")

    _emit_raw_words(lines, "compressed00 (S-mode)", "EEEEEEEEEEEEEE00", length=16,
                    exclusion=[
                        "X01XXXXXXXXXXX00",  # c.fld/c.fsd — bad address
                        "X10XXXXXXXXXXX00",  # c.lw/c.sw — bad address
                        "10000XXXXXXXXX00",  # c.lbu/c.lh/c.lhu — bad address
                        "100010XXXXXXXX00",  # c.sb — bad address
                        "100011XXX0XXXX00",  # c.sh — bad address
                    ])
    _emit_raw_words(lines, "compressed01 (S-mode)", "EEEEEEEEEEEEEE01", length=16,
                    exclusion=[
                        "101XXXXXXXXXXX01",  # c.j — random jump
                        "11XXXXXXXXXXXX01",  # c.beqz/c.bnez — random branch
                        "001XXXXXXXXXXX01",  # c.jr — random jump
                    ])
    _emit_raw_words(lines, "compressed10 (S-mode)", "EEEEEEEEEEEEEE10", length=16,
                    exclusion=[
                        "1000XXXXX0000010",  # c.jr rs1=0 — illegal (tested below)
                        "1001XXXXX0000010",  # c.jalr rs1=0 — c.ebreak space
                        "X01XXXXXXXXXXX10",  # c.fldsp/c.fsdsp — bad address
                        "X10XXXXXXXXXXX10",  # c.swsp/c.lwsp — bad address
                        "1001000000000010",  # c.ebreak — tested in ExceptionsSm
                    ])

    lines.extend([
        "",
        "// Sanity-check samples for excluded memory ops",
        "\t.hword 0b0010000000000000  # c.fld sample",
        "\t.hword 0b0100000000000000  # c.lw  sample",
        "\t.hword 0b1000000000000010  # c.jr rs1=0 (illegal)",
        "",
        "\tli a0, 3",
        "\tecall   // return to M-mode",
    ])
    return lines


# ─────────────────────────────────────────────────────────────────────────────
# cp_reserved_frm — from S-mode
# ─────────────────────────────────────────────────────────────────────────────

def _generate_reserved_frm_s(test_data: TestData) -> list[str]:
    """Generate cp_reserved_frm from S-mode."""
    covergroup = "SsstrictS_instr_cg"
    coverpoint = "cp_reserved_frm"
    lines: list[str] = []

    lines.append(comment_banner(
        coverpoint + " (S-mode)",
        "Test each FRM value 0-7 with FADD.S using dynamic rounding from S-mode.\n"
        "FRM=5 and FRM=6 are reserved. mstatus.FS must be non-zero before entering S-mode.",
    ))
    lines.extend(["\tli a0, 1", "\tecall   // enter S-mode", ""])

    for frm in range(8):
        lines.extend([
            f"\n// cp_reserved_frm: FRM = {frm} (S-mode)",
            f"\t{test_data.add_testcase(f'frm_{frm}_s', coverpoint, covergroup)}",
            f"\tcsrwi frm, {frm}",
            f"\tfadd.s f0, f1, f2",
        ])

    lines.extend(["", "\tli a0, 3", "\tecall   // return to M-mode"])
    return lines


# ─────────────────────────────────────────────────────────────────────────────
# cp_misa_ext_disable — from S-mode
# ─────────────────────────────────────────────────────────────────────────────

def _generate_misa_ext_disable_s(test_data: TestData) -> list[str]:
    """Generate cp_misa_ext_disable from S-mode."""
    covergroup = "SsstrictS_instr_cg"
    coverpoint = "cp_misa_ext_disable"
    lines: list[str] = []

    lines.append(comment_banner(
        coverpoint + " (S-mode)",
        "For each MUTABLE_MISA_* extension: disable the misa bit from M-mode,\n"
        "switch to S-mode, execute a representative instruction (should trap),\n"
        "return to M-mode, re-enable.\n"
        "Also tests entering U-mode with misa.U=0.",
    ))

    ext_tests = [
        ("A",  0,  "amoswap.w x0, x0, (x0)", "A-ext AMO with A=0"),
        ("C",  2,  "c.addi x8, 0",            "C-ext compressed with C=0"),
        ("D",  3,  ".word 0x02008053",         "D-ext fadd.d with D=0"),
        ("F",  5,  "fadd.s f0, f1, f2",        "F-ext fadd.s with F=0"),
        ("M",  12, "mul x1, x2, x3",           "M-ext mul with M=0"),
        ("V",  21, "vadd.vv v0, v1, v2",        "V-ext vadd.vv with V=0"),
    ]

    for ext, bit, instr, desc in ext_tests:
        misa_bit = 1 << bit
        lines.extend([
            "",
            f"// {desc}",
            f"#ifdef MUTABLE_MISA_{ext}",
            f"\tli t0, {misa_bit:#010x}      # misa.{ext} bit",
            f"\tcsrc misa, t0                # disable {ext} from M-mode",
            f"\tli a0, 1                     # switch to S-mode",
            f"\tecall",
            f"\t{test_data.add_testcase(f'misa_{ext}_disable_s', coverpoint, covergroup)}",
            f"\t{instr}                       # should raise illegal-instruction",
            f"\tnop",
            f"\tli a0, 3                     # return to M-mode",
            f"\tecall",
            f"\tcsrs misa, t0                # re-enable {ext}",
            "#endif",
        ])

    # Test entering U-mode with misa.U=0
    lines.extend([
        "",
        "// Attempt to enter U-mode with misa.U=0 — should trap",
        "#ifdef MUTABLE_MISA_U",
        f"\t{test_data.add_testcase('misa_U_entry_s', coverpoint, covergroup)}",
        "\tli t0, 0x100000            # misa.U bit (bit 20)",
        "\tcsrc misa, t0              # disable U from M-mode",
        "\tli a0, 0                   # attempt to enter U-mode",
        "\tecall                      # should trap or fail",
        "\tcsrs misa, t0              # re-enable U",
        "#endif",
    ])

    # B-extension sub-tests from S-mode
    lines.extend([
        "",
        "// B-ext sub-extensions from S-mode",
        "#ifdef MUTABLE_MISA_B",
        "\tli t0, 0x2",
        "\tcsrc misa, t0",
        "\tli a0, 1",
        "\tecall                   // enter S-mode",
        f"\t{test_data.add_testcase('misa_B_zba_s', coverpoint, covergroup)}",
        "\tsh3add x1, x2, x3       // Zba — should trap",
        "\tnop",
        f"\t{test_data.add_testcase('misa_B_zbb_s', coverpoint, covergroup)}",
        "\tandn x1, x2, x3         // Zbb — should trap",
        "\tnop",
        f"\t{test_data.add_testcase('misa_B_zbc_s', coverpoint, covergroup)}",
        "\tclmul x1, x2, x3        // Zbc — should NOT trap (independent of B)",
        "\tnop",
        "\tli a0, 3",
        "\tecall                   // return to M-mode",
        "\tcsrs misa, t0           // re-enable B",
        "#endif",
    ])

    return lines


# ─────────────────────────────────────────────────────────────────────────────
# Main entry point
# ─────────────────────────────────────────────────────────────────────────────

@add_priv_test_generator(
    "SsstrictS",
    required_extensions=["S", "Sm", "Zicsr"],
    march_extensions=["I", "M", "A", "F", "D", "C", "Zicsr",
                      "Zba", "Zbb", "Zbc", "Zbs", "Zacas",
                      "Zca", "Zcb", "Zcd", "Zcf"],
    extra_defines=[
        "#define RVTEST_PRIV_TEST",
        "#define FAST_TRAP_HANDLER",
    ],
)
def make_ssstricts(test_data: TestData) -> list[str]:
    """
    Generate tests for SsstrictS — supervisor-mode strict compliance tests.

    Exercises:
      1. All 4096 CSR addresses (read/write/set/clear) from S-mode
      2. mstatus/sstatus, mie/sie, mip/sip shadow register consistency
      3. All reserved/illegal 32-bit instruction encodings from S-mode
      4. All reserved 16-bit compressed encodings from S-mode
      5. Reserved FP rounding modes from S-mode
      6. misa extension disable/enable behavior from S-mode
    """
    seed(43)
    lines: list[str] = []

    # Install fast trap handler from M-mode before any mode switching
    lines.extend([
        "// Install fast trap handler from M-mode before entering S-mode.",
        "// This handler must survive across mode switches (mtvec is M-mode register).",
        "LA(t0, trap_handler_fastuncompressedillegalinstr)",
        "CSRW(mtvec, t0)",
        "",
    ])

    lines.extend(_generate_csr_tests_s(test_data))
    lines.extend(_generate_illegal_instr_s(test_data))
    lines.extend(_generate_compressed_instr_s(test_data))
    lines.extend(_generate_reserved_frm_s(test_data))
    lines.extend(_generate_misa_ext_disable_s(test_data))

    return lines
