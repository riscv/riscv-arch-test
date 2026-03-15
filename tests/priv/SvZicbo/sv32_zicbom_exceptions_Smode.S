// --------------------------------------------------------------------------------------------------------------------------------
// Developed by: Umer Shahid & Muhammad Zain
// --------------------------------------------------------------------------------------------------------------------------------
// Test cases are as follows:
// --------------------------------------------------------------------------------------------------------------------------------
// 1. At level 1, setup a PTE with V=0
//      → In S-Mode, execute cbo.clean, cbo.flush and cbo.inval. Expected: 3 Store Page faults
// 2. At level 1, setup a PTE with reserved encoding R=0, W=1 & X=1
//      → In S-Mode, execute cbo.clean, cbo.flush and cbo.inval. Expected: 3 Store Page faults
// 3. At level 1, setup a PTE with reserved encoding R=0, W=1 & X=0
//      → In S-Mode, execute cbo.clean, cbo.flush and cbo.inval. Expected: 3 Store Page faults
// 4. At level 1, setup a PTE with RX permissions
//      → In S-Mode, execute cbo.clean, cbo.flush and cbo.inval. Expected: No fault
// 5. At level 1, setup a PTE with RX permissions and set mstatus.SUM
//      → In S-Mode, execute cbo.clean, cbo.flush and cbo.inval. Expected: No fault
// 6. At level 1, setup a PTE with RWX & U permissions
//      → In S-Mode, execute cbo.clean, cbo.flush and cbo.inval. Expected: 3 Store page faults
// 7. At level 1, setup a PTE with X permission only
//      → In S-Mode, execute cbo.clean, cbo.flush and cbo.inval. Expected: 3 Store Page faults
// 8. At level 1, setup a PTE with RWX permissions and A bit unset
//      → In S-Mode, execute cbo.clean, cbo.flush and cbo.inval. Expected: 3 Store page faults
// 9. At level 1, setup a PTE with RWX permissions and D bit unset
//      → In S-Mode, execute cbo.clean, cbo.flush and cbo.inval. Expected: No fault
// 10. At level 1, setup a misaligned megapage
//      → In S-Mode, execute cbo.clean, cbo.flush and cbo.inval. Expected: 3 Store page faults
// 11. At level 1, setup a PTE with RWX permissions that points to RVMODEL_ACCESS_FAULT_ADDRESS
//      → In S-Mode, execute cbo.clean, cbo.flush and cbo.inval. Expected: 3 Store access faults
//
// 12. At level 0, setup a PTE with V=0
//      → In S-Mode, execute cbo.clean, cbo.flush and cbo.inval. Expected: 3 Store Page faults
// 13. At level 0, setup a PTE with reserved encoding R=0, W=1 & X=1
//      → In S-Mode, execute cbo.clean, cbo.flush and cbo.inval. Expected: 3 Store Page faults
// 14. At level 0, setup a PTE with reserved encoding R=0, W=1 & X=0
//      → In S-Mode, execute cbo.clean, cbo.flush and cbo.inval. Expected: 3 Store Page faults
// 15. At level 0, setup a PTE with RX permissions
//      → In S-Mode, execute cbo.clean, cbo.flush and cbo.inval. Expected: No fault
// 16. At level 0, setup a PTE with RX permissions and set mstatus.SUM
//      → In S-Mode, execute cbo.clean, cbo.flush and cbo.inval. Expected: No fault
// 17. At level 0, setup a PTE with RWX & U permissions
//      → In S-Mode, execute cbo.clean, cbo.flush and cbo.inval. Expected: 3 Store page faults
// 18. At level 0, setup a PTE with X permission only
//      → In S-Mode, execute cbo.clean, cbo.flush and cbo.inval. Expected: 3 Store Page faults
// 19. At level 0, setup a PTE with RWX permissions and A bit unset
//      → In S-Mode, execute cbo.clean, cbo.flush and cbo.inval. Expected: 3 Store page faults
// 20. At level 0, setup a PTE with RWX permissions and D bit unset
//      → In S-Mode, execute cbo.clean, cbo.flush and cbo.inval. Expected: No fault
// 21. At level 0, setup a PTE with only V bit set
//      → In S-Mode, execute cbo.clean, cbo.flush and cbo.inval. Expected: 3 Store page faults
// 22. At level 0, setup a PTE with non leaf (lvl 1) PTE pointing to RVMODEL_ACCESS_FAULT_ADDRESS instead of next page table
//      → In S-Mode, execute cbo.clean, cbo.flush and cbo.inval. Expected: 3 Store access faults
// 23. At level 0, setup a PTE with RWX permissions that points to RVMODEL_ACCESS_FAULT_ADDRESS
//      → In S-Mode, execute cbo.clean, cbo.flush and cbo.inval. Expected: 3 Store access faults
// 24. At level 0, setup a PTE with non leaf (lvl 1) PTE.D set
//      → In S-Mode, execute cbo.clean, cbo.flush and cbo.inval. Expected: 3 Store page faults
// 25. At level 0, setup a PTE with non leaf (lvl 1) PTE.A set
//      → In S-Mode, execute cbo.clean, cbo.flush and cbo.inval. Expected: 3 Store page faults
// 26. At level 0, setup a PTE with non leaf (lvl 1) PTE.U set
//      → In S-Mode, execute cbo.clean, cbo.flush and cbo.inval. Expected: 3 Store page faults
//
// Total Expected Faults :: 60
// --------------------------------------------------------------------------------------------------------------------------------

