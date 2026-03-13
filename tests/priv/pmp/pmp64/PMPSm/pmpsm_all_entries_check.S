// --------------------------------------------------------------------------------
// Copyright (C) 2025 Harvey Mudd College & Oklahoma State University, UET Lahore, Habib University
// SPDX-License-Identifier: Apache-2.0
//
// Title        : Comprehensive PMP (Physical Memory Protection) Verification
// Authors      : Umer Shahid, Allen Baum, David Harris
//                Muhammad Abdullah, Hamza Ali, Muhammad Zain
//
// Description : This test verifies the functionality and enforcement of
//               Physical Memory Protection (PMP) configurations in RISC-V
//               systems. It specifically tests the Read, Write, and Execute
//               permissions for a designated memory region, ensuring that
//               the PMP settings are correctly applied and that the system
//               behaves as expected when accessing this region.
//
// Coverpoints : cp_pmp64 for PMPM is partially covered in this test file.
//
// Test Cases  : Checking all (NUM_PMPS - PMP_writable_regs) PMP registers affect
//               load/store access. Just basic checks since bottom PMP_writable_regs
//               have been tested thoroughly. With pmpcfg.L=1, pmpcfg.XWR=101,
//               attempt to lw and sw to each standard region. Read should succeed
//               and write should fail, proving all PMP entries are usable.
//               Supports RVMODEL_NUM_PMPS = 16 or 64.
// --------------------------------------------------------------------------------

##### START_TEST_CONFIG #####
# REQUIRED_EXTENSIONS: ['I']
# params:
#   MXLEN: 64
#   NUM_PMP_ENTRIES: '>0'
# MARCH: rv64i_zicsr
# CONFIG_DEPENDENT: true
##### END_TEST_CONFIG #####

#define TEST_FILE "pmpsm_all_entries_check.S"
#define SIGUPD_COUNT 200

#define rvtest_mtrap_routine
#define RVTEST_PRIV_TEST

#define SKIP_MEPC

#include "riscv_arch_test.h"

RVTEST_BEGIN

#if RVMODEL_PMP_GRAIN != 0
  #define g   (1 << (RVMODEL_PMP_GRAIN + 2))
#else
  #define g   (1 << (RVMODEL_PMP_GRAIN + 3))
#endif

// ---------------------------------------------------------------------------
// VERIFICATION_RWX  ADDRESS, TEST_CASE
//   Attempts a store (expected to fault — write not permitted) then a load
//   (expected to succeed — read is permitted) to ADDRESS.
// ---------------------------------------------------------------------------
.macro VERIFICATION_RWX ADDRESS, TEST_CASE
    LA(a5, \ADDRESS)
    \TEST_CASE\()_1:
    sw a4, 0(a5)
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4,\TEST_CASE\()_1,test_2_str)
    \TEST_CASE\()_2:
    lw a4, 0(a5)
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4,\TEST_CASE\()_2,test_1_str)
.endm

// ---------------------------------------------------------------------------
// Region configuration bit patterns.
//
// In RV64 each pmpcfgN CSR holds 8 PMP entries (one byte each).
// The PMPn_CFG_SHIFT macros select the correct byte within the CSR.
//
// Background / catch-all region (last pmpaddr entry, always RWX+L):
//   16-PMP : pmpaddr15  controlled by pmpcfg2 byte 7 (PMP7_CFG_SHIFT)
//   64-PMP : pmpaddr63  controlled by pmpcfg14 byte 7 (PMP7_CFG_SHIFT)
//
// Test regions all use L=1, R=1, X=1, W=0 (NAPOT) — read+execute, no write.
// ---------------------------------------------------------------------------

#define PMP_REGION_GLOBAL  ((PMP_L|PMP_R|PMP_W|PMP_X|PMP_NAPOT)&0xFF) << PMP7_CFG_SHIFT

