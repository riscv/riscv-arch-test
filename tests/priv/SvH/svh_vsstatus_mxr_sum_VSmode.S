// --------------------------------------------------------------------------------------------------------------------------------
// svh_vsstatus_mxr_sum_VSmode.S
// Config: sail-rv32-max | VS=Sv32 ON, hgatp=Bare
// Coverpoints mapped (SvH_cg): cp_vsstatus_mxr_sum
// What this proves (one line):
//   VS MXR/SUM (via sstatus↔vsstatus) control X-only and U-page load permissions.
// --------------------------------------------------------------------------------------------------------------------------------
// Test cases are as follows:
// --------------------------------------------------------------------------------------------------------------------------------
//  1. MXR=0 SUM=0, S-page X-only: VS lw → Expected Fault (a3 stays 0)
//  2. MXR=1 SUM=0, S-page X-only: VS lw → Successful (0x257A0501)
//  3. MXR=0 SUM=0, U-page X-only: VS lw → Expected Fault (a4 stays 0)
//  4. MXR=1 SUM=1, U-page XWR=111: VS lw → Successful (0x257A0502)
//
// Total Expected Faults :: 2
// --------------------------------------------------------------------------------------------------------------------------------

##### START_TEST_CONFIG #####
# REQUIRED_EXTENSIONS: [I, H, Sv32]
# MARCH: rv32ih_zicsr_zifencei
##### END_TEST_CONFIG #####

#define TEST_FILE "svh_vsstatus_mxr_sum_VSmode.S"
#define SIGUPD_COUNT 4
#define TRAP_SIGUPD_COUNT 64
#define RVTEST_HYPERVISOR

// Mode hops (T-SBI) — return-to-M always uses RVTEST_TSBI_GOTO_MMODE (ecall a0=1;
//   handler rtn2mmode relocates EPC VA→PA). Enter:
//   • Code at PA / identity: RVTEST_TSBI_GOTO_VSMODE / _SMODE (ecall a0=4/2)
//   • Guest code VA≠PA (V_SAVE_AREA_*): RVTEST_GOTO_LOWER_MODE (mret + PA↔VA relocate)
#include "riscv_arch_test.h"

RVTEST_BEGIN

main:
  .set va_x_s,  0x008001000                     // GVA: S-page (U=0) X-only leaf
  .set va_x_u,  0x008002000                     // GVA: U-page X-only leaf
  .set va_u_rw, 0x008003000                     // GVA: U-page R/W/X leaf (needs SUM=1)
  .set va_code, 0x90000000                      // GVA where VS executes this code

  // ---- VS-stage (vsatp Sv32): GVA -> PA  (hgatp Bare ⇒ PTE PPN fields are real PAs) ----
  SUPERPAGE_VS_PTE_SETUP(sv32, rvtest_code_begin, (PTE_D | PTE_A | PTE_X | PTE_R | PTE_V), va_code, LEVEL1)  // leaf: va_code -> PA(code); LEVEL1 = 4 MiB X/R

  csrr a0, mscratch                             // a0 = Msave_area (required by next macro)
  V_SAVE_AREA_SETUP(va_code, rvtest_code_begin, code, LEVEL1)  // framework: VS entry PC is under va_code

  VS_PTE_SETUP(sv32, PA, rvtest_vlvl0_pg_tbl, (PTE_V), va_x_s, LEVEL1)  // non-leaf: data VPN1 -> VS L0 table PA

  // S-page X-only (XWR=001, U=0) — MXR decides whether load is allowed
  VS_PTE_SETUP(sv32, PA, test_region_x_s, (PTE_D | PTE_A | PTE_X | PTE_V), va_x_s, LEVEL0)  // leaf: va_x_s -> PA(test_region_x_s) X-only U=0

  // U-page X-only — needs MXR for load, but U=1 still blocks without SUM
  VS_PTE_SETUP(sv32, PA, test_region_x_u, (PTE_D | PTE_A | PTE_U | PTE_X | PTE_V), va_x_u, LEVEL0)  // leaf: va_x_u -> PA(test_region_x_u) X-only U=1

  // U-page R/W/X — SUM=1 required for any U=1 access
  VS_PTE_SETUP(sv32, PA, test_region_u_rw, (PTE_D | PTE_A | PTE_U | PTE_X | PTE_W | PTE_R | PTE_V), va_u_rw, LEVEL0)  // leaf: va_u_rw -> PA(test_region_u_rw) U=1 R/W/X

  VSATP_SETUP(sv32, PA)                         // vsatp = Sv32, PPN = PA of VS root
  csrw hgatp, x0                                // hgatp = Bare (no G-stage)
  hfence.vvma                                   // invalidate VS-stage TLB entries
  hfence.gvma                                   // invalidate G-stage TLB entries (harmless with Bare)

  LI(t0, 0x257A0501)                            // SPA pattern for S-page X-only (case 2 read target)
  la t1, test_region_x_s                        // SPA of S-page X-only region
  sw t0, 0(t1)                                  // preload (MXR=1 load expects 0x257A0501)
  LI(t0, 0xDEADBEEF)                            // poison pattern (must not appear if case 3 faults)
  la t1, test_region_x_u                        // SPA of U-page X-only region
  sw t0, 0(t1)                                  // poison SPA for U-page X-only (case 3 should fault before read)
  LI(t0, 0x257A0502)                            // SPA pattern for U-page R/W/X (case 4 read target)
  la t1, test_region_u_rw                       // SPA of U-page R/W/X region
  sw t0, 0(t1)                                  // preload (SUM=1 load expects 0x257A0502)

