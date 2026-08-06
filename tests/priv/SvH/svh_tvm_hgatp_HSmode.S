// --------------------------------------------------------------------------------------------------------------------------------
// svh_tvm_hgatp_HSmode.S
// Config: sail-rv32-max | HS hgatp access × mstatus.TVM
// Pair:   svh_tvm_hgatp_RV64_HSmode.S
// Coverpoints mapped (SvH_cg): cp_hgatp_tvm_effects
// What this proves (one line):
//   mstatus.TVM=1 makes HS hgatp writes illegal; TVM=0 allows them.
// --------------------------------------------------------------------------------------------------------------------------------
// Test cases are as follows:
// --------------------------------------------------------------------------------------------------------------------------------
//  1. TVM=0: HS write hgatp.MODE=Sv32x4 → Successful (readback)
//  2. TVM=1: HS write hgatp illegal → Expected Fault (marker unchanged)
//
// Total Expected Faults :: 1
// --------------------------------------------------------------------------------------------------------------------------------

##### START_TEST_CONFIG #####
# REQUIRED_EXTENSIONS: [I, H, Sv32]
# MARCH: rv32ih_zicsr_zifencei
##### END_TEST_CONFIG #####

#define TEST_FILE "svh_tvm_hgatp_HSmode.S"
#define SIGUPD_COUNT 2
#define TRAP_SIGUPD_COUNT 256
#define RVTEST_HYPERVISOR

// Mode hops (T-SBI) — return-to-M always uses RVTEST_TSBI_GOTO_MMODE (ecall a0=1;
//   handler rtn2mmode relocates EPC VA→PA). Enter:
//   • Code at PA / identity: RVTEST_TSBI_GOTO_VSMODE / _SMODE (ecall a0=4/2)
//   • Guest code VA≠PA (V_SAVE_AREA_*): RVTEST_GOTO_LOWER_MODE (mret + PA↔VA relocate)
#include "riscv_arch_test.h"

RVTEST_BEGIN

main:
  // ---- Setup: both stages Bare; traps stay in M (no delegation) ----
  csrw vsatp, x0                                // clear vsatp
  csrw hgatp, x0                                // clear hgatp
  csrw medeleg, x0                              // keep traps in M (simpler TVM fault handling)
  csrw hedeleg, x0                              // do not delegate to HS/VS

//---------------------------------------------------------------------------------------------------------------------------------
// Test case 1: TVM=0 write hgatp allowed | Expected: Successful
//---------------------------------------------------------------------------------------------------------------------------------
  // cp_hgatp_tvm_effects bin: TVM=0 allows HS to write hgatp
  LI(t0, MSTATUS_TVM)                           // t0 = TVM bit mask
  csrc mstatus, t0                              // clear TVM bit
  RVTEST_TSBI_GOTO_SMODE                       // T-SBI: ecall a0=2 → HS/S (code at PA / identity)
  LI(t0, (HGATP_MODE_SV32X4 << 31))             // t0 = MODE Sv32x4 only
  csrw hgatp, t0                                // should succeed
  test1_hgatp:
  RVTEST_SIGUPD_CSR_READ(hgatp, a4, test1_hgatp, test1_hgatp_str)  // signature: read hgatp after TVM=0 write
  RVTEST_TSBI_GOTO_MMODE                       // T-SBI: ecall a0=1 → M (rtn2mmode VA→PA relocate)

//---------------------------------------------------------------------------------------------------------------------------------
// Test case 2: TVM=1 write hgatp illegal | Expected: Expected Fault
//---------------------------------------------------------------------------------------------------------------------------------
  // cp_hgatp_tvm_effects bin: TVM=1 makes HS hgatp write illegal (virtual instruction trap)
  LI(t0, MSTATUS_TVM)                           // t0 = TVM bit mask
  csrs mstatus, t0                              // set TVM
  LI(a4, 0x257A0131)                            // marker: stays 0x257A0131 if csrw is skipped by trap
  RVTEST_TSBI_GOTO_SMODE                       // T-SBI: ecall a0=2 → HS/S (code at PA / identity)
  csrw hgatp, x0                                // illegal; trap handler skips this insn
  nop                                           // pad after possible skip
  addi a4, a4, 1                                // if we continued → 0x257A0132
  RVTEST_TSBI_GOTO_MMODE                       // T-SBI: ecall a0=1 → M (rtn2mmode VA→PA relocate)

  LI(t0, MSTATUS_TVM)                           // t0 = TVM bit mask
  csrc mstatus, t0                              // clear TVM again (tidy)

  test2_marker:
  RVTEST_SIGUPD(x2, x5, x4, a4, test2_marker, test2_marker_str)  // signature: marker proves TVM=1 blocked csrw

//---------------------------------------------------------------------------------------------------------------------------------
RVTEST_CODE_END
RVTEST_DATA_BEGIN
// PASS/FAIL message strings for signature compares

test1_hgatp_str:  .string "\"Mismatch on hgatp write with TVM=0 in Test Case 1!\""
test2_marker_str: .string "\"Mismatch on TVM=1 illegal hgatp write marker in Test Case 2!\""

RVTEST_DATA_END
RVTEST_SIG_SETUP
