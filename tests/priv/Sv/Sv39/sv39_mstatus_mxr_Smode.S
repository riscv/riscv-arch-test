// --------------------------------------------------------------------------------------------------------------------------------
// Developed by: Umer Shahid, Muhammad Abdullah, Muhammad Zain, Hamza Ali and Muhammad Ahmad
// --------------------------------------------------------------------------------------------------------------------------------
// Test cases are as follows:
// --------------------------------------------------------------------------------------------------------------------------------
// 1. mstatus.MXR is unset and X bit is set for the page at level 2:
//        Then, in S-Mode, the page is accessed --> required: Load Page Fault, Store page fault
// 2. mstatus.MXR is set and X bit is set for the page at level 2:
//      Then, in S-Mode, the page is accessed --> required: Store page fault
// 3. mstatus.MXR is unset and X bit is set for the page at level 1:
//        Then, in S-Mode, the page is accessed --> required: Load Page Fault, Store page fault
// 4. mstatus.MXR is set and X bit is set for the page at level 1:
//      Then, in S-Mode, the page is accessed --> required: Store page fault
// 5. mstatus.MXR is unset and X bit is set for the page at level 0:
//        Then, in S-Mode, the page is accessed --> required: Load Page Fault, Store page fault
// 6. mstatus.MXR is set and X bit is set for the page at level 0:
//      Then, in S-Mode, the page is accessed --> required: Store page fault
//
// Total Expected Faults :: 9
// --------------------------------------------------------------------------------------------------------------------------------

##### START_TEST_CONFIG #####
# REQUIRED_EXTENSIONS: [I, Sv39]
# MARCH: rv64i_zicsr
# CONFIG_DEPENDENT: true
##### END_TEST_CONFIG #####

#define TEST_FILE "sv39_mstatus_mxr_Smode.S"
#define SIGUPD_COUNT 50
#define rvtest_mtrap_routine
#define rvtest_strap_routine
#define SKIP_MEPC

#include "riscv_arch_test.h"

RVTEST_BEGIN

//---------------------------------------------------------------------------------------------------------------------------------
// Test RWX permissions
.macro VERIFICATION_RWX
  addi a2, a2, 16

  // Test store permission
  sw  a2, 20(a5)
  nop

  // Test load permission
  lw  a4, 20(a5)
  nop

  // Test execute permission
  LI(  x4, 0xACCE)            // Store a value which is to be checked in trap handler
  jalr ra, a5, 0
  nop
.endm

.macro TEST_CASES_RUNNER LOWER_MODE, VA, level, STR_PTR

  // Adjust offset of VA to point to test region
  .set VA_SHIFT, (\level*9)+12
  LI(a5, (\VA>>VA_SHIFT)<<VA_SHIFT)
  LA(a4, rvtest_data_1)
  slli a4, a4, 64-VA_SHIFT
  srli a4, a4, 64-VA_SHIFT
  add  a5, a5, a4             // Virtual Address

  RVTEST_GOTO_LOWER_MODE \LOWER_MODE

  VERIFICATION_RWX

  RVTEST_GOTO_MMODE

  // Signature Update
  RVTEST_SIGUPD(x2, x5, x4, a2, \STR_PTR)
  RVTEST_SIGUPD(x2, x5, x4, a4, \STR_PTR)
.endm


main:
  li a2, 0x800              // Test signature initialization

//---------------------------------------------------------------------------------------------------------------------------------
//                                   Virtual addresses definition for code and test regions
//---------------------------------------------------------------------------------------------------------------------------------

  // Virtual Address of Test section (rvtest_data_1)
  .set va_data,               0x140802000

  // Virtual Address for code region
  .set va_rvtest_code_begin,  0x180000000


  // PTE setup for Code Region
  SUPERPAGE_PTE_SETUP_SV39(rvtest_code_begin, (PTE_D | PTE_A | PTE_X | PTE_R | PTE_V), va_rvtest_code_begin, LEVEL2)
  sfence.vma

  // Save area setup for code region
  csrr a0, mscratch
  SAVE_AREA_SETUP(va_rvtest_code_begin, rvtest_code_begin, code)

//---------------------------------------------------------------------------------------------------------------------------------
//                                               Test Cases Start from here
//---------------------------------------------------------------------------------------------------------------------------------

  SATP_SETUP_RV64(sv39)                                                  // Set SATP for virtualization
  sfence.vma                                                             // Flush TLB

//---------------------------------------------------------------------------------------------------------------------------------
//---------------------------------------------------------------------------------------------------------------------------------
//                                                    TESTS AT LEVEL 2
//---------------------------------------------------------------------------------------------------------------------------------
//                    1GB PAGE    Region 1 under test at level 2 -- X permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 1: mstatus.MXR unset | Test in S-Mode | X bit set | expected = Store, load page fault
  SUPERPAGE_PTE_SETUP_SV39(rvtest_data_1, (PTE_D | PTE_A | PTE_X | PTE_V), va_data, LEVEL2)
  sfence.vma

  LI(   t0, MSTATUS_MXR)
  CSRC( mstatus, t0)                                                             // Clear mstatus.MXR
  TEST_CASES_RUNNER Smode, va_data, LEVEL2, "test_1"

