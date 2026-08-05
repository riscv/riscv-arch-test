// --------------------------------------------------------------------------------------------------------------------------------
// svh_vs_perm_VSmode.S
// Config: sail-rv32-max | VS=Sv32 ON, hgatp=Bare, SUM=0
// Coverpoints mapped (SvH_cg): cp_vsatp_spages_sum_rwx, cp_vsatp_perm_checks
// What this proves (one line):
//   VS enforces U=0 S-page XWR permissions and blocks U=1 pages when SUM=0.
// --------------------------------------------------------------------------------------------------------------------------------
// Test cases are as follows:
// --------------------------------------------------------------------------------------------------------------------------------
//  1. Leaf XWR=111 U=0: VS sw+lw → Successful (0x257A0401)
//  2. Leaf XWR=001 (X only) U=0: VS lw → Expected Fault (a3 stays 0)
//  3. Leaf XWR=011 (R only) U=0: VS lw → Successful; VS sw → Expected Fault (a5 stays 0)
//  4. Leaf U=1 XWR=111 SUM=0: VS lw → Expected Fault (a6 stays 0)
//
// Total Expected Faults :: 3
// --------------------------------------------------------------------------------------------------------------------------------

##### START_TEST_CONFIG #####
# REQUIRED_EXTENSIONS: [I, H, Sv32]
# MARCH: rv32ih_zicsr_zifencei
##### END_TEST_CONFIG #####

#define TEST_FILE "svh_vs_perm_VSmode.S"
#define SIGUPD_COUNT 4
#define TRAP_SIGUPD_COUNT 64
#define RVTEST_HYPERVISOR

#include "riscv_arch_test.h"

RVTEST_BEGIN

main:
  .set va_rwx,   0x008001000                    // GVA: S-page (U=0) with XWR=111
  .set va_xonly, 0x008002000                    // GVA: S-page (U=0) X-only (XWR=001)
  .set va_ronly, 0x008003000                    // GVA: S-page (U=0) R-only (XWR=011)
  .set va_u_rwx, 0x008004000                    // GVA: U=1 page with XWR=111
  .set va_code,  0x90000000                     // GVA where VS executes this code

  // ---- VS-stage (vsatp Sv32): GVA -> PA  (hgatp Bare ⇒ PTE PPN fields are real PAs) ----
  SUPERPAGE_VS_PTE_SETUP(sv32, rvtest_code_begin, (PTE_D | PTE_A | PTE_X | PTE_R | PTE_V), va_code, LEVEL1)  // leaf: va_code -> PA(code); LEVEL1 = 4 MiB X/R

  csrr a0, mscratch                             // a0 = Msave_area (required by next macro)
  V_SAVE_AREA_SETUP(va_code, rvtest_code_begin, code, LEVEL1)  // framework: VS entry PC is under va_code

  // Shared L1 non-leaf (same VPN1 for all four data VAs)
  VS_PTE_SETUP(sv32, PA, rvtest_vlvl0_pg_tbl, (PTE_V), va_rwx, LEVEL1)  // non-leaf: data VPN1 -> VS L0 table PA

  // Case 1: S-page R/W/X (U=0, XWR=111)
  VS_PTE_SETUP(sv32, PA, test_region_rwx, (PTE_D | PTE_A | PTE_X | PTE_W | PTE_R | PTE_V), va_rwx, LEVEL0)  // leaf: va_rwx -> PA(test_region_rwx) R/W/X

  // Case 2: S-page X-only (U=0, XWR=001)
  VS_PTE_SETUP(sv32, PA, test_region_xonly, (PTE_D | PTE_A | PTE_X | PTE_V), va_xonly, LEVEL0)  // leaf: va_xonly -> PA(test_region_xonly) X-only

  // Case 3: S-page R-only (U=0, XWR=011)
  VS_PTE_SETUP(sv32, PA, test_region_ronly, (PTE_D | PTE_A | PTE_R | PTE_V), va_ronly, LEVEL0)  // leaf: va_ronly -> PA(test_region_ronly) R-only

  // Case 4: U=1 R/W/X (XWR=111, SUM will stay 0)
  VS_PTE_SETUP(sv32, PA, test_region_u, (PTE_D | PTE_A | PTE_U | PTE_X | PTE_W | PTE_R | PTE_V), va_u_rwx, LEVEL0)  // leaf: va_u_rwx -> PA(test_region_u) U=1 R/W/X

  VSATP_SETUP(sv32, PA)                         // vsatp = Sv32, PPN = PA of VS root
  csrw hgatp, x0                                // hgatp = Bare (no G-stage)
  hfence.vvma                                   // invalidate VS-stage TLB entries
  hfence.gvma                                   // invalidate G-stage TLB entries (harmless with Bare)

  // SUM=0 for all cases — guest cannot access U=1 pages
  LI(t0, SSTATUS_SUM)                           // t0 = SUM bit mask (sstatus[18])
  csrc sstatus, t0                              // clear HS SUM
  csrc vsstatus, t0                             // clear VS SUM

  // Preload each SPA with distinct payloads (M-mode baseline for load cases)
  LI(t0, 0x257A0401)                            // SPA pattern for R/W/X S-page (case 1)
  la t1, test_region_rwx                        // SPA of full-permission S-page region
  sw t0, 0(t1)                                  // preload (case 1 load expects 0x257A0401)
  LI(t0, 0x257A0402)                            // SPA pattern for X-only page (case 2)
  la t1, test_region_xonly                      // SPA of X-only region
  sw t0, 0(t1)                                  // preload (load should fault before reading)
  LI(t0, 0x257A0403)                            // SPA pattern for R-only page (case 3)
  la t1, test_region_ronly                      // SPA of R-only region
  sw t0, 0(t1)                                  // preload (R-only load should succeed)
  LI(t0, 0x257A0404)                            // SPA pattern for U=1 page (case 4)
  la t1, test_region_u                          // SPA of U=1 region
  sw t0, 0(t1)                                  // preload (U-page load should fault with SUM=0)

