// --------------------------------------------------------------------------------------------------------------------------------
// Developed by: Umer Shahid & Muhammad Zain
// --------------------------------------------------------------------------------------------------------------------------------
// Test Description:
//                     Construct a 64 KiB NAPOT region by setting up 16 contiguous level 0 PTEs with PTE.N=1,
// RWX permissions and PTE.ppn[0][3:0]=1000 (64 KiB encoding). Then in S-Mode, perform store, load and execute at offsets
// 0KiB, 8KiB and 60KiB within the same 64KiB region.
//
// Total Expected Faults :: 0
// --------------------------------------------------------------------------------------------------------------------------------

##### START_TEST_CONFIG #####
# REQUIRED_EXTENSIONS: [I, Sv57, Svnapot]
# MARCH: rv64i_zicsr_zifencei
##### END_TEST_CONFIG #####

#define SIGUPD_COUNT 15


#include "riscv_arch_test.h"

RVTEST_BEGIN

//---------------------------------------------------------------------------------------------------------------------------------
// Test RWX permissions
.macro VERIFICATION_RWX VA, TEST_CASE
  LI(  a5, \VA)               // Load virtual address
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
  \TEST_CASE\()_exec:
  jalr ra, a5, 0
  nop
.endm

.macro TEST_CASES_RUNNER LOWER_MODE, VA, level, TEST_CASE

  RVTEST_GOTO_LOWER_MODE \LOWER_MODE

  VERIFICATION_RWX \VA, \TEST_CASE

  RVTEST_GOTO_MMODE

  // Signature Update
  RVTEST_SIGUPD(x2, x5, x4, a2, \TEST_CASE\()_store, \TEST_CASE\()_store_str)
  RVTEST_SIGUPD(x2, x5, x4, a3, \TEST_CASE\()_load, \TEST_CASE\()_load_str)
  RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_exec, \TEST_CASE\()_exec_str)

.endm


main:
  LI( a2, 0x800)            // Test signature initialization

//---------------------------------------------------------------------------------------------------------------------------------
//                                   Virtual addresses definition for code and test regions
//---------------------------------------------------------------------------------------------------------------------------------

  // Virtual Address of Test section (rvtest_data_1)
  .set va_data,               0x400280C0410000

  // Virtual Address for code region
  .set va_rvtest_code_begin,  0x03000080000000


  // PTE setup for Code Region
  SUPERPAGE_PTE_SETUP_SV57(rvtest_code_begin, (PTE_D | PTE_A | PTE_X | PTE_R | PTE_V), va_rvtest_code_begin, LEVEL4)
  sfence.vma

  // Save area setup for code region
  csrr a0, mscratch
  SAVE_AREA_SETUP(va_rvtest_code_begin, rvtest_code_begin, code, LEVEL4)

//---------------------------------------------------------------------------------------------------------------------------------
//                                               Test Cases Start from here
//---------------------------------------------------------------------------------------------------------------------------------

  SATP_SETUP_RV64(sv57)                                                  // Set SATP for virtualization
  sfence.vma                                                             // Flush TLB

