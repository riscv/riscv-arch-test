// --------------------------------------------------------------------------------------------------------------------------------
// Developed by: Umer Shahid & Muhammad Zain
// --------------------------------------------------------------------------------------------------------------------------------
// Test cases are as follows:
// --------------------------------------------------------------------------------------------------------------------------------
// .if (RVMODEL_PMP_GRAIN < 10)
// Configure level 4 PTE as NAPOT with X permission (pmp0cfg0)
// 1. Setup a PTE at Level 4 with RWX permissions
//      → Then, in U-Mode, the page is accessed --> required: Store access fault, Load access fault, Instruction access fault
// .endif
//
// Configure level 3 PTE as NAPOT with X permission (pmp0cfg0)
// 2. Setup a PTE at Level 3 with RWX permissions
//      → Then, in U-Mode, the page is accessed --> required: Store access fault, Load access fault, Instruction access fault
//
// Configure level 2 PTE as NAPOT with X permission (pmp0cfg0)
// 3. Setup a PTE at Level 2 with RWX permissions
//      → Then, in U-Mode, the page is accessed --> required: Store access fault, Load access fault, Instruction access fault
//
// Configure level 1 PTE as NAPOT with X permission (pmp0cfg0)
// 4. Setup a PTE at Level 1 with RWX permissions
//      → Then, in U-Mode, the page is accessed --> required: Store access fault, Load access fault, Instruction access fault
//
// Configure level 0 PTE as NAPOT with X permission (pmp0cfg0)
// 5. Setup a PTE at Level 0 with RWX permissions
//      → Then, in U-Mode, the page is accessed --> required: Store access fault, Load access fault, Instruction access fault
//
// .if (RVMODEL_PMP_GRAIN < 10)
//         Total Expected Faults :: 15
// .else
//         Total Expected Faults :: 12
// .endif
// --------------------------------------------------------------------------------------------------------------------------------

##### START_TEST_CONFIG #####
# REQUIRED_EXTENSIONS: [I, Sv57, Smpmp]
# MARCH: rv64i_zicsr
# CONFIG_DEPENDENT: true
##### END_TEST_CONFIG #####

#define TEST_FILE "sv57_pmp_on_pte_Umode.S"
#define SIGUPD_COUNT 50
#define rvtest_mtrap_routine
#define rvtest_strap_routine
#define SKIP_MEPC

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
#define PMP_GLOBAL_RWX        (((PMP_TOR | PMP_X | PMP_W | PMP_R) & 0xFF) << PMP2_CFG_SHIFT)
#define PMP0CFG_X             (((PMP_NAPOT | PMP_X) & 0xFF) << PMP0_CFG_SHIFT)

main:
  li a2, 0x800                // Test signature initialization

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
  .set va_data,               0x0000000000000000

  // Virtual Address for code region
  .set va_rvtest_code_begin,  0xFFFE000080000000


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

// This test case for root page table is skipped if G >= 10, because with PMP granularity ≥ 4KB,
// the entire root page table will lose its read/write permissions, preventing entry into U-Mode.
.if (RVMODEL_PMP_GRAIN < 10)
//---------------------------------------------------------------------------------------------------------------------------------
//---------------------------------------------------------------------------------------------------------------------------------
//                                 Configure level 4 PTE as NAPOT region with X permission
//---------------------------------------------------------------------------------------------------------------------------------
//---------------------------------------------------------------------------------------------------------------------------------

  LA (t2, rvtest_Sroot_pg_tbl)
  srl t2, t2, PMP_SHIFT
  LI (t1, ((1<<RVMODEL_PMP_GRAIN)-1)>>1)    // Minimum range is 8 Bytes (1 PTE). Increases as G increases
  or t2, t2, t1
  RVTEST_SIGUPD_CSR_WRITE(pmpaddr0, t2, "mismatch_pmpaddr0_1")

  LI (t2, PMP_GLOBAL_RWX | PMP0CFG_X)
  RVTEST_SIGUPD_CSR_WRITE(pmpcfg0, t2, "mismatch_pmpcfg0")

