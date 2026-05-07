# failure_code.h
# riscv-arch-test assembly test failure handling code
# Jordan Carlin jcarlin@hmc.edu October 2025
# SPDX-License-Identifier: Apache-2.0
#
# Enhanced trap failure diagnostics added May 2026
# - Trap failure subtypes for per-word mismatch identification
# - xcause human-readable name decoding
# - Full trap signature entry context printing (mode, cause, epc, tval)
# - Extra/missing trap detection with count
# - Interrupt-specific diagnostics (xip, intID)

// Macro to define failure detection code (functions)
// This is instantiated after test code near the end of RVTEST_CODE_END in test_setup.h
.macro RVTEST_FAILURE_CODE
    # Log failure. DEFAULT_LINK_REG (x5) contains return address of jal from the failure and DEFAULT_TEMP_REG (x4) is a vacant temporary register
    failedtest_x5_x4:
        la DEFAULT_TEMP_REG, begin_failure_scratch
        SREG DEFAULT_LINK_REG, 40(DEFAULT_TEMP_REG) # store return address
        SREG x1, 8(DEFAULT_TEMP_REG)                # save x1 early (used for failure_type)
        sw zero, 0(DEFAULT_TEMP_REG)                # failure_type = 0 (integer)
        j failedtest_saveregs

    # Log failure. x8 contains return address of jal from the failure and x7 is a vacant temporary register
    failedtest_x8_x7:
        la x7, begin_failure_scratch
        SREG x8, 64(x7)               # store return address
        SREG DEFAULT_TEMP_REG, 32(x7) # save DEFAULT_TEMP_REG
        SREG DEFAULT_LINK_REG, 40(x7) # save DEFAULT_LINK_REG
        SREG x1, 8(x7)                # save x1 early
        sw zero, 0(x7)                # failure_type = 0 (integer)
        mv DEFAULT_TEMP_REG, x7       # move scratch base into DEFAULT_TEMP_REG
        mv DEFAULT_LINK_REG, x8       # move return address into DEFAULT_LINK_REG
        # now DEFAULT_LINK_REG has the return address of jal from the failure and DEFAULT_TEMP_REG is a vacant temporary register.
        j failedtest_saveregs

    # Log failure. x13 contains return address of jal from the failure and x12 is a vacant temporary register
    failedtest_x13_x12:
        la x12, begin_failure_scratch
        SREG x13, 104(x12)              # store return address
        SREG DEFAULT_TEMP_REG, 32(x12)  # save DEFAULT_TEMP_REG
        SREG DEFAULT_LINK_REG, 40(x12)  # save DEFAULT_LINK_REG
        SREG x1, 8(x12)                 # save x1 early
        sw zero, 0(x12)                 # failure_type = 0 (integer)
        mv DEFAULT_TEMP_REG, x12        # move scratch base into DEFAULT_TEMP_REG
        mv DEFAULT_LINK_REG, x13        # move return address into DEFAULT_LINK_REG
        # now DEFAULT_LINK_REG has the return address of jal from the failure and DEFAULT_TEMP_REG is a vacant temporary register.
        j failedtest_saveregs

    # Log failure. x7 contains return address of jal from the failure and x9 is a vacant temporary register
    # This is the trap handler failure entry point
    failedtest_trap_x7_x9:
        la x9, begin_failure_scratch
        SREG x7, 104(x9)               # store return address
        SREG DEFAULT_TEMP_REG, 32(x9)  # save DEFAULT_TEMP_REG
        SREG DEFAULT_LINK_REG, 40(x9)  # save DEFAULT_LINK_REG
        SREG x1, 8(x9)                 # save x1 early
        li x1, 3
        sw x1, 0(x9)                   # failure_type = 3 (trap handler)
        mv DEFAULT_TEMP_REG, x9        # move scratch base into DEFAULT_TEMP_REG
        mv DEFAULT_LINK_REG, x7        # move return address into DEFAULT_LINK_REG
        j failedtest_saveregs

#ifdef F_SUPPORTED
    # FP failure entry points (failure_type = 1)
    failedtest_fp_x5_x4:
        la DEFAULT_TEMP_REG, begin_failure_scratch
        SREG DEFAULT_LINK_REG, 40(DEFAULT_TEMP_REG)
        SREG x1, 8(DEFAULT_TEMP_REG)
        li x1, 1
        sw x1, 0(DEFAULT_TEMP_REG)                  # failure_type = 1 (fp)
        j failedtest_saveregs

    failedtest_fp_x8_x7:
        la x7, begin_failure_scratch
        SREG x8, 64(x7)
        SREG DEFAULT_TEMP_REG, 32(x7)
        SREG DEFAULT_LINK_REG, 40(x7)
        SREG x1, 8(x7)
        li x1, 1
        sw x1, 0(x7)                                # failure_type = 1 (fp)
        mv DEFAULT_TEMP_REG, x7
        mv DEFAULT_LINK_REG, x8
        j failedtest_saveregs

    failedtest_fp_x13_x12:
        la x12, begin_failure_scratch
        SREG x13, 104(x12)
        SREG DEFAULT_TEMP_REG, 32(x12)
        SREG DEFAULT_LINK_REG, 40(x12)
        SREG x1, 8(x12)
        li x1, 1
        sw x1, 0(x12)                               # failure_type = 1 (fp)
        mv DEFAULT_TEMP_REG, x12
        mv DEFAULT_LINK_REG, x13
        j failedtest_saveregs

    # fflags failure entry points (failure_type = 2)
    failedtest_fflags_x5_x4:
        la DEFAULT_TEMP_REG, begin_failure_scratch
        SREG DEFAULT_LINK_REG, 40(DEFAULT_TEMP_REG)
        SREG x1, 8(DEFAULT_TEMP_REG)
        li x1, 2
        sw x1, 0(DEFAULT_TEMP_REG)                  # failure_type = 2 (fflags)
        j failedtest_saveregs

    failedtest_fflags_x8_x7:
        la x7, begin_failure_scratch
        SREG x8, 64(x7)
        SREG DEFAULT_TEMP_REG, 32(x7)
        SREG DEFAULT_LINK_REG, 40(x7)
        SREG x1, 8(x7)
        li x1, 2
        sw x1, 0(x7)                                # failure_type = 2 (fflags)
        mv DEFAULT_TEMP_REG, x7
        mv DEFAULT_LINK_REG, x8
        j failedtest_saveregs

    failedtest_fflags_x13_x12:
        la x12, begin_failure_scratch
        SREG x13, 104(x12)
        SREG DEFAULT_TEMP_REG, 32(x12)
        SREG DEFAULT_LINK_REG, 40(x12)
        SREG x1, 8(x12)
        li x1, 2
        sw x1, 0(x12)                               # failure_type = 2 (fflags)
        mv DEFAULT_TEMP_REG, x12
        mv DEFAULT_LINK_REG, x13
        j failedtest_saveregs
#endif // F_SUPPORTED

#ifdef RVTEST_VECTOR // *** TODO: change all RVTEST_VECTOR to ZVL32B_SUPPORTED

    # -------- ACTIVE --------
    failedtest_vec_active_x5_x4:
        la DEFAULT_TEMP_REG, begin_failure_scratch
        SREG DEFAULT_LINK_REG, 40(DEFAULT_TEMP_REG)
        SREG x1, 8(DEFAULT_TEMP_REG)
        li x1, 4
        sw x1, 0(DEFAULT_TEMP_REG)                  # failure_type = 4 (vector)
        li x1, 0                                    # vector mismatch region = 0 (active)
        j failedtest_saveregs

    failedtest_vec_active_x8_x7:
        la x7, begin_failure_scratch
        SREG x8, 64(x7)
        SREG DEFAULT_TEMP_REG, 32(x7)
        SREG DEFAULT_LINK_REG, 40(x7)
        SREG x1, 8(x7)
        li x1, 4
        sw x1, 0(x7)                                # failure_type = 4 (vector)
        mv DEFAULT_TEMP_REG, x7
        mv DEFAULT_LINK_REG, x8
        li x1, 0                                    # vector mismatch region = 0 (active)
        j failedtest_saveregs

    failedtest_vec_active_x13_x12:
        la x12, begin_failure_scratch
        SREG x13, 104(x12)
        SREG DEFAULT_TEMP_REG, 32(x12)
        SREG DEFAULT_LINK_REG, 40(x12)
        SREG x1, 8(x12)
        li x1, 4
        sw x1, 0(x12)                               # failure_type = 4 (vector)
        mv DEFAULT_TEMP_REG, x12
        mv DEFAULT_LINK_REG, x13
        li x1, 0                                    # vector mismatch region = 0 (active)
        j failedtest_saveregs

    # -------- TAIL --------
    failedtest_vec_tail_x5_x4:
        la DEFAULT_TEMP_REG, begin_failure_scratch
        SREG DEFAULT_LINK_REG, 40(DEFAULT_TEMP_REG)
        SREG x1, 8(DEFAULT_TEMP_REG)
        li x1, 4
        sw x1, 0(DEFAULT_TEMP_REG)                  # failure_type = 4 (vector)
        li x1, 1                                    # vector mismatch region = 1 (tail)
        j failedtest_saveregs

    failedtest_vec_tail_x8_x7:
        la x7, begin_failure_scratch
        SREG x8, 64(x7)
        SREG DEFAULT_TEMP_REG, 32(x7)
        SREG DEFAULT_LINK_REG, 40(x7)
        SREG x1, 8(x7)
        li x1, 4
        sw x1, 0(x7)                                # failure_type = 4 (vector)
        mv DEFAULT_TEMP_REG, x7
        mv DEFAULT_LINK_REG, x8
        li x1, 1                                    # vector mismatch region = 1 (tail)
        j failedtest_saveregs

    failedtest_vec_tail_x13_x12:
        la x12, begin_failure_scratch
        SREG x13, 104(x12)
        SREG DEFAULT_TEMP_REG, 32(x12)
        SREG DEFAULT_LINK_REG, 40(x12)
        SREG x1, 8(x12)
        li x1, 4
        sw x1, 0(x12)                               # failure_type = 4 (vector)
        mv DEFAULT_TEMP_REG, x12
        mv DEFAULT_LINK_REG, x13
        li x1, 1                                    # vector mismatch region = 1 (tail)
        j failedtest_saveregs

    # -------- MASK --------
    failedtest_vec_mask_x5_x4:
        la DEFAULT_TEMP_REG, begin_failure_scratch
        SREG DEFAULT_LINK_REG, 40(DEFAULT_TEMP_REG)
        SREG x1, 8(DEFAULT_TEMP_REG)
        li x1, 4
        sw x1, 0(DEFAULT_TEMP_REG)                  # failure_type = 4 (vector)
        li x1, 2                                    # vector mismatch region = 2 (mask)
        j failedtest_saveregs

    failedtest_vec_mask_x8_x7:
        la x7, begin_failure_scratch
        SREG x8, 64(x7)
        SREG DEFAULT_TEMP_REG, 32(x7)
        SREG DEFAULT_LINK_REG, 40(x7)
        SREG x1, 8(x7)
        li x1, 4
        sw x1, 0(x7)                                # failure_type = 4 (vector)
        mv DEFAULT_TEMP_REG, x7
        mv DEFAULT_LINK_REG, x8
        li x1, 2                                    # vector mismatch region = 2 (mask)
        j failedtest_saveregs

    failedtest_vec_mask_x13_x12:
        la x12, begin_failure_scratch
        SREG x13, 104(x12)
        SREG DEFAULT_TEMP_REG, 32(x12)
        SREG DEFAULT_LINK_REG, 40(x12)
        SREG x1, 8(x12)
        li x1, 4
        sw x1, 0(x12)                               # failure_type = 4 (vector)
        mv DEFAULT_TEMP_REG, x12
        mv DEFAULT_LINK_REG, x13
        li x1, 2                                    # vector mismatch region = 2 (mask)
        j failedtest_saveregs

    # -------- BASE --------
    failedtest_vec_base_x5_x4:
        la DEFAULT_TEMP_REG, begin_failure_scratch
        SREG DEFAULT_LINK_REG, 40(DEFAULT_TEMP_REG)
        SREG x1, 8(DEFAULT_TEMP_REG)
        li x1, 4
        sw x1, 0(DEFAULT_TEMP_REG)                  # failure_type = 4 (vector)
        li x1, 3                                    # vector mismatch region = 3 (base)
        j failedtest_saveregs

    failedtest_vec_base_x8_x7:
        la x7, begin_failure_scratch
        SREG x8, 64(x7)
        SREG DEFAULT_TEMP_REG, 32(x7)
        SREG DEFAULT_LINK_REG, 40(x7)
        SREG x1, 8(x7)
        li x1, 4
        sw x1, 0(x7)                                # failure_type = 4 (vector)
        mv DEFAULT_TEMP_REG, x7
        mv DEFAULT_LINK_REG, x8
        li x1, 3                                    # vector mismatch region = 3 (base)
        j failedtest_saveregs

    failedtest_vec_base_x13_x12:
        la x12, begin_failure_scratch
        SREG x13, 104(x12)
        SREG DEFAULT_TEMP_REG, 32(x12)
        SREG DEFAULT_LINK_REG, 40(x12)
        SREG x1, 8(x12)
        li x1, 4
        sw x1, 0(x12)                               # failure_type = 4 (vector)
        mv DEFAULT_TEMP_REG, x12
        mv DEFAULT_LINK_REG, x13
        li x1, 3                                    # vector mismatch region = 3 (base)
        j failedtest_saveregs