// Slots 0-14 (used by both 16-PMP and 64-PMP systems)
#define PMP_REGION_14   ((PMP_L|PMP_R|PMP_X|PMP_NAPOT)&0xFF) << PMP6_CFG_SHIFT
#define PMP_REGION_13   ((PMP_L|PMP_R|PMP_X|PMP_NAPOT)&0xFF) << PMP5_CFG_SHIFT
#define PMP_REGION_12   ((PMP_L|PMP_R|PMP_X|PMP_NAPOT)&0xFF) << PMP4_CFG_SHIFT
#define PMP_REGION_11   ((PMP_L|PMP_R|PMP_X|PMP_NAPOT)&0xFF) << PMP3_CFG_SHIFT
#define PMP_REGION_10   ((PMP_L|PMP_R|PMP_X|PMP_NAPOT)&0xFF) << PMP2_CFG_SHIFT
#define PMP_REGION_9    ((PMP_L|PMP_R|PMP_X|PMP_NAPOT)&0xFF) << PMP1_CFG_SHIFT
#define PMP_REGION_8    ((PMP_L|PMP_R|PMP_X|PMP_NAPOT)&0xFF) << PMP0_CFG_SHIFT
#define PMP_REGION_7    ((PMP_L|PMP_R|PMP_X|PMP_NAPOT)&0xFF) << PMP7_CFG_SHIFT
#define PMP_REGION_6    ((PMP_L|PMP_R|PMP_X|PMP_NAPOT)&0xFF) << PMP6_CFG_SHIFT
#define PMP_REGION_5    ((PMP_L|PMP_R|PMP_X|PMP_NAPOT)&0xFF) << PMP5_CFG_SHIFT
#define PMP_REGION_4    ((PMP_L|PMP_R|PMP_X|PMP_NAPOT)&0xFF) << PMP4_CFG_SHIFT
#define PMP_REGION_3    ((PMP_L|PMP_R|PMP_X|PMP_NAPOT)&0xFF) << PMP3_CFG_SHIFT
#define PMP_REGION_2    ((PMP_L|PMP_R|PMP_X|PMP_NAPOT)&0xFF) << PMP2_CFG_SHIFT
#define PMP_REGION_1    ((PMP_L|PMP_R|PMP_X|PMP_NAPOT)&0xFF) << PMP1_CFG_SHIFT
#define PMP_REGION_0    ((PMP_L|PMP_R|PMP_X|PMP_NAPOT)&0xFF) << PMP0_CFG_SHIFT

