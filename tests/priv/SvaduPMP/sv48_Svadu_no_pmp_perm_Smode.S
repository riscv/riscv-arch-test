// --------------------------------------------------------------------------------------------------------------------------------
// Developed by: Umer Shahid & Muhammad Zain
// --------------------------------------------------------------------------------------------------------------------------------
// Test cases are as follows:
// --------------------------------------------------------------------------------------------------------------------------------
// Configure level 3 PTE as PMP NAPOT region without W permission (pmp0cfg0)
// 1. Setup a PTE at Level 3 with PTE.A unset. RWX permissions given
//      → Then, in S-Mode, the page is accessed --> required: Store access fault, Load access fault, Instruction access fault
// 2. Setup a PTE at Level 3 with PTE.D unset. RWX permissions given
//      → Then, in S-Mode, the page is accessed --> required: Store access fault
// 3. Setup a PTE at Level 3 with PTE.D & PTE.A unset. RWX permissions given
//      → Then, in S-Mode, the page is accessed --> required: Store access fault, Load access fault, Instruction access fault
//
// Configure level 2 PTE as PMP NAPOT region without W permission (pmp0cfg0)
// 4. Setup a PTE at Level 2 with PTE.A unset. RWX permissions given
//      → Then, in S-Mode, the page is accessed --> required: Store access fault, Load access fault, Instruction access fault
// 5. Setup a PTE at Level 2 with PTE.D unset. RWX permissions given
//      → Then, in S-Mode, the page is accessed --> required: Store access fault
// 6. Setup a PTE at Level 2 with PTE.D & PTE.A unset. RWX permissions given
//      → Then, in S-Mode, the page is accessed --> required: Store access fault, Load access fault, Instruction access fault
//
// Configure level 1 PTE as PMP NAPOT region without W permission (pmp0cfg0)
// 7. Setup a PTE at Level 1 with PTE.A unset. RWX permissions given
//      → Then, in S-Mode, the page is accessed --> required: Store access fault, Load access fault, Instruction access fault
// 8. Setup a PTE at Level 1 with PTE.D unset. RWX permissions given
//      → Then, in S-Mode, the page is accessed --> required: Store access fault
// 9. Setup a PTE at Level 1 with PTE.D & PTE.A unset. RWX permissions given
//      → Then, in S-Mode, the page is accessed --> required: Store access fault, Load access fault, Instruction access fault
//
// Configure level 0 PTE as PMP NAPOT region without W permission (pmp0cfg0)
// 10. Setup a PTE at Level 0 with PTE.A unset. RWX permissions given
//      → Then, in S-Mode, the page is accessed --> required: Store access fault, Load access fault, Instruction access fault
// 11. Setup a PTE at Level 0 with PTE.D unset. RWX permissions given
//      → Then, in S-Mode, the page is accessed --> required: Store access fault
// 12. Setup a PTE at Level 0 with PTE.D & PTE.A unset. RWX permissions given
//      → Then, in S-Mode, the page is accessed --> required: Store access fault, Load access fault, Instruction access fault
//
// Total Expected Faults :: 28
// --------------------------------------------------------------------------------------------------------------------------------

##### START_TEST_CONFIG #####
# REQUIRED_EXTENSIONS: [I, Sv48, Svadu]
# params:
#   NUM_PMP_ENTRIES: '>0'
# MARCH: rv64i_zicsr
# CONFIG_DEPENDENT: true
##### END_TEST_CONFIG #####

#define TEST_FILE "sv48_Svadu_no_pmp_perm_Smode.S"
#define SIGUPD_COUNT 55
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
  sw  a2, 20(a5)
  nop

  // Test load permission
  \TEST_CASE\()_load:
  lw a3, 20(a5)
  nop

  // Test execute permission
  LI(  x4, 0xACCE)            // Store a value which is to be checked in trap handler
  \TEST_CASE\()_exec:
  jalr ra, a5, 0
  nop
.endm

