// --------------------------------------------------------------------------------------------------------------------------------
// Developed by: Umer Shahid & Muhammad Zain
// --------------------------------------------------------------------------------------------------------------------------------
// Test cases are as follows:
// --------------------------------------------------------------------------------------------------------------------------------
// Configure test data region as NAPOT with RX permissions (pmp1cfg0)
// 1-4. Setup a PTE at Level (3/2/1/0) with RWX permissions
//      → Then, in S-Mode, the page is accessed --> required: 4 Store access faults
//
// Configure test data region as NAPOT with RW permissions (pmp1cfg0)
// 5-8. Setup a PTE at Level (3/2/1/0) with RWX permissions
//      → Then, in S-Mode, the page is accessed --> required: 4 Instruction access faults
//
// Configure test data region as NAPOT with X permission (pmp1cfg0)
// 9-12. Setup a PTE at Level (3/2/1/0) with RWX permissions
//      → Then, in S-Mode, the page is accessed --> required: 4 Store access faults, 4 Load access faults
//
// Total Expected Faults :: 16
// --------------------------------------------------------------------------------------------------------------------------------

##### START_TEST_CONFIG #####
# REQUIRED_EXTENSIONS: [I, Sv48, Smpmp]
# MARCH: rv64i_zicsr
# CONFIG_DEPENDENT: true
##### END_TEST_CONFIG #####

#define TEST_FILE "sv48_pmp_on_pa_Smode.S"
#define SIGUPD_COUNT 50
#define rvtest_mtrap_routine
#define rvtest_strap_routine
#define SKIP_MEPC
#define SKIP_MTVAL

#include "riscv_arch_test.h"

#ifndef RVMODEL_PMP_GRAIN
  #define RVMODEL_PMP_GRAIN 0
#endif

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
  RVTEST_SIGUPD_CSR_WRITE(pmpaddr1, t2, "mismatch_pmpaddr1")

//---------------------------------------------------------------------------------------------------------------------------------
//                                   Virtual addresses definition for code and test regions
//---------------------------------------------------------------------------------------------------------------------------------

  // Virtual Address of Test section (rvtest_data_1)
  .set va_data,               0x028500403000

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

//---------------------------------------------------------------------------------------------------------------------------------
//---------------------------------------------------------------------------------------------------------------------------------
//                             Configure test data region as NAPOT with RX permissions (pmp1cfg0)
//---------------------------------------------------------------------------------------------------------------------------------
//---------------------------------------------------------------------------------------------------------------------------------

  LI (t2, PMP_GLOBAL_RWX | PMP1CFG_RX)
  RVTEST_SIGUPD_CSR_WRITE(pmpcfg0, t2, "mismatch_pmpcfg0_rx")

