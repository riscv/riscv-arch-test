// SPDX-License-Identifier: Apache-2.0
//
// svh_two_stage_ifetch_sv39_VSmode.S
//   Config : sail-rv64-max | VS=Sv39 + G=Sv39x4 (both ON)
//   Pair   : svh_two_stage_ifetch_VSmode.S
//
// Coverpoints mapped (SvH_cg):
//   two_stage_ifetch - VS insn fetch GVA->GPA->SPA (X on both stages)
// What this proves: VS-mode instruction fetches reach real code through Sv39 plus Sv39x4 translation.
// Flow: map guest code -> enter VS at va_code -> execute addi/nops -> return to M -> save PASS/FAIL signatures.
// Gloss: ifetch = instruction fetch, GVA = guest virtual address, GPA = guest physical address, PA/SPA = real physical address.
// Not mapped: two_stage_read, two_stage_write, cp_two_stage_mxr, ...
//
// Path: GVA(va_code) --vsatp--> GPA(gpa_code) --hgatp--> PA(rvtest_code_begin)
// Sample VS retires (EXECUTE + VS_PTE_I/G_PTE_I), not mret.
//

##### START_TEST_CONFIG #####
# REQUIRED_EXTENSIONS: [I, H, Sv39]     # base I, hypervisor H, Sv39 paging
# MARCH: rv64ih_zicsr_zifencei          # RV64 march for this ELF
##### END_TEST_CONFIG #####

#define TEST_FILE "svh_two_stage_ifetch_sv39_VSmode.S"  // name used in trap / fail messages
#define SIGUPD_COUNT 8                                  // signature slots for RVTEST_SIGUPD
#define TRAP_SIGUPD_COUNT 16                            // signature slots for trap path
#define RVTEST_HYPERVISOR                               // enable H PTE / mode macros

#include "riscv_arch_test.h"                            // trap handler, GOTO_*, PTE helpers

RVTEST_BEGIN                                            // open .text + framework prolog

main:
  LI(a2, 0x257A0010)                               // seed; VS addi proves ifetch ran

  .set va_code,                 0x0000000090000000 // GVA where VS executes this code
  .set gpa_code,                0x0000000012000000 // GPA behind va_code (2 MiB aligned)
  .set gpa_rvtest_Vroot_pg_tbl, 0x000000001000A000 // GPA of VS root (LEVEL2) table
  .set gpa_rvtest_vlvl1_pg_tbl, 0x000000001000C000 // GPA of VS mid (LEVEL1) table

  // ---- G-stage (hgatp Sv39x4): GPA -> PA  (walks as U-mode, so U=1 on leaves) ----

  G_PTE_SETUP(sv39x4, rvtest_hlvl1_pg_tbl, (PTE_V), gpa_code, LEVEL2)  // non-leaf: shared VPN2 -> G L1 table
  SUPERPAGE_G_PTE_SETUP(sv39x4, rvtest_code_begin, (PTE_D | PTE_A | PTE_U | PTE_X | PTE_R | PTE_V), gpa_code, LEVEL1)  // gpa_code -> PA(code); LEVEL1 = 2 MiB X leaf

  G_PTE_SETUP(sv39x4, rvtest_hlvl0_pg_tbl, (PTE_V), gpa_rvtest_Vroot_pg_tbl, LEVEL1)  // non-leaf: G VPN1 for VS root GPA -> G L0
  G_PTE_SETUP(sv39x4, rvtest_Vroot_pg_tbl, (PTE_D | PTE_A | PTE_U | PTE_W | PTE_R | PTE_V), gpa_rvtest_Vroot_pg_tbl, LEVEL0)  // leaf: GPA(VS root) -> PA(VS root) R/W
  G_PTE_SETUP(sv39x4, rvtest_vlvl1_pg_tbl, (PTE_D | PTE_A | PTE_U | PTE_W | PTE_R | PTE_V), gpa_rvtest_vlvl1_pg_tbl, LEVEL0)  // leaf: GPA(VS L1) -> PA(VS L1) R/W

  // ---- VS-stage (vsatp Sv39): GVA -> GPA  (3 levels; X so VS may fetch) ----

  VS_PTE_SETUP(sv39, GPA, gpa_rvtest_vlvl1_pg_tbl, (PTE_V), va_code, LEVEL2)  // non-leaf: va_code VPN2 -> VS L1 table GPA
  VS_PTE_SETUP(sv39, GPA, gpa_code, (PTE_D | PTE_A | PTE_X | PTE_R | PTE_V), va_code, LEVEL1)  // leaf: va_code -> gpa_code (X/R, 2 MiB)

  csrr a0, mscratch                             // a0 = Msave_area (required by next macro)
  V_SAVE_AREA_SETUP(va_code, rvtest_code_begin, code, LEVEL1)  // framework: VS entry PC under va_code

  VSATP_SETUP(sv39, GPA)                        // vsatp = Sv39, PPN = GPA of VS root
  HGATP_SETUP(sv39x4)                           // hgatp = Sv39x4, PPN = G root
  hfence.vvma                                   // invalidate VS-stage TLB entries
  hfence.gvma                                   // invalidate G-stage TLB entries

  // ---- stimulus in VS (FC-sample these retires for exec / PTE_I, not mret) ----

  RVTEST_GOTO_LOWER_MODE VSmode                 // M -> VS; first VS ifetch uses both stages
  addi a2, a2, 1                                // a2 = 0x257A0011; proves VS code executed
  nop                                           // another two-stage ifetch retire
  nop                                           // one more simple VS instruction fetch
  RVTEST_GOTO_MMODE                             // VS -> M via ecall to test handler

sig_ifetch:
  RVTEST_SIGUPD(x2, x5, x4, a2, sig_ifetch, sig_ifetch_str)  // save VS result for PASS/FAIL

done:
  addi a2, a2, 1                                // a2 = 0x257A0012; proves we finished
  RVTEST_SIGUPD(x2, x5, x4, a2, done, done_str) // save end marker for PASS/FAIL

RVTEST_CODE_END                                  // end executable text
RVTEST_DATA_BEGIN                                // start data / page-table storage

.align 12                                       // 4 KiB page align
rvtest_hlvl1_pg_tbl:                            // G-stage level-1 PTE storage
  .zero(4096)                                   // reserve one page for G L1 table
.align 12                                       // align to 4 KiB page
rvtest_hlvl0_pg_tbl:                            // G-stage level-0 PTE storage
  .zero(4096)                                   // reserve one page for G L0 table
.align 12                                       // align to 4 KiB page
rvtest_vlvl1_pg_tbl:                            // VS-stage level-1 PTE storage
  .zero(4096)                                   // reserve one page for VS L1 table

sig_ifetch_str: .string "\"two_stage_ifetch: VS ran (sv39)\""  // SIGUPD label
done_str:       .string "\"done\""                             // SIGUPD label

RVTEST_DATA_END                                  // end data section
RVTEST_SIG_SETUP                                 // allocate signature memory for compare
