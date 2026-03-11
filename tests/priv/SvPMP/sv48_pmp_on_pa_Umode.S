// --------------------------------------------------------------------------------------------------------------------------------
// Developed by: Umer Shahid & Muhammad Zain
// --------------------------------------------------------------------------------------------------------------------------------
// Test cases are as follows:
// --------------------------------------------------------------------------------------------------------------------------------
// Configure test data region as NAPOT with RX permissions (pmp1cfg0)
// 1-4. Setup a PTE at Level (3/2/1/0) with RWX permissions
//      → Then, in U-Mode, the page is accessed --> required: 4 Store access faults
//
// Configure test data region as NAPOT with RW permissions (pmp1cfg0)
// 5-8. Setup a PTE at Level (3/2/1/0) with RWX permissions
//      → Then, in U-Mode, the page is accessed --> required: 4 Instruction access faults
//
// Configure test data region as NAPOT with X permission (pmp1cfg0)
// 9-12. Setup a PTE at Level (3/2/1/0) with RWX permissions
//      → Then, in U-Mode, the page is accessed --> required: 4 Store access faults, 4 Load access faults
//
// Total Expected Faults :: 16
// --------------------------------------------------------------------------------------------------------------------------------

##### START_TEST_CONFIG #####
# REQUIRED_EXTENSIONS: [I, Sv48]
# params:
#   NUM_PMP_ENTRIES: '>0'
# MARCH: rv64i_zicsr
# CONFIG_DEPENDENT: true
##### END_TEST_CONFIG #####

#define TEST_FILE "sv48_pmp_on_pa_Umode.S"
#define SIGUPD_COUNT 45
#define TRAP_SIGUPD_COUNT 80
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
.endm

// PMP Macros
#define PMP_GLOBAL_RWX        (((PMP_TOR | PMP_X | PMP_W | PMP_R) & 0xFF) << PMP3_CFG_SHIFT)
#define PMP1CFG_RX            (((PMP_NAPOT | PMP_X | PMP_R) & 0xFF) << PMP1_CFG_SHIFT)
#define PMP1CFG_RW            (((PMP_NAPOT | PMP_W | PMP_R) & 0xFF) << PMP1_CFG_SHIFT)
#define PMP1CFG_X             (((PMP_NAPOT | PMP_X) & 0xFF) << PMP1_CFG_SHIFT)


main:
  li a2, 0x800              // Test signature initialization

//---------------------------------------------------------------------------------------------------------------------------------
//                                                    Setup pmpaddr registers
//---------------------------------------------------------------------------------------------------------------------------------

  li t2, 0                  // Set PMP permission for all memory in pmp3cfg0 (TOR)
  csrw pmpaddr2, t2
  li t2, -1
  csrw pmpaddr3, t2

  LA (t2, rvtest_data_1)    // Configure test region as NAPOT
  srl t2, t2, PMP_SHIFT

  .if (RVMODEL_PMP_GRAIN <= 3)                    // G=3 -> 32 Bytes (Minimum size of test region)
      LI (t1, 0x3)                                // Range = 2^(2+3) = 32 Bytes
  .else
      LI (t1, ((1<<RVMODEL_PMP_GRAIN)-1)>>1)      // Range = 2^(G+3) Bytes
  .endif

  or t2, t2, t1
  CSRW(pmpaddr1, t2)

//---------------------------------------------------------------------------------------------------------------------------------
//                                   Virtual addresses definition for code and test regions
//---------------------------------------------------------------------------------------------------------------------------------

  // Virtual Address of Test section (rvtest_data_1)
  .set va_data,               0x028500403000

  // Virtual Address for code region
  .set va_rvtest_code_begin,  0x030080000000


  // PTE setup for Code Region
  SUPERPAGE_PTE_SETUP_SV48(rvtest_code_begin, (PTE_D | PTE_A | PTE_U | PTE_X | PTE_R | PTE_V), va_rvtest_code_begin, LEVEL3)
  sfence.vma

  // Save area setup for code region
  csrr a0, mscratch
  SAVE_AREA_SETUP(va_rvtest_code_begin, rvtest_code_begin, code)

//---------------------------------------------------------------------------------------------------------------------------------
//                                               Test Cases Start from here
//---------------------------------------------------------------------------------------------------------------------------------

  SATP_SETUP_RV64(sv48)                                                  // Set SATP for virtualization
  sfence.vma                                                             // Flush TLB

