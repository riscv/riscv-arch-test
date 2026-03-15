// --------------------------------------------------------------------------------------------------------------------------------
// Developed by: Umer Shahid & Muhammad Zain
// --------------------------------------------------------------------------------------------------------------------------------
// Test cases are as follows:
// --------------------------------------------------------------------------------------------------------------------------------
// 1. At level 2, setup a PTE with V=0
//      → In S-Mode, execute cbo.zero. Expected: Store Page fault
// 2. At level 2, setup a PTE with reserved encoding R=0, W=1 & X=1
//      → In S-Mode, execute cbo.zero. Expected: Store Page fault
// 3. At level 2, setup a PTE with reserved encoding R=0, W=1 & X=0
//      → In S-Mode, execute cbo.zero. Expected: Store Page fault
// 4. At level 2, setup a PTE with RX permissions
//      → In S-Mode, execute cbo.zero. Expected: Store Page fault
// 5. At level 2, setup a PTE with RX permissions and set mstatus.SUM
//      → In S-Mode, execute cbo.zero. Expected: Store Page fault
// 6. At level 2, setup a PTE with RWX & U permissions
//      → In S-Mode, execute cbo.zero. Expected: Store Page fault
// 7. At level 2, setup a PTE with RWX permissions and A bit unset
//      → In S-Mode, execute cbo.zero. Expected: Store Page fault
// 8. At level 2, setup a PTE with RWX permissions and D bit unset
//      → In S-Mode, execute cbo.zero. Expected: Store Page fault
// 9. At level 2, setup a misaligned gigapage
//      → In S-Mode, execute cbo.zero. Expected: Store Page fault
// 10. At level 2, setup a PTE with RWX permissions that points to RVMODEL_ACCESS_FAULT_ADDRESS
//      → In S-Mode, execute cbo.zero. Expected: Store access fault
//
// 11. At level 1, setup a PTE with V=0
//      → In S-Mode, execute cbo.zero. Expected: Store Page fault
// 12. At level 1, setup a PTE with reserved encoding R=0, W=1 & X=1
//      → In S-Mode, execute cbo.zero. Expected: Store Page fault
// 13. At level 1, setup a PTE with reserved encoding R=0, W=1 & X=0
//      → In S-Mode, execute cbo.zero. Expected: Store Page fault
// 14. At level 1, setup a PTE with RX permissions
//      → In S-Mode, execute cbo.zero. Expected: Store Page fault
// 15. At level 1, setup a PTE with RX permissions and set mstatus.SUM
//      → In S-Mode, execute cbo.zero. Expected: Store Page fault
// 16. At level 1, setup a PTE with RWX & U permissions
//      → In S-Mode, execute cbo.zero. Expected: Store Page fault
// 17. At level 1, setup a PTE with RWX permissions and A bit unset
//      → In S-Mode, execute cbo.zero. Expected: Store Page fault
// 18. At level 1, setup a PTE with RWX permissions and D bit unset
//      → In S-Mode, execute cbo.zero. Expected: Store Page fault
// 19. At level 1, setup a misaligned megapage
//      → In S-Mode, execute cbo.zero. Expected: Store Page fault
// 20. At level 1, setup a PTE with non leaf (lvl 2) PTE pointing to RVMODEL_ACCESS_FAULT_ADDRESS instead of next page table
//      → In S-Mode, execute cbo.zero. Expected: Store access fault
// 21. At level 1, setup a PTE with RWX permissions that points to RVMODEL_ACCESS_FAULT_ADDRESS
//      → In S-Mode, execute cbo.zero. Expected: Store access fault
// 22. At level 1, setup a PTE with non leaf (lvl 2) PTE.D set
//      → In S-Mode, execute cbo.zero. Expected: Store Page fault
// 23. At level 1, setup a PTE with non leaf (lvl 2) PTE.A set
//      → In S-Mode, execute cbo.zero. Expected: Store Page fault
// 24. At level 1, setup a PTE with non leaf (lvl 2) PTE.U set
//      → In S-Mode, execute cbo.zero. Expected: Store Page fault
//
// 25. At level 0, setup a PTE with V=0
//      → In S-Mode, execute cbo.zero. Expected: Store Page fault
// 26. At level 0, setup a PTE with reserved encoding R=0, W=1 & X=1
//      → In S-Mode, execute cbo.zero. Expected: Store Page fault
// 27. At level 0, setup a PTE with reserved encoding R=0, W=1 & X=0
//      → In S-Mode, execute cbo.zero. Expected: Store Page fault
// 28. At level 0, setup a PTE with RX permissions
//      → In S-Mode, execute cbo.zero. Expected: Store Page fault
// 29. At level 0, setup a PTE with RX permissions and set mstatus.SUM
//      → In S-Mode, execute cbo.zero. Expected: Store Page fault
// 30. At level 0, setup a PTE with RWX & U permissions
//      → In S-Mode, execute cbo.zero. Expected: Store Page fault
// 31. At level 0, setup a PTE with RWX permissions and A bit unset
//      → In S-Mode, execute cbo.zero. Expected: Store Page fault
// 32. At level 0, setup a PTE with RWX permissions and D bit unset
//      → In S-Mode, execute cbo.zero. Expected: Store Page fault
// 33. At level 0, setup a PTE with only V bit set
//      → In S-Mode, execute cbo.zero. Expected: Store Page fault
// 34. At level 0, setup a PTE with non leaf (lvl 1) PTE pointing to RVMODEL_ACCESS_FAULT_ADDRESS instead of next page table
//      → In S-Mode, execute cbo.zero. Expected: Store access fault
// 35. At level 0, setup a PTE with RWX permissions that points to RVMODEL_ACCESS_FAULT_ADDRESS
//      → In S-Mode, execute cbo.zero. Expected: Store access fault
// 36. At level 0, setup a PTE with non leaf (lvl 1) PTE.D set
//      → In S-Mode, execute cbo.zero. Expected: Store Page fault
// 37. At level 0, setup a PTE with non leaf (lvl 1) PTE.A set
//      → In S-Mode, execute cbo.zero. Expected: Store Page fault
// 38. At level 0, setup a PTE with non leaf (lvl 1) PTE.U set
//      → In S-Mode, execute cbo.zero. Expected: Store Page fault
//
// Total Expected Faults :: 38
// --------------------------------------------------------------------------------------------------------------------------------

