// --------------------------------------------------------------------------------------------------------------------------------
// Developed by: Umer Shahid & Muhammad Zain
// --------------------------------------------------------------------------------------------------------------------------------
// Test cases are as follows:
// --------------------------------------------------------------------------------------------------------------------------------
// Configure test data region as NAPOT with X permission (pmp0cfg0)
// 1. Setup a PTE at Level 4 with RWX permissions
//      Then, in S-Mode, execute cbo.zero. Expected: Store access fault
// 2. Setup a PTE at Level 3 with RWX permissions
//      Then, in S-Mode, execute cbo.zero. Expected: Store access fault
// 3. Setup a PTE at Level 2 with RWX permissions
//      Then, in S-Mode, execute cbo.zero. Expected: Store access fault
// 4. Setup a PTE at Level 1 with RWX permissions
//      Then, in S-Mode, execute cbo.zero. Expected: Store access fault
// 5. Setup a PTE at Level 0 with RWX permissions
//      Then, in S-Mode, execute cbo.zero. Expected: Store access fault
//
// Total Expected Faults :: 5
// --------------------------------------------------------------------------------------------------------------------------------

##### START_TEST_CONFIG #####
# REQUIRED_EXTENSIONS: [I, Sv57, Zicboz, Sm]
# params:
#   NUM_PMP_ENTRIES: '>0'
# MARCH: rv64i_zicsr_zicboz
# CONFIG_DEPENDENT: true
##### END_TEST_CONFIG #####

#define TEST_FILE "sv57_pmp_on_pa_zicboz_Smode.S"
#define SIGUPD_COUNT 10
#define TRAP_SIGUPD_COUNT 30
#define rvtest_mtrap_routine
#define rvtest_strap_routine
#define RVTEST_PRIV_TEST
#define SKIP_MEPC

#include "riscv_arch_test.h"

RVTEST_BEGIN

//---------------------------------------------------------------------------------------------------------------------------------
// Test RWX permissions
.macro VERIFICATION_RWX

  cbo.zero (a5)
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

// PMP Macros
#define PMP_GLOBAL_RWX        (((PMP_TOR | PMP_X | PMP_W | PMP_R) & 0xFF) << PMP2_CFG_SHIFT)
#define PMP0CFG_X             (((PMP_NAPOT | PMP_X) & 0xFF) << PMP0_CFG_SHIFT)


main:

//---------------------------------------------------------------------------------------------------------------------------------
//                                                    Setup pmp registers
//---------------------------------------------------------------------------------------------------------------------------------

  li t2, 0                                        // Set PMP permission for all memory in pmp2cfg0 (TOR)
  csrw pmpaddr1, t2
  li t2, -1
  csrw pmpaddr2, t2

  LA (t2, rvtest_data_1)                          // Configure test region as NAPOT
  srl t2, t2, PMP_SHIFT

  .if (RVMODEL_PMP_GRAIN <= 3)                    // G=3 -> 32 Bytes (Minimum size of test region)
      LI (t1, 0x3)                                // Range = 2^(2+3) = 32 Bytes
  .else
      LI (t1, ((1<<RVMODEL_PMP_GRAIN)-1)>>1)      // Range = 2^(G+3) Bytes
  .endif

  or t2, t2, t1
  CSRW(pmpaddr0, t2)

  LI (t2, PMP_GLOBAL_RWX | PMP0CFG_X)
  pmpcfg0_x:
  RVTEST_SIGUPD_CSR_WRITE(pmpcfg0, t2, pmpcfg0_x, pmpcfg0_x_str)

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

  LI(t0, MENVCFG_CBZE)
  CSRS(menvcfg, t0)                                                      // Allow execution of cbo.zero in S-Mode

//---------------------------------------------------------------------------------------------------------------------------------
//---------------------------------------------------------------------------------------------------------------------------------
//                                                    TESTS AT LEVEL 4
//---------------------------------------------------------------------------------------------------------------------------------
//                    256TB PAGE    Region 1 under test at level 4 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 1: Test in S-Mode | RWX bit set | expected = Store access fault
  SUPERPAGE_PTE_SETUP_SV57(rvtest_data_1, (PTE_D | PTE_A | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL4)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL4


//---------------------------------------------------------------------------------------------------------------------------------
//---------------------------------------------------------------------------------------------------------------------------------
//                                                    TESTS AT LEVEL 3
//---------------------------------------------------------------------------------------------------------------------------------
//                    512GB PAGE    Region 1 under test at level 3 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 2: Test in S-Mode | RWX bit set | expected = Store access fault
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

  // Test case 3: Test in S-Mode | RWX bit set | expected = Store access fault
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

  // Test case 4: Test in S-Mode | RWX bit set | expected = Store access fault
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

  // Test case 5: Test in S-Mode | RWX bit set | expected = Store access fault
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

// Page Table
.align 12
rvtest_slvl0_pg_tbl:
    .skip(4096)
rvtest_slvl1_pg_tbl:
    .skip(4096)
rvtest_slvl2_pg_tbl:
    .skip(4096)
rvtest_slvl3_pg_tbl:
    .skip(4096)

pmpcfg0_x_str:    .string "\"Mismatch in pmpcfg0 while setting X permission!\""

RVTEST_DATA_END
RVTEST_SIG_SETUP