#endif // RVTEST_VECTOR

    # for the rest of this code, DEFAULT_LINK_REG contains return address of jal from the failure, DEFAULT_TEMP_REG points to scratch space
    failedtest_saveregs:
        # x1 has already been saved by all entry points
        SREG x2, 16(DEFAULT_TEMP_REG)
        SREG x3, 24(DEFAULT_TEMP_REG)
        # SREG x4, 32(DEFAULT_TEMP_REG)
        # SREG x5, 40(DEFAULT_TEMP_REG)
        # x4 and x5 have already been saved if relevant (default temp and link regs)
        SREG x6, 48(DEFAULT_TEMP_REG)
        SREG x7, 56(DEFAULT_TEMP_REG)
        SREG x8, 64(DEFAULT_TEMP_REG)
        SREG x9, 72(DEFAULT_TEMP_REG)
        SREG x10, 80(DEFAULT_TEMP_REG)
        SREG x11, 88(DEFAULT_TEMP_REG)
        SREG x12, 96(DEFAULT_TEMP_REG)
        SREG x13, 104(DEFAULT_TEMP_REG)
        SREG x14, 112(DEFAULT_TEMP_REG)
        SREG x15, 120(DEFAULT_TEMP_REG)
        SREG x16, 128(DEFAULT_TEMP_REG)
        SREG x17, 136(DEFAULT_TEMP_REG)
        SREG x18, 144(DEFAULT_TEMP_REG)
        SREG x19, 152(DEFAULT_TEMP_REG)
        SREG x20, 160(DEFAULT_TEMP_REG)
        SREG x21, 168(DEFAULT_TEMP_REG)
        SREG x22, 176(DEFAULT_TEMP_REG)
        SREG x23, 184(DEFAULT_TEMP_REG)
        SREG x24, 192(DEFAULT_TEMP_REG)
        SREG x25, 200(DEFAULT_TEMP_REG)
        SREG x26, 208(DEFAULT_TEMP_REG)
        SREG x27, 216(DEFAULT_TEMP_REG)
        SREG x28, 224(DEFAULT_TEMP_REG)
        SREG x29, 232(DEFAULT_TEMP_REG)
        SREG x30, 240(DEFAULT_TEMP_REG)
        SREG x31, 248(DEFAULT_TEMP_REG)

    #ifdef RVTEST_VECTOR
        la x6, vecreg_scratch              # vecreg_scratch base address
        vs1r.v v0, (x6)
        addi x6, x6, VLEN_BYTES            # increment by one vector's bytes
        vs1r.v v1, (x6)
        addi x6, x6, VLEN_BYTES
        vs1r.v v2, (x6)
        addi x6, x6, VLEN_BYTES
        vs1r.v v3, (x6)
        addi x6, x6, VLEN_BYTES
        vs1r.v v4, (x6)
        addi x6, x6, VLEN_BYTES
        vs1r.v v5, (x6)
        addi x6, x6, VLEN_BYTES
        vs1r.v v6, (x6)
        addi x6, x6, VLEN_BYTES
        vs1r.v v7, (x6)
        addi x6, x6, VLEN_BYTES
        vs1r.v v8, (x6)
        addi x6, x6, VLEN_BYTES
        vs1r.v v9, (x6)
        addi x6, x6, VLEN_BYTES
        vs1r.v v10, (x6)
        addi x6, x6, VLEN_BYTES
        vs1r.v v11, (x6)
        addi x6, x6, VLEN_BYTES
        vs1r.v v12, (x6)
        addi x6, x6, VLEN_BYTES
        vs1r.v v13, (x6)
        addi x6, x6, VLEN_BYTES
        vs1r.v v14, (x6)
        addi x6, x6, VLEN_BYTES
        vs1r.v v15, (x6)
        addi x6, x6, VLEN_BYTES
        vs1r.v v16, (x6)
        addi x6, x6, VLEN_BYTES
        vs1r.v v17, (x6)
        addi x6, x6, VLEN_BYTES
        vs1r.v v18, (x6)
        addi x6, x6, VLEN_BYTES
        vs1r.v v19, (x6)
        addi x6, x6, VLEN_BYTES
        vs1r.v v20, (x6)
        addi x6, x6, VLEN_BYTES
        vs1r.v v21, (x6)
        addi x6, x6, VLEN_BYTES
        vs1r.v v22, (x6)
        addi x6, x6, VLEN_BYTES
        vs1r.v v23, (x6)
        addi x6, x6, VLEN_BYTES
        vs1r.v v24, (x6)
        addi x6, x6, VLEN_BYTES
        vs1r.v v25, (x6)
        addi x6, x6, VLEN_BYTES
        vs1r.v v26, (x6)
        addi x6, x6, VLEN_BYTES
        vs1r.v v27, (x6)
        addi x6, x6, VLEN_BYTES
        vs1r.v v28, (x6)
        addi x6, x6, VLEN_BYTES
        vs1r.v v29, (x6)
        addi x6, x6, VLEN_BYTES
        vs1r.v v30, (x6)
        addi x6, x6, VLEN_BYTES
        vs1r.v v31, (x6)
    #endif // RVTEST_VECTOR

    failedtest_saveresults:
        # Dispatch based on failure type
        lw x9, failure_type
#if defined(F_SUPPORTED) || defined(ZFINX_SUPPORTED)
        li x10, 1
        beq x9, x10, failedtest_saveresults_fp
        li x10, 2
        beq x9, x10, failedtest_saveresults_fflags
#endif // F_SUPPORTED
#ifdef RVTEST_VECTOR  // *** TODO: change to ZVL32B_SUPPORTED
        li x10, 4
        beq x9, x10, failedtest_saveresults_vector
#endif // RVTEST_VECTOR
        li x10, 3
        beq x9, x10, failedtest_saveresults_trap

    failedtest_saveresults_int:
        # --- INTEGER (type 0): extract info from beq and load instructions ---
        # Reconstruct and extract information from the beq
        # branch might be on 16-byte boundary, so fetch with halfword
        lhu x6, -6(DEFAULT_LINK_REG)     # get upper half of the beq that compared good and bad registers
        lhu x7, -8(DEFAULT_LINK_REG)     # get lower half of the beq
        slli x6, x6, 16     # reassemble beq
        or x6, x6, x7
        # extract rs1 and rs2 from branch (beq format: rs2[24:20] rs1[19:15])
        srli x7, x6, 15
        andi x7, x7, 31     # x7 = rs1 of branch
        srli x8, x6, 20
        andi x8, x8, 31     # x8 = rs2 of branch
        sw x8, 260(DEFAULT_TEMP_REG)      # record id of failing register (rs2 of beq)
        # save bad value from rs2
        slli x6, x8, 3      # rs2 * 8
        add  x6, DEFAULT_TEMP_REG, x6     # address of scratch memory containing rs2
        LREG x6, 0(x6)      # value of rs2 (bad result of operation)
        SREG x6, 272(DEFAULT_TEMP_REG)    # record bad value

        # Reconstruct and extract information from the load
        # The ld loads from an offset of a base register, extract base register and offset
        lhu x6, -10(DEFAULT_LINK_REG)     # get upper half of the ld instruction
        lhu x7, -12(DEFAULT_LINK_REG)     # get lower half of the ld
        slli x6, x6, 16     # reassemble ld
        or x6, x6, x7
        # ld format: imm[11:0] at bits [31:20], rs1 at bits [19:15]
        srai x7, x6, 20     # extract immediate (sign-extended)
        srli x6, x6, 15
        andi x6, x6, 31     # extract rs1 (base register)
        # Load the value of the sigptr register from saved state
        slli x6, x6, 3      # rs1 * 8
        add x6, DEFAULT_TEMP_REG, x6      # address of sigptr register
        LREG x6, 0(x6)      # get sigptr register value
        add x6, x6, x7      # sigptr + offset = address of expected value
        LREG x6, 0(x6)      # load expected value
        SREG x6, 280(DEFAULT_TEMP_REG)    # record expected value
        j failedtest_saveresults_common

  #if defined(F_SUPPORTED) || defined(ZFINX_SUPPORTED)
    failedtest_saveresults_fflags:
        # Re-read fflags for bad value (hasn't changed since failure).
        csrr x6, fflags
        SREG x6, 272(DEFAULT_TEMP_REG)    # failing_value

        # Extract load instruction at -12 for expected value (same approach as integer)
        lhu x6, -10(DEFAULT_LINK_REG)
        lhu x7, -12(DEFAULT_LINK_REG)
        slli x6, x6, 16
        or x6, x6, x7
        srai x7, x6, 20     # extract immediate (sign-extended)
        srli x6, x6, 15
        andi x6, x6, 31     # extract rs1
        slli x6, x6, 3
        add x6, DEFAULT_TEMP_REG, x6
        LREG x6, 0(x6)      # sigptr register value
        add x6, x6, x7      # sigptr + offset
        LREG x6, 0(x6)      # expected value
        SREG x6, 280(DEFAULT_TEMP_REG)    # record expected value
        j failedtest_saveresults_common

    failedtest_saveresults_fp:
        # Extract FP register number from FSREG instruction at -20 from return address
        # FSREG is S-type: imm[11:5] | rs2[24:20] | rs1[19:15] | funct3 | imm[4:0] | opcode
        lhu x6, -18(DEFAULT_LINK_REG)     # upper half of FSREG
        lhu x7, -20(DEFAULT_LINK_REG)     # lower half of FSREG
        slli x6, x6, 16
        or x6, x6, x7
        srli x6, x6, 20
        andi x6, x6, 31                   # FP register number (rs2 of FSREG)
        sw x6, 260(DEFAULT_TEMP_REG)      # record failing_reg

        # Load bad FP value from scratch memory (written by FSREG in the sigupd macro)
        # Use FP_LREG so we read exactly the CONFIG_FLEN bits FSREG stored,
        # zero-extending on RV64+F-only where fsw wrote fewer bytes than LREG reads.
        # See tests/env/utils.h for an explanation of CONFIG_FLEN and TEST_FLEN.
        la x6, scratch
        FP_LREG x7, 0(x6)
        SREG x7, 272(DEFAULT_TEMP_REG)    # failing_value (lower/only)
    #if CONFIG_FLEN > XLEN
        LREG x7, REGWIDTH(x6)
        la x8, failing_value_upper
        SREG x7, 0(x8)                    # failing_value upper half
    #endif

        # Extract sigptr base register from load instruction at -12
        # (use rs1 only, ignore immediate — we load both halves from the base)
        lhu x6, -10(DEFAULT_LINK_REG)
        lhu x7, -12(DEFAULT_LINK_REG)
        slli x6, x6, 16
        or x6, x6, x7
        srli x6, x6, 15
        andi x6, x6, 31                   # rs1 (sigptr register number)
        slli x6, x6, 3
        add x6, DEFAULT_TEMP_REG, x6
        LREG x6, 0(x6)                    # sigptr value (base of FP signature entry)
        # Load full expected FP value from signature
        LREG x7, 0(x6)
        SREG x7, 280(DEFAULT_TEMP_REG)    # expected_value (lower/only)
    #if CONFIG_FLEN > XLEN
        LREG x7, SIG_STRIDE(x6)
        la x8, expected_value_upper
        SREG x7, 0(x8)                    # expected_value upper half
    #endif
        j failedtest_saveresults_common
