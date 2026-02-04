// --------------------------------------------------------------------------------------------------------------------------------
// Developed by: Umer Shahid & Muhammad Zain
// --------------------------------------------------------------------------------------------------------------------------------
// Test cases are as follows:
// --------------------------------------------------------------------------------------------------------------------------------
// ------------------------------------------MPRV test in M Mode (with MPP=U-mode)-------------------------------------------------
// 1. PTE has RWX Permissions at Level 4 (Read, write, execute page) and mstatus.MPRV set:
//        Then, in M-Mode, the page is accessed --> required: Load, Store successful and Fetch without translation (PA) successful
// 2. PTE has RWX Permissions at Level 3 (Read, write, execute page) and mstatus.MPRV set:
//        Then, in M-Mode, the page is accessed --> required: Load, Store successful and Fetch without translation (PA) successful
// 3. PTE has RWX Permissions at Level 2 (Read, write, execute page) and mstatus.MPRV set:
//        Then, in M-Mode, the page is accessed --> required: Load, Store successful and Fetch without translation (PA) successful
// 4. PTE has RWX Permissions at Level 1 (Read, write, execute page) and mstatus.MPRV set:
//        Then, in M-Mode, the page is accessed --> required: Load, Store successful and Fetch without translation (PA) successful
// 5. PTE has RWX Permissions at Level 0 (Read, write, execute page) and mstatus.MPRV set:
//        Then, in M-Mode, the page is accessed --> required: Load, Store successful and Fetch without translation (PA) successful
//
// Total Expected Faults :: 0
// --------------------------------------------------------------------------------------------------------------------------------

##### START_TEST_CONFIG #####
# REQUIRED_EXTENSIONS: [I, Sv57]
# MARCH: rv64i_zicsr
# CONFIG_DEPENDENT: true
##### END_TEST_CONFIG #####

#define TEST_FILE "sv57_mstatus_mprv_Umode.S"
#define SIGUPD_COUNT 50
#define rvtest_mtrap_routine
#define rvtest_strap_routine
#define SKIP_MEPC
#define SKIP_MTVAL

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

  LA(a5, rvtest_data_1)       // Using physical address for fetch

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

  SET_REQ_MSTATUS_VAL \STR_PTR

  VERIFICATION_RWX

  LI(   t0, MSTATUS_MPRV)
  CSRC( mstatus, t0)          // Clear mstatus.MPRV

  // Signature Update
  RVTEST_SIGUPD(x2, x5, x4, a2, \STR_PTR)
  RVTEST_SIGUPD(x2, x5, x4, a4, \STR_PTR)
.endm


.macro SET_REQ_MSTATUS_VAL STR_PTR
  LI(   t0, MSTATUS_MPRV)
  CSRS( mstatus, t0)
  LI(   t0, 0x1800)
  CSRC( mstatus, t0)          // Set to Umode
.endm


main:
  li a2, 0x800                // Test signature initialization

//---------------------------------------------------------------------------------------------------------------------------------
//                                   Virtual addresses definition for code and test regions
//---------------------------------------------------------------------------------------------------------------------------------

  // Virtual Address of Test section (rvtest_data_1)
  .set va_data,               0x07028500403000

  // Virtual Address for code region
  .set va_rvtest_code_begin,  0x03000080000000


  // PTE setup for Code Region
  SUPERPAGE_PTE_SETUP_SV57(rvtest_code_begin, (PTE_D | PTE_A | PTE_U | PTE_X | PTE_R | PTE_V), va_rvtest_code_begin, LEVEL4)
  sfence.vma

  // Save area setup for code region
  csrr a0, mscratch
  SAVE_AREA_SETUP(va_rvtest_code_begin, rvtest_code_begin, code)

//---------------------------------------------------------------------------------------------------------------------------------
//                                               Test Cases Start from here
//---------------------------------------------------------------------------------------------------------------------------------

  SATP_SETUP_RV64(sv57)                                                  // Set SATP for virtualization
  sfence.vma                                                             // Flush TLB

