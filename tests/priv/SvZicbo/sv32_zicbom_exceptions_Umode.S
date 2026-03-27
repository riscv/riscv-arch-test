// --------------------------------------------------------------------------------------------------------------------------------
// Developed by: Umer Shahid & Muhammad Zain
// --------------------------------------------------------------------------------------------------------------------------------
// Test cases are as follows:
// --------------------------------------------------------------------------------------------------------------------------------
// 1. At level 1, setup a PTE with V=0
//      → In U-Mode, execute cbo.clean, cbo.flush and cbo.inval. Expected: 3 Store Page faults
// 2. At level 1, setup a PTE with reserved encoding R=0, W=1 & X=1
//      → In U-Mode, execute cbo.clean, cbo.flush and cbo.inval. Expected: 3 Store Page faults
// 3. At level 1, setup a PTE with reserved encoding R=0, W=1 & X=0
//      → In U-Mode, execute cbo.clean, cbo.flush and cbo.inval. Expected: 3 Store Page faults
// 4. At level 1, setup a PTE with RX permissions
//      → In U-Mode, execute cbo.clean, cbo.flush and cbo.inval. Expected: No fault
// 5. At level 1, setup a PTE with RWX permissions & U bit unset
//      → In U-Mode, execute cbo.clean, cbo.flush and cbo.inval. Expected: 3 Store page faults
// 6. At level 1, setup a PTE with X permission only
//      → In U-Mode, execute cbo.clean, cbo.flush and cbo.inval. Expected: 3 Store Page faults
// 7. At level 1, setup a PTE with RWX permissions and A bit unset
//      → In U-Mode, execute cbo.clean, cbo.flush and cbo.inval. Expected: 3 Store page faults
// 8. At level 1, setup a PTE with RWX permissions and D bit unset
//      → In U-Mode, execute cbo.clean, cbo.flush and cbo.inval. Expected: No fault
// 9. At level 1, setup a misaligned megapage
//      → In U-Mode, execute cbo.clean, cbo.flush and cbo.inval. Expected: 3 Store page faults
// 10. At level 1, setup a PTE with RWX permissions that points to RVMODEL_ACCESS_FAULT_ADDRESS
//      → In U-Mode, execute cbo.clean, cbo.flush and cbo.inval. Expected: 3 Store access faults
//
// 11. At level 0, setup a PTE with V=0
//      → In U-Mode, execute cbo.clean, cbo.flush and cbo.inval. Expected: 3 Store Page faults
// 12. At level 0, setup a PTE with reserved encoding R=0, W=1 & X=1
//      → In U-Mode, execute cbo.clean, cbo.flush and cbo.inval. Expected: 3 Store Page faults
// 13. At level 0, setup a PTE with reserved encoding R=0, W=1 & X=0
//      → In U-Mode, execute cbo.clean, cbo.flush and cbo.inval. Expected: 3 Store Page faults
// 14. At level 0, setup a PTE with RX permissions
//      → In U-Mode, execute cbo.clean, cbo.flush and cbo.inval. Expected: No fault
// 15. At level 0, setup a PTE with RWX permissions & U bit unset
//      → In U-Mode, execute cbo.clean, cbo.flush and cbo.inval. Expected: 3 Store page faults
// 16. At level 0, setup a PTE with X permission only
//      → In U-Mode, execute cbo.clean, cbo.flush and cbo.inval. Expected: 3 Store Page faults
// 17. At level 0, setup a PTE with RWX permissions and A bit unset
//      → In U-Mode, execute cbo.clean, cbo.flush and cbo.inval. Expected: 3 Store page faults
// 18. At level 0, setup a PTE with RWX permissions and D bit unset
//      → In U-Mode, execute cbo.clean, cbo.flush and cbo.inval. Expected: No fault
// 19. At level 0, setup a PTE with only V bit set
//      → In U-Mode, execute cbo.clean, cbo.flush and cbo.inval. Expected: 3 Store page faults
// 20. At level 0, setup a PTE with non leaf (lvl 1) PTE pointing to RVMODEL_ACCESS_FAULT_ADDRESS instead of next page table
//      → In U-Mode, execute cbo.clean, cbo.flush and cbo.inval. Expected: 3 Store access faults
// 21. At level 0, setup a PTE with RWX permissions that points to RVMODEL_ACCESS_FAULT_ADDRESS
//      → In U-Mode, execute cbo.clean, cbo.flush and cbo.inval. Expected: 3 Store access faults
// 22. At level 0, setup a PTE with non leaf (lvl 1) PTE.D set
//      → In U-Mode, execute cbo.clean, cbo.flush and cbo.inval. Expected: 3 Store page faults
// 23. At level 0, setup a PTE with non leaf (lvl 1) PTE.A set
//      → In U-Mode, execute cbo.clean, cbo.flush and cbo.inval. Expected: 3 Store page faults
// 24. At level 0, setup a PTE with non leaf (lvl 1) PTE.U set
//      → In U-Mode, execute cbo.clean, cbo.flush and cbo.inval. Expected: 3 Store page faults
//
// Total Expected Faults :: 60
// --------------------------------------------------------------------------------------------------------------------------------