//---------------------------------------------------------------------------------------------------------------------------------
// Test case 1: S-page XWR=111 VS sw+lw | Expected: Successful
//---------------------------------------------------------------------------------------------------------------------------------
  LI(a5, va_rwx)                                // a5 = GVA of full-permission S-page
  LI(t0, 0x257A0401)                            // store value for case 1 R/W/X S-page
  RVTEST_GOTO_LOWER_MODE VSmode                 // M -> VS
  sw   t0, 0(a5)                                // store through R/W/X S-page → SPA
  nop                                           // trap-skip padding after store
  lw   a3, 0(a5)                                // load back; expect 0x257A0401
  nop                                           // trap-skip padding after load
  RVTEST_GOTO_MMODE                             // VS -> M

  test1_rwx:
  RVTEST_SIGUPD(x2, x5, x4, a3, test1_rwx, test1_rwx_str)  // record case 1 lw result in signature

//---------------------------------------------------------------------------------------------------------------------------------
// Test case 2: S-page X-only VS lw | Expected: Expected Fault
//---------------------------------------------------------------------------------------------------------------------------------
  LI(a5, va_xonly)                              // a5 = GVA of X-only S-page
  LI(a4, 0)                                     // a4 stays 0 if lw is skipped by trap handler
  RVTEST_GOTO_LOWER_MODE VSmode                 // M -> VS
  lw   a4, 0(a5)                                // no read perm on X-only leaf → load-page-fault
  nop                                           // trap-skip padding after load
  RVTEST_GOTO_MMODE                             // VS -> M

  test2_xonly:
  RVTEST_SIGUPD(x2, x5, x4, a4, test2_xonly, test2_xonly_str)  // record case 2 fault sentinel in signature

//---------------------------------------------------------------------------------------------------------------------------------
// Test case 3: S-page R-only VS lw OK, VS sw fault | Expected: lw Successful, sw Expected Fault
//---------------------------------------------------------------------------------------------------------------------------------
  LI(a5, va_ronly)                              // a5 = GVA of R-only S-page
  RVTEST_GOTO_LOWER_MODE VSmode                 // M -> VS
  lw   a3, 0(a5)                                // R-only load permitted → success (0x257A0403)
  nop                                           // trap-skip padding after load
  LI(a4, 0)                                     // a4 stays 0 if sw is skipped by trap handler
  sw   a4, 0(a5)                                // no write perm on R-only leaf → store-page-fault
  nop                                           // trap-skip padding after store
  RVTEST_GOTO_MMODE                             // VS -> M

  test3_lw:
  RVTEST_SIGUPD(x2, x5, x4, a3, test3_lw, test3_lw_str)  // record case 3 lw result in signature

//---------------------------------------------------------------------------------------------------------------------------------
// Test case 4: U=1 XWR=111 SUM=0 VS lw | Expected: Expected Fault
//---------------------------------------------------------------------------------------------------------------------------------
  LI(a5, va_u_rwx)                              // a5 = GVA of U=1 page (SUM still 0)
  LI(a6, 0)                                     // a6 stays 0 if lw is skipped by trap handler
  RVTEST_GOTO_LOWER_MODE VSmode                 // M -> VS
  lw   a6, 0(a5)                                // U-page with SUM=0 → load-page-fault; insn skipped
  nop                                           // trap-skip padding after load
  RVTEST_GOTO_MMODE                             // VS -> M

  test4_u:
  RVTEST_SIGUPD(x2, x5, x4, a6, test4_u, test4_u_str)  // record case 4 fault sentinel in signature

//---------------------------------------------------------------------------------------------------------------------------------
RVTEST_CODE_END
RVTEST_DATA_BEGIN

.align 12                                       // 4 KiB page align
test_region_rwx:                                // real PA backing va_rwx (S-page XWR=111)
  .word 0                                       // data word (initially 0)
  .word 0                                       // padding in same page
  .word 0                                       // padding in same page
  .word 0                                       // padding in same page
.align 12                                       // 4 KiB page align
test_region_xonly:                              // real PA backing va_xonly (S-page X-only)
  .word 0                                       // data word (initially 0)
  .word 0                                       // padding in same page
  .word 0                                       // padding in same page
  .word 0                                       // padding in same page
.align 12                                       // 4 KiB page align
test_region_ronly:                              // real PA backing va_ronly (S-page R-only)
  .word 0                                       // data word (initially 0)
  .word 0                                       // padding in same page
  .word 0                                       // padding in same page
  .word 0                                       // padding in same page
.align 12                                       // 4 KiB page align
test_region_u:                                  // real PA backing va_u_rwx (U=1 page)
  .word 0                                       // data word (initially 0)
  .word 0                                       // padding in same page
  .word 0                                       // padding in same page
  .word 0                                       // padding in same page
.align 12                                       // align to 4 KiB page
rvtest_vlvl0_pg_tbl:                            // VS-stage level-0 PTE storage
  .zero(4096)                                   // 4 KiB page-table storage

test1_rwx_str:   .string "\"Mismatch on S-page R/W/X VS lw in Test Case 1!\""
test2_xonly_str: .string "\"Mismatch on S-page X-only VS lw (expect fault) in Test Case 2!\""
test3_lw_str:    .string "\"Mismatch on S-page R-only VS lw in Test Case 3!\""
test4_u_str:     .string "\"Mismatch on U=1 VS lw with SUM=0 (expect fault) in Test Case 4!\""

RVTEST_DATA_END
RVTEST_SIG_SETUP