#endif // F_SUPPORTED

#ifdef RVTEST_VECTOR

    failedtest_saveresults_vector:
        # --------------------------------------------------
        # Save failing instruction, address and vd
        # --------------------------------------------------
    #if __riscv_xlen == 64
        lwu x6, 0(DEFAULT_LINK_REG)      # load lower 32 bits of instruction address
        lw  x7, 4(DEFAULT_LINK_REG)      # load upper 32 bits
        slli x7, x7, 32
        or x6, x6, x7                    # combine into 64-bit value
    #else
        lw x6, 0(DEFAULT_LINK_REG)       # RV32: 4-byte aligned, safe
    #endif

        # Fetch the failing instruction using INSTR_PTR address
        lhu x7, 0(x6)       # get lower half of the failing instruction
        lhu x8, 2(x6)       # 32-bit: fetch upper half
        slli x8, x8, 16
        or x7, x7, x8
        la x8, failing_instruction
        sw x7, 0(x8)                      # record failing instruction (16 or 32 bits)

        # Extract vd (rd field)
        srli x7, x7, 7
        andi x7, x7, 31
        la x8, failing_reg
        sw x7, 0(x8)                      # failing_reg (vd)

        # --------------------------------------------------
        # Load mismatch index & region
        # --------------------------------------------------
        li a1, 3
        beq x1, a1, base_mismatchindex   # if mismatch region is vector base, skip loading mismatch index since it is not valid

        lhu x18, -14(DEFAULT_LINK_REG)   # mv, instruction which copies mismatch index to _TEMP_REG2
        lhu x19, -16(DEFAULT_LINK_REG)
        slli x18, x18, 16
        or   x18, x18, x19

        # Extract rd field, _TEMP_REG2 = mismatch vd index
        srli x19, x18, 7
        andi x19, x19, 31

        slli x19, x19, 3
        add  x19, DEFAULT_TEMP_REG, x19
        LREG x8, 0(x19)                    # where _TEMP_REG2 (mismatch vd index) is stored in scratch

        la x19, failing_index
        sw x8, 0(x19)                      # store mismatch index
        la x19, failing_region
        sw x1, 0(x19)                      # store region
        j vlvtype_store

        base_mismatchindex:
        li x8, 0
        la x19, failing_index
        sw x8, 0(x19)                      # store mismatch index = 0
        la x19, failing_region
        sw x1, 0(x19)                      # store region

        # --------------------------------------------------
        # Store vl/vtype and SEW for later use
        # --------------------------------------------------
        vlvtype_store:
        csrr x10, vl
        csrr x11, vtype

        la x12, failing_vl
        SREG x10, 0(x12)                   # save vl
        la x12, failing_vtype
        SREG x11, 0(x12)                   # save vtype

        // vtype[5:3] = vsew encoding: 0->e8, 1->e16, 2->e32, 3->e64
        lhu x6, -26(DEFAULT_LINK_REG)      # extract from vsetvli or vle##_VD_EEW.v
        lhu x7, -28(DEFAULT_LINK_REG)
        slli x6, x6, 16
        or   x6, x6, x7

        li a1, 3
        beq x1, a1, base_vdeew             # if mismatch region is base, extract VD_EEW from vle##_VD_EEW.v, encoded in width ([12:10])
        srli x16, x6, 23
        andi x16, x16, 7                   # vsew field
        j vsew_mask

        base_vdeew:
        srli x16, x6, 12
        andi x16, x16, 3                   # vector element is encoded as 1XX in width, where XX is EEW of elements

        vsew_mask:
        li   x17, 1
        sll  x17, x17, x16                 # eew_bytes = 1 << vsew
        slli x18 ,x17, 3                   # element size in bits = eew_bytes * 8
        la x19, failing_sew_bits
        sw x18, 0(x19)                     # save sew_bits for later use in expected/actual value extraction

        # --------------------------------------------------
        # Extract expected value
        # --------------------------------------------------
        lhu x6, -10(DEFAULT_LINK_REG)      # LREG, instruction which loads expected value using sigptr
        lhu x7, -12(DEFAULT_LINK_REG)
        slli x6, x6, 16
        or   x6, x6, x7

        srai x7, x6, 20            # imm
        srli x6, x6, 15
        andi x6, x6, 31            # base register

        slli x6, x6, 3
        add  x6, DEFAULT_TEMP_REG, x6
        LREG x6, 0(x6)             # sigptr base

        add  x6, x6, x7            # base + offset

        # add index * element_size (assume SEW known = shift)
        mul  x8, x8, x17           # failing_index * eew_bytes
        add  x6, x6, x8

        # store SEW-length expected value bytewise
        li x14, 0
        li x15, 0
        li x18, 0                         # bit shift counter
        la x19, expected_value

        badvalue_byte_loop:
            bge x15, x17, badvalue_byte_done

            lbu x16, 0(x6)
            sb  x16, 0(x19)

            sll x16, x16, x18
            or  x14, x14, x16

            addi x6, x6, 1
            addi x15, x15, 1
            addi x18, x18, 8
            addi x19, x19, 1

            j badvalue_byte_loop

        badvalue_byte_done:

        # --------------------------------------------------
        # Extract actual value from saved vd
        # --------------------------------------------------
        la x7, failing_reg
        lw x6, 0(x7)                      # vd index
        li   x7, VLEN_BYTES
        mul  x6, x6, x7                   # offset of vd in bytes = vd_index * vlen_bytes
        la x7, vecreg_scratch
        add  x6, x7, x6

        # offset by mismatch index
        slli x8, x8, 0                    # already scaled above
        add  x6, x6, x8

        # store SEW-length expected value bytewise
        li x14, 0
        li x15, 0
        li x18, 0                         # bit shift counter
        la x19, failing_value             # actual value address

        actual_byte_loop:
            bge x15, x17, actual_byte_done

            lbu x16, 0(x6)
            sb  x16, 0(x19)

            sll x16, x16, x18
            or  x14, x14, x16

            addi x6, x6, 1
            addi x15, x15, 1
            addi x18, x18, 8
            addi x19, x19, 1

            j actual_byte_loop

        actual_byte_done:

        # --------------------------------------------------
        # Store failing mask
        # --------------------------------------------------
        li a1, 3
        beq x1, a1, copy_done    # if mismatch region is vector base, skip copying failing mask since it is not valid

        lhu x18, -30(DEFAULT_LINK_REG)    # vmv.v.v, instruction which moves failing mask to _MTMP2/_VTMP
        lhu x19, -32(DEFAULT_LINK_REG)
        slli x18, x18, 16
        or   x18, x18, x19

        # Extract vd (rd field)
        srli x19, x18, 7
        andi x19, x19, 31

        # --- compute src = vecreg_scratch + vd * vlenb ---
        la x6, vecreg_scratch
        li   x7, VLEN_BYTES
        mul  x19, x19, x7                   # offset of vd in bytes = vd_index * vlen_bytes
        add x6, x6, x19                   # offset to where mismatch register is saved in scratch

        # --- dst = failing_mask_vec ---
        la x7, failing_mask_vec

        # --- copy loop (word-wise for RV32) ---
        csrr x8, vlenb          # x8 = bytes per vector register
        mv   x10, x8            # remaining bytes

        copy_loop:
            beqz x10, copy_done

            lw   x11, 0(x6)
            sw   x11, 0(x7)

            addi x6, x6, 4
            addi x7, x7, 4
            addi x10, x10, -4

            j copy_loop

        copy_done:

        j failedtest_saveresults_common