//---------------------------------------------------------------------------------------------------------------------------------
//---------------------------------------------------------------------------------------------------------------------------------
//                             Configure test data region as NAPOT with RX permissions (pmp1cfg0)
//---------------------------------------------------------------------------------------------------------------------------------
//---------------------------------------------------------------------------------------------------------------------------------

  LI (t2, PMP_GLOBAL_RWX | PMP1CFG_RX)
  pmpcfg0_rx:
  RVTEST_SIGUPD_CSR_WRITE(pmpcfg0, t2, pmpcfg0_rx, pmpcfg0_rx_str)

//---------------------------------------------------------------------------------------------------------------------------------
//                    512GB PAGE    Region 1 under test at level 3 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 1: Test in U-Mode | RWX bit set | expected = Store access fault
  SUPERPAGE_PTE_SETUP_SV48(rvtest_data_1, (PTE_D | PTE_A | PTE_U | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL3)
  sfence.vma

  TEST_CASES_RUNNER Umode, va_data, LEVEL3, test1

//---------------------------------------------------------------------------------------------------------------------------------
//                    1GB PAGE    Region 1 under test at level 2 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 2: Test in U-Mode | RWX bit set | expected = Store access fault
  PTE_SETUP_SV48(rvtest_slvl2_pg_tbl, (PTE_V), va_data, LEVEL3)
  SUPERPAGE_PTE_SETUP_SV48(rvtest_data_1, (PTE_D | PTE_A | PTE_U | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL2)
  sfence.vma

  TEST_CASES_RUNNER Umode, va_data, LEVEL2, test2

//---------------------------------------------------------------------------------------------------------------------------------
//                    2MB PAGE    Region 1 under test at level 1 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 3: Test in U-Mode | RWX bit set | expected = Store access fault
  PTE_SETUP_SV48(rvtest_slvl2_pg_tbl, (PTE_V), va_data, LEVEL3)
  PTE_SETUP_SV48(rvtest_slvl1_pg_tbl, (PTE_V), va_data, LEVEL2)
  SUPERPAGE_PTE_SETUP_SV48(rvtest_data_1, (PTE_D | PTE_A | PTE_U | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL1)
  sfence.vma

  TEST_CASES_RUNNER Umode, va_data, LEVEL1, test3

//---------------------------------------------------------------------------------------------------------------------------------
//                    4KB PAGE    Region 1 under test at level 0 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 4: Test in U-Mode | RWX bit set | expected = Store access fault
  PTE_SETUP_SV48(rvtest_slvl2_pg_tbl, (PTE_V), va_data, LEVEL3)
  PTE_SETUP_SV48(rvtest_slvl1_pg_tbl, (PTE_V), va_data, LEVEL2)
  PTE_SETUP_SV48(rvtest_slvl0_pg_tbl, (PTE_V), va_data, LEVEL1)
  PTE_SETUP_SV48(rvtest_data_1, (PTE_D | PTE_A | PTE_U | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL0)
  sfence.vma

  TEST_CASES_RUNNER Umode, va_data, LEVEL0, test4


//---------------------------------------------------------------------------------------------------------------------------------
//---------------------------------------------------------------------------------------------------------------------------------
//                             Configure test data region as NAPOT with RW permissions (pmp1cfg0)
//---------------------------------------------------------------------------------------------------------------------------------
//---------------------------------------------------------------------------------------------------------------------------------

  LI (t2, PMP_GLOBAL_RWX | PMP1CFG_RW)
  pmpcfg0_rw:
  RVTEST_SIGUPD_CSR_WRITE(pmpcfg0, t2, pmpcfg0_rw, pmpcfg0_rw_str)

//---------------------------------------------------------------------------------------------------------------------------------
//                    512GB PAGE    Region 1 under test at level 3 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 5: Test in U-Mode | RWX bit set | expected = Instruction access fault
  SUPERPAGE_PTE_SETUP_SV48(rvtest_data_1, (PTE_D | PTE_A | PTE_U | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL3)
  sfence.vma

  TEST_CASES_RUNNER Umode, va_data, LEVEL3, test5

//---------------------------------------------------------------------------------------------------------------------------------
//                    1GB PAGE    Region 1 under test at level 2 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 6: Test in U-Mode | RWX bit set | expected = Instruction access fault
  PTE_SETUP_SV48(rvtest_slvl2_pg_tbl, (PTE_V), va_data, LEVEL3)
  SUPERPAGE_PTE_SETUP_SV48(rvtest_data_1, (PTE_D | PTE_A | PTE_U | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL2)
  sfence.vma

  TEST_CASES_RUNNER Umode, va_data, LEVEL2, test6

//---------------------------------------------------------------------------------------------------------------------------------
//                    2MB PAGE    Region 1 under test at level 1 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 7: Test in U-Mode | RWX bit set | expected = Instruction access fault
  PTE_SETUP_SV48(rvtest_slvl2_pg_tbl, (PTE_V), va_data, LEVEL3)
  PTE_SETUP_SV48(rvtest_slvl1_pg_tbl, (PTE_V), va_data, LEVEL2)
  SUPERPAGE_PTE_SETUP_SV48(rvtest_data_1, (PTE_D | PTE_A | PTE_U | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL1)
  sfence.vma

  TEST_CASES_RUNNER Umode, va_data, LEVEL1, test7

//---------------------------------------------------------------------------------------------------------------------------------
//                    4KB PAGE    Region 1 under test at level 0 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 8: Test in U-Mode | RWX bit set | expected = Instruction access fault
  PTE_SETUP_SV48(rvtest_slvl2_pg_tbl, (PTE_V), va_data, LEVEL3)
  PTE_SETUP_SV48(rvtest_slvl1_pg_tbl, (PTE_V), va_data, LEVEL2)
  PTE_SETUP_SV48(rvtest_slvl0_pg_tbl, (PTE_V), va_data, LEVEL1)
  PTE_SETUP_SV48(rvtest_data_1, (PTE_D | PTE_A | PTE_U | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL0)
  sfence.vma

  TEST_CASES_RUNNER Umode, va_data, LEVEL0, test8


//---------------------------------------------------------------------------------------------------------------------------------
//---------------------------------------------------------------------------------------------------------------------------------
//                             Configure test data region as NAPOT with X permissions (pmp1cfg0)
//---------------------------------------------------------------------------------------------------------------------------------
//---------------------------------------------------------------------------------------------------------------------------------

  LI (t2, PMP_GLOBAL_RWX | PMP1CFG_X)
  pmpcfg0_x:
  RVTEST_SIGUPD_CSR_WRITE(pmpcfg0, t2, pmpcfg0_x, pmpcfg0_x_str)

//---------------------------------------------------------------------------------------------------------------------------------
//                    512GB PAGE    Region 1 under test at level 3 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 9: Test in U-Mode | RWX bit set | expected = Store access fault, Load access fault
  SUPERPAGE_PTE_SETUP_SV48(rvtest_data_1, (PTE_D | PTE_A | PTE_U | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL3)
  sfence.vma

  TEST_CASES_RUNNER Umode, va_data, LEVEL3, test9

//---------------------------------------------------------------------------------------------------------------------------------
//                    1GB PAGE    Region 1 under test at level 2 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 10: Test in U-Mode | RWX bit set | expected = Store access fault, Load access fault
  PTE_SETUP_SV48(rvtest_slvl2_pg_tbl, (PTE_V), va_data, LEVEL3)
  SUPERPAGE_PTE_SETUP_SV48(rvtest_data_1, (PTE_D | PTE_A | PTE_U | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL2)
  sfence.vma

  TEST_CASES_RUNNER Umode, va_data, LEVEL2, test10

//---------------------------------------------------------------------------------------------------------------------------------
//                    2MB PAGE    Region 1 under test at level 1 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 11: Test in U-Mode | RWX bit set | expected = Store access fault, Load access fault
  PTE_SETUP_SV48(rvtest_slvl2_pg_tbl, (PTE_V), va_data, LEVEL3)
  PTE_SETUP_SV48(rvtest_slvl1_pg_tbl, (PTE_V), va_data, LEVEL2)
  SUPERPAGE_PTE_SETUP_SV48(rvtest_data_1, (PTE_D | PTE_A | PTE_U | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL1)
  sfence.vma

  TEST_CASES_RUNNER Umode, va_data, LEVEL1, test11

//---------------------------------------------------------------------------------------------------------------------------------
//                    4KB PAGE    Region 1 under test at level 0 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 12: Test in U-Mode | RWX bit set | expected = Store access fault, Load access fault
  PTE_SETUP_SV48(rvtest_slvl2_pg_tbl, (PTE_V), va_data, LEVEL3)
  PTE_SETUP_SV48(rvtest_slvl1_pg_tbl, (PTE_V), va_data, LEVEL2)
  PTE_SETUP_SV48(rvtest_slvl0_pg_tbl, (PTE_V), va_data, LEVEL1)
  PTE_SETUP_SV48(rvtest_data_1, (PTE_D | PTE_A | PTE_U | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL0)
  sfence.vma

  TEST_CASES_RUNNER Umode, va_data, LEVEL0, test12


//---------------------------------------------------------------------------------------------------------------------------------
RVTEST_CODE_END
RVTEST_DATA_BEGIN

//---------------------------------------------------------------------------------------------------------------------------------
//                                            PHYSICAL ADDRESS REGION FOR TESTING
//---------------------------------------------------------------------------------------------------------------------------------
// Physical Address region under testing for LEVEL 0, 1, 2 and 3
.align 12
.align (RVMODEL_PMP_GRAIN+2)
rvtest_data_1:
  nop
  addi a4, a2, 4
  jr ra
  nop
  .word 0xbeefcaf1          // Random word
  .word 0xbeefcaf2          // Random word
  nop
  jr ra

.align (RVMODEL_PMP_GRAIN+2)
//---------------------------------------------------------------------------------------------------------------------------------

// Page Tables
.align 12
rvtest_slvl0_pg_tbl:
    .skip(4096)
rvtest_slvl1_pg_tbl:
    .skip(4096)
rvtest_slvl2_pg_tbl:
    .skip(4096)

canary_mismatch:  .string "Testcase signature canary mismatch!"
pmpcfg0_rx_str:   .string "\"Mismatch in pmpcfg0 while setting RX permission!\""
pmpcfg0_rw_str:   .string "\"Mismatch in pmpcfg0 while setting RW permission!\""
pmpcfg0_x_str:    .string "\"Mismatch in pmpcfg0 while setting X permission!\""
test1_store_str:  .string "\"Mismatch during sw in Test Case 1!\""
test1_load_str:   .string "\"Mismatch during lw in Test Case 1!\""
test1_exec_str:   .string "\"Mismatch during jalr in Test Case 1!\""
test2_store_str:  .string "\"Mismatch during sw in Test Case 2!\""
test2_load_str:   .string "\"Mismatch during lw in Test Case 2!\""
test2_exec_str:   .string "\"Mismatch during jalr in Test Case 2!\""
test3_store_str:  .string "\"Mismatch during sw in Test Case 3!\""
test3_load_str:   .string "\"Mismatch during lw in Test Case 3!\""
test3_exec_str:   .string "\"Mismatch during jalr in Test Case 3!\""
test4_store_str:  .string "\"Mismatch during sw in Test Case 4!\""
test4_load_str:   .string "\"Mismatch during lw in Test Case 4!\""
test4_exec_str:   .string "\"Mismatch during jalr in Test Case 4!\""
test5_store_str:  .string "\"Mismatch during sw in Test Case 5!\""
test5_load_str:   .string "\"Mismatch during lw in Test Case 5!\""
test5_exec_str:   .string "\"Mismatch during jalr in Test Case 5!\""
test6_store_str:  .string "\"Mismatch during sw in Test Case 6!\""
test6_load_str:   .string "\"Mismatch during lw in Test Case 6!\""
test6_exec_str:   .string "\"Mismatch during jalr in Test Case 6!\""
test7_store_str:  .string "\"Mismatch during sw in Test Case 7!\""
test7_load_str:   .string "\"Mismatch during lw in Test Case 7!\""
test7_exec_str:   .string "\"Mismatch during jalr in Test Case 7!\""
test8_store_str:  .string "\"Mismatch during sw in Test Case 8!\""
test8_load_str:   .string "\"Mismatch during lw in Test Case 8!\""
test8_exec_str:   .string "\"Mismatch during jalr in Test Case 8!\""
test9_store_str:  .string "\"Mismatch during sw in Test Case 9!\""
test9_load_str:   .string "\"Mismatch during lw in Test Case 9!\""
test9_exec_str:   .string "\"Mismatch during jalr in Test Case 9!\""
test10_store_str: .string "\"Mismatch during sw in Test Case 10!\""
test10_load_str:  .string "\"Mismatch during lw in Test Case 10!\""
test10_exec_str:  .string "\"Mismatch during jalr in Test Case 10!\""
test11_store_str: .string "\"Mismatch during sw in Test Case 11!\""
test11_load_str:  .string "\"Mismatch during lw in Test Case 11!\""
test11_exec_str:  .string "\"Mismatch during jalr in Test Case 11!\""
test12_store_str: .string "\"Mismatch during sw in Test Case 12!\""
test12_load_str:  .string "\"Mismatch during lw in Test Case 12!\""
test12_exec_str:  .string "\"Mismatch during jalr in Test Case 12!\""

RVTEST_DATA_END
RVTEST_SIG_SETUP