// Slots 16-62 (64-PMP only)
#if RVMODEL_NUM_PMPS == 64
#define PMP_REGION_62   ((PMP_L|PMP_R|PMP_X|PMP_NAPOT)&0xFF) << PMP6_CFG_SHIFT
#define PMP_REGION_61   ((PMP_L|PMP_R|PMP_X|PMP_NAPOT)&0xFF) << PMP5_CFG_SHIFT
#define PMP_REGION_60   ((PMP_L|PMP_R|PMP_X|PMP_NAPOT)&0xFF) << PMP4_CFG_SHIFT
#define PMP_REGION_59   ((PMP_L|PMP_R|PMP_X|PMP_NAPOT)&0xFF) << PMP3_CFG_SHIFT
#define PMP_REGION_58   ((PMP_L|PMP_R|PMP_X|PMP_NAPOT)&0xFF) << PMP2_CFG_SHIFT
#define PMP_REGION_57   ((PMP_L|PMP_R|PMP_X|PMP_NAPOT)&0xFF) << PMP1_CFG_SHIFT
#define PMP_REGION_56   ((PMP_L|PMP_R|PMP_X|PMP_NAPOT)&0xFF) << PMP0_CFG_SHIFT
#define PMP_REGION_55   ((PMP_L|PMP_R|PMP_X|PMP_NAPOT)&0xFF) << PMP7_CFG_SHIFT
#define PMP_REGION_54   ((PMP_L|PMP_R|PMP_X|PMP_NAPOT)&0xFF) << PMP6_CFG_SHIFT
#define PMP_REGION_53   ((PMP_L|PMP_R|PMP_X|PMP_NAPOT)&0xFF) << PMP5_CFG_SHIFT
#define PMP_REGION_52   ((PMP_L|PMP_R|PMP_X|PMP_NAPOT)&0xFF) << PMP4_CFG_SHIFT
#define PMP_REGION_51   ((PMP_L|PMP_R|PMP_X|PMP_NAPOT)&0xFF) << PMP3_CFG_SHIFT
#define PMP_REGION_50   ((PMP_L|PMP_R|PMP_X|PMP_NAPOT)&0xFF) << PMP2_CFG_SHIFT
#define PMP_REGION_49   ((PMP_L|PMP_R|PMP_X|PMP_NAPOT)&0xFF) << PMP1_CFG_SHIFT
#define PMP_REGION_48   ((PMP_L|PMP_R|PMP_X|PMP_NAPOT)&0xFF) << PMP0_CFG_SHIFT
#define PMP_REGION_47   ((PMP_L|PMP_R|PMP_X|PMP_NAPOT)&0xFF) << PMP7_CFG_SHIFT
#define PMP_REGION_46   ((PMP_L|PMP_R|PMP_X|PMP_NAPOT)&0xFF) << PMP6_CFG_SHIFT
#define PMP_REGION_45   ((PMP_L|PMP_R|PMP_X|PMP_NAPOT)&0xFF) << PMP5_CFG_SHIFT
#define PMP_REGION_44   ((PMP_L|PMP_R|PMP_X|PMP_NAPOT)&0xFF) << PMP4_CFG_SHIFT
#define PMP_REGION_43   ((PMP_L|PMP_R|PMP_X|PMP_NAPOT)&0xFF) << PMP3_CFG_SHIFT
#define PMP_REGION_42   ((PMP_L|PMP_R|PMP_X|PMP_NAPOT)&0xFF) << PMP2_CFG_SHIFT
#define PMP_REGION_41   ((PMP_L|PMP_R|PMP_X|PMP_NAPOT)&0xFF) << PMP1_CFG_SHIFT
#define PMP_REGION_40   ((PMP_L|PMP_R|PMP_X|PMP_NAPOT)&0xFF) << PMP0_CFG_SHIFT
#define PMP_REGION_39   ((PMP_L|PMP_R|PMP_X|PMP_NAPOT)&0xFF) << PMP7_CFG_SHIFT
#define PMP_REGION_38   ((PMP_L|PMP_R|PMP_X|PMP_NAPOT)&0xFF) << PMP6_CFG_SHIFT
#define PMP_REGION_37   ((PMP_L|PMP_R|PMP_X|PMP_NAPOT)&0xFF) << PMP5_CFG_SHIFT
#define PMP_REGION_36   ((PMP_L|PMP_R|PMP_X|PMP_NAPOT)&0xFF) << PMP4_CFG_SHIFT
#define PMP_REGION_35   ((PMP_L|PMP_R|PMP_X|PMP_NAPOT)&0xFF) << PMP3_CFG_SHIFT
#define PMP_REGION_34   ((PMP_L|PMP_R|PMP_X|PMP_NAPOT)&0xFF) << PMP2_CFG_SHIFT
#define PMP_REGION_33   ((PMP_L|PMP_R|PMP_X|PMP_NAPOT)&0xFF) << PMP1_CFG_SHIFT
#define PMP_REGION_32   ((PMP_L|PMP_R|PMP_X|PMP_NAPOT)&0xFF) << PMP0_CFG_SHIFT
#define PMP_REGION_31   ((PMP_L|PMP_R|PMP_X|PMP_NAPOT)&0xFF) << PMP7_CFG_SHIFT
#define PMP_REGION_30   ((PMP_L|PMP_R|PMP_X|PMP_NAPOT)&0xFF) << PMP6_CFG_SHIFT
#define PMP_REGION_29   ((PMP_L|PMP_R|PMP_X|PMP_NAPOT)&0xFF) << PMP5_CFG_SHIFT
#define PMP_REGION_28   ((PMP_L|PMP_R|PMP_X|PMP_NAPOT)&0xFF) << PMP4_CFG_SHIFT
#define PMP_REGION_27   ((PMP_L|PMP_R|PMP_X|PMP_NAPOT)&0xFF) << PMP3_CFG_SHIFT
#define PMP_REGION_26   ((PMP_L|PMP_R|PMP_X|PMP_NAPOT)&0xFF) << PMP2_CFG_SHIFT
#define PMP_REGION_25   ((PMP_L|PMP_R|PMP_X|PMP_NAPOT)&0xFF) << PMP1_CFG_SHIFT
#define PMP_REGION_24   ((PMP_L|PMP_R|PMP_X|PMP_NAPOT)&0xFF) << PMP0_CFG_SHIFT
#define PMP_REGION_23   ((PMP_L|PMP_R|PMP_X|PMP_NAPOT)&0xFF) << PMP7_CFG_SHIFT
#define PMP_REGION_22   ((PMP_L|PMP_R|PMP_X|PMP_NAPOT)&0xFF) << PMP6_CFG_SHIFT
#define PMP_REGION_21   ((PMP_L|PMP_R|PMP_X|PMP_NAPOT)&0xFF) << PMP5_CFG_SHIFT
#define PMP_REGION_20   ((PMP_L|PMP_R|PMP_X|PMP_NAPOT)&0xFF) << PMP4_CFG_SHIFT
#define PMP_REGION_19   ((PMP_L|PMP_R|PMP_X|PMP_NAPOT)&0xFF) << PMP3_CFG_SHIFT
#define PMP_REGION_18   ((PMP_L|PMP_R|PMP_X|PMP_NAPOT)&0xFF) << PMP2_CFG_SHIFT
#define PMP_REGION_17   ((PMP_L|PMP_R|PMP_X|PMP_NAPOT)&0xFF) << PMP1_CFG_SHIFT
#define PMP_REGION_16   ((PMP_L|PMP_R|PMP_X|PMP_NAPOT)&0xFF) << PMP0_CFG_SHIFT
#endif  // RVMODEL_NUM_PMPS == 64