//---------------------------------------------------------------------------------------------------------------------------------
// Test case 1: MXR=0 SUM=0 S-page X-only VS lw | Expected: Expected Fault
//---------------------------------------------------------------------------------------------------------------------------------
  LI(t0, SSTATUS_MXR | SSTATUS_SUM)             // t0 = MXR|SUM bit masks (sstatus[19|18])
  csrc sstatus, t0                              // clear HS MXR and SUM
  csrc vsstatus, t0                             // clear VS MXR and SUM — strict permission checks

  LI(a5, va_x_s)                                // a5 = GVA of S-page X-only leaf
  LI(a3, 0)                                     // a3 stays 0 if lw is skipped by trap handler
  RVTEST_GOTO_LOWER_MODE VSmode                 // M→VSmode mret + PA↔VA relocate (guest code VA≠PA; T-SBI enter lacks relocate)
  lw   a3, 0(a5)                                // X-only without MXR → load-page-fault; insn skipped
  nop                                           // trap-skip padding after load
  RVTEST_TSBI_GOTO_MMODE                       // T-SBI: ecall a0=1 → M (rtn2mmode VA→PA relocate)

  test1_mxr0:
  RVTEST_SIGUPD(x2, x5, x4, a3, test1_mxr0, test1_mxr0_str)  // record case 1 fault sentinel in signature

//---------------------------------------------------------------------------------------------------------------------------------
// Test case 2: MXR=1 SUM=0 S-page X-only VS lw | Expected: Successful
//---------------------------------------------------------------------------------------------------------------------------------
  LI(t0, SSTATUS_MXR)                           // t0 = MXR bit mask (sstatus[19])
  csrs sstatus, t0                              // set HS MXR
  csrs vsstatus, t0                             // set VS MXR — X-only pages become readable
  hfence.vvma                                   // flush TLB after MXR change (permission reinterpretation)

  LI(a5, va_x_s)                                // a5 = same S-page X-only GVA
  LI(a4, 0)                                     // a4 will hold load result (0 if fault skipped insn)
  RVTEST_GOTO_LOWER_MODE VSmode                 // M→VSmode mret + PA↔VA relocate (guest code VA≠PA; T-SBI enter lacks relocate)
  lw   a4, 0(a5)                                // MXR=1 treats X-only as readable; expect 0x257A0501
  nop                                           // trap-skip padding after load
  RVTEST_TSBI_GOTO_MMODE                       // T-SBI: ecall a0=1 → M (rtn2mmode VA→PA relocate)

  test2_mxr1:
  RVTEST_SIGUPD(x2, x5, x4, a4, test2_mxr1, test2_mxr1_str)  // record case 2 lw result in signature

