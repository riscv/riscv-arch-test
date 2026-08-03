// SPDX-License-Identifier: Apache-2.0
//
// svh_g_walk_vs_pt_VSmode.S
//   Config : sail-rv32-max | VS=Sv32 + G=Sv32x4 (both ON)
//   Pair   : svh_g_walk_vs_pt_sv39_VSmode.S (write later)
//
// Coverpoints mapped (SvH_cg):
//   cp_h_vm_gstagetrans — VS PT GPAs translated by G (allow + deny)
// What this proves: G-stage translation is used even while the hardware walks VS page tables.
// Flow: map VS page-table GPAs -> VS load succeeds -> invalidate a VS-PT map -> VS load faults -> save PASS/FAIL signatures.
// Gloss: PT = page table, PTE = page-table entry, GPA = guest physical address, PA/SPA = real physical address.
// Not mapped: two_stage_read/write, cp_hgatp_adbit_behavior, …
//
// Path: VS walk reads PTE at GPA --hgatp--> PA(VS PT). Sample VS lw, not mret.
//

##### START_TEST_CONFIG #####
# REQUIRED_EXTENSIONS: [I, H, Sv32]     # base I, hypervisor H, Sv32 paging
# MARCH: rv32ih_zicsr_zifencei          # RV32 march for this ELF
##### END_TEST_CONFIG #####

#define TEST_FILE "svh_g_walk_vs_pt_VSmode.S"   // name used in trap / fail messages
#define SIGUPD_COUNT 8                          // signature slots for RVTEST_SIGUPD
#define TRAP_SIGUPD_COUNT 16                    // signature slots for trap path
#define RVTEST_HYPERVISOR                       // enable H PTE / mode macros

#include "riscv_arch_test.h"                    // trap handler, GOTO_*, PTE helpers

RVTEST_BEGIN                                    // open .text + framework prolog

