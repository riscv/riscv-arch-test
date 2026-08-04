// SPDX-License-Identifier: Apache-2.0
//
// svh_mprv_vsatp_sv39_Mmode.S
//   Config : sail-rv64-max | M-mode MPRV×MPV×vsatp Sv39; hgatp/satp Bare
//   Pair   : svh_mprv_vsatp_Mmode.S
//
// Coverpoints mapped (SvH_cg):
//   cp_vsatp_mprv_effects — MPRV=0 ignore; MPRV=1 MPP=S/U + MPV=1 uses vsatp
// What this proves: On RV64, M-mode data loads use vsatp only when MPRV and MPV
//                   make them act like virtualized S/U-mode (VS/VU) loads.
// Flow: build VS Sv39 maps -> try MPRV=0 load -> try MPRV+MPP=S -> try MPRV+MPP=U
//       -> save PASS/FAIL signatures.
// Gloss: CSR = control register; MPRV = M-mode data uses MPP rules;
//        MPV = pretend virtualized (VS/VU); on RV64 MPV is in mstatus (not mstatush).
//

##### START_TEST_CONFIG #####
# REQUIRED_EXTENSIONS: [I, H, Sv39]     # base I, hypervisor H, Sv39 paging
# MARCH: rv64ih_zicsr_zifencei          # RV64 march for this ELF
##### END_TEST_CONFIG #####

#define TEST_FILE "svh_mprv_vsatp_sv39_Mmode.S"  // name used in trap / fail messages
#define SIGUPD_COUNT 8                          // signature slots for RVTEST_SIGUPD
#define TRAP_SIGUPD_COUNT 16                    // signature slots for trap path
#define RVTEST_HYPERVISOR                       // enable H PTE / mode macros

#include "riscv_arch_test.h"                    // trap handler, CSR constants, PTE helpers

RVTEST_BEGIN                                    // open .text + framework prolog

main:
  LI(a2, 0x257A0140)                            // seed value for the done signature

  .set va_s, 0x0000000080010000                 // guest VA for supervisor-style page (U=0)
  .set va_u, 0x0000000080020000                 // guest VA for user-style page (U=1)

  // --- VS-stage Sv39 maps (hgatp Bare → root table address is a real PA) ---
  // Three levels: LEVEL2 root → LEVEL1 mid → LEVEL0 leaf
  VS_PTE_SETUP(sv39, PA, rvtest_vlvl1_pg_tbl, (PTE_V), va_s, LEVEL2)  // va_s VPN2 points at VS L1 table
  VS_PTE_SETUP(sv39, PA, rvtest_vlvl0_pg_tbl, (PTE_V), va_s, LEVEL1)  // va_s VPN1 points at VS L0 table
  VS_PTE_SETUP(sv39, PA, test_region_s, (PTE_D | PTE_A | PTE_W | PTE_R | PTE_V), va_s, LEVEL0)  // S leaf: R/W, U=0
  VS_PTE_SETUP(sv39, PA, rvtest_vlvl1_pg_tbl, (PTE_V), va_u, LEVEL2)  // va_u VPN2 points at VS L1 table
  VS_PTE_SETUP(sv39, PA, rvtest_vlvl0_pg_tbl, (PTE_V), va_u, LEVEL1)  // va_u VPN1 points at VS L0 table
  VS_PTE_SETUP(sv39, PA, test_region_u, (PTE_D | PTE_A | PTE_U | PTE_W | PTE_R | PTE_V), va_u, LEVEL0)  // U leaf: R/W, U=1

  VSATP_SETUP(sv39, PA)                         // write vsatp so VS-stage Sv39 translation can be used
  csrw hgatp, x0                                // turn off G-stage translation for this test
  csrw satp, x0                                 // turn off ordinary S-stage translation
  hfence.vvma                                   // clear stale VS-stage translations
  hfence.gvma                                   // clear stale G-stage translations

  LI(t0, 0x257A0141)                            // expected value for the supervisor-style page
  la t1, test_region_s                          // t1 = real PA for supervisor-style data
  sw t0, 0(t1)                                  // store expected supervisor-page value in memory
  LI(t0, 0x257A0142)                            // expected value for the user-style page
  la t1, test_region_u                          // t1 = real PA for user-style data
  sw t0, 0(t1)                                  // store expected user-page value in memory

  // ---- MPRV=0: guest VA is NOT translated (negative case) ----
  LI(t0, MSTATUS_MPRV)                          // t0 = bit mask for MPRV
  csrc mstatus, t0                              // clear MPRV so M-mode uses raw addresses
  LI(t0, MSTATUS_MPV)                           // t0 = bit mask for MPV (RV64: in mstatus)
  csrc mstatus, t0                              // clear MPV so memory is not virtualized
  LI(a3, 0)                                     // a3 stays 0 if raw-address load is skipped by trap
  LI(a5, va_s)                                  // a5 = virtual-looking address, not a real PA
  lw   a3, 0(a5)                                // try M-mode load without vsatp translation
  nop                                           // trap-skip padding after load

  // ---- MPRV=1, MPP=S, MPV=1: act like VS → use vsatp ----
  LI(t0, MSTATUS_MPP)                           // t0 = bit mask for MPP field
  csrc mstatus, t0                              // clear old MPP bits
  LI(t0, MPP_SMODE)                             // t0 = value that selects S-mode memory rules
  csrs mstatus, t0                              // set MPP=S in mstatus
  LI(t0, MSTATUS_MPV)                           // t0 = bit mask for MPV
  csrs mstatus, t0                              // set MPV so the lower-mode access is virtual (VS)
  LI(t0, MSTATUS_MPRV)                          // t0 = bit mask for MPRV
  csrs mstatus, t0                              // set MPRV so M-mode load uses MPP/MPV rules
  LI(a4, 0)                                     // a4 should receive the supervisor-page value
  LI(a5, va_s)                                  // a5 = supervisor-page guest virtual address
  lw   a4, 0(a5)                                // load through vsatp as virtualized S-mode
  nop                                           // trap-skip padding after load

  // ---- MPRV=1, MPP=U, MPV=1: act like VU → use vsatp ----
  LI(t0, MSTATUS_MPP)                           // t0 = bit mask for MPP field
  csrc mstatus, t0                              // clear MPP → MPP=U (00)
  LI(a6, 0)                                     // a6 should receive the user-page value
  LI(a5, va_u)                                  // a5 = user-page guest virtual address
  lw   a6, 0(a5)                                // load through vsatp as virtualized U-mode
  nop                                           // trap-skip padding after load

  LI(t0, MSTATUS_MPRV)                          // t0 = bit mask for MPRV
  csrc mstatus, t0                              // clear MPRV before finishing
  LI(t0, MSTATUS_MPV)                           // t0 = bit mask for MPV
  csrc mstatus, t0                              // clear MPV before finishing

