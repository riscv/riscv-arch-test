// SPDX-License-Identifier: Apache-2.0
//
// svh_csr_hgatp_fields_HSmode.S
//   Config : sail-rv32-max | HS writes hgatp; vsatp=Bare
//   Pair   : svh_csr_hgatp_fields_RV64_HSmode.S
//
// What this proves (one line):
//   From HS, hgatp MODE / PPN / VMID can be written and read back.
//
// Flow:
//   vsatp=0 → enter HS → poke hgatp fields → read back → signatures → PASS/FAIL
//
// Coverpoints mapped (SvH_cg):
//   cp_hgatp_mode_field, cp_hgatp_ppn_field,
//   cp_hgatp_vmidlen_detect, cp_hgatp_vmid_scoping
//
// Words: hgatp=hypervisor (G-stage) page-table CSR; VMID=like ASID for guests
//

##### START_TEST_CONFIG #####
# REQUIRED_EXTENSIONS: [I, H, Sv32]
# MARCH: rv32ih_zicsr_zifencei
##### END_TEST_CONFIG #####

#define TEST_FILE "svh_csr_hgatp_fields_HSmode.S"
#define SIGUPD_COUNT 8
#define TRAP_SIGUPD_COUNT 16
#define RVTEST_HYPERVISOR

#include "riscv_arch_test.h"

RVTEST_BEGIN                                    // start test (.text + framework setup)

main:
  LI(a2, 0x257A0120)                            // seed / end marker base

  // --- Partner stage off (sheet rule for hgatp CSR tests) ---
  csrw vsatp, x0                                // vsatp Bare (no VS walk)
  hfence.vvma                                   // flush VS TLB

  RVTEST_GOTO_LOWER_MODE HSmode                 // enter HS

  // --- MODE = Sv32x4; read back ---
  LI(t0, (HGATP_MODE_SV32X4 << 31))             // G-stage Sv32x4 MODE
  csrw hgatp, t0                                // write hgatp (G-stage CSR)
  csrr a3, hgatp                                // MODE sample → a3

  // --- PPN = 0 with Sv32x4 ---
  LI(t0, (HGATP_MODE_SV32X4 << 31))             // t0 = MODE Sv32x4 only
  csrw hgatp, t0                                // write hgatp (G-stage CSR)
  csrr a4, hgatp                                // zero-PPN sample → a4

  // --- VMID all-1s (VMIDLEN) + second read (scoping) ---
  LI(t0, (HGATP_MODE_SV32X4 << 31) | HGATP32_VMID)  // MODE + VMID all-1s
  csrw hgatp, t0                                // write hgatp (G-stage CSR)
  csrr a5, hgatp                                // first read → a5 (VMIDLEN)
  csrr a6, hgatp                                // second read → a6 (scoping)

  // --- PPN all-1s (WARL may clear PPN[1:0] for root align) ---
  LI(t0, (HGATP_MODE_SV32X4 << 31) | 0x3FFFFF)  // MODE + PPN all-1s
  csrw hgatp, t0                                // write hgatp (G-stage CSR)

  // --- PPN walking-1 from bit 2..21 (bits 1:0 often forced 0) ---
  LI(t3, 2)                                     // start PPN walk at bit 2 (bits 1:0 often WARL-0)
ppn_walk:
  LI(t0, (HGATP_MODE_SV32X4 << 31))             // t0 = MODE Sv32x4 only
  LI(t1, 1)                                     // t1 = 1 (will shift into one bit)
  sll t1, t1, t3                                // shift 1 into bit position t3
  or  t0, t0, t1                                // merge MODE with PPN/bit
  csrw hgatp, t0                                // write hgatp (G-stage CSR)
  addi t3, t3, 1                                // next bit/index
  LI(t4, 22)                                    // loop until PPN bits 0..21 done
  blt t3, t4, ppn_walk                          // repeat until all PPN bits tried

  csrr a7, hgatp                                // after walk → a7

  RVTEST_GOTO_MMODE                             // return to M-mode

sig_mode:
  RVTEST_SIGUPD(x2, x5, x4, a3, sig_mode, sig_mode_str)  // save register onto signature answer sheet
sig_ppn0:
  RVTEST_SIGUPD(x2, x5, x4, a4, sig_ppn0, sig_ppn0_str)  // save register onto signature answer sheet
sig_vmid:
  RVTEST_SIGUPD(x2, x5, x4, a5, sig_vmid, sig_vmid_str)  // save register onto signature answer sheet
sig_vmid2:
  RVTEST_SIGUPD(x2, x5, x4, a6, sig_vmid2, sig_vmid2_str)  // save register onto signature answer sheet
sig_ppn1:
  RVTEST_SIGUPD(x2, x5, x4, a7, sig_ppn1, sig_ppn1_str)  // save register onto signature answer sheet

done:
  addi a2, a2, 1                                // bump end marker
  RVTEST_SIGUPD(x2, x5, x4, a2, done, done_str) // save register onto signature answer sheet

RVTEST_CODE_END                                 // end executable code
RVTEST_DATA_BEGIN                               // start data / tables
sig_mode_str:  .string "\"cp_hgatp_mode_field\""
sig_ppn0_str:  .string "\"cp_hgatp_ppn_field zero\""
sig_vmid_str:  .string "\"cp_hgatp_vmidlen_detect\""
sig_vmid2_str: .string "\"cp_hgatp_vmid_scoping\""
sig_ppn1_str:  .string "\"cp_hgatp_ppn_field walk\""
done_str:      .string "\"done\""
RVTEST_DATA_END                                 // end data section
RVTEST_SIG_SETUP                                // allocate signature answer sheet
