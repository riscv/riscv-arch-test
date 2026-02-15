// --------------------------------------------------------------------------------------------------------------------------------
// Test cases are as follows:
// --------------------------------------------------------------------------------------------------------------------------------
// 1. PTE.G set for the page at level 1:
//      Then, in S-Mode, the page is accessed --> required: Successful page table walk
//      sfence.vma with ASID flushes TLB entries for that ASID, keeping global (G=1) entries intact.
//      Since the page is global, it remains accessible without a new page table walk on second access.
// 2. PTE.G set for the page at level 0:
//      Then, in S-Mode, the page is accessed --> required: Successful page table walk
//      sfence.vma with ASID flushes TLB entries for that ASID, keeping global (G=1) entries intact.
//      Since the page is global, it remains accessible without a new page table walk on second access.
//
// NOTE: ACTs can't check if a page table walk occurred. This test only makes sure that second access succeeds
//       after invalidating the TLB.
//
// Total Expected Faults :: 0
//---------------------------------------------------------------------------------------------------------------------------------

##### START_TEST_CONFIG #####
# REQUIRED_EXTENSIONS: [I, Sv32]
# MARCH: rv32i_zicsr
# CONFIG_DEPENDENT: true
##### END_TEST_CONFIG #####

#define TEST_FILE "sv32_global_pte_Smode.S"
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

  .if \level == LEVEL1
    // Adjust offset of VA to point to test region
    LI(  a5, (\VA>>22)<<22)
    LA(  a4, rvtest_data_1)
    slli a4, a4, 10
    srli a4, a4, 10
    add  a5, a5, a4
  .else
    LI(  a5, \VA)
  .endif

  RVTEST_GOTO_LOWER_MODE \LOWER_MODE

  VERIFICATION_RWX

  RVTEST_GOTO_MMODE

  // Signature Update
  RVTEST_SIGUPD(x2, x5, x4, a2, \STR_PTR)
  RVTEST_SIGUPD(x2, x5, x4, a4, \STR_PTR)
.endm


main:
  li a2, 0x800                // Test signature initialization

//---------------------------------------------------------------------------------------------------------------------------------
//                                   Virtual addresses definition for code and test regions
//---------------------------------------------------------------------------------------------------------------------------------

  // Virtual Address of Test section (rvtest_data_1)
  .set va_data,               0x90407000

  // Virtual Address for code region
  .set va_rvtest_code_begin,  0x30000000


  // PTE setup for Code Region
  SUPERPAGE_PTE_SETUP_SV32(rvtest_code_begin, (PTE_D | PTE_A | PTE_X | PTE_R | PTE_V), va_rvtest_code_begin, LEVEL1)
  sfence.vma

  // Save area setup for code region
  csrr a0, mscratch
  SAVE_AREA_SETUP(va_rvtest_code_begin, rvtest_code_begin, code)

//---------------------------------------------------------------------------------------------------------------------------------
//                                               Test Cases Start from here
//---------------------------------------------------------------------------------------------------------------------------------

  SATP_SETUP_SV32                                                        // Set SATP for virtualization
  sfence.vma                                                             // Flush TLB

//---------------------------------------------------------------------------------------------------------------------------------
//---------------------------------------------------------------------------------------------------------------------------------
//                                                  TESTS AT LEVEL 1
//---------------------------------------------------------------------------------------------------------------------------------
//                  4MB PAGE    Region 1 under test at level 1 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 1: Test in S-Mode | G bit set | expected = successful page access and no page table walk on second access
  SUPERPAGE_PTE_SETUP_SV32(rvtest_data_1, (PTE_D | PTE_A | PTE_G | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL1)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL1, "test_1_access_1"

  CSRR( t0, satp)                                              // Extract ASID (Sv32, ASID is in bits 30:22 of satp)
  slli  t0, t0, 1
  srli  t0, t0, 23
  SFENCE_VMA

  TEST_CASES_RUNNER Smode, va_data, LEVEL1, "test_1_access_2"  // No pagetable walk, as the PTE is not invalidated by sfence.vma


//---------------------------------------------------------------------------------------------------------------------------------
//---------------------------------------------------------------------------------------------------------------------------------
//                                                  TESTS AT LEVEL 0
//---------------------------------------------------------------------------------------------------------------------------------
//                  4KB PAGE    Region 1 under test at level 0 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 4: Test in S-Mode | G bit set | expected = successful page access and no page table walk on second access
  PTE_SETUP_SV32(rvtest_slvl0_pg_tbl, (PTE_V), va_data, LEVEL1)
  PTE_SETUP_SV32(rvtest_data_1, (PTE_D | PTE_A | PTE_G | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL0)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL0, "test_2_access_1"

  CSRR( t0, satp)                                              // Extract ASID (Sv32, ASID is in bits 30:22 of satp)
  slli  t0, t0, 1
  srli  t0, t0, 23
  SFENCE_VMA

  TEST_CASES_RUNNER Smode, va_data, LEVEL0, "test_2_access_2"  // No pagetable walk, as the PTE is not invalidated by sfence.vma


//---------------------------------------------------------------------------------------------------------------------------------
RVTEST_CODE_END
RVTEST_DATA_BEGIN

//---------------------------------------------------------------------------------------------------------------------------------
//                                            PHYSICAL ADDRESS REGION FOR TESTING
//---------------------------------------------------------------------------------------------------------------------------------
// Physical Address region under testing for LEVEL 0 and 1
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

// Page Table
.align 12
rvtest_slvl0_pg_tbl:
    .skip(4096)

canary_mismatch: .string "Testcase signature canary mismatch!"
test_1_access_1: .string "\"Mismatch in first TEST_CASE_RUNNER of Test Case 1!\""
test_1_access_2: .string "\"Mismatch in second TEST_CASE_RUNNER of Test Case 1!\""
test_2_access_1: .string "\"Mismatch in first TEST_CASE_RUNNER of Test Case 2!\""
test_2_access_2: .string "\"Mismatch in second TEST_CASE_RUNNER of Test Case 2!\""

RVTEST_DATA_END
RVTEST_SIG_SETUP
