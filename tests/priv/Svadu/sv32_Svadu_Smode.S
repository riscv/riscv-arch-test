// --------------------------------------------------------------------------------------------------------------------------------
// Developed by: Umer Shahid & Muhammad Zain
// --------------------------------------------------------------------------------------------------------------------------------
// Test cases are as follows:
// --------------------------------------------------------------------------------------------------------------------------------
// 1. PTE.A unset, PTE.D set for three distinct leaf PTEs at level 1, RWX permissions (read, write, execute page):
//        Then, in S-Mode, the pages are accessed --> required: No fault
// 2. PTE.D unset, PTE.A set for three distinct leaf PTEs at level 1, RWX permissions (read, write, execute page):
//        Then, in S-Mode, the pages are accessed --> required: No fault
// 3. Both PTE.A & PTE.D unset for three distinct leaf PTEs at level 1, RWX permissions (read, write, execute page):
//        Then, in S-Mode, the pages are accessed --> required: No fault
// 4. PTE.A unset, PTE.D set for three distinct leaf PTEs at level 0, RWX permissions (read, write, execute page):
//        Then, in S-Mode, the pages are accessed --> required: No fault
// 5. PTE.D unset, PTE.A set for three distinct leaf PTEs at level 0, RWX permissions (read, write, execute page):
//        Then, in S-Mode, the pages are accessed --> required: No fault
// 6. Both PTE.A & PTE.D unset for three distinct leaf PTEs at level 0, RWX permissions (read, write, execute page):
//        Then, in S-Mode, the pages are accessed --> required: No fault
//
// Total Expected Faults :: 0
// --------------------------------------------------------------------------------------------------------------------------------

// Remove NORUN once Sail supports Svadu
##### START_TEST_CONFIG #####
# REQUIRED_EXTENSIONS: [I, Sv32, Svadu, NORUN]
# MARCH: rv32i_zicsr
# CONFIG_DEPENDENT: true
##### END_TEST_CONFIG #####

#define TEST_FILE "sv32_Svadu_Smode.S"
#define SIGUPD_COUNT 45
#define rvtest_mtrap_routine
#define rvtest_strap_routine
#define RVTEST_PRIV_TEST
#define SKIP_MEPC

#include "riscv_arch_test.h"

RVTEST_BEGIN

//---------------------------------------------------------------------------------------------------------------------------------
// Test RWX permissions
.macro VERIFICATION_RWX TEST_CASE
  addi a2, a2, 16

  // Test store permission
  \TEST_CASE\()_store:
  sw  a2, 20(a0)
  nop

  // Test load permission
  \TEST_CASE\()_load:
  lw a3, 20(a1)
  nop

  // Test execute permission
  LI(  x4, 0xACCE)            // Store a value which is to be checked in trap handler
  \TEST_CASE\()_exec:
  jalr ra, a5, 0
  nop
.endm

.macro TEST_CASES_RUNNER LOWER_MODE, VA_W, VA_R, VA_X, level, TEST_CASE

  // Adjust offset of VAs to point to test region
  .set VA_SHIFT, (\level*10)+12
  LI(a0, (\VA_W>>VA_SHIFT)<<VA_SHIFT)
  LI(a1, (\VA_R>>VA_SHIFT)<<VA_SHIFT)
  LI(a5, (\VA_X>>VA_SHIFT)<<VA_SHIFT)
  LA(t0, rvtest_data_1)
  slli t0, t0, 32-VA_SHIFT
  srli t0, t0, 32-VA_SHIFT
  add  a0, a0, t0             // a0 has VA for Store
  add  a1, a1, t0             // a1 has VA for Load
  add  a5, a5, t0             // a5 has VA for Execute

  RVTEST_GOTO_LOWER_MODE \LOWER_MODE

  VERIFICATION_RWX \TEST_CASE

  RVTEST_GOTO_MMODE

  // Signature Update
  RVTEST_SIGUPD(x2, x5, x4, a2, \TEST_CASE\()_store, \TEST_CASE\()_store_str)
  RVTEST_SIGUPD(x2, x5, x4, a3, \TEST_CASE\()_load, \TEST_CASE\()_load_str)
  RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_exec, \TEST_CASE\()_exec_str)

  // Read PTEs to check if DA bits have been updated correctly
  .if \level == LEVEL1
      LA(a0, rvtest_Sroot_pg_tbl)
  .elseif \level == LEVEL0
      LA(a0, rvtest_slvl0_pg_tbl)
  .endif
  \TEST_CASE\()_read_store_pte:
  lw   a4, 4(a0)                   // PTE used during Store
  RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_read_store_pte, \TEST_CASE\()_read_store_pte_str)
  \TEST_CASE\()_read_load_pte:
  lw   a4, 8(a0)                   // PTE used during Load
  RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_read_load_pte, \TEST_CASE\()_read_load_pte_str)
  \TEST_CASE\()_read_exec_pte:
  lw   a4, 12(a0)                  // PTE used during Fetch
  RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_read_exec_pte, \TEST_CASE\()_read_exec_pte_str)

.endm


main:
  li a2, 0x800              // Test signature initialization

