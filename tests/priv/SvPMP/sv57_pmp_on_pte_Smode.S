// --------------------------------------------------------------------------------------------------------------------------------
// Developed by: Umer Shahid & Muhammad Zain
// --------------------------------------------------------------------------------------------------------------------------------
// Test cases are as follows:
// --------------------------------------------------------------------------------------------------------------------------------
// .if (RVMODEL_PMP_GRAIN < 10)
// Configure level 4 PTE as NAPOT with X permission (pmp0cfg0)
// 1. Setup a PTE at Level 4 with RWX permissions
//      → Then, in S-Mode, the page is accessed --> required: Store access fault, Load access fault, Instruction access fault
// .endif
//
// Configure level 3 PTE as NAPOT with X permission (pmp0cfg0)
// 2. Setup a PTE at Level 3 with RWX permissions
//      → Then, in S-Mode, the page is accessed --> required: Store access fault, Load access fault, Instruction access fault
//
// Configure level 2 PTE as NAPOT with X permission (pmp0cfg0)
// 3. Setup a PTE at Level 2 with RWX permissions
//      → Then, in S-Mode, the page is accessed --> required: Store access fault, Load access fault, Instruction access fault
//
// Configure level 1 PTE as NAPOT with X permission (pmp0cfg0)
// 4. Setup a PTE at Level 1 with RWX permissions
//      → Then, in S-Mode, the page is accessed --> required: Store access fault, Load access fault, Instruction access fault
//
// Configure level 0 PTE as NAPOT with X permission (pmp0cfg0)
// 5. Setup a PTE at Level 0 with RWX permissions
//      → Then, in S-Mode, the page is accessed --> required: Store access fault, Load access fault, Instruction access fault
//
// .if (RVMODEL_PMP_GRAIN < 10)
//         Total Expected Faults :: 15
// .else
//         Total Expected Faults :: 12
// .endif
// --------------------------------------------------------------------------------------------------------------------------------

##### START_TEST_CONFIG #####
# REQUIRED_EXTENSIONS: [I, Sv57, Sm]
# params:
#   NUM_PMP_ENTRIES: '>0'
# MARCH: rv64i_zicsr
# CONFIG_DEPENDENT: true
##### END_TEST_CONFIG #####

#define TEST_FILE "sv57_pmp_on_pte_Smode.S"
#define SIGUPD_COUNT 25
#define TRAP_SIGUPD_COUNT 70
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
#define PMP_GLOBAL_RWX        (((PMP_TOR | PMP_X | PMP_W | PMP_R) & 0xFF) << PMP2_CFG_SHIFT)
#define PMP0CFG_X             (((PMP_NAPOT | PMP_X) & 0xFF) << PMP0_CFG_SHIFT)

main:
  LI( a2, 0x800)              // Test signature initialization

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
  SUPERPAGE_PTE_SETUP_SV57(rvtest_code_begin, (PTE_D | PTE_A | PTE_X | PTE_R | PTE_V), va_rvtest_code_begin, LEVEL4)
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
// the entire root page table will lose its read/write permissions, preventing entry into S-Mode.
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
  CSRW(pmpaddr0, t2)

  LI (t2, PMP_GLOBAL_RWX | PMP0CFG_X)
  write_pmpcfg0:
  RVTEST_SIGUPD_CSR_WRITE(pmpcfg0, t2, write_pmpcfg0, write_pmpcfg0_str)

