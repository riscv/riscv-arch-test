// SPDX-License-Identifier: Apache-2.0
//
// svh_two_stage_mxr_VSmode.S
//   Config : sail-rv32-max | VS=Sv32 + G=Sv32x4 (both ON)
//   Pair   : svh_two_stage_mxr_sv39_VSmode.S (write later)
//
// Coverpoints mapped (SvH_cg):
//   cp_two_stage_mxr — VS lw of X-only × G X-only × MXR={0,1}
// What this proves: MXR controls whether VS can load from execute-only pages through both stages.
// Flow: map X-only data -> try VS load with MXR=0 -> try again with MXR=1 -> save PASS/FAIL signatures.
// Gloss: MXR = Make eXecutable Readable, PTE = page-table entry, VS = guest OS-like mode.
// Not mapped: two_stage_read/write, cp_vsstatus_mxr_sum, …
//

##### START_TEST_CONFIG #####
# REQUIRED_EXTENSIONS: [I, H, Sv32]     # base I, hypervisor H, Sv32 paging
# MARCH: rv32ih_zicsr_zifencei          # RV32 march for this ELF
##### END_TEST_CONFIG #####

#define TEST_FILE "svh_two_stage_mxr_VSmode.S"  // name used in trap / fail messages
#define SIGUPD_COUNT 8                          // signature slots for RVTEST_SIGUPD
#define TRAP_SIGUPD_COUNT 16                    // signature slots for trap path
#define RVTEST_HYPERVISOR                       // enable H PTE / mode macros

#include "riscv_arch_test.h"                    // trap handler, GOTO_*, PTE helpers

RVTEST_BEGIN                                    // open .text + framework prolog

main:
  LI(a2, 0x257A0100)                            // seed value for the done signature

  .set va_data,                 0x008001000     // GVA for the VS load from X-only data
  .set va_code,                 0x90000000      // GVA where VS executes this code
  .set gpa_data,                0x00C002000     // GPA behind va_data
  .set gpa_code,                0x012000000     // GPA behind va_code (4 MiB aligned)
  .set gpa_rvtest_Vroot_pg_tbl, 0x01000A000     // GPA of VS root page table
  .set gpa_rvtest_vlvl0_pg_tbl, 0x01000B000     // GPA of VS level-0 page table

  // --- G-stage maps for guest code and VS page tables ---
  SUPERPAGE_G_PTE_SETUP(sv32x4, rvtest_code_begin, (PTE_D | PTE_A | PTE_U | PTE_X | PTE_R | PTE_V), gpa_code, LEVEL1)  // map gpa_code -> PA(code) so VS can execute
  G_PTE_SETUP(sv32x4, rvtest_hlvl0_pg_tbl, (PTE_V), gpa_rvtest_Vroot_pg_tbl, LEVEL1)  // point G-stage root entry to G L0 table
  G_PTE_SETUP(sv32x4, rvtest_Vroot_pg_tbl, (PTE_D | PTE_A | PTE_U | PTE_W | PTE_R | PTE_V), gpa_rvtest_Vroot_pg_tbl, LEVEL0)  // map GPA(VS root) -> PA(VS root) for page-table walks
  G_PTE_SETUP(sv32x4, rvtest_vlvl0_pg_tbl, (PTE_D | PTE_A | PTE_U | PTE_W | PTE_R | PTE_V), gpa_rvtest_vlvl0_pg_tbl, LEVEL0)  // map GPA(VS L0) -> PA(VS L0) for page-table walks

  // --- G-stage X-only data map ---
  // G leaf: execute-only (R=0,X=1), U=1
  G_PTE_SETUP(sv32x4, rvtest_hlvl0_pg_tbl, (PTE_V), gpa_data, LEVEL1)  // point G-stage data entry to G L0 table
  G_PTE_SETUP(sv32x4, test_region, (PTE_D | PTE_A | PTE_U | PTE_X | PTE_V), gpa_data, LEVEL0)  // map gpa_data -> PA(test_region) as execute-only

  // --- VS-stage maps for guest code and X-only data ---
  VS_PTE_SETUP(sv32, GPA, gpa_code, (PTE_D | PTE_A | PTE_X | PTE_R | PTE_V), va_code, LEVEL1)  // map va_code -> gpa_code so VS can fetch code
  csrr a0, mscratch                             // read M save area pointer for the next macro
  V_SAVE_AREA_SETUP(va_code, rvtest_code_begin, code, LEVEL1)  // tell framework VS entry PC is under va_code

  // VS leaf: execute-only (R=0,X=1)
  VS_PTE_SETUP(sv32, GPA, gpa_rvtest_vlvl0_pg_tbl, (PTE_V), va_data, LEVEL1)  // point VS data entry to VS L0 table GPA
  VS_PTE_SETUP(sv32, GPA, gpa_data, (PTE_D | PTE_A | PTE_X | PTE_V), va_data, LEVEL0)  // map va_data -> gpa_data as execute-only

  VSATP_SETUP(sv32, GPA)                        // write vsatp so VS-stage translation is on
  HGATP_SETUP(sv32x4)                           // write hgatp so G-stage translation is on
  hfence.vvma                                   // clear stale VS-stage translations
  hfence.gvma                                   // clear stale G-stage translations

  LI(t0, 0x257A0101)                            // expected data value for successful MXR=1 load
  la t1, test_region                            // t1 = real PA backing gpa_data
  sw t0, 0(t1)                                  // store the expected value in real memory

  LI(a5, va_data)                               // a5 = guest virtual address to load

  // ---- MXR=0: load of X-only must fault ----
  LI(t0, SSTATUS_MXR)                           // t0 = bit mask for MXR
  csrc sstatus, t0                              // clear HS MXR setting
  csrc vsstatus, t0                             // clear VS MXR setting
  LI(a3, 0)                                     // a3 stays 0 if the load faults and is skipped
  RVTEST_GOTO_LOWER_MODE VSmode                 // enter VS mode to run the guest load
  lw   a3, 0(a5)                                // expect fault → skipped
  nop                                           // trap-skip padding after load
  RVTEST_GOTO_MMODE                             // return from VS to M-mode test code

  // ---- MXR=1: HS sstatus + vsstatus → load allowed ----
  LI(t0, SSTATUS_MXR)                           // t0 = bit mask for MXR
  csrs sstatus, t0                              // set HS MXR setting
  csrs vsstatus, t0                             // set VS MXR setting
  hfence.vvma                                   // clear VS-stage translations after status change
  LI(a4, 0)                                     // a4 should receive the real memory value
  RVTEST_GOTO_LOWER_MODE VSmode                 // enter VS mode for the allowed load
  lw   a4, 0(a5)                                // expect 0x257A0101
  nop                                           // trap-skip padding after load
  RVTEST_GOTO_MMODE                             // return from VS to M-mode test code

