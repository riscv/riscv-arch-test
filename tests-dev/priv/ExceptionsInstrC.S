///////////////////////////////////////////
// ExceptionsInstrC.S
//
// Written: David_Harris@hmc.edu 29 November 2024
//
// Purpose: Functional coverage tests for illegal compressed instructions
//          Portion of ExceptionsZc_coverage
//
// SPDX-License-Identifier: Apache-2.0
///////////////////////////////////////////


#include "WALLY-init-lib.h"

main:

    # set up fast trap handler for compressed illegal instructions
    # because these tests will throw a huge number of traps
    # This handler just adds 2 to PC and returns.  It cannot
    # handle other functions, so substitute the normal trap handler
    # at the end of the program

    la t0, trap_handler_returnplus2
    csrw mtvec, t0

    # set mstatus.FS to 01 to enable fp
    li t0,0x4000
    csrs mstatus, t0

/////////////////////////////////
// Test illegal compressed instructions
/////////////////////////////////

   #include "ExceptionInstrCompressed-Tests.h"

// Restore trap handler before returning

    la t0, trap_handler
    csrw mtvec, t0

finished:
    j done