//---------------------------------------------------------------------------------------------------------------------------------
//                    1GB PAGE    Region 1 under test at level 2 -- X permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 2: mstatus.MXR set | Test in S-Mode | X bit set | expected = store page fault
  SUPERPAGE_PTE_SETUP_SV39(rvtest_data_1, (PTE_D | PTE_A | PTE_X | PTE_V), va_data, LEVEL2)
  sfence.vma

  LI(   t0, MSTATUS_MXR)
  CSRS( mstatus, t0)                                                             // Set mstatus.MXR
  TEST_CASES_RUNNER Smode, va_data, LEVEL2, "test_2"

//---------------------------------------------------------------------------------------------------------------------------------
//---------------------------------------------------------------------------------------------------------------------------------
//                                                    TESTS AT LEVEL 1
//---------------------------------------------------------------------------------------------------------------------------------
//                    2MB PAGE    Region 1 under test at level 1 -- X permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 3: mstatus.MXR unset | Test in S-Mode | X bit set | expected = store, load page fault
  PTE_SETUP_SV39(rvtest_slvl1_pg_tbl, (PTE_V), va_data, LEVEL2)
  SUPERPAGE_PTE_SETUP_SV39(rvtest_data_1, (PTE_D | PTE_A | PTE_X | PTE_V), va_data, LEVEL1)
  sfence.vma

  LI(   t0, MSTATUS_MXR)
  CSRC( mstatus, t0)                                                             // Clear mstatus.MXR
  TEST_CASES_RUNNER Smode, va_data, LEVEL1, "test_3"

//---------------------------------------------------------------------------------------------------------------------------------
//                    2MB PAGE    Region 1 under test at level 1 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 4: mstatus.MXR set | Test in S-Mode | X bit set | expected = store page fault
  PTE_SETUP_SV39(rvtest_slvl1_pg_tbl, (PTE_V), va_data, LEVEL2)
  SUPERPAGE_PTE_SETUP_SV39(rvtest_data_1, (PTE_D | PTE_A | PTE_X | PTE_V), va_data, LEVEL1)
  sfence.vma

  LI(   t0, MSTATUS_MXR)
  CSRS( mstatus, t0)                                                             // Set mstatus.MXR
  TEST_CASES_RUNNER Smode, va_data, LEVEL1, "test_4"

//---------------------------------------------------------------------------------------------------------------------------------
//---------------------------------------------------------------------------------------------------------------------------------
//                                                    TESTS AT LEVEL 0
//---------------------------------------------------------------------------------------------------------------------------------
//                    4KB PAGE    Region 1 under test at level 0 -- X permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 5: mstatus.MXR unset | Test in S-Mode | X bit set | expected = store, load page fault
  PTE_SETUP_SV39(rvtest_slvl1_pg_tbl, (PTE_V), va_data, LEVEL2)
  PTE_SETUP_SV39(rvtest_slvl0_pg_tbl, (PTE_V), va_data, LEVEL1)
  PTE_SETUP_SV39(rvtest_data_1, (PTE_D | PTE_A | PTE_X | PTE_V), va_data, LEVEL0)
  sfence.vma

  LI(   t0, MSTATUS_MXR)
  CSRC( mstatus, t0)                                                             // Clear mstatus.MXR
  TEST_CASES_RUNNER Smode, va_data, LEVEL0, "test_5"

//---------------------------------------------------------------------------------------------------------------------------------
//                    4KB PAGE    Region 1 under test at level 0 -- X permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 6: mstatus.MXR set | Test in S-Mode | X bit set | expected = store page fault
  PTE_SETUP_SV39(rvtest_slvl1_pg_tbl, (PTE_V), va_data, LEVEL2)
  PTE_SETUP_SV39(rvtest_slvl0_pg_tbl, (PTE_V), va_data, LEVEL1)
  PTE_SETUP_SV39(rvtest_data_1, (PTE_D | PTE_A | PTE_X | PTE_V), va_data, LEVEL0)
  sfence.vma

  LI(   t0, MSTATUS_MXR)
  CSRS( mstatus, t0)                                                             // Set mstatus.MXR
  TEST_CASES_RUNNER Smode, va_data, LEVEL0, "test_6"


//---------------------------------------------------------------------------------------------------------------------------------
RVTEST_CODE_END
RVTEST_DATA_BEGIN

//---------------------------------------------------------------------------------------------------------------------------------
//                                            PHYSICAL ADDRESS REGION FOR TESTING
//---------------------------------------------------------------------------------------------------------------------------------
// Physical Address region under testing for LEVEL 0, 1 and 2
.align 12
rvtest_data_1:
  nop
  addi ra, ra, 4
  jr ra
  nop
  .word 0xbeefcaf1          // Random word
  .word 0xbeefcaf2          // Random word
  nop
  jr ra

//---------------------------------------------------------------------------------------------------------------------------------

// Page Tables
.align 12
rvtest_slvl0_pg_tbl:
    .skip(4096)
rvtest_slvl1_pg_tbl:
    .skip(4096)


canary_mismatch: .string "Testcase signature canary mismatch!"
test_1: .string "\"Mismatch in Test Case 1!\""
test_2: .string "\"Mismatch in Test Case 2!\""
test_3: .string "\"Mismatch in Test Case 3!\""
test_4: .string "\"Mismatch in Test Case 4!\""
test_5: .string "\"Mismatch in Test Case 5!\""
test_6: .string "\"Mismatch in Test Case 6!\""

RVTEST_DATA_END
RVTEST_SIG_SETUP