#endif // RVTEST_VECTOR

    //==========================================================================
    // TRAP FAILURE RESULT EXTRACTION (failure_type == 3)
    //
    // When the trap handler's TRAP_SIGUPD detects a mismatch, it calls
    // failedtest_trap_x7_x9 with:
    //   - DEFAULT_LINK_REG pointing after the jal (to embedded pointer data)
    //   - The embedded data contains:
    //       offset 0:               RVTEST_WORD_PTR <label>  (address of failing check)
    //       offset REGWIDTH:        RVTEST_WORD_PTR <string> (failure description string)
    //       offset 2*REGWIDTH:      .word <CSR_XEPC>         (only for some callers)
    //
    // For trap signature offset mismatches (from check_trap_sig_offset in
    // RVTEST_CODE_END), the actual and expected offsets are available as the
    // mismatching signature value vs. the preloaded reference value.
    //
    // Strategy: identify which trap signature word mismatched by examining the
    // failure string pointer. The string encodes both the mode (M/S/H/V) and
    // the field (vect/cause/epc/tval/ip/intID/mtval2/mtinst). We compare
    // against the known string addresses to determine the subtype, then load
    // the corresponding expected/actual values from the trap signature region.
    //==========================================================================

    failedtest_saveresults_trap:
        //--------------------------------------------------------------
        // Load the failure string pointer from the embedded data
        //--------------------------------------------------------------
    #if __riscv_xlen == 64
        lwu x6, REGWIDTH(DEFAULT_LINK_REG)
        lw  x7, REGWIDTH+4(DEFAULT_LINK_REG)
        slli x7, x7, 32
        or x6, x6, x7
    #else
        lw x6, REGWIDTH(DEFAULT_LINK_REG)
    #endif
        la x16, trap_diag_fail_str_ptr
        SREG x6, 0(x16)                            # save for later printing

        //--------------------------------------------------------------
        // Load the address of the failing check (instruction pointer)
        //--------------------------------------------------------------
    #if __riscv_xlen == 64
        lwu x6, 0(DEFAULT_LINK_REG)
        lw  x7, 4(DEFAULT_LINK_REG)
        slli x7, x7, 32
        or x6, x6, x7
    #else
        lw x6, 0(DEFAULT_LINK_REG)
    #endif
        SREG x6, 264(DEFAULT_TEMP_REG)              # store as failing_addr

        //--------------------------------------------------------------
        // Determine trap failure subtype from the failure string address.
        // Compare the string pointer against known string label addresses.
        // This tells us which word of the trap signature mismatched and
        // which privilege mode the trap was being handled in.
        //--------------------------------------------------------------
        la x16, trap_diag_fail_str_ptr
        LREG x6, 0(x16)                             # reload fail string ptr

        // ---- Check for trap_sig_offset_mismatch (from RVTEST_CODE_END) ----
        la x7, trap_sig_offset_mismatch
        beq x6, x7, trap_diag_offset_mismatch

        // ---- Determine mode from string pointer ----
        // Mode is encoded in string name: sv_M*_str, sv_S*_str, sv_H*_str, sv_V*_str
        // and Xclr_Xext_int_str variants
        // We determine mode and field by checking each known string address

        // Default: unknown subtype, just record the string and skip to common print
        li x8, 0                                     # subtype = 0 (unknown)
        la x16, trap_diag_subtype
        sw x8, 0(x16)

        //--- M-mode trap signature field checks ---
        la x7, sv_Mvect_str
        bne x6, x7, 1f
        li x8, 1                                     # subtype: vect+mode word
        li x9, 0                                     # mode: M
        j trap_diag_field_identified
    1:
        la x7, sv_Mcause_str
        bne x6, x7, 1f
        li x8, 2                                     # subtype: xcause
        li x9, 0
        j trap_diag_field_identified
    1:
        la x7, sv_Mepc_str
        bne x6, x7, 1f
        li x8, 3                                     # subtype: xepc
        li x9, 0
        j trap_diag_field_identified
    1:
        la x7, sv_Mtval_str
        bne x6, x7, 1f
        li x8, 4                                     # subtype: xtval
        li x9, 0
        j trap_diag_field_identified
    1:
        la x7, sv_Mip_str
        bne x6, x7, 1f
        li x8, 5                                     # subtype: xip (interrupt)
        li x9, 0
        j trap_diag_field_identified
    1:
        la x7, sv_Mtval2_str
        bne x6, x7, 1f
        li x8, 6                                     # subtype: mtval2
        li x9, 0
        j trap_diag_field_identified
    1:
        la x7, sv_Mtinst_str
        bne x6, x7, 1f
        li x8, 7                                     # subtype: mtinst
        li x9, 0
        j trap_diag_field_identified
    1:

        //--- S-mode trap signature field checks ---
        la x7, sv_Svect_str
        bne x6, x7, 1f
        li x8, 1
        li x9, 1                                     # mode: S
        j trap_diag_field_identified
    1:
        la x7, sv_Scause_str
        bne x6, x7, 1f
        li x8, 2
        li x9, 1
        j trap_diag_field_identified
    1:
        la x7, sv_Sepc_str
        bne x6, x7, 1f
        li x8, 3
        li x9, 1
        j trap_diag_field_identified
    1:
        la x7, sv_Stval_str
        bne x6, x7, 1f
        li x8, 4
        li x9, 1
        j trap_diag_field_identified
    1:
        la x7, sv_Sip_str
        bne x6, x7, 1f
        li x8, 5
        li x9, 1
        j trap_diag_field_identified
    1:

        //--- HS-mode trap signature field checks ---
        la x7, sv_Hvect_str
        bne x6, x7, 1f
        li x8, 1
        li x9, 2                                     # mode: HS
        j trap_diag_field_identified
    1:
        la x7, sv_Hcause_str
        bne x6, x7, 1f
        li x8, 2
        li x9, 2
        j trap_diag_field_identified
    1:
        la x7, sv_Hepc_str
        bne x6, x7, 1f
        li x8, 3
        li x9, 2
        j trap_diag_field_identified
    1:
        la x7, sv_Htval_str
        bne x6, x7, 1f
        li x8, 4
        li x9, 2
        j trap_diag_field_identified
    1:
        la x7, sv_Hip_str
        bne x6, x7, 1f
        li x8, 5
        li x9, 2
        j trap_diag_field_identified
    1:

        //--- VS-mode trap signature field checks ---
        la x7, sv_Vvect_str
        bne x6, x7, 1f
        li x8, 1
        li x9, 3                                     # mode: VS
        j trap_diag_field_identified
    1:
        la x7, sv_Vcause_str
        bne x6, x7, 1f
        li x8, 2
        li x9, 3
        j trap_diag_field_identified
    1:
        la x7, sv_Vepc_str
        bne x6, x7, 1f
        li x8, 3
        li x9, 3
        j trap_diag_field_identified
    1:
        la x7, sv_Vtval_str
        bne x6, x7, 1f
        li x8, 4
        li x9, 3
        j trap_diag_field_identified
    1:
        la x7, sv_Vip_str
        bne x6, x7, 1f
        li x8, 5
        li x9, 3
        j trap_diag_field_identified
    1:

        //--- External interrupt ID mismatch checks ---
        // These use Xclr_Yext_int_str format
        la x7, Mclr_Mext_int_str
        bne x6, x7, 1f
        li x8, 8                                     # subtype: ext intID
        li x9, 0
        j trap_diag_field_identified
    1:
        la x7, Mclr_Sext_int_str
        bne x6, x7, 1f
        li x8, 8
        li x9, 0
        j trap_diag_field_identified
    1:
        la x7, Sclr_Sext_int_str
        bne x6, x7, 1f
        li x8, 8
        li x9, 1
        j trap_diag_field_identified
    1:
        la x7, Hclr_Sext_int_str
        bne x6, x7, 1f
        li x8, 8
        li x9, 2
        j trap_diag_field_identified
    1:
        // Fall through: unknown string, use generic handler
        j trap_diag_generic_report

        //--------------------------------------------------------------
        // TRAP SIGNATURE OFFSET MISMATCH
        // This means the DUT generated a different number of traps
        // than the reference model.
        //--------------------------------------------------------------
    trap_diag_offset_mismatch:
        li x8, 9                                     # subtype: offset mismatch
        la x16, trap_diag_subtype
        sw x8, 0(x16)

        // The actual offset was stored as the failing SIGUPD value.
        // We need to extract it the same way integer failures do:
        // the beq compared actual vs expected, and the ld loaded expected.
        // For trap_sig_offset_mismatch, the value T1 (actual offset) was
        // the value being checked. Extract from the instruction stream.

        // Extract actual value (rs2 of beq = the value being compared)
        lhu x6, -6(DEFAULT_LINK_REG)
        lhu x7, -8(DEFAULT_LINK_REG)
        slli x6, x6, 16
        or x6, x6, x7
        srli x8, x6, 20
        andi x8, x8, 31                             # rs2 of beq
        slli x6, x8, 3
        add x6, DEFAULT_TEMP_REG, x6
        LREG x6, 0(x6)                              # actual offset value
        la x16, trap_diag_actual_offset
        SREG x6, 0(x16)

        // Extract expected value (from ld before beq)
        lhu x6, -10(DEFAULT_LINK_REG)
        lhu x7, -12(DEFAULT_LINK_REG)
        slli x6, x6, 16
        or x6, x6, x7
        srai x7, x6, 20                             # immediate
        srli x6, x6, 15
        andi x6, x6, 31                             # rs1 (base reg)
        slli x6, x6, 3
        add x6, DEFAULT_TEMP_REG, x6
        LREG x6, 0(x6)                              # base register value
        add x6, x6, x7                              # base + offset
        LREG x6, 0(x6)                              # expected offset value
        la x16, trap_diag_expected_offset
        SREG x6, 0(x16)

        j failedtest_saveresults_common

        //--------------------------------------------------------------
        // FIELD IDENTIFIED: subtype in x8, mode in x9
        //--------------------------------------------------------------
    trap_diag_field_identified:
        la x16, trap_diag_subtype
        sw x8, 0(x16)
        la x16, trap_diag_mode
        sw x9, 0(x16)

        // For field mismatches, extract actual and expected the same way
        // as integer failures (from beq rs2 and ld)

        // Actual value (rs2 of beq)
        lhu x6, -6(DEFAULT_LINK_REG)
        lhu x7, -8(DEFAULT_LINK_REG)
        slli x6, x6, 16
        or x6, x6, x7
        srli x14, x6, 20
        andi x14, x14, 31                           # rs2 of beq
        slli x6, x14, 3
        add x6, DEFAULT_TEMP_REG, x6
        LREG x6, 0(x6)
        SREG x6, 272(DEFAULT_TEMP_REG)              # failing_value = actual
        la x16, trap_diag_actual_value
        SREG x6, 0(x16)

        // Expected value (from ld before beq)
        lhu x6, -10(DEFAULT_LINK_REG)
        lhu x7, -12(DEFAULT_LINK_REG)
        slli x6, x6, 16
        or x6, x6, x7
        srai x7, x6, 20
        srli x6, x6, 15
        andi x6, x6, 31
        slli x6, x6, 3
        add x6, DEFAULT_TEMP_REG, x6
        LREG x6, 0(x6)
        add x6, x6, x7
        LREG x6, 0(x6)
        SREG x6, 280(DEFAULT_TEMP_REG)              # expected_value
        la x16, trap_diag_expected_value
        SREG x6, 0(x16)

        j failedtest_saveresults_common

    trap_diag_generic_report:
        // Unknown trap failure string -- fall through to common with subtype 0
        la x16, trap_diag_subtype
        sw zero, 0(x16)
        j failedtest_saveresults_common


    failedtest_saveresults_common:
        # After the jal instruction there are two XLEN-sized pointers: the instruction address and the test string pointer
        # The jal returns to DEFAULT_LINK_REG, which points to the data after jal  (i.e., the first pointer itself)

        # Save failing address (loaded from embedded instruction pointer after jal)
        # Only guaranteed to be 4-byte aligned, so need to load in 4-byte chunks on rv64
    #if __riscv_xlen == 64
        lwu x6, 0(DEFAULT_LINK_REG)      # load lower 32 bits of instruction address
        lw  x7, 4(DEFAULT_LINK_REG)      # load upper 32 bits
        slli x7, x7, 32
        or x6, x6, x7                    # combine into 64-bit value
    #else
        lw x6, 0(DEFAULT_LINK_REG)       # RV32: 4-byte aligned, safe
    #endif
        SREG x6, 264(DEFAULT_TEMP_REG)

        # Fetch the failing instruction using INSTR_PTR address
        # Check bottom 2 bits: if inst[1:0] != 0b11, it's a 16-bit compressed instruction
        lhu x7, 0(x6)       # get lower half of the failing instruction
        andi x8, x7, 3
        li x9, 3
        bne x8, x9, 1f      # compressed: only lower half needed
        lhu x8, 2(x6)       # 32-bit: fetch upper half
        slli x8, x8, 16
        or x7, x7, x8
    1:
        sw x7, 256(DEFAULT_TEMP_REG)      # record failing instruction (16 or 32 bits)

        # Get pointer to failure string (loaded from second embedded pointer after jal)
        # Only guaranteed to be 4-byte aligned, so need to load in 4-byte chunks on rv64
    #if __riscv_xlen == 64
        lwu x6, REGWIDTH(DEFAULT_LINK_REG)       # load lower 32 bits of string pointer
        lw  x7, REGWIDTH+4(DEFAULT_LINK_REG)      # load upper 32 bits
        slli x7, x7, 32
        or x6, x6, x7                     # combine into 64-bit value
    #else
        lw x6, REGWIDTH(DEFAULT_LINK_REG) # RV32: 4-byte aligned, safe
    #endif
        SREG x6, 288(DEFAULT_TEMP_REG)    # save the string pointer

    failedtest_report:
      print_failstr:
        LA(a0, failstr)
        call rvmodel_io_write_str

        # Print test name string
      print_testnamestr:
        LA(a0, testnamestr)
        call rvmodel_io_write_str
      print_failure_test_name_str:
        LREG a0, failure_string_ptr
        call rvmodel_io_write_str
      print_newline_str:
        LA(a0, newlinestr)
        call rvmodel_io_write_str

        # Dispatch to trap-specific reporting if failure_type == 3
        lw a0, failure_type
        li a1, 3
        beq a0, a1, failedtest_report_trap_detailed

        # Print failing instruction (detect 16-bit compressed vs 32-bit)
        LA(a0, inststr)
        call rvmodel_io_write_str
        lw a0, failing_instruction
        li a1, 32            # assume 32-bit instruction
        andi a2, a0, 3
        li a3, 3
        beq a2, a3, 2f
        li a1, 16            # compressed: print as 16-bit
    2:
        jal failedtest_hex_to_str
        LA(a0, ascii_buffer)
        call rvmodel_io_write_str

        # Print failing address (XLEN-bit)
        LA(a0, addrstr)
        call rvmodel_io_write_str
        LREG a0, failing_addr
        li a1, __riscv_xlen
        jal failedtest_hex_to_str
        LA(a0, ascii_buffer)
        call rvmodel_io_write_str

        # Print failing register — "x<N>" for int, "f<N>" for FP, "fflags" for fflags, "v<N>" for vector
        LA(a0, regstr)
        call rvmodel_io_write_str
        lw a0, failure_type
        beqz a0, 1f
        li a1, 3    # Trap handler also uses int regs
        bne a0, a1, failedtest_report_not_intreg
        # Integer: write "x" + decimal register number
        1:
        li a1, 'x'
        LA(a2, ascii_buffer)
        sb a1, 0(a2)
        addi a2, a2, 1
        lw a0, failing_reg
        jal failedtest_dec_to_str
        j failedtest_report_print_regstr
    failedtest_report_not_intreg:
        li a1, 1
        beq a0, a1, failedtest_report_fpreg
        li a1, 4
        beq a0, a1, failedtest_report_vecreg
        # fflags: print "fflags\n"
        LA(a0, fflagsstr)
        call rvmodel_io_write_str
        j failedtest_report_after_reg
    failedtest_report_fpreg:
        # FP: write "f" + decimal register number
        li a1, 'f'
        LA(a2, ascii_buffer)
        sb a1, 0(a2)
        addi a2, a2, 1
        lw a0, failing_reg
        jal failedtest_dec_to_str
        j failedtest_report_print_regstr
    failedtest_report_vecreg:
        li a1, 'v'
        LA(a2, ascii_buffer)
        sb a1, 0(a2)
        addi a2, a2, 1
        lw a0, failing_reg
        jal failedtest_dec_to_str
    failedtest_report_print_regstr:
        LA(a0, ascii_buffer)
        call rvmodel_io_write_str
    failedtest_report_after_reg:
    #ifdef RVTEST_VECTOR
        // ---- Vector-specific fields (only printed for failure_type == 4) ----
        lw a0, failure_type
        li a1, 4
        bne a0, a1, failedtest_report_vec_done

        // Print region (active / tail / mask)
        LA(a0, regionstr)
        call rvmodel_io_write_str
        lw a0, failing_region
        beqz a0, 1f
        li a1, 1
        beq  a0, a1, 2f
        li a1, 2
        beq  a0, a1, 3f
        LA(a0, region_base_str)
        j 4f
    1:  LA(a0, region_active_str)
        j 4f
    2:  LA(a0, region_tail_str)
        j 4f
    3:  LA(a0, region_mask_str)
    4:  call rvmodel_io_write_str

        // Print element index
        LA(a0, indexstr)
        call rvmodel_io_write_str
        lw a0, failing_index
        LA(a2, ascii_buffer)
        jal failedtest_dec_to_str
        LA(a0, ascii_buffer)
        call rvmodel_io_write_str

        // Print vl
        LA(a0, vlstr)
        call rvmodel_io_write_str
        LREG a0, failing_vl
        li a1, __riscv_xlen
        jal failedtest_hex_to_str
        LA(a0, ascii_buffer)
        call rvmodel_io_write_str

        // Print vtype (full hex) then decoded sew/lmul/vta/vma fields
        LA(a0, vtypestr)
        call rvmodel_io_write_str
        LREG a0, failing_vtype
        li a1, __riscv_xlen
        jal failedtest_hex_to_str
        LA(a0, ascii_buffer)
        call rvmodel_io_write_str

        # Print failing value — SEW long
        LA(a0, badvalstr)
        call rvmodel_io_write_str
        lw t0, failing_sew_bits
        li t1, __riscv_xlen
        ble t0, t1, failing_value_normal_print
        # 64-bit case on RV32
        la t0, failing_value   # load address of failing_value
        lw a1, 0(t0)           # lower 32 bits
        lw a0, 4(t0)           # upper 32 bits
        jal failedtest_combined_hex_to_str
        j failing_value_print_done
        failing_value_normal_print:
        LREG a0, failing_value
        lw a1, failing_sew_bits
        jal failedtest_hex_to_str
        failing_value_print_done:
        LA(a0, ascii_buffer)
        call rvmodel_io_write_str

        # Print expected value - SEW long
        LA(a0, expvalstr)
        call rvmodel_io_write_str
        lw t0, failing_sew_bits
        li t1, __riscv_xlen
        ble t0, t1, expected_value_normal_print
        # 64-bit case on RV32
        la t0, expected_value   # load address of expected_value
        lw a1, 0(t0)            # lower 32 bits
        lw a0, 4(t0)            # upper 32 bits
        jal failedtest_combined_hex_to_str
        j expected_value_print_done
        expected_value_normal_print:
        LREG a0, expected_value
        lw a1, failing_sew_bits
        jal failedtest_hex_to_str
        expected_value_print_done:
        LA(a0, ascii_buffer)
        call rvmodel_io_write_str

        lw a0, failing_region
        li a1, 3
        beq a0, a1, failedtest_report_end   # if mismatch region is vector base, skip printing mismatch mask since it is not valid

        // Print mismatch mask (raw bytes of vec_mismatch_mask, VLEN/8 bytes)
        // We print as a hex string by iterating over the bytes.
        // For brevity we print up to VLENMAX_BYTES bytes.
        LA(a0, mismatch_mask_str)
        call rvmodel_io_write_str

        LA(a2, ascii_buffer)     # buffer pointer
        LI(a3, '0')
        sb a3, 0(a2)            # write '0'
        LI(a3, 'x')
        sb a3, 1(a2)            # write 'x'
        sb zero, 2(a2)          # null terminator
        LA(a0, ascii_buffer)
        call rvmodel_io_write_str   # prints "0x"

        li a1, 8                    # print 8 bits (1 byte) at a time
        csrr x31, vlenb
        LA(x30, failing_mask_vec)       # address of mismatch mask
        add x30, x30, x31
        addi x30, x30, -1              # point to end of mask (mismatch_mask + vlenb - 1)

    failedtest_report_mask_loop:
        beqz x31, failedtest_report_mask_done

        LA(a2, ascii_buffer)           # reuse buffer for one rendered byte at a time
        lbu a0, 0(x30)                 # load byte
        li a3, 8                       # a3 = bit count
        jal failedtest_hex_to_str_loop
        sb zero, 0(a2)                 # null terminate after the two hex chars
        LA(a0, ascii_buffer)
        call rvmodel_io_write_str

        addi x30, x30, -1
        addi x31, x31, -1
        j failedtest_report_mask_loop
    failedtest_report_mask_done:
    # Add newline and null terminator
        LA(a2, ascii_buffer)
        LI(a3, 10)                     # '\n'
        sb a3, 0(a2)
        sb zero, 1(a2)                 # null terminator

        LA(a0, ascii_buffer)
        call rvmodel_io_write_str

        j failedtest_report_end

    failedtest_report_vec_done:
    #endif // RVTEST_VECTOR

        # Print failing value — type-aware
        LA(a0, badvalstr)
        call rvmodel_io_write_str
        lw a0, failure_type
        li a1, 1
        bne a0, a1, failedtest_report_badval_not_fp
    #if defined(F_SUPPORTED) && CONFIG_FLEN > XLEN
        # FP with CONFIG_FLEN > XLEN: combined hex "0xUPPER_LOWER"
        LREG a0, failing_value_upper
        LREG a1, failing_value
        jal failedtest_combined_hex_to_str
    #else
        # FP with CONFIG_FLEN <= XLEN (or CONFIG_FLEN not defined): standard hex
        LREG a0, failing_value
        li a1, __riscv_xlen
        jal failedtest_hex_to_str
    #endif
        j failedtest_report_badval_done
    failedtest_report_badval_not_fp:
        # Integer or fflags: standard XLEN-bit hex
        LREG a0, failing_value
        li a1, __riscv_xlen
        jal failedtest_hex_to_str
    failedtest_report_badval_done:
        LA(a0, ascii_buffer)
        call rvmodel_io_write_str

        # Print expected value — type-aware
        LA(a0, expvalstr)
        call rvmodel_io_write_str
        lw a0, failure_type
        li a1, 1
        bne a0, a1, failedtest_report_expval_not_fp
    #if defined(F_SUPPORTED) && CONFIG_FLEN > XLEN
        # FP with CONFIG_FLEN > XLEN: combined hex "0xUPPER_LOWER"
        LREG a0, expected_value_upper
        LREG a1, expected_value
        jal failedtest_combined_hex_to_str
    #else
        # FP with CONFIG_FLEN <= XLEN (or CONFIG_FLEN not defined): standard hex
        LREG a0, expected_value
        li a1, __riscv_xlen
        jal failedtest_hex_to_str
    #endif
        j failedtest_report_expval_done
    failedtest_report_expval_not_fp:
        # Integer or fflags: standard XLEN-bit hex
        LREG a0, expected_value
        li a1, __riscv_xlen
        jal failedtest_hex_to_str
    failedtest_report_expval_done:
        LA(a0, ascii_buffer)
        call rvmodel_io_write_str

        j failedtest_report_end

    //==========================================================================
    // DETAILED TRAP FAILURE REPORTING (failure_type == 3)
    //
    // This section prints comprehensive trap diagnostic information including:
    //   - Which privilege mode was handling the trap
    //   - Which trap signature field mismatched
    //   - Expected vs actual values
    //   - Human-readable xcause name
    //   - For offset mismatches: extra/missing trap count
    //   - Diagnosis of likely root cause
    //==========================================================================

    failedtest_report_trap_detailed:
        // Print trap failure header
        LA(a0, trap_diag_header_str)
        call rvmodel_io_write_str

        // Print the original failure description string
        LA(a0, trap_diag_origstr_label)
        call rvmodel_io_write_str
        la x16, trap_diag_fail_str_ptr
        LREG a0, 0(x16)
        call rvmodel_io_write_str
        LA(a0, newlinestr)
        call rvmodel_io_write_str

        // Load subtype and dispatch
        lw x8, trap_diag_subtype

        // ---- Subtype 9: Trap signature offset mismatch ----
        li x9, 9
        beq x8, x9, trap_report_offset_mismatch

        // ---- Subtype 0: Unknown / generic ----
        beqz x8, trap_report_generic

        // ---- Subtypes 1-8: Field-specific mismatches ----
        j trap_report_field_mismatch

    //--------------------------------------------------------------
    // OFFSET MISMATCH: DUT generated wrong number of traps
    //--------------------------------------------------------------
    trap_report_offset_mismatch:
        // Print "Trap Count Mismatch"
        LA(a0, trap_diag_count_mismatch_str)
        call rvmodel_io_write_str

        // Print expected offset
        LA(a0, trap_diag_expected_offset_str)
        call rvmodel_io_write_str
        LREG a0, trap_diag_expected_offset
        li a1, __riscv_xlen
        jal failedtest_hex_to_str
        LA(a0, ascii_buffer)
        call rvmodel_io_write_str

        // Print actual offset
        LA(a0, trap_diag_actual_offset_str)
        call rvmodel_io_write_str
        LREG a0, trap_diag_actual_offset
        li a1, __riscv_xlen
        jal failedtest_hex_to_str
        LA(a0, ascii_buffer)
        call rvmodel_io_write_str

        // Determine if extra or missing traps
        LREG x6, trap_diag_actual_offset
        LREG x7, trap_diag_expected_offset
        blt x6, x7, trap_report_missing_traps

    trap_report_extra_traps:
        // DUT generated more traps than expected
        LA(a0, trap_diag_extra_traps_str)
        call rvmodel_io_write_str

        // Calculate and print approximate extra trap count
        // Each standard trap entry is 4*REGWIDTH bytes
        LREG x6, trap_diag_actual_offset
        LREG x7, trap_diag_expected_offset
        sub x6, x6, x7                              # extra bytes
        srli x6, x6, 2                               # divide by REGWIDTH (approx entries * 4/REGWIDTH)
        // Print the byte difference as a hex number (exact entry count depends on entry size)
        LA(a0, trap_diag_extra_bytes_str)
        call rvmodel_io_write_str
        LREG x6, trap_diag_actual_offset
        LREG x7, trap_diag_expected_offset
        sub a0, x6, x7
        li a1, __riscv_xlen
        jal failedtest_hex_to_str
        LA(a0, ascii_buffer)
        call rvmodel_io_write_str

        LA(a0, trap_diag_extra_hint_str)
        call rvmodel_io_write_str
        j failedtest_report_end

    trap_report_missing_traps:
        // DUT generated fewer traps than expected
        LA(a0, trap_diag_missing_traps_str)
        call rvmodel_io_write_str

        LA(a0, trap_diag_extra_bytes_str)
        call rvmodel_io_write_str
        LREG x6, trap_diag_expected_offset
        LREG x7, trap_diag_actual_offset
        sub a0, x6, x7
        li a1, __riscv_xlen
        jal failedtest_hex_to_str
        LA(a0, ascii_buffer)
        call rvmodel_io_write_str

        LA(a0, trap_diag_missing_hint_str)
        call rvmodel_io_write_str
        j failedtest_report_end

    //--------------------------------------------------------------
    // FIELD MISMATCH: specific trap signature word differs
    //--------------------------------------------------------------
    trap_report_field_mismatch:
        // Print handler mode
        LA(a0, trap_diag_handler_mode_str)
        call rvmodel_io_write_str
        lw a0, trap_diag_mode
        beqz a0, trap_mode_m
        li a1, 1
        beq a0, a1, trap_mode_s
        li a1, 2
        beq a0, a1, trap_mode_h
        li a1, 3
        beq a0, a1, trap_mode_v
        LA(a0, trap_diag_mode_unknown_str)
        j trap_mode_print
    trap_mode_m:
        LA(a0, trap_diag_mode_m_str)
        j trap_mode_print
    trap_mode_s:
        LA(a0, trap_diag_mode_s_str)
        j trap_mode_print
    trap_mode_h:
        LA(a0, trap_diag_mode_hs_str)
        j trap_mode_print
    trap_mode_v:
        LA(a0, trap_diag_mode_vs_str)
    trap_mode_print:
        call rvmodel_io_write_str

        // Print which field mismatched
        LA(a0, trap_diag_field_str)
        call rvmodel_io_write_str
        lw a0, trap_diag_subtype
        li a1, 1
        beq a0, a1, trap_field_vect
        li a1, 2
        beq a0, a1, trap_field_cause
        li a1, 3
        beq a0, a1, trap_field_epc
        li a1, 4
        beq a0, a1, trap_field_tval
        li a1, 5
        beq a0, a1, trap_field_ip
        li a1, 6
        beq a0, a1, trap_field_tval2
        li a1, 7
        beq a0, a1, trap_field_tinst
        li a1, 8
        beq a0, a1, trap_field_intid
        LA(a0, trap_diag_field_unknown_str)
        j trap_field_print
    trap_field_vect:
        LA(a0, trap_diag_field_vect_str)
        j trap_field_print
    trap_field_cause:
        LA(a0, trap_diag_field_cause_str)
        j trap_field_print
    trap_field_epc:
        LA(a0, trap_diag_field_epc_str)
        j trap_field_print
    trap_field_tval:
        LA(a0, trap_diag_field_tval_str)
        j trap_field_print
    trap_field_ip:
        LA(a0, trap_diag_field_ip_str)
        j trap_field_print
    trap_field_tval2:
        LA(a0, trap_diag_field_tval2_str)
        j trap_field_print
    trap_field_tinst:
        LA(a0, trap_diag_field_tinst_str)
        j trap_field_print
    trap_field_intid:
        LA(a0, trap_diag_field_intid_str)
    trap_field_print:
        call rvmodel_io_write_str

        // Print expected value
        LA(a0, trap_diag_expected_str)
        call rvmodel_io_write_str
        LREG a0, trap_diag_expected_value
        li a1, __riscv_xlen
        jal failedtest_hex_to_str
        LA(a0, ascii_buffer)
        call rvmodel_io_write_str

        // Print actual value
        LA(a0, trap_diag_actual_str)
        call rvmodel_io_write_str
        LREG a0, trap_diag_actual_value
        li a1, __riscv_xlen
        jal failedtest_hex_to_str
        LA(a0, ascii_buffer)
        call rvmodel_io_write_str

        // For xcause mismatches, decode and print the cause name
        lw a0, trap_diag_subtype
        li a1, 2
        bne a0, a1, trap_field_not_cause

        // Print expected cause name
        LA(a0, trap_diag_expected_cause_name_str)
        call rvmodel_io_write_str
        LREG a0, trap_diag_expected_value
        jal trap_cause_to_str
        call rvmodel_io_write_str

        // Print actual cause name
        LA(a0, trap_diag_actual_cause_name_str)
        call rvmodel_io_write_str
        LREG a0, trap_diag_actual_value
        jal trap_cause_to_str
        call rvmodel_io_write_str

    trap_field_not_cause:

        // For xepc mismatches, also print the instruction at the actual xepc
        lw a0, trap_diag_subtype
        li a1, 3
        bne a0, a1, trap_field_not_epc

        // Print current xepc CSR and instruction at that address
        // (if we're in M-mode, we can read mepc directly)
        LA(a0, trap_diag_curr_xepc_str)
        call rvmodel_io_write_str
        csrr a0, mepc
        li a1, __riscv_xlen
        jal failedtest_hex_to_str
        LA(a0, ascii_buffer)
        call rvmodel_io_write_str

    trap_field_not_epc:

        // Print diagnostic hints based on the mismatch type
        lw a0, trap_diag_subtype
        li a1, 1
        bne a0, a1, 1f
        // vect+mode mismatch hints
        LA(a0, trap_diag_hint_vect_str)
        call rvmodel_io_write_str
        j failedtest_report_end
    1:
        li a1, 2
        bne a0, a1, 1f
        // xcause mismatch hints
        LA(a0, trap_diag_hint_cause_str)
        call rvmodel_io_write_str
        j failedtest_report_end
    1:
        li a1, 3
        bne a0, a1, 1f
        // xepc mismatch hints
        LA(a0, trap_diag_hint_epc_str)
        call rvmodel_io_write_str
        j failedtest_report_end
    1:
        li a1, 4
        bne a0, a1, 1f
        // xtval mismatch hints
        LA(a0, trap_diag_hint_tval_str)
        call rvmodel_io_write_str
        j failedtest_report_end
    1:
        li a1, 5
        bne a0, a1, 1f
        // xip mismatch hints
        LA(a0, trap_diag_hint_ip_str)
        call rvmodel_io_write_str
        j failedtest_report_end
    1:
        j failedtest_report_end

    //--------------------------------------------------------------
    // GENERIC: unknown trap failure, print what we can
    //--------------------------------------------------------------
    trap_report_generic:
        LA(a0, trap_diag_generic_str)
        call rvmodel_io_write_str

        // Still print xepc for context
        LA(a0, xepcstr)
        call rvmodel_io_write_str
        csrr a0, mepc
        li a1, __riscv_xlen
        jal failedtest_hex_to_str
        LA(a0, ascii_buffer)
        call rvmodel_io_write_str

        // Print instruction at mepc
        csrr a2, mepc
        LA(a0, xepcinstrstr)
        call rvmodel_io_write_str
        lhu a0, 0(a2)
        li a1, 16
        andi x8, a0, 3
        li x9, 3
        bne x8, x9, 1f
        lhu x8, 2(a2)
        slli x8, x8, 16
        or a0, a0, x8
        li a1, 32
    1:
        jal failedtest_hex_to_str
        LA(a0, ascii_buffer)
        call rvmodel_io_write_str

        j failedtest_report_end


    //==========================================================================
    // TRAP CAUSE NAME DECODER
    //
    // Input: a0 = xcause value
    // Output: a0 = pointer to null-terminated cause name string
    //
    // Handles both exceptions (MSB=0) and interrupts (MSB=1).
    // Returns "Unknown" for unrecognized cause codes.
    //==========================================================================

    trap_cause_to_str:
        bltz a0, trap_cause_interrupt           # MSB set = interrupt

    trap_cause_exception:
        // Exception causes (MSB=0)
        li a1, 24                                # max known exception cause
        bge a0, a1, trap_cause_unknown

        // Index into exception name pointer table
        la a1, trap_excpt_name_tbl
        slli a2, a0, 2                           # cause * 4 (pointer size on RV32)
    #if __riscv_xlen == 64
        slli a2, a0, 3                           # cause * 8 (pointer size on RV64)
    #endif
        add a1, a1, a2
        LREG a0, 0(a1)                           # load string pointer
        ret

    trap_cause_interrupt:
        // Interrupt causes (MSB=1), mask off MSB
        li a1, 1
        slli a1, a1, (XLEN-1)
        xor a0, a0, a1                           # clear MSB to get cause number
        li a1, 16                                # max known interrupt cause
        bge a0, a1, trap_cause_unknown

        la a1, trap_int_name_tbl
        slli a2, a0, 2
    #if __riscv_xlen == 64
        slli a2, a0, 3
    #endif
        add a1, a1, a2
        LREG a0, 0(a1)
        ret

    trap_cause_unknown:
        LA(a0, trap_cause_unknown_str)
        ret


    failedtest_report_end:
        # Print end string
        LA(a0, endstr)
        call rvmodel_io_write_str

    failedtest_terminate:
        call rvmodel_halt_fail


    # Convert hex number to ASCII string and store result in ascii_buffer
    # a0: value to convert
    # a1: number of bits (32 or 64)
    failedtest_hex_to_str:
        LA(a2, ascii_buffer)     # buffer pointer
        LI(a3, '0')
        sb a3, 0(a2)            # write '0'
        LI(a3, 'x')
        sb a3, 1(a2)            # write 'x'
        addi a2, a2, 2          # move past "0x"
        mv a3, a1               # a3 = bit count
    failedtest_hex_to_str_loop:
        addi a3, a3, -4         # move to next nibble
        srl a4, a0, a3          # shift nibble to bottom
        andi a4, a4, 15         # mask to get nibble

        # Convert nibble to ASCII
        LI(a5, 10)
        blt a4, a5, failedtest_hex_to_str_digit
        # It's a letter (A-F)
        addi a4, a4, 87         # 'a' - 10 = 87
        j failedtest_hex_to_str_write
    failedtest_hex_to_str_digit:
        # It's a digit (0-9)
        addi a4, a4, 48         # '0' = 48
    failedtest_hex_to_str_write:
        sb a4, 0(a2)            # write character to buffer
        addi a2, a2, 1          # advance buffer pointer
        bnez a3, failedtest_hex_to_str_loop

        # Add newline and null terminator
        LI(a3, 10)              # '\n'
        sb a3, 0(a2)
        sb zero, 1(a2)          # null terminator

        ret


    # Convert register number (0-31) to decimal string with newline
    # a0: register number (0-31)
    # a2: buffer pointer (writes digits + '\n' + '\0')
    failedtest_dec_to_str:
        li a3, 10
        blt a0, a3, 1f         # single digit
        addi a0, a0, -10
        li a4, '1'
        blt a0, a3, 2f
        addi a0, a0, -10
        li a4, '2'
        blt a0, a3, 2f
        addi a0, a0, -10
        li a4, '3'
    2:  sb a4, 0(a2)            # tens digit
        addi a2, a2, 1
    1:  addi a0, a0, '0'        # ones digit
        sb a0, 0(a2)
        li a3, 10               # '\n'
        sb a3, 1(a2)
        sb zero, 2(a2)          # null terminator
        ret


