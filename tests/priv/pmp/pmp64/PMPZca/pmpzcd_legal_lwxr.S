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
// Coverpoints : cp_cfg_RW for PMPZca are fully covered in this test file.
//
// Test Cases  : Check that WR bits control write/read access for every type of
//                 load and store. Attempt all types of reads and writes with
//                 pmpcfg_i.L=1, all legal pmpcfg_i.XWR. Observe proper access
//                 faults for restricted read/write regions
// ---------------------------------------------------------------------------

##### START_TEST_CONFIG #####
# REQUIRED_EXTENSIONS:  ['Zcd','Sm']
# params:
#   MXLEN: 64
#   NUM_PMP_ENTRIES: '>0'
# MARCH: rv64i_zicsr_zifencei_zcd
##### END_TEST_CONFIG #####

#define SIGUPD_COUNT 100
#define RVTEST_PRIV_TEST


#include "riscv_arch_test.h"

RVTEST_BEGIN



main:
    // Loop to SET ALL pmpcfg REGs to zero
    .set pmpcfgi, CSR_PMPCFG0
    .rept UDB_NUM_PMP_ENTRIES/8
    csrw pmpcfgi , x0
    .set pmpcfgi, pmpcfgi+2
    .endr

    // Loop to SET ALL pmpaddr REGs to zero
    .set pmpaddri, CSR_PMPADDR0
    .rept UDB_NUM_PMP_ENTRIES
    csrw pmpaddri, x0
    .set pmpaddri, pmpaddri+1
    .endr

    // Enable the FPU: set mstatus.FS = 01 (Initial)
    // mstatus bits 14:13 = FS. Value 0x00006000 sets FS=11 (Dirty), safe for all F ops.
    li   x4, 0x00006000
    csrs mstatus, x4        // set FS bits without disturbing anything else

    // zero out fcsr so fflags start clean
    fscsr x0

#define PMPREGION_LXWR_1000 ((((PMP_L|                  PMP_NAPOT)&0xFF) << PMP5_CFG_SHIFT))
#define PMPREGION_LXWR_1001 ((((PMP_L|PMP_R|            PMP_NAPOT)&0xFF) << PMP4_CFG_SHIFT))
#define PMPREGION_LXWR_1011 ((((PMP_L|PMP_R|PMP_W       |PMP_NAPOT)&0xFF) << PMP3_CFG_SHIFT))
#define PMPREGION_LXWR_1100 ((((PMP_L|              PMP_X|PMP_NAPOT)&0xFF) << PMP2_CFG_SHIFT))
#define PMPREGION_LXWR_1101 ((((PMP_L|PMP_R         |PMP_X|PMP_NAPOT)&0xFF) << PMP1_CFG_SHIFT))
#define PMPREGION_LXWR_1111 ((((PMP_L|PMP_R|PMP_W|PMP_X|PMP_NAPOT)&0xFF) << PMP0_CFG_SHIFT))

#define REGIONSTART            TEST_FOR_EXECUTION    // RAM_BASE_ADDR + PROGRAM_SIZE
#if UDB_PMP_GRANULARITY != 2
    #define PMP_MASK            ~((1 << (UDB_PMP_GRANULARITY - 3))-1)
    #define PMP_REGION_SIZE     (1 << (UDB_PMP_GRANULARITY - 3)) - 1
#else
    #define PMP_MASK            ~0
    #define PMP_REGION_SIZE     0
#endif


    RVTEST_PMP_SET_BACKGROUND x4

//                                            Verification Section
// Test Case: 1 : L -> 1 and No Permissions given to the PMP Region 5

    LA(x5, REGIONSTART)
    srl x5, x5, PMP_SHIFT
    LI(x6, PMP_MASK)
    and x5, x5, x6
    LI(x6, PMP_REGION_SIZE)
    or x5, x5, x6
    csrw pmpaddr5, x5

    LI(x4, PMPREGION_LXWR_1000)
    csrw pmpcfg0, x4

    PMP_VERIFICATION_X_ZCD    TEST_FOR_EXECUTION, test_1

