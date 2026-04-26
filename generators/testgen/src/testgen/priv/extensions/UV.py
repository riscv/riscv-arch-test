##################################
# priv/extensions/UV.py
#
# UV user-mode vector CSR test generator.
# Drives the UV_cg covergroup defined in coverpoints/priv/UV_coverage.svh.
# SPDX-License-Identifier: Apache-2.0
##################################

"""UV privileged test generator (vector CSR access from U-mode)."""

from testgen.asm.helpers import comment_banner
from testgen.data.state import TestData
from testgen.priv.registry import add_priv_test_generator

_CG = "UV_cg"

_VEC_CSRS: list[tuple[str, int]] = [
    ("vstart", 0x008),
    ("vxsat", 0x009),
    ("vxrm", 0x00A),
    ("vcsr", 0x00F),
    ("vl", 0xC20),
    ("vtype", 0xC21),
    ("vlenb", 0xC22),
]


def _gen_uvcsr_access(test_data: TestData, temp_reg: int, dest_reg: int) -> list[str]:
    """csrrc all-1s, csrrw 0, csrrw -1, csrrs all-1s, csrr per CSR (in U-mode)."""
    coverpoint = "cp_uvcsr_access"
    lines = [comment_banner(coverpoint, "Vector CSR access patterns from U-mode (should trap)")]
    for name, _addr in _VEC_CSRS:
        for tag, op_li, asm in (
            ("csrrc_all", -1, f"CSRC({name}, x{temp_reg})"),
            ("csrrw0", 0, f"CSRW({name}, x{temp_reg})"),
            ("csrrw1", -1, f"CSRW({name}, x{temp_reg})"),
            ("csrrs_all", -1, f"CSRS({name}, x{temp_reg})"),
            ("csrr", 0, f"CSRR(x{dest_reg}, {name})"),
        ):
            lines.extend(
                [
                    test_data.add_testcase(f"{name}_{tag}", coverpoint, _CG),
                    f"LI(x{temp_reg}, {op_li})",
                    f"{asm}  # U-mode access to {name}",
                    "nop",
                ]
            )
    return lines


def _gen_uvcsrwalk(test_data: TestData, temp_reg: int) -> list[str]:
    """Walking-1s csrrs and csrrc per writable bit (in U-mode)."""
    coverpoint = "cp_uvcsrwalk"
    lines = [comment_banner(coverpoint, "Walking-1s csrrs/csrrc on each vector CSR from U-mode")]
    for name, _addr in _VEC_CSRS:
        lines.append(f"\n# walking-1s for {name}")
        # 32 bits always; 32-63 only on RV64
        for op, opname in (("CSRS", "csrrs"), ("CSRC", "csrrc")):
            lines.append(f"LI(x{temp_reg}, 1)")
            for i in range(32):
                lines.extend(
                    [
                        test_data.add_testcase(f"{name}_{opname}_bit{i}", coverpoint, _CG),
                        f"{op}({name}, x{temp_reg})",
                        f"slli x{temp_reg}, x{temp_reg}, 1",
                    ]
                )
            lines.append("#if __riscv_xlen == 64")
            for i in range(32, 64):
                lines.extend(
                    [
                        test_data.add_testcase(f"{name}_{opname}_bit{i}", coverpoint, _CG),
                        f"{op}({name}, x{temp_reg})",
                        f"slli x{temp_reg}, x{temp_reg}, 1",
                    ]
                )
            lines.append("#endif")
    return lines


@add_priv_test_generator(
    "UV",
    required_extensions=["Sm", "U", "I", "M", "V", "Zicsr"],
    march_extensions=["I", "M", "V", "Zicsr"],
    extra_defines=[
        "#define RVTEST_VECTOR",
        "#define RVTEST_SEW 0",
        "#define VDSEW 0",
    ],
)
def make_uv(test_data: TestData) -> list[str]:
    """Generate UV tests (U-mode vector CSR access)."""
    temp_reg, dest_reg = test_data.int_regs.get_registers(2)

    lines: list[str] = ["RVTEST_GOTO_LOWER_MODE Umode  # tests run from U-mode\n"]
    lines.extend(_gen_uvcsr_access(test_data, temp_reg, dest_reg))
    lines.extend(_gen_uvcsrwalk(test_data, temp_reg))

    test_data.int_regs.return_registers([temp_reg, dest_reg])
    return lines
