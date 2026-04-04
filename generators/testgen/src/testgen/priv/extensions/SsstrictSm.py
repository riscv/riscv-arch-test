##################################
# priv/extensions/SsstrictSm.py
#
# Ssstrict machine-mode privileged test generator.
# Tests all CSR encodings and reserved instruction encodings from M-mode.
#
# SPDX-License-Identifier: Apache-2.0
##################################

"""SsstrictSm privileged test generator — machine-mode negative/strict tests."""

from random import randint, seed

from testgen.asm.helpers import comment_banner
from testgen.data.state import TestData
from testgen.priv.registry import add_priv_test_generator

# ─────────────────────────────────────────────────────────────────────────────
# CSR address skip sets (match csrtests.py exactly)
# ─────────────────────────────────────────────────────────────────────────────

# Custom / non-standard CSR ranges to skip in M-mode
_M_CSR_SKIP: frozenset[int] = frozenset(
    list(range(0x7A0, 0x7B0))   # debug trigger regs — toggling could corrupt debug state
    + list(range(0x7C0, 0x800)) # M-mode custom
    + list(range(0xBC0, 0xC00)) # M-mode custom2
    + list(range(0xFC0, 0x1000))# M-mode custom3
    # Also skip super/hyper/user custom inherited from lower-mode generators:
    + list(range(0x5C0, 0x600)) # S-mode custom1
    + list(range(0x6C0, 0x700)) # H-mode custom1
    + list(range(0x9C0, 0xA00)) # S-mode custom2
    + list(range(0xAC0, 0xB00)) # H-mode custom2
    + list(range(0xDC0, 0xE00)) # S-mode custom3
    + list(range(0xEC0, 0xF00)) # H-mode custom3
    + list(range(0x800, 0x900)) # user custom2
    + list(range(0xCC0, 0xD00)) # user custom3
    # PMP registers — skip to protect PMP configuration
    + list(range(0x3A0, 0x3F0)) # pmpcfg0-15, pmpaddr0-63
)


# ─────────────────────────────────────────────────────────────────────────────
# Instruction encoding helpers (port of illegalinstrtests.py gen() function)
# ─────────────────────────────────────────────────────────────────────────────

def _gen_encodings(template: str, length: int = 32,
                   exclusion: list[str] | None = None,
                   rng_seed: int = 0) -> list[str]:
    """
    Generate all exhaustive instruction word encodings from a template.

    Template characters:
      E = exhaustively swept (0 and 1 for every combination)
      R = random bit (set once per call, not per encoding)
      0 / 1 = fixed bit

    Returns a list of binary strings (no '0b' prefix) for each non-excluded encoding.
    The exclusion patterns use X as wildcard.
    """
    if exclusion is None:
        exclusion = []

    ebits = template.count("E")
    results: list[str] = []

    for j in range(2 ** ebits):
        instr = ["0"] * length
        e = ebits - 1
        for i in range(length):
            if template[i] == "R":
                instr[i] = str(randint(0, 1))
            elif template[i] == "E":
                instr[i] = str((j >> e) & 1)
                e -= 1
            else:
                instr[i] = template[i]  # '0' or '1'

        instrstr = "".join(instr)
        excluded = False
        for pat in exclusion:
            if all(pat[k] == "X" or pat[k] == instrstr[k] for k in range(length)):
                excluded = True
                break
        if not excluded:
            results.append(instrstr)
    return results


def _emit_raw_words(lines: list[str], comment: str, template: str,
                    length: int = 32, exclusion: list[str] | None = None) -> None:
    """Append raw .word / .hword directives to lines from template."""
    directive = ".word" if length == 32 else ".hword"
    encodings = _gen_encodings(template, length, exclusion)
    lines.append(f"\n// {comment}  ({len(encodings)} encodings from template {template})")
    for enc in encodings:
        lines.append(f"\t{directive} 0b{enc}")


# ─────────────────────────────────────────────────────────────────────────────
# cp_csrr / cp_csrw_corners / cp_csrcs
# ─────────────────────────────────────────────────────────────────────────────

