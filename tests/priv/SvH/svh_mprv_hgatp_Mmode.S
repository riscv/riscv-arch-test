// SPDX-License-Identifier: Apache-2.0
//
// svh_mprv_hgatp_Mmode.S
//   Config : sail-rv32-max | M-mode MPRV×MPP/MPV×hgatp; vsatp/satp Bare
//
// Coverpoints mapped (SvH_cg):
//   cp_hgatp_mprv_effects — MPRV=1 × {M,HS,VS,U,VU} lw;
//                           HLV ignores MPRV (R/W G allow)
// What this proves:
//   MPV=1 (VS/VU): lw of X-only GPA uses G → fault.
//   MPP=M or MPV=0 (HS/U): lw of real PA does not use G → no fault.
//   HLV still uses hgatp and succeeds on R/W GPA.
// Flow: G maps → SPA → five MPRV lw cases → HLV → signatures.
// Gloss: MPRV=data uses MPP rules; MPV=1 means VS/VU (G applies);
//        GPA=guest physical address; HLV=hypervisor load virtual.
//

##### START_TEST_CONFIG #####
# REQUIRED_EXTENSIONS: [I, H, Sv32]     # base I, hypervisor H, Sv32 paging
# MARCH: rv32ih_zicsr_zifencei          # RV32 march for this ELF
##### END_TEST_CONFIG #####

#define TEST_FILE "svh_mprv_hgatp_Mmode.S"  // name used in trap / fail messages
#define SIGUPD_COUNT 10                     // signature slots for RVTEST_SIGUPD
#define TRAP_SIGUPD_COUNT 16                // signature slots for trap path
#define RVTEST_HYPERVISOR                   // enable H PTE / mode macros

#include "riscv_arch_test.h"                // trap handler, CSR constants, PTE helpers

RVTEST_BEGIN                                // open .text + framework prolog

main:
  LI(a2, 0x257A0150)                        // seed value for the done signature

  .set gpa_xonly, 0x00C002000               // GPA mapped execute-only (VS/VU fault case)
  .set gpa_rw,    0x00C003000               // GPA mapped read/write (HLV success case)

  // --- G-stage X-only map (VS/VU MPRV lw must fault) ---
  G_PTE_SETUP(sv32x4, rvtest_hlvl0_pg_tbl, (PTE_V), gpa_xonly, LEVEL1)  // point gpa_xonly VPN1 to the G L0 table
  G_PTE_SETUP(sv32x4, test_region_x, (PTE_D | PTE_A | PTE_U | PTE_X | PTE_V), gpa_xonly, LEVEL0)  // map gpa_xonly -> PA(test_region_x) as execute-only

  // --- G-stage R/W map (HLV ignores MPRV; needs read perm) ---
  G_PTE_SETUP(sv32x4, rvtest_hlvl0_pg_tbl, (PTE_V), gpa_rw, LEVEL1)  // point gpa_rw VPN1 to the G L0 table
  G_PTE_SETUP(sv32x4, test_region_rw, (PTE_D | PTE_A | PTE_U | PTE_W | PTE_R | PTE_V), gpa_rw, LEVEL0)  // map gpa_rw -> PA(test_region_rw) with read/write

  csrw vsatp, x0                            // turn off VS-stage translation
  csrw satp, x0                             // turn off ordinary S-stage translation
  HGATP_SETUP(sv32x4)                       // write hgatp so G-stage translation is on
  hfence.vvma                               // clear stale VS-stage translations
  hfence.gvma                               // clear stale G-stage translations

  LI(t0, 0x257A0151)                        // expected value in the X-only physical page
  la t1, test_region_x                      // t1 = real PA for X-only backing memory
  sw t0, 0(t1)                              // store the X-only page value in real memory
  LI(t0, 0x257A0152)                        // expected value in the read/write physical page
  la t1, test_region_rw                     // t1 = real PA for read/write backing memory
  sw t0, 0(t1)                              // store the read/write page value in real memory

  // --- Direct SPA read (baseline; no MPRV, no G) ---
  la t1, test_region_x                      // t1 = real PA for X-only backing memory
  lw a3, 0(t1)                              // read physical memory directly without hgatp

  // --- MPRV=1, MPP=M: act like M → physical, no G ---
  LI(t0, MSTATUS_MPP)                       // t0 = bit mask for MPP field
  csrc mstatus, t0                          // clear old MPP bits
  LI(t0, MPP_MMODE)                         // t0 = value that selects M-mode memory rules
  csrs mstatus, t0                          // set MPP=M in mstatus
  LI(t0, MSTATUSH_MPV)                      // t0 = bit mask for MPV
  csrc mstatush, t0                         // clear MPV (not virtualized)
  LI(t0, MSTATUS_MPRV)                      // t0 = bit mask for MPRV
  csrs mstatus, t0                          // set MPRV so M-mode load uses MPP rules
  LI(a4, 0)                                 // a4 should receive the X-only page value
  la t1, test_region_x                      // t1 = real PA (not GPA)
  lw a4, 0(t1)                              // load as M → no G walk; should succeed
  nop                                       // trap-skip padding after load

  // --- MPRV=1, MPP=S, MPV=0 (HS): no G ---
  LI(t0, MSTATUS_MPP)                       // t0 = bit mask for MPP field
  csrc mstatus, t0                          // clear old MPP bits
  LI(t0, MPP_SMODE)                         // t0 = value that selects S/HS memory rules
  csrs mstatus, t0                          // set MPP=S in mstatus
  LI(a5, 0)                                 // a5 should receive the X-only page value
  la t1, test_region_x                      // t1 = real PA (satp Bare → no translate)
  lw a5, 0(t1)                              // load as HS → no G walk; should succeed
  nop                                       // trap-skip padding after load

  // --- MPRV=1, MPP=S, MPV=1 (VS): G X-only → fault ---
  LI(t0, MSTATUSH_MPV)                      // t0 = bit mask for MPV
  csrs mstatush, t0                         // set MPV so access is virtualized (VS)
  LI(a6, 0)                                 // a6 stays 0 if the load faults and is skipped
  LI(t1, gpa_xonly)                         // t1 = GPA that hgatp maps execute-only
  lw a6, 0(t1)                              // load as VS through G; should fault (no R)
  nop                                       // trap-skip padding after load

  // --- MPRV=1, MPP=U, MPV=0 (U): no G ---
  LI(t0, MSTATUS_MPP)                       // t0 = bit mask for MPP field
  csrc mstatus, t0                          // clear MPP → MPP=U (00)
  LI(t0, MSTATUSH_MPV)                      // t0 = bit mask for MPV
  csrc mstatush, t0                         // clear MPV (not virtualized)
  LI(a7, 0)                                 // a7 should receive the X-only page value
  la t1, test_region_x                      // t1 = real PA
  lw a7, 0(t1)                              // load as U → no G walk; should succeed
  nop                                       // trap-skip padding after load

  // --- MPRV=1, MPP=U, MPV=1 (VU): G X-only → fault ---
  LI(t0, MSTATUSH_MPV)                      // t0 = bit mask for MPV
  csrs mstatush, t0                         // set MPV so access is virtualized (VU)
  LI(s1, 0)                                 // s1 stays 0 if the load faults and is skipped
  LI(t1, gpa_xonly)                         // t1 = GPA that hgatp maps execute-only
  lw s1, 0(t1)                              // load as VU through G; should fault (no R)
  nop                                       // trap-skip padding after load

  // --- HLV of R/W GPA (HLV ignores MPRV; still uses hgatp) ---
  LI(s2, 0)                                 // s2 should receive the read/write page value
  LI(t1, gpa_rw)                            // t1 = GPA that hgatp maps read/write
  hlv.w s2, (t1)                            // hypervisor-load word through hgatp into s2
  nop                                       // trap-skip padding after HLV

  LI(t0, MSTATUS_MPRV)                      // t0 = bit mask for MPRV
  csrc mstatus, t0                          // clear MPRV before finishing
  LI(t0, MSTATUSH_MPV)                      // t0 = bit mask for MPV
  csrc mstatush, t0                         // clear MPV before finishing

