##################################
# priv/extensions/SmnpmUSm.py
#
# SmnpmUSm privileged extension test generator.
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

COVERGROUP = "SmnpmUSm_cg"


@add_priv_test_generator(
    "SmnpmUSm",
    required_extensions=["Smnpm"],
    forbidden_extensions=["S"],
    march_extensions=["I", "A", "F", "D", "V", "Zabha", "Zacas", "Zicbom", "Zicbop", "Zicboz"],
    extra_defines=["#define BOOT_TO_MMODE"],
)
def make_smnpmusm(test_data: TestData) -> list[TestChunk]:
    """M-mode half of SmnpmU: MPRV=1 with MPP=U on a hart without S-mode.

    Without S-mode, menvcfg.PMM (Smnpm), governs U-mode, so it decides
    whether the pointer is masked, and mseccfg.PMM does not apply.
    """
    tc = test_data.begin_test_chunk()
    tc.raw_data.extend(mprv_data_section())
    tc.code = [
        *generate_mprv_lower_mode_tests(
            test_data,
            COVERGROUP,
            mpp="PRV_U",
            pmm_csr="menvcfg",
            cp="cp_pm_mprv_mpp_u",
            s_mode=False,
        ),
    ]
    return [test_data.end_test_chunk()]