.macro TEST_CASES_RUNNER LOWER_MODE, VA, level, TEST_CASE

  // Adjust offset of VA to point to test region
  .set VA_SHIFT, (\level*9)+12
  LI(a5, (\VA>>VA_SHIFT)<<VA_SHIFT)
  LA(a0, rvtest_data_1)
  slli a0, a0, 64-VA_SHIFT
  srli a0, a0, 64-VA_SHIFT
  add  a5, a5, a0             // Virtual Address

  RVTEST_GOTO_LOWER_MODE \LOWER_MODE

  VERIFICATION_RWX \TEST_CASE

  RVTEST_GOTO_MMODE

  // Signature Update
  RVTEST_SIGUPD(x2, x5, x4, a2, \TEST_CASE\()_store, \TEST_CASE\()_store_str)
  RVTEST_SIGUPD(x2, x5, x4, a3, \TEST_CASE\()_load, \TEST_CASE\()_load_str)
  RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_exec, \TEST_CASE\()_exec_str)

  // Read PTE to confirm that DPTE.As haven't been incorrectly updated
  .if \level == LEVEL3
    LA( a0, rvtest_Sroot_pg_tbl)
  .elseif \level == LEVEL2
    LA( a0, rvtest_slvl2_pg_tbl)
  .elseif \level == LEVEL1
    LA( a0, rvtest_slvl1_pg_tbl)
  .elseif \level == LEVEL0
    LA( a0, rvtest_slvl0_pg_tbl)
  .endif
  \TEST_CASE\()_read_pte:
  ld  a4, 0(a0)
  RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_read_pte, \TEST_CASE\()_read_pte_str)

.endm

// PMP Macros
#define PMP_GLOBAL_RWX        (((PMP_TOR | PMP_X | PMP_W | PMP_R) & 0xFF) << PMP2_CFG_SHIFT)
#define PMP0CFG_RX            (((PMP_NAPOT | PMP_X | PMP_R) & 0xFF) << PMP0_CFG_SHIFT)


main:
  li a2, 0x800              // Test signature initialization

//---------------------------------------------------------------------------------------------------------------------------------
//                                                    Setup pmpaddr registers
//---------------------------------------------------------------------------------------------------------------------------------

  li t2, 0                  // Set PMP permission for all memory in pmp2cfg0 (TOR)
  csrw pmpaddr1, t2
  li t2, -1
  csrw pmpaddr2, t2

//---------------------------------------------------------------------------------------------------------------------------------
//                                   Virtual addresses definition for code and test regions
//---------------------------------------------------------------------------------------------------------------------------------

  // Virtual Address of Test section (rvtest_data_1)
  .set va_data,               0x000000000000

  // Virtual Address for code region
  .set va_rvtest_code_begin,  0x030080000000


  // PTE setup for Code Region
  SUPERPAGE_PTE_SETUP_SV48(rvtest_code_begin, (PTE_D | PTE_A | PTE_X | PTE_R | PTE_V), va_rvtest_code_begin, LEVEL3)
  sfence.vma

  // Save area setup for code region
  csrr a0, mscratch
  SAVE_AREA_SETUP(va_rvtest_code_begin, rvtest_code_begin, code)

//---------------------------------------------------------------------------------------------------------------------------------
//                                               Test Cases Start from here
//---------------------------------------------------------------------------------------------------------------------------------

  SATP_SETUP_RV64(sv48)                                                  // Set SATP for virtualization
  sfence.vma                                                             // Flush TLB

  LI(t0, MENVCFG_ADUE)
  CSRS(menvcfg, t0)                                                      // Enable Svadu

//---------------------------------------------------------------------------------------------------------------------------------
//---------------------------------------------------------------------------------------------------------------------------------
//                               Configure level 3 PTE as PMP NAPOT region with no write permission
//---------------------------------------------------------------------------------------------------------------------------------
//---------------------------------------------------------------------------------------------------------------------------------

  LA (t2, rvtest_Sroot_pg_tbl)
  srl t2, t2, PMP_SHIFT
  LI (t1, ((1<<RVMODEL_PMP_GRAIN)-1)>>1)    // Minimum range is 8 Bytes (1 PTE). Increases as G increases
  or t2, t2, t1
  CSRW(pmpaddr0, t2)

  LI (t2, PMP_GLOBAL_RWX | PMP0CFG_RX)
  write_pmpcfg0:
  RVTEST_SIGUPD_CSR_WRITE(pmpcfg0, t2, write_pmpcfg0, write_pmpcfg0_str)

