// --------------------------------------------------------------------------------------------------------------------------------
// Developed by: Umer Shahid & Muhammad Zain
// --------------------------------------------------------------------------------------------------------------------------------
// Test cases are as follows:
// --------------------------------------------------------------------------------------------------------------------------------
// -------------------------------------------------- mstatus.SBE set -------------------------------------------------------------
// 1. Level 3 page set up with RWX Permissions (Read, write, execute):
//        Then, in S-Mode, the page is accessed --> required: No Fault
// 2. Level 2 page set up with RWX Permissions (Read, write, execute):
//        Then, in S-Mode, the page is accessed --> required: No Fault
// 3. Level 1 page set up with RWX Permissions (Read, write, execute):
//        Then, in S-Mode, the page is accessed --> required: No Fault
// 4. Level 0 page set up with RWX Permissions (Read, write, execute):
//        Then, in S-Mode, the page is accessed --> required: No Fault
//
// Total Expected Faults :: 0
// --------------------------------------------------------------------------------------------------------------------------------

##### START_TEST_CONFIG #####
# REQUIRED_EXTENSIONS: [I, Sv48]
# MARCH: rv64i_zicsr
# CONFIG_DEPENDENT: true
##### END_TEST_CONFIG #####

#define TEST_FILE "sv48_mstatus_sbe_set_Smode.S"
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


.macro CHANGE_PTE_TO_BE
  // After PTE_SETUP_SV48 completes, a0 has the PTE (PPN and Permission bits) while t1 has the PTE address
  li a3, 0
  li a4, 0
  li a5, 56
  .rept(8)
    andi a3, a0, 0xFF
    srli a0, a0, 8
    sll  a3, a3, a5
    or   a4, a4, a3
    addi a5, a5, -8
  .endr
  SREG a4, 0(t1)
.endm


main:
  li a2, 0x800                // Test signature initialization

//---------------------------------------------------------------------------------------------------------------------------------
//                                   Virtual addresses definition for code and test regions
//---------------------------------------------------------------------------------------------------------------------------------

  // Virtual Address of Test section (rvtest_data_1)
  .set va_data,               0x028500403000

  // Virtual Address for code region
  .set va_rvtest_code_begin,  0x030080000000


  // PTE setup for Code Region
  SUPERPAGE_PTE_SETUP_SV48(rvtest_code_begin, (PTE_D | PTE_A | PTE_X | PTE_R | PTE_V), va_rvtest_code_begin, LEVEL3)
  CHANGE_PTE_TO_BE
  sfence.vma

  // Save area setup for code region
  csrr a0, mscratch
  SAVE_AREA_SETUP(va_rvtest_code_begin, rvtest_code_begin, code)

//---------------------------------------------------------------------------------------------------------------------------------
//                                               Test Cases Start from here
//---------------------------------------------------------------------------------------------------------------------------------

  SATP_SETUP_RV64(sv48)                                                  // Set SATP for virtualization
  sfence.vma                                                             // Flush TLB

  LI(   t0, MSTATUS_SBE)
  CSRS( mstatus, t0)                                                     // Set mstatus.SBE (Supervisor Big Endian)

//---------------------------------------------------------------------------------------------------------------------------------
//---------------------------------------------------------------------------------------------------------------------------------
//                                                  TESTS AT LEVEL 3
//---------------------------------------------------------------------------------------------------------------------------------
//                  512GB PAGE  Region 1 under test at level 3 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 1: Test in S-Mode | RWX bit set | expected = successful page access
  SUPERPAGE_PTE_SETUP_SV48(rvtest_data_1, (PTE_D | PTE_A | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL3)
  CHANGE_PTE_TO_BE
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL3, "test_1"

//---------------------------------------------------------------------------------------------------------------------------------
//---------------------------------------------------------------------------------------------------------------------------------
//                                                  TESTS AT LEVEL 2
//---------------------------------------------------------------------------------------------------------------------------------
//                  1GB PAGE    Region 1 under test at level 2 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 2: Test in S-Mode | RWX bit set | expected = successful page access
  PTE_SETUP_SV48(rvtest_slvl2_pg_tbl, (PTE_V), va_data, LEVEL3)
  CHANGE_PTE_TO_BE
  SUPERPAGE_PTE_SETUP_SV48(rvtest_data_1, (PTE_D | PTE_A | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL2)
  CHANGE_PTE_TO_BE
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL2, "test_2"

//---------------------------------------------------------------------------------------------------------------------------------
//---------------------------------------------------------------------------------------------------------------------------------
//                                                  TESTS AT LEVEL 1
//---------------------------------------------------------------------------------------------------------------------------------
//                  2MB PAGE    Region 1 under test at level 1 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 3: Test in S-Mode | RWX bit set | expected = successful page access
  PTE_SETUP_SV48(rvtest_slvl2_pg_tbl, (PTE_V), va_data, LEVEL3)
  CHANGE_PTE_TO_BE
  PTE_SETUP_SV48(rvtest_slvl1_pg_tbl, (PTE_V), va_data, LEVEL2)
  CHANGE_PTE_TO_BE
  SUPERPAGE_PTE_SETUP_SV48(rvtest_data_1, (PTE_D | PTE_A | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL1)
  CHANGE_PTE_TO_BE
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL1, "test_3"

//---------------------------------------------------------------------------------------------------------------------------------
//---------------------------------------------------------------------------------------------------------------------------------
//                                                  TESTS AT LEVEL 0
//---------------------------------------------------------------------------------------------------------------------------------
//                  4KB PAGE    Region 1 under test at level 0 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 4: Test in S-Mode | RWX bit set | expected = successful page access
  PTE_SETUP_SV48(rvtest_slvl2_pg_tbl, (PTE_V), va_data, LEVEL3)
  CHANGE_PTE_TO_BE
  PTE_SETUP_SV48(rvtest_slvl1_pg_tbl, (PTE_V), va_data, LEVEL2)
  CHANGE_PTE_TO_BE
  PTE_SETUP_SV48(rvtest_slvl0_pg_tbl, (PTE_V), va_data, LEVEL1)
  CHANGE_PTE_TO_BE
  PTE_SETUP_SV48(rvtest_data_1, (PTE_D | PTE_A | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL0)
  CHANGE_PTE_TO_BE
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL0, "test_4"


//---------------------------------------------------------------------------------------------------------------------------------
RVTEST_CODE_END
RVTEST_DATA_BEGIN

//---------------------------------------------------------------------------------------------------------------------------------
//                                            PHYSICAL ADDRESS REGION FOR TESTING
//---------------------------------------------------------------------------------------------------------------------------------
// Physical Address region under testing for LEVEL 0, 1, 2 and 3
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

canary_mismatch: .string "Testcase signature canary mismatch!"
test_1: .string "\"Mismatch in Test Case 1!\""
test_2: .string "\"Mismatch in Test Case 2!\""
test_3: .string "\"Mismatch in Test Case 3!\""
test_4: .string "\"Mismatch in Test Case 4!\""

RVTEST_DATA_END
RVTEST_SIG_SETUP