sig_mxr0:
  RVTEST_SIGUPD(x2, x5, x4, a3, sig_mxr0, sig_mxr0_str)  // save MXR=0 fault result for PASS/FAIL
sig_mxr1:
  RVTEST_SIGUPD(x2, x5, x4, a4, sig_mxr1, sig_mxr1_str)  // save MXR=1 load result for PASS/FAIL

done:
  addi a2, a2, 2                                // a2 = 0x257A0102; proves we finished both cases
  RVTEST_SIGUPD(x2, x5, x4, a2, done, done_str) // save end marker for PASS/FAIL

RVTEST_CODE_END                                 // end executable text
RVTEST_DATA_BEGIN                               // start data / page-table storage

.align 12                                       // 4 KiB page align
test_region:                                    // real PA backing the X-only guest data page
  .word 0                                       // data slot used by the load
  .word 0                                       // padding in the same page
  .word 0                                       // padding in the same page
  .word 0                                       // padding in the same page
.align 12                                       // align to 4 KiB page
rvtest_hlvl0_pg_tbl:                            // G-stage level-0 PTE storage
  .zero(4096)                                   // reserve one page for G L0 table
.align 12                                       // align to 4 KiB page
rvtest_vlvl0_pg_tbl:                            // VS-stage level-0 PTE storage
  .zero(4096)                                   // reserve one page for VS L0 table

sig_mxr0_str: .string "\"cp_two_stage_mxr: MXR0 fault\""  // SIGUPD label
sig_mxr1_str: .string "\"cp_two_stage_mxr: MXR1 load\""   // SIGUPD label
done_str:     .string "\"done\""                          // SIGUPD label

RVTEST_DATA_END                                 // end data section
RVTEST_SIG_SETUP                                // allocate signature memory for compare
