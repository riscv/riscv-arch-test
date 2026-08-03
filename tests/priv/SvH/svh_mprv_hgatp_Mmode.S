// SPDX-License-Identifier: Apache-2.0
//
// svh_mprv_hgatp_Mmode.S
//   Config : sail-rv32-max | M-mode MPRV×MPV×hgatp; vsatp Bare
//
// Coverpoints mapped (SvH_cg):
//   cp_hgatp_mprv_effects — lw under MPRV+MPV uses G (X-only deny);
//                           HLV ignores MPRV and still uses hgatp (R/W allow)
// What this proves: MPRV+MPV can make an M-mode load use hgatp, while HLV uses hgatp independently of MPRV.
// Flow: build one X-only G map and one R/W G map -> direct PA read -> MPRV load faults -> HLV succeeds -> save PASS/FAIL signatures.
// Gloss: hgatp = hypervisor page-table CSR, HLV = hypervisor load virtual instruction, GPA = guest physical address.
//

##### START_TEST_CONFIG #####
# REQUIRED_EXTENSIONS: [I, H, Sv32]     # base I, hypervisor H, Sv32 paging
# MARCH: rv32ih_zicsr_zifencei          # RV32 march for this ELF
##### END_TEST_CONFIG #####

#define TEST_FILE "svh_mprv_hgatp_Mmode.S"  // name used in trap / fail messages
#define SIGUPD_COUNT 8                      // signature slots for RVTEST_SIGUPD
#define TRAP_SIGUPD_COUNT 16                // signature slots for trap path
#define RVTEST_HYPERVISOR                   // enable H PTE / mode macros

#include "riscv_arch_test.h"                // trap handler, CSR constants, PTE helpers

RVTEST_BEGIN                                // open .text + framework prolog

main:
  LI(a2, 0x257A0150)                        // seed value for the done signature

  .set gpa_xonly, 0x00C002000               // GPA mapped execute-only for the fault case
  .set gpa_rw,    0x00C003000               // GPA mapped read/write for the HLV success case

  // --- G-stage X-only map ---
  // G: execute-only leaf (MPRV lw must fault)
  G_PTE_SETUP(sv32x4, rvtest_hlvl0_pg_tbl, (PTE_V), gpa_xonly, LEVEL1)  // point gpa_xonly VPN1 to the G L0 table
  G_PTE_SETUP(sv32x4, test_region_x, (PTE_D | PTE_A | PTE_U | PTE_X | PTE_V), gpa_xonly, LEVEL0)  // map gpa_xonly -> PA(test_region_x) as execute-only

  // --- G-stage read/write map ---
  // G: R/W leaf for HLV (unaffected by MPRV)
  G_PTE_SETUP(sv32x4, rvtest_hlvl0_pg_tbl, (PTE_V), gpa_rw, LEVEL1)  // point gpa_rw VPN1 to the G L0 table
  G_PTE_SETUP(sv32x4, test_region_rw, (PTE_D | PTE_A | PTE_U | PTE_W | PTE_R | PTE_V), gpa_rw, LEVEL0)  // map gpa_rw -> PA(test_region_rw) with read/write

  csrw vsatp, x0                            // turn off VS-stage translation
  HGATP_SETUP(sv32x4)                       // write hgatp so G-stage translation is on
  hfence.vvma                               // clear stale VS-stage translations
  hfence.gvma                               // clear stale G-stage translations

  LI(t0, 0x257A0151)                        // expected value in the X-only physical page
  la t1, test_region_x                      // t1 = real PA for X-only backing memory
  sw t0, 0(t1)                              // store the X-only page value in real memory
  LI(t0, 0x257A0152)                        // expected value in the read/write physical page
  la t1, test_region_rw                     // t1 = real PA for read/write backing memory
  sw t0, 0(t1)                              // store the read/write page value in real memory

  // --- Direct M-mode physical read ---
  // Direct SPA read (no G)
  la t1, test_region_x                      // t1 = real PA for X-only backing memory
  lw a3, 0(t1)                              // read physical memory directly without hgatp

  // --- MPRV/MPV load through hgatp ---
  // MPRV=1, MPP=S, MPV=1: G X-only → load fault
  LI(t0, MSTATUS_MPP)                       // t0 = bit mask for MPP field
  csrc mstatus, t0                          // clear old MPP bits
  LI(t0, MPP_SMODE)                         // t0 = value that selects S-mode memory rules
  csrs mstatus, t0                          // set MPP=S in mstatus
  LI(t0, MSTATUSH_MPV)                      // t0 = bit mask for MPV
  csrs mstatush, t0                         // set MPV so lower-mode access is virtualized
  LI(t0, MSTATUS_MPRV)                      // t0 = bit mask for MPRV
  csrs mstatus, t0                          // set MPRV so M-mode load uses MPP/MPV rules
  LI(a4, 0)                                 // a4 stays 0 if the load faults and is skipped
  LI(a5, gpa_xonly)                         // a5 = GPA that hgatp maps execute-only
  lw   a4, 0(a5)                            // try normal load through hgatp; should fault
  nop                                       // trap-skip padding after load

  // --- HLV through hgatp ---
  // Same MPRV/MPV: HLV of R/W GPA must succeed (HLV ignores MPRV)
  LI(a6, 0)                                 // a6 should receive the read/write page value
  LI(a5, gpa_rw)                            // a5 = GPA that hgatp maps read/write
  hlv.w a6, (a5)                            // hypervisor-load word through hgatp into a6
  nop                                       // trap-skip padding after HLV

  LI(t0, MSTATUS_MPRV)                      // t0 = bit mask for MPRV
  csrc mstatus, t0                          // clear MPRV before finishing
  LI(t0, MSTATUSH_MPV)                      // t0 = bit mask for MPV
  csrc mstatush, t0                         // clear MPV before finishing

sig_spa:
  RVTEST_SIGUPD(x2, x5, x4, a3, sig_spa, sig_spa_str)  // save direct physical read for PASS/FAIL
sig_deny:
  RVTEST_SIGUPD(x2, x5, x4, a4, sig_deny, sig_deny_str)  // save MPRV fault result for PASS/FAIL
sig_hlv:
  RVTEST_SIGUPD(x2, x5, x4, a6, sig_hlv, sig_hlv_str)  // save HLV success result for PASS/FAIL

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
sig_spa_str:  .string "\"cp_hgatp_mprv_effects: SPA\""        // SIGUPD label
sig_deny_str: .string "\"cp_hgatp_mprv_effects: MPRV fault\"" // SIGUPD label
sig_hlv_str:  .string "\"cp_hgatp_mprv_effects: HLV ok\""     // SIGUPD label
done_str:     .string "\"done\""                             // SIGUPD label
RVTEST_DATA_END                            // end data section
RVTEST_SIG_SETUP                           // allocate signature memory for compare