##### START_TEST_CONFIG #####
# REQUIRED_EXTENSIONS: [I, Sv32, Zicbom]
# MARCH: rv32i_zicsr_zicbom
# CONFIG_DEPENDENT: true
##### END_TEST_CONFIG #####

#define TEST_FILE "sv32_zicbom_exceptions_Smode.S"
#define SIGUPD_COUNT 85
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

  \TEST_CASE\()_clean:
  cbo.clean (a5)
  addi a2, a2, 4

  \TEST_CASE\()_flush:
  cbo.flush (a5)
  addi a3, a2, 4

  \TEST_CASE\()_inval:
  cbo.inval (a5)
  addi a4, a2, 4

.endm

.macro TEST_CASES_RUNNER LOWER_MODE, VA, level, TEST_CASE

  .if \level == LEVEL1
    // Adjust offset of VA to point to test region
    LI(  a5, (\VA>>22)<<22)
    LA(  a0, rvtest_data_1)
    slli a0, a0, 10
    srli a0, a0, 10
    add  a5, a5, a0
  .else
    LI(  a5, \VA)
  .endif

  RVTEST_GOTO_LOWER_MODE \LOWER_MODE

  VERIFICATION_RWX \TEST_CASE

  RVTEST_GOTO_MMODE

  // Signature Update
  RVTEST_SIGUPD(x2, x5, x4, a2, \TEST_CASE\()_clean, \TEST_CASE\()_clean_str)
  RVTEST_SIGUPD(x2, x5, x4, a3, \TEST_CASE\()_flush, \TEST_CASE\()_flush_str)
  RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_inval, \TEST_CASE\()_inval_str)
.endm

// This TEST_CASES_RUNNER is used when PA is not a label
// Useful to test misaligned pages & pages at RVMODEL_ACCESS_FAULT_ADDRESS
.macro TEST_CASES_RUNNER_2 LOWER_MODE, PA, VA, level, TEST_CASE

  .if \level == LEVEL1
    // Adjust offset of VA to point to test region
    LI(  a5, (\VA>>22)<<22)
    LI(  a0, \PA)
    slli a0, a0, 10
    srli a0, a0, 10
    add  a5, a5, a0
  .else
    LI(  a5, \VA)
  .endif

  RVTEST_GOTO_LOWER_MODE \LOWER_MODE

  VERIFICATION_RWX \TEST_CASE

  RVTEST_GOTO_MMODE

  // Signature Update
  RVTEST_SIGUPD(x2, x5, x4, a2, \TEST_CASE\()_clean, \TEST_CASE\()_clean_str)
  RVTEST_SIGUPD(x2, x5, x4, a3, \TEST_CASE\()_flush, \TEST_CASE\()_flush_str)
  RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_inval, \TEST_CASE\()_inval_str)
.endm