//---------------------------------------------------------------------------------------------------------------------------------
//                                                    TESTS AT LEVEL 4
//---------------------------------------------------------------------------------------------------------------------------------
//                    256TB PAGE    Region 1 under test at level 4 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 1: Test in S-Mode | RWX bit set | expected = Store access fault, Load access fault, Instruction access fault
  SUPERPAGE_PTE_SETUP_SV57(rvtest_data_1, (PTE_D | PTE_A | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL4)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL4, test1


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
  CSRW(pmpaddr0, t2)

//---------------------------------------------------------------------------------------------------------------------------------
//                                                    TESTS AT LEVEL 3
//---------------------------------------------------------------------------------------------------------------------------------
//                    512GB PAGE    Region 1 under test at level 3 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 2: Test in S-Mode | RWX bit set | expected = Store access fault, Load access fault, Instruction access fault
  PTE_SETUP_SV57(rvtest_slvl3_pg_tbl, (PTE_V), va_data, LEVEL4)
  SUPERPAGE_PTE_SETUP_SV57(rvtest_data_1, (PTE_D | PTE_A | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL3)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL3, test2


//---------------------------------------------------------------------------------------------------------------------------------
//---------------------------------------------------------------------------------------------------------------------------------
//                                 Configure level 2 PTE as NAPOT region with X permission
//---------------------------------------------------------------------------------------------------------------------------------
//---------------------------------------------------------------------------------------------------------------------------------

  LA (t2, rvtest_slvl2_pg_tbl)
  srl t2, t2, PMP_SHIFT
  LI (t1, ((1<<RVMODEL_PMP_GRAIN)-1)>>1)    // Minimum range is 8 Bytes (1 PTE). Increases as G increases
  or t2, t2, t1
  CSRW(pmpaddr0, t2)

//---------------------------------------------------------------------------------------------------------------------------------
//                                                    TESTS AT LEVEL 2
//---------------------------------------------------------------------------------------------------------------------------------
//                    1GB PAGE    Region 1 under test at level 2 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 3: Test in S-Mode | RWX set | expected = Store access fault, Load access fault, Instruction access fault
  PTE_SETUP_SV57(rvtest_slvl3_pg_tbl, (PTE_V), va_data, LEVEL4)
  PTE_SETUP_SV57(rvtest_slvl2_pg_tbl, (PTE_V), va_data, LEVEL3)
  SUPERPAGE_PTE_SETUP_SV57(rvtest_data_1, (PTE_D | PTE_A | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL2)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL2, test3


//---------------------------------------------------------------------------------------------------------------------------------
//---------------------------------------------------------------------------------------------------------------------------------
//                                 Configure level 1 PTE as NAPOT region with X permission
//---------------------------------------------------------------------------------------------------------------------------------
//---------------------------------------------------------------------------------------------------------------------------------

  LA (t2, rvtest_slvl1_pg_tbl)
  srl t2, t2, PMP_SHIFT
  LI (t1, ((1<<RVMODEL_PMP_GRAIN)-1)>>1)    // Minimum range is 8 Bytes (1 PTE). Increases as G increases
  or t2, t2, t1
  CSRW(pmpaddr0, t2)

//---------------------------------------------------------------------------------------------------------------------------------
//                                                    TESTS AT LEVEL 1
//---------------------------------------------------------------------------------------------------------------------------------
//                    2MB PAGE    Region 1 under test at level 1 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 4: Test in S-Mode | RWX set | expected = Store access fault, Load access fault, Instruction access fault
  PTE_SETUP_SV57(rvtest_slvl3_pg_tbl, (PTE_V), va_data, LEVEL4)
  PTE_SETUP_SV57(rvtest_slvl2_pg_tbl, (PTE_V), va_data, LEVEL3)
  PTE_SETUP_SV57(rvtest_slvl1_pg_tbl, (PTE_V), va_data, LEVEL2)
  SUPERPAGE_PTE_SETUP_SV57(rvtest_data_1, (PTE_D | PTE_A | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL1)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL1, test4


//---------------------------------------------------------------------------------------------------------------------------------
//---------------------------------------------------------------------------------------------------------------------------------
//                                 Configure level 0 PTE as NAPOT region with X permission
//---------------------------------------------------------------------------------------------------------------------------------
//---------------------------------------------------------------------------------------------------------------------------------

  LA (t2, rvtest_slvl0_pg_tbl)
  srl t2, t2, PMP_SHIFT
  LI (t1, ((1<<RVMODEL_PMP_GRAIN)-1)>>1)    // Minimum range is 8 Bytes (1 PTE). Increases as G increases
  or t2, t2, t1
  CSRW(pmpaddr0, t2)

//---------------------------------------------------------------------------------------------------------------------------------
//                                                    TESTS AT LEVEL 0
//---------------------------------------------------------------------------------------------------------------------------------
//                    4KB PAGE    Region 1 under test at level 0 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 5: Test in S-Mode | RWX set | expected = Store access fault, Load access fault, Instruction access fault
  PTE_SETUP_SV57(rvtest_slvl3_pg_tbl, (PTE_V), va_data, LEVEL4)
  PTE_SETUP_SV57(rvtest_slvl2_pg_tbl, (PTE_V), va_data, LEVEL3)
  PTE_SETUP_SV57(rvtest_slvl1_pg_tbl, (PTE_V), va_data, LEVEL2)
  PTE_SETUP_SV57(rvtest_slvl0_pg_tbl, (PTE_V), va_data, LEVEL1)
  PTE_SETUP_SV57(rvtest_data_1, (PTE_D | PTE_A | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL0)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL0, test5


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
rvtest_slvl3_pg_tbl:
    .skip(4096)
.align (RVMODEL_PMP_GRAIN+2)

write_pmpcfg0_str:   .string "\"Mismatch in pmpcfg0!\""
test1_store_str:     .string "\"Mismatch during sw in Test Case 1!\""
test1_load_str:      .string "\"Mismatch during lw in Test Case 1!\""
test1_exec_str:      .string "\"Mismatch during jalr in Test Case 1!\""
test2_store_str:     .string "\"Mismatch during sw in Test Case 2!\""
test2_load_str:      .string "\"Mismatch during lw in Test Case 2!\""
test2_exec_str:      .string "\"Mismatch during jalr in Test Case 2!\""
test3_store_str:     .string "\"Mismatch during sw in Test Case 3!\""
test3_load_str:      .string "\"Mismatch during lw in Test Case 3!\""
test3_exec_str:      .string "\"Mismatch during jalr in Test Case 3!\""
test4_store_str:     .string "\"Mismatch during sw in Test Case 4!\""
test4_load_str:      .string "\"Mismatch during lw in Test Case 4!\""
test4_exec_str:      .string "\"Mismatch during jalr in Test Case 4!\""
test5_store_str:     .string "\"Mismatch during sw in Test Case 5!\""
test5_load_str:      .string "\"Mismatch during lw in Test Case 5!\""
test5_exec_str:      .string "\"Mismatch during jalr in Test Case 5!\""

RVTEST_DATA_END
RVTEST_SIG_SETUP
