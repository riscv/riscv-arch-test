// --------------------------------------------------------------------------------------------------------------------------------
// Developed by: Umer Shahid & Muhammad Zain
// --------------------------------------------------------------------------------------------------------------------------------
// Test cases are as follows:
// --------------------------------------------------------------------------------------------------------------------------------
// 1. At level 4, setup a PTE with V=0
//      → In U-Mode, execute cbo.zero. Expected: Store Page fault
// 2. At level 4, setup a PTE with reserved encoding R=0, W=1 & X=1
//      → In U-Mode, execute cbo.zero. Expected: Store Page fault
// 3. At level 4, setup a PTE with reserved encoding R=0, W=1 & X=0
//      → In U-Mode, execute cbo.zero. Expected: Store Page fault
// 4. At level 4, setup a PTE with RX permissions
//      → In U-Mode, execute cbo.zero. Expected: Store Page fault
// 5. At level 4, setup a PTE with RWX permissions & U bit unset
//      → In U-Mode, execute cbo.zero. Expected: Store Page fault
// 6. At level 4, setup a PTE with RWX permissions and A bit unset
//      → In U-Mode, execute cbo.zero. Expected: Store Page fault
// 7. At level 4, setup a PTE with RWX permissions and D bit unset
//      → In U-Mode, execute cbo.zero. Expected: Store Page fault
// 8. At level 4, setup a misaligned petapage
//      → In U-Mode, execute cbo.zero. Expected: Store Page fault
// 9. At level 4, setup a PTE with RWX permissions that points to RVMODEL_ACCESS_FAULT_ADDRESS
//      → In U-Mode, execute cbo.zero. Expected: Store access fault
//
// 10. At level 3, setup a PTE with V=0
//      → In U-Mode, execute cbo.zero. Expected: Store Page fault
// 11. At level 3, setup a PTE with reserved encoding R=0, W=1 & X=1
//      → In U-Mode, execute cbo.zero. Expected: Store Page fault
// 12. At level 3, setup a PTE with reserved encoding R=0, W=1 & X=0
//      → In U-Mode, execute cbo.zero. Expected: Store Page fault
// 13. At level 3, setup a PTE with RX permissions
//      → In U-Mode, execute cbo.zero. Expected: Store Page fault
// 14. At level 3, setup a PTE with RWX permissions & U bit unset
//      → In U-Mode, execute cbo.zero. Expected: Store Page fault
// 15. At level 3, setup a PTE with RWX permissions and A bit unset
//      → In U-Mode, execute cbo.zero. Expected: Store Page fault
// 16. At level 3, setup a PTE with RWX permissions and D bit unset
//      → In U-Mode, execute cbo.zero. Expected: Store Page fault
// 17. At level 3, setup a misaligned terapage
//      → In U-Mode, execute cbo.zero. Expected: Store Page fault
// 18. At level 3, setup a PTE with non leaf (lvl 4) PTE pointing to RVMODEL_ACCESS_FAULT_ADDRESS instead of next page table
//      → In U-Mode, execute cbo.zero. Expected: Store access fault
// 19. At level 3, setup a PTE with RWX permissions that points to RVMODEL_ACCESS_FAULT_ADDRESS
//      → In U-Mode, execute cbo.zero. Expected: Store access fault
// 20. At level 3, setup a PTE with non leaf (lvl 4) PTE.D set
//      → In U-Mode, execute cbo.zero. Expected: Store Page fault
// 21. At level 3, setup a PTE with non leaf (lvl 4) PTE.A set
//      → In U-Mode, execute cbo.zero. Expected: Store Page fault
// 22. At level 3, setup a PTE with non leaf (lvl 4) PTE.U set
//      → In U-Mode, execute cbo.zero. Expected: Store Page fault
//
// 23. At level 2, setup a PTE with V=0
//      → In U-Mode, execute cbo.zero. Expected: Store Page fault
// 24. At level 2, setup a PTE with reserved encoding R=0, W=1 & X=1
//      → In U-Mode, execute cbo.zero. Expected: Store Page fault
// 25. At level 2, setup a PTE with reserved encoding R=0, W=1 & X=0
//      → In U-Mode, execute cbo.zero. Expected: Store Page fault
// 26. At level 2, setup a PTE with RX permissions
//      → In U-Mode, execute cbo.zero. Expected: Store Page fault
// 27. At level 2, setup a PTE with RWX permissions & U bit unset
//      → In U-Mode, execute cbo.zero. Expected: Store Page fault
// 28. At level 2, setup a PTE with RWX permissions and A bit unset
//      → In U-Mode, execute cbo.zero. Expected: Store Page fault
// 29. At level 2, setup a PTE with RWX permissions and D bit unset
//      → In U-Mode, execute cbo.zero. Expected: Store Page fault
// 30. At level 2, setup a misaligned gigapage
//      → In U-Mode, execute cbo.zero. Expected: Store Page fault
// 31. At level 2, setup a PTE with non leaf (lvl 3) PTE pointing to RVMODEL_ACCESS_FAULT_ADDRESS instead of next page table
//      → In U-Mode, execute cbo.zero. Expected: Store access fault
// 32. At level 2, setup a PTE with RWX permissions that points to RVMODEL_ACCESS_FAULT_ADDRESS
//      → In U-Mode, execute cbo.zero. Expected: Store access fault
// 33. At level 2, setup a PTE with non leaf (lvl 3) PTE.D set
//      → In U-Mode, execute cbo.zero. Expected: Store Page fault
// 34. At level 2, setup a PTE with non leaf (lvl 3) PTE.A set
//      → In U-Mode, execute cbo.zero. Expected: Store Page fault
// 35. At level 2, setup a PTE with non leaf (lvl 3) PTE.U set
//      → In U-Mode, execute cbo.zero. Expected: Store Page fault
//
// 36. At level 1, setup a PTE with V=0
//      → In U-Mode, execute cbo.zero. Expected: Store Page fault
// 37. At level 1, setup a PTE with reserved encoding R=0, W=1 & X=1
//      → In U-Mode, execute cbo.zero. Expected: Store Page fault
// 38. At level 1, setup a PTE with reserved encoding R=0, W=1 & X=0
//      → In U-Mode, execute cbo.zero. Expected: Store Page fault
// 39. At level 1, setup a PTE with RX permissions
//      → In U-Mode, execute cbo.zero. Expected: Store Page fault
// 40. At level 1, setup a PTE with RWX permissions & U bit unset
//      → In U-Mode, execute cbo.zero. Expected: Store Page fault
// 41. At level 1, setup a PTE with RWX permissions and A bit unset
//      → In U-Mode, execute cbo.zero. Expected: Store Page fault
// 42. At level 1, setup a PTE with RWX permissions and D bit unset
//      → In U-Mode, execute cbo.zero. Expected: Store Page fault
// 43. At level 1, setup a misaligned megapage
//      → In U-Mode, execute cbo.zero. Expected: Store Page fault
// 44. At level 1, setup a PTE with non leaf (lvl 2) PTE pointing to RVMODEL_ACCESS_FAULT_ADDRESS instead of next page table
//      → In U-Mode, execute cbo.zero. Expected: Store access fault
// 45. At level 1, setup a PTE with RWX permissions that points to RVMODEL_ACCESS_FAULT_ADDRESS
//      → In U-Mode, execute cbo.zero. Expected: Store access fault
// 46. At level 1, setup a PTE with non leaf (lvl 2) PTE.D set
//      → In U-Mode, execute cbo.zero. Expected: Store Page fault
// 47. At level 1, setup a PTE with non leaf (lvl 2) PTE.A set
//      → In U-Mode, execute cbo.zero. Expected: Store Page fault
// 48. At level 1, setup a PTE with non leaf (lvl 2) PTE.U set
//      → In U-Mode, execute cbo.zero. Expected: Store Page fault
//
// 49. At level 0, setup a PTE with V=0
//      → In U-Mode, execute cbo.zero. Expected: Store Page fault
// 50. At level 0, setup a PTE with reserved encoding R=0, W=1 & X=1
//      → In U-Mode, execute cbo.zero. Expected: Store Page fault
// 51. At level 0, setup a PTE with reserved encoding R=0, W=1 & X=0
//      → In U-Mode, execute cbo.zero. Expected: Store Page fault
// 52. At level 0, setup a PTE with RX permissions
//      → In U-Mode, execute cbo.zero. Expected: Store Page fault
// 53. At level 0, setup a PTE with RWX permissions & U bit unset
//      → In U-Mode, execute cbo.zero. Expected: Store Page fault
// 54. At level 0, setup a PTE with RWX permissions and A bit unset
//      → In U-Mode, execute cbo.zero. Expected: Store Page fault
// 55. At level 0, setup a PTE with RWX permissions and D bit unset
//      → In U-Mode, execute cbo.zero. Expected: Store Page fault
// 56. At level 0, setup a PTE with only V bit set
//      → In U-Mode, execute cbo.zero. Expected: Store Page fault
// 57. At level 0, setup a PTE with non leaf (lvl 1) PTE pointing to RVMODEL_ACCESS_FAULT_ADDRESS instead of next page table
//      → In U-Mode, execute cbo.zero. Expected: Store access fault
// 58. At level 0, setup a PTE with RWX permissions that points to RVMODEL_ACCESS_FAULT_ADDRESS
//      → In U-Mode, execute cbo.zero. Expected: Store access fault
// 59. At level 0, setup a PTE with non leaf (lvl 1) PTE.D set
//      → In U-Mode, execute cbo.zero. Expected: Store Page fault
// 60. At level 0, setup a PTE with non leaf (lvl 1) PTE.A set
//      → In U-Mode, execute cbo.zero. Expected: Store Page fault
// 61. At level 0, setup a PTE with non leaf (lvl 1) PTE.U set
//      → In U-Mode, execute cbo.zero. Expected: Store Page fault
//
// Total Expected Faults :: 61
// --------------------------------------------------------------------------------------------------------------------------------

