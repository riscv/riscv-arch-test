// --------------------------------------------------------------------------------------------------------------------------------
// svh_sum_Upages_VSmode.S
// Config: sail-rv32-max | VS=Sv32 ON, hgatp=Bare
// Coverpoints mapped (SvH_cg): cp_vsatp_sum_effects_rw, vsatp_sum_set
// What this proves (one line):
//   VS SUM controls whether VS can R/W U=1 pages (fault when SUM=0).
// --------------------------------------------------------------------------------------------------------------------------------
// Test cases are as follows:
// --------------------------------------------------------------------------------------------------------------------------------
//  1. SUM=0: VS lw of U=1 page → Expected Fault (a3 stays 0)
//  2. SUM=0: SPA still poisoned (0xDEADBEEF) → Successful
//  3. SUM=1: VS lw of U=1 page → Successful (0x257A0201)
//  4. SUM=1: SPA readback confirms store → Successful (0x257A0201)
//
// Total Expected Faults :: 1
// --------------------------------------------------------------------------------------------------------------------------------

##### START_TEST_CONFIG #####
# REQUIRED_EXTENSIONS: [I, H, Sv32]
# MARCH: rv32ih_zicsr_zifencei
##### END_TEST_CONFIG #####

#define TEST_FILE "svh_sum_Upages_VSmode.S"
#define SIGUPD_COUNT 4
#define TRAP_SIGUPD_COUNT 64
#define RVTEST_HYPERVISOR

#include "riscv_arch_test.h"

RVTEST_BEGIN

