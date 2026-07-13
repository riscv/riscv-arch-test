# SPDX-License-Identifier: Apache-2.0
# cp_custom_act3_crypto.py
# Ryan Wolk (rwolk@g.hmc.edu)

import vector_testgen_common as common
from coverpoint_registry import register

# Taken From ACT3 riscv-test-suite/env/test_macros_vector.h
ACT3_TEST_DATA = [
    0x0f1e2d3c, 0x4b5a6978,
    0xf0e1d2c3, 0xb4a59687,
    0x5a5a5a5a, 0x5a5a5a5a,
    0xa5a5a5a5, 0xa5a5a5a5,
    0x10111213, 0x14151617,
    0xf8f9fafb, 0xfcfdfeff,
    0x01112131, 0x41516171,
    0x8f9fafbf, 0xcfdfefff,
    0x00ff00ff, 0x00ff00ff,
    0xff00ff00, 0xff00ff00,
    0x08800880, 0x08800880,
    0x80088008, 0x80088008,
    0x00010203, 0x04050607,
    0x08090a0b, 0x0c0d0e0f,
    0x80818283, 0x84858687,
    0x88898a8b, 0x8c8d8e8f,
    0x00000000, 0x00000000,
    0x00000000, 0x00000000,
    0x00000000, 0x00000000,
    0x00000000, 0x00000000,
    0x00000000, 0x00000000,
    0x00000000, 0x00000000,
    0x00000000, 0x00000000,
    0x00000000, 0x00000000,
    0xffffffff, 0xffffffff,
    0xffffffff, 0xffffffff,
    0xffffffff, 0xffffffff,
    0xffffffff, 0xffffffff,
    0xffffffff, 0xffffffff,
    0xffffffff, 0xffffffff,
    0xffffffff, 0xffffffff,
    0xffffffff, 0xffffffff,
]

# Taken From ACT3 riscv-test-suite/rv32i_m/Zvk/src/vaesdf.vs-01.S
# All tests use the same values in this suite
ACT3_TEST_OFFSETS = [
    (0*4, 0*4),
    (1*4, 0*4),
    (2*4, 2*4),
    (0*4, 0*4),
    (2*4, 3*4),
    (2*4, 3*4),
    (2*4, 3*4),
    (2*4, 3*4),
    (0*4, 4*4),
    (4*4, 0*4),
    (0*4, 0*4),
    (0*4, 11*4),
    (2*4, 9*4),
    (4*4, 7*4),
    (6*4, 5*4),
    (8*4, 3*4),
    (10*4, 1*4),
]

@register("cp_custom_act3_crypto")
def make(test: str, sew: int):
    for i, (vd_ptr, vs2_ptr) in enumerate(ACT3_TEST_OFFSETS):
        vd_val_ptr = f"act3_crypto_value_{i}_vd"
        vs2_val_ptr = f"act3_crypto_value_{i}_vs2"

        common.registerCustomData(vd_val_ptr, ACT3_TEST_DATA[vd_ptr:vd_ptr+4], 32)
        common.registerCustomData(vs2_val_ptr, ACT3_TEST_DATA[vs2_ptr:vs2_ptr+4], 32)

        description = f"ACT3 Vector Crypto Test {i}"
        cp = f"cp_custom_act3_crypto_{i}"

        instruction_data = common.randomizeVectorInstructionData(test, sew, common.getBaseSuiteTestCount(), lmul=4, vd_val_ptr=vd_val_ptr, vs2_val_ptr=vs2_val_ptr, additional_no_overlap=[['vd', 'vs2']])
        common.writeTest(description, test, cp, instruction_data, sew, lmul=4, vl=4, egs=4)
        common.incrementBasetestCount()