// ---------------------------------------------------------------------------
// Address helpers
// ---------------------------------------------------------------------------
#define PMPADDRESS_TOP_GLOBAL   -1              // Covers entire address space
#define REGIONSTART     TEST_FOR_EXECUTION      // RAM_BASE_ADDR + PROGRAM_SIZE

#if RVMODEL_PMP_GRAIN != 0
    #define PMP_MASK        ~((1 << (RVMODEL_PMP_GRAIN - 1))-1)
    #define PMP_REGION_SIZE (1 << (RVMODEL_PMP_GRAIN - 1)) - 1
#else
    #define PMP_MASK        ~0
    #define PMP_REGION_SIZE 0
#endif

// ---------------------------------------------------------------------------
// SET_PMP_ENTRY  ADDR_REG, CFG_REG, CFG_BITS
//   Encodes REGIONSTART in NAPOT format, writes pmpaddr, then writes pmpcfg.
// ---------------------------------------------------------------------------
.macro SET_PMP_ENTRY ADDR_REG, CFG_REG, CFG_BITS
    LA(x5, REGIONSTART)
    srl x5, x5, PMP_SHIFT
    andi x5, x5, PMP_MASK
    ori x5, x5, PMP_REGION_SIZE
    csrw \ADDR_REG, x5
    LI(x4, \CFG_BITS)
    csrw \CFG_REG, x4
.endm