//---------------------------------------------------------------------------------------------------------------------------------
//                                                    TESTS AT LEVEL 4
//---------------------------------------------------------------------------------------------------------------------------------
//                    256TB PAGE    Region 1 under test at level 4 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 1: Test in U-Mode | RWX bit set | expected = Store access fault, Load access fault, Instruction access fault
  SUPERPAGE_PTE_SETUP_SV57(rvtest_data_1, (PTE_D | PTE_A | PTE_U | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL4)
  sfence.vma

  TEST_CASES_RUNNER Umode, va_data, LEVEL4, "test_1"


.endif
//---------------------------------------------------------------------------------------------------------------------------------
//---------------------------------------------------------------------------------------------------------------------------------
//                                 Configure level 3 PTE as NAPOT region with X permission
//---------------------------------------------------------------------------------------------------------------------------------
//---------------------------------------------------------------------------------------------------------------------------------

  LA (t2, rvtest_slvl3_pg_tbl)
  srl t2, t2, PMP_SHIFT
  LI (t1, ((1<<RVMODEL_PMP_GRAIN)-1)>>1)    // Minimum range is 8 Bytes (1 PTE). Increases as G increases
  or t2, t2, t1
  RVTEST_SIGUPD_CSR_WRITE(pmpaddr0, t2, "mismatch_pmpaddr0_2")

//---------------------------------------------------------------------------------------------------------------------------------
//                                                    TESTS AT LEVEL 3
//---------------------------------------------------------------------------------------------------------------------------------
//                    512GB PAGE    Region 1 under test at level 3 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 1: Test in U-Mode | RWX bit set | expected = Store access fault, Load access fault, Instruction access fault
  PTE_SETUP_SV57(rvtest_slvl3_pg_tbl, (PTE_V), va_data, LEVEL4)
  SUPERPAGE_PTE_SETUP_SV57(rvtest_data_1, (PTE_D | PTE_A | PTE_U | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL3)
  sfence.vma

  TEST_CASES_RUNNER Umode, va_data, LEVEL3, "test_2"


//---------------------------------------------------------------------------------------------------------------------------------
//---------------------------------------------------------------------------------------------------------------------------------
//                                 Configure level 2 PTE as NAPOT region with X permission
//---------------------------------------------------------------------------------------------------------------------------------
//---------------------------------------------------------------------------------------------------------------------------------

  LA (t2, rvtest_slvl2_pg_tbl)
  srl t2, t2, PMP_SHIFT
  LI (t1, ((1<<RVMODEL_PMP_GRAIN)-1)>>1)    // Minimum range is 8 Bytes (1 PTE). Increases as G increases
  or t2, t2, t1
  RVTEST_SIGUPD_CSR_WRITE(pmpaddr0, t2, "mismatch_pmpaddr0_3")

//---------------------------------------------------------------------------------------------------------------------------------
//                                                    TESTS AT LEVEL 2
//---------------------------------------------------------------------------------------------------------------------------------
//                    1GB PAGE    Region 1 under test at level 2 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 2: Test in U-Mode | RWX set | expected = Store access fault, Load access fault, Instruction access fault
  PTE_SETUP_SV57(rvtest_slvl3_pg_tbl, (PTE_V), va_data, LEVEL4)
  PTE_SETUP_SV57(rvtest_slvl2_pg_tbl, (PTE_V), va_data, LEVEL3)
  SUPERPAGE_PTE_SETUP_SV57(rvtest_data_1, (PTE_D | PTE_A | PTE_U | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL2)
  sfence.vma

  TEST_CASES_RUNNER Umode, va_data, LEVEL2, "test_3"


//---------------------------------------------------------------------------------------------------------------------------------
//---------------------------------------------------------------------------------------------------------------------------------
//                                 Configure level 1 PTE as NAPOT region with X permission
//---------------------------------------------------------------------------------------------------------------------------------
//---------------------------------------------------------------------------------------------------------------------------------

  LA (t2, rvtest_slvl1_pg_tbl)
  srl t2, t2, PMP_SHIFT
  LI (t1, ((1<<RVMODEL_PMP_GRAIN)-1)>>1)    // Minimum range is 8 Bytes (1 PTE). Increases as G increases
  or t2, t2, t1
  RVTEST_SIGUPD_CSR_WRITE(pmpaddr0, t2, "mismatch_pmpaddr0_4")

//---------------------------------------------------------------------------------------------------------------------------------
//                                                    TESTS AT LEVEL 1
//---------------------------------------------------------------------------------------------------------------------------------
//                    2MB PAGE    Region 1 under test at level 1 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 3: Test in U-Mode | RWX set | expected = Store access fault, Load access fault, Instruction access fault
  PTE_SETUP_SV57(rvtest_slvl3_pg_tbl, (PTE_V), va_data, LEVEL4)
  PTE_SETUP_SV57(rvtest_slvl2_pg_tbl, (PTE_V), va_data, LEVEL3)
  PTE_SETUP_SV57(rvtest_slvl1_pg_tbl, (PTE_V), va_data, LEVEL2)
  SUPERPAGE_PTE_SETUP_SV57(rvtest_data_1, (PTE_D | PTE_A | PTE_U | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL1)
  sfence.vma

  TEST_CASES_RUNNER Umode, va_data, LEVEL1, "test_4"


//---------------------------------------------------------------------------------------------------------------------------------
//---------------------------------------------------------------------------------------------------------------------------------
//                                 Configure level 0 PTE as NAPOT region with X permission
//---------------------------------------------------------------------------------------------------------------------------------
//---------------------------------------------------------------------------------------------------------------------------------

  LA (t2, rvtest_slvl0_pg_tbl)
  srl t2, t2, PMP_SHIFT
  LI (t1, ((1<<RVMODEL_PMP_GRAIN)-1)>>1)    // Minimum range is 8 Bytes (1 PTE). Increases as G increases
  or t2, t2, t1
  RVTEST_SIGUPD_CSR_WRITE(pmpaddr0, t2, "mismatch_pmpaddr0_5")

//---------------------------------------------------------------------------------------------------------------------------------
//                                                    TESTS AT LEVEL 0
//---------------------------------------------------------------------------------------------------------------------------------
//                    4KB PAGE    Region 1 under test at level 0 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 4: Test in U-Mode | RWX set | expected = Store access fault, Load access fault, Instruction access fault
  PTE_SETUP_SV57(rvtest_slvl3_pg_tbl, (PTE_V), va_data, LEVEL4)
  PTE_SETUP_SV57(rvtest_slvl2_pg_tbl, (PTE_V), va_data, LEVEL3)
  PTE_SETUP_SV57(rvtest_slvl1_pg_tbl, (PTE_V), va_data, LEVEL2)
  PTE_SETUP_SV57(rvtest_slvl0_pg_tbl, (PTE_V), va_data, LEVEL1)
  PTE_SETUP_SV57(rvtest_data_1, (PTE_D | PTE_A | PTE_U | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL0)
  sfence.vma

  TEST_CASES_RUNNER Umode, va_data, LEVEL0, "test_5"


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
rvtest_slvl3_pg_tbl:
    .skip(4096)
.align (RVMODEL_PMP_GRAIN+2)

canary_mismatch:     .string "Testcase signature canary mismatch!"
mismatch_pmpcfg0:    .string "\"Mismatch in pmpcfg0!\""
mismatch_pmpaddr0_1: .string "\"Mismatch in pmpaddr0 in Test Case 1!\""
mismatch_pmpaddr0_2: .string "\"Mismatch in pmpaddr0 in Test Case 2!\""
mismatch_pmpaddr0_3: .string "\"Mismatch in pmpaddr0 in Test Case 3!\""
mismatch_pmpaddr0_4: .string "\"Mismatch in pmpaddr0 in Test Case 4!\""
mismatch_pmpaddr0_5: .string "\"Mismatch in pmpaddr0 in Test Case 5!\""
test_1: .string "\"Mismatch in Test Case 1!\""
test_2: .string "\"Mismatch in Test Case 2!\""
test_3: .string "\"Mismatch in Test Case 3!\""
test_4: .string "\"Mismatch in Test Case 4!\""
test_5: .string "\"Mismatch in Test Case 5!\""

RVTEST_DATA_END
RVTEST_SIG_SETUP
