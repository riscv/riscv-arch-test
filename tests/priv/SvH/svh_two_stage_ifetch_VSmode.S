// SPDX-License-Identifier: Apache-2.0
//
// svh_two_stage_ifetch_VSmode.S
//   Config : sail-rv32-max | VS=Sv32 + G=Sv32x4 (both ON)
//   Pair   : svh_two_stage_ifetch_sv39_VSmode.S (write later)
//
// Coverpoints mapped (SvH_cg):
//   two_stage_ifetch — VS insn fetch GVA→GPA→SPA (X on both stages)
// What this proves: VS-mode instruction fetches reach real code through both translation stages.
// Flow: map guest code -> enter VS at va_code -> execute addi/nops -> return to M -> save PASS/FAIL signatures.
// Gloss: ifetch = instruction fetch, GVA = guest virtual address, GPA = guest physical address, PA/SPA = real physical address.
// Not mapped: two_stage_read, two_stage_write, cp_two_stage_mxr, …
//
// Path: GVA(va_code) --vsatp--> GPA(gpa_code) --hgatp--> PA(rvtest_code_begin)
// Sample VS retires (EXECUTE + VS_PTE_I/G_PTE_I), not mret.
//

##### START_TEST_CONFIG #####
# REQUIRED_EXTENSIONS: [I, H, Sv32]     # base I, hypervisor H, Sv32 paging
# MARCH: rv32ih_zicsr_zifencei          # RV32 march for this ELF
##### END_TEST_CONFIG #####

#define TEST_FILE "svh_two_stage_ifetch_VSmode.S"  // name used in trap / fail messages
#define SIGUPD_COUNT 8                             // signature slots for RVTEST_SIGUPD
#define TRAP_SIGUPD_COUNT 16                       // signature slots for trap path
#define RVTEST_HYPERVISOR                          // enable H PTE / mode macros

#include "riscv_arch_test.h"                       // trap handler, GOTO_*, PTE helpers

RVTEST_BEGIN                                       // open .text + framework prolog

main:
  LI(a2, 0x257A0010)                               // seed; VS addi proves ifetch ran

  .set va_code,                 0x90000000         // GVA where VS executes this code
  .set gpa_code,                0x012000000        // GPA behind va_code (4 MiB aligned)
  .set gpa_rvtest_Vroot_pg_tbl, 0x01000A000        // GPA of VS root page table

  // ---- G-stage (hgatp Sv32x4): GPA -> PA  (walks as U-mode → U=1 on leaves) ----

  SUPERPAGE_G_PTE_SETUP(sv32x4, rvtest_code_begin, (PTE_D | PTE_A | PTE_U | PTE_X | PTE_R | PTE_V), gpa_code, LEVEL1)  // gpa_code -> PA(code); LEVEL1 = 4 MiB X leaf

  G_PTE_SETUP(sv32x4, rvtest_hlvl0_pg_tbl, (PTE_V), gpa_rvtest_Vroot_pg_tbl, LEVEL1)  // non-leaf: G VPN1 -> G L0 table
  G_PTE_SETUP(sv32x4, rvtest_Vroot_pg_tbl, (PTE_D | PTE_A | PTE_U | PTE_W | PTE_R | PTE_V), gpa_rvtest_Vroot_pg_tbl, LEVEL0)  // leaf: GPA(VS root) -> PA(VS root) R/W (PT walk)

  // ---- VS-stage (vsatp Sv32): GVA -> GPA  (X so VS may fetch; U=0) ----

  VS_PTE_SETUP(sv32, GPA, gpa_code, (PTE_D | PTE_A | PTE_X | PTE_R | PTE_V), va_code, LEVEL1)  // leaf: va_code -> gpa_code (X/R)

  csrr a0, mscratch                                // a0 = Msave_area (required by next macro)
  V_SAVE_AREA_SETUP(va_code, rvtest_code_begin, code, LEVEL1)  // framework: VS entry PC under va_code

  VSATP_SETUP(sv32, GPA)                           // vsatp = Sv32, PPN = GPA of VS root
  HGATP_SETUP(sv32x4)                              // hgatp = Sv32x4, PPN = G root
  hfence.vvma                                      // invalidate VS-stage TLB entries
  hfence.gvma                                      // invalidate G-stage TLB entries

  // ---- stimulus in VS (FC-sample these retires for exec / PTE_I — not mret) ----

  RVTEST_GOTO_LOWER_MODE VSmode                    // M -> VS; first VS ifetch uses both stages
  addi a2, a2, 1                                   // a2 = 0x257A0011 — ifetch of this insn
  nop                                              // another two-stage ifetch retire
  nop                                           // pad (trap handler may skip prior insn)
  RVTEST_GOTO_MMODE                                // VS -> M via ecall to test handler

sig_ifetch:
  RVTEST_SIGUPD(x2, x5, x4, a2, sig_ifetch, sig_ifetch_str)  // expect 0x257A0011

done:
  addi a2, a2, 1                                   // a2 = 0x257A0012 (proves we finished)
  RVTEST_SIGUPD(x2, x5, x4, a2, done, done_str)    // signature: end marker

RVTEST_CODE_END                                    // end executable text
RVTEST_DATA_BEGIN                                  // start data / page-table storage

.align 12                                       // align to 4 KiB page
rvtest_hlvl0_pg_tbl:                               // G-stage level-0 PTE storage
  .zero(4096)                                   // 4 KiB page-table storage

sig_ifetch_str: .string "\"two_stage_ifetch: VS ran (sv32)\""  // SIGUPD label
done_str:       .string "\"done\""                             // SIGUPD label

RVTEST_DATA_END                                    // end data section
RVTEST_SIG_SETUP                                   // allocate signature memory for compare