##### START_TEST_CONFIG #####
# REQUIRED_EXTENSIONS: [I, Sv39, Zicboz]
# MARCH: rv64i_zicsr_zicboz
# CONFIG_DEPENDENT: true
##### END_TEST_CONFIG #####

#define TEST_FILE "sv39_zicboz_exceptions_Smode.S"
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

  \TEST_CASE\():
  cbo.zero (a5)
  addi a4, a2, 4

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
  RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\(), \TEST_CASE\()_str)
.endm

// This TEST_CASES_RUNNER is used when PA is not a label
// Useful to test misaligned pages & pages at RVMODEL_ACCESS_FAULT_ADDRESS
.macro TEST_CASES_RUNNER_2 LOWER_MODE, PA, VA, level, TEST_CASE

  // Adjust offset of VA to point to test region
  .set VA_SHIFT, (\level*9)+12
  LI(a5, (\VA>>VA_SHIFT)<<VA_SHIFT)
  LI(a0, \PA)
  slli a0, a0, 64-VA_SHIFT
  srli a0, a0, 64-VA_SHIFT
  add  a5, a5, a0             // Virtual Address

  RVTEST_GOTO_LOWER_MODE \LOWER_MODE

  VERIFICATION_RWX \TEST_CASE

  RVTEST_GOTO_MMODE

  // Signature Update
  RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\(), \TEST_CASE\()_str)
.endm


main:
  li a2, 0x800              // Test signature initialization

//---------------------------------------------------------------------------------------------------------------------------------
//                                   Virtual addresses definition for code and test regions
//---------------------------------------------------------------------------------------------------------------------------------

  // Virtual Address of Test section (rvtest_data_1)
  .set va_data,               0x140802000

  // Virtual Address for code region
  .set va_rvtest_code_begin,  0x180000000


  // PTE setup for Code Region
  SUPERPAGE_PTE_SETUP_SV39(rvtest_code_begin, (PTE_D | PTE_A | PTE_X | PTE_R | PTE_V), va_rvtest_code_begin, LEVEL2)
  sfence.vma

  // Save area setup for code region
  csrr a0, mscratch
  SAVE_AREA_SETUP(va_rvtest_code_begin, rvtest_code_begin, code)

