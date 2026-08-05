// --------------------------------------------------------------------------------------------------------------------------------
// svh_mprv_hgatp_Mmode.S
// Config: sail-rv32-max | M-mode MPRV×MPP/MPV×hgatp; vsatp/satp Bare
// Coverpoints mapped (SvH_cg): cp_hgatp_mprv_effects
// What this proves (one line):
//   MPRV×MPP×MPV selects how M-mode loads walk through hgatp (and HLV).
// --------------------------------------------------------------------------------------------------------------------------------
// Test cases are as follows:
// --------------------------------------------------------------------------------------------------------------------------------
//  1. Direct SPA lw of X-only page (baseline) → Successful (0x257A0151)
//  2. MPRV=1, MPP=M lw of SPA → Successful (no G walk)
//  3. MPRV=1, MPP=S, MPV=0 (HS) lw of SPA → Successful (no G walk)
//  4. MPRV=1, MPP=S, MPV=1 (VS) lw of X-only GPA → Expected Fault (a6 stays 0)
//  5. MPRV=1, MPP=U, MPV=0 lw of SPA → Successful (no G walk)
//  6. MPRV=1, MPP=U, MPV=1 (VU) lw of X-only GPA → Expected Fault (s1 stays 0)
//  7. HLV of R/W GPA (ignores MPRV) → Successful (0x257A0152)
//
// Total Expected Faults :: 2
// --------------------------------------------------------------------------------------------------------------------------------

##### START_TEST_CONFIG #####
# REQUIRED_EXTENSIONS: [I, H, Sv32]
# MARCH: rv32ih_zicsr_zifencei
##### END_TEST_CONFIG #####

#define TEST_FILE "svh_mprv_hgatp_Mmode.S"
#define SIGUPD_COUNT 7
#define TRAP_SIGUPD_COUNT 16
#define RVTEST_HYPERVISOR

#include "riscv_arch_test.h"

RVTEST_BEGIN

main:
  .set gpa_xonly, 0x00C002000               // GPA mapped execute-only (VS/VU fault case)
  .set gpa_rw,    0x00C003000               // GPA mapped read/write (HLV success case)

  // ---- G-stage (hgatp Sv32x4): X-only and R/W GPA maps for MPRV matrix ----
  // --- G-stage X-only map (VS/VU MPRV lw must fault) ---
  G_PTE_SETUP(sv32x4, rvtest_hlvl0_pg_tbl, (PTE_V), gpa_xonly, LEVEL1)  // point gpa_xonly VPN1 to the G L0 table
  G_PTE_SETUP(sv32x4, test_region_x, (PTE_D | PTE_A | PTE_U | PTE_X | PTE_V), gpa_xonly, LEVEL0)  // map gpa_xonly -> PA(test_region_x) as execute-only

  // --- G-stage R/W map (HLV ignores MPRV; needs read perm) ---
  G_PTE_SETUP(sv32x4, rvtest_hlvl0_pg_tbl, (PTE_V), gpa_rw, LEVEL1)  // point gpa_rw VPN1 to the G L0 table
  G_PTE_SETUP(sv32x4, test_region_rw, (PTE_D | PTE_A | PTE_U | PTE_W | PTE_R | PTE_V), gpa_rw, LEVEL0)  // map gpa_rw -> PA(test_region_rw) with read/write

  csrw vsatp, x0                            // VS Bare — isolate hgatp MPRV effects
  csrw satp, x0                             // S Bare — HS loads use SPA when MPV=0
  HGATP_SETUP(sv32x4)                       // G on: virtualized loads (MPV=1) walk hgatp
  hfence.vvma                               // flush VS TLB (vsatp Bare)
  hfence.gvma                               // flush G TLB after hgatp setup

  LI(t0, 0x257A0151)                        // expected value in the X-only physical page
  la t1, test_region_x                      // t1 = real PA for X-only backing memory
  sw t0, 0(t1)                              // store the X-only page value in real memory
  LI(t0, 0x257A0152)                        // expected value in the read/write physical page
  la t1, test_region_rw                     // t1 = real PA for read/write backing memory
  sw t0, 0(t1)                              // store the read/write page value in real memory

//---------------------------------------------------------------------------------------------------------------------------------
// Test case 1: Direct SPA lw (baseline) | Expected: Successful
//---------------------------------------------------------------------------------------------------------------------------------
  la t1, test_region_x                      // t1 = real PA for X-only backing memory
  lw a3, 0(t1)                              // read physical memory directly without hgatp
  test1_spa:
  RVTEST_SIGUPD(x2, x5, x4, a3, test1_spa, test1_spa_str)  // record case 1 direct SPA lw in signature

//---------------------------------------------------------------------------------------------------------------------------------
// Test case 2: MPRV=1, MPP=M lw of SPA | Expected: Successful
//---------------------------------------------------------------------------------------------------------------------------------
  // MPRV matrix case: MPRV=1, MPP=M, MPV=0 → M-mode load of SPA (no G walk)
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
  test2_m:
  RVTEST_SIGUPD(x2, x5, x4, a4, test2_m, test2_m_str)  // record case 2 MPRV MPP=M load in signature

