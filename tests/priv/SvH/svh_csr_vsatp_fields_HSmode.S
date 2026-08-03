// SPDX-License-Identifier: Apache-2.0
//
// svh_csr_vsatp_fields_HSmode.S
//   Config : sail-rv32-max | HS writes vsatp; hgatp=Bare
//   Pair   : svh_csr_vsatp_fields_RV64_HSmode.S
//
// What this proves (one line):
//   From HS, vsatp MODE / PPN / ASID can be written and read back (CSR knobs only).
//
// Flow:
//   hgatp=0 → enter HS → poke vsatp fields → read back → signatures → PASS/FAIL
//
// Coverpoints mapped (SvH_cg):
//   cp_vsatp_mode_field, cp_vsatp_ppn_field, cp_vsatp_asidlen_detect
//
// Words: CSR=settings knob; HS=host supervisor; Bare=paging off;
//        MODE=paging type; PPN=page-table root page#; ASID=address-space id
//

##### START_TEST_CONFIG #####
# REQUIRED_EXTENSIONS: [I, H, Sv32]     # needs integer, hypervisor, Sv32
# MARCH: rv32ih_zicsr_zifencei          # build as RV32
##### END_TEST_CONFIG #####

#define TEST_FILE "svh_csr_vsatp_fields_HSmode.S"
#define SIGUPD_COUNT 8                          // slots for answer-sheet updates
#define TRAP_SIGUPD_COUNT 16
#define RVTEST_HYPERVISOR                       // turn on H helpers

#include "riscv_arch_test.h"                    // trap handler, GOTO_*, PTE macros

RVTEST_BEGIN                                    // framework start (.text + setup)

main:
  LI(a2, 0x257A0110)                            // seed; later proves we finished

  // --- Partner stage off (sheet rule for vsatp CSR tests) ---
  csrw hgatp, x0                                // hgatp=0 → G-stage Bare (no G walk)
  hfence.gvma                                   // flush old G TLB so Bare is real

  RVTEST_GOTO_LOWER_MODE HSmode                 // leave M; enter HS (can write vsatp)

  // --- MODE = Sv32; read back ---
  LI(t0, (SATP_MODE_SV32 << 31))                // RV32: MODE lives in bit 31
  csrw vsatp, t0                                // write guest page-table CSR
  csrr a3, vsatp                                // read back → save in a3

  // --- PPN = 0 with Sv32 ---
  LI(t0, (SATP_MODE_SV32 << 31))                // MODE=Sv32, PPN field all 0
  csrw vsatp, t0                                // write vsatp (guest page-table CSR)
  csrr a4, vsatp                                // read back zero-PPN case

  // --- ASID all-1s (see which bits stick = ASIDLEN) ---
  LI(t0, (SATP_MODE_SV32 << 31) | SATP32_ASID)  // set every ASID bit
  csrw vsatp, t0                                // write vsatp (guest page-table CSR)
  csrr a5, vsatp                                // readback shows legal ASID width

  // --- PPN all-1s (22 bits on Sv32) ---
  LI(t0, (SATP_MODE_SV32 << 31) | 0x3FFFFF)     // MODE + PPN ones
  csrw vsatp, t0                                // write vsatp (guest page-table CSR)

  // --- PPN walking-1: bit0, bit1, … bit21 ---
  LI(t3, 0)                                     // bit index
ppn_walk:
  LI(t0, (SATP_MODE_SV32 << 31))                // start from MODE only
  LI(t1, 1)                                     // t1 = 1 (will shift into one bit)
  sll t1, t1, t3                                // t1 = 1 << bit
  or  t0, t0, t1                                // MODE | that PPN bit
  csrw vsatp, t0                                // write
  addi t3, t3, 1                                // next bit/index
  LI(t4, 22)                                    // loop until PPN bits 0..21 done
  blt t3, t4, ppn_walk                          // loop 22 times

  csrr a6, vsatp                                // final read after walk

  RVTEST_GOTO_MMODE                             // back to M for signatures

  // --- Answer sheet (signature) ---
sig_mode:
  RVTEST_SIGUPD(x2, x5, x4, a3, sig_mode, sig_mode_str)   // save MODE readback
sig_ppn0:
  RVTEST_SIGUPD(x2, x5, x4, a4, sig_ppn0, sig_ppn0_str)   // save PPN0 readback
sig_asid:
  RVTEST_SIGUPD(x2, x5, x4, a5, sig_asid, sig_asid_str)   // save ASID readback
sig_ppn1:
  RVTEST_SIGUPD(x2, x5, x4, a6, sig_ppn1, sig_ppn1_str)   // save after PPN walk

done:
  addi a2, a2, 1                                // a2 bump = reached end
  RVTEST_SIGUPD(x2, x5, x4, a2, done, done_str) // save register onto signature answer sheet

RVTEST_CODE_END                                 // end executable code
RVTEST_DATA_BEGIN                               // start data / tables
sig_mode_str: .string "\"cp_vsatp_mode_field\""
sig_ppn0_str: .string "\"cp_vsatp_ppn_field zero\""
sig_asid_str: .string "\"cp_vsatp_asidlen_detect\""
sig_ppn1_str: .string "\"cp_vsatp_ppn_field walk\""
done_str:     .string "\"done\""
RVTEST_DATA_END                                 // end data section
RVTEST_SIG_SETUP                                // allocate signature memory