//---------------------------------------------------------------------------------------------------------------------------------
//---------------------------------------------------------------------------------------------------------------------------------
//                                                    TESTS AT LEVEL 3
//---------------------------------------------------------------------------------------------------------------------------------
//                    512GB PAGE    Region 1 under test at level 3 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 1: PTE.A unset | Test in S-Mode | RWX bit set | expected = Store, Load & Instr access faults
  SUPERPAGE_PTE_SETUP_SV48(rvtest_data_1, (PTE_D | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL3)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL3, test1

//---------------------------------------------------------------------------------------------------------------------------------
//                    512GB PAGE    Region 1 under test at level 3 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 2: PTE.D unset | Test in S-Mode | RWX bit set | expected = Store access fault
  SUPERPAGE_PTE_SETUP_SV48(rvtest_data_1, (PTE_A | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL3)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL3, test2

//---------------------------------------------------------------------------------------------------------------------------------
//                    512GB PAGE    Region 1 under test at level 3 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 3: Both PTE.D & PTE.A unset | Test in S-Mode | RWX bit set | expected = Store, Load & Instr access faults
  SUPERPAGE_PTE_SETUP_SV48(rvtest_data_1, (PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL3)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL3, test3


//---------------------------------------------------------------------------------------------------------------------------------
//---------------------------------------------------------------------------------------------------------------------------------
//                               Configure level 2 PTE as PMP NAPOT region with no write permission
//---------------------------------------------------------------------------------------------------------------------------------
//---------------------------------------------------------------------------------------------------------------------------------

  LA (t2, rvtest_slvl2_pg_tbl)
  srl t2, t2, PMP_SHIFT
  LI (t1, ((1<<RVMODEL_PMP_GRAIN)-1)>>1)    // Minimum range is 8 Bytes (1 PTE). Increases as G increases
  or t2, t2, t1
  CSRW(pmpaddr0, t2)

//---------------------------------------------------------------------------------------------------------------------------------
//---------------------------------------------------------------------------------------------------------------------------------
//                                                    TESTS AT LEVEL 2
//---------------------------------------------------------------------------------------------------------------------------------
//                    1GB PAGE    Region 1 under test at level 2 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 4: PTE.A unset | Test in S-Mode | RWX bit set | expected = Store, Load & Instr access faults
  PTE_SETUP_SV48(rvtest_slvl2_pg_tbl, (PTE_V), va_data, LEVEL3)
  SUPERPAGE_PTE_SETUP_SV48(rvtest_data_1, (PTE_D | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL2)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL2, test4

//---------------------------------------------------------------------------------------------------------------------------------
//                    1GB PAGE    Region 1 under test at level 2 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 5: PTE.D unset | Test in S-Mode | RWX bit set | expected = Store access fault
  PTE_SETUP_SV48(rvtest_slvl2_pg_tbl, (PTE_V), va_data, LEVEL3)
  SUPERPAGE_PTE_SETUP_SV48(rvtest_data_1, (PTE_A | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL2)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL2, test5

//---------------------------------------------------------------------------------------------------------------------------------
//                    1GB PAGE    Region 1 under test at level 2 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 6: Both PTE.D & PTE.A unset | Test in S-Mode | RWX bit set | expected = Store, Load & Instr access faults
  PTE_SETUP_SV48(rvtest_slvl2_pg_tbl, (PTE_V), va_data, LEVEL3)
  SUPERPAGE_PTE_SETUP_SV48(rvtest_data_1, (PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL2)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL2, test6


//---------------------------------------------------------------------------------------------------------------------------------
//---------------------------------------------------------------------------------------------------------------------------------
//                               Configure level 1 PTE as PMP NAPOT region with no write permission
//---------------------------------------------------------------------------------------------------------------------------------
//---------------------------------------------------------------------------------------------------------------------------------

  LA (t2, rvtest_slvl1_pg_tbl)
  srl t2, t2, PMP_SHIFT
  LI (t1, ((1<<RVMODEL_PMP_GRAIN)-1)>>1)    // Minimum range is 8 Bytes (1 PTE). Increases as G increases
  or t2, t2, t1
  CSRW(pmpaddr0, t2)

//---------------------------------------------------------------------------------------------------------------------------------
//---------------------------------------------------------------------------------------------------------------------------------
//                                                    TESTS AT LEVEL 1
//---------------------------------------------------------------------------------------------------------------------------------
//                    2MB PAGE    Region 1 under test at level 1 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 7: PTE.A unset | Test in S-Mode | RWX bit set | expected = Store, Load & Instr access faults
  PTE_SETUP_SV48(rvtest_slvl2_pg_tbl, (PTE_V), va_data, LEVEL3)
  PTE_SETUP_SV48(rvtest_slvl1_pg_tbl, (PTE_V), va_data, LEVEL2)
  SUPERPAGE_PTE_SETUP_SV48(rvtest_data_1, (PTE_D | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL1)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL1, test7

//---------------------------------------------------------------------------------------------------------------------------------
//                    2MB PAGE    Region 1 under test at level 1 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 8: PTE.D unset | Test in S-Mode | RWX bit set | expected = Store access fault
  PTE_SETUP_SV48(rvtest_slvl2_pg_tbl, (PTE_V), va_data, LEVEL3)
  PTE_SETUP_SV48(rvtest_slvl1_pg_tbl, (PTE_V), va_data, LEVEL2)
  SUPERPAGE_PTE_SETUP_SV48(rvtest_data_1, (PTE_A | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL1)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL1, test8

//---------------------------------------------------------------------------------------------------------------------------------
//                    2MB PAGE    Region 1 under test at level 1 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 9: Both PTE.D & PTE.A unset | Test in S-Mode | RWX bit set | expected = Store, Load & Instr access faults
  PTE_SETUP_SV48(rvtest_slvl2_pg_tbl, (PTE_V), va_data, LEVEL3)
  PTE_SETUP_SV48(rvtest_slvl1_pg_tbl, (PTE_V), va_data, LEVEL2)
  SUPERPAGE_PTE_SETUP_SV48(rvtest_data_1, (PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL1)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL1, test9


//---------------------------------------------------------------------------------------------------------------------------------
//---------------------------------------------------------------------------------------------------------------------------------
//                               Configure level 0 PTE as PMP NAPOT region with no write permission
//---------------------------------------------------------------------------------------------------------------------------------
//---------------------------------------------------------------------------------------------------------------------------------

  LA (t2, rvtest_slvl0_pg_tbl)
  srl t2, t2, PMP_SHIFT
  LI (t1, ((1<<RVMODEL_PMP_GRAIN)-1)>>1)    // Minimum range is 8 Bytes (1 PTE). Increases as G increases
  or t2, t2, t1
  CSRW(pmpaddr0, t2)

//---------------------------------------------------------------------------------------------------------------------------------
//---------------------------------------------------------------------------------------------------------------------------------
//                                                    TESTS AT LEVEL 0
//---------------------------------------------------------------------------------------------------------------------------------
//                    4KB PAGE    Region 1 under test at level 0 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 10: PTE.A unset | Test in S-Mode | RWX bit set | expected = Store, Load & Instr access faults
  PTE_SETUP_SV48(rvtest_slvl2_pg_tbl, (PTE_V), va_data, LEVEL3)
  PTE_SETUP_SV48(rvtest_slvl1_pg_tbl, (PTE_V), va_data, LEVEL2)
  PTE_SETUP_SV48(rvtest_slvl0_pg_tbl, (PTE_V), va_data, LEVEL1)
  PTE_SETUP_SV48(rvtest_data_1, (PTE_D | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL0)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL0, test10

//---------------------------------------------------------------------------------------------------------------------------------
//                    4KB PAGE    Region 1 under test at level 0 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 11: PTE.D unset | Test in S-Mode | RWX bit set | expected = Store access fault
  PTE_SETUP_SV48(rvtest_slvl2_pg_tbl, (PTE_V), va_data, LEVEL3)
  PTE_SETUP_SV48(rvtest_slvl1_pg_tbl, (PTE_V), va_data, LEVEL2)
  PTE_SETUP_SV48(rvtest_slvl0_pg_tbl, (PTE_V), va_data, LEVEL1)
  PTE_SETUP_SV48(rvtest_data_1, (PTE_A | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL0)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL0, test11

//---------------------------------------------------------------------------------------------------------------------------------
//                    4KB PAGE    Region 1 under test at level 0 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 12: Both PTE.D & PTE.A unset | Test in S-Mode | RWX bit set | expected = Store, Load & Instr access faults
  PTE_SETUP_SV48(rvtest_slvl2_pg_tbl, (PTE_V), va_data, LEVEL3)
  PTE_SETUP_SV48(rvtest_slvl1_pg_tbl, (PTE_V), va_data, LEVEL2)
  PTE_SETUP_SV48(rvtest_slvl0_pg_tbl, (PTE_V), va_data, LEVEL1)
  PTE_SETUP_SV48(rvtest_data_1, (PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL0)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL0, test12


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
  addi a4, a2, 4
  jr ra
  nop
  .word 0xbeefcaf1          // Random word
  .word 0xbeefcaf2          // Random word
  nop
  jr ra

//---------------------------------------------------------------------------------------------------------------------------------

// Page Tables
.align 12
.align (RVMODEL_PMP_GRAIN+2)
rvtest_slvl0_pg_tbl:
    .skip(4096)
.align (RVMODEL_PMP_GRAIN+2)
rvtest_slvl1_pg_tbl:
    .skip(4096)
.align (RVMODEL_PMP_GRAIN+2)
rvtest_slvl2_pg_tbl:
    .skip(4096)
.align (RVMODEL_PMP_GRAIN+2)

write_pmpcfg0_str:   .string "\"Mismatch in pmpcfg0!\""
test1_store_str:     .string "\"Mismatch during sw in Test Case 1!\""
test1_load_str:      .string "\"Mismatch during lw in Test Case 1!\""
test1_exec_str:      .string "\"Mismatch during jalr in Test Case 1!\""
test1_read_pte_str:  .string "\"Mismatch in PTE value in Test Case 1!\""
test2_store_str:     .string "\"Mismatch during sw in Test Case 2!\""
test2_load_str:      .string "\"Mismatch during lw in Test Case 2!\""
test2_exec_str:      .string "\"Mismatch during jalr in Test Case 2!\""
test2_read_pte_str:  .string "\"Mismatch in PTE value in Test Case 2!\""
test3_store_str:     .string "\"Mismatch during sw in Test Case 3!\""
test3_load_str:      .string "\"Mismatch during lw in Test Case 3!\""
test3_exec_str:      .string "\"Mismatch during jalr in Test Case 3!\""
test3_read_pte_str:  .string "\"Mismatch in PTE value in Test Case 3!\""
test4_store_str:     .string "\"Mismatch during sw in Test Case 4!\""
test4_load_str:      .string "\"Mismatch during lw in Test Case 4!\""
test4_exec_str:      .string "\"Mismatch during jalr in Test Case 4!\""
test4_read_pte_str:  .string "\"Mismatch in PTE value in Test Case 4!\""
test5_store_str:     .string "\"Mismatch during sw in Test Case 5!\""
test5_load_str:      .string "\"Mismatch during lw in Test Case 5!\""
test5_exec_str:      .string "\"Mismatch during jalr in Test Case 5!\""
test5_read_pte_str:  .string "\"Mismatch in PTE value in Test Case 5!\""
test6_store_str:     .string "\"Mismatch during sw in Test Case 6!\""
test6_load_str:      .string "\"Mismatch during lw in Test Case 6!\""
test6_exec_str:      .string "\"Mismatch during jalr in Test Case 6!\""
test6_read_pte_str:  .string "\"Mismatch in PTE value in Test Case 6!\""
test7_store_str:     .string "\"Mismatch during sw in Test Case 7!\""
test7_load_str:      .string "\"Mismatch during lw in Test Case 7!\""
test7_exec_str:      .string "\"Mismatch during jalr in Test Case 7!\""
test7_read_pte_str:  .string "\"Mismatch in PTE value in Test Case 7!\""
test8_store_str:     .string "\"Mismatch during sw in Test Case 8!\""
test8_load_str:      .string "\"Mismatch during lw in Test Case 8!\""
test8_exec_str:      .string "\"Mismatch during jalr in Test Case 8!\""
test8_read_pte_str:  .string "\"Mismatch in PTE value in Test Case 8!\""
test9_store_str:     .string "\"Mismatch during sw in Test Case 9!\""
test9_load_str:      .string "\"Mismatch during lw in Test Case 9!\""
test9_exec_str:      .string "\"Mismatch during jalr in Test Case 9!\""
test9_read_pte_str:  .string "\"Mismatch in PTE value in Test Case 9!\""
test10_store_str:     .string "\"Mismatch during sw in Test Case 10!\""
test10_load_str:      .string "\"Mismatch during lw in Test Case 10!\""
test10_exec_str:      .string "\"Mismatch during jalr in Test Case 10!\""
test10_read_pte_str:  .string "\"Mismatch in PTE value in Test Case 10!\""
test11_store_str:     .string "\"Mismatch during sw in Test Case 11!\""
test11_load_str:      .string "\"Mismatch during lw in Test Case 11!\""
test11_exec_str:      .string "\"Mismatch during jalr in Test Case 11!\""
test11_read_pte_str:  .string "\"Mismatch in PTE value in Test Case 11!\""
test12_store_str:     .string "\"Mismatch during sw in Test Case 12!\""
test12_load_str:      .string "\"Mismatch during lw in Test Case 12!\""
test12_exec_str:      .string "\"Mismatch during jalr in Test Case 12!\""
test12_read_pte_str:  .string "\"Mismatch in PTE value in Test Case 12!\""

RVTEST_DATA_END
RVTEST_SIG_SETUP