main:
  li a2, 0x800              // Test signature initialization

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

  LI(t0, MENVCFG_CBCFE | MENVCFG_CBIE)
  CSRS(menvcfg, t0)                                                      // Allow execution of Zicbom instructions in S-Mode

//---------------------------------------------------------------------------------------------------------------------------------
//---------------------------------------------------------------------------------------------------------------------------------
//                                                    TESTS AT LEVEL 1
//---------------------------------------------------------------------------------------------------------------------------------
//                    4MB PAGE    Region 1 under test at level 1 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 1: Test in S-Mode | V bit unset | expected = 3 Store page faults
  SUPERPAGE_PTE_SETUP_SV32(rvtest_data_1, (PTE_D | PTE_A | PTE_X | PTE_W | PTE_R), va_data, LEVEL1)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL1, test1

//---------------------------------------------------------------------------------------------------------------------------------
//                    4MB PAGE    Region 1 under test at level 1 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 2: Test in S-Mode | WX bit set | expected = 3 Store page faults
  SUPERPAGE_PTE_SETUP_SV32(rvtest_data_1, (PTE_D | PTE_A | PTE_X | PTE_W | PTE_V), va_data, LEVEL1)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL1, test2

//---------------------------------------------------------------------------------------------------------------------------------
//                    4MB PAGE    Region 1 under test at level 1 -- RWX permission given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 3: Test in S-Mode | W bit set | expected = 3 Store page faults
  SUPERPAGE_PTE_SETUP_SV32(rvtest_data_1, (PTE_D | PTE_A | PTE_W | PTE_V), va_data, LEVEL1)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL1, test3

//---------------------------------------------------------------------------------------------------------------------------------
//                    4MB PAGE    Region 1 under test at level 1 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 4: Test in S-Mode | RX bit set | expected = No fault
  SUPERPAGE_PTE_SETUP_SV32(rvtest_data_1, (PTE_D | PTE_A | PTE_X | PTE_R | PTE_V), va_data, LEVEL1)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL1, test4

//---------------------------------------------------------------------------------------------------------------------------------
//                    4MB PAGE    Region 1 under test at level 1 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 5: Test in S-Mode | RX bit set | mstatus.SUM set | expected = No fault
  SUPERPAGE_PTE_SETUP_SV32(rvtest_data_1, (PTE_D | PTE_A | PTE_X | PTE_R | PTE_V), va_data, LEVEL1)
  sfence.vma

  LI(t0, MSTATUS_SUM)
  CSRS(mstatus, t0)                                               // Set mstatus.SUM
  TEST_CASES_RUNNER Smode, va_data, LEVEL1, test5
  LI(t0, MSTATUS_SUM)
  CSRC(mstatus, t0)                                               // Clear mstatus.SUM

