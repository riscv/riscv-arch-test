// SPDX-License-Identifier: Apache-2.0
//
// svh_csr_hgatp_fields_RV64_HSmode.S
//   Config : sail-rv64-max | HS writes hgatp; vsatp=Bare
//   Pair   : svh_csr_hgatp_fields_HSmode.S
//
// What this proves (one line):
//   On RV64, from HS, hgatp MODE / PPN / VMID write+read works.
//
// Flow:
//   vsatp=0 → enter HS → poke MODE/VMID/PPN → read back → signatures → PASS/FAIL
//
// Coverpoints mapped (SvH_cg):
//   cp_hgatp_mode_field, cp_hgatp_ppn_field,
//   cp_hgatp_vmidlen_detect, cp_hgatp_vmid_scoping
//

##### START_TEST_CONFIG #####
# REQUIRED_EXTENSIONS: [I, H, Sv39]
# MARCH: rv64ih_zicsr_zifencei
##### END_TEST_CONFIG #####

#define TEST_FILE "svh_csr_hgatp_fields_RV64_HSmode.S"
#define SIGUPD_COUNT 8
#define TRAP_SIGUPD_COUNT 16
#define RVTEST_HYPERVISOR

#include "riscv_arch_test.h"

RVTEST_BEGIN                                    // start test (.text + framework setup)

main:
  LI(a2, 0x257A0120)                            // seed / end marker base

  csrw vsatp, x0                                // VS Bare (partner off)
  hfence.vvma                                   // flush VS-stage TLB

  RVTEST_GOTO_LOWER_MODE HSmode                 // enter HS

  // --- MODE = Sv39x4 ---
  LI(t0, (HGATP_MODE_SV39X4 << 60))             // RV64 MODE in [63:60]
  csrw hgatp, t0                                // write hgatp (G-stage CSR)
  csrr a3, hgatp                                // read hgatp → a3

  // --- MODE walk 0..15 ---
  LI(t3, 0)                                     // bit/index = 0
mode_walk:
  sll t0, t3, 60                                // MODE = t3
  csrw hgatp, t0                                // write hgatp (G-stage CSR)
  addi t3, t3, 1                                // next bit/index
  LI(t4, 16)                                    // loop until 16 MODE values tried
  blt t3, t4, mode_walk                         // repeat until all MODE values tried

  LI(t0, (1 << 60))                             // MODE = 1 sample
  csrw hgatp, t0                                // write hgatp (G-stage CSR)
  csrr a4, hgatp                                // read hgatp → a4

  // --- VMID all-1s + second read ---
  LI(t0, (HGATP_MODE_SV39X4 << 60) | HGATP64_VMID)  // MODE + VMID all-1s
  csrw hgatp, t0                                // write hgatp (G-stage CSR)
  csrr a5, hgatp                                // VMIDLEN sample
  csrr a6, hgatp                                // scoping sample

  // --- PPN all-1s but clear [1:0] (Sv*x4 root align) ---
  LI(t0, (HGATP_MODE_SV39X4 << 60))             // t0 = MODE Sv39x4 only
  LI(t1, -1)                                    // t1 = all ones
  slli t1, t1, 20                               // shift to isolate high bits
  srli t1, t1, 20                               // low 44 bits
  andi t1, t1, -4                               // force PPN[1:0]=0
  or   t0, t0, t1                               // merge MODE with PPN/bit
  csrw hgatp, t0                                // write hgatp (G-stage CSR)

  // --- PPN walking-1 bits 2..43 ---
  LI(t3, 2)                                     // start PPN walk at bit 2 (bits 1:0 often WARL-0)
ppn_walk:
  LI(t0, (HGATP_MODE_SV39X4 << 60))             // t0 = MODE Sv39x4 only
  LI(t1, 1)                                     // t1 = 1 (will shift into one bit)
  sll t1, t1, t3                                // shift 1 into bit position t3
  or  t0, t0, t1                                // merge MODE with PPN/bit
  csrw hgatp, t0                                // write hgatp (G-stage CSR)
  addi t3, t3, 1                                // next bit/index
  LI(t4, 44)                                    // loop until PPN bits done (44)
  blt t3, t4, ppn_walk                          // repeat until all PPN bits tried

  csrr a7, hgatp                                // read hgatp → a7

  RVTEST_GOTO_MMODE                             // return to M-mode

sig_mode:
  RVTEST_SIGUPD(x2, x5, x4, a3, sig_mode, sig_mode_str)  // save register onto signature answer sheet
sig_m1:
  RVTEST_SIGUPD(x2, x5, x4, a4, sig_m1, sig_m1_str)  // save register onto signature answer sheet
sig_vmid:
  RVTEST_SIGUPD(x2, x5, x4, a5, sig_vmid, sig_vmid_str)  // save register onto signature answer sheet
sig_vmid2:
  RVTEST_SIGUPD(x2, x5, x4, a6, sig_vmid2, sig_vmid2_str)  // save register onto signature answer sheet
sig_ppn:
  RVTEST_SIGUPD(x2, x5, x4, a7, sig_ppn, sig_ppn_str)  // save register onto signature answer sheet

done:
  addi a2, a2, 1                                // bump end marker
  RVTEST_SIGUPD(x2, x5, x4, a2, done, done_str) // save register onto signature answer sheet

RVTEST_CODE_END                                 // end executable code
RVTEST_DATA_BEGIN                               // start data / tables
sig_mode_str:  .string "\"cp_hgatp_mode_field Sv39x4\""
sig_m1_str:    .string "\"cp_hgatp_mode_field MODE1\""
sig_vmid_str:  .string "\"cp_hgatp_vmidlen_detect\""
sig_vmid2_str: .string "\"cp_hgatp_vmid_scoping\""
sig_ppn_str:   .string "\"cp_hgatp_ppn_field\""
done_str:      .string "\"done\""
RVTEST_DATA_END                                 // end data section
RVTEST_SIG_SETUP                                // allocate signature answer sheet
