// --------------------------------------------------------------------------------------------------------------------------------
// svh_hgatp_fault_VSmode.S
// Config: sail-rv32-max | vsatp=Bare, hgatp=Sv32x4 ON
// Coverpoints mapped (SvH_cg): cp_hgatp_invalid_pte, cp_hgatp_nonleaf_lvl0
// What this proves (one line):
//   Invalid G PTE (V=0) and L0 non-leaf-only entry cause guest-page faults.
// --------------------------------------------------------------------------------------------------------------------------------
// Test cases are as follows:
// --------------------------------------------------------------------------------------------------------------------------------
//  1. G leaf V=0 (D|A|U|W|R set): VS Bare lw → Expected Fault (a3 stays 0)
//  2. G L0 PTE_V only (non-leaf XWR=000): VS Bare lw → Expected Fault (a4 stays 0)
//  3. HS HLV to V=0 GPA → Expected Fault (a6 stays 0)
//  4. Restore valid U=1 R/W G leaf: VS Bare lw → Successful (0x257A0221)
//
// Total Expected Faults :: 3
// --------------------------------------------------------------------------------------------------------------------------------

##### START_TEST_CONFIG #####
# REQUIRED_EXTENSIONS: [I, H, Sv32]
# MARCH: rv32ih_zicsr_zifencei
##### END_TEST_CONFIG #####

#define TEST_FILE "svh_hgatp_fault_VSmode.S"
#define SIGUPD_COUNT 4
#define TRAP_SIGUPD_COUNT 64
#define RVTEST_HYPERVISOR

#include "riscv_arch_test.h"

RVTEST_BEGIN

main:
  .set gpa_data, 0x00C002000                     // GPA for data (vsatp Bare ⇒ address-as-GPA)
  .set gpa_code, 0x80000000                      // identity GPA superpage for code + G PTs at 0x8000_0000

  // ---- G-stage (hgatp Sv32x4 ON): GPA -> PA ----
  SUPERPAGE_G_PTE_SETUP(sv32x4, rvtest_code_begin, (PTE_D | PTE_A | PTE_U | PTE_X | PTE_R | PTE_V), gpa_code, LEVEL1)  // gpa_code -> PA(code)

  G_PTE_SETUP(sv32x4, rvtest_hlvl0_pg_tbl, (PTE_V), gpa_data, LEVEL1)  // non-leaf: G VPN1 for data -> G L0 table
  G_PTE_SETUP(sv32x4, test_region, (PTE_D | PTE_A | PTE_U | PTE_W | PTE_R | PTE_V | PTE_G), gpa_data, LEVEL0)  // valid baseline leaf (cases 1–2 overwrite)

  // ---- vsatp Bare + hgatp ON ----
  csrw vsatp, x0                                // VS Bare
  HGATP_SETUP(sv32x4)                           // hgatp = Sv32x4, PPN = G root
  hfence.vvma                                   // flush VS TLB
  hfence.gvma                                   // flush G TLB so next access rewalks

  LI(t0, 0x257A0221)                            // known SPA pattern (read after restore in case 4)
  la t1, test_region                            // SPA of data page
  sw t0, 0(t1)                                  // preload known pattern at SPA before guest access

  LI(a5, gpa_data)                              // a5 = GPA pointer for VS Bare lw

//---------------------------------------------------------------------------------------------------------------------------------
// Test case 1: G leaf V=0 | Expected: Expected Fault
// cp_hgatp_invalid_pte_rw bin: g_pte_d_inv — V=0 with other bits set still invalid
//---------------------------------------------------------------------------------------------------------------------------------
  G_PTE_SETUP(sv32x4, test_region, (PTE_D | PTE_A | PTE_U | PTE_W | PTE_R), gpa_data, LEVEL0)  // strip V bit; perm bits remain
  hfence.gvma                                   // flush so walk sees V=0 PTE

  LI(a3, 0)                                     // sentinel: stays 0 if trap fires
  RVTEST_GOTO_LOWER_MODE VSmode                 // enter VS for Bare GPA load
  lw   a3, 0(a5)                                // invalid G leaf → fault before load completes
  nop                                           // trap-skip padding if previous access faults
  RVTEST_GOTO_MMODE                             // return to M-mode after VS case

  test1_v0:
  RVTEST_SIGUPD(x2, x5, x4, a3, test1_v0, test1_v0_str)  // record result in signature