def _generate_csr_tests_m(test_data: TestData) -> list[str]:
    """Generate cp_csrr, cp_csrw_corners, cp_csrcs for M-mode."""
    covergroup = "SsstrictSm_mcsr_cg"
    lines: list[str] = []

    lines.append(comment_banner(
        "cp_csrr / cp_csrw_corners / cp_csrcs",
        "Read all 4096 CSRs, write all-zeros/all-ones, set/clear all bits.\n"
        "Fast trap handler must already be installed before this section.\n"
        "Skips: PMP regs 0x3A0-0x3EF, debug regs 0x7B0-0x7BF, and all custom CSR ranges.",
    ))

    # Lock PMP region 0 so PMP CSRs can be accessed without corrupting PMP config
    lines.extend([
        "",
        "// Lock PMP region 0 with TOR RWX so all PMP CSRs can be accessed",
        "\tli t0, 0x8F",
        "\tcsrw pmpcfg0, t0   # configure PMP0 to TOR RWX locked",
        "",
    ])

    for csr_addr in range(4096):
        if csr_addr in _M_CSR_SKIP:
            continue

        # Use three distinct random non-zero registers (avoid x0 for reads that need result)
        r1 = randint(1, 31)
        r2 = randint(1, 31)
        while r2 == r1:
            r2 = randint(1, 31)
        r3 = randint(1, 31)
        while r3 in (r1, r2):
            r3 = randint(1, 31)

        ih = hex(csr_addr)
        coverpoint_r  = "cp_csrr"
        coverpoint_w  = "cp_csrw_corners"
        coverpoint_cs = "cp_csrcs"

        lines.extend([
            f"\n// CSR {ih}",
            # cp_csrr — read with non-zero rd
            f"\t{test_data.add_testcase(f'csrr_{ih}', coverpoint_r, covergroup)}",
            f"\tcsrr x{r1}, {ih}                  // cp_csrr: read CSR",
            # cp_csrw_corners — write all 1s then all 0s
            f"\tli x{r2}, -1",
            f"\t{test_data.add_testcase(f'csrw_ones_{ih}', coverpoint_w, covergroup)}",
            f"\tcsrrw x{r3}, {ih}, x{r2}          // cp_csrw_corners: write all 1s",
            f"\t{test_data.add_testcase(f'csrw_zeros_{ih}', coverpoint_w, covergroup)}",
            f"\tcsrrw x{r3}, {ih}, x0             // cp_csrw_corners: write all 0s",
            # cp_csrcs — set all bits then clear all bits
            f"\t{test_data.add_testcase(f'csrrs_{ih}', coverpoint_cs, covergroup)}",
            f"\tcsrrs x{r3}, {ih}, x{r2}          // cp_csrcs: set all bits",
            f"\t{test_data.add_testcase(f'csrrc_{ih}', coverpoint_cs, covergroup)}",
            f"\tcsrrc x{r3}, {ih}, x{r2}          // cp_csrcs: clear all bits",
            # Restore original value
            f"\tcsrrw x{r3}, {ih}, x{r1}          // restore CSR",
        ])

    return lines


# ─────────────────────────────────────────────────────────────────────────────
# cp_illegal_instruction — reserved 32-bit encodings
# ─────────────────────────────────────────────────────────────────────────────

