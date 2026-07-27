// ---------------------------------------------------------------------------
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
//
// Coverpoints : cp_prefetch for PMPZicbo is partially covered in this test file.
//
// Test Cases  : Check that XWR bits control access for prefetch.
//                 Attempt {prefetch.i/w/r} with pmpcfg_i.L=1, legal pmpcfg_i.XWR,
//                 at start of 4 KB region plenty long to encompass a cache line.
//                 No exceptions should be raised.
// ---------------------------------------------------------------------------

##### START_TEST_CONFIG #####
# REQUIRED_EXTENSIONS:  ['Sm','Zicbop']
# params:
#   MXLEN: 32
#   NUM_PMP_ENTRIES: '>0'
# MARCH: rv32i_zicsr_zifencei_zicbop
##### END_TEST_CONFIG #####

#define SIGUPD_COUNT 100
#define RVTEST_PRIV_TEST


#include "riscv_arch_test.h"

RVTEST_BEGIN

.macro VERIFICATION_RWX ADDRESS TEST_CASE

    // Address must be aligned to the cache block
    LA(t0, \ADDRESS)
    \TEST_CASE\()_1:
    prefetch.i 0(t0)
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_1, test_1_str)

    \TEST_CASE\()_2:
    prefetch.r 0(t0)
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_2, test_2_str)

    \TEST_CASE\()_3:
    prefetch.w 0(t0)
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_3, test_3_str)

.endm

main:
    // Loop to SET ALL pmpcfg REGs to zero
    .set pmpcfgi, CSR_PMPCFG0
    .rept UDB_NUM_PMP_ENTRIES/4
    csrw pmpcfgi , x0
    .set pmpcfgi, pmpcfgi+1
    .endr

    // Loop to SET ALL pmpaddr REGs to zero
    .set pmpaddri, CSR_PMPADDR0
    .rept UDB_NUM_PMP_ENTRIES
    csrw pmpaddri, x0
    .set pmpaddri, pmpaddri+1
    .endr


#define PMPREGION_LXWR_1000             ((((PMP_L|                  PMP_NAPOT)&0xFF) << PMP1_CFG_SHIFT))
#define PMPREGION_LXWR_1001             ((((PMP_L|PMP_R|            PMP_NAPOT)&0xFF) << PMP0_CFG_SHIFT))
#define PMPREGION_LXWR_1011             ((((PMP_L|PMP_R|PMP_W       |PMP_NAPOT)&0xFF) << PMP3_CFG_SHIFT))
#define PMPREGION_LXWR_1100             ((((PMP_L|              PMP_X|PMP_NAPOT)&0xFF) << PMP2_CFG_SHIFT))
#define PMPREGION_LXWR_1101             ((((PMP_L|PMP_R         |PMP_X|PMP_NAPOT)&0xFF) << PMP1_CFG_SHIFT))
#define PMPREGION_LXWR_1111             ((((PMP_L|PMP_R|PMP_W|PMP_X|PMP_NAPOT)&0xFF) << PMP0_CFG_SHIFT))

#define MENVCFG                            0xF0                                                             // menvcfg.CBIE, CBCFE, CBZE = 1

#define REGIONSTART                TEST_FOR_EXECUTION_1
#if UDB_PMP_GRANULARITY > 12
    #define PMPZICBO_REGION_SHIFT  UDB_PMP_GRANULARITY
#else
    #define PMPZICBO_REGION_SHIFT  12
#endif
#define PMP_MASK                   ~((1 << (PMPZICBO_REGION_SHIFT - 3))-1)
#define PMP_REGION_SIZE            ((1 << (PMPZICBO_REGION_SHIFT - 3)) - 1)



    RVTEST_PMP_SET_BACKGROUND x4

    li t0, MENVCFG
    csrrs zero, menvcfg, t0

