// SPDX-License-Identifier: Apache-2.0
//
// svh_csr_vsatp_fields_RV64_HSmode.S
//   Config : sail-rv64-max | HS writes vsatp; hgatp=Bare
//   Pair   : svh_csr_vsatp_fields_HSmode.S
//
// What this proves (one line):
//   On RV64, from HS, vsatp MODE / PPN / ASID write+read works (CSR knobs only).
//
// Flow:
//   hgatp=0 → enter HS → poke MODE/ASID/PPN → read back → signatures → PASS/FAIL
//
// Coverpoints mapped (SvH_cg):
//   cp_vsatp_mode_field, cp_vsatp_ppn_field, cp_vsatp_asidlen_detect
//
// Words: CSR=settings knob; HS=host supervisor; Bare=paging off;
//        MODE bits on RV64 are [63:60]; PPN is wider (44b for Sv39)
//

##### START_TEST_CONFIG #####
# REQUIRED_EXTENSIONS: [I, H, Sv39]
# MARCH: rv64ih_zicsr_zifencei
##### END_TEST_CONFIG #####

#define TEST_FILE "svh_csr_vsatp_fields_RV64_HSmode.S"
#define SIGUPD_COUNT 8
#define TRAP_SIGUPD_COUNT 16
#define RVTEST_HYPERVISOR

#include "riscv_arch_test.h"

RVTEST_BEGIN                                    // start test (.text + framework setup)

main:
  LI(a2, 0x257A0110)                            // seed / end marker base

  csrw hgatp, x0                                // G-stage Bare (partner off)
  hfence.gvma                                   // flush G TLB

  RVTEST_GOTO_LOWER_MODE HSmode                 // enter HS

  // --- MODE = Sv39; read back ---
  LI(t0, (SATP_MODE_SV39 << 60))                // RV64: MODE in bits [63:60]
  csrw vsatp, t0                                // write guest satp-like CSR
  csrr a3, vsatp                                // read back → a3

  // --- Try MODE encodings 0..15 (WARL: illegal may be ignored) ---
  LI(t3, 0)                                     // bit/index = 0
mode_walk:
  sll t0, t3, 60                                // put t3 into MODE field
  csrw vsatp, t0                                // write that MODE
  addi t3, t3, 1                                // next bit/index
  LI(t4, 16)                                    // loop until 16 MODE values tried
  blt t3, t4, mode_walk                         // 16 tries

  LI(t0, (1 << 60))                             // MODE = 1 sample
  csrw vsatp, t0                                // write vsatp (guest page-table CSR)
  csrr a4, vsatp                                // readback → a4

  // --- ASID all-1s (measure ASIDLEN) ---
  LI(t0, (SATP_MODE_SV39 << 60) | SATP64_ASID)  // Sv39 + every ASID bit
  csrw vsatp, t0                                // write vsatp (guest page-table CSR)
  csrr a5, vsatp                                // which ASID bits stuck?

  // --- PPN all-1s (44 bits) + Sv39 ---
  LI(t0, (SATP_MODE_SV39 << 60))                // t0 = MODE Sv39 only
  LI(t1, -1)                                    // t1 = all ones
  slli t1, t1, 20                               // shift to isolate high bits
  srli t1, t1, 20                               // keep low 44 bits = 1
  or   t0, t0, t1                               // merge MODE with PPN/bit
  csrw vsatp, t0                                // write vsatp (guest page-table CSR)

  // --- PPN walking-1 bits 0..43 ---
  LI(t3, 0)                                     // bit/index = 0
ppn_walk:
  LI(t0, (SATP_MODE_SV39 << 60))                // MODE only
  LI(t1, 1)                                     // t1 = 1 (will shift into one bit)
  sll t1, t1, t3                                // one PPN bit
  or  t0, t0, t1                                // merge MODE with PPN/bit
  csrw vsatp, t0                                // write vsatp (guest page-table CSR)
  addi t3, t3, 1                                // next bit/index
  LI(t4, 44)                                    // loop until PPN bits done (44)
  blt t3, t4, ppn_walk                          // repeat until all PPN bits tried

  csrr a6, vsatp                                // final after walk

  RVTEST_GOTO_MMODE                             // return to M-mode

sig_mode:
  RVTEST_SIGUPD(x2, x5, x4, a3, sig_mode, sig_mode_str)  // Sv39 MODE sample
sig_m1:
  RVTEST_SIGUPD(x2, x5, x4, a4, sig_m1, sig_m1_str)      // MODE=1 sample
sig_asid:
  RVTEST_SIGUPD(x2, x5, x4, a5, sig_asid, sig_asid_str)  // ASIDLEN sample
sig_ppn:
  RVTEST_SIGUPD(x2, x5, x4, a6, sig_ppn, sig_ppn_str)    // PPN walk end

done:
  addi a2, a2, 1                                // bump end marker
  RVTEST_SIGUPD(x2, x5, x4, a2, done, done_str) // save register onto signature answer sheet

RVTEST_CODE_END                                 // end executable code
RVTEST_DATA_BEGIN                               // start data / tables
sig_mode_str: .string "\"cp_vsatp_mode_field Sv39\""
sig_m1_str:   .string "\"cp_vsatp_mode_field MODE1\""
sig_asid_str: .string "\"cp_vsatp_asidlen_detect\""
sig_ppn_str:  .string "\"cp_vsatp_ppn_field\""
done_str:     .string "\"done\""
RVTEST_DATA_END                                 // end data section
RVTEST_SIG_SETUP                                // allocate signature answer sheet
