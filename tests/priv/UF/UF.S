///////////////////////////////////////////
// UF.S
//
// Written: David_Harris@hmc.edu 12 January 2025
//
// Purpose: Functional coverage tests for floating-point CSRs from user mode
//
// SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
///////////////////////////////////////////

##### START_TEST_CONFIG #####
# REQUIRED_EXTENSIONS: [I, U, F, Zicsr]
# MARCH: rv${XLEN}if_zicsr
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


finished:
    // return to machine mode
    li a0, 3
    ecall
    j done
