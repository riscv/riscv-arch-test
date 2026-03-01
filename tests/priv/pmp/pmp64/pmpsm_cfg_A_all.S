// --------------------------------------------------------------------------------
// Copyright (C) 2025 Harvey Mudd College & Oklahoma State University, UET Lahore, Habib University
// SPDX-License-Identifier: Apache-2.0
//
// Title           : Comprehensive PMP (Physical Memory Protection) Verification
// Authors         : Umer Shahid, Allen Baum, David Harris
//                  Muhammad Abdullah, Hamza Ali, Muhammad Zain
//
// Description : This test verifies the functionality and enforcement of
//               Physical Memory Protection (PMP) configurations in RISC-V
//               systems. It specifically tests the Read, Write, and Execute
//               permissions for a designated memory region, ensuring that
//               the PMP settings are correctly applied and that the system
//               behaves as expected when accessing this region.
//
// Coverpoints : cp_cfg_A_all for PMPM is fully covered in this test file.
//
// Test Cases  : Checking that A is writable in each region. For each standard
//               region, attempt to write pmpcfg.A={OFF, TOR, NA4, NAPOT} with
//               pmpcfg.L=0, pmpcfg.RWX = 000.  Only able to write NA4 if grain
//                G = 0. Other pmpcfg bits are writable.
//
// --------------------------------------------------------------------------------

##### START_TEST_CONFIG #####
# REQUIRED_EXTENSIONS:  ['I','Smpmp']
# params:
#   MXLEN: 64
# MARCH: rv64i_zicsr
# CONFIG_DEPENDENT: true
##### END_TEST_CONFIG #####

// Define the name of this test file for reporting and the size of the signature region
#define TEST_FILE "pmpsm_cfg_A_all.S"
#define SIGUPD_COUNT 50

// Enable trap handler
#define rvtest_mtrap_routine
#define RVTEST_PRIV_TEST

#define SKIP_MEPC

// Include framework macros
#include "riscv_arch_test.h"

// Set up test environment and declare main entry point
RVTEST_BEGIN

main:
    // Loop to SET ALL pmpcfg REGs to zero
    .set pmpcfgi, CSR_PMPCFG0
    .rept RVMODEL_NUM_PMPS/8
    csrw pmpcfgi , x0
    .set pmpcfgi, pmpcfgi+2
    .endr

#define PMP_REGION_GLOBAL    ((PMP_L|PMP_R|PMP_W|PMP_X|PMP_NAPOT)&0xFF)  // Background region with RWX enable.
#define PMPADDRESS_TOP_GLOBAL        -1                                                // All memory region
#define NAPOT   (PMP_NAPOT & 0xFF)
#define TOR     (PMP_TOR   & 0xFF)
#define NA4     (PMP_NA4   & 0xFF)

    LA(x4, PMPADDRESS_TOP_GLOBAL)
    csrw     pmpaddr15, x4

    //Lock the Background region.
    LI(x4, (PMP_REGION_GLOBAL << PMP7_CFG_SHIFT))
    csrw pmpcfg2, x4

//                                            Verification Section
// Test Case 1 : Setting region 0-14 to be NA4, NAPOT, TOR and OFF with L->0, XWR->000

    LI(x4, (NA4   << PMP7_CFG_SHIFT|NA4   << PMP6_CFG_SHIFT|NA4   << PMP5_CFG_SHIFT|NA4   << PMP4_CFG_SHIFT|NA4   << PMP3_CFG_SHIFT|NA4   << PMP2_CFG_SHIFT|NA4   << PMP1_CFG_SHIFT|NA4  ))
    csrw pmpcfg0, x4
    csrw pmpcfg2, x4

.if RVMODEL_NUM_PMPS == 64
    csrw pmpcfg4, x4
    csrw pmpcfg6, x4
    csrw pmpcfg8, x4
    csrw pmpcfg10, x4
    csrw pmpcfg12, x4
    csrw pmpcfg14, x4
.endif

    LI(x4, (NAPOT << PMP7_CFG_SHIFT|NAPOT << PMP6_CFG_SHIFT|NAPOT << PMP5_CFG_SHIFT|NAPOT << PMP4_CFG_SHIFT|NAPOT << PMP3_CFG_SHIFT|NAPOT << PMP2_CFG_SHIFT|NAPOT << PMP1_CFG_SHIFT|NAPOT))
    csrw pmpcfg0, x4
    csrw pmpcfg2, x4

.if RVMODEL_NUM_PMPS == 64
    csrw pmpcfg4, x4
    csrw pmpcfg6, x4
    csrw pmpcfg8, x4
    csrw pmpcfg10, x4
    csrw pmpcfg12, x4
    csrw pmpcfg14, x4
.endif

    LI(x4, (TOR   << PMP7_CFG_SHIFT|TOR   << PMP6_CFG_SHIFT|TOR   << PMP5_CFG_SHIFT|TOR    << PMP4_CFG_SHIFT|TOR   << PMP3_CFG_SHIFT|TOR   << PMP2_CFG_SHIFT|TOR  << PMP1_CFG_SHIFT|TOR  ))
    csrw pmpcfg0, x4
    csrw pmpcfg2, x4

.if RVMODEL_NUM_PMPS == 64
    csrw pmpcfg4, x4
    csrw pmpcfg6, x4
    csrw pmpcfg8, x4
    csrw pmpcfg10, x4
    csrw pmpcfg12, x4
    csrw pmpcfg14, x4
.endif

    csrw pmpcfg0, zero
    csrw pmpcfg2, zero

.if RVMODEL_NUM_PMPS == 64
    csrw pmpcfg4, zero
    csrw pmpcfg6, zero
    csrw pmpcfg8, zero
    csrw pmpcfg10, zero
    csrw pmpcfg12, zero
    csrw pmpcfg14, zero
.endif

// ---------------------------------------------------------------------------

    j exit                                                        // Verification Complete, exit the test

.align 12
.align (RVMODEL_PMP_GRAIN+2)

RETURN_INSTRUCTION:
    nop
    nop
    jr ra                                                        // Get back to the point from where TEST_FOR_EXECUTION was called.

exit:

RVTEST_CODE_END
RVTEST_DATA_BEGIN
.align 4

// Test case strings for reporting
canary_mismatch: .string "Testcase signature canary mismatch!"

RVTEST_DATA_END

// Signature region for self-checking
RVTEST_SIG_SETUP
