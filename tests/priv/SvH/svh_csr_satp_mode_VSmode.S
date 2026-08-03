// SPDX-License-Identifier: Apache-2.0
//
// svh_csr_satp_mode_VSmode.S
//   Config : sail-rv64-max | VS writes satp MODE
//
// What this proves (one line):
//   In VS, satp.MODE is WARL; satp and vsatp stay aliases.
//
// Flow:
//   map code identity → enter VS → read satp/vsatp → walk MODE 0..15 (restore Sv39) → signatures
//
// Coverpoints mapped (SvH_cg):
//   cp_satp_mode_field
//

##### START_TEST_CONFIG #####
# REQUIRED_EXTENSIONS: [I, H, Sv39]
# MARCH: rv64ih_zicsr_zifencei
##### END_TEST_CONFIG #####

#define TEST_FILE "svh_csr_satp_mode_VSmode.S"
#define SIGUPD_COUNT 8
#define TRAP_SIGUPD_COUNT 32
#define RVTEST_HYPERVISOR

#include "riscv_arch_test.h"

RVTEST_BEGIN                                    // start test (.text + framework setup)

main:
  LI(a2, 0x257A0160)                            // seed / end marker base

  // Keep PC mapped while we change MODE: VA 0x80000000 → real code PA
  .set va_code, 0x0000000080000000

  VS_PTE_SETUP(sv39, PA, rvtest_code_begin, (PTE_D | PTE_A | PTE_X | PTE_R | PTE_W | PTE_V), va_code, LEVEL2)  // map code so MODE flips cannot unmap us
  csrr a0, mscratch                             // needed by V_SAVE_AREA_SETUP
  V_SAVE_AREA_SETUP(va_code, rvtest_code_begin, code, LEVEL2)  // tell framework: VS entry PC = va_code
  VSATP_SETUP(sv39, PA)                         // turn on VS paging (root at PA)
  csrw hgatp, x0                                // G Bare
  hfence.vvma                                   // flush VS-stage TLB
  hfence.gvma                                   // flush G-stage TLB

  RVTEST_GOTO_LOWER_MODE VSmode                 // enter guest VS

  csrr a3, satp                                 // guest sees satp (should be Sv39)
  csrr a4, vsatp                                // vsatp must match (alias)

  // Walk MODE 0..15 but keep same PPN; restore Sv39 each time so PC stays mapped
  csrr t2, satp                                 // save current satp
  li   t0, ~((0xF) << 60)                       // mask to clear MODE nibble
  and  t2, t2, t0                               // strip MODE; keep PPN/ASID
  LI(t3, 0)                                     // bit/index = 0
mode_walk:
  sll  t0, t3, 60                               // candidate MODE
  or   t1, t2, t0                               // combine kept PPN/ASID with MODE
  csrw satp, t1                                 // try that MODE
  csrr a5, satp                                 // WARL sample (last kept in a5)
  li   t0, (SATP_MODE_SV39 << 60)               // put Sv39 back
  or   t1, t2, t0                               // combine kept PPN/ASID with MODE
  csrw satp, t1                                 // restore so next fetch works
  addi t3, t3, 1                                // next bit/index
  LI(t4, 16)                                    // loop until 16 MODE values tried
  blt  t3, t4, mode_walk                        // repeat until all MODE values tried

  csrr a6, satp                                 // final satp after loop

  RVTEST_GOTO_MMODE                             // return to M-mode

sig_sv39:
  RVTEST_SIGUPD(x2, x5, x4, a3, sig_sv39, sig_sv39_str)  // save register onto signature answer sheet
sig_alias:
  RVTEST_SIGUPD(x2, x5, x4, a4, sig_alias, sig_alias_str)  // save register onto signature answer sheet
sig_m1:
  RVTEST_SIGUPD(x2, x5, x4, a5, sig_m1, sig_m1_str)  // save register onto signature answer sheet
sig_m15:
  RVTEST_SIGUPD(x2, x5, x4, a6, sig_m15, sig_m15_str)  // save register onto signature answer sheet

done:
  addi a2, a2, 1                                // bump end marker
  RVTEST_SIGUPD(x2, x5, x4, a2, done, done_str) // save register onto signature answer sheet

RVTEST_CODE_END                                 // end executable code
RVTEST_DATA_BEGIN                               // start data / tables
sig_sv39_str:  .string "\"cp_satp_mode_field: Sv39\""
sig_alias_str: .string "\"cp_satp_mode_field: vsatp alias\""
sig_m1_str:    .string "\"cp_satp_mode_field: MODE1\""
sig_m15_str:   .string "\"cp_satp_mode_field: MODE15\""
done_str:      .string "\"done\""
RVTEST_DATA_END                                 // end data section
RVTEST_SIG_SETUP                                // allocate signature answer sheet
