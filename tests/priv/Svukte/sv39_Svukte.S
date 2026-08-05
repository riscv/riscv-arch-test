// --------------------------------------------------------------------------------------------------------------------------------
// Developed by: Alexander Portland & Noah Rousell
// --------------------------------------------------------------------------------------------------------------------------------
// Test cases are as follows:
// --------------------------------------------------------------------------------------------------------------------------------
// 1. UKTE disabled, no PTE for the top-half virtual address:
//        Then, in U-Mode, execute sw, lw & jalr.
//        Expected: Store-page-fault, Load-page-fault, Fetch-page-fault
// 2. UKTE enabled, no PTE for the top-half virtual address:
//        Then, in U-Mode, execute sw, lw & jalr.
//        Expected: Store-page-fault, Load-page-fault, Fetch-page-fault
// 3. UKTE disabled, valid RWXU PTE for the top-half virtual address:
//        Then, in U-Mode, execute sw, lw & jalr.
//        Expected: All accesses complete successfully
// 4. UKTE enabled, valid RWXU PTE for the top-half virtual address:
//        Then, in U-Mode, execute sw, lw & jalr.
//        Expected: Store-page-fault, Load-page-fault, Fetch-page-fault
// 5. UKTE disabled, no PTE for the lower-half virtual address:
//        Then, in U-Mode, execute sw, lw & jalr.
//        Expected: Store-page-fault, Load-page-fault, Fetch-page-fault
// 6. UKTE enabled, no PTE for the lower-half virtual address:
//        Then, in U-Mode, execute sw, lw & jalr.
//        Expected: Store-page-fault, Load-page-fault, Fetch-page-fault
// 7. UKTE disabled, valid RWXU PTE for the lower-half virtual address:
//        Then, in U-Mode, execute sw, lw & jalr.
//        Expected: All accesses complete successfully
// 8. UKTE enabled, valid RWXU PTE for the lower-half virtual address:
//        Then, in U-Mode, execute sw, lw & jalr.
//        Expected: All accesses complete successfully
// 9. UKTE disabled, valid RWXU PTE for the top-half virtual address:
//        Then, in M-Mode (mstatus.MPRV set, mstatus.MPP=Umode), execute sw & lw.
//        Expected: All accesses complete successfully
// 10. UKTE enabled, valid RWXU PTE for the top-half virtual address:
//        Then, in M-Mode (mstatus.MPRV set, mstatus.MPP=Umode), execute sw & lw.
//        Svukte qualification depends on the *effective* privilege mode, so these
//        accesses are qualified without ever leaving M-Mode.
//        Expected: Store-page-fault, Load-page-fault
// --------------------------------------------------------------------------------------------------------------------------------
// Total Expected Faults :: 17
// --------------------------------------------------------------------------------------------------------------------------------

##### START_TEST_CONFIG #####
# REQUIRED_EXTENSIONS: [I, Sv39, Svukte]
# MARCH: rv64i_zicsr_zifencei
##### END_TEST_CONFIG #####

#define SIGUPD_COUNT 28
#define TRAP_SIGUPD_COUNT 80


#include "riscv_arch_test.h"

RVTEST_BEGIN

//---------------------------------------------------------------------------------------------------------------------------------
// Set mstatus.MPRV=1 and mstatus.MPP=Umode, so that M-mode loads and stores are
// translated and protected as though the current privilege mode were U.
//
// This must be re-applied before every access under test: a trap taken to M-mode
// overwrites mstatus.MPP with the interrupted privilege mode, so the pair does not
// survive a faulting access.
.macro SET_MPRV_UMODE
  LI(   t0, MSTATUS_MPRV)
  csrs  mstatus, t0           // mstatus.MPRV = 1
  LI(   t0, MSTATUS_MPP)
  csrc  mstatus, t0           // mstatus.MPP  = Umode (0b00)
.endm

// Test RWX permissions
//
// When MPRV=1 the accesses execute in M-mode with an effective privilege of U, so
// mstatus.MPRV/MPP are re-established before each one. The execute case is skipped
// in that mode because mstatus.MPRV does not affect instruction fetch.
.macro VERIFICATION_RWX TEST_CASE, MPRV=0
  addi a2, a2, 16

  // Test store permission
  .if \MPRV
    SET_MPRV_UMODE
  .endif
  \TEST_CASE\()_store:
  sw  a2, 20(a5)
  nop

  // Test load permission
  .if \MPRV
    SET_MPRV_UMODE
  .endif
  \TEST_CASE\()_load:
  lw a3, 20(a5)
  nop

  .if \MPRV == 0
    // Test execute permission
    \TEST_CASE\()_exec:
    jalr ra, a5, 0
    nop
  .endif
.endm

