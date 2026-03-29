// --------------------------------------------------------------------------------------------------------------------------------
// Developed by: Umer Shahid & Muhammad Zain
// --------------------------------------------------------------------------------------------------------------------------------
// Test cases are as follows:
// --------------------------------------------------------------------------------------------------------------------------------
// 1. mstatus.MPRV set, mstatus.MPP = S-mode and virtualization is disabled (satp.MODE = Bare):
// 2. mstatus.MPRV set, mstatus.MPP = U-mode and virtualization is disabled (satp.MODE = Bare):
//
// Total Expected Faults :: 0
//---------------------------------------------------------------------------------------------------------------------------------

##### START_TEST_CONFIG #####
# REQUIRED_EXTENSIONS: [I, S]
# MARCH: rv${XLEN}i_zicsr
# CONFIG_DEPENDENT: true
##### END_TEST_CONFIG #####

#define TEST_FILE "Svbare_mstatus_mprv.S"
#define SIGUPD_COUNT 15
#define TRAP_SIGUPD_COUNT 10
#define rvtest_mtrap_routine
#define rvtest_strap_routine
#define RVTEST_PRIV_TEST
#define SKIP_MEPC

#include "riscv_arch_test.h"

RVTEST_BEGIN

//---------------------------------------------------------------------------------------------------------------------------------
// Test RWX permissions
.macro VERIFICATION_RWX TEST_CASE
  LA(  a5, rvtest_data_1)     // Load Physical Address
  addi a2, a2, 16

  // Test store permission
  \TEST_CASE\()_store:
  sw  a2, 20(a5)
  nop

  // Test load permission
  \TEST_CASE\()_load:
  lw  a3, 20(a5)
  nop

  // Test execute permission
  \TEST_CASE\()_exec:
  jalr ra, a5, 0
  nop

  // Signature Update
  RVTEST_SIGUPD(x2, x5, x4, a2, \TEST_CASE\()_store, \TEST_CASE\()_store_str)
  RVTEST_SIGUPD(x2, x5, x4, a3, \TEST_CASE\()_load, \TEST_CASE\()_load_str)
  RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_exec, \TEST_CASE\()_exec_str)
.endm


main:
  LI( a2, 0x800)              // Test signature initialization

  #if __riscv_xlen == 64
    LI( a0, 0x0123456789ABCDEF)
  #else
    LI( a0, 0x789ABCDE)
  #endif

  CSRW(satp, a0)              // Set satp.MODE = Bare
  
  satp_bare:
  RVTEST_SIGUPD_CSR_READ(satp, a4, satp_bare, satp_bare_str)

//---------------------------------------------------------------------------------------------------------------------------------
// Test case 1: Set mstatus.MPRV and set mstatus.MPP to S-Mode
//---------------------------------------------------------------------------------------------------------------------------------

  LI(   t0, MSTATUS_MPRV)
  CSRS( mstatus, t0)
  LI(   t0, 0x1800)
  CSRC( mstatus, t0)
  LI(   t0, 0x800)
  CSRS( mstatus, t0)          // Set to Smode

  test1_mstatus:
  RVTEST_SIGUPD_CSR_READ(mstatus, a4, test1_mstatus, test1_mstatus_str)

  VERIFICATION_RWX test1

  RVTEST_GOTO_MMODE

//---------------------------------------------------------------------------------------------------------------------------------
// Test case 2: Set mstatus.MPRV and set mstatus.MPP to U-Mode
//---------------------------------------------------------------------------------------------------------------------------------

  LI(   s7, MSTATUS_MPRV)
  CSRS( mstatus, s7)
  LI(   s7, 0x1800)
  CSRC( mstatus, s7)          // Set to Umode

  test2_mstatus:
  RVTEST_SIGUPD_CSR_READ(mstatus, a4, test2_mstatus, test2_mstatus_str)

  VERIFICATION_RWX test2

  RVTEST_GOTO_MMODE


//---------------------------------------------------------------------------------------------------------------------------------
RVTEST_CODE_END
RVTEST_DATA_BEGIN

//---------------------------------------------------------------------------------------------------------------------------------
//                                            PHYSICAL ADDRESS REGION FOR TESTING
//---------------------------------------------------------------------------------------------------------------------------------
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

satp_bare_str:     .string "\"Mismatch in satp value!\""
test1_mstatus_str: .string "\"Mismatch in mstatus value in Test Case 1!\""
test1_store_str:   .string "\"Mismatch during sw in Test Case 1!\""
test1_load_str:    .string "\"Mismatch during lw in Test Case 1!\""
test1_exec_str:    .string "\"Mismatch during jalr in Test Case 1!\""
test2_mstatus_str: .string "\"Mismatch in mstatus value in Test Case 2!\""
test2_store_str:   .string "\"Mismatch during sw in Test Case 2!\""
test2_load_str:    .string "\"Mismatch during lw in Test Case 2!\""
test2_exec_str:    .string "\"Mismatch during jalr in Test Case 2!\""

RVTEST_DATA_END
RVTEST_SIG_SETUP
