///////////////////////////////////////////
// ZicntrM.S
//
// Written: David_Harris@hmc.edu 27 February 2024
//
// Purpose: Functional coverage tests for counters in machine mode
//
// SPDX-License-Identifier: Apache-2.0
///////////////////////////////////////////

#include "WALLY-init-lib.h"

main:

    # set up fast trap handler for uncompressed illegal instructions
    # because Zicntr tests will throw a lot of illegal instruction traps while attempting to access CSRs
    # This cuts the instruction count and runtime by nearly 2x
    # However, don't blindly use this handler in other privileged tests
    la t0, trap_handler_fastuncompressedillegalinstr
    csrw mtvec, t0

/////////////////////////////////
// cp_mtime_write
/////////////////////////////////

    li t0, 0x80
    csrci mstatus, 0x8   # Turn off mstatus.MIE global interrupt enable

// Testing walking zeros and ones for mtime in CLINT
    la a0, MTIME  # address of mtime register
    jal walk

#ifdef __riscv_xlen
    #if __riscv_xlen == 32
        addi a0, a0, 4      # upper word of MTIME
        jal walk
    #endif
#else
    ERROR: __riscv_xlen not defined
#endif


/////////////////////////////////
// cp_cntr_write
// cp_cntrh_write
/////////////////////////////////

#include "ZicntrM-Walk.h"

finished:
    j done

walk:
    SREG zero, 0(a0)   # clear mtime
    li t1, -1           # all 1s
    SREG t1, 0(a0)     # set mtime
    li t0, 1            # 1 in lsb
1:
    SREG t0, 0(a0)     # walking 1s
    not t1, t0          # walking zeros
    SREG t1, 0(a0)     # write walking 0
    slli t0, t0, 1      # move the 1
    bnez t0, 1b         # repeat until all bits are walked
    ret