// ===========================================================================
// main
// ===========================================================================
main:
    // Zero all pmpcfg registers
    .set pmpcfgi, CSR_PMPCFG0
    .rept RVMODEL_NUM_PMPS/8
    csrw pmpcfgi, x0
    .set pmpcfgi, pmpcfgi+2
    .endr

    // Zero all pmpaddr registers
    .set pmpaddri, CSR_PMPADDR0
    .rept RVMODEL_NUM_PMPS
    csrw pmpaddri, x0
    .set pmpaddri, pmpaddri+1
    .endr

    // -----------------------------------------------------------------------
    // Background (catch-all) region — must be the highest-numbered entry so
    // that all lower entries take priority over it.
    //   16-PMP : last entry = pmpaddr15, config byte lives in pmpcfg2[PMP7]
    //   64-PMP : last entry = pmpaddr63, config byte lives in pmpcfg14[PMP7]
    // -----------------------------------------------------------------------
#if RVMODEL_NUM_PMPS == 64
    LA(x4, PMPADDRESS_TOP_GLOBAL)
    csrw pmpaddr63, x4
    LI(x4, PMP_REGION_GLOBAL)
    csrw pmpcfg14, x4
#elif RVMODEL_NUM_PMPS == 16
    LA(x4, PMPADDRESS_TOP_GLOBAL)
    csrw pmpaddr15, x4
    LI(x4, PMP_REGION_GLOBAL)
    csrw pmpcfg2, x4
#else
    #error "Unsupported RVMODEL_NUM_PMPS value; only 16 and 64 are supported."
#endif

// ===========================================================================
// TEST CASES — 64-PMP ONLY (slots 16-62, test cases 1-47)
// Slots 0-14 follow as test cases 48-62 in this build.
// ===========================================================================
#if RVMODEL_NUM_PMPS == 64

// Test Case: 1 — slot 62, pmpcfg14
    SET_PMP_ENTRY pmpaddr62, pmpcfg14, PMP_REGION_62
    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_1

// Test Case: 2 — slot 61, pmpcfg14
    SET_PMP_ENTRY pmpaddr61, pmpcfg14, PMP_REGION_61
    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_2

// Test Case: 3 — slot 60, pmpcfg14
    SET_PMP_ENTRY pmpaddr60, pmpcfg14, PMP_REGION_60
    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_3

// Test Case: 4 — slot 59, pmpcfg14
    SET_PMP_ENTRY pmpaddr59, pmpcfg14, PMP_REGION_59
    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_4

// Test Case: 5 — slot 58, pmpcfg14
    SET_PMP_ENTRY pmpaddr58, pmpcfg14, PMP_REGION_58
    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_5

// Test Case: 6 — slot 57, pmpcfg14
    SET_PMP_ENTRY pmpaddr57, pmpcfg14, PMP_REGION_57
    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_6

// Test Case: 7 — slot 56, pmpcfg14
    SET_PMP_ENTRY pmpaddr56, pmpcfg14, PMP_REGION_56
    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_7

// Test Case: 8 — slot 55, pmpcfg12
    SET_PMP_ENTRY pmpaddr55, pmpcfg12, PMP_REGION_55
    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_8

// Test Case: 9 — slot 54, pmpcfg12
    SET_PMP_ENTRY pmpaddr54, pmpcfg12, PMP_REGION_54
    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_9

// Test Case: 10 — slot 53, pmpcfg12
    SET_PMP_ENTRY pmpaddr53, pmpcfg12, PMP_REGION_53
    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_10

// Test Case: 11 — slot 52, pmpcfg12
    SET_PMP_ENTRY pmpaddr52, pmpcfg12, PMP_REGION_52
    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_11

// Test Case: 12 — slot 51, pmpcfg12
    SET_PMP_ENTRY pmpaddr51, pmpcfg12, PMP_REGION_51
    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_12

// Test Case: 13 — slot 50, pmpcfg12
    SET_PMP_ENTRY pmpaddr50, pmpcfg12, PMP_REGION_50
    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_13

// Test Case: 14 — slot 49, pmpcfg12
    SET_PMP_ENTRY pmpaddr49, pmpcfg12, PMP_REGION_49
    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_14