//---------------------------------------------------------------------------------------------------------------------------------
//                    512GB PAGE    Region 1 under test at level 3 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 1: Test in S-Mode | RWX bit set | expected = Store access fault
  SUPERPAGE_PTE_SETUP_SV48(rvtest_data_1, (PTE_D | PTE_A | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL3)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL3, "test_1"

//---------------------------------------------------------------------------------------------------------------------------------
//                    1GB PAGE    Region 1 under test at level 2 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 2: Test in S-Mode | RWX bit set | expected = Store access fault
  PTE_SETUP_SV48(rvtest_slvl2_pg_tbl, (PTE_V), va_data, LEVEL3)
  SUPERPAGE_PTE_SETUP_SV48(rvtest_data_1, (PTE_D | PTE_A | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL2)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL2, "test_2"

//---------------------------------------------------------------------------------------------------------------------------------
//                    2MB PAGE    Region 1 under test at level 1 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 3: Test in S-Mode | RWX bit set | expected = Store access fault
  PTE_SETUP_SV48(rvtest_slvl2_pg_tbl, (PTE_V), va_data, LEVEL3)
  PTE_SETUP_SV48(rvtest_slvl1_pg_tbl, (PTE_V), va_data, LEVEL2)
  SUPERPAGE_PTE_SETUP_SV48(rvtest_data_1, (PTE_D | PTE_A | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL1)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL1, "test_3"

//---------------------------------------------------------------------------------------------------------------------------------
//                    4KB PAGE    Region 1 under test at level 0 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 4: Test in S-Mode | RWX bit set | expected = Store access fault
  PTE_SETUP_SV48(rvtest_slvl2_pg_tbl, (PTE_V), va_data, LEVEL3)
  PTE_SETUP_SV48(rvtest_slvl1_pg_tbl, (PTE_V), va_data, LEVEL2)
  PTE_SETUP_SV48(rvtest_slvl0_pg_tbl, (PTE_V), va_data, LEVEL1)
  PTE_SETUP_SV48(rvtest_data_1, (PTE_D | PTE_A | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL0)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL0, "test_4"


//---------------------------------------------------------------------------------------------------------------------------------
//---------------------------------------------------------------------------------------------------------------------------------
//                             Configure test data region as NAPOT with RW permissions (pmp1cfg0)
//---------------------------------------------------------------------------------------------------------------------------------
//---------------------------------------------------------------------------------------------------------------------------------

  LI (t2, PMP_GLOBAL_RWX | PMP1CFG_RW)
  RVTEST_SIGUPD_CSR_WRITE(pmpcfg0, t2, "mismatch_pmpcfg0_rw")

//---------------------------------------------------------------------------------------------------------------------------------
//                    512GB PAGE    Region 1 under test at level 3 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 5: Test in S-Mode | RWX bit set | expected = Instruction access fault
  SUPERPAGE_PTE_SETUP_SV48(rvtest_data_1, (PTE_D | PTE_A | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL3)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL3, "test_5"

//---------------------------------------------------------------------------------------------------------------------------------
//                    1GB PAGE    Region 1 under test at level 2 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 6: Test in S-Mode | RWX bit set | expected = Instruction access fault
  PTE_SETUP_SV48(rvtest_slvl2_pg_tbl, (PTE_V), va_data, LEVEL3)
  SUPERPAGE_PTE_SETUP_SV48(rvtest_data_1, (PTE_D | PTE_A | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL2)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL2, "test_6"

//---------------------------------------------------------------------------------------------------------------------------------
//                    2MB PAGE    Region 1 under test at level 1 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 7: Test in S-Mode | RWX bit set | expected = Instruction access fault
  PTE_SETUP_SV48(rvtest_slvl2_pg_tbl, (PTE_V), va_data, LEVEL3)
  PTE_SETUP_SV48(rvtest_slvl1_pg_tbl, (PTE_V), va_data, LEVEL2)
  SUPERPAGE_PTE_SETUP_SV48(rvtest_data_1, (PTE_D | PTE_A | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL1)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL1, "test_7"

//---------------------------------------------------------------------------------------------------------------------------------
//                    4KB PAGE    Region 1 under test at level 0 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 8: Test in S-Mode | RWX bit set | expected = Instruction access fault
  PTE_SETUP_SV48(rvtest_slvl2_pg_tbl, (PTE_V), va_data, LEVEL3)
  PTE_SETUP_SV48(rvtest_slvl1_pg_tbl, (PTE_V), va_data, LEVEL2)
  PTE_SETUP_SV48(rvtest_slvl0_pg_tbl, (PTE_V), va_data, LEVEL1)
  PTE_SETUP_SV48(rvtest_data_1, (PTE_D | PTE_A | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL0)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL0, "test_8"


//---------------------------------------------------------------------------------------------------------------------------------
//---------------------------------------------------------------------------------------------------------------------------------
//                             Configure test data region as NAPOT with X permissions (pmp1cfg0)
//---------------------------------------------------------------------------------------------------------------------------------
//---------------------------------------------------------------------------------------------------------------------------------

  LI (t2, PMP_GLOBAL_RWX | PMP1CFG_X)
  RVTEST_SIGUPD_CSR_WRITE(pmpcfg0, t2, "mismatch_pmpcfg0_x")

//---------------------------------------------------------------------------------------------------------------------------------
//                    512GB PAGE    Region 1 under test at level 3 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 9: Test in S-Mode | RWX bit set | expected = Store access fault, Load access fault
  SUPERPAGE_PTE_SETUP_SV48(rvtest_data_1, (PTE_D | PTE_A | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL3)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL3, "test_9"

//---------------------------------------------------------------------------------------------------------------------------------
//                    1GB PAGE    Region 1 under test at level 2 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 10: Test in S-Mode | RWX bit set | expected = Store access fault, Load access fault
  PTE_SETUP_SV48(rvtest_slvl2_pg_tbl, (PTE_V), va_data, LEVEL3)
  SUPERPAGE_PTE_SETUP_SV48(rvtest_data_1, (PTE_D | PTE_A | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL2)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL2, "test_10"

//---------------------------------------------------------------------------------------------------------------------------------
//                    2MB PAGE    Region 1 under test at level 1 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 11: Test in S-Mode | RWX bit set | expected = Store access fault, Load access fault
  PTE_SETUP_SV48(rvtest_slvl2_pg_tbl, (PTE_V), va_data, LEVEL3)
  PTE_SETUP_SV48(rvtest_slvl1_pg_tbl, (PTE_V), va_data, LEVEL2)
  SUPERPAGE_PTE_SETUP_SV48(rvtest_data_1, (PTE_D | PTE_A | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL1)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL1, "test_11"

//---------------------------------------------------------------------------------------------------------------------------------
//                    4KB PAGE    Region 1 under test at level 0 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 12: Test in S-Mode | RWX bit set | expected = Store access fault, Load access fault
  PTE_SETUP_SV48(rvtest_slvl2_pg_tbl, (PTE_V), va_data, LEVEL3)
  PTE_SETUP_SV48(rvtest_slvl1_pg_tbl, (PTE_V), va_data, LEVEL2)
  PTE_SETUP_SV48(rvtest_slvl0_pg_tbl, (PTE_V), va_data, LEVEL1)
  PTE_SETUP_SV48(rvtest_data_1, (PTE_D | PTE_A | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL0)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL0, "test_12"


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
  addi ra, ra, 4
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

canary_mismatch:     .string "Testcase signature canary mismatch!"
mismatch_pmpaddr1:   .string "\"Mismatch in pmpaddr1!\""
mismatch_pmpcfg0_rx: .string "\"Mismatch in pmpcfg0 while setting RX permission!\""
mismatch_pmpcfg0_rw: .string "\"Mismatch in pmpcfg0 while setting RW permission!\""
mismatch_pmpcfg0_x:  .string "\"Mismatch in pmpcfg0 while setting X permission!\""
test_1: .string "\"Mismatch in Test Case 1!\""
test_2: .string "\"Mismatch in Test Case 2!\""
test_3: .string "\"Mismatch in Test Case 3!\""
test_4: .string "\"Mismatch in Test Case 4!\""
test_5: .string "\"Mismatch in Test Case 5!\""
test_6: .string "\"Mismatch in Test Case 6!\""
test_7: .string "\"Mismatch in Test Case 7!\""
test_8: .string "\"Mismatch in Test Case 8!\""
test_9: .string "\"Mismatch in Test Case 9!\""
test_10: .string "\"Mismatch in Test Case 10!\""
test_11: .string "\"Mismatch in Test Case 11!\""
test_12: .string "\"Mismatch in Test Case 12!\""

RVTEST_DATA_END
RVTEST_SIG_SETUP
