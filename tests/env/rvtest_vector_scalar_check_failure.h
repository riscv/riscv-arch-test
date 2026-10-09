// rvtest_vector_scalar_check_failure.h
// SPDX-License-Identifier: Apache-2.0
// -----------
// Failure reporting for scalar self-checking vector tests (RVTEST_VEC_SCALAR_CHECK).
// Included by riscv_arch_test.h after rvtest_failure_code.h, whose register names
// (DEFAULT_LINK_REG, DEFAULT_TEMP_REG) this code uses. The hooks in rvtest_failure_code.h
// invoke these macros in place of code that uses other vector instructions.

#ifndef RVTEST_VECTOR_SCALAR_CHECK_FAILURE_H
#define RVTEST_VECTOR_SCALAR_CHECK_FAILURE_H

// Stores v0-v31 to the buffer at x6 with vse8.v at VLMAX instead of vs1r.v. Clobbers x6 and x7.
.macro RVTEST_VSC_SAVE_VREGS
        vsetvli x7, x0, e8, m1, ta, ma     # vse8.v at VLMAX stores the whole register
        vse8.v v0, (x6)
        addi x6, x6, VLEN_BYTES
        vse8.v v1, (x6)
        addi x6, x6, VLEN_BYTES
        vse8.v v2, (x6)
        addi x6, x6, VLEN_BYTES
        vse8.v v3, (x6)
        addi x6, x6, VLEN_BYTES
        vse8.v v4, (x6)
        addi x6, x6, VLEN_BYTES
        vse8.v v5, (x6)
        addi x6, x6, VLEN_BYTES
        vse8.v v6, (x6)
        addi x6, x6, VLEN_BYTES
        vse8.v v7, (x6)
        addi x6, x6, VLEN_BYTES
        vse8.v v8, (x6)
        addi x6, x6, VLEN_BYTES
        vse8.v v9, (x6)
        addi x6, x6, VLEN_BYTES
        vse8.v v10, (x6)
        addi x6, x6, VLEN_BYTES
        vse8.v v11, (x6)
        addi x6, x6, VLEN_BYTES
        vse8.v v12, (x6)
        addi x6, x6, VLEN_BYTES
        vse8.v v13, (x6)
        addi x6, x6, VLEN_BYTES
        vse8.v v14, (x6)
        addi x6, x6, VLEN_BYTES
        vse8.v v15, (x6)
        addi x6, x6, VLEN_BYTES
        vse8.v v16, (x6)
        addi x6, x6, VLEN_BYTES
        vse8.v v17, (x6)
        addi x6, x6, VLEN_BYTES
        vse8.v v18, (x6)
        addi x6, x6, VLEN_BYTES
        vse8.v v19, (x6)
        addi x6, x6, VLEN_BYTES
        vse8.v v20, (x6)
        addi x6, x6, VLEN_BYTES
        vse8.v v21, (x6)
        addi x6, x6, VLEN_BYTES
        vse8.v v22, (x6)
        addi x6, x6, VLEN_BYTES
        vse8.v v23, (x6)
        addi x6, x6, VLEN_BYTES
        vse8.v v24, (x6)
        addi x6, x6, VLEN_BYTES
        vse8.v v25, (x6)
        addi x6, x6, VLEN_BYTES
        vse8.v v26, (x6)
        addi x6, x6, VLEN_BYTES
        vse8.v v27, (x6)
        addi x6, x6, VLEN_BYTES
        vse8.v v28, (x6)
        addi x6, x6, VLEN_BYTES
        vse8.v v29, (x6)
        addi x6, x6, VLEN_BYTES
        vse8.v v30, (x6)
        addi x6, x6, VLEN_BYTES
        vse8.v v31, (x6)
.endm

// Failure entry points (failure_type = 4, region from rvtest_vsc_ctx) and the routine
// that records the mismatch details from rvtest_vsc_ctx for the failure report.
.macro RVTEST_VSC_FAILURE_CODE
    # Scalar vector check failure entry points (failure_type = 4, region from rvtest_vsc_ctx)
    failedtest_vsc_x5_x4:
        la DEFAULT_TEMP_REG, begin_failure_scratch
        SREG DEFAULT_LINK_REG, 40(DEFAULT_TEMP_REG)
        SREG x1, 8(DEFAULT_TEMP_REG)
        li x1, 4
        SREG x1, 0(DEFAULT_TEMP_REG)                  # failure_type = 4 (vector)
        la x1, rvtest_vsc_ctx
        LREG x1, VSC_REGION(x1)                     # vector mismatch region
        j failedtest_saveregs

    failedtest_vsc_x8_x7:
        la x7, begin_failure_scratch
        SREG x8, 64(x7)
        SREG DEFAULT_TEMP_REG, 32(x7)
        SREG DEFAULT_LINK_REG, 40(x7)
        SREG x1, 8(x7)
        li x1, 4
        SREG x1, 0(x7)                                # failure_type = 4 (vector)
        mv DEFAULT_TEMP_REG, x7
        mv DEFAULT_LINK_REG, x8
        la x1, rvtest_vsc_ctx
        LREG x1, VSC_REGION(x1)                     # vector mismatch region
        j failedtest_saveregs

    failedtest_vsc_x14_x13:
        la x13, begin_failure_scratch
        SREG x14, 112(x13)
        SREG DEFAULT_TEMP_REG, 32(x13)
        SREG DEFAULT_LINK_REG, 40(x13)
        SREG x1, 8(x13)
        li x1, 4
        SREG x1, 0(x13)                               # failure_type = 4 (vector)
        mv DEFAULT_TEMP_REG, x13
        mv DEFAULT_LINK_REG, x14
        la x1, rvtest_vsc_ctx
        LREG x1, VSC_REGION(x1)                     # vector mismatch region
        j failedtest_saveregs

    failedtest_saveresults_vector_sc:
        # The scalar check routine records the mismatch details in rvtest_vsc_ctx
        la x6, rvtest_vsc_ctx

        # Extract vd from the dummy instruction after _STR_PTR
    #ifdef UDB_MXLEN_64
        lhu x7, 16(DEFAULT_LINK_REG)
    #else
        lhu x7, 8(DEFAULT_LINK_REG)
    #endif
        srli x7, x7, 7
        andi x7, x7, 31
        la x8, failing_reg
        sw x7, 0(x8)

        LREG x7, VSC_REGION(x6)
        la x8, failing_region
        sw x7, 0(x8)
        LREG x7, VSC_INDEX(x6)
        la x8, failing_index
        sw x7, 0(x8)
        LREG x7, VSC_VL(x6)
        la x8, failing_vl
        SREG x7, 0(x8)
        LREG x7, VSC_VTYPE(x6)
        la x8, failing_vtype
        SREG x7, 0(x8)

        # Element width in bits (a mask bit is reported as one byte)
        LREG x7, VSC_EEWLOG(x6)
        li x8, 8
        sll x8, x8, x7
        la x9, failing_sew_bits
        sw x8, 0(x9)

        lw x7, VSC_EXPB(x6)
        lw x8, VSC_EXPB+4(x6)
        la x9, expected_value
        sw x7, 0(x9)
        sw x8, 4(x9)
        lw x7, VSC_ACTB(x6)
        lw x8, VSC_ACTB+4(x6)
        la x9, failing_value
        sw x7, 0(x9)
        sw x8, 4(x9)

        # failing_mask_vec was filled by the check routine
        j failedtest_saveresults_common
.endm

#endif // RVTEST_VECTOR_SCALAR_CHECK_FAILURE_H