// Remove NORUN once Sail version 0.11 is released
##### START_TEST_CONFIG #####
# REQUIRED_EXTENSIONS: [I, Sv57, Zicboz, NORUN]
# MARCH: rv64i_zicsr_zicboz
# CONFIG_DEPENDENT: true
##### END_TEST_CONFIG #####

#define TEST_FILE "sv57_zicboz_exceptions_Umode.S"
#define SIGUPD_COUNT 70
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
  LI( a2, 0x800)            // Test signature initialization

//---------------------------------------------------------------------------------------------------------------------------------
//                                   Virtual addresses definition for code and test regions
//---------------------------------------------------------------------------------------------------------------------------------

  // Virtual Address of Test section (rvtest_data_1)
  .set va_data,               0x07028500403000

  // Virtual Address for code region
  .set va_rvtest_code_begin,  0x03000080000000


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

  LI(t0, MENVCFG_CBZE)
  CSRS(menvcfg, t0)                                                      // Allow execution of cbo.zero in S-Mode
  CSRS(senvcfg, t0)                                                      // Further delegate the permission to U-Mode

//---------------------------------------------------------------------------------------------------------------------------------
//---------------------------------------------------------------------------------------------------------------------------------
//                                                    TESTS AT LEVEL 4
//---------------------------------------------------------------------------------------------------------------------------------
//                    256TB PAGE    Region 1 under test at level 4 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 1: Test in U-Mode | V bit unset | expected = Store Page fault
  SUPERPAGE_PTE_SETUP_SV57(rvtest_data_1, (PTE_D | PTE_A | PTE_U | PTE_X | PTE_W | PTE_R), va_data, LEVEL4)
  sfence.vma

  TEST_CASES_RUNNER Umode, va_data, LEVEL4, test1

//---------------------------------------------------------------------------------------------------------------------------------
//                    256TB PAGE    Region 1 under test at level 4 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 2: Test in U-Mode | WX bit set | expected = Store Page fault
  SUPERPAGE_PTE_SETUP_SV57(rvtest_data_1, (PTE_D | PTE_A | PTE_U | PTE_X | PTE_W | PTE_V), va_data, LEVEL4)
  sfence.vma

  TEST_CASES_RUNNER Umode, va_data, LEVEL4, test2

//---------------------------------------------------------------------------------------------------------------------------------
//                    256TB PAGE    Region 1 under test at level 4 -- RWX permission given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 3: Test in U-Mode | W bit set | expected = Store Page fault
  SUPERPAGE_PTE_SETUP_SV57(rvtest_data_1, (PTE_D | PTE_A | PTE_U | PTE_W | PTE_V), va_data, LEVEL4)
  sfence.vma

  TEST_CASES_RUNNER Umode, va_data, LEVEL4, test3

//---------------------------------------------------------------------------------------------------------------------------------
//                    256TB PAGE    Region 1 under test at level 4 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 4: Test in U-Mode | RX bit set | expected = Store Page fault
  SUPERPAGE_PTE_SETUP_SV57(rvtest_data_1, (PTE_D | PTE_A | PTE_U | PTE_X | PTE_R | PTE_V), va_data, LEVEL4)
  sfence.vma

  TEST_CASES_RUNNER Umode, va_data, LEVEL4, test4