//---------------------------------------------------------------------------------------------------------------------------------
//---------------------------------------------------------------------------------------------------------------------------------
//                                                    TESTS AT LEVEL 0
//---------------------------------------------------------------------------------------------------------------------------------
//                    64KB PAGE    Region 1 under test at level 0 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 1: Test in S-Mode | RWX bit set | Bit 63 (PTE.N) set | PTE.PPN[0][3:0] set to 4'b1000 (64KiB region encoding)
  PTE_SETUP_SV57(rvtest_slvl3_pg_tbl, (PTE_V), va_data, LEVEL4)
  PTE_SETUP_SV57(rvtest_slvl2_pg_tbl, (PTE_V), va_data, LEVEL3)
  PTE_SETUP_SV57(rvtest_slvl1_pg_tbl, (PTE_V), va_data, LEVEL2)
  PTE_SETUP_SV57(rvtest_slvl0_pg_tbl, (PTE_V), va_data, LEVEL1)
  PTE_SETUP_SV57(rvtest_data_1, (PTE_N | (1 << 13) | PTE_D | PTE_A | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL0)
  PTE_SETUP_SV57(rvtest_data_1, (PTE_N | (1 << 13) | PTE_D | PTE_A | PTE_X | PTE_W | PTE_R | PTE_V), (va_data+0x1000), LEVEL0)
  PTE_SETUP_SV57(rvtest_data_1, (PTE_N | (1 << 13) | PTE_D | PTE_A | PTE_X | PTE_W | PTE_R | PTE_V), (va_data+0x2000), LEVEL0)
  PTE_SETUP_SV57(rvtest_data_1, (PTE_N | (1 << 13) | PTE_D | PTE_A | PTE_X | PTE_W | PTE_R | PTE_V), (va_data+0x3000), LEVEL0)
  PTE_SETUP_SV57(rvtest_data_1, (PTE_N | (1 << 13) | PTE_D | PTE_A | PTE_X | PTE_W | PTE_R | PTE_V), (va_data+0x4000), LEVEL0)
  PTE_SETUP_SV57(rvtest_data_1, (PTE_N | (1 << 13) | PTE_D | PTE_A | PTE_X | PTE_W | PTE_R | PTE_V), (va_data+0x5000), LEVEL0)
  PTE_SETUP_SV57(rvtest_data_1, (PTE_N | (1 << 13) | PTE_D | PTE_A | PTE_X | PTE_W | PTE_R | PTE_V), (va_data+0x6000), LEVEL0)
  PTE_SETUP_SV57(rvtest_data_1, (PTE_N | (1 << 13) | PTE_D | PTE_A | PTE_X | PTE_W | PTE_R | PTE_V), (va_data+0x7000), LEVEL0)
  PTE_SETUP_SV57(rvtest_data_1, (PTE_N | (1 << 13) | PTE_D | PTE_A | PTE_X | PTE_W | PTE_R | PTE_V), (va_data+0x8000), LEVEL0)
  PTE_SETUP_SV57(rvtest_data_1, (PTE_N | (1 << 13) | PTE_D | PTE_A | PTE_X | PTE_W | PTE_R | PTE_V), (va_data+0x9000), LEVEL0)
  PTE_SETUP_SV57(rvtest_data_1, (PTE_N | (1 << 13) | PTE_D | PTE_A | PTE_X | PTE_W | PTE_R | PTE_V), (va_data+0xA000), LEVEL0)
  PTE_SETUP_SV57(rvtest_data_1, (PTE_N | (1 << 13) | PTE_D | PTE_A | PTE_X | PTE_W | PTE_R | PTE_V), (va_data+0xB000), LEVEL0)
  PTE_SETUP_SV57(rvtest_data_1, (PTE_N | (1 << 13) | PTE_D | PTE_A | PTE_X | PTE_W | PTE_R | PTE_V), (va_data+0xC000), LEVEL0)
  PTE_SETUP_SV57(rvtest_data_1, (PTE_N | (1 << 13) | PTE_D | PTE_A | PTE_X | PTE_W | PTE_R | PTE_V), (va_data+0xD000), LEVEL0)
  PTE_SETUP_SV57(rvtest_data_1, (PTE_N | (1 << 13) | PTE_D | PTE_A | PTE_X | PTE_W | PTE_R | PTE_V), (va_data+0xE000), LEVEL0)
  PTE_SETUP_SV57(rvtest_data_1, (PTE_N | (1 << 13) | PTE_D | PTE_A | PTE_X | PTE_W | PTE_R | PTE_V), (va_data+0xF000), LEVEL0)
  sfence.vma

  // Access different addresses within 64KB region
  TEST_CASES_RUNNER Smode, va_data,        LEVEL0, test1_access1
  TEST_CASES_RUNNER Smode, va_data+0x2000, LEVEL0, test1_access2
  TEST_CASES_RUNNER Smode, va_data+0xF000, LEVEL0, test1_access3


//---------------------------------------------------------------------------------------------------------------------------------
RVTEST_CODE_END
RVTEST_DATA_BEGIN

//---------------------------------------------------------------------------------------------------------------------------------
//                                            PHYSICAL ADDRESS REGIONS FOR TESTING
//---------------------------------------------------------------------------------------------------------------------------------
// Physical Address region under testing for LEVEL 0 (Aligned to 64KiB)
.p2align 16
rvtest_data_1:
  nop
  addi a4, a2, 4
  jr ra
  nop
  .word 0xbeefcaf1
  .word 0xbeefcaf2
  jr ra
  .skip (2 << 12) - (7*4)              // Skip to 8KB aligned region

  nop
  addi a4, a2, 4
  jr ra
  nop
  .word 0xbeefcaf3
  .word 0xbeefcaf4
  jr ra
  .skip (13 << 12) - (7*4)             // Skip to 60KB aligned region

  nop
  addi a4, a2, 4
  jr ra
  nop
  .word 0xbeefcaf3
  .word 0xbeefcaf4
  jr ra

//---------------------------------------------------------------------------------------------------------------------------------

// Page Tables
.p2align 12
rvtest_slvl0_pg_tbl:
    .skip(4096)
rvtest_slvl1_pg_tbl:
    .skip(4096)
rvtest_slvl2_pg_tbl:
    .skip(4096)
rvtest_slvl3_pg_tbl:
    .skip(4096)

test1_access1_store_str:  .string "\"Mismatch during sw in Test Case 1, Access 1!\""
test1_access1_load_str:   .string "\"Mismatch during lw in Test Case 1, Access 1!\""
test1_access1_exec_str:   .string "\"Mismatch during jalr in Test Case 1, Access 1!\""
test1_access2_store_str:  .string "\"Mismatch during sw in Test Case 1, Access 2!\""
test1_access2_load_str:   .string "\"Mismatch during lw in Test Case 1, Access 2!\""
test1_access2_exec_str:   .string "\"Mismatch during jalr in Test Case 1, Access 2!\""
test1_access3_store_str:  .string "\"Mismatch during sw in Test Case 1, Access 3!\""
test1_access3_load_str:   .string "\"Mismatch during lw in Test Case 1, Access 3!\""
test1_access3_exec_str:   .string "\"Mismatch during jalr in Test Case 1, Access 3!\""

RVTEST_DATA_END
RVTEST_SIG_SETUP