//---------------------------------------------------------------------------------------------------------------------------------
//                                               Test Cases Start from here
//---------------------------------------------------------------------------------------------------------------------------------

  SATP_SETUP_RV64(sv39)                                                  // Set SATP for virtualization
  sfence.vma                                                             // Flush TLB

  LI(t0, MENVCFG_CBZE)
  CSRS(menvcfg, t0)                                                      // Allow execution of cbo.zero in S-Mode

//---------------------------------------------------------------------------------------------------------------------------------
//---------------------------------------------------------------------------------------------------------------------------------
//                                                    TESTS AT LEVEL 2
//---------------------------------------------------------------------------------------------------------------------------------
//                    1GB PAGE    Region 1 under test at level 2 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 1: Test in S-Mode | V bit unset | expected = Store Page fault
  SUPERPAGE_PTE_SETUP_SV39(rvtest_data_1, (PTE_D | PTE_A | PTE_X | PTE_W | PTE_R), va_data, LEVEL2)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL2, test1

//---------------------------------------------------------------------------------------------------------------------------------
//                    1GB PAGE    Region 1 under test at level 2 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 2: Test in S-Mode | WX bit set | expected = Store Page fault
  SUPERPAGE_PTE_SETUP_SV39(rvtest_data_1, (PTE_D | PTE_A | PTE_X | PTE_W | PTE_V), va_data, LEVEL2)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL2, test2

//---------------------------------------------------------------------------------------------------------------------------------
//                    1GB PAGE    Region 1 under test at level 2 -- RWX permission given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 3: Test in S-Mode | W bit set | expected = Store Page fault
  SUPERPAGE_PTE_SETUP_SV39(rvtest_data_1, (PTE_D | PTE_A | PTE_W | PTE_V), va_data, LEVEL2)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL2, test3

//---------------------------------------------------------------------------------------------------------------------------------
//                    1GB PAGE    Region 1 under test at level 2 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 4: Test in S-Mode | RX bit set | expected = Store Page fault
  SUPERPAGE_PTE_SETUP_SV39(rvtest_data_1, (PTE_D | PTE_A | PTE_X | PTE_R | PTE_V), va_data, LEVEL2)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL2, test4

//---------------------------------------------------------------------------------------------------------------------------------
//                    1GB PAGE    Region 1 under test at level 2 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 5: Test in S-Mode | RX bit set | mstatus.SUM set | expected = Store Page fault
  SUPERPAGE_PTE_SETUP_SV39(rvtest_data_1, (PTE_D | PTE_A | PTE_X | PTE_R | PTE_V), va_data, LEVEL2)
  sfence.vma

  LI(t0, MSTATUS_SUM)
  CSRS(mstatus, t0)                                               // Set mstatus.SUM
  TEST_CASES_RUNNER Smode, va_data, LEVEL2, test5
  LI(t0, MSTATUS_SUM)
  CSRC(mstatus, t0)                                               // Clear mstatus.SUM