#if defined(F_SUPPORTED) && CONFIG_FLEN > XLEN || defined(RVTEST_VECTOR)
    # Convert two XLEN-wide values to combined hex string: "0xUPPER_LOWER\n\0"
    # a0: upper XLEN-bit value
    # a1: lower XLEN-bit value
    failedtest_combined_hex_to_str:
        LA(a2, ascii_buffer)     # buffer pointer
        LI(a3, '0')
        sb a3, 0(a2)
        LI(a3, 'x')
        sb a3, 1(a2)
        addi a2, a2, 2          # past "0x"
        # Convert upper half nibbles
        li a3, __riscv_xlen
    failedtest_combined_upper_loop:
        addi a3, a3, -4
        srl a4, a0, a3
        andi a4, a4, 15
        LI(a5, 10)
        blt a4, a5, failedtest_combined_upper_digit
        addi a4, a4, 87         # 'a' - 10
        j failedtest_combined_upper_write
    failedtest_combined_upper_digit:
        addi a4, a4, 48         # '0'
    failedtest_combined_upper_write:
        sb a4, 0(a2)
        addi a2, a2, 1
        bnez a3, failedtest_combined_upper_loop
        # Convert lower half nibbles
        mv a0, a1
        li a3, __riscv_xlen
    failedtest_combined_lower_loop:
        addi a3, a3, -4
        srl a4, a0, a3
        andi a4, a4, 15
        LI(a5, 10)
        blt a4, a5, failedtest_combined_lower_digit
        addi a4, a4, 87         # 'a' - 10
        j failedtest_combined_lower_write
    failedtest_combined_lower_digit:
        addi a4, a4, 48         # '0'
    failedtest_combined_lower_write:
        sb a4, 0(a2)
        addi a2, a2, 1
        bnez a3, failedtest_combined_lower_loop
        # Add newline and null terminator
        LI(a3, 10)              # '\n'
        sb a3, 0(a2)
        sb zero, 1(a2)          # null terminator
        ret