def _generate_illegal_instr(test_data: TestData) -> list[str]:
    """Generate cp_illegal_instruction: all reserved/illegal 32-bit encoding patterns."""
    covergroup = "SsstrictSm_instr_cg"
    coverpoint = "cp_illegal_instruction"
    lines: list[str] = []

    lines.append(comment_banner(
        coverpoint,
        "Exhaustive test of reserved and illegal 32-bit instruction encodings.\n"
        "Each .word directive is a raw encoding that should raise illegal-instruction\n"
        "or behave as a legal instruction that the coverage tool then classifies.\n"
        "Fast trap handler handles each trap. mstatus.FS/VS must be enabled.",
    ))

    # Enable FP and Vector extensions before encoding sweep
    lines.extend([
        "",
        "// Enable FP (mstatus.FS) and vector (mstatus.VS) to reduce unnecessary FP/V exceptions",
        "\tli t0, 1",
        "\tslli t1, t0, 13",
        "\tcsrs mstatus, t1    # mstatus.FS = 01 (Initial)",
        "\tslli t1, t0, 9",
        "\tcsrs mstatus, t1    # mstatus.VS = 01 (Initial, if V supported)",
        "",
    ])

    # Add a single testcase label for the whole illegal instruction section
    lines.append(f"\t{test_data.add_testcase('illegal_instr_sweep', coverpoint, covergroup)}")

    # ── Reserved major opcodes ───────────────────────────────────────────────
    for op_comment, template in [
        ("Illegal op7  (reserved)",  "RRRRRRRRRRRRRRRRRRRRRRRRR0011111"),
        ("Illegal op15 (reserved)",  "RRRRRRRRRRRRRRRRRRRRRRRRR0111111"),
        ("Illegal op21 (reserved)",  "RRRRRRRRRRRRRRRRRRRRRRRRR1010111"),
        ("Illegal op23 (reserved)",  "RRRRRRRRRRRRRRRRRRRRRRRRR1011111"),
        ("Illegal op26 (reserved)",  "RRRRRRRRRRRRRRRRRRRRRRRRR1101011"),
        ("Illegal op29 (reserved)",  "RRRRRRRRRRRRRRRRRRRRRRRRR1110111"),
        ("Illegal op31 (reserved)",  "RRRRRRRRRRRRRRRRRRRRRRRRR1111111"),
    ]:
        _emit_raw_words(lines, op_comment, template)

    # ── LOAD/STORE/FP load-store reserved funct3 ────────────────────────────
    _emit_raw_words(lines, "cp_load: reserved funct3 in LOAD opcode",
                    "RRRRRRRRRRRRRRRRREEERRRRR0000011")
    _emit_raw_words(lines, "cp_fload: reserved funct3 in FLOAD opcode",
                    "RRRRRRRRRRRRRRRRREEERRRRR0000111")
    _emit_raw_words(lines, "cp_fence_cbo: reserved funct3 in FENCE/CBO opcode",
                    "RRRRRRRRRRRRRRRRREEERRRRR0001111")
    _emit_raw_words(lines, "cp_cbo_immediate: all CBO immediates (rs1=0 to avoid bad writes)",
                    "EEEEEEEEEEEE00000010000000001111")
    _emit_raw_words(lines, "cp_cbo_rd: CBO with non-zero rd",
                    "00000000000RRRRRR010EEEEE0001111")
    _emit_raw_words(lines, "cp_store: reserved funct3 in STORE opcode (rs1=0)",
                    "RRRRRRRRRRRR00000EEERRRRR0100011")
    _emit_raw_words(lines, "cp_fstore: reserved funct3 in FSTORE opcode (rs1=0)",
                    "RRRRRRRRRRRR00000EEERRRRR0100111")

    # ── Integer arithmetic reserved fields ──────────────────────────────────
    _emit_raw_words(lines, "cp_Itype: reserved funct3[2:1]=01 in I-type arithmetic",
                    "EEEEEEEEEEEERRRRRE01RRRRR0010011")
    _emit_raw_words(lines, "cp_llAItype: all funct3 of I-type arithmetic",
                    "RRRRRRRRRRRRRRRRREEERRRRR0010011")
    _emit_raw_words(lines, "cp_aes64ks1i: reserved rnum values",
                    "0011000EEEEERRRRR001RRRRR0010011")
    _emit_raw_words(lines, "cp_IWtype: reserved funct3 in IW-type (RV64 word ops)",
                    "RRRRRRRRRRRRRRRRREEERRRRR0011011")
    _emit_raw_words(lines, "cp_IWshift: reserved shift types and imm[5]=1 for word shifts",
                    "EEEEEEERRRRRRRRRRE01RRRRR0011011")

    # ── Atomics ──────────────────────────────────────────────────────────────
    _emit_raw_words(lines, "cp_atomic_funct3: reserved funct3 in atomics (rs1=0)",
                    "RRRRRRRRRRRR00000EEERRRRR0101111")
    _emit_raw_words(lines, "cp_atomic_funct7: reserved funct7 in AMOs (rs1=0)",
                    "EEEEERRRRRRR0000001ERRRRR0101111")
    _emit_raw_words(lines, "cp_lrsc: reserved fields in LR/SC",
                    "00010RREEEEE0000001ERRRRR0101111")

    # ── R-type / RW-type ─────────────────────────────────────────────────────
    _emit_raw_words(lines, "cp_rtype: reserved funct3/funct7 in R-type",
                    "EEEEEEERRRRRRRRRREEERRRRR0110011")
    _emit_raw_words(lines, "cp_rwtype: reserved fields in RW-type",
                    "EEEEEEERRRRRRRRRREEERRRRR0111011")

    # ── Floating-point ───────────────────────────────────────────────────────
    _emit_raw_words(lines, "cp_ftype: reserved fmt/funct5 combinations in FP",
                    "EEEEERRRRRRRRRRRREEERRRRR1010011")
    _emit_raw_words(lines, "cp_fsqrt: reserved rs2 in fsqrt",
                    "0101100EEEEERRRRRRRRRRRRR1010011")
    _emit_raw_words(lines, "cp_fclass: reserved rs2 in fclass",
                    "1110000EEEEERRRRR001RRRRR1010011")
    _emit_raw_words(lines, "cp_fcvtif: reserved fmt/rs2 in fcvt (int←float)",
                    "1100000EEE00RRRRR000RRRRR1010011")
    _emit_raw_words(lines, "cp_fcvtif_fmt: reserved fmt fields in fcvt (int←float)",
                    "11000EE000EERRRRR000RRRRR1010011")
    _emit_raw_words(lines, "cp_fcvtfi: reserved fmt/rs2 in fcvt (float←int)",
                    "1101000EEER00RRRR000RRRRR1010011")
    _emit_raw_words(lines, "cp_fcvtfi_fmt: reserved fmt fields in fcvt (float←int)",
                    "11010EE000EERRRRR000RRRRR1010011")
    _emit_raw_words(lines, "cp_fcvtff: reserved fmt/rs2 in fcvt (float←float)",
                    "0100000EEER00RRRR000RRRRR1010011")
    _emit_raw_words(lines, "cp_fcvtff_fmt: reserved fmt fields in fcvt (float←float)",
                    "01000EEEEEEERRRRR000RRRRR1010011")
    _emit_raw_words(lines, "cp_fmvif: reserved fields in fmv.x.*",
                    "11100EEEEEEERRRRR000RRRRR1010011")
    _emit_raw_words(lines, "cp_fmvfi: reserved fields in fmv.*.x",
                    "11110EEEEEEERRRRR000RRRRR1010011")
    _emit_raw_words(lines, "cp_fli: reserved fields in fli (Zfa)",
                    "11110EEEEEEERRRRR000RRRRR1010011")
    _emit_raw_words(lines, "cp_fmvh: reserved fields in fmvh (Zfa)",
                    "11100EEEEEEERRRRR000RRRRR1010011")
    _emit_raw_words(lines, "cp_fmvp: reserved fields in fmvp (Zfa)",
                    "10110EERRRRRRRRRR000RRRRR1010011")
    _emit_raw_words(lines, "cp_fcvtmodwd: reserved fmt in fcvtmod.w.d",
                    "11000EEEEEEERRRRR001RRRRR1010011")
    _emit_raw_words(lines, "cp_fcvtmodwdfrm: reserved frm in fcvtmod.w.d",
                    "110000101000RRRRREEERRRRR1010011")

    # ── Branch / JALR reserved funct3 ───────────────────────────────────────
    _emit_raw_words(lines, "cp_branch2: reserved funct3=010 in BRANCH",
                    "RRRRRRRRRRRRRRRRR010RRRRR1100011")
    _emit_raw_words(lines, "cp_branch3: reserved funct3=011 in BRANCH",
                    "RRRRRRRRRRRRRRRRR011RRRRR1100011")
    _emit_raw_words(lines, "cp_jalr0: reserved funct3[1:0]!=00 in JALR",
                    "RRRRRRRRRRRRRRRRREE1RRRRR1100111")
    _emit_raw_words(lines, "cp_jalr1: reserved funct3=010 in JALR",
                    "RRRRRRRRRRRRRRRRR010RRRRR1100111")
    _emit_raw_words(lines, "cp_jalr2: reserved funct3=100 in JALR",
                    "RRRRRRRRRRRRRRRRR100RRRRR1100111")
    _emit_raw_words(lines, "cp_jalr3: reserved funct3=110 in JALR",
                    "RRRRRRRRRRRRRRRRR110RRRRR1100111")

    # ── SYSTEM opcode reserved fields ────────────────────────────────────────
    _emit_raw_words(lines, "cp_privileged_f3: reserved funct3 in SYSTEM opcode",
                    "00000000000100000EEE000001110011")
    _emit_raw_words(lines, "cp_privileged_000: reserved rs2/funct7 in funct3=000 SYSTEM",
                    "EEEEEEEEEEEE00000000000001110011",
                    exclusion=[
                        "1XXX11XXXXXX00000000000001110011",  # custom system
                        "00X10000001000000000000001110011",  # mret/sret
                        "00000000000000000000000001110011",  # ecall
                        "00010000010100000000000001110011",  # wfi
                    ])
    _emit_raw_words(lines, "cp_privileged_rd: non-zero rd in privilege instructions",
                    "00000000000000000000EEEEE1110011",
                    exclusion=["00000000000000000000000001110011"])  # exclude ecall
    _emit_raw_words(lines, "cp_privileged_rs2: reserved rs2 in privilege instructions",
                    "000000000000EEEEE000000001110011",
                    exclusion=["00000000000000000000000001110011"])  # exclude ecall

    # ── Reserved FMA / FENCE encodings ───────────────────────────────────────
    _emit_raw_words(lines, "cp_reserved_fma: reserved rm in FMA instructions",
                    "RRRRRRRRRRRRRRRRREEERRRRR100EE11")
    _emit_raw_words(lines, "cp_reserved_fence_fm_tso: reserved FM and TSO fields in FENCE",
                    "EEEE00000000RRRRR000RRRRR0001111")
    _emit_raw_words(lines, "cp_reserved_fence_rs1: reserved rs1 for FENCE.TSO",
                    "00001111111100001000RRRRE0001111")
    _emit_raw_words(lines, "cp_reserved_fence_rd: reserved rd for FENCE.TSO",
                    "000011111111RRRRE000000010001111")

    # ── Upper register sweep (cp_upperreg) ───────────────────────────────────
    lines.append(comment_banner("cp_upperreg", "Upper registers x16-x31 as rd/rs1/rs2"))
    for op_comment, template in [
        ("cp_upperreg_rs1_add",      "0000000000011EEEE000000010110011"),
        ("cp_upperreg_rs2_add",      "00000001EEEE00001000000100110011"),
        ("cp_upperreg_rd_add",       "000000000001000010001EEEE0110011"),
        ("cp_upperreg_rs1_mul",      "0000001000011EEEE000000010110011"),
        ("cp_upperreg_rs2_mul",      "00000011EEEE00001000000100110011"),
        ("cp_upperreg_rd_mul",       "000000100001000010001EEEE0110011"),
        ("cp_upperreg_rs1_fadd-s",   "0000000000011EEEE000000011010011"),
        ("cp_upperreg_rs2_fadd-s",   "00000001EEEE00001000000101010011"),
        ("cp_upperreg_rd_fadd-s",    "000000000001000010001EEEE1010011"),
        ("cp_upperreg_imm_rs1_addi0","0000000000001EEEE000000010010011"),
        ("cp_upperreg_imm_rs1_addi1","1111111111111EEEE000000010010011"),
        ("cp_upperreg_imm_rd_addi0", "000000000000000010001EEEE0010011"),
        ("cp_upperreg_imm_rd_addi1", "111111111111000010001EEEE0010011"),
        ("cp_upperreg_fmv_x_w_rs1",  "1110000000001EEEE000000011010011"),
        ("cp_upperreg_fmv_x_w_rd",   "111000000000000010001EEEE1010011"),
        ("cp_upperreg_fmv_w_x_rs1",  "1111000000001EEEE000000011010011"),
        ("cp_upperreg_fmv_w_x_rd",   "111100000000000010001EEEE1010011"),
    ]:
        _emit_raw_words(lines, op_comment, template)

    # ── Zacas: amocas with odd register IDs ──────────────────────────────────
    _emit_raw_words(lines, "cp_amocas_odd: AMOCAS with odd rd/rs2",
                    "00101RRRRRRRRRRREEEERRRRE0101111")

    # ── Vector vset reserved encodings ───────────────────────────────────────
    for op_comment, template in [
        ("cp_v_vsetvl: reserved vsetvl variants",       "10EEEEERRRRRRRRRR111RRRRR1010111"),
        ("cp_v_vsetvli_sew: vsetvli reserved SEW",      "0000RR1EERRRRRRRR111RRRRR1010111"),
        ("cp_v_vsetvli_res: vsetvli reserved upper",    "EEE0RR0RRRRRRRRRR111RRRRR1010111"),
        ("cp_v_vsetivli_sew: vsetivli reserved SEW",    "1100RR1EERRRRRRRR111RRRRR1010111"),
        ("cp_v_vsetivli_res: vsetivli reserved upper",  "11EERR0RRRRRRRRRR111RRRRR1010111"),
    ]:
        _emit_raw_words(lines, op_comment, template)

    # ── Reserved vector load/store widths ────────────────────────────────────
    for width_tag, load_op, store_op in [
        ("000", "RRR0RRRRRRRRRRRRR000RRRRR0000111", "RRR0RRRRRRRRRRRRR000RRRRR0100111"),
        ("101", "RRR0RRRRRRRRRRRRR101RRRRR0000111", "RRR0RRRRRRRRRRRRR101RRRRR0100111"),
        ("110", "RRR0RRRRRRRRRRRRR110RRRRR0000111", "RRR0RRRRRRRRRRRRR110RRRRR0100111"),
        ("111", "RRR0RRRRRRRRRRRRR111RRRRR0000111", "RRR0RRRRRRRRRRRRR111RRRRR0100111"),
        ("mew1_000", "RRR1RRRRRRRRRRRRR000RRRRR0000111", "RRR1RRRRRRRRRRRRR000RRRRR0100111"),
        ("mew1_101", "RRR1RRRRRRRRRRRRR101RRRRR0000111", "RRR1RRRRRRRRRRRRR101RRRRR0100111"),
        ("mew1_110", "RRR1RRRRRRRRRRRRR110RRRRR0000111", "RRR1RRRRRRRRRRRRR110RRRRR0100111"),
        ("mew1_111", "RRR1RRRRRRRRRRRRR111RRRRR0000111", "RRR1RRRRRRRRRRRRR111RRRRR0100111"),
    ]:
        _emit_raw_words(lines, f"cp_vl_{width_tag}: reserved vector load width {width_tag}", load_op)
        _emit_raw_words(lines, f"cp_vs_{width_tag}: reserved vector store width {width_tag}", store_op)

    # ── Reserved vector load lumop ────────────────────────────────────────────
    for sew_name, width3 in [("8","000"), ("16","101"), ("32","110"), ("64","111")]:
        _emit_raw_words(lines, f"cp_vl_lumop_{sew_name}: reserved lumop for {sew_name}-bit vload",
                        f"RRR0RR1EEEEERRRRR{width3}RRRRR0000111")
        _emit_raw_words(lines, f"cp_vs_lumop_{sew_name}: reserved lumop for {sew_name}-bit vstore",
                        f"RRR0RR1EEEEERRRRR{width3}RRRRR0100111")

    # ── Per-SEW vector arithmetic ─────────────────────────────────────────────
    for sew in ["8", "16", "32", "64"]:
        lines.append(f"\n// Vector instructions with SEW = {sew}")
        lines.append(f"\tvsetivli x0, 1, e{sew}, m1, ta, ma")
        for vop_comment, vtemplate in [
            ("cp_IVV_f6: OPIVV funct6",     "EEEEEEERRRRRRRRRR000RRRRR1010111"),
            ("cp_FVV_f6: OPFVV funct6",     "EEEEEEERRRRRRRRRR001RRRRR1010111"),
            ("cp_MVV_f6: OPMVV funct6",     "EEEEEEERRRRRRRRRR010RRRRR1010111"),
            ("cp_IVI_f6: OPIVI funct6",     "EEEEEEERRRRRRRRRR011RRRRR1010111"),
            ("cp_IVX_f6: OPIVX funct6",     "EEEEEEERRRRRRRRRR100RRRRR1010111"),
            ("cp_FVF_f6: OPFVF funct6",     "EEEEEEERRRRRRRRRR101RRRRR1010111"),
            ("cp_MVX_f6: OPMVX funct6",     "EEEEEEERRRRRRRRRR110RRRRR1010111"),
            ("cp_MVV_VWRXUNARY0",           "010000ERRRRREEEEE010RRRRR1010111"),
            ("cp_MVX_VRXUNARY0",            "010000EEEEEERRRRR110RRRRR1010111"),
            ("cp_MVV_VXUNARY0",             "010010ERRRRREEEEE010RRRRR1010111"),
            ("cp_MVV_VMUNARY0",             "010100ERRRRREEEEE010RRRRR1010111"),
            ("cp_FVV_VWFUNARY0",            "010000ERRRRREEEEE001RRRRR1010111"),
            ("cp_FVF_VRFUNARY0",            "010000EEEEEERRRRR101RRRRR1010111"),
            ("cp_FVV_VFUNARY0",             "010010ERRRRREEEEE001RRRRR1010111"),
            ("cp_FVV_VFUNARY1",             "010011ERRRRREEEEE001RRRRR1010111"),
            ("cp_MVV_vaesvv: vaes.vv",      "101000ERRRRREEEEE010RRRRR1010111"),
            ("cp_MVV_vaesvs: vaes.vs",      "101001ERRRRREEEEE010RRRRR1010111"),
        ]:
            _emit_raw_words(lines, vop_comment, vtemplate)

    return lines