//---------------------------------------------------------------------------------------------------------------------------------
//                                   Virtual addresses definition for code and test regions
//---------------------------------------------------------------------------------------------------------------------------------

  // Each access (store, load & execute) within TEST_CASE_RUNNER will update DA bits.
  // Therefore, use 3 different VAs that point to 3 different PTEs
  .set va_data_l1_w,          0x00400000
  .set va_data_l1_r,          0x00800000
  .set va_data_l1_x,          0x00C00000
  .set va_data_l0_w,          0x01001000
  .set va_data_l0_r,          0x01002000
  .set va_data_l0_x,          0x01003000

  // Virtual Address for code region
  .set va_rvtest_code_begin,  0x90000000


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

  LI(t0, MENVCFGH_ADUE)
  CSRS(menvcfgh, t0)                                                     // Enable Svadu

//---------------------------------------------------------------------------------------------------------------------------------
//---------------------------------------------------------------------------------------------------------------------------------
//                                                    TESTS AT LEVEL 1
//---------------------------------------------------------------------------------------------------------------------------------
//                    4MB PAGE    Region 1 under test at level 1 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 1: PTE.A unset | Test in S-Mode | RWX bit set | expected = No fault
  SUPERPAGE_PTE_SETUP_SV32(rvtest_data_1, (PTE_D | PTE_X | PTE_W | PTE_R | PTE_V), va_data_l1_w, LEVEL1)
  SUPERPAGE_PTE_SETUP_SV32(rvtest_data_1, (PTE_D | PTE_X | PTE_W | PTE_R | PTE_V), va_data_l1_r, LEVEL1)
  SUPERPAGE_PTE_SETUP_SV32(rvtest_data_1, (PTE_D | PTE_X | PTE_W | PTE_R | PTE_V), va_data_l1_x, LEVEL1)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data_l1_w, va_data_l1_r, va_data_l1_x, LEVEL1, test1

//---------------------------------------------------------------------------------------------------------------------------------
//                    4MB PAGE    Region 1 under test at level 1 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 2: PTE.D unset | Test in S-Mode | RWX bit set | expected = No fault
  SUPERPAGE_PTE_SETUP_SV32(rvtest_data_1, (PTE_A | PTE_X | PTE_W | PTE_R | PTE_V), va_data_l1_w, LEVEL1)
  SUPERPAGE_PTE_SETUP_SV32(rvtest_data_1, (PTE_A | PTE_X | PTE_W | PTE_R | PTE_V), va_data_l1_r, LEVEL1)
  SUPERPAGE_PTE_SETUP_SV32(rvtest_data_1, (PTE_A | PTE_X | PTE_W | PTE_R | PTE_V), va_data_l1_x, LEVEL1)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data_l1_w, va_data_l1_r, va_data_l1_x, LEVEL1, test2

//---------------------------------------------------------------------------------------------------------------------------------
//                    4MB PAGE    Region 1 under test at level 1 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 3: Both PTE.D & PTE.A unset | Test in S-Mode | RWX bit set | expected = No fault
  SUPERPAGE_PTE_SETUP_SV32(rvtest_data_1, (PTE_X | PTE_W | PTE_R | PTE_V), va_data_l1_w, LEVEL1)
  SUPERPAGE_PTE_SETUP_SV32(rvtest_data_1, (PTE_X | PTE_W | PTE_R | PTE_V), va_data_l1_r, LEVEL1)
  SUPERPAGE_PTE_SETUP_SV32(rvtest_data_1, (PTE_X | PTE_W | PTE_R | PTE_V), va_data_l1_x, LEVEL1)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data_l1_w, va_data_l1_r, va_data_l1_x, LEVEL1, test3


//---------------------------------------------------------------------------------------------------------------------------------
//---------------------------------------------------------------------------------------------------------------------------------
//                                                    TESTS AT LEVEL 0
//---------------------------------------------------------------------------------------------------------------------------------
//                    4KB PAGE    Region 1 under test at level 0 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 4: PTE.A unset | Test in S-Mode | RWX bit set | expected = No fault
  PTE_SETUP_SV32(rvtest_slvl0_pg_tbl, (PTE_V), va_data_l0_w, LEVEL1)
  PTE_SETUP_SV32(rvtest_data_1, (PTE_D | PTE_X | PTE_W | PTE_R | PTE_V), va_data_l0_w, LEVEL0)
  PTE_SETUP_SV32(rvtest_data_1, (PTE_D | PTE_X | PTE_W | PTE_R | PTE_V), va_data_l0_r, LEVEL0)
  PTE_SETUP_SV32(rvtest_data_1, (PTE_D | PTE_X | PTE_W | PTE_R | PTE_V), va_data_l0_x, LEVEL0)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data_l0_w, va_data_l0_r, va_data_l0_x, LEVEL0, test4