// Test Case: 15 — slot 48, pmpcfg12
    SET_PMP_ENTRY pmpaddr48, pmpcfg12, PMP_REGION_48
    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_15

// Test Case: 16 — slot 47, pmpcfg10
    SET_PMP_ENTRY pmpaddr47, pmpcfg10, PMP_REGION_47
    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_16

// Test Case: 17 — slot 46, pmpcfg10
    SET_PMP_ENTRY pmpaddr46, pmpcfg10, PMP_REGION_46
    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_17

// Test Case: 18 — slot 45, pmpcfg10
    SET_PMP_ENTRY pmpaddr45, pmpcfg10, PMP_REGION_45
    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_18

// Test Case: 19 — slot 44, pmpcfg10
    SET_PMP_ENTRY pmpaddr44, pmpcfg10, PMP_REGION_44
    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_19

// Test Case: 20 — slot 43, pmpcfg10
    SET_PMP_ENTRY pmpaddr43, pmpcfg10, PMP_REGION_43
    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_20

// Test Case: 21 — slot 42, pmpcfg10
    SET_PMP_ENTRY pmpaddr42, pmpcfg10, PMP_REGION_42
    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_21

// Test Case: 22 — slot 41, pmpcfg10
    SET_PMP_ENTRY pmpaddr41, pmpcfg10, PMP_REGION_41
    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_22

// Test Case: 23 — slot 40, pmpcfg10
    SET_PMP_ENTRY pmpaddr40, pmpcfg10, PMP_REGION_40
    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_23

// Test Case: 24 — slot 39, pmpcfg8
    SET_PMP_ENTRY pmpaddr39, pmpcfg8, PMP_REGION_39
    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_24

// Test Case: 25 — slot 38, pmpcfg8
    SET_PMP_ENTRY pmpaddr38, pmpcfg8, PMP_REGION_38
    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_25

// Test Case: 26 — slot 37, pmpcfg8
    SET_PMP_ENTRY pmpaddr37, pmpcfg8, PMP_REGION_37
    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_26

// Test Case: 27 — slot 36, pmpcfg8
    SET_PMP_ENTRY pmpaddr36, pmpcfg8, PMP_REGION_36
    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_27

// Test Case: 28 — slot 35, pmpcfg8
    SET_PMP_ENTRY pmpaddr35, pmpcfg8, PMP_REGION_35
    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_28

// Test Case: 29 — slot 34, pmpcfg8
    SET_PMP_ENTRY pmpaddr34, pmpcfg8, PMP_REGION_34
    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_29

// Test Case: 30 — slot 33, pmpcfg8
    SET_PMP_ENTRY pmpaddr33, pmpcfg8, PMP_REGION_33
    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_30

// Test Case: 31 — slot 32, pmpcfg8
    SET_PMP_ENTRY pmpaddr32, pmpcfg8, PMP_REGION_32
    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_31

// Test Case: 32 — slot 31, pmpcfg6
    SET_PMP_ENTRY pmpaddr31, pmpcfg6, PMP_REGION_31
    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_32

// Test Case: 33 — slot 30, pmpcfg6
    SET_PMP_ENTRY pmpaddr30, pmpcfg6, PMP_REGION_30
    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_33

// Test Case: 34 — slot 29, pmpcfg6
    SET_PMP_ENTRY pmpaddr29, pmpcfg6, PMP_REGION_29
    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_34

// Test Case: 35 — slot 28, pmpcfg6
    SET_PMP_ENTRY pmpaddr28, pmpcfg6, PMP_REGION_28
    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_35

// Test Case: 36 — slot 27, pmpcfg6
    SET_PMP_ENTRY pmpaddr27, pmpcfg6, PMP_REGION_27
    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_36

// Test Case: 37 — slot 26, pmpcfg6
    SET_PMP_ENTRY pmpaddr26, pmpcfg6, PMP_REGION_26
    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_37

// Test Case: 38 — slot 25, pmpcfg6
    SET_PMP_ENTRY pmpaddr25, pmpcfg6, PMP_REGION_25
    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_38