# ─────────────────────────────────────────────────────────────────────────────
# cp_illegal_compressed_instruction — reserved 16-bit encodings
# ─────────────────────────────────────────────────────────────────────────────

def _generate_compressed_instr(test_data: TestData) -> list[str]:
    """Generate cp_illegal_compressed_instruction: all 16-bit quadrant sweeps."""
    covergroup = "SsstrictSm_instr_cg"
    coverpoint = "cp_illegal_compressed_instruction"
    lines: list[str] = []

    lines.append(comment_banner(
        coverpoint,
        "Exhaustive test of all 16-bit instruction encodings in quadrants 00/01/10.\n"
        "Excludes jumps/branches (random targets) and most load/stores (bad address).\n"
        "Includes one sanity-check instruction for each excluded memory operation.",
    ))
    lines.append(f"\t{test_data.add_testcase('compressed_sweep', coverpoint, covergroup)}")

    # Quadrant 00
    _emit_raw_words(lines, "compressed00: all encodings in quadrant 00",
                    "EEEEEEEEEEEEEE00", length=16,
                    exclusion=[
                        "X01XXXXXXXXXXX00",  # c.fld, c.fsd — bad address
                        "X10XXXXXXXXXXX00",  # c.lw, c.sw — bad address
                        "10000XXXXXXXXX00",  # c.lbu, c.lh, c.lhu — bad address
                        "100010XXXXXXXX00",  # c.sb — bad address
                        "100011XXX0XXXX00",  # c.sh — bad address
                    ])

    # Quadrant 01
    _emit_raw_words(lines, "compressed01: all encodings in quadrant 01",
                    "EEEEEEEEEEEEEE01", length=16,
                    exclusion=[
                        "101XXXXXXXXXXX01",  # c.j — random jump
                        "11XXXXXXXXXXXX01",  # c.beqz, c.bnez — random branch
                        "001XXXXXXXXXXX01",  # c.jr (in 01) — random jump
                    ])

    # Quadrant 10
    _emit_raw_words(lines, "compressed10: all encodings in quadrant 10",
                    "EEEEEEEEEEEEEE10", length=16,
                    exclusion=[
                        "1000XXXXX0000010",  # c.jr rs1=0 — illegal (tested separately)
                        "1001XXXXX0000010",  # c.jalr rs1=0 — c.ebreak, tested elsewhere
                        "X01XXXXXXXXXXX10",  # c.fldsp, c.fsdsp — bad address
                        "X10XXXXXXXXXXX10",  # c.swsp, c.lwsp — bad address
                        "1001000000000010",  # c.ebreak — legal, tested in ExceptionsSm
                    ])

    # Sanity-check instructions for excluded memory ops
    lines.extend([
        "",
        "// Sanity-check one encoding for each excluded memory operation",
        "\t.hword 0b0010000000000000  # c.fld (one sample)",
        "\t.hword 0b1010000000000000  # c.fsd (one sample)",
        "\t.hword 0b0100000000000000  # c.lw  (one sample)",
        "\t.hword 0b1100000000000000  # c.sw  (one sample)",
        "\t.hword 0b1000000000000000  # c.lbu (one sample)",
        "\t.hword 0b1000010000000000  # c.lhu (one sample)",
        "\t.hword 0b1000010001000000  # c.lh  (one sample)",
        "\t.hword 0b1000100000000000  # c.sb  (one sample)",
        "\t.hword 0b1000110000000000  # c.sh  (one sample)",
        "\t.hword 0b0100100000000010  # c.lwsp (one sample)",
        "\t.hword 0b1100000000000010  # c.swsp (one sample)",
        "\t.hword 0b0010000000000010  # c.fldsp (one sample)",
        "\t.hword 0b1010000000000010  # c.fsdsp (one sample)",
        "\t.hword 0b1001000000000010  # jalr with rs1=0 (illegal: actually c.ebreak encoding space)",
        "\t.hword 0b1000000000000010  # almost c.jr but rs1=0: illegal instruction",
    ])

    return lines