// Pass MPRV=1 to run the accesses from M-mode with an effective privilege of U
// (mstatus.MPRV set, mstatus.MPP=Umode) instead of dropping into U-mode.
.macro TEST_CASES_RUNNER QUAL, VA, level, TEST_CASE, MPRV=0

  // Set or clear senvcfg.UKTE for this test case.
  LI(t0, SENVCFG_UKTE)
  .ifc \QUAL, Qualified
    csrs senvcfg, t0
  .else
    csrc senvcfg, t0
  .endif

  // Adjust offset of VA to point to the test region.
  .set VA_SHIFT, (\level*9)+12
  LI(a5, (\VA>>VA_SHIFT)<<VA_SHIFT)
  LA(a0, rvtest_data_1)
  slli a0, a0, 64-VA_SHIFT
  srli a0, a0, 64-VA_SHIFT
  add  a5, a5, a0             // Virtual Address

  // Initialize result registers so a fault leaves their sentinels unchanged.
  LI(a3, 0xdeadbeef)
  LI(a4, 0xdeadbeef)

  .if \MPRV
    // Stay in M-mode; the effective privilege of each access comes from
    // mstatus.MPRV/MPP instead.
    VERIFICATION_RWX \TEST_CASE, \MPRV

    // Clear mstatus.MPRV so the signature stores below are translated as M-mode
    // accesses rather than being Svukte-qualified themselves.
    LI(   t0, MSTATUS_MPRV)
    csrc  mstatus, t0
  .else
    RVTEST_GOTO_LOWER_MODE Umode

    VERIFICATION_RWX \TEST_CASE, \MPRV

    RVTEST_GOTO_MMODE
  .endif

  // Signature Update
  RVTEST_SIGUPD(x2, x5, x4, a2, \TEST_CASE\()_store, \TEST_CASE\()_store_str)
  RVTEST_SIGUPD(x2, x5, x4, a3, \TEST_CASE\()_load, \TEST_CASE\()_load_str)
  .if \MPRV == 0
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_exec, \TEST_CASE\()_exec_str)
  .endif
.endm


main:
  LI( a2, 0x800)            // Test signature initialization

//---------------------------------------------------------------------------------------------------------------------------------
//                                   Virtual addresses definition for code and test regions
//---------------------------------------------------------------------------------------------------------------------------------

  // Virtual address in the supervisor half (VA >= 2^(SXLEN-1)).
  .set va_data, 0xFFFFFFC000000000

  // Virtual Address for code region
  .set va_rvtest_code_begin,  0x180000000

  // PTE setup for Code Region
  SUPERPAGE_PTE_SETUP_SV39(rvtest_code_begin, (PTE_D | PTE_A | PTE_U | PTE_X | PTE_R | PTE_V), va_rvtest_code_begin, LEVEL2)
  sfence.vma

  // Save area setup for code region
  csrr a0, mscratch
  SAVE_AREA_SETUP(va_rvtest_code_begin, rvtest_code_begin, code, LEVEL2)

//---------------------------------------------------------------------------------------------------------------------------------
//                                               Test Cases Start from here
//---------------------------------------------------------------------------------------------------------------------------------

  SATP_SETUP_RV64(sv39)                                                  // Set SATP for virtualization
  sfence.vma                                                             // Flush TLB

//---------------------------------------------------------------------------------------------------------------------------------
//                                                    TESTS WITHOUT A DATA PTE
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 1: UKTE disabled | Test in U-Mode | no PTE | expected = RWX fault
  TEST_CASES_RUNNER Unqualified, va_data, LEVEL2, test1

  // Test case 2: UKTE enabled | Test in U-Mode | no PTE | expected = RWX fault
  TEST_CASES_RUNNER Qualified, va_data, LEVEL2, test2

