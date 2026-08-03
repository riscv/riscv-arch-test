// SPDX-License-Identifier: Apache-2.0
//
// svh_tvm_hgatp_HSmode.S
//   Config : sail-rv32-max | HS hgatp access × mstatus.TVM
//
// What this proves (one line):
//   TVM=0 → HS may write hgatp; TVM=1 → that write is illegal.
//
// Flow:
//   TVM=0 + HS csrw hgatp OK → TVM=1 + HS csrw hgatp faults → signatures
//
// Coverpoints mapped (SvH_cg):
//   cp_hgatp_tvm_effects
//
// Words: TVM = "Trap Virtual Memory" bit in mstatus; when 1, HS satp/hgatp access traps
//

##### START_TEST_CONFIG #####
# REQUIRED_EXTENSIONS: [I, H, Sv32]
# MARCH: rv32ih_zicsr_zifencei
##### END_TEST_CONFIG #####

#define TEST_FILE "svh_tvm_hgatp_HSmode.S"
#define SIGUPD_COUNT 16
#define TRAP_SIGUPD_COUNT 256
#define RVTEST_HYPERVISOR

#include "riscv_arch_test.h"

RVTEST_BEGIN                                    // start test (.text + framework setup)

main:
  LI(a2, 0x257A0130)                            // seed / end marker base

  csrw vsatp, x0                                // clear vsatp
  csrw hgatp, x0                                // clear hgatp
  csrw medeleg, x0                              // keep traps in M (simpler)
  csrw hedeleg, x0                              // do not delegate to HS/VS

  // ========== Case A: TVM=0 → write hgatp is allowed ==========
  LI(t0, MSTATUS_TVM)                           // t0 = TVM bit mask
  csrc mstatus, t0                              // clear TVM bit
  RVTEST_GOTO_LOWER_MODE HSmode                 // enter HS
  LI(t0, (HGATP_MODE_SV32X4 << 31))             // t0 = MODE Sv32x4 only
  csrw hgatp, t0                                // should succeed
  csrr a3, hgatp                                // readback → a3
  RVTEST_GOTO_MMODE                             // return to M-mode

  // ========== Case B: TVM=1 → write hgatp is illegal ==========
  LI(t0, MSTATUS_TVM)                           // t0 = TVM bit mask
  csrs mstatus, t0                              // set TVM
  LI(a4, 0x257A0131)                            // marker before the illegal write
  RVTEST_GOTO_LOWER_MODE HSmode                 // enter HS (host supervisor)
  csrw hgatp, x0                                // illegal; trap handler skips this insn
  nop                                           // pad after possible skip
  addi a4, a4, 1                                // if we continued → 0x257A0132
  RVTEST_GOTO_MMODE                             // return to M-mode

  LI(t0, MSTATUS_TVM)                           // t0 = TVM bit mask
  csrc mstatus, t0                              // clear TVM again (tidy)

sig_tvm0:
  RVTEST_SIGUPD(x2, x5, x4, a3, sig_tvm0, sig_tvm0_str)  // hgatp after legal write
sig_tvm1:
  RVTEST_SIGUPD(x2, x5, x4, a4, sig_tvm1, sig_tvm1_str)  // survived illegal path

done:
  addi a2, a2, 1                                // bump end marker
  RVTEST_SIGUPD(x2, x5, x4, a2, done, done_str) // save register onto signature answer sheet

RVTEST_CODE_END                                 // end executable code
RVTEST_DATA_BEGIN                               // start data / tables
sig_tvm0_str: .string "\"cp_hgatp_tvm_effects: TVM0\""
sig_tvm1_str: .string "\"cp_hgatp_tvm_effects: TVM1\""
done_str:     .string "\"done\""
RVTEST_DATA_END                                 // end data section
RVTEST_SIG_SETUP                                // allocate signature answer sheet
