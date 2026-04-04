##################################
# priv/extensions/SsstrictU.py
#
# Ssstrict user-mode privileged test generator.
# Tests all CSR encodings and reserved instruction encodings from U-mode.
#
# SPDX-License-Identifier: Apache-2.0
##################################

"""SsstrictU privileged test generator — user-mode negative/strict tests."""

from random import randint, seed

from testgen.asm.helpers import comment_banner
from testgen.data.state import TestData
from testgen.priv.extensions.SsstrictSm import _emit_raw_words
from testgen.priv.registry import add_priv_test_generator

# ─────────────────────────────────────────────────────────────────────────────
# CSR address skip set for U-mode
# ─────────────────────────────────────────────────────────────────────────────

# Only skip user-custom CSR ranges — everything else should be tested
# (most will trap from U-mode, which is exactly what we want to verify)
_U_CSR_SKIP: frozenset[int] = frozenset(
    list(range(0x800, 0x900))    # user custom2
    + list(range(0xCC0, 0xD00))  # user custom3
)


# ─────────────────────────────────────────────────────────────────────────────
# cp_csrr / cp_csrw_corners / cp_csrcs
# ─────────────────────────────────────────────────────────────────────────────

def _generate_csr_tests_u(test_data: TestData) -> list[str]:
    """Generate CSR access coverpoints from U-mode."""
    covergroup = "SsstrictU_ucsr_cg"
    lines: list[str] = []

    lines.append(comment_banner(
        "cp_csrr / cp_csrw_corners / cp_csrcs (U-mode)",
        "Read all CSRs, write all-zeros/all-ones, set/clear from U-mode.\n"
        "Only user-level CSRs (cycle, time, fflags, frm, fcsr etc.) succeed;\n"
        "all others raise illegal-instruction from U-mode.",
    ))

    lines.extend([
        "",
        "// Switch to user mode for CSR sweep",
        "\tli a0, 0               # ecall code for U-mode",
        "\tecall                  # enter U-mode",
        "",
    ])

    for csr_addr in range(4096):
        if csr_addr in _U_CSR_SKIP:
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
            f"\n// CSR {ih} (U-mode)",
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

    # Return to M-mode
    lines.extend([
        "",
        "\tli a0, 3",
        "\tecall                  // return to M-mode",
    ])

    return lines


# ─────────────────────────────────────────────────────────────────────────────
# cp_illegal_instruction — reserved 32-bit encodings from U-mode
# ─────────────────────────────────────────────────────────────────────────────

def _generate_illegal_instr_u(test_data: TestData) -> list[str]:
    """Generate cp_illegal_instruction from U-mode."""
    covergroup = "SsstrictU_instr_cg"
    coverpoint = "cp_illegal_instruction"
    lines: list[str] = []

    lines.append(comment_banner(
        coverpoint + " (U-mode)",
        "Same reserved/illegal encoding sweep as SsstrictSm/S but from U-mode.\n"
        "S-mode and M-mode instructions also trap from U-mode.",
    ))

    # Enable FP/V from M-mode before U-mode switch
    lines.extend([
        "// Enable FP and Vector from M-mode before switching to U-mode",
        "\tli t0, 1",
        "\tslli t1, t0, 13",
        "\tcsrs mstatus, t1    # mstatus.FS = Initial",
        "\tslli t1, t0, 9",
        "\tcsrs mstatus, t1    # mstatus.VS = Initial",
        "",
        "// Switch to U-mode",
        "\tli a0, 0",
        "\tecall",
        "",
    ])

    lines.append(f"\t{test_data.add_testcase('illegal_instr_sweep_u', coverpoint, covergroup)}")

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
        _emit_raw_words(lines, op_comment + " (U-mode)", template)

    lines.extend(["", "\tli a0, 3", "\tecall   // return to M-mode"])
    return lines


# ─────────────────────────────────────────────────────────────────────────────
# cp_illegal_compressed_instruction — from U-mode
# ─────────────────────────────────────────────────────────────────────────────