//---------------------------------------------------------------------------------------------------------------------------------
//                                                    TESTS WITH A VALID DATA PTE
//---------------------------------------------------------------------------------------------------------------------------------

  // Valid RWXU PTE for the top-half test region.
  SUPERPAGE_PTE_SETUP_SV39(rvtest_data_1, (PTE_D | PTE_A | PTE_U | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL2)
  sfence.vma

  // Test case 3: UKTE disabled | Test in U-Mode | valid RWXU PTE | expected = no fault
  TEST_CASES_RUNNER Unqualified, va_data, LEVEL2, test3

  // Test case 4: UKTE enabled | Test in U-Mode | valid RWXU PTE | expected = RWX fault
  TEST_CASES_RUNNER Qualified, va_data, LEVEL2, test4

//---------------------------------------------------------------------------------------------------------------------------------
//                             MACHINE-MODE TESTS WITH MPRV (effective privilege = Umode)
//
// The PTE installed above is still in effect, so it grants RWXU on the top-half
// region. Any fault below is therefore attributable only to Svukte, not to the
// page-table contents.
//---------------------------------------------------------------------------------------------------------------------------------

  // Test case 9: UKTE disabled | Test in M-Mode w/ MPRV | valid RWXU PTE | expected = no fault
  TEST_CASES_RUNNER Unqualified, va_data, LEVEL2, test9, 1

  // Test case 10: UKTE enabled | Test in M-Mode w/ MPRV | valid RWXU PTE | expected = RW fault
  TEST_CASES_RUNNER Qualified, va_data, LEVEL2, test10, 1

//---------------------------------------------------------------------------------------------------------------------------------
//                                                    TESTS IN THE LOWER HALF
//---------------------------------------------------------------------------------------------------------------------------------

  // Virtual address in the lower, canonical half of the Sv39 address space.
  .set va_data_lower, 0x0000000040000000

  // Test case 5: UKTE disabled | Test in U-Mode | no PTE | expected = RWX fault
  TEST_CASES_RUNNER Unqualified, va_data_lower, LEVEL2, test5

  // Test case 6: UKTE enabled | Test in U-Mode | no PTE | expected = RWX fault
  // UKTE does not change accesses below 2^(SXLEN-1).
  TEST_CASES_RUNNER Qualified, va_data_lower, LEVEL2, test6

  // Valid RWXU PTE for the lower-half test region.
  SUPERPAGE_PTE_SETUP_SV39(rvtest_data_1, (PTE_D | PTE_A | PTE_U | PTE_X | PTE_W | PTE_R | PTE_V), va_data_lower, LEVEL2)
  sfence.vma

  // Test case 7: UKTE disabled | Test in U-Mode | valid RWXU PTE | expected = no fault
  TEST_CASES_RUNNER Unqualified, va_data_lower, LEVEL2, test7

  // Test case 8: UKTE enabled | Test in U-Mode | valid RWXU PTE | expected = no fault
  // UKTE does not change accesses below 2^(SXLEN-1).
  TEST_CASES_RUNNER Qualified, va_data_lower, LEVEL2, test8

//---------------------------------------------------------------------------------------------------------------------------------
RVTEST_CODE_END
RVTEST_DATA_BEGIN

//---------------------------------------------------------------------------------------------------------------------------------

.p2align 12
rvtest_data_1:
  nop
  addi a4, a2, 4
  jr ra
  nop
  .word 0xbeefcaf1          // Random word
  .word 0xbeefcaf2          // Random word
  nop
  jr ra

// Page Tables
.p2align 12
rvtest_slvl0_pg_tbl:
    .skip(4096)
rvtest_slvl1_pg_tbl:
    .skip(4096)

test1_store_str: .string "\"Mismatch during sw in Test Case 1!\""
test1_load_str:  .string "\"Mismatch during lw in Test Case 1!\""
test1_exec_str:  .string "\"Mismatch during jalr in Test Case 1!\""
test2_store_str: .string "\"Mismatch during sw in Test Case 2!\""
test2_load_str:  .string "\"Mismatch during lw in Test Case 2!\""
test2_exec_str:  .string "\"Mismatch during jalr in Test Case 2!\""
test3_store_str: .string "\"Mismatch during sw in Test Case 3!\""
test3_load_str:  .string "\"Mismatch during lw in Test Case 3!\""
test3_exec_str:  .string "\"Mismatch during jalr in Test Case 3!\""
test4_store_str: .string "\"Mismatch during sw in Test Case 4!\""
test4_load_str:  .string "\"Mismatch during lw in Test Case 4!\""
test4_exec_str:  .string "\"Mismatch during jalr in Test Case 4!\""
test5_store_str: .string "\"Mismatch during sw in Test Case 5!\""
test5_load_str:  .string "\"Mismatch during lw in Test Case 5!\""
test5_exec_str:  .string "\"Mismatch during jalr in Test Case 5!\""
test6_store_str: .string "\"Mismatch during sw in Test Case 6!\""
test6_load_str:  .string "\"Mismatch during lw in Test Case 6!\""
test6_exec_str:  .string "\"Mismatch during jalr in Test Case 6!\""
test7_store_str: .string "\"Mismatch during sw in Test Case 7!\""
test7_load_str:  .string "\"Mismatch during lw in Test Case 7!\""
test7_exec_str:  .string "\"Mismatch during jalr in Test Case 7!\""
test8_store_str: .string "\"Mismatch during sw in Test Case 8!\""
test8_load_str:  .string "\"Mismatch during lw in Test Case 8!\""
test8_exec_str:  .string "\"Mismatch during jalr in Test Case 8!\""
test9_store_str:  .string "\"Mismatch during sw in Test Case 9!\""
test9_load_str:   .string "\"Mismatch during lw in Test Case 9!\""
test10_store_str: .string "\"Mismatch during sw in Test Case 10!\""
test10_load_str:  .string "\"Mismatch during lw in Test Case 10!\""

RVTEST_DATA_END
RVTEST_SIG_SETUP
