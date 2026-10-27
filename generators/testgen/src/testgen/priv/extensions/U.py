##################################
# U.py
#
# U user mode privileged extension test generator.
# Also generates the U_F, U_V and U_VF groups, run only when F, Zve32x or Zve32f is also supported.
# Also generates the U_Zicntr group, run only when Zicntr is also supported.
# David_Harris@hmc.edu 1 March 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""U privileged extension test generator."""

from testgen.data.state import TestData
from testgen.data.test_chunk import TestChunk
from testgen.priv.extensions.FCommon import gen_fcsr_tests
from testgen.priv.extensions.PrivCommon import csr_insufficient_priv_tests, csr_ro_write_tests, priv_inst_trap_tests
from testgen.priv.extensions.VCommon import gen_v_tests
from testgen.priv.extensions.VFCommon import gen_vf_tests
from testgen.priv.extensions.ZicntrCommon import (
    counter_inc_inaccessible_tests,
    counteren_walk_tests,
    instret_exception_tests,
    instret_interrupt_tests,
    instret_retire_tests,
)
from testgen.priv.registry import add_priv_test_generator


@add_priv_test_generator(
    "U",
    required_extensions=["U"],
)
def make_u(test_data: TestData) -> list[TestChunk]:
    """Generate tests for U user-mode testsuite."""
    test_chunks: list[TestChunk] = []
    tc = test_data.begin_test_chunk()

    tc.code.extend(
        priv_inst_trap_tests(
            test_data,
            "U_uprivinst_cg",
            "cp_uprivinst",
            "Execute privileged instructions",
            ["ebreak", "mret", "sret"],
        )
    )
    csr_insufficient_priv_tests(
        test_data,
        test_chunks,
        "U_ucsr_cg",
        [range(0x100, 0x400), range(0x500, 0x800), range(0x900, 0xC00), range(0xD00, 0x1000)],
        "ucsr",
        "Attempt to read non-user-mode registers.  Should throw illegal instruction",
    )
    csr_ro_write_tests(test_data, test_chunks, "U_ucsr_cg", [range(0xC00, 0xD00)], "ucsr_ro")

    test_chunks.append(test_data.end_test_chunk())
    return test_chunks


@add_priv_test_generator(
    "U",
    required_extensions=["U", "F"],
    march_extensions=["F", "D", "Zfa"],
)
def make_u_f(test_data: TestData) -> list[TestChunk]:
    """Generate tests for U_F user-mode floating-point testsuite."""
    test_chunks: list[TestChunk] = []
    tc = test_data.begin_test_chunk("F")

    tc.code.extend(gen_fcsr_tests(test_data, "U", "U_F_cg"))

    test_chunks.append(test_data.end_test_chunk())
    return test_chunks


@add_priv_test_generator(
    "U",
    required_extensions=["U", "Zve32x"],
    extra_defines=[
        "#define RVTEST_VECTOR",
        "#define RVTEST_SEW 0",
        "#define VDSEW 0",
    ],
)
def make_u_v(test_data: TestData) -> list[TestChunk]:
    """Generate U_V tests (vector CSRs, vsetvl* behavior, vill, vstart, xstatus.VS from U-mode)."""
    return gen_v_tests(test_data, "U", "U_V_cg")


@add_priv_test_generator(
    "U",
    required_extensions=["U", "Zve32f"],
    extra_defines=[
        "#define RVTEST_VECTOR",
        "#define RVTEST_SEW 0",
        "#define VDSEW 0",
    ],
)
def make_u_vf(test_data: TestData) -> list[TestChunk]:
    """Generate U_VF tests (vector-FP x mstatus.FS state from U-mode)."""
    return gen_vf_tests(test_data, "U", "U_VF_cg")


_ZICNTR_CG = "U_Zicntr_cg"


@add_priv_test_generator(
    "U",
    required_extensions=["U", "Zicntr"],
    march_extensions=["Zicntr", "Zihpm", "Zawrs"],
)
def make_zicntru(test_data: TestData) -> list[TestChunk]:
    """Generate U_Zicntr tests"""
    test_chunks: list[TestChunk] = []
    tc = test_data.begin_test_chunk("Zicntr")
    tc.code.extend(
        counteren_walk_tests(
            test_data,
            _ZICNTR_CG,
            "cp_mcounteren_access_u",
            "If S_SUPPORTED, write scounteren = 1s.  Write walking 1s and 0s to mcounteren.  Read from corresponding counter and counterh in U-mode",
            csrs=["mcounteren"],
            mode="U",
            scounteren="ones",
        )
    )
    tc.code.extend(counter_inc_inaccessible_tests(test_data, _ZICNTR_CG, "U"))
    tc.code.extend(instret_retire_tests(test_data, _ZICNTR_CG, "U"))
    tc.code.extend(instret_exception_tests(test_data, _ZICNTR_CG, "U"))
    tc.code.extend(instret_interrupt_tests(test_data, _ZICNTR_CG, "U"))
    test_chunks.append(test_data.end_test_chunk())
    return test_chunks
