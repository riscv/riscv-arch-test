##################################
# cp_imm_edges_jal.py
#
# jcarlin@hmc.edu Oct 2025
# SPDX-License-Identifier: Apache-2.0
##################################


"""cp_imm_edges_jal and cp_imm_edges_c_jal coverpoint generators."""

from testgen.coverpoints.coverpoints import add_coverpoint_generator
from testgen.data.test_data import TestData
from testgen.utils.common import return_test_regs, write_sigupd
from testgen.utils.param_generator import generate_random_params


@add_coverpoint_generator("cp_imm_edges_jal", "cp_imm_edges_c_jal")
def make_cp_imm_edges_jal(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[str]:
    """Generate tests covering immediate-edge bins for jal / c.j / c.jal."""

    test_lines: list[str] = []

    # Generate parameters specific to instruction
    if instr_name == "c.jal":
        params = generate_random_params(test_data, instr_type, exclude_regs=[0, 1], rd=1)  # c.jal always uses x1 (ra)
    elif instr_name == "c.j":
        params = generate_random_params(test_data, instr_type, exclude_regs=[0], rd=0)  # c.j always uses x0
    elif instr_name == "jal":
        params = generate_random_params(test_data, instr_type, exclude_regs=[0])
    else:
        raise ValueError(f"Unsupported instruction for cp_imm_edges_jal/cp_imm_edges_c_jal: {instr_name}")
    assert params.temp_reg is not None and params.rd is not None

    # Determine alignment and which instructions to use based on coverpoint variant
    if coverpoint == "cp_imm_edges_jal":
        instr_size = 4
        # jal has 20-bit signed offset, but we only test up to 4096
        max_fwd_align = 12  # 2^12 = 4096
        max_bwd_align = 12  # 2^12 = 4096
        min_align = 2
        li_instr = "li"
    elif coverpoint == "cp_imm_edges_c_jal":
        instr_size = 2
        max_fwd_align = 10  # 2^10 = 1024
        max_bwd_align = 11  # 2^11 = 2048
        min_align = 1
        li_instr = "c.li"
    else:
        raise ValueError(f"Unsupported coverpoint variant for cp_imm_edges_jal/cp_imm_edges_c_jal: {coverpoint}")

    for align in range(min_align, max_fwd_align + 1):
        bin_name = f"b_{1 << align}"

        # For small offsets the inline self-check doesn't fit.
        skip_check = (instr_size == 2 and align <= 1) or (instr_size == 4 and align <= 2)

        test_lines.extend(
            [
                test_data.add_testcase(coverpoint),
                f"# {coverpoint}: forward jump by {1 << align}",
                f"{li_instr} x{params.temp_reg}, 1 # success code"
                if not skip_check
                else "# offset too small, skipping self-check",
                f".align {align}",
                f"{instr_name} {f'x{params.rd},' if instr_name == 'jal' else ''} {coverpoint}_fwd_{bin_name}",
                f"{li_instr} x{params.temp_reg}, -1 # failure code"
                if not skip_check
                else "# offset too small, skipping self-check",
                f".align {align}",
                f"{coverpoint}_fwd_{bin_name}:",
                "# Check jump taken/not-taken",
                write_sigupd(params.temp_reg, test_data)
                if not skip_check
                else "# offset too small, skipping self-check",
                "# Check destination register",
                write_sigupd(params.rd, test_data),
            ]
        )

    for align in range(min_align, max_bwd_align + 1):
        bin_name = f"b_m{1 << align}"

        # For small offsets the inline self-check doesn't fit.
        skip_check = (instr_size == 2 and align <= 1) or (instr_size == 4 and align <= 2)

        test_lines.extend(
            [
                test_data.add_testcase(coverpoint),
                f"# {coverpoint}: backward jump by {1 << align}",
                f"{li_instr} x{params.temp_reg}, 1 # success code"
                if not skip_check
                else "# offset too small, skipping self-check",
                f".align {align + 1}",
                # Jump over the target
                f"{instr_name} {f'x{params.rd},' if instr_name == 'jal' else ''} {coverpoint}_skip_{bin_name}",
                # Align target to 2^align boundary
                f".align {align}",
                f"{coverpoint}_bwd_{bin_name}:",
                # Target label (when backward jump lands here, escape forward to done)
                f"{instr_name} {f'x{params.rd},' if instr_name == 'jal' else ''} {coverpoint}_done_{bin_name}",
                # Skip point
                f"{coverpoint}_skip_{bin_name}:",
                # Align source to 2^(align+1) boundary for backward jump
                f".align {align + 1}",
            ]
        )

        # Backward jump
        if align == 10 and coverpoint == "cp_imm_edges_c_jal":
            # Workaround for GCC expanding c.j/c.jal to full jal for -1024 offset
            if instr_name == "c.j":
                test_lines.append(".insn 0xB101 # backward c.j by -1024; GCC expands to jal")
            else:  # c.jal
                test_lines.append(".insn 0x3101 # backward c.jal by -1024; GCC expands to jal")
        elif align == 11 and coverpoint == "cp_imm_edges_c_jal":
            # Workaround for GCC bug with -2048 offset
            # https://github.com/riscv-collab/riscv-gnu-toolchain/issues/1647
            if instr_name == "c.j":
                test_lines.append(
                    ".insn 0xB001 # backward c.j by -2048; GCC doesn't generate compressed branch properly"
                )
            else:  # c.jal
                test_lines.append(
                    ".insn 0x3001 # backward c.jal by -2048; GCC doesn't generate compressed branch properly"
                )
        else:
            test_lines.append(
                f"{instr_name} {f'x{params.rd},' if instr_name == 'jal' else ''} {coverpoint}_bwd_{bin_name}"
            )

        # Fall-through failure case and done label
        test_lines.extend(
            [
                f"{li_instr} x{params.temp_reg}, -1 # failure code"
                if not skip_check
                else "# offset too small, skipping self-check",
                f"{coverpoint}_done_{bin_name}:",
                "# Check jump taken/not-taken",
                write_sigupd(params.temp_reg, test_data)
                if not skip_check
                else "# offset too small, skipping self-check",
                "# Check destination register",
                write_sigupd(params.rd, test_data),
            ]
        )

    return_test_regs(test_data, params)
    return test_lines
