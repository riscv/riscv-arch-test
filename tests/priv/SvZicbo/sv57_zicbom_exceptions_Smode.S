// --------------------------------------------------------------------------------------------------------------------------------
// Developed by: Umer Shahid & Muhammad Zain
// --------------------------------------------------------------------------------------------------------------------------------
// Test cases are as follows:
// --------------------------------------------------------------------------------------------------------------------------------
// 1. At level 4, setup a PTE with V=0
//      → In S-Mode, execute cbo.clean, cbo.flush and cbo.inval. Expected: 3 Store Page faults
// 2. At level 4, setup a PTE with reserved encoding R=0, W=1 & X=1
//      → In S-Mode, execute cbo.clean, cbo.flush and cbo.inval. Expected: 3 Store Page faults
// 3. At level 4, setup a PTE with reserved encoding R=0, W=1 & X=0
//      → In S-Mode, execute cbo.clean, cbo.flush and cbo.inval. Expected: 3 Store Page faults
// 4. At level 4, setup a PTE with RX permissions
//      → In S-Mode, execute cbo.clean, cbo.flush and cbo.inval. Expected: No fault
// 5. At level 4, setup a PTE with RX permissions and set mstatus.SUM
//      → In S-Mode, execute cbo.clean, cbo.flush and cbo.inval. Expected: No fault
// 6. At level 4, setup a PTE with RWX & U permissions
//      → In S-Mode, execute cbo.clean, cbo.flush and cbo.inval. Expected: 3 Store page faults
// 7. At level 4, setup a PTE with X permission only
//      → In S-Mode, execute cbo.clean, cbo.flush and cbo.inval. Expected: 3 Store Page faults
// 8. At level 4, setup a PTE with RWX permissions and A bit unset
//      → In S-Mode, execute cbo.clean, cbo.flush and cbo.inval. Expected: 3 Store page faults
// 9. At level 4, setup a PTE with RWX permissions and D bit unset
//      → In S-Mode, execute cbo.clean, cbo.flush and cbo.inval. Expected: No fault
// 10. At level 4, setup a misaligned petapage
//      → In S-Mode, execute cbo.clean, cbo.flush and cbo.inval. Expected: 3 Store page faults
// 11. At level 4, setup a PTE with RWX permissions that points to RVMODEL_ACCESS_FAULT_ADDRESS
//      → In S-Mode, execute cbo.clean, cbo.flush and cbo.inval. Expected: 3 Store access faults
//
// 12. At level 3, setup a PTE with V=0
//      → In S-Mode, execute cbo.clean, cbo.flush and cbo.inval. Expected: 3 Store Page faults
// 13. At level 3, setup a PTE with reserved encoding R=0, W=1 & X=1
//      → In S-Mode, execute cbo.clean, cbo.flush and cbo.inval. Expected: 3 Store Page faults
// 14. At level 3, setup a PTE with reserved encoding R=0, W=1 & X=0
//      → In S-Mode, execute cbo.clean, cbo.flush and cbo.inval. Expected: 3 Store Page faults
// 15. At level 3, setup a PTE with RX permissions
//      → In S-Mode, execute cbo.clean, cbo.flush and cbo.inval. Expected: No fault
// 16. At level 3, setup a PTE with RX permissions and set mstatus.SUM
//      → In S-Mode, execute cbo.clean, cbo.flush and cbo.inval. Expected: No fault
// 17. At level 3, setup a PTE with RWX & U permissions
//      → In S-Mode, execute cbo.clean, cbo.flush and cbo.inval. Expected: 3 Store page faults
// 18. At level 3, setup a PTE with X permission only
//      → In S-Mode, execute cbo.clean, cbo.flush and cbo.inval. Expected: 3 Store Page faults
// 19. At level 3, setup a PTE with RWX permissions and A bit unset
//      → In S-Mode, execute cbo.clean, cbo.flush and cbo.inval. Expected: 3 Store page faults
// 20. At level 3, setup a PTE with RWX permissions and D bit unset
//      → In S-Mode, execute cbo.clean, cbo.flush and cbo.inval. Expected: No fault
// 21. At level 3, setup a misaligned terapage
//      → In S-Mode, execute cbo.clean, cbo.flush and cbo.inval. Expected: 3 Store page faults
// 22. At level 3, setup a PTE with non leaf (lvl 4) PTE pointing to RVMODEL_ACCESS_FAULT_ADDRESS instead of next page table
//      → In S-Mode, execute cbo.clean, cbo.flush and cbo.inval. Expected: 3 Store access faults
// 23. At level 3, setup a PTE with RWX permissions that points to RVMODEL_ACCESS_FAULT_ADDRESS
//      → In S-Mode, execute cbo.clean, cbo.flush and cbo.inval. Expected: 3 Store access faults
// 24. At level 3, setup a PTE with non leaf (lvl 4) PTE.D set
//      → In S-Mode, execute cbo.clean, cbo.flush and cbo.inval. Expected: 3 Store page faults
// 25. At level 3, setup a PTE with non leaf (lvl 4) PTE.A set
//      → In S-Mode, execute cbo.clean, cbo.flush and cbo.inval. Expected: 3 Store page faults
// 26. At level 3, setup a PTE with non leaf (lvl 4) PTE.U set
//      → In S-Mode, execute cbo.clean, cbo.flush and cbo.inval. Expected: 3 Store page faults
//
// 27. At level 2, setup a PTE with V=0
//      → In S-Mode, execute cbo.clean, cbo.flush and cbo.inval. Expected: 3 Store Page faults
// 28. At level 2, setup a PTE with reserved encoding R=0, W=1 & X=1
//      → In S-Mode, execute cbo.clean, cbo.flush and cbo.inval. Expected: 3 Store Page faults
// 29. At level 2, setup a PTE with reserved encoding R=0, W=1 & X=0
//      → In S-Mode, execute cbo.clean, cbo.flush and cbo.inval. Expected: 3 Store Page faults
// 30. At level 2, setup a PTE with RX permissions
//      → In S-Mode, execute cbo.clean, cbo.flush and cbo.inval. Expected: No fault
// 31. At level 2, setup a PTE with RX permissions and set mstatus.SUM
//      → In S-Mode, execute cbo.clean, cbo.flush and cbo.inval. Expected: No fault
// 32. At level 2, setup a PTE with RWX & U permissions
//      → In S-Mode, execute cbo.clean, cbo.flush and cbo.inval. Expected: 3 Store page faults
// 33. At level 2, setup a PTE with X permission only
//      → In S-Mode, execute cbo.clean, cbo.flush and cbo.inval. Expected: 3 Store Page faults
// 34. At level 2, setup a PTE with RWX permissions and A bit unset
//      → In S-Mode, execute cbo.clean, cbo.flush and cbo.inval. Expected: 3 Store page faults
// 35. At level 2, setup a PTE with RWX permissions and D bit unset
//      → In S-Mode, execute cbo.clean, cbo.flush and cbo.inval. Expected: No fault
// 36. At level 2, setup a misaligned gigapage
//      → In S-Mode, execute cbo.clean, cbo.flush and cbo.inval. Expected: 3 Store page faults
// 37. At level 2, setup a PTE with non leaf (lvl 3) PTE pointing to RVMODEL_ACCESS_FAULT_ADDRESS instead of next page table
//      → In S-Mode, execute cbo.clean, cbo.flush and cbo.inval. Expected: 3 Store access faults
// 38. At level 2, setup a PTE with RWX permissions that points to RVMODEL_ACCESS_FAULT_ADDRESS
//      → In S-Mode, execute cbo.clean, cbo.flush and cbo.inval. Expected: 3 Store access faults
// 39. At level 2, setup a PTE with non leaf (lvl 3) PTE.D set
//      → In S-Mode, execute cbo.clean, cbo.flush and cbo.inval. Expected: 3 Store page faults
// 40. At level 2, setup a PTE with non leaf (lvl 3) PTE.A set
//      → In S-Mode, execute cbo.clean, cbo.flush and cbo.inval. Expected: 3 Store page faults
// 41. At level 2, setup a PTE with non leaf (lvl 3) PTE.U set
//      → In S-Mode, execute cbo.clean, cbo.flush and cbo.inval. Expected: 3 Store page faults
//
// 42. At level 1, setup a PTE with V=0
//      → In S-Mode, execute cbo.clean, cbo.flush and cbo.inval. Expected: 3 Store Page faults
// 43. At level 1, setup a PTE with reserved encoding R=0, W=1 & X=1
//      → In S-Mode, execute cbo.clean, cbo.flush and cbo.inval. Expected: 3 Store Page faults
// 44. At level 1, setup a PTE with reserved encoding R=0, W=1 & X=0
//      → In S-Mode, execute cbo.clean, cbo.flush and cbo.inval. Expected: 3 Store Page faults
// 45. At level 1, setup a PTE with RX permissions
//      → In S-Mode, execute cbo.clean, cbo.flush and cbo.inval. Expected: No fault
// 46. At level 1, setup a PTE with RX permissions and set mstatus.SUM
//      → In S-Mode, execute cbo.clean, cbo.flush and cbo.inval. Expected: No fault
// 47. At level 1, setup a PTE with RWX & U permissions
//      → In S-Mode, execute cbo.clean, cbo.flush and cbo.inval. Expected: 3 Store page faults
// 48. At level 1, setup a PTE with X permission only
//      → In S-Mode, execute cbo.clean, cbo.flush and cbo.inval. Expected: 3 Store Page faults
// 49. At level 1, setup a PTE with RWX permissions and A bit unset
//      → In S-Mode, execute cbo.clean, cbo.flush and cbo.inval. Expected: 3 Store page faults
// 50. At level 1, setup a PTE with RWX permissions and D bit unset
//      → In S-Mode, execute cbo.clean, cbo.flush and cbo.inval. Expected: No fault
// 51. At level 1, setup a misaligned megapage
//      → In S-Mode, execute cbo.clean, cbo.flush and cbo.inval. Expected: 3 Store page faults
// 52. At level 1, setup a PTE with non leaf (lvl 2) PTE pointing to RVMODEL_ACCESS_FAULT_ADDRESS instead of next page table
//      → In S-Mode, execute cbo.clean, cbo.flush and cbo.inval. Expected: 3 Store access faults
// 53. At level 1, setup a PTE with RWX permissions that points to RVMODEL_ACCESS_FAULT_ADDRESS
//      → In S-Mode, execute cbo.clean, cbo.flush and cbo.inval. Expected: 3 Store access faults
// 54. At level 1, setup a PTE with non leaf (lvl 2) PTE.D set
//      → In S-Mode, execute cbo.clean, cbo.flush and cbo.inval. Expected: 3 Store page faults
// 55. At level 1, setup a PTE with non leaf (lvl 2) PTE.A set
//      → In S-Mode, execute cbo.clean, cbo.flush and cbo.inval. Expected: 3 Store page faults
// 56. At level 1, setup a PTE with non leaf (lvl 2) PTE.U set
//      → In S-Mode, execute cbo.clean, cbo.flush and cbo.inval. Expected: 3 Store page faults
//
// 57. At level 0, setup a PTE with V=0
//      → In S-Mode, execute cbo.clean, cbo.flush and cbo.inval. Expected: 3 Store Page faults
// 58. At level 0, setup a PTE with reserved encoding R=0, W=1 & X=1
//      → In S-Mode, execute cbo.clean, cbo.flush and cbo.inval. Expected: 3 Store Page faults
// 59. At level 0, setup a PTE with reserved encoding R=0, W=1 & X=0
//      → In S-Mode, execute cbo.clean, cbo.flush and cbo.inval. Expected: 3 Store Page faults
// 60. At level 0, setup a PTE with RX permissions
//      → In S-Mode, execute cbo.clean, cbo.flush and cbo.inval. Expected: No fault
// 61. At level 0, setup a PTE with RX permissions and set mstatus.SUM
//      → In S-Mode, execute cbo.clean, cbo.flush and cbo.inval. Expected: No fault
// 62. At level 0, setup a PTE with RWX & U permissions
//      → In S-Mode, execute cbo.clean, cbo.flush and cbo.inval. Expected: 3 Store page faults
// 63. At level 0, setup a PTE with X permission only
//      → In S-Mode, execute cbo.clean, cbo.flush and cbo.inval. Expected: 3 Store Page faults
// 64. At level 0, setup a PTE with RWX permissions and A bit unset
//      → In S-Mode, execute cbo.clean, cbo.flush and cbo.inval. Expected: 3 Store page faults
// 65. At level 0, setup a PTE with RWX permissions and D bit unset
//      → In S-Mode, execute cbo.clean, cbo.flush and cbo.inval. Expected: No fault
// 66. At level 0, setup a PTE with only V bit set
//      → In S-Mode, execute cbo.clean, cbo.flush and cbo.inval. Expected: 3 Store page faults
// 67. At level 0, setup a PTE with non leaf (lvl 1) PTE pointing to RVMODEL_ACCESS_FAULT_ADDRESS instead of next page table
//      → In S-Mode, execute cbo.clean, cbo.flush and cbo.inval. Expected: 3 Store access faults
// 68. At level 0, setup a PTE with RWX permissions that points to RVMODEL_ACCESS_FAULT_ADDRESS
//      → In S-Mode, execute cbo.clean, cbo.flush and cbo.inval. Expected: 3 Store access faults
// 69. At level 0, setup a PTE with non leaf (lvl 1) PTE.D set
//      → In S-Mode, execute cbo.clean, cbo.flush and cbo.inval. Expected: 3 Store page faults
// 70. At level 0, setup a PTE with non leaf (lvl 1) PTE.A set
//      → In S-Mode, execute cbo.clean, cbo.flush and cbo.inval. Expected: 3 Store page faults
// 71. At level 0, setup a PTE with non leaf (lvl 1) PTE.U set
//      → In S-Mode, execute cbo.clean, cbo.flush and cbo.inval. Expected: 3 Store page faults
//
// Total Expected Faults :: 168
// --------------------------------------------------------------------------------------------------------------------------------