//---------------------------------------------------------------------------------------------------------------------------------
//                    1GB PAGE    Region 1 under test at level 2 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 6: Test in S-Mode | RWXU bit set | expected = Store Page fault
  SUPERPAGE_PTE_SETUP_SV39(rvtest_data_1, (PTE_D | PTE_A | PTE_U | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL2)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL2, test6

//---------------------------------------------------------------------------------------------------------------------------------
//                    1GB PAGE    Region 1 under test at level 2 -- RWX permission given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 7: Test in S-Mode | PTE.A unset | expected = Store Page fault
  SUPERPAGE_PTE_SETUP_SV39(rvtest_data_1, (PTE_D | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL2)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL2, test7

//---------------------------------------------------------------------------------------------------------------------------------
//                    1GB PAGE    Region 1 under test at level 2 -- RWX permission given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 8: Test in S-Mode | PTE.D unset | expected = Store Page fault
  SUPERPAGE_PTE_SETUP_SV39(rvtest_data_1, (PTE_A | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL2)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL2, test8

//---------------------------------------------------------------------------------------------------------------------------------
//                    1GB PAGE    Region 1 under test at level 2 -- RWX permission given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 9: Test in S-Mode | RWX bit set | Misaligned Gigapage | expected = Store Page fault
  PTE_SETUP_SV39(rvtest_data_1, (PTE_D | PTE_A | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL2)
  sfence.vma

  TEST_CASES_RUNNER_2 Smode, 0x0, va_data, LEVEL2, test9

//---------------------------------------------------------------------------------------------------------------------------------
//                    1GB PAGE    Region 1 under test at level 2 -- RWX permission given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 10: Test in S-Mode | RWX bit set | expected = Store access fault
  SUPERPAGE_PTE_SETUP_SV39(RVMODEL_ACCESS_FAULT_ADDRESS, (PTE_D | PTE_A | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL2)
  sfence.vma

  TEST_CASES_RUNNER_2 Smode, RVMODEL_ACCESS_FAULT_ADDRESS, va_data, LEVEL2, test10


//---------------------------------------------------------------------------------------------------------------------------------
//---------------------------------------------------------------------------------------------------------------------------------
//                                                    TESTS AT LEVEL 1
//---------------------------------------------------------------------------------------------------------------------------------
//                    2MB PAGE    Region 1 under test at level 1 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 11: Test in S-Mode | V bit unset | expected = Store Page fault
  PTE_SETUP_SV39(rvtest_slvl1_pg_tbl, (PTE_V), va_data, LEVEL2)
  SUPERPAGE_PTE_SETUP_SV39(rvtest_data_1, (PTE_D | PTE_A | PTE_X | PTE_W | PTE_R), va_data, LEVEL1)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL1, test11

//---------------------------------------------------------------------------------------------------------------------------------
//                    2MB PAGE    Region 1 under test at level 1 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 12: Test in S-Mode | WX bit set | expected = Store Page fault
  PTE_SETUP_SV39(rvtest_slvl1_pg_tbl, (PTE_V), va_data, LEVEL2)
  SUPERPAGE_PTE_SETUP_SV39(rvtest_data_1, (PTE_D | PTE_A | PTE_X | PTE_W | PTE_V), va_data, LEVEL1)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL1, test12

//---------------------------------------------------------------------------------------------------------------------------------
//                    2MB PAGE    Region 1 under test at level 1 -- RWX permission given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 13: Test in S-Mode | W bit set | expected = Store Page fault
  PTE_SETUP_SV39(rvtest_slvl1_pg_tbl, (PTE_V), va_data, LEVEL2)
  SUPERPAGE_PTE_SETUP_SV39(rvtest_data_1, (PTE_D | PTE_A | PTE_W | PTE_V), va_data, LEVEL1)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL1, test13

//---------------------------------------------------------------------------------------------------------------------------------
//                    2MB PAGE    Region 1 under test at level 1 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 14: Test in S-Mode | RX bit set | expected = Store Page fault
  PTE_SETUP_SV39(rvtest_slvl1_pg_tbl, (PTE_V), va_data, LEVEL2)
  SUPERPAGE_PTE_SETUP_SV39(rvtest_data_1, (PTE_D | PTE_A | PTE_X | PTE_R | PTE_V), va_data, LEVEL1)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL1, test14

//---------------------------------------------------------------------------------------------------------------------------------
//                    2MB PAGE    Region 1 under test at level 1 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 15: Test in S-Mode | RX bit set | expected = Store Page fault
  PTE_SETUP_SV39(rvtest_slvl1_pg_tbl, (PTE_V), va_data, LEVEL2)
  SUPERPAGE_PTE_SETUP_SV39(rvtest_data_1, (PTE_D | PTE_A | PTE_X | PTE_R | PTE_V), va_data, LEVEL1)
  sfence.vma

  LI(t0, MSTATUS_SUM)
  CSRS(mstatus, t0)                                               // Set mstatus.SUM
  TEST_CASES_RUNNER Smode, va_data, LEVEL1, test15
  LI(t0, MSTATUS_SUM)
  CSRC(mstatus, t0)                                               // Clear mstatus.SUM

//---------------------------------------------------------------------------------------------------------------------------------
//                    2MB PAGE    Region 1 under test at level 1 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 16: Test in S-Mode | RWXU bit set | expected = Store Page fault
  PTE_SETUP_SV39(rvtest_slvl1_pg_tbl, (PTE_V), va_data, LEVEL2)
  SUPERPAGE_PTE_SETUP_SV39(rvtest_data_1, (PTE_D | PTE_A | PTE_U | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL1)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL1, test16

//---------------------------------------------------------------------------------------------------------------------------------
//                    2MB PAGE    Region 1 under test at level 1 -- RWX permission given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 17: Test in S-Mode | PTE.A unset | expected = Store Page fault
  PTE_SETUP_SV39(rvtest_slvl1_pg_tbl, (PTE_V), va_data, LEVEL2)
  SUPERPAGE_PTE_SETUP_SV39(rvtest_data_1, (PTE_D | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL1)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL1, test17

//---------------------------------------------------------------------------------------------------------------------------------
//                    2MB PAGE    Region 1 under test at level 1 -- RWX permission given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 18: Test in S-Mode | PTE.D unset | expected = Store Page fault
  PTE_SETUP_SV39(rvtest_slvl1_pg_tbl, (PTE_V), va_data, LEVEL2)
  SUPERPAGE_PTE_SETUP_SV39(rvtest_data_1, (PTE_A | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL1)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL1, test18

//---------------------------------------------------------------------------------------------------------------------------------
//                    2MB PAGE    Region 1 under test at level 1 -- RWX permission given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 19: Test in S-Mode | RWX bit set | Misaligned Megapage | expected = Store Page fault
  PTE_SETUP_SV39(rvtest_slvl1_pg_tbl, (PTE_V), va_data, LEVEL2)
  PTE_SETUP_SV39(rvtest_data_1, (PTE_D | PTE_A | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL1)
  sfence.vma

  TEST_CASES_RUNNER_2 Smode, 0x0, va_data, LEVEL1, test19

//---------------------------------------------------------------------------------------------------------------------------------
//                    2MB PAGE    Region 1 under test at level 1 -- RWX permission given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 20: Test in S-Mode | Incorrect PTE setup | expected = Store access fault
  PTE_SETUP_SV39(RVMODEL_ACCESS_FAULT_ADDRESS, (PTE_V), va_data, LEVEL2)
  SUPERPAGE_PTE_SETUP_SV39(rvtest_data_1, (PTE_A | PTE_D | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL1)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL1, test20

//---------------------------------------------------------------------------------------------------------------------------------
//                    2MB PAGE    Region 1 under test at level 1 -- RWX permission given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 21: Test in S-Mode | RWX bit set | expected = Store access fault
  PTE_SETUP_SV39(rvtest_slvl1_pg_tbl, (PTE_V), va_data, LEVEL2)
  SUPERPAGE_PTE_SETUP_SV39(RVMODEL_ACCESS_FAULT_ADDRESS, (PTE_D | PTE_A | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL1)
  sfence.vma

  TEST_CASES_RUNNER_2 Smode, RVMODEL_ACCESS_FAULT_ADDRESS, va_data, LEVEL1, test21

//---------------------------------------------------------------------------------------------------------------------------------
//                    2MB PAGE    Region 1 under test at level 1 -- RWX permission given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 22: Test in S-Mode | PTE.D set for level 2 PTE | expected = Store Page fault
  PTE_SETUP_SV39(rvtest_slvl1_pg_tbl, (PTE_D | PTE_V), va_data, LEVEL2)
  SUPERPAGE_PTE_SETUP_SV39(rvtest_data_1, (PTE_D | PTE_A | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL1)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL1, test22

//---------------------------------------------------------------------------------------------------------------------------------
//                    2MB PAGE    Region 1 under test at level 1 -- RWX permission given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 23: Test in S-Mode | PTE.A set for level 2 PTE | expected = Store Page fault
  PTE_SETUP_SV39(rvtest_slvl1_pg_tbl, (PTE_A | PTE_V), va_data, LEVEL2)
  SUPERPAGE_PTE_SETUP_SV39(rvtest_data_1, (PTE_D | PTE_A | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL0)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL1, test23

//---------------------------------------------------------------------------------------------------------------------------------
//                    2MB PAGE    Region 1 under test at level 1 -- RWX permission given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 24: Test in S-Mode | PTE.U set for level 2 PTE | expected = Store Page fault
  PTE_SETUP_SV39(rvtest_slvl1_pg_tbl, (PTE_U | PTE_V), va_data, LEVEL2)
  SUPERPAGE_PTE_SETUP_SV39(rvtest_data_1, (PTE_D | PTE_A | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL1)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL1, test24


//---------------------------------------------------------------------------------------------------------------------------------
//---------------------------------------------------------------------------------------------------------------------------------
//                                                    TESTS AT LEVEL 0
//---------------------------------------------------------------------------------------------------------------------------------
//                    4KB PAGE    Region 1 under test at level 0 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 25: Test in S-Mode | V bit unset | expected = Store Page fault
  PTE_SETUP_SV39(rvtest_slvl1_pg_tbl, (PTE_V), va_data, LEVEL2)
  PTE_SETUP_SV39(rvtest_slvl0_pg_tbl, (PTE_V), va_data, LEVEL1)
  PTE_SETUP_SV39(rvtest_data_1, (PTE_D | PTE_A | PTE_X | PTE_W | PTE_R), va_data, LEVEL0)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL0, test25

//---------------------------------------------------------------------------------------------------------------------------------
//                    4KB PAGE    Region 1 under test at level 0 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 26: Test in S-Mode | WX bit set | expected = Store Page fault
  PTE_SETUP_SV39(rvtest_slvl1_pg_tbl, (PTE_V), va_data, LEVEL2)
  PTE_SETUP_SV39(rvtest_slvl0_pg_tbl, (PTE_V), va_data, LEVEL1)
  PTE_SETUP_SV39(rvtest_data_1, (PTE_D | PTE_A | PTE_X | PTE_W | PTE_V), va_data, LEVEL0)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL0, test26

//---------------------------------------------------------------------------------------------------------------------------------
//                    4KB PAGE    Region 1 under test at level 0 -- RWX permission given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 27: Test in S-Mode | W bit set | expected = Store Page fault
  PTE_SETUP_SV39(rvtest_slvl1_pg_tbl, (PTE_V), va_data, LEVEL2)
  PTE_SETUP_SV39(rvtest_slvl0_pg_tbl, (PTE_V), va_data, LEVEL1)
  PTE_SETUP_SV39(rvtest_data_1, (PTE_D | PTE_A | PTE_W | PTE_V), va_data, LEVEL0)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL0, test27

//---------------------------------------------------------------------------------------------------------------------------------
//                    4KB PAGE    Region 1 under test at level 0 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 28: Test in S-Mode | RX bit set | expected = Store Page fault
  PTE_SETUP_SV39(rvtest_slvl1_pg_tbl, (PTE_V), va_data, LEVEL2)
  PTE_SETUP_SV39(rvtest_slvl0_pg_tbl, (PTE_V), va_data, LEVEL1)
  PTE_SETUP_SV39(rvtest_data_1, (PTE_D | PTE_A | PTE_X | PTE_R | PTE_V), va_data, LEVEL0)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL0, test28

//---------------------------------------------------------------------------------------------------------------------------------
//                    4KB PAGE    Region 1 under test at level 0 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 29: Test in S-Mode | RX bit set | expected = Store Page fault
  PTE_SETUP_SV39(rvtest_slvl1_pg_tbl, (PTE_V), va_data, LEVEL2)
  PTE_SETUP_SV39(rvtest_slvl0_pg_tbl, (PTE_V), va_data, LEVEL1)
  PTE_SETUP_SV39(rvtest_data_1, (PTE_D | PTE_A | PTE_X | PTE_R | PTE_V), va_data, LEVEL0)
  sfence.vma

  LI(t0, MSTATUS_SUM)
  CSRS(mstatus, t0)                                               // Set mstatus.SUM
  TEST_CASES_RUNNER Smode, va_data, LEVEL0, test29
  LI(t0, MSTATUS_SUM)
  CSRC(mstatus, t0)                                               // Clear mstatus.SUM

//---------------------------------------------------------------------------------------------------------------------------------
//                    4KB PAGE    Region 1 under test at level 0 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 30: Test in S-Mode | RWXU bit set | expected = Store Page fault
  PTE_SETUP_SV39(rvtest_slvl1_pg_tbl, (PTE_V), va_data, LEVEL2)
  PTE_SETUP_SV39(rvtest_slvl0_pg_tbl, (PTE_V), va_data, LEVEL1)
  PTE_SETUP_SV39(rvtest_data_1, (PTE_D | PTE_A | PTE_U | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL0)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL0, test30

//---------------------------------------------------------------------------------------------------------------------------------
//                    4KB PAGE    Region 1 under test at level 0 -- RWX permission given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 31: Test in S-Mode | PTE.A unset | expected = Store Page fault
  PTE_SETUP_SV39(rvtest_slvl1_pg_tbl, (PTE_V), va_data, LEVEL2)
  PTE_SETUP_SV39(rvtest_slvl0_pg_tbl, (PTE_V), va_data, LEVEL1)
  PTE_SETUP_SV39(rvtest_data_1, (PTE_D | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL0)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL0, test31

//---------------------------------------------------------------------------------------------------------------------------------
//                    4KB PAGE    Region 1 under test at level 0 -- RWX permission given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 32: Test in S-Mode | PTE.D unset | expected = Store Page fault
  PTE_SETUP_SV39(rvtest_slvl1_pg_tbl, (PTE_V), va_data, LEVEL2)
  PTE_SETUP_SV39(rvtest_slvl0_pg_tbl, (PTE_V), va_data, LEVEL1)
  PTE_SETUP_SV39(rvtest_data_1, (PTE_A | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL0)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL0, test32

//---------------------------------------------------------------------------------------------------------------------------------
//                    4KB PAGE    Region 1 under test at level 0 -- RWX permission given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 33: Test in S-Mode | Only V bit set at Level 0 | expected = Store Page fault
  PTE_SETUP_SV39(rvtest_slvl1_pg_tbl, (PTE_V), va_data, LEVEL2)
  PTE_SETUP_SV39(rvtest_slvl0_pg_tbl, (PTE_V), va_data, LEVEL1)
  PTE_SETUP_SV39(rvtest_data_1, (PTE_V), va_data, LEVEL0)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL0, test33

//---------------------------------------------------------------------------------------------------------------------------------
//                    4KB PAGE    Region 1 under test at level 0 -- RWX permission given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 34: Test in S-Mode | Incorrect PTE setup | expected = Store access fault
  PTE_SETUP_SV39(rvtest_slvl1_pg_tbl, (PTE_V), va_data, LEVEL2)
  PTE_SETUP_SV39(RVMODEL_ACCESS_FAULT_ADDRESS, (PTE_V), va_data, LEVEL1)
  PTE_SETUP_SV39(rvtest_data_1, (PTE_D | PTE_A | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL0)
  sfence.vma

  TEST_CASES_RUNNER_2 Smode, RVMODEL_ACCESS_FAULT_ADDRESS, va_data, LEVEL0, test34

//---------------------------------------------------------------------------------------------------------------------------------
//                    4KB PAGE    Region 1 under test at level 0 -- RWX permission given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 35: Test in S-Mode | RWX bit set | expected = Store access fault
  PTE_SETUP_SV39(rvtest_slvl1_pg_tbl, (PTE_V), va_data, LEVEL2)
  PTE_SETUP_SV39(rvtest_slvl0_pg_tbl, (PTE_V), va_data, LEVEL1)
  PTE_SETUP_SV39(RVMODEL_ACCESS_FAULT_ADDRESS, (PTE_D | PTE_A | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL0)
  sfence.vma

  TEST_CASES_RUNNER_2 Smode, RVMODEL_ACCESS_FAULT_ADDRESS, va_data, LEVEL0, test35

//---------------------------------------------------------------------------------------------------------------------------------
//                    4KB PAGE    Region 1 under test at level 0 -- RWX permission given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 36: Test in S-Mode | PTE.D set for level 1 PTE | expected = Store Page fault
  PTE_SETUP_SV39(rvtest_slvl1_pg_tbl, (PTE_V), va_data, LEVEL2)
  PTE_SETUP_SV39(rvtest_slvl0_pg_tbl, (PTE_D | PTE_V), va_data, LEVEL1)
  PTE_SETUP_SV39(rvtest_data_1, (PTE_D | PTE_A | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL0)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL0, test36

//---------------------------------------------------------------------------------------------------------------------------------
//                    4KB PAGE    Region 1 under test at level 0 -- RWX permission given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 37: Test in S-Mode | PTE.A set for level 1 PTE | expected = Store Page fault
  PTE_SETUP_SV39(rvtest_slvl1_pg_tbl, (PTE_V), va_data, LEVEL2)
  PTE_SETUP_SV39(rvtest_slvl0_pg_tbl, (PTE_A | PTE_V), va_data, LEVEL1)
  PTE_SETUP_SV39(rvtest_data_1, (PTE_D | PTE_A | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL0)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL0, test37

//---------------------------------------------------------------------------------------------------------------------------------
//                    4KB PAGE    Region 1 under test at level 0 -- RWX permission given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 38: Test in S-Mode | PTE.U set for level 1 PTE | expected = Store Page fault
  PTE_SETUP_SV39(rvtest_slvl1_pg_tbl, (PTE_V), va_data, LEVEL2)
  PTE_SETUP_SV39(rvtest_slvl0_pg_tbl, (PTE_U | PTE_V), va_data, LEVEL1)
  PTE_SETUP_SV39(rvtest_data_1, (PTE_D | PTE_A | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL0)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL0, test38


//---------------------------------------------------------------------------------------------------------------------------------
RVTEST_CODE_END
RVTEST_DATA_BEGIN

//---------------------------------------------------------------------------------------------------------------------------------
//                                            PHYSICAL ADDRESS REGION FOR TESTING
//---------------------------------------------------------------------------------------------------------------------------------
// Physical Address region under testing for LEVEL 0, 1 and 2
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

canary_mismatch:  .string "Testcase signature canary mismatch!"
test1_str:  .string "\"Mismatch during cbo.zero in Test Case 1!\""
test2_str:  .string "\"Mismatch during cbo.zero in Test Case 2!\""
test3_str:  .string "\"Mismatch during cbo.zero in Test Case 3!\""
test4_str:  .string "\"Mismatch during cbo.zero in Test Case 4!\""
test5_str:  .string "\"Mismatch during cbo.zero in Test Case 5!\""
test6_str:  .string "\"Mismatch during cbo.zero in Test Case 6!\""
test7_str:  .string "\"Mismatch during cbo.zero in Test Case 7!\""
test8_str:  .string "\"Mismatch during cbo.zero in Test Case 8!\""
test9_str:  .string "\"Mismatch during cbo.zero in Test Case 9!\""
test10_str:  .string "\"Mismatch during cbo.zero in Test Case 10!\""
test11_str:  .string "\"Mismatch during cbo.zero in Test Case 11!\""
test12_str:  .string "\"Mismatch during cbo.zero in Test Case 12!\""
test13_str:  .string "\"Mismatch during cbo.zero in Test Case 13!\""
test14_str:  .string "\"Mismatch during cbo.zero in Test Case 14!\""
test15_str:  .string "\"Mismatch during cbo.zero in Test Case 15!\""
test16_str:  .string "\"Mismatch during cbo.zero in Test Case 16!\""
test17_str:  .string "\"Mismatch during cbo.zero in Test Case 17!\""
test18_str:  .string "\"Mismatch during cbo.zero in Test Case 18!\""
test19_str:  .string "\"Mismatch during cbo.zero in Test Case 19!\""
test20_str:  .string "\"Mismatch during cbo.zero in Test Case 20!\""
test21_str:  .string "\"Mismatch during cbo.zero in Test Case 21!\""
test22_str:  .string "\"Mismatch during cbo.zero in Test Case 22!\""
test23_str:  .string "\"Mismatch during cbo.zero in Test Case 23!\""
test24_str:  .string "\"Mismatch during cbo.zero in Test Case 24!\""
test25_str:  .string "\"Mismatch during cbo.zero in Test Case 25!\""
test26_str:  .string "\"Mismatch during cbo.zero in Test Case 26!\""
test27_str:  .string "\"Mismatch during cbo.zero in Test Case 27!\""
test28_str:  .string "\"Mismatch during cbo.zero in Test Case 28!\""
test29_str:  .string "\"Mismatch during cbo.zero in Test Case 29!\""
test30_str:  .string "\"Mismatch during cbo.zero in Test Case 30!\""
test31_str:  .string "\"Mismatch during cbo.zero in Test Case 31!\""
test32_str:  .string "\"Mismatch during cbo.zero in Test Case 32!\""
test33_str:  .string "\"Mismatch during cbo.zero in Test Case 33!\""
test34_str:  .string "\"Mismatch during cbo.zero in Test Case 34!\""
test35_str:  .string "\"Mismatch during cbo.zero in Test Case 35!\""
test36_str:  .string "\"Mismatch during cbo.zero in Test Case 36!\""
test37_str:  .string "\"Mismatch during cbo.zero in Test Case 37!\""
test38_str:  .string "\"Mismatch during cbo.zero in Test Case 38!\""

RVTEST_DATA_END
RVTEST_SIG_SETUP