# ─────────────────────────────────────────────────────────────────────────────
# cp_reserved_frm
# ─────────────────────────────────────────────────────────────────────────────

def _generate_reserved_frm(test_data: TestData) -> list[str]:
    """Generate cp_reserved_frm: reserved FP rounding modes 0-7 with FADD.S."""
    covergroup = "SsstrictSm_instr_cg"
    coverpoint = "cp_reserved_frm"
    lines: list[str] = []

    lines.append(comment_banner(
        coverpoint,
        "Test each FRM value 0–7 with a FADD.S using dynamic rounding (rm=7).\n"
        "FRM=5 and FRM=6 are reserved; FRM=7 with dynamic FRM=5/6/7 raises invalid FP exception.",
    ))

    for frm in range(8):
        lines.extend([
            "",
            f"// cp_reserved_frm: FRM = {frm}",
            f"\t{test_data.add_testcase(f'frm_{frm}', coverpoint, covergroup)}",
            f"\tcsrwi frm, {frm}        # set FRM to {frm}",
            f"\tfadd.s f0, f1, f2       # use dynamic rounding mode (inherits FRM={frm})",
        ])

    return lines


# ─────────────────────────────────────────────────────────────────────────────
# cp_misa_ext_disable
# ─────────────────────────────────────────────────────────────────────────────