#endif
.endm

// Macro to define failure code data section
// This should be called separately in the RVTEST_DATA_END section to avoid mixing code and data
.macro RVTEST_FAILURE_DATA
    .data
    .align 4
    failure_type:                # 0=int, 1=fp, 2=fflags (reuses x0 slot at offset 0), 3=trap handler, 4=vector
    begin_failure_scratch:
        .fill 64, 4, 0xfeedf00dbaaaaaad
    failing_instruction:
        .fill 1, 4, 0xfeedf00d
    failing_reg:
        .fill 1, 4, 0xbaaaaaad
    failing_addr:
        .fill 2, 4, 0xfeedf00dbaaaaaad
    failing_value:
        .fill 2, 4, 0xfeedf00dbaaaaaad
    expected_value:
        .fill 2, 4, 0xfeedf00dbaaaaaad
    failure_string_ptr:
        .fill 2, 4, 0xfeedf00dbaaaaaad
#if defined(F_SUPPORTED) && CONFIG_FLEN > XLEN
    failing_value_upper:
        .fill 2, 4, 0xfeedf00dbaaaaaad
    expected_value_upper:
        .fill 2, 4, 0xfeedf00dbaaaaaad
#endif
#ifdef RVTEST_VECTOR
    failing_region:                              # 0=active, 1=tail, 2=mask, 3=base
        .fill 1, 4, 0xfeedf00d
    failing_index:                               # element index of first mismatch
        .fill 1, 4, 0xbaaaaaad
    failing_vl:                                  # vl at point of failure
        .fill 2, 4, 0xfeedf00d
    failing_vtype:                               # vtype at point of failure
        .fill 2, 4, 0xbaaaaaad
    failing_sew_bits:                            # SEW in bits
        .fill 1, 4, 0xbaaaaaad
    failing_mask_vec:                            # value of failing mask vector register
        .fill VLEN_WORDS, 4, 0xbaaaaaad
    vecreg_scratch:                              # space to save full vector register contents
        .fill VECREG_REGION_WORDS, 4, 0xfeedf00dbaaaaaad
