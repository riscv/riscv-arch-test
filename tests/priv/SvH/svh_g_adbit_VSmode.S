// --------------------------------------------------------------------------------------------------------------------------------
// svh_g_adbit_VSmode.S
// Config: sail-rv32-max | vsatp=Bare, hgatp=Sv32x4 ON (Svade on)
// Coverpoints mapped (SvH_cg): cp_hgatp_adbit_behavior
// What this proves (one line):
//   With Svade, G leaf A=0 faults; A=1 allows HS HLV / VS Bare load.
// --------------------------------------------------------------------------------------------------------------------------------
// Test cases are as follows:
// --------------------------------------------------------------------------------------------------------------------------------
//  1. G leaf A=0 D=0 U=1 R/W: VS Bare lw → Expected Fault (a3 stays 0)
//  2. G leaf A=1 D=1 U=1 R/W: VS Bare lw → Successful (0x257A0251)
//  3. G leaf A=0 again: HS HLV → Expected Fault (a7 stays 0)
//
// Total Expected Faults :: 2
// --------------------------------------------------------------------------------------------------------------------------------

##### START_TEST_CONFIG #####
# REQUIRED_EXTENSIONS: [I, H, Sv32]
# MARCH: rv32ih_zicsr_zifencei
##### END_TEST_CONFIG #####

#define TEST_FILE "svh_g_adbit_VSmode.S"
#define SIGUPD_COUNT 3
#define TRAP_SIGUPD_COUNT 64
#define RVTEST_HYPERVISOR

// Mode hops (T-SBI) — return-to-M always uses RVTEST_TSBI_GOTO_MMODE (ecall a0=1;
//   handler rtn2mmode relocates EPC VA→PA). Enter:
//   • Code at PA / identity: RVTEST_TSBI_GOTO_VSMODE / _SMODE (ecall a0=4/2)
//   • Guest code VA≠PA (V_SAVE_AREA_*): RVTEST_GOTO_LOWER_MODE (mret + PA↔VA relocate)
#include "riscv_arch_test.h"

RVTEST_BEGIN

main:
  .set gpa_data, 0x00C002000                     // GPA for data (vsatp Bare ⇒ address-as-GPA)
  .set gpa_code, 0x80000000                      // identity GPA superpage for code + G PTs at 0x8000_0000

  // ---- G-stage (hgatp Sv32x4 ON): GPA -> PA ----
  SUPERPAGE_G_PTE_SETUP(sv32x4, rvtest_code_begin, (PTE_D | PTE_A | PTE_U | PTE_X | PTE_R | PTE_V), gpa_code, LEVEL1)  // gpa_code -> PA(code)

  G_PTE_SETUP(sv32x4, rvtest_hlvl0_pg_tbl, (PTE_V), gpa_data, LEVEL1)  // non-leaf: G VPN1 for data -> G L0 table
  G_PTE_SETUP(sv32x4, test_region, (PTE_U | PTE_W | PTE_R | PTE_V), gpa_data, LEVEL0)  // leaf: A=D=0 intentionally (Svade will fault)

  // ---- vsatp Bare + hgatp ON ----
  csrw vsatp, x0                                // VS Bare
  HGATP_SETUP(sv32x4)                           // hgatp = Sv32x4, PPN = G root
  hfence.vvma                                   // flush VS TLB
  hfence.gvma                                   // flush G TLB so next access rewalks

  LI(t0, 0x257A0251)                            // known SPA pattern (case 2 should read this)
  la t1, test_region                            // SPA of data page
  sw t0, 0(t1)                                  // preload known pattern at SPA before guest access

  LI(a5, gpa_data)                              // a5 = GPA pointer for VS Bare lw