##### START_TEST_CONFIG #####
# REQUIRED_EXTENSIONS: [I, Sv57, Zicbom]
# MARCH: rv64i_zicsr_zicbom
# CONFIG_DEPENDENT: true
##### END_TEST_CONFIG #####

#define TEST_FILE "sv57_zicbom_exceptions_Smode.S"
#define SIGUPD_COUNT 220
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
  RVTEST_SIGUPD(x2, x5, x4, a2, \TEST_CASE\()_clean, \TEST_CASE\()_clean_str)
  RVTEST_SIGUPD(x2, x5, x4, a3, \TEST_CASE\()_flush, \TEST_CASE\()_flush_str)
  RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_inval, \TEST_CASE\()_inval_str)
.endm

// This TEST_CASES_RUNNER is used when PA is not a label
// It's used to test misaligned pages & pages at RVMODEL_ACCESS_FAULT_ADDRESS
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

  LI(t0, MENVCFG_CBCFE | MENVCFG_CBIE)
  CSRS(menvcfg, t0)                                                      // Allow execution of Zicbom instructions in S-Mode

//---------------------------------------------------------------------------------------------------------------------------------
//---------------------------------------------------------------------------------------------------------------------------------
//                                                    TESTS AT LEVEL 4
//---------------------------------------------------------------------------------------------------------------------------------
//                    256TB PAGE    Region 1 under test at level 4 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 1: Test in S-Mode | V bit unset | expected = 3 Store page faults
  SUPERPAGE_PTE_SETUP_SV57(rvtest_data_1, (PTE_D | PTE_A | PTE_X | PTE_W | PTE_R), va_data, LEVEL4)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL4, test1

//---------------------------------------------------------------------------------------------------------------------------------
//                    256TB PAGE    Region 1 under test at level 4 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 2: Test in S-Mode | WX bit set | expected = 3 Store page faults
  SUPERPAGE_PTE_SETUP_SV57(rvtest_data_1, (PTE_D | PTE_A | PTE_X | PTE_W | PTE_V), va_data, LEVEL4)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL4, test2

//---------------------------------------------------------------------------------------------------------------------------------
//                    256TB PAGE    Region 1 under test at level 4 -- RWX permission given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 3: Test in S-Mode | W bit set | expected = 3 Store page faults
  SUPERPAGE_PTE_SETUP_SV57(rvtest_data_1, (PTE_D | PTE_A | PTE_W | PTE_V), va_data, LEVEL4)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL4, test3

//---------------------------------------------------------------------------------------------------------------------------------
//                    256TB PAGE    Region 1 under test at level 4 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 4: Test in S-Mode | RX bit set | expected = No fault
  SUPERPAGE_PTE_SETUP_SV57(rvtest_data_1, (PTE_D | PTE_A | PTE_X | PTE_R | PTE_V), va_data, LEVEL4)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL4, test4

//---------------------------------------------------------------------------------------------------------------------------------
//                    256TB PAGE    Region 1 under test at level 4 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 5: Test in S-Mode | RX bit set | mstatus.SUM set | expected = No fault
  SUPERPAGE_PTE_SETUP_SV57(rvtest_data_1, (PTE_D | PTE_A | PTE_X | PTE_R | PTE_V), va_data, LEVEL4)
  sfence.vma

  LI(t0, MSTATUS_SUM)
  CSRS(mstatus, t0)                                               // Set mstatus.SUM
  TEST_CASES_RUNNER Smode, va_data, LEVEL4, test5
  LI(t0, MSTATUS_SUM)
  CSRC(mstatus, t0)                                               // Clear mstatus.SUM