//---------------------------------------------------------------------------------------------------------------------------------
// Test case 3: MXR=0 SUM=0 U-page X-only VS lw | Expected: Expected Fault
//---------------------------------------------------------------------------------------------------------------------------------
  LI(t0, SSTATUS_MXR | SSTATUS_SUM)             // t0 = MXR|SUM bit masks
  csrc sstatus, t0                              // clear MXR and SUM again
  csrc vsstatus, t0                             // clear VS MXR and SUM — U-page blocked without SUM
  hfence.vvma                                   // flush TLB after flag change

  LI(a5, va_x_u)                                // a5 = GVA of U-page X-only leaf
  LI(a6, 0)                                     // a6 stays 0 if lw is skipped by trap handler
  RVTEST_GOTO_LOWER_MODE VSmode                 // M→VSmode mret + PA↔VA relocate (guest code VA≠PA; T-SBI enter lacks relocate)
  lw   a6, 0(a5)                                // U-page blocked by SUM=0 even if MXR were set → fault
  nop                                           // trap-skip padding after load
  RVTEST_TSBI_GOTO_MMODE                       // T-SBI: ecall a0=1 → M (rtn2mmode VA→PA relocate)

  test3_u_xonly:
  RVTEST_SIGUPD(x2, x5, x4, a6, test3_u_xonly, test3_u_xonly_str)  // record case 3 fault sentinel in signature

//---------------------------------------------------------------------------------------------------------------------------------
// Test case 4: MXR=1 SUM=1 U-page XWR=111 VS lw | Expected: Successful
//---------------------------------------------------------------------------------------------------------------------------------
  LI(t0, SSTATUS_MXR | SSTATUS_SUM)             // t0 = MXR|SUM bit masks
  csrs sstatus, t0                              // set both MXR and SUM
  csrs vsstatus, t0                             // guest may load U=1 pages; MXR available if needed
  hfence.vvma                                   // flush TLB before final load

  LI(a5, va_u_rw)                               // a5 = GVA of U=1 R/W/X leaf
  LI(a7, 0)                                     // a7 will hold load result (0 if fault skipped insn)
  RVTEST_GOTO_LOWER_MODE VSmode                 // M→VSmode mret + PA↔VA relocate (guest code VA≠PA; T-SBI enter lacks relocate)
  lw   a7, 0(a5)                                // SUM=1 allows U-page load; expect 0x257A0502
  nop                                           // trap-skip padding after load
  RVTEST_TSBI_GOTO_MMODE                       // T-SBI: ecall a0=1 → M (rtn2mmode VA→PA relocate)

  test4_u_rwx:
  RVTEST_SIGUPD(x2, x5, x4, a7, test4_u_rwx, test4_u_rwx_str)  // record case 4 lw result in signature

//---------------------------------------------------------------------------------------------------------------------------------
RVTEST_CODE_END
RVTEST_DATA_BEGIN

.align 12                                       // 4 KiB page align
test_region_x_s:                                // real PA backing va_x_s (S-page X-only)
  .word 0                                       // data word (initially 0)
  .word 0                                       // padding in same page
  .word 0                                       // padding in same page
  .word 0                                       // padding in same page
.align 12                                       // 4 KiB page align
test_region_x_u:                                // real PA backing va_x_u (U-page X-only)
  .word 0                                       // data word (initially 0)
  .word 0                                       // padding in same page
  .word 0                                       // padding in same page
  .word 0                                       // padding in same page
.align 12                                       // 4 KiB page align
test_region_u_rw:                               // real PA backing va_u_rw (U-page R/W/X)
  .word 0                                       // data word (initially 0)
  .word 0                                       // padding in same page
  .word 0                                       // padding in same page
  .word 0                                       // padding in same page
.align 12                                       // align to 4 KiB page
rvtest_vlvl0_pg_tbl:                            // VS-stage level-0 PTE storage
  .zero(4096)                                   // 4 KiB page-table storage

test1_mxr0_str:    .string "\"Mismatch on MXR=0 S-page X-only VS lw (expect fault) in Test Case 1!\""
test2_mxr1_str:    .string "\"Mismatch on MXR=1 S-page X-only VS lw in Test Case 2!\""
test3_u_xonly_str: .string "\"Mismatch on MXR=0 U-page X-only VS lw (expect fault) in Test Case 3!\""
test4_u_rwx_str:   .string "\"Mismatch on MXR=1 SUM=1 U-page VS lw in Test Case 4!\""

RVTEST_DATA_END
RVTEST_SIG_SETUP