//---------------------------------------------------------------------------------------------------------------------------------
// Test case 3: MPRV=1, MPP=S, MPV=0 (HS) lw of SPA | Expected: Successful
//---------------------------------------------------------------------------------------------------------------------------------
  // MPRV matrix case: MPRV=1, MPP=S, MPV=0 → HS load of SPA (satp Bare, no G walk)
  LI(t0, MSTATUS_MPP)                       // t0 = bit mask for MPP field
  csrc mstatus, t0                          // clear old MPP bits
  LI(t0, MPP_SMODE)                         // t0 = value that selects S/HS memory rules
  csrs mstatus, t0                          // set MPP=S in mstatus
  LI(a5, 0)                                 // a5 should receive the X-only page value
  la t1, test_region_x                      // t1 = real PA (satp Bare → no translate)
  lw a5, 0(t1)                              // load as HS → no G walk; should succeed
  nop                                       // trap-skip padding after load
  test3_hs:
  RVTEST_SIGUPD(x2, x5, x4, a5, test3_hs, test3_hs_str)  // record case 3 MPRV HS load in signature

//---------------------------------------------------------------------------------------------------------------------------------
// Test case 4: MPRV=1, MPP=S, MPV=1 (VS) lw of X-only GPA | Expected: Expected Fault
//---------------------------------------------------------------------------------------------------------------------------------
  // MPRV matrix case: MPRV=1, MPP=S, MPV=1 → VS load through hgatp; X-only G leaf faults
  LI(t0, MSTATUSH_MPV)                      // t0 = bit mask for MPV
  csrs mstatush, t0                         // set MPV so access is virtualized (VS)
  LI(a6, 0)                                 // a6 stays 0 if the load faults and is skipped
  LI(t1, gpa_xonly)                         // t1 = GPA that hgatp maps execute-only
  lw a6, 0(t1)                              // load as VS through G; should fault (no R)
  nop                                       // trap-skip padding after load
  test4_vs:
  RVTEST_SIGUPD(x2, x5, x4, a6, test4_vs, test4_vs_str)  // record case 4 VS X-only GPA fault in signature

//---------------------------------------------------------------------------------------------------------------------------------
// Test case 5: MPRV=1, MPP=U, MPV=0 lw of SPA | Expected: Successful
//---------------------------------------------------------------------------------------------------------------------------------
  // MPRV matrix case: MPRV=1, MPP=U, MPV=0 → U-mode load of SPA (no G walk)
  LI(t0, MSTATUS_MPP)                       // t0 = bit mask for MPP field
  csrc mstatus, t0                          // clear MPP → MPP=U (00)
  LI(t0, MSTATUSH_MPV)                      // t0 = bit mask for MPV
  csrc mstatush, t0                         // clear MPV (not virtualized)
  LI(a7, 0)                                 // a7 should receive the X-only page value
  la t1, test_region_x                      // t1 = real PA
  lw a7, 0(t1)                              // load as U → no G walk; should succeed
  nop                                       // trap-skip padding after load
  test5_u:
  RVTEST_SIGUPD(x2, x5, x4, a7, test5_u, test5_u_str)  // record case 5 MPRV U load in signature

//---------------------------------------------------------------------------------------------------------------------------------
// Test case 6: MPRV=1, MPP=U, MPV=1 (VU) lw of X-only GPA | Expected: Expected Fault
//---------------------------------------------------------------------------------------------------------------------------------
  // MPRV matrix case: MPRV=1, MPP=U, MPV=1 → VU load through hgatp; X-only G leaf faults
  LI(t0, MSTATUSH_MPV)                      // t0 = bit mask for MPV
  csrs mstatush, t0                         // set MPV so access is virtualized (VU)
  LI(s1, 0)                                 // s1 stays 0 if the load faults and is skipped
  LI(t1, gpa_xonly)                         // t1 = GPA that hgatp maps execute-only
  lw s1, 0(t1)                              // load as VU through G; should fault (no R)
  nop                                       // trap-skip padding after load
  test6_vu:
  RVTEST_SIGUPD(x2, x5, x4, s1, test6_vu, test6_vu_str)  // record case 6 VU X-only GPA fault in signature

//---------------------------------------------------------------------------------------------------------------------------------
// Test case 7: HLV of R/W GPA (ignores MPRV) | Expected: Successful
//---------------------------------------------------------------------------------------------------------------------------------
  // HLV always walks hgatp as HS (ignores MPRV/MPP/MPV); R/W G leaf succeeds
  LI(s2, 0)                                 // s2 should receive the read/write page value
  LI(t1, gpa_rw)                            // t1 = GPA that hgatp maps read/write
  hlv.w s2, (t1)                            // hypervisor-load word through hgatp into s2
  nop                                       // trap-skip padding after HLV

  LI(t0, MSTATUS_MPRV)                      // t0 = bit mask for MPRV
  csrc mstatus, t0                          // clear MPRV before finishing
  LI(t0, MSTATUSH_MPV)                      // t0 = bit mask for MPV
  csrc mstatush, t0                         // clear MPV before finishing

  test7_hlv:
  RVTEST_SIGUPD(x2, x5, x4, s2, test7_hlv, test7_hlv_str)  // record case 7 HLV R/W GPA load in signature

//---------------------------------------------------------------------------------------------------------------------------------
RVTEST_CODE_END
RVTEST_DATA_BEGIN
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

test1_spa_str: .string "\"Mismatch on direct SPA load in Test Case 1!\""
test2_m_str:   .string "\"Mismatch on MPRV MPP=M load in Test Case 2!\""
test3_hs_str:  .string "\"Mismatch on MPRV HS load in Test Case 3!\""
test4_vs_str:  .string "\"Mismatch on MPRV VS X-only GPA load (expect fault) in Test Case 4!\""
test5_u_str:   .string "\"Mismatch on MPRV U load in Test Case 5!\""
test6_vu_str:  .string "\"Mismatch on MPRV VU X-only GPA load (expect fault) in Test Case 6!\""
test7_hlv_str: .string "\"Mismatch on HLV R/W GPA load in Test Case 7!\""

RVTEST_DATA_END
RVTEST_SIG_SETUP