//---------------------------------------------------------------------------------------------------------------------------------
//                    256TB PAGE    Region 1 under test at level 4 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 6: Test in S-Mode | RWXU bit set | expected = 3 Store page faults
  SUPERPAGE_PTE_SETUP_SV57(rvtest_data_1, (PTE_D | PTE_A | PTE_U | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL4)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL4, test6

//---------------------------------------------------------------------------------------------------------------------------------
//                    256TB PAGE    Region 1 under test at level 4 -- RWX permission given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 7: Test in S-Mode | X bit set | expected = 3 Store page faults
  SUPERPAGE_PTE_SETUP_SV57(rvtest_data_1, (PTE_D | PTE_A | PTE_X | PTE_V), va_data, LEVEL4)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL4, test7

//---------------------------------------------------------------------------------------------------------------------------------
//                    256TB PAGE    Region 1 under test at level 4 -- RWX permission given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 8: Test in S-Mode | PTE.A unset | expected = 3 Store page faults
  SUPERPAGE_PTE_SETUP_SV57(rvtest_data_1, (PTE_D | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL4)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL4, test8

//---------------------------------------------------------------------------------------------------------------------------------
//                    256TB PAGE    Region 1 under test at level 4 -- RWX permission given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 9: Test in S-Mode | PTE.D unset | expected = No fault
  SUPERPAGE_PTE_SETUP_SV57(rvtest_data_1, (PTE_A | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL4)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL4, test9

//---------------------------------------------------------------------------------------------------------------------------------
//                    256TB PAGE    Region 1 under test at level 4 -- RWX permission given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 10: Test in S-Mode | RWX bit set | Misaligned Terapage | expected = 3 Store page faults
  PTE_SETUP_SV57(rvtest_data_1, (PTE_D | PTE_A | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL4)
  sfence.vma

  TEST_CASES_RUNNER_2 Smode, 0x0, va_data, LEVEL4, test10

//---------------------------------------------------------------------------------------------------------------------------------
//                    256TB PAGE    Region 1 under test at level 4 -- RWX permission given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 11: Test in S-Mode | RWX bit set | expected = 3 Store access faults
  SUPERPAGE_PTE_SETUP_SV57(RVMODEL_ACCESS_FAULT_ADDRESS, (PTE_D | PTE_A | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL4)
  sfence.vma

  TEST_CASES_RUNNER_2 Smode, RVMODEL_ACCESS_FAULT_ADDRESS, va_data, LEVEL4, test11


//---------------------------------------------------------------------------------------------------------------------------------
//---------------------------------------------------------------------------------------------------------------------------------
//                                                    TESTS AT LEVEL 3
//---------------------------------------------------------------------------------------------------------------------------------
//                    512GB PAGE    Region 1 under test at level 3 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 12: Test in S-Mode | V bit unset | expected = 3 Store page faults
  PTE_SETUP_SV57(rvtest_slvl3_pg_tbl, (PTE_V), va_data, LEVEL4)
  SUPERPAGE_PTE_SETUP_SV57(rvtest_data_1, (PTE_D | PTE_A | PTE_X | PTE_W | PTE_R), va_data, LEVEL3)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL3, test12

//---------------------------------------------------------------------------------------------------------------------------------
//                    512GB PAGE    Region 1 under test at level 3 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 13: Test in S-Mode | WX bit set | expected = 3 Store page faults
  PTE_SETUP_SV57(rvtest_slvl3_pg_tbl, (PTE_V), va_data, LEVEL4)
  SUPERPAGE_PTE_SETUP_SV57(rvtest_data_1, (PTE_D | PTE_A | PTE_X | PTE_W | PTE_V), va_data, LEVEL3)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL3, test13

//---------------------------------------------------------------------------------------------------------------------------------
//                    512GB PAGE    Region 1 under test at level 3 -- RWX permission given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 14: Test in S-Mode | W bit set | expected = 3 Store page faults
  PTE_SETUP_SV57(rvtest_slvl3_pg_tbl, (PTE_V), va_data, LEVEL4)
  SUPERPAGE_PTE_SETUP_SV57(rvtest_data_1, (PTE_D | PTE_A | PTE_W | PTE_V), va_data, LEVEL3)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL3, test14

//---------------------------------------------------------------------------------------------------------------------------------
//                    512GB PAGE    Region 1 under test at level 3 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 15: Test in S-Mode | RX bit set | expected = No fault
  PTE_SETUP_SV57(rvtest_slvl3_pg_tbl, (PTE_V), va_data, LEVEL4)
  SUPERPAGE_PTE_SETUP_SV57(rvtest_data_1, (PTE_D | PTE_A | PTE_X | PTE_R | PTE_V), va_data, LEVEL3)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL3, test15

//---------------------------------------------------------------------------------------------------------------------------------
//                    512GB PAGE    Region 1 under test at level 3 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 16: Test in S-Mode | RX bit set | expected = No fault
  PTE_SETUP_SV57(rvtest_slvl3_pg_tbl, (PTE_V), va_data, LEVEL4)
  SUPERPAGE_PTE_SETUP_SV57(rvtest_data_1, (PTE_D | PTE_A | PTE_X | PTE_R | PTE_V), va_data, LEVEL3)
  sfence.vma

  LI(t0, MSTATUS_SUM)
  CSRS(mstatus, t0)                                               // Set mstatus.SUM
  TEST_CASES_RUNNER Smode, va_data, LEVEL3, test16
  LI(t0, MSTATUS_SUM)
  CSRC(mstatus, t0)                                               // Clear mstatus.SUM

//---------------------------------------------------------------------------------------------------------------------------------
//                    512GB PAGE    Region 1 under test at level 3 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 17: Test in S-Mode | RWXU bit set | expected = 3 Store page faults
  PTE_SETUP_SV57(rvtest_slvl3_pg_tbl, (PTE_V), va_data, LEVEL4)
  SUPERPAGE_PTE_SETUP_SV57(rvtest_data_1, (PTE_D | PTE_A | PTE_U | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL3)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL3, test17

//---------------------------------------------------------------------------------------------------------------------------------
//                    512GB PAGE    Region 1 under test at level 3 -- RWX permission given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 18: Test in S-Mode | X bit set | expected = 3 Store page faults
  PTE_SETUP_SV57(rvtest_slvl3_pg_tbl, (PTE_V), va_data, LEVEL4)
  SUPERPAGE_PTE_SETUP_SV57(rvtest_data_1, (PTE_D | PTE_A | PTE_X | PTE_V), va_data, LEVEL3)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL3, test18

//---------------------------------------------------------------------------------------------------------------------------------
//                    512GB PAGE    Region 1 under test at level 3 -- RWX permission given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 19: Test in S-Mode | PTE.A unset | expected = 3 Store page faults
  PTE_SETUP_SV57(rvtest_slvl3_pg_tbl, (PTE_V), va_data, LEVEL4)
  SUPERPAGE_PTE_SETUP_SV57(rvtest_data_1, (PTE_D | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL3)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL3, test19

//---------------------------------------------------------------------------------------------------------------------------------
//                    512GB PAGE    Region 1 under test at level 3 -- RWX permission given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 20: Test in S-Mode | PTE.D unset | expected = No fault
  PTE_SETUP_SV57(rvtest_slvl3_pg_tbl, (PTE_V), va_data, LEVEL4)
  SUPERPAGE_PTE_SETUP_SV57(rvtest_data_1, (PTE_A | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL3)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL3, test20

//---------------------------------------------------------------------------------------------------------------------------------
//                    512GB PAGE    Region 1 under test at level 3 -- RWX permission given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 21: Test in S-Mode | RWX bit set | Misaligned Gigapage | expected = 3 Store page faults
  PTE_SETUP_SV57(rvtest_slvl3_pg_tbl, (PTE_V), va_data, LEVEL4)
  PTE_SETUP_SV57(rvtest_data_1, (PTE_D | PTE_A | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL3)
  sfence.vma

  TEST_CASES_RUNNER_2 Smode, 0x0, va_data, LEVEL3, test21

//---------------------------------------------------------------------------------------------------------------------------------
//                    512GB PAGE    Region 1 under test at level 3 -- RWX permission given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 22: Test in S-Mode | Incorrect PTE setup | expected = 3 Store access faults
  PTE_SETUP_SV57(RVMODEL_ACCESS_FAULT_ADDRESS, (PTE_V), va_data, LEVEL4)
  SUPERPAGE_PTE_SETUP_SV57(rvtest_data_1, (PTE_A | PTE_D | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL3)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL3, test22

//---------------------------------------------------------------------------------------------------------------------------------
//                    512GB PAGE    Region 1 under test at level 3 -- RWX permission given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 23: Test in S-Mode | RWX bit set | expected = 3 Store access faults
  PTE_SETUP_SV57(rvtest_slvl3_pg_tbl, (PTE_V), va_data, LEVEL4)
  SUPERPAGE_PTE_SETUP_SV57(RVMODEL_ACCESS_FAULT_ADDRESS, (PTE_D | PTE_A | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL3)
  sfence.vma

  TEST_CASES_RUNNER_2 Smode, RVMODEL_ACCESS_FAULT_ADDRESS, va_data, LEVEL3, test23

//---------------------------------------------------------------------------------------------------------------------------------
//                    512GB PAGE    Region 1 under test at level 3 -- RWX permission given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 24: Test in S-Mode | PTE.D set for level 2 PTE | expected = 3 Store page faults
  PTE_SETUP_SV57(rvtest_slvl3_pg_tbl, (PTE_D | PTE_V), va_data, LEVEL4)
  SUPERPAGE_PTE_SETUP_SV57(rvtest_data_1, (PTE_D | PTE_A | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL3)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL3, test24

//---------------------------------------------------------------------------------------------------------------------------------
//                    512GB PAGE    Region 1 under test at level 3 -- RWX permission given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 25: Test in S-Mode | PTE.A set for level 2 PTE | expected = 3 Store page faults
  PTE_SETUP_SV57(rvtest_slvl3_pg_tbl, (PTE_A | PTE_V), va_data, LEVEL4)
  SUPERPAGE_PTE_SETUP_SV57(rvtest_data_1, (PTE_D | PTE_A | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL0)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL3, test25

//---------------------------------------------------------------------------------------------------------------------------------
//                    512GB PAGE    Region 1 under test at level 3 -- RWX permission given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 26: Test in S-Mode | PTE.U set for level 2 PTE | expected = 3 Store page faults
  PTE_SETUP_SV57(rvtest_slvl3_pg_tbl, (PTE_U | PTE_V), va_data, LEVEL4)
  SUPERPAGE_PTE_SETUP_SV57(rvtest_data_1, (PTE_D | PTE_A | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL3)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL3, test26


//---------------------------------------------------------------------------------------------------------------------------------
//---------------------------------------------------------------------------------------------------------------------------------
//                                                    TESTS AT LEVEL 2
//---------------------------------------------------------------------------------------------------------------------------------
//                    1GB PAGE    Region 1 under test at level 2 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 27: Test in S-Mode | V bit unset | expected = 3 Store page faults
  PTE_SETUP_SV57(rvtest_slvl3_pg_tbl, (PTE_V), va_data, LEVEL4)
  PTE_SETUP_SV57(rvtest_slvl2_pg_tbl, (PTE_V), va_data, LEVEL3)
  SUPERPAGE_PTE_SETUP_SV57(rvtest_data_1, (PTE_D | PTE_A | PTE_X | PTE_W | PTE_R), va_data, LEVEL2)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL2, test27

//---------------------------------------------------------------------------------------------------------------------------------
//                    1GB PAGE    Region 1 under test at level 2 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 28: Test in S-Mode | WX bit set | expected = 3 Store page faults
  PTE_SETUP_SV57(rvtest_slvl3_pg_tbl, (PTE_V), va_data, LEVEL4)
  PTE_SETUP_SV57(rvtest_slvl2_pg_tbl, (PTE_V), va_data, LEVEL3)
  SUPERPAGE_PTE_SETUP_SV57(rvtest_data_1, (PTE_D | PTE_A | PTE_X | PTE_W | PTE_V), va_data, LEVEL2)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL2, test28

//---------------------------------------------------------------------------------------------------------------------------------
//                    1GB PAGE    Region 1 under test at level 2 -- RWX permission given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 29: Test in S-Mode | W bit set | expected = 3 Store page faults
  PTE_SETUP_SV57(rvtest_slvl3_pg_tbl, (PTE_V), va_data, LEVEL4)
  PTE_SETUP_SV57(rvtest_slvl2_pg_tbl, (PTE_V), va_data, LEVEL3)
  SUPERPAGE_PTE_SETUP_SV57(rvtest_data_1, (PTE_D | PTE_A | PTE_W | PTE_V), va_data, LEVEL2)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL2, test29

//---------------------------------------------------------------------------------------------------------------------------------
//                    1GB PAGE    Region 1 under test at level 2 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 30: Test in S-Mode | RX bit set | expected = No fault
  PTE_SETUP_SV57(rvtest_slvl3_pg_tbl, (PTE_V), va_data, LEVEL4)
  PTE_SETUP_SV57(rvtest_slvl2_pg_tbl, (PTE_V), va_data, LEVEL3)
  SUPERPAGE_PTE_SETUP_SV57(rvtest_data_1, (PTE_D | PTE_A | PTE_X | PTE_R | PTE_V), va_data, LEVEL2)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL2, test30

//---------------------------------------------------------------------------------------------------------------------------------
//                    1GB PAGE    Region 1 under test at level 2 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 31: Test in S-Mode | RX bit set | expected = No fault
  PTE_SETUP_SV57(rvtest_slvl3_pg_tbl, (PTE_V), va_data, LEVEL4)
  PTE_SETUP_SV57(rvtest_slvl2_pg_tbl, (PTE_V), va_data, LEVEL3)
  SUPERPAGE_PTE_SETUP_SV57(rvtest_data_1, (PTE_D | PTE_A | PTE_X | PTE_R | PTE_V), va_data, LEVEL2)
  sfence.vma

  LI(t0, MSTATUS_SUM)
  CSRS(mstatus, t0)                                               // Set mstatus.SUM
  TEST_CASES_RUNNER Smode, va_data, LEVEL2, test31
  LI(t0, MSTATUS_SUM)
  CSRC(mstatus, t0)                                               // Clear mstatus.SUM

//---------------------------------------------------------------------------------------------------------------------------------
//                    1GB PAGE    Region 1 under test at level 2 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 32: Test in S-Mode | RWXU bit set | expected = 3 Store page faults
  PTE_SETUP_SV57(rvtest_slvl3_pg_tbl, (PTE_V), va_data, LEVEL4)
  PTE_SETUP_SV57(rvtest_slvl2_pg_tbl, (PTE_V), va_data, LEVEL3)
  SUPERPAGE_PTE_SETUP_SV57(rvtest_data_1, (PTE_D | PTE_A | PTE_U | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL2)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL2, test32

//---------------------------------------------------------------------------------------------------------------------------------
//                    1GB PAGE    Region 1 under test at level 2 -- RWX permission given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 33: Test in S-Mode | X bit set | expected = 3 Store page faults
  PTE_SETUP_SV57(rvtest_slvl3_pg_tbl, (PTE_V), va_data, LEVEL4)
  PTE_SETUP_SV57(rvtest_slvl2_pg_tbl, (PTE_V), va_data, LEVEL3)
  SUPERPAGE_PTE_SETUP_SV57(rvtest_data_1, (PTE_D | PTE_A | PTE_X | PTE_V), va_data, LEVEL2)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL2, test33

//---------------------------------------------------------------------------------------------------------------------------------
//                    1GB PAGE    Region 1 under test at level 2 -- RWX permission given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 34: Test in S-Mode | PTE.A unset | expected = 3 Store page faults
  PTE_SETUP_SV57(rvtest_slvl3_pg_tbl, (PTE_V), va_data, LEVEL4)
  PTE_SETUP_SV57(rvtest_slvl2_pg_tbl, (PTE_V), va_data, LEVEL3)
  SUPERPAGE_PTE_SETUP_SV57(rvtest_data_1, (PTE_D | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL2)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL2, test34

//---------------------------------------------------------------------------------------------------------------------------------
//                    1GB PAGE    Region 1 under test at level 2 -- RWX permission given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 35: Test in S-Mode | PTE.D unset | expected = No fault
  PTE_SETUP_SV57(rvtest_slvl3_pg_tbl, (PTE_V), va_data, LEVEL4)
  PTE_SETUP_SV57(rvtest_slvl2_pg_tbl, (PTE_V), va_data, LEVEL3)
  SUPERPAGE_PTE_SETUP_SV57(rvtest_data_1, (PTE_A | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL2)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL2, test35

//---------------------------------------------------------------------------------------------------------------------------------
//                    1GB PAGE    Region 1 under test at level 2 -- RWX permission given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 36: Test in S-Mode | RWX bit set | Misaligned Gigapage | expected = 3 Store page faults
  PTE_SETUP_SV57(rvtest_slvl3_pg_tbl, (PTE_V), va_data, LEVEL4)
  PTE_SETUP_SV57(rvtest_slvl2_pg_tbl, (PTE_V), va_data, LEVEL3)
  PTE_SETUP_SV57(rvtest_data_1, (PTE_D | PTE_A | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL2)
  sfence.vma

  TEST_CASES_RUNNER_2 Smode, 0x0, va_data, LEVEL2, test36

//---------------------------------------------------------------------------------------------------------------------------------
//                    1GB PAGE    Region 1 under test at level 2 -- RWX permission given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 37: Test in S-Mode | Incorrect PTE setup | expected = 3 Store access faults
  PTE_SETUP_SV57(rvtest_slvl3_pg_tbl, (PTE_V), va_data, LEVEL4)
  PTE_SETUP_SV57(RVMODEL_ACCESS_FAULT_ADDRESS, (PTE_V), va_data, LEVEL3)
  SUPERPAGE_PTE_SETUP_SV57(rvtest_data_1, (PTE_A | PTE_D | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL2)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL2, test37

//---------------------------------------------------------------------------------------------------------------------------------
//                    1GB PAGE    Region 1 under test at level 2 -- RWX permission given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 38: Test in S-Mode | RWX bit set | expected = 3 Store access faults
  PTE_SETUP_SV57(rvtest_slvl3_pg_tbl, (PTE_V), va_data, LEVEL4)
  PTE_SETUP_SV57(rvtest_slvl2_pg_tbl, (PTE_V), va_data, LEVEL3)
  SUPERPAGE_PTE_SETUP_SV57(RVMODEL_ACCESS_FAULT_ADDRESS, (PTE_D | PTE_A | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL2)
  sfence.vma

  TEST_CASES_RUNNER_2 Smode, RVMODEL_ACCESS_FAULT_ADDRESS, va_data, LEVEL2, test38

//---------------------------------------------------------------------------------------------------------------------------------
//                    1GB PAGE    Region 1 under test at level 2 -- RWX permission given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 39: Test in S-Mode | PTE.D set for level 2 PTE | expected = 3 Store page faults
  PTE_SETUP_SV57(rvtest_slvl3_pg_tbl, (PTE_V), va_data, LEVEL4)
  PTE_SETUP_SV57(rvtest_slvl2_pg_tbl, (PTE_D | PTE_V), va_data, LEVEL3)
  SUPERPAGE_PTE_SETUP_SV57(rvtest_data_1, (PTE_D | PTE_A | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL2)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL2, test39

//---------------------------------------------------------------------------------------------------------------------------------
//                    1GB PAGE    Region 1 under test at level 2 -- RWX permission given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 40: Test in S-Mode | PTE.A set for level 2 PTE | expected = 3 Store page faults
  PTE_SETUP_SV57(rvtest_slvl3_pg_tbl, (PTE_V), va_data, LEVEL4)
  PTE_SETUP_SV57(rvtest_slvl2_pg_tbl, (PTE_A | PTE_V), va_data, LEVEL3)
  SUPERPAGE_PTE_SETUP_SV57(rvtest_data_1, (PTE_D | PTE_A | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL0)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL2, test40

//---------------------------------------------------------------------------------------------------------------------------------
//                    1GB PAGE    Region 1 under test at level 2 -- RWX permission given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 41: Test in S-Mode | PTE.U set for level 2 PTE | expected = 3 Store page faults
  PTE_SETUP_SV57(rvtest_slvl3_pg_tbl, (PTE_V), va_data, LEVEL4)
  PTE_SETUP_SV57(rvtest_slvl2_pg_tbl, (PTE_U | PTE_V), va_data, LEVEL3)
  SUPERPAGE_PTE_SETUP_SV57(rvtest_data_1, (PTE_D | PTE_A | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL2)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL2, test41


//---------------------------------------------------------------------------------------------------------------------------------
//---------------------------------------------------------------------------------------------------------------------------------
//                                                    TESTS AT LEVEL 1
//---------------------------------------------------------------------------------------------------------------------------------
//                    2MB PAGE    Region 1 under test at level 1 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 42: Test in S-Mode | V bit unset | expected = 3 Store page faults
  PTE_SETUP_SV57(rvtest_slvl3_pg_tbl, (PTE_V), va_data, LEVEL4)
  PTE_SETUP_SV57(rvtest_slvl2_pg_tbl, (PTE_V), va_data, LEVEL3)
  PTE_SETUP_SV57(rvtest_slvl1_pg_tbl, (PTE_V), va_data, LEVEL2)
  SUPERPAGE_PTE_SETUP_SV57(rvtest_data_1, (PTE_D | PTE_A | PTE_X | PTE_W | PTE_R), va_data, LEVEL1)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL1, test42

//---------------------------------------------------------------------------------------------------------------------------------
//                    2MB PAGE    Region 1 under test at level 1 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 43: Test in S-Mode | WX bit set | expected = 3 Store page faults
  PTE_SETUP_SV57(rvtest_slvl3_pg_tbl, (PTE_V), va_data, LEVEL4)
  PTE_SETUP_SV57(rvtest_slvl2_pg_tbl, (PTE_V), va_data, LEVEL3)
  PTE_SETUP_SV57(rvtest_slvl1_pg_tbl, (PTE_V), va_data, LEVEL2)
  SUPERPAGE_PTE_SETUP_SV57(rvtest_data_1, (PTE_D | PTE_A | PTE_X | PTE_W | PTE_V), va_data, LEVEL1)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL1, test43

//---------------------------------------------------------------------------------------------------------------------------------
//                    2MB PAGE    Region 1 under test at level 1 -- RWX permission given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 44: Test in S-Mode | W bit set | expected = 3 Store page faults
  PTE_SETUP_SV57(rvtest_slvl3_pg_tbl, (PTE_V), va_data, LEVEL4)
  PTE_SETUP_SV57(rvtest_slvl2_pg_tbl, (PTE_V), va_data, LEVEL3)
  PTE_SETUP_SV57(rvtest_slvl1_pg_tbl, (PTE_V), va_data, LEVEL2)
  SUPERPAGE_PTE_SETUP_SV57(rvtest_data_1, (PTE_D | PTE_A | PTE_W | PTE_V), va_data, LEVEL1)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL1, test44

//---------------------------------------------------------------------------------------------------------------------------------
//                    2MB PAGE    Region 1 under test at level 1 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 45: Test in S-Mode | RX bit set | expected = No fault
  PTE_SETUP_SV57(rvtest_slvl3_pg_tbl, (PTE_V), va_data, LEVEL4)
  PTE_SETUP_SV57(rvtest_slvl2_pg_tbl, (PTE_V), va_data, LEVEL3)
  PTE_SETUP_SV57(rvtest_slvl1_pg_tbl, (PTE_V), va_data, LEVEL2)
  SUPERPAGE_PTE_SETUP_SV57(rvtest_data_1, (PTE_D | PTE_A | PTE_X | PTE_R | PTE_V), va_data, LEVEL1)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL1, test45

//---------------------------------------------------------------------------------------------------------------------------------
//                    2MB PAGE    Region 1 under test at level 1 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 46: Test in S-Mode | RX bit set | expected = No fault
  PTE_SETUP_SV57(rvtest_slvl3_pg_tbl, (PTE_V), va_data, LEVEL4)
  PTE_SETUP_SV57(rvtest_slvl2_pg_tbl, (PTE_V), va_data, LEVEL3)
  PTE_SETUP_SV57(rvtest_slvl1_pg_tbl, (PTE_V), va_data, LEVEL2)
  SUPERPAGE_PTE_SETUP_SV57(rvtest_data_1, (PTE_D | PTE_A | PTE_X | PTE_R | PTE_V), va_data, LEVEL1)
  sfence.vma

  LI(t0, MSTATUS_SUM)
  CSRS(mstatus, t0)                                               // Set mstatus.SUM
  TEST_CASES_RUNNER Smode, va_data, LEVEL1, test46
  LI(t0, MSTATUS_SUM)
  CSRC(mstatus, t0)                                               // Clear mstatus.SUM

//---------------------------------------------------------------------------------------------------------------------------------
//                    2MB PAGE    Region 1 under test at level 1 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 47: Test in S-Mode | RWXU bit set | expected = 3 Store page faults
  PTE_SETUP_SV57(rvtest_slvl3_pg_tbl, (PTE_V), va_data, LEVEL4)
  PTE_SETUP_SV57(rvtest_slvl2_pg_tbl, (PTE_V), va_data, LEVEL3)
  PTE_SETUP_SV57(rvtest_slvl1_pg_tbl, (PTE_V), va_data, LEVEL2)
  SUPERPAGE_PTE_SETUP_SV57(rvtest_data_1, (PTE_D | PTE_A | PTE_U | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL1)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL1, test47

//---------------------------------------------------------------------------------------------------------------------------------
//                    2MB PAGE    Region 1 under test at level 1 -- RWX permission given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 48: Test in S-Mode | X bit set | expected = 3 Store page faults
  PTE_SETUP_SV57(rvtest_slvl3_pg_tbl, (PTE_V), va_data, LEVEL4)
  PTE_SETUP_SV57(rvtest_slvl2_pg_tbl, (PTE_V), va_data, LEVEL3)
  PTE_SETUP_SV57(rvtest_slvl1_pg_tbl, (PTE_V), va_data, LEVEL2)
  SUPERPAGE_PTE_SETUP_SV57(rvtest_data_1, (PTE_D | PTE_A | PTE_X | PTE_V), va_data, LEVEL1)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL1, test48

//---------------------------------------------------------------------------------------------------------------------------------
//                    2MB PAGE    Region 1 under test at level 1 -- RWX permission given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 49: Test in S-Mode | PTE.A unset | expected = 3 Store page faults
  PTE_SETUP_SV57(rvtest_slvl3_pg_tbl, (PTE_V), va_data, LEVEL4)
  PTE_SETUP_SV57(rvtest_slvl2_pg_tbl, (PTE_V), va_data, LEVEL3)
  PTE_SETUP_SV57(rvtest_slvl1_pg_tbl, (PTE_V), va_data, LEVEL2)
  SUPERPAGE_PTE_SETUP_SV57(rvtest_data_1, (PTE_D | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL1)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL1, test49

//---------------------------------------------------------------------------------------------------------------------------------
//                    2MB PAGE    Region 1 under test at level 1 -- RWX permission given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 50: Test in S-Mode | PTE.D unset | expected = No fault
  PTE_SETUP_SV57(rvtest_slvl3_pg_tbl, (PTE_V), va_data, LEVEL4)
  PTE_SETUP_SV57(rvtest_slvl2_pg_tbl, (PTE_V), va_data, LEVEL3)
  PTE_SETUP_SV57(rvtest_slvl1_pg_tbl, (PTE_V), va_data, LEVEL2)
  SUPERPAGE_PTE_SETUP_SV57(rvtest_data_1, (PTE_A | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL1)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL1, test50

//---------------------------------------------------------------------------------------------------------------------------------
//                    2MB PAGE    Region 1 under test at level 1 -- RWX permission given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 51: Test in S-Mode | RWX bit set | Misaligned Megapage | expected = 3 Store page faults
  PTE_SETUP_SV57(rvtest_slvl3_pg_tbl, (PTE_V), va_data, LEVEL4)
  PTE_SETUP_SV57(rvtest_slvl2_pg_tbl, (PTE_V), va_data, LEVEL3)
  PTE_SETUP_SV57(rvtest_slvl1_pg_tbl, (PTE_V), va_data, LEVEL2)
  PTE_SETUP_SV57(rvtest_data_1, (PTE_D | PTE_A | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL1)
  sfence.vma

  TEST_CASES_RUNNER_2 Smode, 0x0, va_data, LEVEL1, test51

//---------------------------------------------------------------------------------------------------------------------------------
//                    2MB PAGE    Region 1 under test at level 1 -- RWX permission given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 52: Test in S-Mode | Incorrect PTE setup | expected = 3 Store access faults
  PTE_SETUP_SV57(rvtest_slvl3_pg_tbl, (PTE_V), va_data, LEVEL4)
  PTE_SETUP_SV57(rvtest_slvl2_pg_tbl, (PTE_V), va_data, LEVEL3)
  PTE_SETUP_SV57(RVMODEL_ACCESS_FAULT_ADDRESS, (PTE_V), va_data, LEVEL2)
  SUPERPAGE_PTE_SETUP_SV57(rvtest_data_1, (PTE_A | PTE_D | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL1)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL1, test52

//---------------------------------------------------------------------------------------------------------------------------------
//                    2MB PAGE    Region 1 under test at level 1 -- RWX permission given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 53: Test in S-Mode | RWX bit set | expected = 3 Store access faults
  PTE_SETUP_SV57(rvtest_slvl3_pg_tbl, (PTE_V), va_data, LEVEL4)
  PTE_SETUP_SV57(rvtest_slvl2_pg_tbl, (PTE_V), va_data, LEVEL3)
  PTE_SETUP_SV57(rvtest_slvl1_pg_tbl, (PTE_V), va_data, LEVEL2)
  SUPERPAGE_PTE_SETUP_SV57(RVMODEL_ACCESS_FAULT_ADDRESS, (PTE_D | PTE_A | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL1)
  sfence.vma

  TEST_CASES_RUNNER_2 Smode, RVMODEL_ACCESS_FAULT_ADDRESS, va_data, LEVEL1, test53

//---------------------------------------------------------------------------------------------------------------------------------
//                    2MB PAGE    Region 1 under test at level 1 -- RWX permission given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 54: Test in S-Mode | PTE.D set for level 2 PTE | expected = 3 Store page faults
  PTE_SETUP_SV57(rvtest_slvl3_pg_tbl, (PTE_V), va_data, LEVEL4)
  PTE_SETUP_SV57(rvtest_slvl2_pg_tbl, (PTE_V), va_data, LEVEL3)
  PTE_SETUP_SV57(rvtest_slvl1_pg_tbl, (PTE_D | PTE_V), va_data, LEVEL2)
  SUPERPAGE_PTE_SETUP_SV57(rvtest_data_1, (PTE_D | PTE_A | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL1)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL1, test54

//---------------------------------------------------------------------------------------------------------------------------------
//                    2MB PAGE    Region 1 under test at level 1 -- RWX permission given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 55: Test in S-Mode | PTE.A set for level 2 PTE | expected = 3 Store page faults
  PTE_SETUP_SV57(rvtest_slvl3_pg_tbl, (PTE_V), va_data, LEVEL4)
  PTE_SETUP_SV57(rvtest_slvl2_pg_tbl, (PTE_V), va_data, LEVEL3)
  PTE_SETUP_SV57(rvtest_slvl1_pg_tbl, (PTE_A | PTE_V), va_data, LEVEL2)
  SUPERPAGE_PTE_SETUP_SV57(rvtest_data_1, (PTE_D | PTE_A | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL0)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL1, test55

//---------------------------------------------------------------------------------------------------------------------------------
//                    2MB PAGE    Region 1 under test at level 1 -- RWX permission given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 56: Test in S-Mode | PTE.U set for level 2 PTE | expected = 3 Store page faults
  PTE_SETUP_SV57(rvtest_slvl3_pg_tbl, (PTE_V), va_data, LEVEL4)
  PTE_SETUP_SV57(rvtest_slvl2_pg_tbl, (PTE_V), va_data, LEVEL3)
  PTE_SETUP_SV57(rvtest_slvl1_pg_tbl, (PTE_U | PTE_V), va_data, LEVEL2)
  SUPERPAGE_PTE_SETUP_SV57(rvtest_data_1, (PTE_D | PTE_A | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL1)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL1, test56


//---------------------------------------------------------------------------------------------------------------------------------
//---------------------------------------------------------------------------------------------------------------------------------
//                                                    TESTS AT LEVEL 0
//---------------------------------------------------------------------------------------------------------------------------------
//                    4KB PAGE    Region 1 under test at level 0 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 57: Test in S-Mode | V bit unset | expected = 3 Store page faults
  PTE_SETUP_SV57(rvtest_slvl3_pg_tbl, (PTE_V), va_data, LEVEL4)
  PTE_SETUP_SV57(rvtest_slvl2_pg_tbl, (PTE_V), va_data, LEVEL3)
  PTE_SETUP_SV57(rvtest_slvl1_pg_tbl, (PTE_V), va_data, LEVEL2)
  PTE_SETUP_SV57(rvtest_slvl0_pg_tbl, (PTE_V), va_data, LEVEL1)
  PTE_SETUP_SV57(rvtest_data_1, (PTE_D | PTE_A | PTE_X | PTE_W | PTE_R), va_data, LEVEL0)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL0, test57

//---------------------------------------------------------------------------------------------------------------------------------
//                    4KB PAGE    Region 1 under test at level 0 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 58: Test in S-Mode | WX bit set | expected = 3 Store page faults
  PTE_SETUP_SV57(rvtest_slvl3_pg_tbl, (PTE_V), va_data, LEVEL4)
  PTE_SETUP_SV57(rvtest_slvl2_pg_tbl, (PTE_V), va_data, LEVEL3)
  PTE_SETUP_SV57(rvtest_slvl1_pg_tbl, (PTE_V), va_data, LEVEL2)
  PTE_SETUP_SV57(rvtest_slvl0_pg_tbl, (PTE_V), va_data, LEVEL1)
  PTE_SETUP_SV57(rvtest_data_1, (PTE_D | PTE_A | PTE_X | PTE_W | PTE_V), va_data, LEVEL0)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL0, test58

//---------------------------------------------------------------------------------------------------------------------------------
//                    4KB PAGE    Region 1 under test at level 0 -- RWX permission given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 59: Test in S-Mode | W bit set | expected = 3 Store page faults
  PTE_SETUP_SV57(rvtest_slvl3_pg_tbl, (PTE_V), va_data, LEVEL4)
  PTE_SETUP_SV57(rvtest_slvl2_pg_tbl, (PTE_V), va_data, LEVEL3)
  PTE_SETUP_SV57(rvtest_slvl1_pg_tbl, (PTE_V), va_data, LEVEL2)
  PTE_SETUP_SV57(rvtest_slvl0_pg_tbl, (PTE_V), va_data, LEVEL1)
  PTE_SETUP_SV57(rvtest_data_1, (PTE_D | PTE_A | PTE_W | PTE_V), va_data, LEVEL0)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL0, test59

//---------------------------------------------------------------------------------------------------------------------------------
//                    4KB PAGE    Region 1 under test at level 0 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 60: Test in S-Mode | RX bit set | expected = No fault
  PTE_SETUP_SV57(rvtest_slvl3_pg_tbl, (PTE_V), va_data, LEVEL4)
  PTE_SETUP_SV57(rvtest_slvl2_pg_tbl, (PTE_V), va_data, LEVEL3)
  PTE_SETUP_SV57(rvtest_slvl1_pg_tbl, (PTE_V), va_data, LEVEL2)
  PTE_SETUP_SV57(rvtest_slvl0_pg_tbl, (PTE_V), va_data, LEVEL1)
  PTE_SETUP_SV57(rvtest_data_1, (PTE_D | PTE_A | PTE_X | PTE_R | PTE_V), va_data, LEVEL0)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL0, test60

//---------------------------------------------------------------------------------------------------------------------------------
//                    4KB PAGE    Region 1 under test at level 0 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 61: Test in S-Mode | RX bit set | expected = No fault
  PTE_SETUP_SV57(rvtest_slvl3_pg_tbl, (PTE_V), va_data, LEVEL4)
  PTE_SETUP_SV57(rvtest_slvl2_pg_tbl, (PTE_V), va_data, LEVEL3)
  PTE_SETUP_SV57(rvtest_slvl1_pg_tbl, (PTE_V), va_data, LEVEL2)
  PTE_SETUP_SV57(rvtest_slvl0_pg_tbl, (PTE_V), va_data, LEVEL1)
  PTE_SETUP_SV57(rvtest_data_1, (PTE_D | PTE_A | PTE_X | PTE_R | PTE_V), va_data, LEVEL0)
  sfence.vma

  LI(t0, MSTATUS_SUM)
  CSRS(mstatus, t0)                                               // Set mstatus.SUM
  TEST_CASES_RUNNER Smode, va_data, LEVEL0, test61
  LI(t0, MSTATUS_SUM)
  CSRC(mstatus, t0)                                               // Clear mstatus.SUM

//---------------------------------------------------------------------------------------------------------------------------------
//                    4KB PAGE    Region 1 under test at level 0 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 62: Test in S-Mode | RWXU bit set | expected = 3 Store page faults
  PTE_SETUP_SV57(rvtest_slvl3_pg_tbl, (PTE_V), va_data, LEVEL4)
  PTE_SETUP_SV57(rvtest_slvl2_pg_tbl, (PTE_V), va_data, LEVEL3)
  PTE_SETUP_SV57(rvtest_slvl1_pg_tbl, (PTE_V), va_data, LEVEL2)
  PTE_SETUP_SV57(rvtest_slvl0_pg_tbl, (PTE_V), va_data, LEVEL1)
  PTE_SETUP_SV57(rvtest_data_1, (PTE_D | PTE_A | PTE_U | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL0)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL0, test62

//---------------------------------------------------------------------------------------------------------------------------------
//                    4KB PAGE    Region 1 under test at level 0 -- RWX permission given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 63: Test in S-Mode | X bit set | expected = 3 Store page faults
  PTE_SETUP_SV57(rvtest_slvl3_pg_tbl, (PTE_V), va_data, LEVEL4)
  PTE_SETUP_SV57(rvtest_slvl2_pg_tbl, (PTE_V), va_data, LEVEL3)
  PTE_SETUP_SV57(rvtest_slvl1_pg_tbl, (PTE_V), va_data, LEVEL2)
  PTE_SETUP_SV57(rvtest_slvl0_pg_tbl, (PTE_V), va_data, LEVEL1)
  PTE_SETUP_SV57(rvtest_data_1, (PTE_D | PTE_A | PTE_X | PTE_V), va_data, LEVEL0)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL0, test63

//---------------------------------------------------------------------------------------------------------------------------------
//                    4KB PAGE    Region 1 under test at level 0 -- RWX permission given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 64: Test in S-Mode | PTE.A unset | expected = 3 Store page faults
  PTE_SETUP_SV57(rvtest_slvl3_pg_tbl, (PTE_V), va_data, LEVEL4)
  PTE_SETUP_SV57(rvtest_slvl2_pg_tbl, (PTE_V), va_data, LEVEL3)
  PTE_SETUP_SV57(rvtest_slvl1_pg_tbl, (PTE_V), va_data, LEVEL2)
  PTE_SETUP_SV57(rvtest_slvl0_pg_tbl, (PTE_V), va_data, LEVEL1)
  PTE_SETUP_SV57(rvtest_data_1, (PTE_D | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL0)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL0, test64

//---------------------------------------------------------------------------------------------------------------------------------
//                    4KB PAGE    Region 1 under test at level 0 -- RWX permission given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 65: Test in S-Mode | PTE.D unset | expected = No fault
  PTE_SETUP_SV57(rvtest_slvl3_pg_tbl, (PTE_V), va_data, LEVEL4)
  PTE_SETUP_SV57(rvtest_slvl2_pg_tbl, (PTE_V), va_data, LEVEL3)
  PTE_SETUP_SV57(rvtest_slvl1_pg_tbl, (PTE_V), va_data, LEVEL2)
  PTE_SETUP_SV57(rvtest_slvl0_pg_tbl, (PTE_V), va_data, LEVEL1)
  PTE_SETUP_SV57(rvtest_data_1, (PTE_A | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL0)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL0, test65

//---------------------------------------------------------------------------------------------------------------------------------
//                    4KB PAGE    Region 1 under test at level 0 -- RWX permission given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 66: Test in S-Mode | Only V bit set at Level 0 | expected = 3 Store page faults
  PTE_SETUP_SV57(rvtest_slvl3_pg_tbl, (PTE_V), va_data, LEVEL4)
  PTE_SETUP_SV57(rvtest_slvl2_pg_tbl, (PTE_V), va_data, LEVEL3)
  PTE_SETUP_SV57(rvtest_slvl1_pg_tbl, (PTE_V), va_data, LEVEL2)
  PTE_SETUP_SV57(rvtest_slvl0_pg_tbl, (PTE_V), va_data, LEVEL1)
  PTE_SETUP_SV57(rvtest_data_1, (PTE_V), va_data, LEVEL0)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL0, test66

//---------------------------------------------------------------------------------------------------------------------------------
//                    4KB PAGE    Region 1 under test at level 0 -- RWX permission given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 67: Test in S-Mode | Incorrect PTE setup | expected = 3 Store access faults
  PTE_SETUP_SV57(rvtest_slvl3_pg_tbl, (PTE_V), va_data, LEVEL4)
  PTE_SETUP_SV57(rvtest_slvl2_pg_tbl, (PTE_V), va_data, LEVEL3)
  PTE_SETUP_SV57(rvtest_slvl1_pg_tbl, (PTE_V), va_data, LEVEL2)
  PTE_SETUP_SV57(RVMODEL_ACCESS_FAULT_ADDRESS, (PTE_V), va_data, LEVEL1)
  PTE_SETUP_SV57(rvtest_data_1, (PTE_D | PTE_A | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL0)
  sfence.vma

  TEST_CASES_RUNNER_2 Smode, RVMODEL_ACCESS_FAULT_ADDRESS, va_data, LEVEL0, test67

//---------------------------------------------------------------------------------------------------------------------------------
//                    4KB PAGE    Region 1 under test at level 0 -- RWX permission given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 68: Test in S-Mode | RWX bit set | expected = 3 Store access faults
  PTE_SETUP_SV57(rvtest_slvl3_pg_tbl, (PTE_V), va_data, LEVEL4)
  PTE_SETUP_SV57(rvtest_slvl2_pg_tbl, (PTE_V), va_data, LEVEL3)
  PTE_SETUP_SV57(rvtest_slvl1_pg_tbl, (PTE_V), va_data, LEVEL2)
  PTE_SETUP_SV57(rvtest_slvl0_pg_tbl, (PTE_V), va_data, LEVEL1)
  PTE_SETUP_SV57(RVMODEL_ACCESS_FAULT_ADDRESS, (PTE_D | PTE_A | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL0)
  sfence.vma

  TEST_CASES_RUNNER_2 Smode, RVMODEL_ACCESS_FAULT_ADDRESS, va_data, LEVEL0, test68

//---------------------------------------------------------------------------------------------------------------------------------
//                    4KB PAGE    Region 1 under test at level 0 -- RWX permission given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 69: Test in S-Mode | PTE.D set for level 1 PTE | expected = 3 Store page faults
  PTE_SETUP_SV57(rvtest_slvl3_pg_tbl, (PTE_V), va_data, LEVEL4)
  PTE_SETUP_SV57(rvtest_slvl2_pg_tbl, (PTE_V), va_data, LEVEL3)
  PTE_SETUP_SV57(rvtest_slvl1_pg_tbl, (PTE_V), va_data, LEVEL2)
  PTE_SETUP_SV57(rvtest_slvl0_pg_tbl, (PTE_D | PTE_V), va_data, LEVEL1)
  PTE_SETUP_SV57(rvtest_data_1, (PTE_D | PTE_A | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL0)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL0, test69

//---------------------------------------------------------------------------------------------------------------------------------
//                    4KB PAGE    Region 1 under test at level 0 -- RWX permission given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 70: Test in S-Mode | PTE.A set for level 1 PTE | expected = 3 Store page faults
  PTE_SETUP_SV57(rvtest_slvl3_pg_tbl, (PTE_V), va_data, LEVEL4)
  PTE_SETUP_SV57(rvtest_slvl2_pg_tbl, (PTE_V), va_data, LEVEL3)
  PTE_SETUP_SV57(rvtest_slvl1_pg_tbl, (PTE_V), va_data, LEVEL2)
  PTE_SETUP_SV57(rvtest_slvl0_pg_tbl, (PTE_A | PTE_V), va_data, LEVEL1)
  PTE_SETUP_SV57(rvtest_data_1, (PTE_D | PTE_A | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL0)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL0, test70

//---------------------------------------------------------------------------------------------------------------------------------
//                    4KB PAGE    Region 1 under test at level 0 -- RWX permission given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 71: Test in S-Mode | PTE.U set for level 1 PTE | expected = 3 Store page faults
  PTE_SETUP_SV57(rvtest_slvl3_pg_tbl, (PTE_V), va_data, LEVEL4)
  PTE_SETUP_SV57(rvtest_slvl2_pg_tbl, (PTE_V), va_data, LEVEL3)
  PTE_SETUP_SV57(rvtest_slvl1_pg_tbl, (PTE_V), va_data, LEVEL2)
  PTE_SETUP_SV57(rvtest_slvl0_pg_tbl, (PTE_U | PTE_V), va_data, LEVEL1)
  PTE_SETUP_SV57(rvtest_data_1, (PTE_D | PTE_A | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL0)
  sfence.vma

  TEST_CASES_RUNNER Smode, va_data, LEVEL0, test71


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
test27_clean_str:  .string "\"Mismatch during cbo.clean in Test Case 27!\""
test27_flush_str:  .string "\"Mismatch during cbo.flush in Test Case 27!\""
test27_inval_str:  .string "\"Mismatch during cbo.inval in Test Case 27!\""
test28_clean_str:  .string "\"Mismatch during cbo.clean in Test Case 28!\""
test28_flush_str:  .string "\"Mismatch during cbo.flush in Test Case 28!\""
test28_inval_str:  .string "\"Mismatch during cbo.inval in Test Case 28!\""
test29_clean_str:  .string "\"Mismatch during cbo.clean in Test Case 29!\""
test29_flush_str:  .string "\"Mismatch during cbo.flush in Test Case 29!\""
test29_inval_str:  .string "\"Mismatch during cbo.inval in Test Case 29!\""
test30_clean_str:  .string "\"Mismatch during cbo.clean in Test Case 30!\""
test30_flush_str:  .string "\"Mismatch during cbo.flush in Test Case 30!\""
test30_inval_str:  .string "\"Mismatch during cbo.inval in Test Case 30!\""
test31_clean_str:  .string "\"Mismatch during cbo.clean in Test Case 31!\""
test31_flush_str:  .string "\"Mismatch during cbo.flush in Test Case 31!\""
test31_inval_str:  .string "\"Mismatch during cbo.inval in Test Case 31!\""
test32_clean_str:  .string "\"Mismatch during cbo.clean in Test Case 32!\""
test32_flush_str:  .string "\"Mismatch during cbo.flush in Test Case 32!\""
test32_inval_str:  .string "\"Mismatch during cbo.inval in Test Case 32!\""
test33_clean_str:  .string "\"Mismatch during cbo.clean in Test Case 33!\""
test33_flush_str:  .string "\"Mismatch during cbo.flush in Test Case 33!\""
test33_inval_str:  .string "\"Mismatch during cbo.inval in Test Case 33!\""
test34_clean_str:  .string "\"Mismatch during cbo.clean in Test Case 34!\""
test34_flush_str:  .string "\"Mismatch during cbo.flush in Test Case 34!\""
test34_inval_str:  .string "\"Mismatch during cbo.inval in Test Case 34!\""
test35_clean_str:  .string "\"Mismatch during cbo.clean in Test Case 35!\""
test35_flush_str:  .string "\"Mismatch during cbo.flush in Test Case 35!\""
test35_inval_str:  .string "\"Mismatch during cbo.inval in Test Case 35!\""
test36_clean_str:  .string "\"Mismatch during cbo.clean in Test Case 36!\""
test36_flush_str:  .string "\"Mismatch during cbo.flush in Test Case 36!\""
test36_inval_str:  .string "\"Mismatch during cbo.inval in Test Case 36!\""
test37_clean_str:  .string "\"Mismatch during cbo.clean in Test Case 37!\""
test37_flush_str:  .string "\"Mismatch during cbo.flush in Test Case 37!\""
test37_inval_str:  .string "\"Mismatch during cbo.inval in Test Case 37!\""
test38_clean_str:  .string "\"Mismatch during cbo.clean in Test Case 38!\""
test38_flush_str:  .string "\"Mismatch during cbo.flush in Test Case 38!\""
test38_inval_str:  .string "\"Mismatch during cbo.inval in Test Case 38!\""
test39_clean_str:  .string "\"Mismatch during cbo.clean in Test Case 39!\""
test39_flush_str:  .string "\"Mismatch during cbo.flush in Test Case 39!\""
test39_inval_str:  .string "\"Mismatch during cbo.inval in Test Case 39!\""
test40_clean_str:  .string "\"Mismatch during cbo.clean in Test Case 40!\""
test40_flush_str:  .string "\"Mismatch during cbo.flush in Test Case 40!\""
test40_inval_str:  .string "\"Mismatch during cbo.inval in Test Case 40!\""
test41_clean_str:  .string "\"Mismatch during cbo.clean in Test Case 41!\""
test41_flush_str:  .string "\"Mismatch during cbo.flush in Test Case 41!\""
test41_inval_str:  .string "\"Mismatch during cbo.inval in Test Case 41!\""
test42_clean_str:  .string "\"Mismatch during cbo.clean in Test Case 42!\""
test42_flush_str:  .string "\"Mismatch during cbo.flush in Test Case 42!\""
test42_inval_str:  .string "\"Mismatch during cbo.inval in Test Case 42!\""
test43_clean_str:  .string "\"Mismatch during cbo.clean in Test Case 43!\""
test43_flush_str:  .string "\"Mismatch during cbo.flush in Test Case 43!\""
test43_inval_str:  .string "\"Mismatch during cbo.inval in Test Case 43!\""
test44_clean_str:  .string "\"Mismatch during cbo.clean in Test Case 44!\""
test44_flush_str:  .string "\"Mismatch during cbo.flush in Test Case 44!\""
test44_inval_str:  .string "\"Mismatch during cbo.inval in Test Case 44!\""
test45_clean_str:  .string "\"Mismatch during cbo.clean in Test Case 45!\""
test45_flush_str:  .string "\"Mismatch during cbo.flush in Test Case 45!\""
test45_inval_str:  .string "\"Mismatch during cbo.inval in Test Case 45!\""
test46_clean_str:  .string "\"Mismatch during cbo.clean in Test Case 46!\""
test46_flush_str:  .string "\"Mismatch during cbo.flush in Test Case 46!\""
test46_inval_str:  .string "\"Mismatch during cbo.inval in Test Case 46!\""
test47_clean_str:  .string "\"Mismatch during cbo.clean in Test Case 47!\""
test47_flush_str:  .string "\"Mismatch during cbo.flush in Test Case 47!\""
test47_inval_str:  .string "\"Mismatch during cbo.inval in Test Case 47!\""
test48_clean_str:  .string "\"Mismatch during cbo.clean in Test Case 48!\""
test48_flush_str:  .string "\"Mismatch during cbo.flush in Test Case 48!\""
test48_inval_str:  .string "\"Mismatch during cbo.inval in Test Case 48!\""
test49_clean_str:  .string "\"Mismatch during cbo.clean in Test Case 49!\""
test49_flush_str:  .string "\"Mismatch during cbo.flush in Test Case 49!\""
test49_inval_str:  .string "\"Mismatch during cbo.inval in Test Case 49!\""
test50_clean_str:  .string "\"Mismatch during cbo.clean in Test Case 50!\""
test50_flush_str:  .string "\"Mismatch during cbo.flush in Test Case 50!\""
test50_inval_str:  .string "\"Mismatch during cbo.inval in Test Case 50!\""
test51_clean_str:  .string "\"Mismatch during cbo.clean in Test Case 51!\""
test51_flush_str:  .string "\"Mismatch during cbo.flush in Test Case 51!\""
test51_inval_str:  .string "\"Mismatch during cbo.inval in Test Case 51!\""
test52_clean_str:  .string "\"Mismatch during cbo.clean in Test Case 52!\""
test52_flush_str:  .string "\"Mismatch during cbo.flush in Test Case 52!\""
test52_inval_str:  .string "\"Mismatch during cbo.inval in Test Case 52!\""
test53_clean_str:  .string "\"Mismatch during cbo.clean in Test Case 53!\""
test53_flush_str:  .string "\"Mismatch during cbo.flush in Test Case 53!\""
test53_inval_str:  .string "\"Mismatch during cbo.inval in Test Case 53!\""
test54_clean_str:  .string "\"Mismatch during cbo.clean in Test Case 54!\""
test54_flush_str:  .string "\"Mismatch during cbo.flush in Test Case 54!\""
test54_inval_str:  .string "\"Mismatch during cbo.inval in Test Case 54!\""
test55_clean_str:  .string "\"Mismatch during cbo.clean in Test Case 55!\""
test55_flush_str:  .string "\"Mismatch during cbo.flush in Test Case 55!\""
test55_inval_str:  .string "\"Mismatch during cbo.inval in Test Case 55!\""
test56_clean_str:  .string "\"Mismatch during cbo.clean in Test Case 56!\""
test56_flush_str:  .string "\"Mismatch during cbo.flush in Test Case 56!\""
test56_inval_str:  .string "\"Mismatch during cbo.inval in Test Case 56!\""
test57_clean_str:  .string "\"Mismatch during cbo.clean in Test Case 57!\""
test57_flush_str:  .string "\"Mismatch during cbo.flush in Test Case 57!\""
test57_inval_str:  .string "\"Mismatch during cbo.inval in Test Case 57!\""
test58_clean_str:  .string "\"Mismatch during cbo.clean in Test Case 58!\""
test58_flush_str:  .string "\"Mismatch during cbo.flush in Test Case 58!\""
test58_inval_str:  .string "\"Mismatch during cbo.inval in Test Case 58!\""
test59_clean_str:  .string "\"Mismatch during cbo.clean in Test Case 59!\""
test59_flush_str:  .string "\"Mismatch during cbo.flush in Test Case 59!\""
test59_inval_str:  .string "\"Mismatch during cbo.inval in Test Case 59!\""
test60_clean_str:  .string "\"Mismatch during cbo.clean in Test Case 60!\""
test60_flush_str:  .string "\"Mismatch during cbo.flush in Test Case 60!\""
test60_inval_str:  .string "\"Mismatch during cbo.inval in Test Case 60!\""
test61_clean_str:  .string "\"Mismatch during cbo.clean in Test Case 61!\""
test61_flush_str:  .string "\"Mismatch during cbo.flush in Test Case 61!\""
test61_inval_str:  .string "\"Mismatch during cbo.inval in Test Case 61!\""
test62_clean_str:  .string "\"Mismatch during cbo.clean in Test Case 62!\""
test62_flush_str:  .string "\"Mismatch during cbo.flush in Test Case 62!\""
test62_inval_str:  .string "\"Mismatch during cbo.inval in Test Case 62!\""
test63_clean_str:  .string "\"Mismatch during cbo.clean in Test Case 63!\""
test63_flush_str:  .string "\"Mismatch during cbo.flush in Test Case 63!\""
test63_inval_str:  .string "\"Mismatch during cbo.inval in Test Case 63!\""
test64_clean_str:  .string "\"Mismatch during cbo.clean in Test Case 64!\""
test64_flush_str:  .string "\"Mismatch during cbo.flush in Test Case 64!\""
test64_inval_str:  .string "\"Mismatch during cbo.inval in Test Case 64!\""
test65_clean_str:  .string "\"Mismatch during cbo.clean in Test Case 65!\""
test65_flush_str:  .string "\"Mismatch during cbo.flush in Test Case 65!\""
test65_inval_str:  .string "\"Mismatch during cbo.inval in Test Case 65!\""
test66_clean_str:  .string "\"Mismatch during cbo.clean in Test Case 66!\""
test66_flush_str:  .string "\"Mismatch during cbo.flush in Test Case 66!\""
test66_inval_str:  .string "\"Mismatch during cbo.inval in Test Case 66!\""
test67_clean_str:  .string "\"Mismatch during cbo.clean in Test Case 67!\""
test67_flush_str:  .string "\"Mismatch during cbo.flush in Test Case 67!\""
test67_inval_str:  .string "\"Mismatch during cbo.inval in Test Case 67!\""
test68_clean_str:  .string "\"Mismatch during cbo.clean in Test Case 68!\""
test68_flush_str:  .string "\"Mismatch during cbo.flush in Test Case 68!\""
test68_inval_str:  .string "\"Mismatch during cbo.inval in Test Case 68!\""
test69_clean_str:  .string "\"Mismatch during cbo.clean in Test Case 69!\""
test69_flush_str:  .string "\"Mismatch during cbo.flush in Test Case 69!\""
test69_inval_str:  .string "\"Mismatch during cbo.inval in Test Case 69!\""
test70_clean_str:  .string "\"Mismatch during cbo.clean in Test Case 70!\""
test70_flush_str:  .string "\"Mismatch during cbo.flush in Test Case 70!\""
test70_inval_str:  .string "\"Mismatch during cbo.inval in Test Case 70!\""
test71_clean_str:  .string "\"Mismatch during cbo.clean in Test Case 71!\""
test71_flush_str:  .string "\"Mismatch during cbo.flush in Test Case 71!\""
test71_inval_str:  .string "\"Mismatch during cbo.inval in Test Case 71!\""

RVTEST_DATA_END
RVTEST_SIG_SETUP
