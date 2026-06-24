##################################
# vector_helpers.py
#
# rwolk@hmc.edu June 2026
# SPDX-License-Identifier: Apache-2.0
##################################


from testgen.data.config import TestConfig


def get_legal_lmuls(sew: int, test_config: TestConfig) -> list[int]:
    lmulmin = test_config.sew_min / test_config.elen

    legalvlmuls = [0, 1, 2, 3]
    # A given supported fractional LMUL setting must support SEW settings between SEWMIN and LMUL * ELEN
    if (lmulmin <= 0.5) and (sew in [8, 16, 32]):
        legalvlmuls.append(-1)
    if (lmulmin <= 0.25) and (sew in [8, 16]):
        legalvlmuls.append(-2)
    if (lmulmin <= 0.125) and (sew == 8):
        legalvlmuls.append(-3)

    return legalvlmuls