//---------------------------------------------------------------------------------------------------------------------------------
//                    4MB PAGE    Region 1 under test at level 1 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 6: Test in S-Mode | RWXU bit set | expected = 3 Store page faults
  SUPERPAGE_PTE_SETUP_SV32(rvtest_data_1, (PTE_D | PTE_A | PTE_U | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL1)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL1, test6

//---------------------------------------------------------------------------------------------------------------------------------
//                    4MB PAGE    Region 1 under test at level 1 -- RWX permission given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 7: Test in S-Mode | X bit set | expected = 3 Store page faults
  SUPERPAGE_PTE_SETUP_SV32(rvtest_data_1, (PTE_D | PTE_A | PTE_X | PTE_V), va_data, LEVEL1)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL1, test7

//---------------------------------------------------------------------------------------------------------------------------------
//                    4MB PAGE    Region 1 under test at level 1 -- RWX permission given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 8: Test in S-Mode | PTE.A unset | expected = 3 Store page faults
  SUPERPAGE_PTE_SETUP_SV32(rvtest_data_1, (PTE_D | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL1)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL1, test8

//---------------------------------------------------------------------------------------------------------------------------------
//                    4MB PAGE    Region 1 under test at level 1 -- RWX permission given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 9: Test in S-Mode | PTE.D unset | expected = No fault
  SUPERPAGE_PTE_SETUP_SV32(rvtest_data_1, (PTE_A | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL1)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL1, test9

//---------------------------------------------------------------------------------------------------------------------------------
//                    4MB PAGE    Region 1 under test at level 1 -- RWX permission given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 10: Test in S-Mode | RWX bit set | Misaligned Megapage | expected = 3 Store page faults
  PTE_SETUP_SV32(rvtest_data_1, (PTE_D | PTE_A | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL1)
  sfence.vma

  TEST_CASES_RUNNER_2 Smode, 0x0, va_data, LEVEL1, test10

//---------------------------------------------------------------------------------------------------------------------------------
//                    4MB PAGE    Region 1 under test at level 1 -- RWX permission given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 11: Test in S-Mode | RWX bit set | expected = 3 Store access faults
  SUPERPAGE_PTE_SETUP_SV32(RVMODEL_ACCESS_FAULT_ADDRESS, (PTE_D | PTE_A | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL1)
  sfence.vma

  TEST_CASES_RUNNER_2 Smode, RVMODEL_ACCESS_FAULT_ADDRESS, va_data, LEVEL1, test11


//---------------------------------------------------------------------------------------------------------------------------------
//---------------------------------------------------------------------------------------------------------------------------------
//                                                    TESTS AT LEVEL 0
//---------------------------------------------------------------------------------------------------------------------------------
//                    4KB PAGE    Region 1 under test at level 0 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 12: Test in S-Mode | V bit unset | expected = 3 Store page faults
  PTE_SETUP_SV32(rvtest_slvl0_pg_tbl, (PTE_V), va_data, LEVEL1)
  PTE_SETUP_SV32(rvtest_data_1, (PTE_D | PTE_A | PTE_X | PTE_W | PTE_R), va_data, LEVEL0)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL0, test12

//---------------------------------------------------------------------------------------------------------------------------------
//                    4KB PAGE    Region 1 under test at level 0 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 13: Test in S-Mode | WX bit set | expected = 3 Store page faults
  PTE_SETUP_SV32(rvtest_slvl0_pg_tbl, (PTE_V), va_data, LEVEL1)
  PTE_SETUP_SV32(rvtest_data_1, (PTE_D | PTE_A | PTE_X | PTE_W | PTE_V), va_data, LEVEL0)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL0, test13

//---------------------------------------------------------------------------------------------------------------------------------
//                    4KB PAGE    Region 1 under test at level 0 -- RWX permission given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 14: Test in S-Mode | W bit set | expected = 3 Store page faults
  PTE_SETUP_SV32(rvtest_slvl0_pg_tbl, (PTE_V), va_data, LEVEL1)
  PTE_SETUP_SV32(rvtest_data_1, (PTE_D | PTE_A | PTE_W | PTE_V), va_data, LEVEL0)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL0, test14

//---------------------------------------------------------------------------------------------------------------------------------
//                    4KB PAGE    Region 1 under test at level 0 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 15: Test in S-Mode | RX bit set | expected = No fault
  PTE_SETUP_SV32(rvtest_slvl0_pg_tbl, (PTE_V), va_data, LEVEL1)
  PTE_SETUP_SV32(rvtest_data_1, (PTE_D | PTE_A | PTE_X | PTE_R | PTE_V), va_data, LEVEL0)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL0, test15

//---------------------------------------------------------------------------------------------------------------------------------
//                    4KB PAGE    Region 1 under test at level 0 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 16: Test in S-Mode | RX bit set | expected = No fault
  PTE_SETUP_SV32(rvtest_slvl0_pg_tbl, (PTE_V), va_data, LEVEL1)
  PTE_SETUP_SV32(rvtest_data_1, (PTE_D | PTE_A | PTE_X | PTE_R | PTE_V), va_data, LEVEL0)
  sfence.vma

  LI(t0, MSTATUS_SUM)
  CSRS(mstatus, t0)                                               // Set mstatus.SUM
  TEST_CASES_RUNNER Smode, va_data, LEVEL0, test16
  LI(t0, MSTATUS_SUM)
  CSRC(mstatus, t0)                                               // Clear mstatus.SUM

//---------------------------------------------------------------------------------------------------------------------------------
//                    4KB PAGE    Region 1 under test at level 0 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 17: Test in S-Mode | RWXU bit set | expected = 3 Store page faults
  PTE_SETUP_SV32(rvtest_slvl0_pg_tbl, (PTE_V), va_data, LEVEL1)
  PTE_SETUP_SV32(rvtest_data_1, (PTE_D | PTE_A | PTE_U | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL0)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL0, test17

//---------------------------------------------------------------------------------------------------------------------------------
//                    4KB PAGE    Region 1 under test at level 0 -- RWX permission given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 18: Test in S-Mode | X bit set | expected = 3 Store page faults
  PTE_SETUP_SV32(rvtest_slvl0_pg_tbl, (PTE_V), va_data, LEVEL1)
  PTE_SETUP_SV32(rvtest_data_1, (PTE_D | PTE_A | PTE_X | PTE_V), va_data, LEVEL0)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL0, test18

//---------------------------------------------------------------------------------------------------------------------------------
//                    4KB PAGE    Region 1 under test at level 0 -- RWX permission given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 19: Test in S-Mode | PTE.A unset | expected = 3 Store page faults
  PTE_SETUP_SV32(rvtest_slvl0_pg_tbl, (PTE_V), va_data, LEVEL1)
  PTE_SETUP_SV32(rvtest_data_1, (PTE_D | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL0)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL0, test19

//---------------------------------------------------------------------------------------------------------------------------------
//                    4KB PAGE    Region 1 under test at level 0 -- RWX permission given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 20: Test in S-Mode | PTE.D unset | expected = No fault
  PTE_SETUP_SV32(rvtest_slvl0_pg_tbl, (PTE_V), va_data, LEVEL1)
  PTE_SETUP_SV32(rvtest_data_1, (PTE_A | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL0)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL0, test20

//---------------------------------------------------------------------------------------------------------------------------------
//                    4KB PAGE    Region 1 under test at level 0 -- RWX permission given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 21: Test in S-Mode | Only V bit set at Level 0 | expected = 3 Store page faults
  PTE_SETUP_SV32(rvtest_slvl0_pg_tbl, (PTE_V), va_data, LEVEL1)
  PTE_SETUP_SV32(rvtest_data_1, (PTE_V), va_data, LEVEL0)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL0, test21

//---------------------------------------------------------------------------------------------------------------------------------
//                    4KB PAGE    Region 1 under test at level 0 -- RWX permission given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 22: Test in S-Mode | Incorrect PTE setup | expected = 3 Store access faults
  PTE_SETUP_SV32(RVMODEL_ACCESS_FAULT_ADDRESS, (PTE_V), va_data, LEVEL1)
  PTE_SETUP_SV32(rvtest_data_1, (PTE_D | PTE_A | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL0)
  sfence.vma

  TEST_CASES_RUNNER_2 Smode, RVMODEL_ACCESS_FAULT_ADDRESS, va_data, LEVEL0, test22

//---------------------------------------------------------------------------------------------------------------------------------
//                    4KB PAGE    Region 1 under test at level 0 -- RWX permission given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 23: Test in S-Mode | RWX bit set | expected = 3 Store access faults
  PTE_SETUP_SV32(rvtest_slvl0_pg_tbl, (PTE_V), va_data, LEVEL1)
  PTE_SETUP_SV32(RVMODEL_ACCESS_FAULT_ADDRESS, (PTE_D | PTE_A | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL0)
  sfence.vma

  TEST_CASES_RUNNER_2 Smode, RVMODEL_ACCESS_FAULT_ADDRESS, va_data, LEVEL0, test23

//---------------------------------------------------------------------------------------------------------------------------------
//                    4KB PAGE    Region 1 under test at level 0 -- RWX permission given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 24: Test in S-Mode | PTE.D set for level 1 PTE | expected = 3 Store page faults
  PTE_SETUP_SV32(rvtest_slvl0_pg_tbl, (PTE_D | PTE_V), va_data, LEVEL1)
  PTE_SETUP_SV32(rvtest_data_1, (PTE_D | PTE_A | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL0)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL0, test24

//---------------------------------------------------------------------------------------------------------------------------------
//                    4KB PAGE    Region 1 under test at level 0 -- RWX permission given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 25: Test in S-Mode | PTE.A set for level 1 PTE | expected = 3 Store page faults
  PTE_SETUP_SV32(rvtest_slvl0_pg_tbl, (PTE_A | PTE_V), va_data, LEVEL1)
  PTE_SETUP_SV32(rvtest_data_1, (PTE_D | PTE_A | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL0)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL0, test25

//---------------------------------------------------------------------------------------------------------------------------------
//                    4KB PAGE    Region 1 under test at level 0 -- RWX permission given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 26: Test in S-Mode | PTE.U set for level 1 PTE | expected = 3 Store page faults
  PTE_SETUP_SV32(rvtest_slvl0_pg_tbl, (PTE_U | PTE_V), va_data, LEVEL1)
  PTE_SETUP_SV32(rvtest_data_1, (PTE_D | PTE_A | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL0)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL0, test26


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

canary_mismatch:  .string "Testcase signature canary mismatch!"
test1_clean_str:  .string "\"Mismatch during cbo.clean in Test Case 1!\""
test1_flush_str:  .string "\"Mismatch during cbo.flush in Test Case 1!\""
test1_inval_str:  .string "\"Mismatch during cbo.inval in Test Case 1!\""
test2_clean_str:  .string "\"Mismatch during cbo.clean in Test Case 2!\""
test2_flush_str:  .string "\"Mismatch during cbo.flush in Test Case 2!\""
test2_inval_str:  .string "\"Mismatch during cbo.inval in Test Case 2!\""
test3_clean_str:  .string "\"Mismatch during cbo.clean in Test Case 3!\""
test3_flush_str:  .string "\"Mismatch during cbo.flush in Test Case 3!\""
test3_inval_str:  .string "\"Mismatch during cbo.inval in Test Case 3!\""
test4_clean_str:  .string "\"Mismatch during cbo.clean in Test Case 4!\""
test4_flush_str:  .string "\"Mismatch during cbo.flush in Test Case 4!\""
test4_inval_str:  .string "\"Mismatch during cbo.inval in Test Case 4!\""
test5_clean_str:  .string "\"Mismatch during cbo.clean in Test Case 5!\""
test5_flush_str:  .string "\"Mismatch during cbo.flush in Test Case 5!\""
test5_inval_str:  .string "\"Mismatch during cbo.inval in Test Case 5!\""
test6_clean_str:  .string "\"Mismatch during cbo.clean in Test Case 6!\""
test6_flush_str:  .string "\"Mismatch during cbo.flush in Test Case 6!\""
test6_inval_str:  .string "\"Mismatch during cbo.inval in Test Case 6!\""
test7_clean_str:  .string "\"Mismatch during cbo.clean in Test Case 7!\""
test7_flush_str:  .string "\"Mismatch during cbo.flush in Test Case 7!\""
test7_inval_str:  .string "\"Mismatch during cbo.inval in Test Case 7!\""
test8_clean_str:  .string "\"Mismatch during cbo.clean in Test Case 8!\""
test8_flush_str:  .string "\"Mismatch during cbo.flush in Test Case 8!\""
test8_inval_str:  .string "\"Mismatch during cbo.inval in Test Case 8!\""
test9_clean_str:  .string "\"Mismatch during cbo.clean in Test Case 9!\""
test9_flush_str:  .string "\"Mismatch during cbo.flush in Test Case 9!\""
test9_inval_str:  .string "\"Mismatch during cbo.inval in Test Case 9!\""
test10_clean_str:  .string "\"Mismatch during cbo.clean in Test Case 10!\""
test10_flush_str:  .string "\"Mismatch during cbo.flush in Test Case 10!\""
test10_inval_str:  .string "\"Mismatch during cbo.inval in Test Case 10!\""
test11_clean_str:  .string "\"Mismatch during cbo.clean in Test Case 11!\""
test11_flush_str:  .string "\"Mismatch during cbo.flush in Test Case 11!\""
test11_inval_str:  .string "\"Mismatch during cbo.inval in Test Case 11!\""
test12_clean_str:  .string "\"Mismatch during cbo.clean in Test Case 12!\""
test12_flush_str:  .string "\"Mismatch during cbo.flush in Test Case 12!\""
test12_inval_str:  .string "\"Mismatch during cbo.inval in Test Case 12!\""
test13_clean_str:  .string "\"Mismatch during cbo.clean in Test Case 13!\""
test13_flush_str:  .string "\"Mismatch during cbo.flush in Test Case 13!\""
test13_inval_str:  .string "\"Mismatch during cbo.inval in Test Case 13!\""
test14_clean_str:  .string "\"Mismatch during cbo.clean in Test Case 14!\""
test14_flush_str:  .string "\"Mismatch during cbo.flush in Test Case 14!\""
test14_inval_str:  .string "\"Mismatch during cbo.inval in Test Case 14!\""
test15_clean_str:  .string "\"Mismatch during cbo.clean in Test Case 15!\""
test15_flush_str:  .string "\"Mismatch during cbo.flush in Test Case 15!\""
test15_inval_str:  .string "\"Mismatch during cbo.inval in Test Case 15!\""
test16_clean_str:  .string "\"Mismatch during cbo.clean in Test Case 16!\""
test16_flush_str:  .string "\"Mismatch during cbo.flush in Test Case 16!\""
test16_inval_str:  .string "\"Mismatch during cbo.inval in Test Case 16!\""
test17_clean_str:  .string "\"Mismatch during cbo.clean in Test Case 17!\""
test17_flush_str:  .string "\"Mismatch during cbo.flush in Test Case 17!\""
test17_inval_str:  .string "\"Mismatch during cbo.inval in Test Case 17!\""
test18_clean_str:  .string "\"Mismatch during cbo.clean in Test Case 18!\""
test18_flush_str:  .string "\"Mismatch during cbo.flush in Test Case 18!\""
test18_inval_str:  .string "\"Mismatch during cbo.inval in Test Case 18!\""
test19_clean_str:  .string "\"Mismatch during cbo.clean in Test Case 19!\""
test19_flush_str:  .string "\"Mismatch during cbo.flush in Test Case 19!\""
test19_inval_str:  .string "\"Mismatch during cbo.inval in Test Case 19!\""
test20_clean_str:  .string "\"Mismatch during cbo.clean in Test Case 20!\""
test20_flush_str:  .string "\"Mismatch during cbo.flush in Test Case 20!\""
test20_inval_str:  .string "\"Mismatch during cbo.inval in Test Case 20!\""
test21_clean_str:  .string "\"Mismatch during cbo.clean in Test Case 21!\""
test21_flush_str:  .string "\"Mismatch during cbo.flush in Test Case 21!\""
test21_inval_str:  .string "\"Mismatch during cbo.inval in Test Case 21!\""
test22_clean_str:  .string "\"Mismatch during cbo.clean in Test Case 22!\""
test22_flush_str:  .string "\"Mismatch during cbo.flush in Test Case 22!\""
test22_inval_str:  .string "\"Mismatch during cbo.inval in Test Case 22!\""
test23_clean_str:  .string "\"Mismatch during cbo.clean in Test Case 23!\""
test23_flush_str:  .string "\"Mismatch during cbo.flush in Test Case 23!\""
test23_inval_str:  .string "\"Mismatch during cbo.inval in Test Case 23!\""
test24_clean_str:  .string "\"Mismatch during cbo.clean in Test Case 24!\""
test24_flush_str:  .string "\"Mismatch during cbo.flush in Test Case 24!\""
test24_inval_str:  .string "\"Mismatch during cbo.inval in Test Case 24!\""
test25_clean_str:  .string "\"Mismatch during cbo.clean in Test Case 25!\""
test25_flush_str:  .string "\"Mismatch during cbo.flush in Test Case 25!\""
test25_inval_str:  .string "\"Mismatch during cbo.inval in Test Case 25!\""
test26_clean_str:  .string "\"Mismatch during cbo.clean in Test Case 26!\""
test26_flush_str:  .string "\"Mismatch during cbo.flush in Test Case 26!\""
test26_inval_str:  .string "\"Mismatch during cbo.inval in Test Case 26!\""

RVTEST_DATA_END
RVTEST_SIG_SETUP