main:
  .set va_data,                 0x008001000     // GVA for U=1 data page (SUM target)
  .set va_code,                 0x90000000      // GVA where VS executes this code (U=0)

  // ---- VS-stage (vsatp Sv32): GVA -> PA  (hgatp Bare ⇒ PTE PPN fields are real PAs) ----
  // Code superpage stays U=0 so VS can fetch without SUM.
  SUPERPAGE_VS_PTE_SETUP(sv32, rvtest_code_begin, (PTE_D | PTE_A | PTE_X | PTE_R | PTE_V), va_code, LEVEL1)  // leaf: va_code -> PA(code); LEVEL1 = 4 MiB X/R

  csrr a0, mscratch                             // a0 = Msave_area (required by next macro)
  V_SAVE_AREA_SETUP(va_code, rvtest_code_begin, code, LEVEL1)  // framework: VS entry PC is under va_code

  // Data page: U=1 leaf with full XWR (coverpoint vs_pte_xwr111_u_d = 8'b11?11111)
  VS_PTE_SETUP(sv32, PA, rvtest_vlvl0_pg_tbl, (PTE_V), va_data, LEVEL1)  // non-leaf: va_data VPN1 -> VS L0 table PA
  VS_PTE_SETUP(sv32, PA, test_region, (PTE_D | PTE_A | PTE_U | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL0)  // leaf: va_data -> PA(test_region) U=1 R/W/X

  VSATP_SETUP(sv32, PA)                         // vsatp = Sv32, PPN = PA of VS root
  csrw hgatp, x0                                // hgatp = Bare (no G-stage; GPA == PA)
  hfence.vvma                                   // invalidate VS-stage TLB entries
  hfence.gvma                                   // invalidate G-stage TLB entries (harmless with Bare)

  LI(t0, 0xDEADBEEF)                            // poison value written to PA
  la t1, test_region                            // t1 = SPA of U=1 data page
  sw t0, 0(t1)                                  // SPA starts as 0xDEADBEEF (proves SUM=0 store never ran)

  LI(a5, va_data)                               // a5 = GVA pointer for guest load/store

//---------------------------------------------------------------------------------------------------------------------------------
// Test case 1: SUM=0 VS lw of U=1 page | Expected: Expected Fault
//---------------------------------------------------------------------------------------------------------------------------------
  LI(t0, SSTATUS_SUM)                           // t0 = SUM bit mask (sstatus[18])
  csrc sstatus, t0                              // clear HS SUM (shadow for vsstatus)
  csrc vsstatus, t0                             // clear VS SUM — guest cannot touch U=1 pages
  LI(a3, 0)                                     // a3 stays 0 if lw is skipped by trap handler
  LI(a4, 0)                                     // a4 stays 0 if sw is skipped by trap handler
  RVTEST_GOTO_LOWER_MODE VSmode                 // M -> VS (mret via framework)
  lw   a3, 0(a5)                                // U=1 page with SUM=0 → load-page-fault; insn skipped
  nop                                           // trap-skip padding after load
  sw   a4, 0(a5)                                // same leaf → store-page-fault; insn skipped
  nop                                           // trap-skip padding after store
  RVTEST_GOTO_MMODE                             // VS -> M via ecall to test handler

  test1_sum0_lw:
  RVTEST_SIGUPD(x2, x5, x4, a3, test1_sum0_lw, test1_sum0_lw_str)  // record case 1 fault sentinel in signature

//---------------------------------------------------------------------------------------------------------------------------------
// Test case 2: SUM=0 SPA unchanged | Expected: Successful
//---------------------------------------------------------------------------------------------------------------------------------
  // M-mode: SPA must still be poison (SUM=0 guest store never committed)
  la t1, test_region                            // t1 = SPA again
  lw t2, 0(t1)                                  // t2 expect 0xDEADBEEF (not guest-written)
  test2_sum0_spa:
  RVTEST_SIGUPD(x2, x5, x4, t2, test2_sum0_spa, test2_sum0_spa_str)  // record case 2 SPA poison check in signature

//---------------------------------------------------------------------------------------------------------------------------------
// Test case 3: SUM=1 VS lw of U=1 page | Expected: Successful
//---------------------------------------------------------------------------------------------------------------------------------
  // Split store and load into separate VS entries so each access re-walks the leaf.
  // A TLB hit would drop VS_PTE_D from .rvvi and miss coverpoint leaf_pte on the second access.
  LI(t0, SSTATUS_SUM)                           // t0 = SUM bit mask (sstatus[18])
  csrs sstatus, t0                              // set HS SUM
  csrs vsstatus, t0                             // set VS SUM — guest may R/W U=1 pages
  hfence.vvma                                   // flush stale TLB entries after SUM change

  LI(a6, 0x257A0201)                            // value to store through U=1 page
  RVTEST_GOTO_LOWER_MODE VSmode                 // M -> VS
  sw   a6, 0(a5)                                // SUM=1 store through U=1 leaf → SPA
  nop                                           // trap-skip padding after store
  RVTEST_GOTO_MMODE                             // VS -> M

  hfence.vvma                                   // force next VS load to page-walk (coverpoint sampling)
  LI(a7, 0)                                     // a7 will hold VS load result
  RVTEST_GOTO_LOWER_MODE VSmode                 // M -> VS again (fresh walk)
  lw   a7, 0(a5)                                // SUM=1 load of U=1 page; expect 0x257A0201
  nop                                           // trap-skip padding after load
  RVTEST_GOTO_MMODE                             // VS -> M

  test3_sum1_lw:
  RVTEST_SIGUPD(x2, x5, x4, a7, test3_sum1_lw, test3_sum1_lw_str)  // record case 3 lw result in signature

//---------------------------------------------------------------------------------------------------------------------------------
// Test case 4: SUM=1 SPA readback | Expected: Successful
//---------------------------------------------------------------------------------------------------------------------------------
  // M-mode: SPA must show guest store (stronger than VS lw alone)
  la t1, test_region                            // t1 = SPA of U=1 page
  lw t3, 0(t1)                                  // t3 expect 0x257A0201
  test4_sum1_spa:
  RVTEST_SIGUPD(x2, x5, x4, t3, test4_sum1_spa, test4_sum1_spa_str)  // record case 4 SPA readback in signature

//---------------------------------------------------------------------------------------------------------------------------------
RVTEST_CODE_END
RVTEST_DATA_BEGIN

.align 12                                       // 4 KiB page align
test_region:                                    // real PA backing va_data (U=1 leaf target)
  .word 0                                       // data word (initially 0)
  .word 0                                       // data word (initially 0)
  .word 0                                       // data word (initially 0)
  .word 0                                       // data word (initially 0)

.align 12                                       // align to 4 KiB page
rvtest_vlvl0_pg_tbl:                            // VS-stage level-0 PTE storage
  .zero(4096)                                   // 4 KiB page-table storage

test1_sum0_lw_str:  .string "\"Mismatch on SUM=0 lw of U=1 page (expect fault) in Test Case 1!\""
test2_sum0_spa_str: .string "\"Mismatch on SPA unchanged after SUM=0 in Test Case 2!\""
test3_sum1_lw_str:  .string "\"Mismatch on SUM=1 lw of U=1 page in Test Case 3!\""
test4_sum1_spa_str: .string "\"Mismatch on SPA after SUM=1 store in Test Case 4!\""

RVTEST_DATA_END
RVTEST_SIG_SETUP
