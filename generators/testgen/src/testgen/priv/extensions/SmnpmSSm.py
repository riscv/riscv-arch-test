##################################
# priv/extensions/SmnpmSSm.py
#
# SmnpmSSm privileged extension test generator.
# Author : Umer Shahid & Ammarah Wakeel email:ammarahwakeel9@gmail.com (UET, JULY 2026)
# SPDX-License-Identifier: Apache-2.0
##################################

from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.extensions.ZpmCommon import (
    generate_mprv_lower_mode_tests,
    mprv_data_section,
)
from testgen.priv.registry import add_priv_test_generator

COVERGROUP = "SmnpmSSm_cg"


@add_priv_test_generator(
    "SmnpmSSm",
    required_extensions=["Smnpm", "S"],
    march_extensions=["I", "A", "F", "D", "V", "Zabha", "Zacas", "Zicbom", "Zicbop", "Zicboz"],
    extra_defines=["#define BOOT_TO_MMODE"],
)
def make_smnpmssm(test_data: TestData) -> list[TestChunk]:
    """M-mode half of SmnpmS: MPRV=1 with MPP=S.

    The probes run in M-mode but take S-mode's effective privilege, so menvcfg.PMM --
    the CSR Smnpm adds -- decides whether the pointer is masked, and mseccfg.PMM does
    not apply. That pairing is why these cases cannot live in the Smmpm suite: a hart
    with Smmpm alone has no menvcfg.PMM to program.
    """
    tc = test_data.begin_test_chunk()
    tc.raw_data.extend(mprv_data_section())
    tc.code = [
        *generate_mprv_lower_mode_tests(
            test_data,
            COVERGROUP,
            mpp="PRV_S",
            pmm_csr="menvcfg",
            cp="cp_pm_mprv_mpp_s",
        ),
    ]
    return [test_data.end_test_chunk()]