main:
  LI(a2, 0x257A0040)                            // seed

  .set va_data,                 0x008001000     // GVA for VS lw
  .set va_code,                 0x90000000      // GVA for VS code
  .set gpa_data,                0x00C002000     // GPA behind va_data
  .set gpa_code,                0x012000000     // GPA behind va_code
  .set gpa_rvtest_Vroot_pg_tbl, 0x01000A000     // GPA of VS root (G must map)
  .set gpa_rvtest_vlvl0_pg_tbl, 0x01000B000     // GPA of VS L0   (G must map)

  // ---- G-stage: map code, data, and VS page-table GPAs ----

  SUPERPAGE_G_PTE_SETUP(sv32x4, rvtest_code_begin, (PTE_D | PTE_A | PTE_U | PTE_X | PTE_R | PTE_V), gpa_code, LEVEL1)  // map gpa_code -> PA(code) so VS can execute

  G_PTE_SETUP(sv32x4, rvtest_hlvl0_pg_tbl, (PTE_V), gpa_rvtest_Vroot_pg_tbl, LEVEL1)  // point G entry for VS root GPA to G L0 table
  G_PTE_SETUP(sv32x4, rvtest_Vroot_pg_tbl, (PTE_D | PTE_A | PTE_U | PTE_W | PTE_R | PTE_V), gpa_rvtest_Vroot_pg_tbl, LEVEL0)  // G maps VS root GPA → PA (PT walk read)
  G_PTE_SETUP(sv32x4, rvtest_vlvl0_pg_tbl, (PTE_D | PTE_A | PTE_U | PTE_W | PTE_R | PTE_V), gpa_rvtest_vlvl0_pg_tbl, LEVEL0)  // G maps VS L0 GPA → PA (PT walk read)

  G_PTE_SETUP(sv32x4, rvtest_hlvl0_pg_tbl, (PTE_V), gpa_data, LEVEL1)  // point G data entry to G L0 table
  G_PTE_SETUP(sv32x4, test_region, (PTE_D | PTE_A | PTE_U | PTE_W | PTE_R | PTE_V), gpa_data, LEVEL0)  // map gpa_data -> PA(test_region) for the actual load

  // ---- VS-stage: GVA → GPA (PPNs are GPAs; G translates them) ----

  VS_PTE_SETUP(sv32, GPA, gpa_code, (PTE_D | PTE_A | PTE_X | PTE_R | PTE_V), va_code, LEVEL1)  // map va_code -> gpa_code so VS can fetch code
  csrr a0, mscratch                             // read M save area pointer for the next macro
  V_SAVE_AREA_SETUP(va_code, rvtest_code_begin, code, LEVEL1)  // tell framework VS entry PC is under va_code

  VS_PTE_SETUP(sv32, GPA, gpa_rvtest_vlvl0_pg_tbl, (PTE_V), va_data, LEVEL1)  // point VS data entry to VS L0 table GPA
  VS_PTE_SETUP(sv32, GPA, gpa_data, (PTE_D | PTE_A | PTE_W | PTE_R | PTE_V), va_data, LEVEL0)  // map va_data -> gpa_data for the VS load

  VSATP_SETUP(sv32, GPA)                        // write vsatp so VS-stage translation is on
  HGATP_SETUP(sv32x4)                           // write hgatp so G-stage translation is on
  hfence.vvma                                   // clear stale VS-stage translations
  hfence.gvma                                   // clear stale G-stage translations

  LI(t0, 0x257A0041)                            // known SPA pattern
  la t1, test_region                            // t1 = real PA backing gpa_data
  sw t0, 0(t1)                                  // store the value that VS should read

  // ---- Case A: G allows VS-PT GPAs → VS lw succeeds (G walked for PTEs) ----

  LI(a5, va_data)                               // a5 = guest virtual address to load
  RVTEST_GOTO_LOWER_MODE VSmode                 // enter VS mode to run the guest load
  lw   a3, 0(a5)                                // VS walk: G translates VS PT GPAs
  nop                                           // trap-skip padding after load
  RVTEST_GOTO_MMODE                             // return from VS to M-mode test code

  // ---- Case B: G denies VS L0 GPA → VS lw guest-page-faults ----

  G_PTE_SETUP(sv32x4, rvtest_vlvl0_pg_tbl, (PTE_D | PTE_A | PTE_U | PTE_W | PTE_R), gpa_rvtest_vlvl0_pg_tbl, LEVEL0)  // V=0: G denies VS L0 PT walk
  hfence.vvma                                   // clear stale VS-stage translations after the PTE change
  hfence.gvma                                   // clear stale G-stage translations after the PTE change

  LI(a4, 0)                                     // stays 0 if lw is skipped by trap
  RVTEST_GOTO_LOWER_MODE VSmode                 // enter VS mode to retry the load
  lw   a4, 0(a5)                                // expect guest-page fault (handler skips)
  nop                                           // trap-skip padding after load
  RVTEST_GOTO_MMODE                             // return from VS to M-mode test code

sig_allow:
  RVTEST_SIGUPD(x2, x5, x4, a3, sig_allow, sig_allow_str)  // save allowed-walk result for PASS/FAIL
sig_deny:
  RVTEST_SIGUPD(x2, x5, x4, a4, sig_deny, sig_deny_str)    // save denied-walk result for PASS/FAIL

done:
  addi a2, a2, 2                                // a2 = 0x257A0042
  RVTEST_SIGUPD(x2, x5, x4, a2, done, done_str) // save end marker for PASS/FAIL

RVTEST_CODE_END                                 // end executable text
RVTEST_DATA_BEGIN                               // start data / page-table storage

.align 12                                      // 4 KiB page align
test_region:                                   // real PA backing gpa_data
  .word 0                                      // data slot used by the VS load
  .word 0                                      // padding in the same page
  .word 0                                      // padding in the same page
  .word 0                                      // padding in the same page

.align 12                                       // align to 4 KiB page
rvtest_hlvl0_pg_tbl:                           // G-stage level-0 PTE storage
  .zero(4096)                                  // reserve one page for G L0 table
.align 12                                       // align to 4 KiB page
rvtest_vlvl0_pg_tbl:                           // VS-stage level-0 PTE storage
  .zero(4096)                                  // reserve one page for VS L0 table

sig_allow_str: .string "\"cp_h_vm_gstagetrans: G allow VS-PT walk\""  // SIGUPD label
sig_deny_str:  .string "\"cp_h_vm_gstagetrans: G deny VS-PT walk\""   // SIGUPD label
done_str:      .string "\"done\""                                     // SIGUPD label

RVTEST_DATA_END                                // end data section
RVTEST_SIG_SETUP                               // allocate signature memory for compare
