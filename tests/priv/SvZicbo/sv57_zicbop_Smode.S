// --------------------------------------------------------------------------------------------------------------------------------
// Developed by: Umer Shahid & Muhammad Zain
// --------------------------------------------------------------------------------------------------------------------------------
// Test cases are as follows:
// --------------------------------------------------------------------------------------------------------------------------------
// 1. Setup a valid PTE at level 4 with RWX permissions
//     Then, in S-Mode, execute prefetch.i, prefetch.r and prefetch.w. Expected: No fault
// 2. Setup a valid PTE at level 3 with RWX permissions
//     Then, in S-Mode, execute prefetch.i, prefetch.r and prefetch.w. Expected: No fault
// 3. Setup a valid PTE at level 2 with RWX permissions
//     Then, in S-Mode, execute prefetch.i, prefetch.r and prefetch.w. Expected: No fault
// 4. Setup a valid PTE at level 1 with RWX permissions
//     Then, in S-Mode, execute prefetch.i, prefetch.r and prefetch.w. Expected: No fault
// 5. Setup a valid PTE at level 0 with RWX permissions
//     Then, in S-Mode, execute prefetch.i, prefetch.r and prefetch.w. Expected: No fault
//
// Total Expected Faults :: 0
// --------------------------------------------------------------------------------------------------------------------------------

##### START_TEST_CONFIG #####
# REQUIRED_EXTENSIONS: [I, Sv57, Zicbop]
# MARCH: rv64i_zicsr_zicbop
# CONFIG_DEPENDENT: true
##### END_TEST_CONFIG #####

#define TEST_FILE "sv57_zicbop_Smode.S"
#define SIGUPD_COUNT 10
#define TRAP_SIGUPD_COUNT 10
#define rvtest_mtrap_routine
#define rvtest_strap_routine
#define RVTEST_PRIV_TEST
#define SKIP_MEPC

#include "riscv_arch_test.h"

RVTEST_BEGIN

//---------------------------------------------------------------------------------------------------------------------------------
// Test RWX permissions
.macro VERIFICATION_RWX

  prefetch.i 0(a5)
  nop

  prefetch.r 0(a5)
  nop

  prefetch.w 0(a5)
  nop

.endm


.macro TEST_CASES_RUNNER LOWER_MODE, VA, level

  // Adjust offset of VA to point to test region
  .set VA_SHIFT, (\level*9)+12
  LI(a5, (\VA>>VA_SHIFT)<<VA_SHIFT)
  LA(a0, rvtest_data_1)
  slli a0, a0, 64-VA_SHIFT
  srli a0, a0, 64-VA_SHIFT
  add  a5, a5, a0             // Virtual Address

  RVTEST_GOTO_LOWER_MODE \LOWER_MODE

  VERIFICATION_RWX

  RVTEST_GOTO_MMODE

.endm


main:

//---------------------------------------------------------------------------------------------------------------------------------
//                                   Virtual addresses definition for code and test regions
//---------------------------------------------------------------------------------------------------------------------------------

  // Virtual Address of Test section (rvtest_data_1)
  .set va_data,               0x07028500403000

  // Virtual Address for code region
  .set va_rvtest_code_begin,  0x03000080000000


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

//---------------------------------------------------------------------------------------------------------------------------------
//---------------------------------------------------------------------------------------------------------------------------------
//                                                    TESTS AT LEVEL 4
//---------------------------------------------------------------------------------------------------------------------------------
//                    256TB PAGE    Region 1 under test at level 4 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 1: Test in S-Mode | RWX set | expected = No fault
  SUPERPAGE_PTE_SETUP_SV57(rvtest_data_1, (PTE_D | PTE_A | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL4)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL4


//---------------------------------------------------------------------------------------------------------------------------------
//---------------------------------------------------------------------------------------------------------------------------------
//                                                    TESTS AT LEVEL 3
//---------------------------------------------------------------------------------------------------------------------------------
//                    512GB PAGE    Region 1 under test at level 3 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 2: Test in S-Mode | RWX set | expected = No fault
  PTE_SETUP_SV57(rvtest_slvl3_pg_tbl, (PTE_V), va_data, LEVEL4)
  SUPERPAGE_PTE_SETUP_SV57(rvtest_data_1, (PTE_D | PTE_A | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL3)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL3


//---------------------------------------------------------------------------------------------------------------------------------
//---------------------------------------------------------------------------------------------------------------------------------
//                                                    TESTS AT LEVEL 2
//---------------------------------------------------------------------------------------------------------------------------------
//                    1GB PAGE    Region 1 under test at level 2 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 3: Test in S-Mode | RWX set | expected = No fault
  PTE_SETUP_SV57(rvtest_slvl3_pg_tbl, (PTE_V), va_data, LEVEL4)
  PTE_SETUP_SV57(rvtest_slvl2_pg_tbl, (PTE_V), va_data, LEVEL3)
  SUPERPAGE_PTE_SETUP_SV57(rvtest_data_1, (PTE_D | PTE_A | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL2)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL2


//---------------------------------------------------------------------------------------------------------------------------------
//---------------------------------------------------------------------------------------------------------------------------------
//                                                    TESTS AT LEVEL 1
//---------------------------------------------------------------------------------------------------------------------------------
//                    2MB PAGE    Region 1 under test at level 1 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 4: Test in S-Mode | RWX set | expected = No fault
  PTE_SETUP_SV57(rvtest_slvl3_pg_tbl, (PTE_V), va_data, LEVEL4)
  PTE_SETUP_SV57(rvtest_slvl2_pg_tbl, (PTE_V), va_data, LEVEL3)
  PTE_SETUP_SV57(rvtest_slvl1_pg_tbl, (PTE_V), va_data, LEVEL2)
  SUPERPAGE_PTE_SETUP_SV57(rvtest_data_1, (PTE_D | PTE_A | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL1)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL1


//---------------------------------------------------------------------------------------------------------------------------------
//---------------------------------------------------------------------------------------------------------------------------------
//                                                    TESTS AT LEVEL 0
//---------------------------------------------------------------------------------------------------------------------------------
//                    4KB PAGE    Region 1 under test at level 0 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 5: Test in S-Mode | RWX set | expected = No fault
  PTE_SETUP_SV57(rvtest_slvl3_pg_tbl, (PTE_V), va_data, LEVEL4)
  PTE_SETUP_SV57(rvtest_slvl2_pg_tbl, (PTE_V), va_data, LEVEL3)
  PTE_SETUP_SV57(rvtest_slvl1_pg_tbl, (PTE_V), va_data, LEVEL2)
  PTE_SETUP_SV57(rvtest_slvl0_pg_tbl, (PTE_V), va_data, LEVEL1)
  PTE_SETUP_SV57(rvtest_data_1, (PTE_D | PTE_A | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL0)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL0


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
rvtest_slvl0_pg_tbl:
    .skip(4096)
rvtest_slvl1_pg_tbl:
    .skip(4096)
rvtest_slvl2_pg_tbl:
    .skip(4096)
rvtest_slvl3_pg_tbl:
    .skip(4096)


RVTEST_DATA_END
RVTEST_SIG_SETUP