#endif // RVTEST_VECTOR

    //==========================================================================
    // TRAP DIAGNOSTIC DATA SECTION
    //==========================================================================
    .align 4
    trap_diag_subtype:                           # 0=unknown, 1=vect, 2=cause, 3=epc, 4=tval,
                                                 # 5=xip, 6=mtval2, 7=mtinst, 8=intID, 9=offset
        .word 0
    trap_diag_mode:                              # 0=M, 1=S, 2=HS, 3=VS
        .word 0
    trap_diag_actual_value:                      # actual trap sig value (DUT)
        .fill 2, 4, 0
    trap_diag_expected_value:                    # expected trap sig value (reference)
        .fill 2, 4, 0
    trap_diag_actual_offset:                     # actual trap sig pointer offset
        .fill 2, 4, 0
    trap_diag_expected_offset:                   # expected trap sig pointer offset
        .fill 2, 4, 0
    trap_diag_fail_str_ptr:                      # saved failure string pointer for dispatch
        .fill 2, 4, 0

    ascii_buffer:
        .fill 40, 1, 0          # Buffer for hex string conversion (max "0x" + 16 + 16 + "\n" + null)
    end_failure_scratch:

    //==========================================================================
    // TRAP CAUSE NAME TABLES
    //
    // Pointer tables indexed by cause number.
    // Exception table: cause 0..23 (NUM_SPECD_EXCPTCAUSES)
    // Interrupt table: cause 0..15
    //==========================================================================
    .align REGWIDTH

    trap_excpt_name_tbl:
        RVTEST_WORD_PTR trap_excpt_name_0
        RVTEST_WORD_PTR trap_excpt_name_1
        RVTEST_WORD_PTR trap_excpt_name_2
        RVTEST_WORD_PTR trap_excpt_name_3
        RVTEST_WORD_PTR trap_excpt_name_4
        RVTEST_WORD_PTR trap_excpt_name_5
        RVTEST_WORD_PTR trap_excpt_name_6
        RVTEST_WORD_PTR trap_excpt_name_7
        RVTEST_WORD_PTR trap_excpt_name_8
        RVTEST_WORD_PTR trap_excpt_name_9
        RVTEST_WORD_PTR trap_excpt_name_10
        RVTEST_WORD_PTR trap_excpt_name_11
        RVTEST_WORD_PTR trap_excpt_name_12
        RVTEST_WORD_PTR trap_excpt_name_13
        RVTEST_WORD_PTR trap_excpt_name_14
        RVTEST_WORD_PTR trap_excpt_name_15
        RVTEST_WORD_PTR trap_excpt_name_16
        RVTEST_WORD_PTR trap_excpt_name_17
        RVTEST_WORD_PTR trap_excpt_name_18
        RVTEST_WORD_PTR trap_excpt_name_19
        RVTEST_WORD_PTR trap_excpt_name_20
        RVTEST_WORD_PTR trap_excpt_name_21
        RVTEST_WORD_PTR trap_excpt_name_22
        RVTEST_WORD_PTR trap_excpt_name_23

    trap_int_name_tbl:
        RVTEST_WORD_PTR trap_int_name_0
        RVTEST_WORD_PTR trap_int_name_1
        RVTEST_WORD_PTR trap_int_name_2
        RVTEST_WORD_PTR trap_int_name_3
        RVTEST_WORD_PTR trap_int_name_4
        RVTEST_WORD_PTR trap_int_name_5
        RVTEST_WORD_PTR trap_int_name_6
        RVTEST_WORD_PTR trap_int_name_7
        RVTEST_WORD_PTR trap_int_name_8
        RVTEST_WORD_PTR trap_int_name_9
        RVTEST_WORD_PTR trap_int_name_10
        RVTEST_WORD_PTR trap_int_name_11
        RVTEST_WORD_PTR trap_int_name_12
        RVTEST_WORD_PTR trap_int_name_13
        RVTEST_WORD_PTR trap_int_name_14
        RVTEST_WORD_PTR trap_int_name_15

    //==========================================================================
    // EXCEPTION CAUSE NAME STRINGS
    //==========================================================================
    trap_excpt_name_0:
        .string "Instruction address misaligned\n"
    trap_excpt_name_1:
        .string "Instruction access fault\n"
    trap_excpt_name_2:
        .string "Illegal instruction\n"
    trap_excpt_name_3:
        .string "Breakpoint\n"
    trap_excpt_name_4:
        .string "Load address misaligned\n"
    trap_excpt_name_5:
        .string "Load access fault\n"
    trap_excpt_name_6:
        .string "Store/AMO address misaligned\n"
    trap_excpt_name_7:
        .string "Store/AMO access fault\n"
    trap_excpt_name_8:
        .string "Environment call from U-mode\n"
    trap_excpt_name_9:
        .string "Environment call from S-mode\n"
    trap_excpt_name_10:
        .string "Environment call from VS-mode\n"
    trap_excpt_name_11:
        .string "Environment call from M-mode\n"
    trap_excpt_name_12:
        .string "Instruction page fault\n"
    trap_excpt_name_13:
        .string "Load page fault\n"
    trap_excpt_name_14:
        .string "Reserved (14)\n"
    trap_excpt_name_15:
        .string "Store/AMO page fault\n"
    trap_excpt_name_16:
        .string "Double trap\n"
    trap_excpt_name_17:
        .string "Reserved (17)\n"
    trap_excpt_name_18:
        .string "Software check\n"
    trap_excpt_name_19:
        .string "Hardware error\n"
    trap_excpt_name_20:
        .string "Instruction guest-page fault\n"
    trap_excpt_name_21:
        .string "Load guest-page fault\n"
    trap_excpt_name_22:
        .string "Virtual instruction\n"
    trap_excpt_name_23:
        .string "Store/AMO guest-page fault\n"

    //==========================================================================
    // INTERRUPT CAUSE NAME STRINGS
    //==========================================================================
    trap_int_name_0:
        .string "Reserved interrupt (0)\n"
    trap_int_name_1:
        .string "Supervisor software interrupt\n"
    trap_int_name_2:
        .string "Virtual supervisor software interrupt\n"
    trap_int_name_3:
        .string "Machine software interrupt\n"
    trap_int_name_4:
        .string "Reserved interrupt (4)\n"
    trap_int_name_5:
        .string "Supervisor timer interrupt\n"
    trap_int_name_6:
        .string "Virtual supervisor timer interrupt\n"
    trap_int_name_7:
        .string "Machine timer interrupt\n"
    trap_int_name_8:
        .string "Reserved interrupt (8)\n"
    trap_int_name_9:
        .string "Supervisor external interrupt\n"
    trap_int_name_10:
        .string "Virtual supervisor external interrupt\n"
    trap_int_name_11:
        .string "Machine external interrupt\n"
    trap_int_name_12:
        .string "Supervisor guest external interrupt\n"
    trap_int_name_13:
        .string "Counter overflow interrupt\n"
    trap_int_name_14:
        .string "Reserved interrupt (14)\n"
    trap_int_name_15:
        .string "Reserved interrupt (15)\n"

    trap_cause_unknown_str:
        .string "Unknown/custom cause\n"

    //==========================================================================
    // GENERAL STRINGS (unchanged from original)
    //==========================================================================
    successstr:
        // Sequence of .ascii and .asciz is used to create a multi-part string with a single null terminator
        // clang does not allow implicit string concatenation with .string directives
        // NOTE: the SELFCHECK and non-SELFCHECK branches MUST emit the same number of bytes so
        // that every symbol defined after successstr (including begin_signature) lands at the
        // same address in both the .elf and .sig.elf builds.
        #ifdef RVTEST_SELFCHECK
            .ascii "\nRVCP-SUMMARY: TEST PASSED - Test File \""
        #else
            .ascii "\nRVCP-SUMMARY: TEST SIGRUN - Test File \""
        #endif
        .ascii TEST_FILE
        .asciz "\"\n\n"
    failstr:
        .ascii "\nRVCP-SUMMARY: TEST FAILED - Test File \""
        .ascii TEST_FILE
        .asciz "\"\nRVCP: DEBUG INFORMATION FOLLOWS\n"
    abortstr:
        .string "\"The trap handler aborted the test before normal completion!\"";
    testnamestr:
        .string "RVCP: Test Info: "
    newlinestr:
        .string "\n"
    inststr:
        .string "RVCP: Instruction: "

    // Failure strings for privileged tests
    addrstr:
        .string "RVCP: Approximate address (failure may be slightly after this): "
    xepcstr:
        .string "RVCP: Address of instruction that trapped (XEPC): "
    xepcinstrstr:
        .string "RVCP: Instruction that trapped: "
    trap_sig_offset_mismatch:
        .string "\"Mismatch in trap signature pointer offset! The test likely observed an incorrect number of traps.\"";
    sv_Mvect_str:
        .string "\"Mismatch in trap signature! Trap was being handled in M-Mode.\"";
    sv_Svect_str:
        .string "\"Mismatch in trap signature! Trap was being handled in S-Mode.\"";
    sv_Hvect_str:
        .string "\"Mismatch in trap signature! Trap was being handled in HS-Mode.\"";
    sv_Vvect_str:
        .string "\"Mismatch in trap signature! Trap was being handled in VS-Mode.\"";
    sv_Mcause_str:
        .string "\"Mismatch in mcause value! Trap was being handled in M-Mode.\"";
    sv_Scause_str:
        .string "\"Mismatch in scause value! Trap was being handled in S-Mode.\"";
    sv_Hcause_str:
        .string "\"Mismatch in scause value! Trap was being handled in HS-Mode.\"";
    sv_Vcause_str:
        .string "\"Mismatch in vscause value! Trap was being handled in VS-Mode.\"";
    sv_Mepc_str:
        .string "\"Mismatch in mepc value! Trap was being handled in M-Mode.\"";
    sv_Sepc_str:
        .string "\"Mismatch in sepc value! Trap was being handled in S-Mode.\"";
    sv_Hepc_str:
        .string "\"Mismatch in sepc value! Trap was being handled in HS-Mode.\"";
    sv_Vepc_str:
        .string "\"Mismatch in vsepc value! Trap was being handled in VS-Mode.\"";
    sv_Mtval_str:
        .string "\"Mismatch in mtval value! Trap was being handled in M-Mode.\"";
    sv_Stval_str:
        .string "\"Mismatch in stval value! Trap was being handled in S-Mode.\"";
    sv_Htval_str:
        .string "\"Mismatch in stval value! Trap was being handled in HS-Mode.\"";
    sv_Vtval_str:
        .string "\"Mismatch in vstval value! Trap was being handled in VS-Mode.\"";
    sv_Mtval2_str:
        .string "\"Mismatch in mtval2 value! Trap was being handled in M-Mode.\"";
    sv_Mtinst_str:
        .string "\"Mismatch in mtinst value! Trap was being handled in M-Mode.\"";
    sv_Mip_str:
        .string "\"Mismatch in mip value! Trap was being handled in M-Mode.\"";
    sv_Sip_str:
        .string "\"Mismatch in sip value! Trap was being handled in S-Mode.\"";
    sv_Hip_str:
        .string "\"Mismatch in hip value! Trap was being handled in HS-Mode.\"";
    sv_Vip_str:
        .string "\"Mismatch in vsip value! Trap was being handled in VS-Mode.\"";
    Mclr_Mext_int_str:
        .string "\"Mismatch in machine external interrupt ID! Trap was being handled in M-Mode.\"";
    Mclr_Sext_int_str:
        .string "\"Mismatch in supervisor external interrupt ID! Trap was being handled in M-Mode.\"";
    Mclr_Vext_int_str:
        .string "\"Mismatch in virtual supervisor external interrupt ID! Trap was being handled in M-Mode.\"";
    Sclr_Mext_int_str:
        .string "\"Mismatch in machine external interrupt ID! Trap was being handled in S-Mode.\"";
    Sclr_Sext_int_str:
        .string "\"Mismatch in supervisor external interrupt ID! Trap was being handled in S-Mode.\"";
    Sclr_Vext_int_str:
        .string "\"Mismatch in virtual supervisor external interrupt ID! Trap was being handled in S-Mode.\"";
    Hclr_Mext_int_str:
        .string "\"Mismatch in machine external interrupt ID! Trap was being handled in HS-Mode.\"";
    Hclr_Sext_int_str:
        .string "\"Mismatch in supervisor external interrupt ID! Trap was being handled in HS-Mode.\"";
    Hclr_Vext_int_str:
        .string "\"Mismatch in virtual supervisor external interrupt ID! Trap was being handled in HS-Mode.\"";
    Vclr_Mext_int_str:
        .string "\"Mismatch in machine external interrupt ID! Trap was being handled in VS-Mode.\"";
    Vclr_Sext_int_str:
        .string "\"Mismatch in supervisor external interrupt ID! Trap was being handled in VS-Mode.\"";
    Vclr_Vext_int_str:
        .string "\"Mismatch in virtual supervisor external interrupt ID! Trap was being handled in VS-Mode.\"";