// Remove NORUN once Sail version 0.11 is released
##### START_TEST_CONFIG #####
# REQUIRED_EXTENSIONS: [I, Sv32, Zicbom, NORUN]
# MARCH: rv32i_zicsr_zicbom
# CONFIG_DEPENDENT: true
##### END_TEST_CONFIG #####

#define TEST_FILE "sv32_zicbom_exceptions_Umode.S"
#define SIGUPD_COUNT 80
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
  LI( a2, 0x800)            // Test signature initialization

//---------------------------------------------------------------------------------------------------------------------------------
//                                   Virtual addresses definition for code and test regions
//---------------------------------------------------------------------------------------------------------------------------------

  // Virtual Address of Test section (rvtest_data_1)
  .set va_data,               0x90407000

  // Virtual Address for code region
  .set va_rvtest_code_begin,  0x30000000


  // PTE setup for Code Region
  SUPERPAGE_PTE_SETUP_SV32(rvtest_code_begin, (PTE_D | PTE_A | PTE_U | PTE_X | PTE_R | PTE_V), va_rvtest_code_begin, LEVEL1)
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
  CSRS(senvcfg, t0)                                                      // Further delegate the permission to U-Mode

//---------------------------------------------------------------------------------------------------------------------------------
//---------------------------------------------------------------------------------------------------------------------------------
//                                                    TESTS AT LEVEL 1
//---------------------------------------------------------------------------------------------------------------------------------
//                    4MB PAGE    Region 1 under test at level 1 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 1: Test in U-Mode | V bit unset | expected = 3 Store page faults
  SUPERPAGE_PTE_SETUP_SV32(rvtest_data_1, (PTE_D | PTE_A | PTE_U | PTE_X | PTE_W | PTE_R), va_data, LEVEL1)
  sfence.vma

  TEST_CASES_RUNNER Umode, va_data, LEVEL1, test1

//---------------------------------------------------------------------------------------------------------------------------------
//                    4MB PAGE    Region 1 under test at level 1 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 2: Test in U-Mode | WX bit set | expected = 3 Store page faults
  SUPERPAGE_PTE_SETUP_SV32(rvtest_data_1, (PTE_D | PTE_A | PTE_U | PTE_X | PTE_W | PTE_V), va_data, LEVEL1)
  sfence.vma

  TEST_CASES_RUNNER Umode, va_data, LEVEL1, test2

//---------------------------------------------------------------------------------------------------------------------------------
//                    4MB PAGE    Region 1 under test at level 1 -- RWX permission given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 3: Test in U-Mode | W bit set | expected = 3 Store page faults
  SUPERPAGE_PTE_SETUP_SV32(rvtest_data_1, (PTE_D | PTE_A | PTE_U | PTE_W | PTE_V), va_data, LEVEL1)
  sfence.vma

  TEST_CASES_RUNNER Umode, va_data, LEVEL1, test3