def _generate_misa_ext_disable(test_data: TestData) -> list[str]:
    """Generate cp_misa_ext_disable: disable each misa extension bit, run an instruction."""
    covergroup = "SsstrictSm_mcsr_cg"
    coverpoint = "cp_misa_ext_disable"
    lines: list[str] = []

    lines.append(comment_banner(
        coverpoint,
        "For each MUTABLE_MISA_* extension, clear the misa bit, execute a representative\n"
        "instruction (should raise illegal-instruction), then re-enable.\n"
        "Gated by MUTABLE_MISA_* UDB parameters at compile time.\n"
        "Note: Zbc (clmul) is NOT controlled by the B bit — it should still work when B=0.",
    ))

    # misa bit positions: A=0, B=1, C=2, D=3, F=5, H=7, I=8, M=12, Q=16, S=18, U=20, V=21
    ext_tests = [
        ("A", 0,  "amoswap.w x0, x0, (x0)",       "A-ext: AMO instruction with A=0"),
        ("C", 2,  "c.addi x8, 0",                  "C-ext: compressed instruction with C=0"),
        ("D", 3,  ".word 0x02008053",               "D-ext: fadd.d f0,f1,f2 with D=0"),
        ("F", 5,  "fadd.s f0, f1, f2",              "F-ext: fadd.s with F=0"),
        ("M", 12, "mul x1, x2, x3",                "M-ext: mul with M=0"),
        ("V", 21, "vadd.vv v0, v1, v2",             "V-ext: vector add with V=0"),
    ]

    for ext, bit, instr, desc in ext_tests:
        misa_bit = 1 << bit
        lines.extend([
            "",
            f"// {desc}",
            f"#ifdef MUTABLE_MISA_{ext}",
            f"\t{test_data.add_testcase(f'misa_{ext}_disable', coverpoint, covergroup)}",
            f"\tli t0, {misa_bit:#010x}    # misa.{ext} bit",
            f"\tcsrc misa, t0              # disable {ext} extension",
            f"\tnop                        # ensure pipeline sees new misa",
            f"\t{instr}                     # should raise illegal-instruction",
            f"\tnop",
            f"\tcsrs misa, t0              # re-enable {ext} extension",
            "#endif",
        ])

    # B-extension: test Zba, Zbb, Zbs (trap with B=0); Zbc (no trap, Zbc independent)
    lines.extend([
        "",
        "// B-ext: test sub-extensions Zba, Zbb, Zbs trap; Zbc does NOT trap",
        "#ifdef MUTABLE_MISA_B",
        f"\t{test_data.add_testcase('misa_B_zba', coverpoint, covergroup)}",
        "\tli t0, 0x2              # misa.B bit",
        "\tcsrc misa, t0",
        "\tsh3add x1, x2, x3      # Zba instruction — should trap",
        "\tnop",
        f"\t{test_data.add_testcase('misa_B_zbb', coverpoint, covergroup)}",
        "\tandn x1, x2, x3        # Zbb instruction — should trap",
        "\tnop",
        f"\t{test_data.add_testcase('misa_B_zbs', coverpoint, covergroup)}",
        "\tbext x1, x2, x3        # Zbs instruction — should trap",
        "\tnop",
        f"\t{test_data.add_testcase('misa_B_zbc', coverpoint, covergroup)}",
        "\tclmul x1, x2, x3       # Zbc instruction — should NOT trap (independent of B)",
        "\tnop",
        "\tcsrs misa, t0           # re-enable B",
        "#endif",
    ])

    # I-extension disable: run instruction using x16-x31 (should trap with E active)
    lines.extend([
        "",
        "// I-ext: with misa.I=0 (misa.E=1), x16-x31 access should trap",
        "#ifdef MUTABLE_MISA_I",
        f"\t{test_data.add_testcase('misa_I_upperreg', coverpoint, covergroup)}",
        "\tli t0, 0x100            # misa.I bit",
        "\tcsrc misa, t0           # clear I → E activates",
        "\t.word 0x01080833        # add x16, x16, x16 — should trap with E active",
        "\tnop",
        "\tcsrs misa, t0           # re-enable I",
        "#endif",
    ])

    return lines