//---------------------------------------------------------------------------------------------------------------------------------
// Test case 2: G L0 non-leaf PTE_V only | Expected: Expected Fault
// cp_hgatp_nonleaf_lvl0_rw bin: g_pte_nonleaf_lvl0_d — L0 entry with V=1 but XWR=000
//---------------------------------------------------------------------------------------------------------------------------------
  G_PTE_SETUP(sv32x4, test_region, (PTE_V), gpa_data, LEVEL0)  // V only at L0 (non-leaf shape at leaf level)
  hfence.gvma                                   // flush G TLB so next access rewalks

  LI(a4, 0)                                     // sentinel: stays 0 if trap fires
  RVTEST_GOTO_LOWER_MODE VSmode                 // enter VS for Bare GPA load
  lw   a4, 0(a5)                                // walk stops at non-leaf L0 → guest-page fault
  nop                                           // trap-skip padding if previous access faults
  RVTEST_GOTO_MMODE                             // return to M-mode after VS case

  test2_nonleaf:
  RVTEST_SIGUPD(x2, x5, x4, a4, test2_nonleaf, test2_nonleaf_str)  // record result in signature

//---------------------------------------------------------------------------------------------------------------------------------
// Test case 3: HS HLV to V=0 GPA | Expected: Expected Fault
// cp_hgatp_invalid_pte_rw bin: priv_mode HS, same V=0 leaf (case 2 left non-leaf; reinstall V=0)
//---------------------------------------------------------------------------------------------------------------------------------
  // Case 2 left L0 as non-leaf; reinstall V=0 leaf for invalid_pte sampling from HS HLV path.
  G_PTE_SETUP(sv32x4, test_region, (PTE_D | PTE_A | PTE_U | PTE_W | PTE_R), gpa_data, LEVEL0)  // V=0 leaf again
  hfence.gvma                                   // flush G TLB so next access rewalks

  RVTEST_GOTO_LOWER_MODE HSmode                 // enter HS for hypervisor load
  LI(a6, 0)                                     // sentinel: stays 0 if trap fires
  LI(t1, gpa_data)                              // t1 = GPA pointer for HLV
  hlv.w a6, (t1)                                // HS hypervisor load hits V=0 → guest-page fault
  nop                                           // trap-skip padding if previous access faults
  RVTEST_GOTO_MMODE                             // return to M-mode after HS case

  test3_hlv_v0:
  RVTEST_SIGUPD(x2, x5, x4, a6, test3_hlv_v0, test3_hlv_v0_str)  // record result in signature

//---------------------------------------------------------------------------------------------------------------------------------
// Test case 4: Restore valid U=1 R/W G leaf | Expected: Successful
// sanity: legal leaf after fault cases — confirms setup still works
//---------------------------------------------------------------------------------------------------------------------------------
  G_PTE_SETUP(sv32x4, test_region, (PTE_D | PTE_A | PTE_U | PTE_W | PTE_R | PTE_V | PTE_G), gpa_data, LEVEL0)  // restore valid U=1 R/W+G leaf
  hfence.gvma                                   // force walk on restored leaf (G_PTE_D in .rvvi)

  LI(a7, 0)                                     // clear result register before load
  RVTEST_GOTO_LOWER_MODE VSmode                 // enter VS for Bare GPA load
  lw   a7, 0(a5)                                // expect 0x257A0221
  nop                                           // trap-skip padding if previous access faults
  RVTEST_GOTO_MMODE                             // return to M-mode after VS case

  test4_restore:
  RVTEST_SIGUPD(x2, x5, x4, a7, test4_restore, test4_restore_str)  // record result in signature

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

test1_v0_str:      .string "\"Mismatch on VS lw with G leaf V=0 (expect fault) in Test Case 1!\""
test2_nonleaf_str: .string "\"Mismatch on VS lw with G L0 non-leaf only (expect fault) in Test Case 2!\""
test3_hlv_v0_str:  .string "\"Mismatch on HS HLV with G leaf V=0 (expect fault) in Test Case 3!\""
test4_restore_str: .string "\"Mismatch on VS lw after valid G leaf restore in Test Case 4!\""

RVTEST_DATA_END
RVTEST_SIG_SETUP
