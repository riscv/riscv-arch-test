// --------------------------------------------------------------------------------------------------------------------------------
// svh_g_u_bit_HSmode.S
// Config: sail-rv32-max | vsatp=Bare, hgatp=Sv32x4 ON, HS HLV
// Coverpoints mapped (SvH_cg): cp_hgatp_u_mode_access
// What this proves (one line):
//   G-stage walks as U-mode; HS HLV faults when G leaf U=0, succeeds when U=1.
// --------------------------------------------------------------------------------------------------------------------------------
// Test cases are as follows:
// --------------------------------------------------------------------------------------------------------------------------------
//  1. G leaf U=1 R/W: HS hlv.w → Successful (0x257A0231)
//  2. G leaf U=0 R/W: HS hlv.w → Expected Fault (a4 stays 0)
//  3. Restore G leaf U=1 R/W: HS hlv.w → Successful (0x257A0231)
//
// Total Expected Faults :: 1
// --------------------------------------------------------------------------------------------------------------------------------

##### START_TEST_CONFIG #####
# REQUIRED_EXTENSIONS: [I, H, Sv32]
# MARCH: rv32ih_zicsr_zifencei
##### END_TEST_CONFIG #####

#define TEST_FILE "svh_g_u_bit_HSmode.S"
#define SIGUPD_COUNT 3
#define TRAP_SIGUPD_COUNT 64
#define RVTEST_HYPERVISOR

#include "riscv_arch_test.h"

RVTEST_BEGIN

main:
  .set gpa_data, 0x00C002000                     // GPA for data (vsatp Bare ⇒ HLV uses GPA directly)
  .set gpa_code, 0x80000000                      // identity GPA superpage for code + G PTs at 0x8000_0000

  // ---- G-stage (hgatp Sv32x4 ON): GPA -> PA ----
  // G-stage page walks always run as U-mode, so U=1 is required on G leaves for HS HLV data access.
  SUPERPAGE_G_PTE_SETUP(sv32x4, rvtest_code_begin, (PTE_D | PTE_A | PTE_U | PTE_X | PTE_R | PTE_V), gpa_code, LEVEL1)  // gpa_code -> PA(code)

  G_PTE_SETUP(sv32x4, rvtest_hlvl0_pg_tbl, (PTE_V), gpa_data, LEVEL1)  // non-leaf: G VPN1 for data -> G L0 table
  G_PTE_SETUP(sv32x4, test_region, (PTE_D | PTE_A | PTE_U | PTE_W | PTE_R | PTE_V), gpa_data, LEVEL0)  // leaf: U=1 R/W baseline

  // ---- vsatp Bare + hgatp ON ----
  csrw vsatp, x0                                // VS Bare (irrelevant here — all cases run in HS)
  HGATP_SETUP(sv32x4)                           // hgatp = Sv32x4, PPN = G root
  hfence.vvma                                   // flush VS TLB
  hfence.gvma                                   // flush G TLB so next access rewalks

  LI(t0, 0x257A0231)                            // known SPA pattern
  la t1, test_region                            // SPA of data page
  sw t0, 0(t1)                                  // preload known pattern at SPA before guest access

  LI(t1, gpa_data)                              // t1 = GPA pointer for all HS HLV cases

  RVTEST_GOTO_LOWER_MODE HSmode                 // enter HS once; cases 2–3 bounce M↔HS to rewrite PTEs

//---------------------------------------------------------------------------------------------------------------------------------
// Test case 1: G leaf U=1 R/W HS HLV | Expected: Successful
// cp_hgatp_u_mode_access_rw bin: g_pte_d_u=1, priv_mode HS, vsatp_bare
//---------------------------------------------------------------------------------------------------------------------------------
  LI(a3, 0)                                     // clear result register before load
  hlv.w a3, (t1)                                // G walk as U-mode sees U=1 → load succeeds
  nop                                           // trap-skip padding if previous access faults
  test1_u1:
  RVTEST_SIGUPD(x2, x5, x4, a3, test1_u1, test1_u1_str)  // record result in signature

//---------------------------------------------------------------------------------------------------------------------------------
// Test case 2: G leaf U=0 R/W HS HLV | Expected: Expected Fault
// cp_hgatp_u_mode_access_rw bin: g_pte_d_u=0 → guest-page fault on HLV
//---------------------------------------------------------------------------------------------------------------------------------
  RVTEST_GOTO_MMODE                             // back to M to rewrite G PTE safely
  G_PTE_SETUP(sv32x4, test_region, (PTE_D | PTE_A | PTE_W | PTE_R | PTE_V), gpa_data, LEVEL0)  // strip U bit; keep R/W
  hfence.gvma                                   // flush G TLB before HS retries HLV
  RVTEST_GOTO_LOWER_MODE HSmode                 // re-enter HS for HLV retry

  LI(a4, 0)                                     // sentinel: stays 0 if trap fires
  LI(t1, gpa_data)                              // reload GPA pointer (M-mode may clobber t1)
  hlv.w a4, (t1)                                // U=0 G leaf → fault (G walk as U-mode)
  nop                                           // trap-skip padding if previous access faults
  test2_u0:
  RVTEST_SIGUPD(x2, x5, x4, a4, test2_u0, test2_u0_str)  // record result in signature

//---------------------------------------------------------------------------------------------------------------------------------
// Test case 3: Restore G leaf U=1 R/W HS HLV | Expected: Successful
// cp_hgatp_u_mode_access_rw bin: back to g_pte_d_u=1
//---------------------------------------------------------------------------------------------------------------------------------
  RVTEST_GOTO_MMODE                             // back to M to restore G PTE
  G_PTE_SETUP(sv32x4, test_region, (PTE_D | PTE_A | PTE_U | PTE_W | PTE_R | PTE_V), gpa_data, LEVEL0)  // restore U=1
  hfence.gvma                                   // flush G TLB so next access rewalks
  RVTEST_GOTO_LOWER_MODE HSmode                 // re-enter HS for final HLV

  LI(a7, 0)                                     // clear result register before load
  hlv.w a7, (t1)                                // expect 0x257A0231 again
  nop                                           // trap-skip padding if previous access faults
  test3_restore:
  RVTEST_SIGUPD(x2, x5, x4, a7, test3_restore, test3_restore_str)  // record result in signature

  RVTEST_GOTO_MMODE                             // return to M-mode for test teardown

//---------------------------------------------------------------------------------------------------------------------------------
RVTEST_CODE_END
RVTEST_DATA_BEGIN

.align 12                                      // 4 KiB page align
test_region:                                  // SPA backing for GPA data leaf
  .word 0                                     // payload word (preloaded in M)
  .word 0                                     // padding in same page
  .word 0                                     // padding in same page
  .word 0                                     // padding in same page

.align 12                                      // 4 KiB page align
rvtest_hlvl0_pg_tbl:                          // G-stage L0 PTE storage (4 KiB)
  .zero(4096)                                  // reserve 4 KiB page-table storage

test1_u1_str:      .string "\"Mismatch on HS HLV with G U=1 R/W in Test Case 1!\""
test2_u0_str:      .string "\"Mismatch on HS HLV with G U=0 R/W (expect fault) in Test Case 2!\""
test3_restore_str: .string "\"Mismatch on HS HLV after G U-bit restore in Test Case 3!\""

RVTEST_DATA_END
RVTEST_SIG_SETUP