# ─────────────────────────────────────────────────────────────────────────────
# Main entry point
# ─────────────────────────────────────────────────────────────────────────────

@add_priv_test_generator(
    "SsstrictSm",
    required_extensions=["Sm", "Zicsr"],
    march_extensions=["I", "M", "A", "F", "D", "C", "Zicsr", "Zba", "Zbb", "Zbc", "Zbs", "Zacas",
                      "Zca", "Zcb", "Zcd", "Zcf"],
    extra_defines=[
        "#define RVTEST_PRIV_TEST",
        "#define FAST_TRAP_HANDLER",   # signals test infrastructure to install fast handler
    ],
)
def make_ssstrictsm(test_data: TestData) -> list[str]:
    """
    Generate tests for SsstrictSm — machine-mode strict compliance tests.

    This testsuite verifies that a RISC-V implementation correctly handles:
    1. Every CSR address (read/write/set/clear) from M-mode
    2. Every reserved and illegal 32-bit instruction encoding from M-mode
    3. Every reserved 16-bit compressed instruction encoding from M-mode
    4. Upper register (x16-x31) accesses with the E extension
    5. misa extension disable/enable and resulting illegal instructions
    6. Reserved floating-point rounding modes

    Note: This generates a very large test body (~100k+ instructions).
    The single-TestChunk approach is used; the framework note suggests splitting
    for Ssstrict if needed. See generate/priv.py comment about Ssstrict.
    """
    # Seed RNG for reproducible randomized register choices
    seed(42)

    lines: list[str] = []

    # Install fast trap handler for uncompressed illegal instructions
    # This dramatically reduces runtime for the CSR sweep (2x speedup)
    lines.extend([
        "// Install fast trap handler for uncompressed illegal instructions.",
        "// The normal trap handler costs ~40 instructions per trap; this costs ~5.",
        "// This is safe here because SsstrictSm tests trap recovery, not trap cause details.",
        "LA(t0, trap_handler_fastuncompressedillegalinstr)",
        "CSRW(mtvec, t0)",
        "",
    ])

    lines.extend(_generate_csr_tests_m(test_data))
    lines.extend(_generate_illegal_instr(test_data))
    lines.extend(_generate_compressed_instr(test_data))
    lines.extend(_generate_reserved_frm(test_data))
    lines.extend(_generate_misa_ext_disable(test_data))

    return lines