sig_mprv0:
  RVTEST_SIGUPD(x2, x5, x4, a3, sig_mprv0, sig_mprv0_str)  // save MPRV=0 result for PASS/FAIL
sig_mprv_s:
  RVTEST_SIGUPD(x2, x5, x4, a4, sig_mprv_s, sig_mprv_s_str)  // save MPP=S result for PASS/FAIL
sig_mprv_u:
  RVTEST_SIGUPD(x2, x5, x4, a6, sig_mprv_u, sig_mprv_u_str)  // save MPP=U result for PASS/FAIL

done:
  addi a2, a2, 1                                // a2 bump proves we finished
  RVTEST_SIGUPD(x2, x5, x4, a2, done, done_str) // save end marker for PASS/FAIL

RVTEST_CODE_END                                 // end executable text
RVTEST_DATA_BEGIN                               // start data / page-table storage
.align 12                                       // 4 KiB page align
test_region_s:                                  // real PA backing the supervisor-style page
  .word 0                                       // data slot for va_s
  .word 0                                       // padding in the same page
  .word 0                                       // padding in the same page
  .word 0                                       // padding in the same page
.align 12                                       // 4 KiB page align
test_region_u:                                  // real PA backing the user-style page
  .word 0                                       // data slot for va_u
  .word 0                                       // padding in the same page
  .word 0                                       // padding in the same page
  .word 0                                       // padding in the same page
.align 12                                       // 4 KiB page align
rvtest_vlvl1_pg_tbl:                            // VS-stage level-1 PTE storage
  .zero(4096)                                   // reserve one page for VS L1 table
.align 12                                       // 4 KiB page align
rvtest_vlvl0_pg_tbl:                            // VS-stage level-0 PTE storage
  .zero(4096)                                   // reserve one page for VS L0 table
sig_mprv0_str: .string "\"cp_vsatp_mprv_effects: MPRV0\""  // SIGUPD label
sig_mprv_s_str: .string "\"cp_vsatp_mprv_effects: MPP_S\"" // SIGUPD label
sig_mprv_u_str: .string "\"cp_vsatp_mprv_effects: MPP_U\"" // SIGUPD label
done_str:      .string "\"done\""                         // SIGUPD label
RVTEST_DATA_END                                 // end data section
RVTEST_SIG_SETUP                                // allocate signature memory for compare