//---------------------------------------------------------------------------------------------------------------------------------
//                    4KB PAGE    Region 1 under test at level 0 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 5: PTE.D unset | Test in S-Mode | RWX bit set | expected = No fault
  PTE_SETUP_SV32(rvtest_slvl0_pg_tbl, (PTE_V), va_data_l0_w, LEVEL1)
  PTE_SETUP_SV32(rvtest_data_1, (PTE_A | PTE_X | PTE_W | PTE_R | PTE_V), va_data_l0_w, LEVEL0)
  PTE_SETUP_SV32(rvtest_data_1, (PTE_A | PTE_X | PTE_W | PTE_R | PTE_V), va_data_l0_r, LEVEL0)
  PTE_SETUP_SV32(rvtest_data_1, (PTE_A | PTE_X | PTE_W | PTE_R | PTE_V), va_data_l0_x, LEVEL0)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data_l0_w, va_data_l0_r, va_data_l0_x, LEVEL0, test5

//---------------------------------------------------------------------------------------------------------------------------------
//                    4KB PAGE    Region 1 under test at level 0 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 6: Both PTE.D & PTE.A unset | Test in S-Mode | RWX bit set | expected = No fault
  PTE_SETUP_SV32(rvtest_slvl0_pg_tbl, (PTE_V), va_data_l0_w, LEVEL1)
  PTE_SETUP_SV32(rvtest_data_1, (PTE_X | PTE_W | PTE_R | PTE_V), va_data_l0_w, LEVEL0)
  PTE_SETUP_SV32(rvtest_data_1, (PTE_X | PTE_W | PTE_R | PTE_V), va_data_l0_r, LEVEL0)
  PTE_SETUP_SV32(rvtest_data_1, (PTE_X | PTE_W | PTE_R | PTE_V), va_data_l0_x, LEVEL0)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data_l0_w, va_data_l0_r, va_data_l0_x, LEVEL0, test6


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
  addi a4, a2, 4
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

test1_store_str:          .string "\"Mismatch during sw in Test Case 1!\""
test1_load_str:           .string "\"Mismatch during lw in Test Case 1!\""
test1_exec_str:           .string "\"Mismatch during jalr in Test Case 1!\""
test1_read_store_pte_str: .string "\"Mismatch in PTE used during sw in Test Case 1!\""
test1_read_load_pte_str:  .string "\"Mismatch in PTE used during lw in Test Case 1!\""
test1_read_exec_pte_str:  .string "\"Mismatch in PTE used during jalr in Test Case 1!\""
test2_store_str:          .string "\"Mismatch during sw in Test Case 2!\""
test2_load_str:           .string "\"Mismatch during lw in Test Case 2!\""
test2_exec_str:           .string "\"Mismatch during jalr in Test Case 2!\""
test2_read_store_pte_str: .string "\"Mismatch in PTE used during sw in Test Case 2!\""
test2_read_load_pte_str:  .string "\"Mismatch in PTE used during lw in Test Case 2!\""
test2_read_exec_pte_str:  .string "\"Mismatch in PTE used during jalr in Test Case 2!\""
test3_store_str:          .string "\"Mismatch during sw in Test Case 3!\""
test3_load_str:           .string "\"Mismatch during lw in Test Case 3!\""
test3_exec_str:           .string "\"Mismatch during jalr in Test Case 3!\""
test3_read_store_pte_str: .string "\"Mismatch in PTE used during sw in Test Case 3!\""
test3_read_load_pte_str:  .string "\"Mismatch in PTE used during lw in Test Case 3!\""
test3_read_exec_pte_str:  .string "\"Mismatch in PTE used during jalr in Test Case 3!\""
test4_store_str:          .string "\"Mismatch during sw in Test Case 4!\""
test4_load_str:           .string "\"Mismatch during lw in Test Case 4!\""
test4_exec_str:           .string "\"Mismatch during jalr in Test Case 4!\""
test4_read_store_pte_str: .string "\"Mismatch in PTE used during sw in Test Case 4!\""
test4_read_load_pte_str:  .string "\"Mismatch in PTE used during lw in Test Case 4!\""
test4_read_exec_pte_str:  .string "\"Mismatch in PTE used during jalr in Test Case 4!\""
test5_store_str:          .string "\"Mismatch during sw in Test Case 5!\""
test5_load_str:           .string "\"Mismatch during lw in Test Case 5!\""
test5_exec_str:           .string "\"Mismatch during jalr in Test Case 5!\""
test5_read_store_pte_str: .string "\"Mismatch in PTE used during sw in Test Case 5!\""
test5_read_load_pte_str:  .string "\"Mismatch in PTE used during lw in Test Case 5!\""
test5_read_exec_pte_str:  .string "\"Mismatch in PTE used during jalr in Test Case 5!\""
test6_store_str:          .string "\"Mismatch during sw in Test Case 6!\""
test6_load_str:           .string "\"Mismatch during lw in Test Case 6!\""
test6_exec_str:           .string "\"Mismatch during jalr in Test Case 6!\""
test6_read_store_pte_str: .string "\"Mismatch in PTE used during sw in Test Case 6!\""
test6_read_load_pte_str:  .string "\"Mismatch in PTE used during lw in Test Case 6!\""
test6_read_exec_pte_str:  .string "\"Mismatch in PTE used during jalr in Test Case 6!\""

RVTEST_DATA_END
RVTEST_SIG_SETUP
