// SPDX-License-Identifier: Apache-2.0
//
// svh_stage_both_bare_sv39_VSmode.S
//   Config : sail-rv64-max | vsatp=Bare + hgatp=Bare
//   Pair   : svh_stage_both_bare_VSmode.S
//
// What this proves (one line):
//   Same as RV32 both_bare: both stages Bare ⇒ VA used as real PA (RV64 build).
//
// Flow:
//   vsatp=0, hgatp=0 → poison mem → VS sw/lw → M checks SPA → signatures
//
// Coverpoints mapped (SvH_cg):
//   stage_both_bare
//
// Note: body matches RV32 twin; only MARCH/XLEN differ.
//

##### START_TEST_CONFIG #####
# REQUIRED_EXTENSIONS: [I, H, Sv39]
# MARCH: rv64ih_zicsr_zifencei
##### END_TEST_CONFIG #####

#define TEST_FILE "svh_stage_both_bare_sv39_VSmode.S"
#define SIGUPD_COUNT 8
#define TRAP_SIGUPD_COUNT 16
#define RVTEST_HYPERVISOR

#include "riscv_arch_test.h"

RVTEST_BEGIN                                    // start test (.text + framework setup)

main:
  LI(a2, 0x257A0020)                            // seed payload

  csrw vsatp, x0                                // VS paging OFF
  csrw hgatp, x0                                // G paging OFF
  hfence.vvma                                   // flush VS-stage TLB
  hfence.gvma                                   // flush G-stage TLB

  LI(t0, 0xDEADBEEF)                            // poison SPA
  la t1, test_region                            // t1 = real address of test_region
  sw t0, 0(t1)                                  // store pattern to memory

  la a5, test_region                            // Bare: this VA is the SPA
  RVTEST_GOTO_LOWER_MODE VSmode                 // enter VS (guest)
  addi a2, a2, 1                                // a2 = 0x257A0021
  sw   a2, 0(a5)                                // store
  nop                                           // pad (trap handler may skip prior insn)
  lw   a3, 0(a5)                                // load → a3
  nop                                           // pad (trap handler may skip prior insn)
  RVTEST_GOTO_MMODE                             // return to M-mode

  la t1, test_region                            // t1 = real address of test_region
  lw t2, 0(t1)                                  // expect 0x257A0021

sig_vs:
  RVTEST_SIGUPD(x2, x5, x4, a3, sig_vs, sig_vs_str)  // save register onto signature answer sheet
sig_pa:
  RVTEST_SIGUPD(x2, x5, x4, t2, sig_pa, sig_pa_str)  // save register onto signature answer sheet

done:
  addi a2, a2, 1                                // bump end marker
  RVTEST_SIGUPD(x2, x5, x4, a2, done, done_str) // save register onto signature answer sheet

RVTEST_CODE_END                                 // end executable code
RVTEST_DATA_BEGIN                               // start data / tables

.align 12                                       // align to 4 KiB page
test_region:
  .word 0                                       // data word (initially 0)
  .word 0                                       // data word (initially 0)
  .word 0                                       // data word (initially 0)
  .word 0                                       // data word (initially 0)

sig_vs_str: .string "\"stage_both_bare: VS lw==sw\""
sig_pa_str: .string "\"stage_both_bare: SPA==sw\""
done_str:   .string "\"done\""

RVTEST_DATA_END                                 // end data section
RVTEST_SIG_SETUP                                // allocate signature answer sheet