#ifdef RVTEST_VECTOR
    regionstr:
        .string "RVCP: Region: "
    region_active_str:
        .string "ACTIVE\n"
    region_tail_str:
        .string "TAIL\n"
    region_mask_str:
        .string "MASK\n"
    region_base_str:
        .string "BASE\n"
    indexstr:
        .string "RVCP: Element Index: "
    vlstr:
        .string "RVCP: VL: "
    vtypestr:
        .string "RVCP: VTYPE: "
    mismatch_mask_str:
        .string "RVCP: Mismatch Mask (one bit per element, up to VLMAX bits):\n"
#endif
    regstr:
        .string "RVCP: Register: "
    badvalstr:
        .string "RVCP: Bad Value:      "
    expvalstr:
        .string "RVCP: Expected Value: "
    endstr:
        .string "RVCP: END OF DEBUG INFORMATION\n\n"
    fflagsstr:
        .string "fflags\n"
    canary_mismatch:
        .string "Testcase signature canary mismatch!"

    //==========================================================================
    // TRAP DIAGNOSTIC STRINGS
    //==========================================================================
    trap_diag_header_str:
        .string "RVCP: ===== TRAP FAILURE DIAGNOSTICS =====\n"
    trap_diag_origstr_label:
        .string "RVCP: Failure: "
    trap_diag_count_mismatch_str:
        .string "RVCP: TRAP COUNT MISMATCH - DUT generated a different number of traps than the reference model.\n"
    trap_diag_expected_offset_str:
        .string "RVCP: Expected trap signature offset: "
    trap_diag_actual_offset_str:
        .string "RVCP: Actual trap signature offset:   "
    trap_diag_extra_traps_str:
        .string "RVCP: DIAGNOSIS: DUT generated MORE traps than expected.\n"
    trap_diag_missing_traps_str:
        .string "RVCP: DIAGNOSIS: DUT generated FEWER traps than expected (missing traps).\n"
    trap_diag_extra_bytes_str:
        .string "RVCP: Difference in trap signature bytes: "
    trap_diag_extra_hint_str:
        .ascii  "RVCP: HINT: Extra traps may indicate: spurious interrupts, incorrect exception\n"
        .ascii  "RVCP:       delegation, wrong privilege mode at instruction execution, or an\n"
        .asciz  "RVCP:       instruction causing a fault that should not fault on this DUT.\n"
    trap_diag_missing_hint_str:
        .ascii  "RVCP: HINT: Missing traps may indicate: exception not raised when expected,\n"
        .ascii  "RVCP:       incorrect CSR state preventing trap (e.g. xIE disabled), trap\n"
        .asciz  "RVCP:       delegation causing handler in wrong mode, or PMP/page fault missed.\n"

    trap_diag_handler_mode_str:
        .string "RVCP: Trap handler mode: "
    trap_diag_mode_m_str:
        .string "M-mode\n"
    trap_diag_mode_s_str:
        .string "S-mode\n"
    trap_diag_mode_hs_str:
        .string "HS-mode\n"
    trap_diag_mode_vs_str:
        .string "VS-mode\n"
    trap_diag_mode_unknown_str:
        .string "Unknown\n"

    trap_diag_field_str:
        .string "RVCP: Mismatching field: "
    trap_diag_field_vect_str:
        .string "Vector+Mode+Status word (trap signature word 0)\n"
    trap_diag_field_cause_str:
        .string "XCAUSE (trap signature word 1)\n"
    trap_diag_field_epc_str:
        .string "XEPC (trap signature word 2)\n"
    trap_diag_field_tval_str:
        .string "XTVAL (trap signature word 3)\n"
    trap_diag_field_ip_str:
        .string "XIP (trap signature word 2, interrupt)\n"
    trap_diag_field_tval2_str:
        .string "MTVAL2 (trap signature word 4, hypervisor)\n"
    trap_diag_field_tinst_str:
        .string "MTINST (trap signature word 5, hypervisor)\n"
    trap_diag_field_intid_str:
        .string "External Interrupt ID (trap signature word 3)\n"
    trap_diag_field_unknown_str:
        .string "Unknown field\n"

    trap_diag_expected_str:
        .string "RVCP: Expected value: "
    trap_diag_actual_str:
        .string "RVCP: Actual value:   "
    trap_diag_expected_cause_name_str:
        .string "RVCP: Expected cause: "
    trap_diag_actual_cause_name_str:
        .string "RVCP: Actual cause:   "
    trap_diag_curr_xepc_str:
        .string "RVCP: Current MEPC:   "

    trap_diag_generic_str:
        .string "RVCP: Unrecognized trap failure context. Printing available CSR state:\n"

    trap_diag_hint_vect_str:
        .ascii  "RVCP: HINT: Vector+Mode word mismatch may indicate: trap handled in wrong\n"
        .ascii  "RVCP:       privilege mode (check medeleg/mideleg), incorrect mstatus fields\n"
        .asciz  "RVCP:       (MPP/SPP/MPV), or wrong vectored interrupt entry.\n"
    trap_diag_hint_cause_str:
        .ascii  "RVCP: HINT: XCAUSE mismatch means a different exception or interrupt type was\n"
        .ascii  "RVCP:       observed. Check: instruction encoding correctness, CSR accessibility\n"
        .asciz  "RVCP:       at current privilege, PMP/page table configuration, extension support.\n"
    trap_diag_hint_epc_str:
        .ascii  "RVCP: HINT: XEPC mismatch means the trap occurred at a different instruction.\n"
        .ascii  "RVCP:       This could indicate: different code layout (linker issue), instruction\n"
        .asciz  "RVCP:       alignment difference, or a preceding instruction causing an unexpected trap.\n"
    trap_diag_hint_tval_str:
        .ascii  "RVCP: HINT: XTVAL mismatch. For illegal instructions, xtval should contain the\n"
        .ascii  "RVCP:       instruction encoding (or 0). For address faults, it should contain the\n"
        .asciz  "RVCP:       faulting address. Check DUT's xtval reporting behavior.\n"
    trap_diag_hint_ip_str:
        .ascii  "RVCP: HINT: XIP mismatch means interrupt pending bits differ. Check: interrupt\n"
        .ascii  "RVCP:       controller configuration, RVMODEL interrupt set/clear macros, timer\n"
        .asciz  "RVCP:       configuration (mtime/mtimecmp), and delegation settings.\n"

.endm