// Test Case: 39 — slot 24, pmpcfg6
    SET_PMP_ENTRY pmpaddr24, pmpcfg6, PMP_REGION_24
    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_39

// Test Case: 40 — slot 23, pmpcfg4
    SET_PMP_ENTRY pmpaddr23, pmpcfg4, PMP_REGION_23
    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_40

// Test Case: 41 — slot 22, pmpcfg4
    SET_PMP_ENTRY pmpaddr22, pmpcfg4, PMP_REGION_22
    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_41

// Test Case: 42 — slot 21, pmpcfg4
    SET_PMP_ENTRY pmpaddr21, pmpcfg4, PMP_REGION_21
    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_42

// Test Case: 43 — slot 20, pmpcfg4
    SET_PMP_ENTRY pmpaddr20, pmpcfg4, PMP_REGION_20
    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_43

// Test Case: 44 — slot 19, pmpcfg4
    SET_PMP_ENTRY pmpaddr19, pmpcfg4, PMP_REGION_19
    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_44

// Test Case: 45 — slot 18, pmpcfg4
    SET_PMP_ENTRY pmpaddr18, pmpcfg4, PMP_REGION_18
    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_45

// Test Case: 46 — slot 17, pmpcfg4
    SET_PMP_ENTRY pmpaddr17, pmpcfg4, PMP_REGION_17
    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_46

// Test Case: 47 — slot 16, pmpcfg4
    SET_PMP_ENTRY pmpaddr16, pmpcfg4, PMP_REGION_16
    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_47

// Test Case: 48 — slot 14, pmpcfg2
    SET_PMP_ENTRY pmpaddr14, pmpcfg2, PMP_REGION_14
    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_48

// Test Case: 49 — slot 13, pmpcfg2
    SET_PMP_ENTRY pmpaddr13, pmpcfg2, PMP_REGION_13
    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_49

// Test Case: 50 — slot 12, pmpcfg2
    SET_PMP_ENTRY pmpaddr12, pmpcfg2, PMP_REGION_12
    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_50

// Test Case: 51 — slot 11, pmpcfg2
    SET_PMP_ENTRY pmpaddr11, pmpcfg2, PMP_REGION_11
    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_51

// Test Case: 52 — slot 10, pmpcfg2
    SET_PMP_ENTRY pmpaddr10, pmpcfg2, PMP_REGION_10
    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_52

// Test Case: 53 — slot 9, pmpcfg2
    SET_PMP_ENTRY pmpaddr9, pmpcfg2, PMP_REGION_9
    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_53

// Test Case: 54 — slot 8, pmpcfg2
    SET_PMP_ENTRY pmpaddr8, pmpcfg2, PMP_REGION_8
    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_54

// Test Case: 55 — slot 7, pmpcfg0
    SET_PMP_ENTRY pmpaddr7, pmpcfg0, PMP_REGION_7
    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_55

// Test Case: 56 — slot 6, pmpcfg0
    SET_PMP_ENTRY pmpaddr6, pmpcfg0, PMP_REGION_6
    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_56

// Test Case: 57 — slot 5, pmpcfg0
    SET_PMP_ENTRY pmpaddr5, pmpcfg0, PMP_REGION_5
    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_57

// Test Case: 58 — slot 4, pmpcfg0
    SET_PMP_ENTRY pmpaddr4, pmpcfg0, PMP_REGION_4
    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_58

// Test Case: 59 — slot 3, pmpcfg0
    SET_PMP_ENTRY pmpaddr3, pmpcfg0, PMP_REGION_3
    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_59

// Test Case: 60 — slot 2, pmpcfg0
    SET_PMP_ENTRY pmpaddr2, pmpcfg0, PMP_REGION_2
    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_60

// Test Case: 61 — slot 1, pmpcfg0
    SET_PMP_ENTRY pmpaddr1, pmpcfg0, PMP_REGION_1
    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_61

