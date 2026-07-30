// SPDX-License-Identifier: Apache-2.0
//
// svh_two_stage_rw_VSmode.S — sail-rv32-max two-stage VS lw/sw
//   VS-stage Sv32, G-stage Sv32x4  |  SvH-US: two_stage_write / two_stage_read
//   Pair: svh_two_stage_rw_sv39_VSmode.S (sail-rv64-max)
//   Path: GVA --vsatp--> GPA --hgatp--> PA(test_region)
//

##### START_TEST_CONFIG #####
# REQUIRED_EXTENSIONS: [I, H, Sv32]     # need base I, hypervisor H, Sv32 paging
# MARCH: rv32ih_zicsr_zifencei          # RV32 compile march for this ELF
##### END_TEST_CONFIG #####

#define TEST_FILE "svh_two_stage_rw_VSmode.S"   // name used in trap / fail messages
#define SIGUPD_COUNT 8                          // signature slots for RVTEST_SIGUPD
#define TRAP_SIGUPD_COUNT 16                    // signature slots for trap path
#define RVTEST_HYPERVISOR                       // enable H PTE / mode macros

#include "riscv_arch_test.h"                    // trap handler, GOTO_*, PTE helpers

RVTEST_BEGIN                                    // open .text + framework prolog

main:
  LI(a2, 0x257A0001)                            // seed payload (later becomes 0x257A0005)

  .set va_data,                 0x008001000     // GVA used by VS sw/lw (data)
  .set va_code,                 0x90000000      // GVA where VS executes this code
  .set gpa_data,                0x00C002000     // GPA behind va_data
  .set gpa_code,                0x012000000     // GPA behind va_code (4 MiB aligned)
  .set gpa_rvtest_Vroot_pg_tbl, 0x01000A000     // GPA of VS root page table
  .set gpa_rvtest_vlvl0_pg_tbl, 0x01000B000     // GPA of VS level-0 page table

  // ---- G-stage (hgatp Sv32x4): GPA -> PA  (walks as U-mode → U=1 on leaves) ----

  SUPERPAGE_G_PTE_SETUP(sv32x4, rvtest_code_begin, (PTE_D | PTE_A | PTE_U | PTE_X | PTE_R | PTE_V), gpa_code, LEVEL1)
                                                // gpa_code -> PA(code); LEVEL1 = 4 MiB leaf

  G_PTE_SETUP(sv32x4, rvtest_hlvl0_pg_tbl, (PTE_V), gpa_rvtest_Vroot_pg_tbl, LEVEL1)
                                                // non-leaf: G VPN1 slot -> G L0 table
  G_PTE_SETUP(sv32x4, rvtest_Vroot_pg_tbl, (PTE_D | PTE_A | PTE_U | PTE_W | PTE_R | PTE_V), gpa_rvtest_Vroot_pg_tbl, LEVEL0)
                                                // leaf: GPA(VS root) -> PA(VS root) R/W
  G_PTE_SETUP(sv32x4, rvtest_vlvl0_pg_tbl, (PTE_D | PTE_A | PTE_U | PTE_W | PTE_R | PTE_V), gpa_rvtest_vlvl0_pg_tbl, LEVEL0)
                                                // leaf: GPA(VS L0) -> PA(VS L0) R/W

  G_PTE_SETUP(sv32x4, rvtest_hlvl0_pg_tbl, (PTE_V), gpa_data, LEVEL1)
                                                // non-leaf: G VPN1 for data -> G L0 table
  G_PTE_SETUP(sv32x4, test_region, (PTE_D | PTE_A | PTE_U | PTE_W | PTE_R | PTE_V), gpa_data, LEVEL0)
                                                // leaf: gpa_data -> PA(test_region) R/W

  // ---- VS-stage (vsatp Sv32): GVA -> GPA  (leaf U=0 so VS R/W without SUM) ----

  VS_PTE_SETUP(sv32, GPA, gpa_code, (PTE_D | PTE_A | PTE_X | PTE_R | PTE_V), va_code, LEVEL1)
                                                // leaf: va_code -> gpa_code (X/R)

  csrr a0, mscratch                             // a0 = Msave_area (required by next macro)
  V_SAVE_AREA_SETUP(va_code, rvtest_code_begin, code, LEVEL1)
                                                // tell framework VS entry PC is under va_code

  VS_PTE_SETUP(sv32, GPA, gpa_rvtest_vlvl0_pg_tbl, (PTE_V), va_data, LEVEL1)
                                                // non-leaf: va_data VPN1 -> VS L0 table GPA
  VS_PTE_SETUP(sv32, GPA, gpa_data, (PTE_D | PTE_A | PTE_W | PTE_R | PTE_V), va_data, LEVEL0)
                                                // leaf: va_data -> gpa_data (W/R)

  VSATP_SETUP(sv32, GPA)                        // vsatp = Sv32, PPN = GPA of VS root
  HGATP_SETUP(sv32x4)                           // hgatp = Sv32x4, PPN = G root
  hfence.vvma                                   // invalidate VS-stage TLB entries
  hfence.gvma                                   // invalidate G-stage TLB entries

  // ---- stimulus ----

  LI(a5, va_data)                               // a5 = GVA pointer for store/load
  RVTEST_GOTO_LOWER_MODE VSmode                 // M -> VS (mret via framework)
  addi a2, a2, 4                                // a2 = 0x257A0005 (value to store)
  sw   a2, 0(a5)                                // two_stage_write: GVA->GPA->PA store
  nop                                           // trap-skip padding after store
  lw   a3, 0(a5)                                // two_stage_read: GVA->GPA->PA load
  nop                                           // trap-skip padding after load
  RVTEST_GOTO_MMODE                             // VS -> M via ecall to test handler

sig_vs:
  RVTEST_SIGUPD(x2, x5, x4, a3, sig_vs, sig_vs_str)  // signature: loaded value (expect 0x257A0005)

done:
  addi a2, a2, 1                                // a2 = 0x257A0006 (proves we finished)
  RVTEST_SIGUPD(x2, x5, x4, a2, done, done_str) // signature: end marker

RVTEST_CODE_END                                 // end executable text
RVTEST_DATA_BEGIN                               // start data / page-table storage

.align 12                                       // 4 KiB page align
test_region:                                    // real PA backing gpa_data
  .word 0
  .word 0
  .word 0
  .word 0

.align 12
rvtest_hlvl0_pg_tbl:                            // G-stage level-0 PTE storage
  .zero(4096)
.align 12
rvtest_vlvl0_pg_tbl:                            // VS-stage level-0 PTE storage
  .zero(4096)

sig_vs_str: .string "\"two_stage_read/write: VS lw==sw (sv32)\""  // SIGUPD label
done_str:   .string "\"done\""                                    // SIGUPD label

RVTEST_DATA_END                                 // end data section
RVTEST_SIG_SETUP                                // allocate signature memory for compare
