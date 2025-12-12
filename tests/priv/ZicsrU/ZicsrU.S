///////////////////////////////////////////
// ZicsrU.S
//
// Written: vkrishna@hmc.edu 17 February 2024
//
// Purpose: Functional coverage tests for CSRs in user mode
//
// SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
///////////////////////////////////////////

// General notes:
// Use csrrw/csrrs/csrrc t6, csr, rs1    when modifying a CSR to also check the old value.

// There is no better place to test the pause instruction, so it is included here.
// Therefore, Zihintpause is needed in the MARCH to compile the pause instruction.
// If Zihintpause is not supported on the DUT, the pause instruction behaves as a NOP.
// Therefore, Zihintpause is not needed in the REQUIRED_EXTENSIONS.

##### START_TEST_CONFIG #####
# REQUIRED_EXTENSIONS: [I, U, Zicsr]
# MARCH: rv${XLEN}i_zicsr_zihintpause
# CONFIG_DEPENDENT: true
##### END_TEST_CONFIG #####

#include "WALLY-init-lib.h"

main:

    # set up fast trap handler for uncompressed illegal instructions
    # because Zicsr tests will throw a lot of illegal instruction traps while attempting to access CSRs
    # This cuts the instruction count and runtime by nearly 2x
    # However, don't blindly use this handler in other privileged tests
    la t0, trap_handler_fastuncompressedillegalinstr
    csrw mtvec, t0

    // Turn on floating-point so these tests can write to user-level floating-point CSRs
    li t0,0x4000
    csrs mstatus, t0

    # enter user mode
    li a0, 0
    ecall

/////////////////////////////////
// cp_uprivinst
/////////////////////////////////
cp_uprivinst:
    li a0, 0     # test switching from user mode to user mode
    ecall

    // ebreak
    ebreak       # take a trap, and the trap handler returns

    // fences.  These aren't really privileged instructions, but don't have a better place to test
    fence
    fence rw, rw
    fence.tso
    pause

/////////////////////////////////
// cp_mret
/////////////////////////////////
cp_mret:
    // Executing mret in user mode
    // Should throw an illegal instruction exception
    mret

/////////////////////////////////
// cp_sret
/////////////////////////////////
cp_sret:
    // Executing sret in user mode
    // Should throw an illegal instruction exception
    sret

///////////////////////////////////
// walking 1s and 0s for each register
///////////////////////////////////
// fflags, frm, fcsr
///////////////////////////////////

#include "ZicsrU-CSR-Tests.h"

finished:
    // return to machine mode
    li a0, 3
    ecall
    j done