//---------------------------------------------------------------------------------------------------------------------------------
//                    256TB PAGE    Region 1 under test at level 4 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 5: Test in U-Mode | RWX bit set | expected = Store Page fault
  SUPERPAGE_PTE_SETUP_SV57(rvtest_data_1, (PTE_D | PTE_A | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL4)
  sfence.vma

  TEST_CASES_RUNNER Umode, va_data, LEVEL4, test5

//---------------------------------------------------------------------------------------------------------------------------------
//                    256TB PAGE    Region 1 under test at level 4 -- RWX permission given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 6: Test in U-Mode | PTE.A unset | expected = Store Page fault
  SUPERPAGE_PTE_SETUP_SV57(rvtest_data_1, (PTE_D | PTE_U | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL4)
  sfence.vma

  TEST_CASES_RUNNER Umode, va_data, LEVEL4, test6

//---------------------------------------------------------------------------------------------------------------------------------
//                    256TB PAGE    Region 1 under test at level 4 -- RWX permission given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 7: Test in U-Mode | PTE.D unset | expected = Store Page fault
  SUPERPAGE_PTE_SETUP_SV57(rvtest_data_1, (PTE_A | PTE_U | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL4)
  sfence.vma

  TEST_CASES_RUNNER Umode, va_data, LEVEL4, test7

//---------------------------------------------------------------------------------------------------------------------------------
//                    256TB PAGE    Region 1 under test at level 4 -- RWX permission given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 8: Test in U-Mode | RWX bit set | Misaligned Terapage | expected = Store Page fault
  PTE_SETUP_SV57(rvtest_data_1, (PTE_D | PTE_A | PTE_U | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL4)
  sfence.vma

  TEST_CASES_RUNNER_2 Umode, 0x0, va_data, LEVEL4, test8

//---------------------------------------------------------------------------------------------------------------------------------
//                    256TB PAGE    Region 1 under test at level 4 -- RWX permission given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 9: Test in U-Mode | RWX bit set | expected = Store access fault
  SUPERPAGE_PTE_SETUP_SV57(RVMODEL_ACCESS_FAULT_ADDRESS, (PTE_D | PTE_A | PTE_U | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL4)
  sfence.vma

  TEST_CASES_RUNNER_2 Umode, RVMODEL_ACCESS_FAULT_ADDRESS, va_data, LEVEL4, test9


//---------------------------------------------------------------------------------------------------------------------------------
//---------------------------------------------------------------------------------------------------------------------------------
//                                                    TESTS AT LEVEL 3
//---------------------------------------------------------------------------------------------------------------------------------
//                    512GB PAGE    Region 1 under test at level 3 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 10: Test in U-Mode | V bit unset | expected = Store Page fault
  PTE_SETUP_SV57(rvtest_slvl3_pg_tbl, (PTE_V), va_data, LEVEL4)
  SUPERPAGE_PTE_SETUP_SV57(rvtest_data_1, (PTE_D | PTE_A | PTE_U | PTE_X | PTE_W | PTE_R), va_data, LEVEL3)
  sfence.vma

  TEST_CASES_RUNNER Umode, va_data, LEVEL3, test10

//---------------------------------------------------------------------------------------------------------------------------------
//                    512GB PAGE    Region 1 under test at level 3 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 11: Test in U-Mode | WX bit set | expected = Store Page fault
  PTE_SETUP_SV57(rvtest_slvl3_pg_tbl, (PTE_V), va_data, LEVEL4)
  SUPERPAGE_PTE_SETUP_SV57(rvtest_data_1, (PTE_D | PTE_A | PTE_U | PTE_X | PTE_W | PTE_V), va_data, LEVEL3)
  sfence.vma

  TEST_CASES_RUNNER Umode, va_data, LEVEL3, test11

//---------------------------------------------------------------------------------------------------------------------------------
//                    512GB PAGE    Region 1 under test at level 3 -- RWX permission given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 12: Test in U-Mode | W bit set | expected = Store Page fault
  PTE_SETUP_SV57(rvtest_slvl3_pg_tbl, (PTE_V), va_data, LEVEL4)
  SUPERPAGE_PTE_SETUP_SV57(rvtest_data_1, (PTE_D | PTE_A | PTE_U | PTE_W | PTE_V), va_data, LEVEL3)
  sfence.vma

  TEST_CASES_RUNNER Umode, va_data, LEVEL3, test12

//---------------------------------------------------------------------------------------------------------------------------------
//                    512GB PAGE    Region 1 under test at level 3 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 13: Test in U-Mode | RX bit set | expected = Store Page fault
  PTE_SETUP_SV57(rvtest_slvl3_pg_tbl, (PTE_V), va_data, LEVEL4)
  SUPERPAGE_PTE_SETUP_SV57(rvtest_data_1, (PTE_D | PTE_A | PTE_U | PTE_X | PTE_R | PTE_V), va_data, LEVEL3)
  sfence.vma

  TEST_CASES_RUNNER Umode, va_data, LEVEL3, test13

//---------------------------------------------------------------------------------------------------------------------------------
//                    512GB PAGE    Region 1 under test at level 3 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 14: Test in U-Mode | RWX bit set | expected = Store Page fault
  PTE_SETUP_SV57(rvtest_slvl3_pg_tbl, (PTE_V), va_data, LEVEL4)
  SUPERPAGE_PTE_SETUP_SV57(rvtest_data_1, (PTE_D | PTE_A | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL3)
  sfence.vma

  TEST_CASES_RUNNER Umode, va_data, LEVEL3, test14

//---------------------------------------------------------------------------------------------------------------------------------
//                    512GB PAGE    Region 1 under test at level 3 -- RWX permission given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 15: Test in U-Mode | PTE.A unset | expected = Store Page fault
  PTE_SETUP_SV57(rvtest_slvl3_pg_tbl, (PTE_V), va_data, LEVEL4)
  SUPERPAGE_PTE_SETUP_SV57(rvtest_data_1, (PTE_D | PTE_U | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL3)
  sfence.vma

  TEST_CASES_RUNNER Umode, va_data, LEVEL3, test15

//---------------------------------------------------------------------------------------------------------------------------------
//                    512GB PAGE    Region 1 under test at level 3 -- RWX permission given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 16: Test in U-Mode | PTE.D unset | expected = Store Page fault
  PTE_SETUP_SV57(rvtest_slvl3_pg_tbl, (PTE_V), va_data, LEVEL4)
  SUPERPAGE_PTE_SETUP_SV57(rvtest_data_1, (PTE_A | PTE_U | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL3)
  sfence.vma

  TEST_CASES_RUNNER Umode, va_data, LEVEL3, test16

//---------------------------------------------------------------------------------------------------------------------------------
//                    512GB PAGE    Region 1 under test at level 3 -- RWX permission given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 17: Test in U-Mode | RWX bit set | Misaligned Gigapage | expected = Store Page fault
  PTE_SETUP_SV57(rvtest_slvl3_pg_tbl, (PTE_V), va_data, LEVEL4)
  PTE_SETUP_SV57(rvtest_data_1, (PTE_D | PTE_A | PTE_U | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL3)
  sfence.vma

  TEST_CASES_RUNNER_2 Umode, 0x0, va_data, LEVEL3, test17

//---------------------------------------------------------------------------------------------------------------------------------
//                    512GB PAGE    Region 1 under test at level 3 -- RWX permission given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 18: Test in U-Mode | Incorrect PTE setup | expected = Store access fault
  PTE_SETUP_SV57(RVMODEL_ACCESS_FAULT_ADDRESS, (PTE_V), va_data, LEVEL4)
  SUPERPAGE_PTE_SETUP_SV57(rvtest_data_1, (PTE_A | PTE_D | PTE_U | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL3)
  sfence.vma

  TEST_CASES_RUNNER Umode, va_data, LEVEL3, test18

//---------------------------------------------------------------------------------------------------------------------------------
//                    512GB PAGE    Region 1 under test at level 3 -- RWX permission given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 19: Test in U-Mode | RWX bit set | expected = Store access fault
  PTE_SETUP_SV57(rvtest_slvl3_pg_tbl, (PTE_V), va_data, LEVEL4)
  SUPERPAGE_PTE_SETUP_SV57(RVMODEL_ACCESS_FAULT_ADDRESS, (PTE_D | PTE_A | PTE_U | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL3)
  sfence.vma

  TEST_CASES_RUNNER_2 Umode, RVMODEL_ACCESS_FAULT_ADDRESS, va_data, LEVEL3, test19

//---------------------------------------------------------------------------------------------------------------------------------
//                    512GB PAGE    Region 1 under test at level 3 -- RWX permission given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 20: Test in U-Mode | PTE.D set for level 2 PTE | expected = Store Page fault
  PTE_SETUP_SV57(rvtest_slvl3_pg_tbl, (PTE_D | PTE_V), va_data, LEVEL4)
  SUPERPAGE_PTE_SETUP_SV57(rvtest_data_1, (PTE_D | PTE_A | PTE_U | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL3)
  sfence.vma

  TEST_CASES_RUNNER Umode, va_data, LEVEL3, test20

//---------------------------------------------------------------------------------------------------------------------------------
//                    512GB PAGE    Region 1 under test at level 3 -- RWX permission given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 21: Test in U-Mode | PTE.A set for level 2 PTE | expected = Store Page fault
  PTE_SETUP_SV57(rvtest_slvl3_pg_tbl, (PTE_A | PTE_V), va_data, LEVEL4)
  SUPERPAGE_PTE_SETUP_SV57(rvtest_data_1, (PTE_D | PTE_A | PTE_U | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL0)
  sfence.vma

  TEST_CASES_RUNNER Umode, va_data, LEVEL3, test21

//---------------------------------------------------------------------------------------------------------------------------------
//                    512GB PAGE    Region 1 under test at level 3 -- RWX permission given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 22: Test in U-Mode | PTE.U set for level 2 PTE | expected = Store Page fault
  PTE_SETUP_SV57(rvtest_slvl3_pg_tbl, (PTE_U | PTE_V), va_data, LEVEL4)
  SUPERPAGE_PTE_SETUP_SV57(rvtest_data_1, (PTE_D | PTE_A | PTE_U | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL3)
  sfence.vma

  TEST_CASES_RUNNER Umode, va_data, LEVEL3, test22


//---------------------------------------------------------------------------------------------------------------------------------
//---------------------------------------------------------------------------------------------------------------------------------
//                                                    TESTS AT LEVEL 2
//---------------------------------------------------------------------------------------------------------------------------------
//                    1GB PAGE    Region 1 under test at level 2 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 23: Test in U-Mode | V bit unset | expected = Store Page fault
  PTE_SETUP_SV57(rvtest_slvl3_pg_tbl, (PTE_V), va_data, LEVEL4)
  PTE_SETUP_SV57(rvtest_slvl2_pg_tbl, (PTE_V), va_data, LEVEL3)
  SUPERPAGE_PTE_SETUP_SV57(rvtest_data_1, (PTE_D | PTE_A | PTE_U | PTE_X | PTE_W | PTE_R), va_data, LEVEL2)
  sfence.vma

  TEST_CASES_RUNNER Umode, va_data, LEVEL2, test23

//---------------------------------------------------------------------------------------------------------------------------------
//                    1GB PAGE    Region 1 under test at level 2 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 24: Test in U-Mode | WX bit set | expected = Store Page fault
  PTE_SETUP_SV57(rvtest_slvl3_pg_tbl, (PTE_V), va_data, LEVEL4)
  PTE_SETUP_SV57(rvtest_slvl2_pg_tbl, (PTE_V), va_data, LEVEL3)
  SUPERPAGE_PTE_SETUP_SV57(rvtest_data_1, (PTE_D | PTE_A | PTE_U | PTE_X | PTE_W | PTE_V), va_data, LEVEL2)
  sfence.vma

  TEST_CASES_RUNNER Umode, va_data, LEVEL2, test24

//---------------------------------------------------------------------------------------------------------------------------------
//                    1GB PAGE    Region 1 under test at level 2 -- RWX permission given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 25: Test in U-Mode | W bit set | expected = Store Page fault
  PTE_SETUP_SV57(rvtest_slvl3_pg_tbl, (PTE_V), va_data, LEVEL4)
  PTE_SETUP_SV57(rvtest_slvl2_pg_tbl, (PTE_V), va_data, LEVEL3)
  SUPERPAGE_PTE_SETUP_SV57(rvtest_data_1, (PTE_D | PTE_A | PTE_U | PTE_W | PTE_V), va_data, LEVEL2)
  sfence.vma

  TEST_CASES_RUNNER Umode, va_data, LEVEL2, test25

//---------------------------------------------------------------------------------------------------------------------------------
//                    1GB PAGE    Region 1 under test at level 2 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 26: Test in U-Mode | RX bit set | expected = Store Page fault
  PTE_SETUP_SV57(rvtest_slvl3_pg_tbl, (PTE_V), va_data, LEVEL4)
  PTE_SETUP_SV57(rvtest_slvl2_pg_tbl, (PTE_V), va_data, LEVEL3)
  SUPERPAGE_PTE_SETUP_SV57(rvtest_data_1, (PTE_D | PTE_A | PTE_U | PTE_X | PTE_R | PTE_V), va_data, LEVEL2)
  sfence.vma

  TEST_CASES_RUNNER Umode, va_data, LEVEL2, test26

//---------------------------------------------------------------------------------------------------------------------------------
//                    1GB PAGE    Region 1 under test at level 2 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 27: Test in U-Mode | RWX bit set | expected = Store Page fault
  PTE_SETUP_SV57(rvtest_slvl3_pg_tbl, (PTE_V), va_data, LEVEL4)
  PTE_SETUP_SV57(rvtest_slvl2_pg_tbl, (PTE_V), va_data, LEVEL3)
  SUPERPAGE_PTE_SETUP_SV57(rvtest_data_1, (PTE_D | PTE_A | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL2)
  sfence.vma

  TEST_CASES_RUNNER Umode, va_data, LEVEL2, test27

//---------------------------------------------------------------------------------------------------------------------------------
//                    1GB PAGE    Region 1 under test at level 2 -- RWX permission given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 28: Test in U-Mode | PTE.A unset | expected = Store Page fault
  PTE_SETUP_SV57(rvtest_slvl3_pg_tbl, (PTE_V), va_data, LEVEL4)
  PTE_SETUP_SV57(rvtest_slvl2_pg_tbl, (PTE_V), va_data, LEVEL3)
  SUPERPAGE_PTE_SETUP_SV57(rvtest_data_1, (PTE_D | PTE_U | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL2)
  sfence.vma

  TEST_CASES_RUNNER Umode, va_data, LEVEL2, test28

//---------------------------------------------------------------------------------------------------------------------------------
//                    1GB PAGE    Region 1 under test at level 2 -- RWX permission given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 29: Test in U-Mode | PTE.D unset | expected = Store Page fault
  PTE_SETUP_SV57(rvtest_slvl3_pg_tbl, (PTE_V), va_data, LEVEL4)
  PTE_SETUP_SV57(rvtest_slvl2_pg_tbl, (PTE_V), va_data, LEVEL3)
  SUPERPAGE_PTE_SETUP_SV57(rvtest_data_1, (PTE_A | PTE_U | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL2)
  sfence.vma

  TEST_CASES_RUNNER Umode, va_data, LEVEL2, test29

//---------------------------------------------------------------------------------------------------------------------------------
//                    1GB PAGE    Region 1 under test at level 2 -- RWX permission given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 30: Test in U-Mode | RWX bit set | Misaligned Gigapage | expected = Store Page fault
  PTE_SETUP_SV57(rvtest_slvl3_pg_tbl, (PTE_V), va_data, LEVEL4)
  PTE_SETUP_SV57(rvtest_slvl2_pg_tbl, (PTE_V), va_data, LEVEL3)
  PTE_SETUP_SV57(rvtest_data_1, (PTE_D | PTE_A | PTE_U | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL2)
  sfence.vma

  TEST_CASES_RUNNER_2 Umode, 0x0, va_data, LEVEL2, test30

//---------------------------------------------------------------------------------------------------------------------------------
//                    1GB PAGE    Region 1 under test at level 2 -- RWX permission given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 31: Test in U-Mode | Incorrect PTE setup | expected = Store access fault
  PTE_SETUP_SV57(rvtest_slvl3_pg_tbl, (PTE_V), va_data, LEVEL4)
  PTE_SETUP_SV57(RVMODEL_ACCESS_FAULT_ADDRESS, (PTE_V), va_data, LEVEL3)
  SUPERPAGE_PTE_SETUP_SV57(rvtest_data_1, (PTE_A | PTE_D | PTE_U | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL2)
  sfence.vma

  TEST_CASES_RUNNER Umode, va_data, LEVEL2, test31

//---------------------------------------------------------------------------------------------------------------------------------
//                    1GB PAGE    Region 1 under test at level 2 -- RWX permission given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 32: Test in U-Mode | RWX bit set | expected = Store access fault
  PTE_SETUP_SV57(rvtest_slvl3_pg_tbl, (PTE_V), va_data, LEVEL4)
  PTE_SETUP_SV57(rvtest_slvl2_pg_tbl, (PTE_V), va_data, LEVEL3)
  SUPERPAGE_PTE_SETUP_SV57(RVMODEL_ACCESS_FAULT_ADDRESS, (PTE_D | PTE_A | PTE_U | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL2)
  sfence.vma

  TEST_CASES_RUNNER_2 Umode, RVMODEL_ACCESS_FAULT_ADDRESS, va_data, LEVEL2, test32

//---------------------------------------------------------------------------------------------------------------------------------
//                    1GB PAGE    Region 1 under test at level 2 -- RWX permission given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 33: Test in U-Mode | PTE.D set for level 2 PTE | expected = Store Page fault
  PTE_SETUP_SV57(rvtest_slvl3_pg_tbl, (PTE_V), va_data, LEVEL4)
  PTE_SETUP_SV57(rvtest_slvl2_pg_tbl, (PTE_D | PTE_V), va_data, LEVEL3)
  SUPERPAGE_PTE_SETUP_SV57(rvtest_data_1, (PTE_D | PTE_A | PTE_U | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL2)
  sfence.vma

  TEST_CASES_RUNNER Umode, va_data, LEVEL2, test33

//---------------------------------------------------------------------------------------------------------------------------------
//                    1GB PAGE    Region 1 under test at level 2 -- RWX permission given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 34: Test in U-Mode | PTE.A set for level 2 PTE | expected = Store Page fault
  PTE_SETUP_SV57(rvtest_slvl3_pg_tbl, (PTE_V), va_data, LEVEL4)
  PTE_SETUP_SV57(rvtest_slvl2_pg_tbl, (PTE_A | PTE_V), va_data, LEVEL3)
  SUPERPAGE_PTE_SETUP_SV57(rvtest_data_1, (PTE_D | PTE_A | PTE_U | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL0)
  sfence.vma

  TEST_CASES_RUNNER Umode, va_data, LEVEL2, test34

//---------------------------------------------------------------------------------------------------------------------------------
//                    1GB PAGE    Region 1 under test at level 2 -- RWX permission given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 35: Test in U-Mode | PTE.U set for level 2 PTE | expected = Store Page fault
  PTE_SETUP_SV57(rvtest_slvl3_pg_tbl, (PTE_V), va_data, LEVEL4)
  PTE_SETUP_SV57(rvtest_slvl2_pg_tbl, (PTE_U | PTE_V), va_data, LEVEL3)
  SUPERPAGE_PTE_SETUP_SV57(rvtest_data_1, (PTE_D | PTE_A | PTE_U | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL2)
  sfence.vma

  TEST_CASES_RUNNER Umode, va_data, LEVEL2, test35


//---------------------------------------------------------------------------------------------------------------------------------
//---------------------------------------------------------------------------------------------------------------------------------
//                                                    TESTS AT LEVEL 1
//---------------------------------------------------------------------------------------------------------------------------------
//                    2MB PAGE    Region 1 under test at level 1 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 36: Test in U-Mode | V bit unset | expected = Store Page fault
  PTE_SETUP_SV57(rvtest_slvl3_pg_tbl, (PTE_V), va_data, LEVEL4)
  PTE_SETUP_SV57(rvtest_slvl2_pg_tbl, (PTE_V), va_data, LEVEL3)
  PTE_SETUP_SV57(rvtest_slvl1_pg_tbl, (PTE_V), va_data, LEVEL2)
  SUPERPAGE_PTE_SETUP_SV57(rvtest_data_1, (PTE_D | PTE_A | PTE_U | PTE_X | PTE_W | PTE_R), va_data, LEVEL1)
  sfence.vma

  TEST_CASES_RUNNER Umode, va_data, LEVEL1, test36

//---------------------------------------------------------------------------------------------------------------------------------
//                    2MB PAGE    Region 1 under test at level 1 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 37: Test in U-Mode | WX bit set | expected = Store Page fault
  PTE_SETUP_SV57(rvtest_slvl3_pg_tbl, (PTE_V), va_data, LEVEL4)
  PTE_SETUP_SV57(rvtest_slvl2_pg_tbl, (PTE_V), va_data, LEVEL3)
  PTE_SETUP_SV57(rvtest_slvl1_pg_tbl, (PTE_V), va_data, LEVEL2)
  SUPERPAGE_PTE_SETUP_SV57(rvtest_data_1, (PTE_D | PTE_A | PTE_U | PTE_X | PTE_W | PTE_V), va_data, LEVEL1)
  sfence.vma

  TEST_CASES_RUNNER Umode, va_data, LEVEL1, test37

//---------------------------------------------------------------------------------------------------------------------------------
//                    2MB PAGE    Region 1 under test at level 1 -- RWX permission given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 38: Test in U-Mode | W bit set | expected = Store Page fault
  PTE_SETUP_SV57(rvtest_slvl3_pg_tbl, (PTE_V), va_data, LEVEL4)
  PTE_SETUP_SV57(rvtest_slvl2_pg_tbl, (PTE_V), va_data, LEVEL3)
  PTE_SETUP_SV57(rvtest_slvl1_pg_tbl, (PTE_V), va_data, LEVEL2)
  SUPERPAGE_PTE_SETUP_SV57(rvtest_data_1, (PTE_D | PTE_A | PTE_U | PTE_W | PTE_V), va_data, LEVEL1)
  sfence.vma

  TEST_CASES_RUNNER Umode, va_data, LEVEL1, test38

//---------------------------------------------------------------------------------------------------------------------------------
//                    2MB PAGE    Region 1 under test at level 1 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 39: Test in U-Mode | RX bit set | expected = Store Page fault
  PTE_SETUP_SV57(rvtest_slvl3_pg_tbl, (PTE_V), va_data, LEVEL4)
  PTE_SETUP_SV57(rvtest_slvl2_pg_tbl, (PTE_V), va_data, LEVEL3)
  PTE_SETUP_SV57(rvtest_slvl1_pg_tbl, (PTE_V), va_data, LEVEL2)
  SUPERPAGE_PTE_SETUP_SV57(rvtest_data_1, (PTE_D | PTE_A | PTE_U | PTE_X | PTE_R | PTE_V), va_data, LEVEL1)
  sfence.vma

  TEST_CASES_RUNNER Umode, va_data, LEVEL1, test39

//---------------------------------------------------------------------------------------------------------------------------------
//                    2MB PAGE    Region 1 under test at level 1 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 40: Test in U-Mode | RWX bit set | expected = Store Page fault
  PTE_SETUP_SV57(rvtest_slvl3_pg_tbl, (PTE_V), va_data, LEVEL4)
  PTE_SETUP_SV57(rvtest_slvl2_pg_tbl, (PTE_V), va_data, LEVEL3)
  PTE_SETUP_SV57(rvtest_slvl1_pg_tbl, (PTE_V), va_data, LEVEL2)
  SUPERPAGE_PTE_SETUP_SV57(rvtest_data_1, (PTE_D | PTE_A | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL1)
  sfence.vma

  TEST_CASES_RUNNER Umode, va_data, LEVEL1, test40

//---------------------------------------------------------------------------------------------------------------------------------
//                    2MB PAGE    Region 1 under test at level 1 -- RWX permission given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 41: Test in U-Mode | PTE.A unset | expected = Store Page fault
  PTE_SETUP_SV57(rvtest_slvl3_pg_tbl, (PTE_V), va_data, LEVEL4)
  PTE_SETUP_SV57(rvtest_slvl2_pg_tbl, (PTE_V), va_data, LEVEL3)
  PTE_SETUP_SV57(rvtest_slvl1_pg_tbl, (PTE_V), va_data, LEVEL2)
  SUPERPAGE_PTE_SETUP_SV57(rvtest_data_1, (PTE_D | PTE_U | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL1)
  sfence.vma

  TEST_CASES_RUNNER Umode, va_data, LEVEL1, test41

//---------------------------------------------------------------------------------------------------------------------------------
//                    2MB PAGE    Region 1 under test at level 1 -- RWX permission given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 42: Test in U-Mode | PTE.D unset | expected = Store Page fault
  PTE_SETUP_SV57(rvtest_slvl3_pg_tbl, (PTE_V), va_data, LEVEL4)
  PTE_SETUP_SV57(rvtest_slvl2_pg_tbl, (PTE_V), va_data, LEVEL3)
  PTE_SETUP_SV57(rvtest_slvl1_pg_tbl, (PTE_V), va_data, LEVEL2)
  SUPERPAGE_PTE_SETUP_SV57(rvtest_data_1, (PTE_A | PTE_U | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL1)
  sfence.vma

  TEST_CASES_RUNNER Umode, va_data, LEVEL1, test42

//---------------------------------------------------------------------------------------------------------------------------------
//                    2MB PAGE    Region 1 under test at level 1 -- RWX permission given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 43: Test in U-Mode | RWX bit set | Misaligned Megapage | expected = Store Page fault
  PTE_SETUP_SV57(rvtest_slvl3_pg_tbl, (PTE_V), va_data, LEVEL4)
  PTE_SETUP_SV57(rvtest_slvl2_pg_tbl, (PTE_V), va_data, LEVEL3)
  PTE_SETUP_SV57(rvtest_slvl1_pg_tbl, (PTE_V), va_data, LEVEL2)
  PTE_SETUP_SV57(rvtest_data_1, (PTE_D | PTE_A | PTE_U | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL1)
  sfence.vma

  TEST_CASES_RUNNER_2 Umode, 0x0, va_data, LEVEL1, test43

//---------------------------------------------------------------------------------------------------------------------------------
//                    2MB PAGE    Region 1 under test at level 1 -- RWX permission given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 44: Test in U-Mode | Incorrect PTE setup | expected = Store access fault
  PTE_SETUP_SV57(rvtest_slvl3_pg_tbl, (PTE_V), va_data, LEVEL4)
  PTE_SETUP_SV57(rvtest_slvl2_pg_tbl, (PTE_V), va_data, LEVEL3)
  PTE_SETUP_SV57(RVMODEL_ACCESS_FAULT_ADDRESS, (PTE_V), va_data, LEVEL2)
  SUPERPAGE_PTE_SETUP_SV57(rvtest_data_1, (PTE_A | PTE_D | PTE_U | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL1)
  sfence.vma

  TEST_CASES_RUNNER Umode, va_data, LEVEL1, test44

//---------------------------------------------------------------------------------------------------------------------------------
//                    2MB PAGE    Region 1 under test at level 1 -- RWX permission given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 45: Test in U-Mode | RWX bit set | expected = Store access fault
  PTE_SETUP_SV57(rvtest_slvl3_pg_tbl, (PTE_V), va_data, LEVEL4)
  PTE_SETUP_SV57(rvtest_slvl2_pg_tbl, (PTE_V), va_data, LEVEL3)
  PTE_SETUP_SV57(rvtest_slvl1_pg_tbl, (PTE_V), va_data, LEVEL2)
  SUPERPAGE_PTE_SETUP_SV57(RVMODEL_ACCESS_FAULT_ADDRESS, (PTE_D | PTE_A | PTE_U | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL1)
  sfence.vma

  TEST_CASES_RUNNER_2 Umode, RVMODEL_ACCESS_FAULT_ADDRESS, va_data, LEVEL1, test45

//---------------------------------------------------------------------------------------------------------------------------------
//                    2MB PAGE    Region 1 under test at level 1 -- RWX permission given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 46: Test in U-Mode | PTE.D set for level 2 PTE | expected = Store Page fault
  PTE_SETUP_SV57(rvtest_slvl3_pg_tbl, (PTE_V), va_data, LEVEL4)
  PTE_SETUP_SV57(rvtest_slvl2_pg_tbl, (PTE_V), va_data, LEVEL3)
  PTE_SETUP_SV57(rvtest_slvl1_pg_tbl, (PTE_D | PTE_V), va_data, LEVEL2)
  SUPERPAGE_PTE_SETUP_SV57(rvtest_data_1, (PTE_D | PTE_A | PTE_U | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL1)
  sfence.vma

  TEST_CASES_RUNNER Umode, va_data, LEVEL1, test46

//---------------------------------------------------------------------------------------------------------------------------------
//                    2MB PAGE    Region 1 under test at level 1 -- RWX permission given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 47: Test in U-Mode | PTE.A set for level 2 PTE | expected = Store Page fault
  PTE_SETUP_SV57(rvtest_slvl3_pg_tbl, (PTE_V), va_data, LEVEL4)
  PTE_SETUP_SV57(rvtest_slvl2_pg_tbl, (PTE_V), va_data, LEVEL3)
  PTE_SETUP_SV57(rvtest_slvl1_pg_tbl, (PTE_A | PTE_V), va_data, LEVEL2)
  SUPERPAGE_PTE_SETUP_SV57(rvtest_data_1, (PTE_D | PTE_A | PTE_U | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL0)
  sfence.vma

  TEST_CASES_RUNNER Umode, va_data, LEVEL1, test47

//---------------------------------------------------------------------------------------------------------------------------------
//                    2MB PAGE    Region 1 under test at level 1 -- RWX permission given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 48: Test in U-Mode | PTE.U set for level 2 PTE | expected = Store Page fault
  PTE_SETUP_SV57(rvtest_slvl3_pg_tbl, (PTE_V), va_data, LEVEL4)
  PTE_SETUP_SV57(rvtest_slvl2_pg_tbl, (PTE_V), va_data, LEVEL3)
  PTE_SETUP_SV57(rvtest_slvl1_pg_tbl, (PTE_U | PTE_V), va_data, LEVEL2)
  SUPERPAGE_PTE_SETUP_SV57(rvtest_data_1, (PTE_D | PTE_A | PTE_U | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL1)
  sfence.vma

  TEST_CASES_RUNNER Umode, va_data, LEVEL1, test48


//---------------------------------------------------------------------------------------------------------------------------------
//---------------------------------------------------------------------------------------------------------------------------------
//                                                    TESTS AT LEVEL 0
//---------------------------------------------------------------------------------------------------------------------------------
//                    4KB PAGE    Region 1 under test at level 0 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 49: Test in U-Mode | V bit unset | expected = Store Page fault
  PTE_SETUP_SV57(rvtest_slvl3_pg_tbl, (PTE_V), va_data, LEVEL4)
  PTE_SETUP_SV57(rvtest_slvl2_pg_tbl, (PTE_V), va_data, LEVEL3)
  PTE_SETUP_SV57(rvtest_slvl1_pg_tbl, (PTE_V), va_data, LEVEL2)
  PTE_SETUP_SV57(rvtest_slvl0_pg_tbl, (PTE_V), va_data, LEVEL1)
  PTE_SETUP_SV57(rvtest_data_1, (PTE_D | PTE_A | PTE_U | PTE_X | PTE_W | PTE_R), va_data, LEVEL0)
  sfence.vma

  TEST_CASES_RUNNER Umode, va_data, LEVEL0, test49

//---------------------------------------------------------------------------------------------------------------------------------
//                    4KB PAGE    Region 1 under test at level 0 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 50: Test in U-Mode | WX bit set | expected = Store Page fault
  PTE_SETUP_SV57(rvtest_slvl3_pg_tbl, (PTE_V), va_data, LEVEL4)
  PTE_SETUP_SV57(rvtest_slvl2_pg_tbl, (PTE_V), va_data, LEVEL3)
  PTE_SETUP_SV57(rvtest_slvl1_pg_tbl, (PTE_V), va_data, LEVEL2)
  PTE_SETUP_SV57(rvtest_slvl0_pg_tbl, (PTE_V), va_data, LEVEL1)
  PTE_SETUP_SV57(rvtest_data_1, (PTE_D | PTE_A | PTE_U | PTE_X | PTE_W | PTE_V), va_data, LEVEL0)
  sfence.vma

  TEST_CASES_RUNNER Umode, va_data, LEVEL0, test50

//---------------------------------------------------------------------------------------------------------------------------------
//                    4KB PAGE    Region 1 under test at level 0 -- RWX permission given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 51: Test in U-Mode | W bit set | expected = Store Page fault
  PTE_SETUP_SV57(rvtest_slvl3_pg_tbl, (PTE_V), va_data, LEVEL4)
  PTE_SETUP_SV57(rvtest_slvl2_pg_tbl, (PTE_V), va_data, LEVEL3)
  PTE_SETUP_SV57(rvtest_slvl1_pg_tbl, (PTE_V), va_data, LEVEL2)
  PTE_SETUP_SV57(rvtest_slvl0_pg_tbl, (PTE_V), va_data, LEVEL1)
  PTE_SETUP_SV57(rvtest_data_1, (PTE_D | PTE_A | PTE_U | PTE_W | PTE_V), va_data, LEVEL0)
  sfence.vma

  TEST_CASES_RUNNER Umode, va_data, LEVEL0, test51

//---------------------------------------------------------------------------------------------------------------------------------
//                    4KB PAGE    Region 1 under test at level 0 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 52: Test in U-Mode | RX bit set | expected = Store Page fault
  PTE_SETUP_SV57(rvtest_slvl3_pg_tbl, (PTE_V), va_data, LEVEL4)
  PTE_SETUP_SV57(rvtest_slvl2_pg_tbl, (PTE_V), va_data, LEVEL3)
  PTE_SETUP_SV57(rvtest_slvl1_pg_tbl, (PTE_V), va_data, LEVEL2)
  PTE_SETUP_SV57(rvtest_slvl0_pg_tbl, (PTE_V), va_data, LEVEL1)
  PTE_SETUP_SV57(rvtest_data_1, (PTE_D | PTE_A | PTE_U | PTE_X | PTE_R | PTE_V), va_data, LEVEL0)
  sfence.vma

  TEST_CASES_RUNNER Umode, va_data, LEVEL0, test52

//---------------------------------------------------------------------------------------------------------------------------------
//                    4KB PAGE    Region 1 under test at level 0 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 53: Test in U-Mode | RWX bit set | expected = Store Page fault
  PTE_SETUP_SV57(rvtest_slvl3_pg_tbl, (PTE_V), va_data, LEVEL4)
  PTE_SETUP_SV57(rvtest_slvl2_pg_tbl, (PTE_V), va_data, LEVEL3)
  PTE_SETUP_SV57(rvtest_slvl1_pg_tbl, (PTE_V), va_data, LEVEL2)
  PTE_SETUP_SV57(rvtest_slvl0_pg_tbl, (PTE_V), va_data, LEVEL1)
  PTE_SETUP_SV57(rvtest_data_1, (PTE_D | PTE_A | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL0)
  sfence.vma

  TEST_CASES_RUNNER Umode, va_data, LEVEL0, test53

//---------------------------------------------------------------------------------------------------------------------------------
//                    4KB PAGE    Region 1 under test at level 0 -- RWX permission given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 54: Test in U-Mode | PTE.A unset | expected = Store Page fault
  PTE_SETUP_SV57(rvtest_slvl3_pg_tbl, (PTE_V), va_data, LEVEL4)
  PTE_SETUP_SV57(rvtest_slvl2_pg_tbl, (PTE_V), va_data, LEVEL3)
  PTE_SETUP_SV57(rvtest_slvl1_pg_tbl, (PTE_V), va_data, LEVEL2)
  PTE_SETUP_SV57(rvtest_slvl0_pg_tbl, (PTE_V), va_data, LEVEL1)
  PTE_SETUP_SV57(rvtest_data_1, (PTE_D | PTE_U | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL0)
  sfence.vma

  TEST_CASES_RUNNER Umode, va_data, LEVEL0, test54

//---------------------------------------------------------------------------------------------------------------------------------
//                    4KB PAGE    Region 1 under test at level 0 -- RWX permission given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 55: Test in U-Mode | PTE.D unset | expected = Store Page fault
  PTE_SETUP_SV57(rvtest_slvl3_pg_tbl, (PTE_V), va_data, LEVEL4)
  PTE_SETUP_SV57(rvtest_slvl2_pg_tbl, (PTE_V), va_data, LEVEL3)
  PTE_SETUP_SV57(rvtest_slvl1_pg_tbl, (PTE_V), va_data, LEVEL2)
  PTE_SETUP_SV57(rvtest_slvl0_pg_tbl, (PTE_V), va_data, LEVEL1)
  PTE_SETUP_SV57(rvtest_data_1, (PTE_A | PTE_U | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL0)
  sfence.vma

  TEST_CASES_RUNNER Umode, va_data, LEVEL0, test55

//---------------------------------------------------------------------------------------------------------------------------------
//                    4KB PAGE    Region 1 under test at level 0 -- RWX permission given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 56: Test in U-Mode | Only V & U bit set at Level 0 | expected = Store Page fault
  PTE_SETUP_SV57(rvtest_slvl3_pg_tbl, (PTE_V), va_data, LEVEL4)
  PTE_SETUP_SV57(rvtest_slvl2_pg_tbl, (PTE_V), va_data, LEVEL3)
  PTE_SETUP_SV57(rvtest_slvl1_pg_tbl, (PTE_V), va_data, LEVEL2)
  PTE_SETUP_SV57(rvtest_slvl0_pg_tbl, (PTE_V), va_data, LEVEL1)
  PTE_SETUP_SV57(rvtest_data_1, (PTE_U | PTE_V), va_data, LEVEL0)
  sfence.vma

  TEST_CASES_RUNNER Umode, va_data, LEVEL0, test56

//---------------------------------------------------------------------------------------------------------------------------------
//                    4KB PAGE    Region 1 under test at level 0 -- RWX permission given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 57: Test in U-Mode | Incorrect PTE setup | expected = Store access fault
  PTE_SETUP_SV57(rvtest_slvl3_pg_tbl, (PTE_V), va_data, LEVEL4)
  PTE_SETUP_SV57(rvtest_slvl2_pg_tbl, (PTE_V), va_data, LEVEL3)
  PTE_SETUP_SV57(rvtest_slvl1_pg_tbl, (PTE_V), va_data, LEVEL2)
  PTE_SETUP_SV57(RVMODEL_ACCESS_FAULT_ADDRESS, (PTE_V), va_data, LEVEL1)
  PTE_SETUP_SV57(rvtest_data_1, (PTE_D | PTE_A | PTE_U | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL0)
  sfence.vma

  TEST_CASES_RUNNER_2 Umode, RVMODEL_ACCESS_FAULT_ADDRESS, va_data, LEVEL0, test57

//---------------------------------------------------------------------------------------------------------------------------------
//                    4KB PAGE    Region 1 under test at level 0 -- RWX permission given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 58: Test in U-Mode | RWX bit set | expected = Store access fault
  PTE_SETUP_SV57(rvtest_slvl3_pg_tbl, (PTE_V), va_data, LEVEL4)
  PTE_SETUP_SV57(rvtest_slvl2_pg_tbl, (PTE_V), va_data, LEVEL3)
  PTE_SETUP_SV57(rvtest_slvl1_pg_tbl, (PTE_V), va_data, LEVEL2)
  PTE_SETUP_SV57(rvtest_slvl0_pg_tbl, (PTE_V), va_data, LEVEL1)
  PTE_SETUP_SV57(RVMODEL_ACCESS_FAULT_ADDRESS, (PTE_D | PTE_A | PTE_U | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL0)
  sfence.vma

  TEST_CASES_RUNNER_2 Umode, RVMODEL_ACCESS_FAULT_ADDRESS, va_data, LEVEL0, test58

//---------------------------------------------------------------------------------------------------------------------------------
//                    4KB PAGE    Region 1 under test at level 0 -- RWX permission given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 59: Test in U-Mode | PTE.D set for level 1 PTE | expected = Store Page fault
  PTE_SETUP_SV57(rvtest_slvl3_pg_tbl, (PTE_V), va_data, LEVEL4)
  PTE_SETUP_SV57(rvtest_slvl2_pg_tbl, (PTE_V), va_data, LEVEL3)
  PTE_SETUP_SV57(rvtest_slvl1_pg_tbl, (PTE_V), va_data, LEVEL2)
  PTE_SETUP_SV57(rvtest_slvl0_pg_tbl, (PTE_D | PTE_V), va_data, LEVEL1)
  PTE_SETUP_SV57(rvtest_data_1, (PTE_D | PTE_A | PTE_U | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL0)
  sfence.vma

  TEST_CASES_RUNNER Umode, va_data, LEVEL0, test59

//---------------------------------------------------------------------------------------------------------------------------------
//                    4KB PAGE    Region 1 under test at level 0 -- RWX permission given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 60: Test in U-Mode | PTE.A set for level 1 PTE | expected = Store Page fault
  PTE_SETUP_SV57(rvtest_slvl3_pg_tbl, (PTE_V), va_data, LEVEL4)
  PTE_SETUP_SV57(rvtest_slvl2_pg_tbl, (PTE_V), va_data, LEVEL3)
  PTE_SETUP_SV57(rvtest_slvl1_pg_tbl, (PTE_V), va_data, LEVEL2)
  PTE_SETUP_SV57(rvtest_slvl0_pg_tbl, (PTE_A | PTE_V), va_data, LEVEL1)
  PTE_SETUP_SV57(rvtest_data_1, (PTE_D | PTE_A | PTE_U | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL0)
  sfence.vma

  TEST_CASES_RUNNER Umode, va_data, LEVEL0, test60

//---------------------------------------------------------------------------------------------------------------------------------
//                    4KB PAGE    Region 1 under test at level 0 -- RWX permission given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 61: Test in U-Mode | PTE.U set for level 1 PTE | expected = Store Page fault
  PTE_SETUP_SV57(rvtest_slvl3_pg_tbl, (PTE_V), va_data, LEVEL4)
  PTE_SETUP_SV57(rvtest_slvl2_pg_tbl, (PTE_V), va_data, LEVEL3)
  PTE_SETUP_SV57(rvtest_slvl1_pg_tbl, (PTE_V), va_data, LEVEL2)
  PTE_SETUP_SV57(rvtest_slvl0_pg_tbl, (PTE_U | PTE_V), va_data, LEVEL1)
  PTE_SETUP_SV57(rvtest_data_1, (PTE_D | PTE_A | PTE_U | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL0)
  sfence.vma

  TEST_CASES_RUNNER Umode, va_data, LEVEL0, test61


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
test39_str:  .string "\"Mismatch during cbo.zero in Test Case 39!\""
test40_str:  .string "\"Mismatch during cbo.zero in Test Case 40!\""
test41_str:  .string "\"Mismatch during cbo.zero in Test Case 41!\""
test42_str:  .string "\"Mismatch during cbo.zero in Test Case 42!\""
test43_str:  .string "\"Mismatch during cbo.zero in Test Case 43!\""
test44_str:  .string "\"Mismatch during cbo.zero in Test Case 44!\""
test45_str:  .string "\"Mismatch during cbo.zero in Test Case 45!\""
test46_str:  .string "\"Mismatch during cbo.zero in Test Case 46!\""
test47_str:  .string "\"Mismatch during cbo.zero in Test Case 47!\""
test48_str:  .string "\"Mismatch during cbo.zero in Test Case 48!\""
test49_str:  .string "\"Mismatch during cbo.zero in Test Case 49!\""
test50_str:  .string "\"Mismatch during cbo.zero in Test Case 50!\""
test51_str:  .string "\"Mismatch during cbo.zero in Test Case 51!\""
test52_str:  .string "\"Mismatch during cbo.zero in Test Case 52!\""
test53_str:  .string "\"Mismatch during cbo.zero in Test Case 53!\""
test54_str:  .string "\"Mismatch during cbo.zero in Test Case 54!\""
test55_str:  .string "\"Mismatch during cbo.zero in Test Case 55!\""
test56_str:  .string "\"Mismatch during cbo.zero in Test Case 56!\""
test57_str:  .string "\"Mismatch during cbo.zero in Test Case 57!\""
test58_str:  .string "\"Mismatch during cbo.zero in Test Case 58!\""
test59_str:  .string "\"Mismatch during cbo.zero in Test Case 59!\""
test60_str:  .string "\"Mismatch during cbo.zero in Test Case 60!\""
test61_str:  .string "\"Mismatch during cbo.zero in Test Case 61!\""

RVTEST_DATA_END
RVTEST_SIG_SETUP
