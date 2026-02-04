// --------------------------------------------------------------------------------------------------------------------------------
// Developed by: Umer Shahid, Muhammad Zain, Hamza Ali, Muhammad Abdullah and Muhammad Ahmed
// --------------------------------------------------------------------------------------------------------------------------------
// Test cases are as follows:
// --------------------------------------------------------------------------------------------------------------------------------
// 1. mstatus.MPRV set, mstatus.MPP = S-mode and virtualization is not enabled (Bare Mode):
//        Then, in M-Mode, Load, Store & Execute is performed --> required: No Fault
// 2. mstatus.MPRV set, mstatus.MPP = U-mode and virtualization is not enabled (Bare Mode):
//        Then, in M-Mode, Load, Store & Execute is performed --> required: No Fault
//
// Total Expected Faults :: 0
//---------------------------------------------------------------------------------------------------------------------------------

##### START_TEST_CONFIG #####
# REQUIRED_EXTENSIONS: [I, S]
# MARCH: rv64i_zicsr
# CONFIG_DEPENDENT: true
##### END_TEST_CONFIG #####

#define TEST_FILE "vm_mstatus_mprv_satp_bare_mode.S"
#define SIGUPD_COUNT 50
#define rvtest_mtrap_routine
#define rvtest_strap_routine
#define SKIP_MEPC
#define SKIP_MTVAL

#include "riscv_arch_test.h"

RVTEST_BEGIN

//---------------------------------------------------------------------------------------------------------------------------------
// Test RWX permissions
.macro VERIFICATION_RWX STR_PTR
  // As we are in bare mode, we will test using physical address
  LA(  a5, rvtest_data_1)
  addi a2, a2, 16

  // Test store permission
  sw  a2, 20(a5)
  nop
  RVTEST_SIGUPD(x2, x5, x4, a2, \STR_PTR)

  // Test load permission
  lw  a4, 20(a5)
  nop
  RVTEST_SIGUPD(x2, x5, x4, a4, \STR_PTR)

  // Test execute permission
  LI(  x4, 0xACCE)            // Store a value which is to be checked in trap handler
  jalr ra, a5, 0
  nop
.endm


main:
  li a2, 0x800                // Test signature initialization

//---------------------------------------------------------------------------------------------------------------------------------
// Test case 1: Set mstatus.MPRV and set mstatus.MPP to S Mode
//---------------------------------------------------------------------------------------------------------------------------------

  LI(   t0, MSTATUS_MPRV)
  CSRS( mstatus, t0)
  LI(   t0, 0x1800)
  CSRC( mstatus, t0)
  LI(   t0, 0x800)
  CSRS( mstatus, t0)          // Set to Smode

  RVTEST_SIGUPD_CSR_READ(mstatus, a4, "test_1")

  // Verify Load, Store & Execute in Bare mode
  VERIFICATION_RWX "test_1"

  RVTEST_GOTO_MMODE

//---------------------------------------------------------------------------------------------------------------------------------
// Test case 2: Set mstatus.MPRV and set mstatus.MPP to U Mode
//---------------------------------------------------------------------------------------------------------------------------------

  LI(   s7, MSTATUS_MPRV)
  CSRS( mstatus, s7)
  LI(   s7, 0x1800)
  CSRC( mstatus, s7)          // Set to Umode

  RVTEST_SIGUPD_CSR_READ(mstatus, a4, "test_2")

  // Verify Load, Store & Execute in Bare mode
  VERIFICATION_RWX "test_2"

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
  addi ra, ra, 4
  jr ra
  nop
  .word 0xbeefcaf1          // Random word
  .word 0xbeefcaf2          // Random word
  nop
  jr ra

//---------------------------------------------------------------------------------------------------------------------------------

canary_mismatch: .string "Testcase signature canary mismatch!"
test_1: .string "\"Mismatch in Test Case 1!\""
test_2: .string "\"Mismatch in Test Case 2!\""

RVTEST_DATA_END
RVTEST_SIG_SETUP