sig_spa:
  RVTEST_SIGUPD(x2, x5, x4, a3, sig_spa, sig_spa_str)  // save direct physical read for PASS/FAIL
sig_m:
  RVTEST_SIGUPD(x2, x5, x4, a4, sig_m, sig_m_str)      // save MPP=M result for PASS/FAIL
sig_hs:
  RVTEST_SIGUPD(x2, x5, x4, a5, sig_hs, sig_hs_str)    // save HS (MPP=S,MPV=0) result for PASS/FAIL
sig_vs:
  RVTEST_SIGUPD(x2, x5, x4, a6, sig_vs, sig_vs_str)    // save VS fault result for PASS/FAIL
sig_u:
  RVTEST_SIGUPD(x2, x5, x4, a7, sig_u, sig_u_str)      // save U (MPP=U,MPV=0) result for PASS/FAIL
sig_vu:
  RVTEST_SIGUPD(x2, x5, x4, s1, sig_vu, sig_vu_str)    // save VU fault result for PASS/FAIL
sig_hlv:
  RVTEST_SIGUPD(x2, x5, x4, s2, sig_hlv, sig_hlv_str)  // save HLV success result for PASS/FAIL

done:
  addi a2, a2, 1                            // a2 = 0x257A0151; proves we finished
  RVTEST_SIGUPD(x2, x5, x4, a2, done, done_str)  // save end marker for PASS/FAIL

RVTEST_CODE_END                             // end executable text
RVTEST_DATA_BEGIN                           // start data / page-table storage
.align 12                                   // 4 KiB page align
test_region_x:                              // real PA backing the X-only GPA
  .word 0                                   // data slot for gpa_xonly
  .word 0                                   // padding in the same page
  .word 0                                   // padding in the same page
  .word 0                                   // padding in the same page
.align 12                                   // 4 KiB page align
test_region_rw:                             // real PA backing the read/write GPA
  .word 0                                   // data slot for gpa_rw
  .word 0                                   // padding in the same page
  .word 0                                   // padding in the same page
  .word 0                                   // padding in the same page
.align 12                                   // 4 KiB page align
rvtest_hlvl0_pg_tbl:                        // G-stage level-0 PTE storage
  .zero(4096)                               // reserve one page for G L0 table
sig_spa_str: .string "\"cp_hgatp_mprv_effects: SPA\""        // SIGUPD label
sig_m_str:   .string "\"cp_hgatp_mprv_effects: MPP_M\""      // SIGUPD label
sig_hs_str:  .string "\"cp_hgatp_mprv_effects: HS\""         // SIGUPD label
sig_vs_str:  .string "\"cp_hgatp_mprv_effects: VS fault\""   // SIGUPD label
sig_u_str:   .string "\"cp_hgatp_mprv_effects: U\""          // SIGUPD label
sig_vu_str:  .string "\"cp_hgatp_mprv_effects: VU fault\""   // SIGUPD label
sig_hlv_str: .string "\"cp_hgatp_mprv_effects: HLV ok\""     // SIGUPD label
done_str:    .string "\"done\""                              // SIGUPD label
RVTEST_DATA_END                             // end data section
RVTEST_SIG_SETUP                            // allocate signature memory for compare