// Test Case: 2 : L -> 1 and R Permissions given to the PMP Region 4

    LA(x5, REGIONSTART)
    srl x5, x5, PMP_SHIFT
    LI(x6, PMP_MASK)
    and x5, x5, x6
    LI(x6, PMP_REGION_SIZE)
    or x5, x5, x6
    csrw pmpaddr4, x5

    LI(x4, PMPREGION_LXWR_1001)
    csrw pmpcfg0, x4

    PMP_VERIFICATION_X_ZCD    TEST_FOR_EXECUTION, test_2

// Test Case: 3 : L -> 1 and WR Permissions given to the PMP Region 3

    LA(x5, REGIONSTART)
    srl x5, x5, PMP_SHIFT
    LI(x6, PMP_MASK)
    and x5, x5, x6
    LI(x6, PMP_REGION_SIZE)
    or x5, x5, x6
    csrw pmpaddr3, x5

    LI(x4, PMPREGION_LXWR_1011)
    csrw pmpcfg0, x4

    PMP_VERIFICATION_X_ZCD    TEST_FOR_EXECUTION, test_3

// Test Case: 4 : L -> 1 and X Permissions given to the PMP Region 2

    LA(x5, REGIONSTART)
    srl x5, x5, PMP_SHIFT
    LI(x6, PMP_MASK)
    and x5, x5, x6
    LI(x6, PMP_REGION_SIZE)
    or x5, x5, x6
    csrw pmpaddr2, x5

    LI(x4, PMPREGION_LXWR_1100)
    csrw pmpcfg0, x4

    PMP_VERIFICATION_X_ZCD    TEST_FOR_EXECUTION, test_4

// Test Case: 5 : L -> 1 and XR Permissions given to the PMP Region 1

    LA(x5, REGIONSTART)
    srl x5, x5, PMP_SHIFT
    LI(x6, PMP_MASK)
    and x5, x5, x6
    LI(x6, PMP_REGION_SIZE)
    or x5, x5, x6
    csrw pmpaddr1, x5

    LI(x4, PMPREGION_LXWR_1101)
    csrw pmpcfg0, x4

    PMP_VERIFICATION_X_ZCD    TEST_FOR_EXECUTION, test_5

// Test Case: 6 : L -> 1 and XWR Permissions given to the PMP Region 0

    LA(x5, REGIONSTART)
    srl x5, x5, PMP_SHIFT
    LI(x6, PMP_MASK)
    and x5, x5, x6
    LI(x6, PMP_REGION_SIZE)
    or x5, x5, x6
    csrw pmpaddr0, x5

    LI(x4, PMPREGION_LXWR_1111)
    csrw pmpcfg0, x4

    PMP_VERIFICATION_X_ZCD    TEST_FOR_EXECUTION, test_6

   j exit                                                        // Verification Complete, exit the test

exit:

RVTEST_CODE_END

RVTEST_DATA_BEGIN
.p2align 4

// Test case strings for reporting
test_1_str:  .string "\"test: 1;  cp: pmpzcb_cfg_wr_c.fsd\""
test_2_str:  .string "\"test: 2;  cp: pmpzcb_cfg_wr_c.fld\""

.p2align 12
.p2align (UDB_PMP_GRANULARITY)
TEST_FOR_EXECUTION_X:
    jalr x0, x1, 0

.p2align (UDB_PMP_GRANULARITY)
TEST_FOR_EXECUTION:
    .rept (1<<(UDB_PMP_GRANULARITY))
    nop
    .endr

RETURN_INSTRUCTION:
    nop
    nop
    jr ra                                                        // Get back to the point from where TEST_FOR_EXECUTION was called.


RVTEST_DATA_END

// Signature region for self-checking
RVTEST_SIG_SETUP