//---------------------------------------------------------------------------------------------------------------------------------
//                    4MB PAGE    Region 1 under test at level 1 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 4: Test in U-Mode | RX bit set | expected = No fault
  SUPERPAGE_PTE_SETUP_SV32(rvtest_data_1, (PTE_D | PTE_A | PTE_U | PTE_X | PTE_R | PTE_V), va_data, LEVEL1)
  sfence.vma

  TEST_CASES_RUNNER Umode, va_data, LEVEL1, test4

//---------------------------------------------------------------------------------------------------------------------------------
//                    4MB PAGE    Region 1 under test at level 1 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 5: Test in U-Mode | RWX bit set | expected = 3 Store page faults
  SUPERPAGE_PTE_SETUP_SV32(rvtest_data_1, (PTE_D | PTE_A | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL1)
  sfence.vma

  TEST_CASES_RUNNER Umode, va_data, LEVEL1, test5

//---------------------------------------------------------------------------------------------------------------------------------
//                    4MB PAGE    Region 1 under test at level 1 -- RWX permission given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 6: Test in U-Mode | X bit set | expected = 3 Store page faults
  SUPERPAGE_PTE_SETUP_SV32(rvtest_data_1, (PTE_D | PTE_A | PTE_U | PTE_X | PTE_V), va_data, LEVEL1)
  sfence.vma

  TEST_CASES_RUNNER Umode, va_data, LEVEL1, test6

//---------------------------------------------------------------------------------------------------------------------------------
//                    4MB PAGE    Region 1 under test at level 1 -- RWX permission given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 7: Test in U-Mode | PTE.A unset | expected = 3 Store page faults
  SUPERPAGE_PTE_SETUP_SV32(rvtest_data_1, (PTE_D | PTE_U | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL1)
  sfence.vma

  TEST_CASES_RUNNER Umode, va_data, LEVEL1, test7

//---------------------------------------------------------------------------------------------------------------------------------
//                    4MB PAGE    Region 1 under test at level 1 -- RWX permission given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 8: Test in U-Mode | PTE.D unset | expected = No fault
  SUPERPAGE_PTE_SETUP_SV32(rvtest_data_1, (PTE_A | PTE_U | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL1)
  sfence.vma

  TEST_CASES_RUNNER Umode, va_data, LEVEL1, test8

//---------------------------------------------------------------------------------------------------------------------------------
//                    4MB PAGE    Region 1 under test at level 1 -- RWX permission given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 9: Test in U-Mode | RWX bit set | Misaligned Megapage | expected = 3 Store page faults
  PTE_SETUP_SV32(rvtest_data_1, (PTE_D | PTE_A | PTE_U | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL1)
  sfence.vma

  TEST_CASES_RUNNER_2 Umode, 0x0, va_data, LEVEL1, test9

//---------------------------------------------------------------------------------------------------------------------------------
//                    4MB PAGE    Region 1 under test at level 1 -- RWX permission given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 10: Test in U-Mode | RWX bit set | expected = 3 Store access faults
  SUPERPAGE_PTE_SETUP_SV32(RVMODEL_ACCESS_FAULT_ADDRESS, (PTE_D | PTE_A | PTE_U | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL1)
  sfence.vma

  TEST_CASES_RUNNER_2 Umode, RVMODEL_ACCESS_FAULT_ADDRESS, va_data, LEVEL1, test10


//---------------------------------------------------------------------------------------------------------------------------------
//---------------------------------------------------------------------------------------------------------------------------------
//                                                    TESTS AT LEVEL 0
//---------------------------------------------------------------------------------------------------------------------------------
//                    4KB PAGE    Region 1 under test at level 0 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 11: Test in U-Mode | V bit unset | expected = 3 Store page faults
  PTE_SETUP_SV32(rvtest_slvl0_pg_tbl, (PTE_V), va_data, LEVEL1)
  PTE_SETUP_SV32(rvtest_data_1, (PTE_D | PTE_A | PTE_U | PTE_X | PTE_W | PTE_R), va_data, LEVEL0)
  sfence.vma

  TEST_CASES_RUNNER Umode, va_data, LEVEL0, test11

//---------------------------------------------------------------------------------------------------------------------------------
//                    4KB PAGE    Region 1 under test at level 0 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 12: Test in U-Mode | WX bit set | expected = 3 Store page faults
  PTE_SETUP_SV32(rvtest_slvl0_pg_tbl, (PTE_V), va_data, LEVEL1)
  PTE_SETUP_SV32(rvtest_data_1, (PTE_D | PTE_A | PTE_U | PTE_X | PTE_W | PTE_V), va_data, LEVEL0)
  sfence.vma

  TEST_CASES_RUNNER Umode, va_data, LEVEL0, test12

//---------------------------------------------------------------------------------------------------------------------------------
//                    4KB PAGE    Region 1 under test at level 0 -- RWX permission given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 13: Test in U-Mode | W bit set | expected = 3 Store page faults
  PTE_SETUP_SV32(rvtest_slvl0_pg_tbl, (PTE_V), va_data, LEVEL1)
  PTE_SETUP_SV32(rvtest_data_1, (PTE_D | PTE_A | PTE_U | PTE_W | PTE_V), va_data, LEVEL0)
  sfence.vma

  TEST_CASES_RUNNER Umode, va_data, LEVEL0, test13

//---------------------------------------------------------------------------------------------------------------------------------
//                    4KB PAGE    Region 1 under test at level 0 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 14: Test in U-Mode | RX bit set | expected = No fault
  PTE_SETUP_SV32(rvtest_slvl0_pg_tbl, (PTE_V), va_data, LEVEL1)
  PTE_SETUP_SV32(rvtest_data_1, (PTE_D | PTE_A | PTE_U | PTE_X | PTE_R | PTE_V), va_data, LEVEL0)
  sfence.vma

  TEST_CASES_RUNNER Umode, va_data, LEVEL0, test14

//---------------------------------------------------------------------------------------------------------------------------------
//                    4KB PAGE    Region 1 under test at level 0 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 15: Test in U-Mode | RWX bit set | expected = 3 Store page faults
  PTE_SETUP_SV32(rvtest_slvl0_pg_tbl, (PTE_V), va_data, LEVEL1)
  PTE_SETUP_SV32(rvtest_data_1, (PTE_D | PTE_A | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL0)
  sfence.vma

  TEST_CASES_RUNNER Umode, va_data, LEVEL0, test15

//---------------------------------------------------------------------------------------------------------------------------------
//                    4KB PAGE    Region 1 under test at level 0 -- RWX permission given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 16: Test in U-Mode | X bit set | expected = 3 Store page faults
  PTE_SETUP_SV32(rvtest_slvl0_pg_tbl, (PTE_V), va_data, LEVEL1)
  PTE_SETUP_SV32(rvtest_data_1, (PTE_D | PTE_A | PTE_U | PTE_X | PTE_V), va_data, LEVEL0)
  sfence.vma

  TEST_CASES_RUNNER Umode, va_data, LEVEL0, test16

//---------------------------------------------------------------------------------------------------------------------------------
//                    4KB PAGE    Region 1 under test at level 0 -- RWX permission given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 17: Test in U-Mode | PTE.A unset | expected = 3 Store page faults
  PTE_SETUP_SV32(rvtest_slvl0_pg_tbl, (PTE_V), va_data, LEVEL1)
  PTE_SETUP_SV32(rvtest_data_1, (PTE_D | PTE_U | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL0)
  sfence.vma

  TEST_CASES_RUNNER Umode, va_data, LEVEL0, test17

//---------------------------------------------------------------------------------------------------------------------------------
//                    4KB PAGE    Region 1 under test at level 0 -- RWX permission given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 18: Test in U-Mode | PTE.D unset | expected = No fault
  PTE_SETUP_SV32(rvtest_slvl0_pg_tbl, (PTE_V), va_data, LEVEL1)
  PTE_SETUP_SV32(rvtest_data_1, (PTE_A | PTE_U | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL0)
  sfence.vma

  TEST_CASES_RUNNER Umode, va_data, LEVEL0, test18

//---------------------------------------------------------------------------------------------------------------------------------
//                    4KB PAGE    Region 1 under test at level 0 -- RWX permission given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 19: Test in U-Mode | Only V & U bit set at Level 0 | expected = 3 Store page faults
  PTE_SETUP_SV32(rvtest_slvl0_pg_tbl, (PTE_V), va_data, LEVEL1)
  PTE_SETUP_SV32(rvtest_data_1, (PTE_U | PTE_V), va_data, LEVEL0)
  sfence.vma

  TEST_CASES_RUNNER Umode, va_data, LEVEL0, test19

//---------------------------------------------------------------------------------------------------------------------------------
//                    4KB PAGE    Region 1 under test at level 0 -- RWX permission given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 20: Test in U-Mode | Incorrect PTE setup | expected = 3 Store access faults
  PTE_SETUP_SV32(RVMODEL_ACCESS_FAULT_ADDRESS, (PTE_V), va_data, LEVEL1)
  PTE_SETUP_SV32(rvtest_data_1, (PTE_D | PTE_A | PTE_U | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL0)
  sfence.vma

  TEST_CASES_RUNNER_2 Umode, RVMODEL_ACCESS_FAULT_ADDRESS, va_data, LEVEL0, test20

//---------------------------------------------------------------------------------------------------------------------------------
//                    4KB PAGE    Region 1 under test at level 0 -- RWX permission given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 21: Test in U-Mode | RWX bit set | expected = 3 Store access faults
  PTE_SETUP_SV32(rvtest_slvl0_pg_tbl, (PTE_V), va_data, LEVEL1)
  PTE_SETUP_SV32(RVMODEL_ACCESS_FAULT_ADDRESS, (PTE_D | PTE_A | PTE_U | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL0)
  sfence.vma

  TEST_CASES_RUNNER_2 Umode, RVMODEL_ACCESS_FAULT_ADDRESS, va_data, LEVEL0, test21

//---------------------------------------------------------------------------------------------------------------------------------
//                    4KB PAGE    Region 1 under test at level 0 -- RWX permission given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 22: Test in U-Mode | PTE.D set for level 1 PTE | expected = 3 Store page faults
  PTE_SETUP_SV32(rvtest_slvl0_pg_tbl, (PTE_D | PTE_V), va_data, LEVEL1)
  PTE_SETUP_SV32(rvtest_data_1, (PTE_D | PTE_A | PTE_U | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL0)
  sfence.vma

  TEST_CASES_RUNNER Umode, va_data, LEVEL0, test22

//---------------------------------------------------------------------------------------------------------------------------------
//                    4KB PAGE    Region 1 under test at level 0 -- RWX permission given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 23: Test in U-Mode | PTE.A set for level 1 PTE | expected = 3 Store page faults
  PTE_SETUP_SV32(rvtest_slvl0_pg_tbl, (PTE_A | PTE_V), va_data, LEVEL1)
  PTE_SETUP_SV32(rvtest_data_1, (PTE_D | PTE_A | PTE_U | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL0)
  sfence.vma

  TEST_CASES_RUNNER Umode, va_data, LEVEL0, test23

//---------------------------------------------------------------------------------------------------------------------------------
//                    4KB PAGE    Region 1 under test at level 0 -- RWX permission given to the region
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 24: Test in U-Mode | PTE.U set for level 1 PTE | expected = 3 Store page faults
  PTE_SETUP_SV32(rvtest_slvl0_pg_tbl, (PTE_U | PTE_V), va_data, LEVEL1)
  PTE_SETUP_SV32(rvtest_data_1, (PTE_D | PTE_A | PTE_U | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL0)
  sfence.vma

  TEST_CASES_RUNNER Umode, va_data, LEVEL0, test24


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

RVTEST_DATA_END
RVTEST_SIG_SETUP
