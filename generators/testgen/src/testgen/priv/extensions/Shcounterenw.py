##################################
# Shcounterenw.py
#
# Shcounterenw extension test generator: hcounteren bits are writable for implemented hpmcounters.
# David_Harris@hmc.edu 24 September 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""Shcounterenw extension test generator: hcounteren bits are writable for implemented hpmcounters."""

from testgen.asm.csr import gen_csr_read_sigupd
from testgen.asm.helpers import comment_banner, write_sigupd
from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.registry import add_priv_test_generator

_CG = "Shcounterenw_cg"
coverpoint = "cp_shcounterenw"


@add_priv_test_generator(
    "Shcounterenw",
    required_extensions=["H", "Shcounterenw"],
    extra_defines=["#define BOOT_TO_SMODE"],
    # VS and VU traps need the visible trap handler
    params=["TIME_CSR_IMPLEMENTED: true"],
)
def make_shcounterenw(test_data: TestData) -> list[TestChunk]:
    """Generate tests for Shcounterenw coverpoints."""
    tc = test_data.begin_test_chunk()
    save_reg, val_reg, mask_reg, temp_reg = test_data.int_regs.get_registers(4)
    tc.code.extend(
        [
            comment_banner(
                coverpoint,
                "In HS-mode, write all 0s and all 1s to hcounteren.  Each bit is writable or read-only zero, so all\n"
                "bits read 0 after the 0s.  After the 1s, the bit of each hpmcounter that is not read-only zero\n"
                "(HPM_COUNTER_EN) must read 1; CY, TM, IR and the other HPM bits may be read-only zero",
            ),
            f"csrr x{save_reg}, hcounteren",
            test_data.add_testcase("zeros", coverpoint, _CG),
            "csrw hcounteren, zero",
            gen_csr_read_sigupd(val_reg, ("hcounteren", None), test_data),
            f"LI(x{mask_reg}, 0)",
        ]
    )
    for n in range(3, 32):
        tc.code.extend(
            [
                f"#ifdef UDB_HPM_COUNTER_EN_{n}",
                f"LI(x{temp_reg}, {1 << n:#x})",
                f"or x{mask_reg}, x{mask_reg}, x{temp_reg}",
                "#endif",
            ]
        )
    tc.code.extend(
        [
            f"LI(x{val_reg}, -1)",
            test_data.add_testcase("ones", coverpoint, _CG),
            f"csrw hcounteren, x{val_reg}",
            f"csrr x{val_reg}, hcounteren",
            f"and x{val_reg}, x{val_reg}, x{mask_reg}    # keep the bits of implemented hpmcounters",
            write_sigupd(val_reg, test_data),
            f"csrw hcounteren, x{save_reg}",
        ]
    )
    test_data.int_regs.return_registers([save_reg, val_reg, mask_reg, temp_reg])
    return [test_data.end_test_chunk()]