//---------------------------------------------------------------------------------------------------------------------------------
//---------------------------------------------------------------------------------------------------------------------------------
//                                                  TESTS AT LEVEL 4
//---------------------------------------------------------------------------------------------------------------------------------
//                  256TB PAGE  Region 1 under test at level 4 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 1: Test in M-Mode | RWX bit set | expected = successful page access
  SUPERPAGE_PTE_SETUP_SV57(rvtest_data_1, (PTE_D | PTE_A | PTE_U | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL4)
  sfence.vma

  TEST_CASES_RUNNER Mmode, va_data, LEVEL4, "test_1"

//---------------------------------------------------------------------------------------------------------------------------------
//---------------------------------------------------------------------------------------------------------------------------------
//                                                  TESTS AT LEVEL 3
//---------------------------------------------------------------------------------------------------------------------------------
//                  512GB PAGE  Region 1 under test at level 3 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 2: Test in M-Mode | RWX bit set | expected = successful page access
  PTE_SETUP_SV57(rvtest_slvl3_pg_tbl, (PTE_V), va_data, LEVEL4)
  SUPERPAGE_PTE_SETUP_SV57(rvtest_data_1, (PTE_D | PTE_A | PTE_U | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL3)
  sfence.vma

  TEST_CASES_RUNNER Mmode, va_data, LEVEL3, "test_2"

//---------------------------------------------------------------------------------------------------------------------------------
//---------------------------------------------------------------------------------------------------------------------------------
//                                                  TESTS AT LEVEL 2
//---------------------------------------------------------------------------------------------------------------------------------
//                  1GB PAGE    Region 1 under test at level 2 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 3: Test in M-Mode | RWX bit set | expected = successful page access
  PTE_SETUP_SV57(rvtest_slvl3_pg_tbl, (PTE_V), va_data, LEVEL4)
  PTE_SETUP_SV57(rvtest_slvl2_pg_tbl, (PTE_V), va_data, LEVEL3)
  SUPERPAGE_PTE_SETUP_SV57(rvtest_data_1, (PTE_D | PTE_A | PTE_U | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL2)
  sfence.vma

  TEST_CASES_RUNNER Mmode, va_data, LEVEL2, "test_3"

//---------------------------------------------------------------------------------------------------------------------------------
//---------------------------------------------------------------------------------------------------------------------------------
//                                                  TESTS AT LEVEL 1
//---------------------------------------------------------------------------------------------------------------------------------
//                  2MB PAGE    Region 1 under test at level 1 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 4: Test in M-Mode | RWX bit set | expected = successful page access
  PTE_SETUP_SV57(rvtest_slvl3_pg_tbl, (PTE_V), va_data, LEVEL4)
  PTE_SETUP_SV57(rvtest_slvl2_pg_tbl, (PTE_V), va_data, LEVEL3)
  PTE_SETUP_SV57(rvtest_slvl1_pg_tbl, (PTE_V), va_data, LEVEL2)
  SUPERPAGE_PTE_SETUP_SV57(rvtest_data_1, (PTE_D | PTE_A | PTE_U | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL1)
  sfence.vma

  TEST_CASES_RUNNER Mmode, va_data, LEVEL1, "test_4"

//---------------------------------------------------------------------------------------------------------------------------------
//---------------------------------------------------------------------------------------------------------------------------------
//                                                  TESTS AT LEVEL 0
//---------------------------------------------------------------------------------------------------------------------------------
//                  2MB PAGE    Region 1 under test at level 0 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 5: Test in M-Mode | RWX bit set | expected = successful page access
  PTE_SETUP_SV57(rvtest_slvl3_pg_tbl, (PTE_V), va_data, LEVEL4)
  PTE_SETUP_SV57(rvtest_slvl2_pg_tbl, (PTE_V), va_data, LEVEL3)
  PTE_SETUP_SV57(rvtest_slvl1_pg_tbl, (PTE_V), va_data, LEVEL2)
  PTE_SETUP_SV57(rvtest_slvl0_pg_tbl, (PTE_V), va_data, LEVEL1)
  PTE_SETUP_SV57(rvtest_data_1, (PTE_D | PTE_A | PTE_U | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL0)
  sfence.vma

  TEST_CASES_RUNNER Mmode, va_data, LEVEL0, "test_5"


//---------------------------------------------------------------------------------------------------------------------------------
RVTEST_CODE_END
RVTEST_DATA_BEGIN

//---------------------------------------------------------------------------------------------------------------------------------
//                                            PHYSICAL ADDRESS REGION FOR TESTING
//---------------------------------------------------------------------------------------------------------------------------------
// Physical Address region under testing for LEVEL 0, 1, 2, 3 and 4
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
rvtest_slvl2_pg_tbl:
    .skip(4096)
rvtest_slvl3_pg_tbl:
    .skip(4096)

canary_mismatch: .string "Testcase signature canary mismatch!"
test_1: .string "\"Mismatch in Test Case 1!\""
test_2: .string "\"Mismatch in Test Case 2!\""
test_3: .string "\"Mismatch in Test Case 3!\""
test_4: .string "\"Mismatch in Test Case 4!\""
test_5: .string "\"Mismatch in Test Case 5!\""

RVTEST_DATA_END
RVTEST_SIG_SETUP