//---------------------------------------------------------------------------------------------------------------------------------
// Test case 1: G leaf A=D=0 VS Bare lw | Expected: Expected Fault (Svade)
// cp_hgatp_adbit_behavior bin: g_pte_ad_unset — A=0 on G leaf faults before access under Svade
//---------------------------------------------------------------------------------------------------------------------------------
  LI(a3, 0)                                     // sentinel: stays 0 if trap fires
  RVTEST_TSBI_GOTO_VSMODE                      // T-SBI: ecall a0=4 → VS (code at PA / identity)
  lw   a3, 0(a5)                                // A=0 → guest-page fault under Svade (no silent A-set)
  nop                                           // trap-skip padding if previous access faults
  RVTEST_TSBI_GOTO_MMODE                       // T-SBI: ecall a0=1 → M (rtn2mmode VA→PA relocate)

  test1_ad_unset:
  RVTEST_SIGUPD(x2, x5, x4, a3, test1_ad_unset, test1_ad_unset_str)  // record result in signature

//---------------------------------------------------------------------------------------------------------------------------------
// Test case 2: G leaf A=1 D=1 VS Bare lw | Expected: Successful
// cp_hgatp_adbit_behavior bin: g_pte_ad_unset=0 (A/D set) — legal access path
//---------------------------------------------------------------------------------------------------------------------------------
  G_PTE_SETUP(sv32x4, test_region, (PTE_D | PTE_A | PTE_U | PTE_W | PTE_R | PTE_V), gpa_data, LEVEL0)  // set A=D=1
  hfence.gvma                                   // flush so walk sees updated A/D bits

  LI(a4, 0)                                     // clear result register before load
  RVTEST_TSBI_GOTO_VSMODE                      // T-SBI: ecall a0=4 → VS (code at PA / identity)
  hfence.gvma                                   // force fresh G walk (G_PTE_D with A=1 visible in .rvvi)
  lw   a4, 0(a5)                                // expect 0x257A0251
  nop                                           // trap-skip padding if previous access faults
  RVTEST_TSBI_GOTO_MMODE                       // T-SBI: ecall a0=1 → M (rtn2mmode VA→PA relocate)

  test2_ad_set:
  RVTEST_SIGUPD(x2, x5, x4, a4, test2_ad_set, test2_ad_set_str)  // record result in signature

//---------------------------------------------------------------------------------------------------------------------------------
// Test case 3: G leaf A=D=0 HS HLV | Expected: Expected Fault (Svade)
// cp_hgatp_adbit_behavior bin: g_pte_ad_unset from HS HLV path (priv_mode HS)
//---------------------------------------------------------------------------------------------------------------------------------
  G_PTE_SETUP(sv32x4, test_region, (PTE_U | PTE_W | PTE_R | PTE_V), gpa_data, LEVEL0)  // clear A/D again
  hfence.gvma                                   // flush G TLB so next access rewalks

  RVTEST_TSBI_GOTO_SMODE                       // T-SBI: ecall a0=2 → HS/S (code at PA / identity)
  LI(a7, 0)                                     // sentinel: stays 0 if trap fires
  LI(t1, gpa_data)                              // t1 = GPA pointer for HLV
  hlv.w a7, (t1)                                // A=0 → guest-page fault under Svade even from HS
  nop                                           // trap-skip padding if previous access faults
  RVTEST_TSBI_GOTO_MMODE                       // T-SBI: ecall a0=1 → M (rtn2mmode VA→PA relocate)

  test3_hlv_ad_unset:
  RVTEST_SIGUPD(x2, x5, x4, a7, test3_hlv_ad_unset, test3_hlv_ad_unset_str)  // record result in signature

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

test1_ad_unset_str:      .string "\"Mismatch on VS lw with G A=0 (expect fault) in Test Case 1!\""
test2_ad_set_str:        .string "\"Mismatch on VS lw with G A=1 in Test Case 2!\""
test3_hlv_ad_unset_str:  .string "\"Mismatch on HS HLV with G A=0 (expect fault) in Test Case 3!\""

RVTEST_DATA_END
RVTEST_SIG_SETUP