// Test Case: 62 — slot 0, pmpcfg0
    SET_PMP_ENTRY pmpaddr0, pmpcfg0, PMP_REGION_0
    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_62

#endif  // RVMODEL_NUM_PMPS == 64

// ===========================================================================
// TEST CASES — 16-PMP ONLY (slots 14-0, test cases 1-15)
// slot 15 is the background region; we test slots 14 down to 0.
// pmpcfg2 covers pmpaddr8-15  (RV64: one 64-bit CSR = 8 entries)
// pmpcfg0 covers pmpaddr0-7
// ===========================================================================
#if RVMODEL_NUM_PMPS == 16

// Test Case: 1 — slot 14, pmpcfg2
    SET_PMP_ENTRY pmpaddr14, pmpcfg2, PMP_REGION_14
    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_1

// Test Case: 2 — slot 13, pmpcfg2
    SET_PMP_ENTRY pmpaddr13, pmpcfg2, PMP_REGION_13
    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_2

// Test Case: 3 — slot 12, pmpcfg2
    SET_PMP_ENTRY pmpaddr12, pmpcfg2, PMP_REGION_12
    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_3

// Test Case: 4 — slot 11, pmpcfg2
    SET_PMP_ENTRY pmpaddr11, pmpcfg2, PMP_REGION_11
    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_4

// Test Case: 5 — slot 10, pmpcfg2
    SET_PMP_ENTRY pmpaddr10, pmpcfg2, PMP_REGION_10
    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_5

// Test Case: 6 — slot 9, pmpcfg2
    SET_PMP_ENTRY pmpaddr9, pmpcfg2, PMP_REGION_9
    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_6

// Test Case: 7 — slot 8, pmpcfg2
    SET_PMP_ENTRY pmpaddr8, pmpcfg2, PMP_REGION_8
    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_7

// Test Case: 8 — slot 7, pmpcfg0
    SET_PMP_ENTRY pmpaddr7, pmpcfg0, PMP_REGION_7
    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_8

// Test Case: 9 — slot 6, pmpcfg0
    SET_PMP_ENTRY pmpaddr6, pmpcfg0, PMP_REGION_6
    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_9

// Test Case: 10 — slot 5, pmpcfg0
    SET_PMP_ENTRY pmpaddr5, pmpcfg0, PMP_REGION_5
    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_10

// Test Case: 11 — slot 4, pmpcfg0
    SET_PMP_ENTRY pmpaddr4, pmpcfg0, PMP_REGION_4
    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_11

// Test Case: 12 — slot 3, pmpcfg0
    SET_PMP_ENTRY pmpaddr3, pmpcfg0, PMP_REGION_3
    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_12

// Test Case: 13 — slot 2, pmpcfg0
    SET_PMP_ENTRY pmpaddr2, pmpcfg0, PMP_REGION_2
    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_13

// Test Case: 14 — slot 1, pmpcfg0
    SET_PMP_ENTRY pmpaddr1, pmpcfg0, PMP_REGION_1
    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_14

// Test Case: 15 — slot 0, pmpcfg0
    SET_PMP_ENTRY pmpaddr0, pmpcfg0, PMP_REGION_0
    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_15

#endif  // RVMODEL_NUM_PMPS == 16

    j exit                                                  // Verification complete

.align 12
TEST_FOR_EXECUTION:
    .rept (1<<(RVMODEL_PMP_GRAIN+2))
    nop
    .endr

RETURN_INSTRUCTION:
    nop
    nop
    jr ra                                                   // Return to caller

exit:

RVTEST_CODE_END
RVTEST_DATA_BEGIN
.align 4

canary_mismatch: .string "Testcase signature canary mismatch!"
test_1_str: .string "\"test: 1; cp: cp_pmpm64_lw\""
test_2_str: .string "\"test: 2; cp: cp_pmpm64_sw\""

RVTEST_DATA_END

RVTEST_SIG_SETUP