def _generate_compressed_instr_u(test_data: TestData) -> list[str]:
    """Generate cp_illegal_compressed_instruction from U-mode."""
    covergroup = "SsstrictU_instr_cg"
    coverpoint = "cp_illegal_compressed_instruction"
    lines: list[str] = []

    lines.append(comment_banner(
        coverpoint + " (U-mode)",
        "All compressed quadrant sweeps executed from U-mode.",
    ))
    lines.extend([
        "\tli a0, 0",
        "\tecall   // enter U-mode",
        "",
    ])
    lines.append(f"\t{test_data.add_testcase('compressed_sweep_u', coverpoint, covergroup)}")

    _emit_raw_words(lines, "compressed00 (U-mode)", "EEEEEEEEEEEEEE00", length=16,
                    exclusion=[
                        "X01XXXXXXXXXXX00",
                        "X10XXXXXXXXXXX00",
                        "10000XXXXXXXXX00",
                        "100010XXXXXXXX00",
                        "100011XXX0XXXX00",
                    ])
    _emit_raw_words(lines, "compressed01 (U-mode)", "EEEEEEEEEEEEEE01", length=16,
                    exclusion=[
                        "101XXXXXXXXXXX01",
                        "11XXXXXXXXXXXX01",
                        "001XXXXXXXXXXX01",
                    ])
    _emit_raw_words(lines, "compressed10 (U-mode)", "EEEEEEEEEEEEEE10", length=16,
                    exclusion=[
                        "1000XXXXX0000010",
                        "1001XXXXX0000010",
                        "X01XXXXXXXXXXX10",
                        "X10XXXXXXXXXXX10",
                        "1001000000000010",
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
# cp_reserved_frm — from U-mode
# ─────────────────────────────────────────────────────────────────────────────

def _generate_reserved_frm_u(test_data: TestData) -> list[str]:
    """Generate cp_reserved_frm from U-mode."""
    covergroup = "SsstrictU_instr_cg"
    coverpoint = "cp_reserved_frm"
    lines: list[str] = []

    lines.append(comment_banner(
        coverpoint + " (U-mode)",
        "Test each FRM value 0-7 with FADD.S using dynamic rounding from U-mode.\n"
        "Requires F extension. mstatus.FS enabled by M-mode before U-mode entry.",
    ))
    lines.extend(["\tli a0, 0", "\tecall   // enter U-mode", ""])

    for frm in range(8):
        lines.extend([
            f"\n// cp_reserved_frm: FRM = {frm} (U-mode)",
            f"\t{test_data.add_testcase(f'frm_{frm}_u', coverpoint, covergroup)}",
            f"\tcsrwi frm, {frm}",
            f"\tfadd.s f0, f1, f2",
        ])

    lines.extend(["", "\tli a0, 3", "\tecall   // return to M-mode"])
    return lines


# ─────────────────────────────────────────────────────────────────────────────
# cp_misa_ext_disable — from U-mode
# ─────────────────────────────────────────────────────────────────────────────

def _generate_misa_ext_disable_u(test_data: TestData) -> list[str]:
    """Generate cp_misa_ext_disable from U-mode."""
    covergroup = "SsstrictU_instr_cg"
    coverpoint = "cp_misa_ext_disable"
    lines: list[str] = []

    lines.append(comment_banner(
        coverpoint + " (U-mode)",
        "For each MUTABLE_MISA_* extension: disable the misa bit from M-mode,\n"
        "switch to U-mode, execute a representative instruction (should trap),\n"
        "return to M-mode, re-enable.",
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
            f"\tli a0, 0                     # switch to U-mode",
            f"\tecall",
            f"\t{test_data.add_testcase(f'misa_{ext}_disable_u', coverpoint, covergroup)}",
            f"\t{instr}                       # should raise illegal-instruction",
            f"\tnop",
            f"\tli a0, 3                     # return to M-mode",
            f"\tecall",
            f"\tcsrs misa, t0                # re-enable {ext}",
            "#endif",
        ])

    # B-extension sub-tests from U-mode
    lines.extend([
        "",
        "// B-ext sub-extensions from U-mode",
        "#ifdef MUTABLE_MISA_B",
        "\tli t0, 0x2",
        "\tcsrc misa, t0",
        "\tli a0, 0",
        "\tecall                   // enter U-mode",
        f"\t{test_data.add_testcase('misa_B_zba_u', coverpoint, covergroup)}",
        "\tsh3add x1, x2, x3       // Zba — should trap",
        "\tnop",
        f"\t{test_data.add_testcase('misa_B_zbb_u', coverpoint, covergroup)}",
        "\tandn x1, x2, x3         // Zbb — should trap",
        "\tnop",
        f"\t{test_data.add_testcase('misa_B_zbc_u', coverpoint, covergroup)}",
        "\tclmul x1, x2, x3        // Zbc — should NOT trap (Zbc independent of B)",
        "\tnop",
        "\tli a0, 3",
        "\tecall                   // return to M-mode",
        "\tcsrs misa, t0           // re-enable B",
        "#endif",
    ])

    # I-extension: upper register access in U-mode
    lines.extend([
        "",
        "// I-ext: with misa.I=0 (misa.E=1), x16-x31 access should trap from U-mode",
        "#ifdef MUTABLE_MISA_I",
        f"\t{test_data.add_testcase('misa_I_upperreg_u', coverpoint, covergroup)}",
        "\tli t0, 0x100             # misa.I bit",
        "\tcsrc misa, t0            # clear I → E activates",
        "\tli a0, 0",
        "\tecall                    # switch to U-mode",
        "\t.word 0x01080833         # add x16, x16, x16 — should trap with E active",
        "\tnop",
        "\tli a0, 3",
        "\tecall                    # return to M-mode",
        "\tcsrs misa, t0            # re-enable I",
        "#endif",
    ])

    return lines


# ─────────────────────────────────────────────────────────────────────────────
# Main entry point
# ─────────────────────────────────────────────────────────────────────────────

@add_priv_test_generator(
    "SsstrictU",
    required_extensions=["Sm", "U", "Zicsr"],
    march_extensions=["I", "M", "A", "F", "D", "C", "Zicsr",
                      "Zba", "Zbb", "Zbc", "Zbs", "Zacas",
                      "Zca", "Zcb", "Zcd", "Zcf"],
    extra_defines=[
        "#define RVTEST_PRIV_TEST",
        "#define FAST_TRAP_HANDLER",
    ],
)
def make_ssstrictu(test_data: TestData) -> list[str]:
    """
    Generate tests for SsstrictU — user-mode strict compliance tests.

    Exercises:
      1. All 4096 CSR addresses (read/write/set/clear) from U-mode
      2. All reserved/illegal 32-bit instruction encodings from U-mode
      3. All reserved 16-bit compressed encodings from U-mode
      4. Reserved FP rounding modes from U-mode
      5. misa extension disable/enable behavior from U-mode
    """
    seed(44)
    lines: list[str] = []

    # Install fast trap handler from M-mode
    # Traps from U-mode also vector through M-mode mtvec
    lines.extend([
        "// Install fast trap handler from M-mode.",
        "// Traps originating from U-mode also go through M-mode mtvec,",
        "// so this handler is valid for the entire test.",
        "LA(t0, trap_handler_fastuncompressedillegalinstr)",
        "CSRW(mtvec, t0)",
        "",
    ])

    lines.extend(_generate_csr_tests_u(test_data))
    lines.extend(_generate_illegal_instr_u(test_data))
    lines.extend(_generate_compressed_instr_u(test_data))
    lines.extend(_generate_reserved_frm_u(test_data))
    lines.extend(_generate_misa_ext_disable_u(test_data))

    return lines