//                                                Verification Section
// Test Case: 1 : L -> 1 and No Permissions given to the PMP Region

    LA(x4, REGIONSTART)
    srl x4, x4, PMP_SHIFT
    LI(x6, PMP_MASK)
    and x4, x4, x6
    LI(x6, PMP_REGION_SIZE)
    or x4, x4, x6
    csrw pmpaddr5, x4

    LI(x4, PMPREGION_LXWR_1000)
    csrw pmpcfg1, x4

    VERIFICATION_RWX    TEST_FOR_EXECUTION_1, test_1

// Test Case: 2 : L -> 1 and R Permissions given to the PMP Region

    LA(x4, REGIONSTART)
    srl x4, x4, PMP_SHIFT
    LI(x6, PMP_MASK)
    and x4, x4, x6
    LI(x6, PMP_REGION_SIZE)
    or x4, x4, x6
    csrw pmpaddr4, x4

    LI(x4, PMPREGION_LXWR_1001)
    csrw pmpcfg1, x4

    VERIFICATION_RWX    TEST_FOR_EXECUTION_1, test_2

// Test Case: 3 : L -> 1 and WR Permissions given to the PMP Region

    LA(x4, REGIONSTART)
    srl x4, x4, PMP_SHIFT
    LI(x6, PMP_MASK)
    and x4, x4, x6
    LI(x6, PMP_REGION_SIZE)
    or x4, x4, x6
    csrw pmpaddr3, x4

    LI(x4, PMPREGION_LXWR_1011)
    csrw pmpcfg0, x4

    VERIFICATION_RWX    TEST_FOR_EXECUTION_1, test_3

// Test Case: 4 : L -> 1 and X Permissions given to the PMP Region

    LA(x4, REGIONSTART)
    srl x4, x4, PMP_SHIFT
    LI(x6, PMP_MASK)
    and x4, x4, x6
    LI(x6, PMP_REGION_SIZE)
    or x4, x4, x6
    csrw pmpaddr2, x4

    LI(x4, PMPREGION_LXWR_1100)
    csrw pmpcfg0, x4

    VERIFICATION_RWX    TEST_FOR_EXECUTION_1, test_4

// Test Case: 5 : L -> 1 and XR Permissions given to the PMP Region

    LA(x4, REGIONSTART)
    srl x4, x4, PMP_SHIFT
    LI(x6, PMP_MASK)
    and x4, x4, x6
    LI(x6, PMP_REGION_SIZE)
    or x4, x4, x6
    csrw pmpaddr1, x4

    LI(x4, PMPREGION_LXWR_1101)
    csrw pmpcfg0, x4

    VERIFICATION_RWX    TEST_FOR_EXECUTION_1, test_5

// Test Case: 6 : L -> 1 and XWR Permissions given to the PMP Region

    LA(x4, REGIONSTART)
    srl x4, x4, PMP_SHIFT
    LI(x6, PMP_MASK)
    and x4, x4, x6
    LI(x6, PMP_REGION_SIZE)
    or x4, x4, x6
    csrw pmpaddr0, x4

    LI(x4, PMPREGION_LXWR_1111)
    csrw pmpcfg0, x4

    VERIFICATION_RWX    TEST_FOR_EXECUTION_1, test_6

    j exit                                        // Verification Complete, exit the test

exit:
RVTEST_CODE_END

RVTEST_DATA_BEGIN
.p2align 4

// Test case strings for reporting
test_1_str:  .string "\"test: 1;  cp: pmpzicbo_prefetch_i\""
test_2_str:  .string "\"test: 2;  cp: pmpzicbo_prefetch_r\""
test_3_str:  .string "\"test: 3;  cp: pmpzicbo_prefetch_w\""

.p2align 12
.p2align (UDB_PMP_GRANULARITY)
TEST_FOR_EXECUTION_1:
    .rept 1024
    nop
    .endr

.p2align (UDB_PMP_GRANULARITY)
TEST_FOR_EXECUTION_2:
    .rept 1024
    nop
    .endr

RETURN_INSTRUCTION:
    nop
    nop
    jr ra                                                        // Get back to the point from where TEST_FOR_EXECUTION was called.


RVTEST_DATA_END

// Signature region for self-checking
RVTEST_SIG_SETUP
