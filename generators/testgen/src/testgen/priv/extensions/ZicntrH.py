##################################
# ZicntrH.py
#
# ZicntrH privileged extension test generator: counter access and htimedelta in HS, VS, U and VU modes.
# David_Harris@hmc.edu 24 September 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""ZicntrH extension test generator.

The suite boots to HS-mode.  The HS-mode handler takes the illegal- and virtual-instruction traps
from U, VS and VU (hedeleg = 0).
"""

from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.extensions.ZicntrCommon import Counteren, Mode, counteren_walk_tests, htimedelta_tests
from testgen.priv.registry import add_priv_test_generator

_CG = "ZicntrH_cg"

# (coverpoint, mode, CSR walked, mcounteren, hcounteren, scounteren)
_WALKS: list[tuple[str, Mode, str, Counteren | None, Counteren | None, Counteren | None]] = [
    ("cp_scounteren_access_hs", "S", "scounteren", "ones", "zeros", None),
    ("cp_mcounteren_access_vs", "VS", "mcounteren", None, "ones", "zeros"),
    ("cp_hcounteren_access_vs", "VS", "hcounteren", "ones", None, "zeros"),
    ("cp_scounteren_access_u", "U", "scounteren", "ones", "zeros", None),
    ("cp_hcounteren_access_vu", "VU", "hcounteren", "ones", None, "ones"),
    ("cp_scounteren_access_vu", "VU", "scounteren", "ones", "ones", None),
]


@add_priv_test_generator(
    "ZicntrH",
    required_extensions=["H", "Zicntr"],
    extra_defines=["#define BOOT_TO_SMODE"],
    # VS and VU traps need the visible trap handler
    params=["TIME_CSR_IMPLEMENTED: true"],
)
def make_zicntrh(test_data: TestData) -> list[TestChunk]:
    """Generate tests for ZicntrH coverpoints."""
    test_chunks: list[TestChunk] = []
    for coverpoint, mode, csr, mcounteren, hcounteren, scounteren in _WALKS:
        presets = ", ".join(
            f"{name} = all {setting}"
            for name, setting in (("mcounteren", mcounteren), ("hcounteren", hcounteren), ("scounteren", scounteren))
            if setting
        )
        tc = test_data.new_test_chunk(test_chunks)
        tc.code.extend(
            [
                *([f"RVTEST_TSBI_GOTO_{mode}MODE"] if mode != "S" else []),
                *counteren_walk_tests(
                    test_data,
                    _CG,
                    coverpoint,
                    f"Write walking 1s and 0s to {csr} with {presets}.  Read from corresponding counter and\n"
                    f"counterh in {'HS' if mode == 'S' else mode}-mode",
                    csrs=[csr],
                    mode=mode,
                    mcounteren=mcounteren,
                    hcounteren=hcounteren,
                    scounteren=scounteren,
                ),
                *(["RVTEST_TSBI_GOTO_SMODE"] if mode != "S" else []),
            ]
        )

    tc = test_data.new_test_chunk(test_chunks)
    ones_reg = test_data.int_regs.get_register()
    tc.code.extend(
        [
            "RVTEST_TSBI_CSR_WRITE(CSR_MCOUNTEREN, -1)",
            f"LI(x{ones_reg}, -1)",
            f"csrw hcounteren, x{ones_reg}",
            f"csrw scounteren, x{ones_reg}",
        ]
    )
    test_data.int_regs.return_register(ones_reg)
    modes: tuple[Mode, ...] = ("S", "VS", "U", "VU")
    for mode in modes:
        tc.code.extend(htimedelta_tests(test_data, _CG, mode))
    test_chunks.append(test_data.end_test_chunk())
    return test_chunks
