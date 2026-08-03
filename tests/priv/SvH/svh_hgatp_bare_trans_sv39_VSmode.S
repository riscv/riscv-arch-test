// SPDX-License-Identifier: Apache-2.0
//
// svh_hgatp_bare_trans_sv39_VSmode.S
//   Config : sail-rv64-max | VS=Sv39 ON, hgatp=Bare
//   Pair   : svh_hgatp_bare_trans_VSmode.S
//
// What this proves (one line):
//   Same as RV32: VS paging ON + hgatp Bare ⇒ GVA→GPA used as SPA (Sv39 tables).
//
// Flow:
//   build Sv39 VS maps (PPNs=PA) → hgatp=0 → VS sw/lw → check SPA + hgatp==0
//
// Coverpoints mapped (SvH_cg):
//   cp_hgatp_bare_trans
//

##### START_TEST_CONFIG #####
# REQUIRED_EXTENSIONS: [I, H, Sv39]
# MARCH: rv64ih_zicsr_zifencei
##### END_TEST_CONFIG #####

#define TEST_FILE "svh_hgatp_bare_trans_sv39_VSmode.S"
#define SIGUPD_COUNT 8
#define TRAP_SIGUPD_COUNT 16
#define RVTEST_HYPERVISOR

#include "riscv_arch_test.h"

RVTEST_BEGIN                                    // start test (.text + framework setup)

main:
  LI(a2, 0x257A0030)                            // seed payload

  .set va_data, 0x0000000080010000              // guest VA for data
  .set va_code, 0x0000000090000000              // guest VA for code

  // --- VS Sv39 only (3 levels); hgatp Bare ⇒ targets are real PAs ---

  VS_PTE_SETUP(sv39, PA, rvtest_vlvl1_pg_tbl, (PTE_V), va_code, LEVEL2)  // non-leaf → mid table
  SUPERPAGE_VS_PTE_SETUP(sv39, rvtest_code_begin, (PTE_D | PTE_A | PTE_X | PTE_R | PTE_V), va_code, LEVEL1)  // 2 MiB leaf: va_code → PA(code)

  csrr a0, mscratch                             // a0 = M save area (needed by next macro)
  V_SAVE_AREA_SETUP(va_code, rvtest_code_begin, code, LEVEL1)  // tell framework VS entry PC uses this VA

  VS_PTE_SETUP(sv39, PA, rvtest_vlvl1_pg_tbl, (PTE_V), va_data, LEVEL2)  // VS non-leaf: VPN2 → VS L1 table GPA
  VS_PTE_SETUP(sv39, PA, rvtest_vlvl0_pg_tbl, (PTE_V), va_data, LEVEL1)  // VS non-leaf: → VS L0 table
  VS_PTE_SETUP(sv39, PA, test_region, (PTE_D | PTE_A | PTE_W | PTE_R | PTE_V), va_data, LEVEL0)  // leaf: va_data → PA(test_region)

  VSATP_SETUP(sv39, PA)                         // VS on
  csrw hgatp, x0                                // G Bare
  hfence.vvma                                   // flush VS-stage TLB
  hfence.gvma                                   // flush G-stage TLB

  LI(t0, 0xDEADBEEF)                            // poison pattern
  la t1, test_region                            // t1 = real address of test_region
  sw t0, 0(t1)                                  // store pattern to memory

  LI(a5, va_data)                               // a5 = address/pointer for guest access
  RVTEST_GOTO_LOWER_MODE VSmode                 // enter VS (guest)
  addi a2, a2, 1                                // bump end marker
  sw   a2, 0(a5)                                // store via VS only
  nop                                           // pad (trap handler may skip prior insn)
  lw   a3, 0(a5)                                // load from a5 → a3
  nop                                           // pad (trap handler may skip prior insn)
  RVTEST_GOTO_MMODE                             // return to M-mode

  la t1, test_region                            // t1 = real address of test_region
  lw t2, 0(t1)                                  // expect store visible
  csrr t3, hgatp                                // expect 0

sig_vs:
  RVTEST_SIGUPD(x2, x5, x4, a3, sig_vs, sig_vs_str)  // save register onto signature answer sheet
sig_pa:
  RVTEST_SIGUPD(x2, x5, x4, t2, sig_pa, sig_pa_str)  // save register onto signature answer sheet
sig_hgatp:
  RVTEST_SIGUPD(x2, x5, x4, t3, sig_hgatp, sig_hgatp_str)  // save register onto signature answer sheet

done:
  addi a2, a2, 1                                // bump end marker
  RVTEST_SIGUPD(x2, x5, x4, a2, done, done_str) // save register onto signature answer sheet

RVTEST_CODE_END                                 // end executable code
RVTEST_DATA_BEGIN                               // start data / tables

.align 12                                       // align to 4 KiB page
test_region:
  .word 0                                       // data word (initially 0)
  .word 0                                       // data word (initially 0)
  .word 0                                       // data word (initially 0)
  .word 0                                       // data word (initially 0)

.align 12                                       // align to 4 KiB page
rvtest_vlvl1_pg_tbl:
  .zero(4096)                                   // 4 KiB page-table storage
.align 12                                       // align to 4 KiB page
rvtest_vlvl0_pg_tbl:
  .zero(4096)                                   // 4 KiB page-table storage

sig_vs_str:    .string "\"cp_hgatp_bare_trans: VS lw==sw\""
sig_pa_str:    .string "\"cp_hgatp_bare_trans: SPA==sw\""
sig_hgatp_str: .string "\"cp_hgatp_bare_trans: hgatp==0\""
done_str:      .string "\"done\""

RVTEST_DATA_END                                 // end data section
RVTEST_SIG_SETUP                                // allocate signature answer sheet
