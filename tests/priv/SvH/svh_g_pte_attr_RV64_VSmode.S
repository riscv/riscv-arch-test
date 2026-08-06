// --------------------------------------------------------------------------------------------------------------------------------
// svh_g_pte_attr_RV64_VSmode.S
// Config: sail-rv64-max | vsatp=Bare, hgatp=Sv39x4 ON, HS HLV
// Pair:   svh_g_pte_attr_VSmode.S
// Coverpoints mapped (SvH_cg): cp_hgatp_pte_rsw, cp_hgatp_reserved_fields, cp_hgatp_svpbmt
// What this proves (one line):
//   Sv39x4 G PTE RSW ok; reserved/PBMT encodings dump Sail result (fault or pass).
// --------------------------------------------------------------------------------------------------------------------------------
// Test cases are as follows:
// --------------------------------------------------------------------------------------------------------------------------------
//  1. G leaf RSW=00 U=1 R/W: HS HLV → Successful (0x257A0241)
//  2. G leaf RSW=11 U=1 R/W: HS HLV → Successful (0x257A0241)
//  3. G leaf PTE_RSVD set: HS HLV → Expected Fault if Sail checks reserved (a4 stays 0)
//  4. G leaf PTE_PBMT=1 (PBMTE=1): HS HLV → dump (impl-dependent)
//  5. Restore valid leaf: HS HLV → Successful (0x257A0241)
//
// Total Expected Faults :: 1–2 (Sail-dependent for cases 3–4)
// --------------------------------------------------------------------------------------------------------------------------------

##### START_TEST_CONFIG #####
# REQUIRED_EXTENSIONS: [I, H, Sv39]
# MARCH: rv64ih_zicsr_zifencei
##### END_TEST_CONFIG #####

#define TEST_FILE "svh_g_pte_attr_RV64_VSmode.S"
#define SIGUPD_COUNT 5
#define TRAP_SIGUPD_COUNT 64
#define RVTEST_HYPERVISOR

// Mode hops (T-SBI) — return-to-M always uses RVTEST_TSBI_GOTO_MMODE (ecall a0=1;
//   handler rtn2mmode relocates EPC VA→PA). Enter:
//   • Code at PA / identity: RVTEST_TSBI_GOTO_VSMODE / _SMODE (ecall a0=4/2)
//   • Guest code VA≠PA (V_SAVE_AREA_*): RVTEST_GOTO_LOWER_MODE (mret + PA↔VA relocate)
#include "riscv_arch_test.h"

RVTEST_BEGIN

main:
  .set gpa_data, 0x0000000000C002000           // GPA for data page (vsatp/sATP Bare ⇒ used as-is)

  // ---- G-stage (hgatp Sv39x4 ON): 3-level walk GPA -> PA ----
  // No identity superpage here — Sv39x4 needs L2/L1 non-leaf + L0 leaf for gpa_data.
  G_PTE_SETUP(sv39x4, rvtest_hlvl1_pg_tbl, (PTE_V), gpa_data, LEVEL2)  // non-leaf: G VPN2 -> G L1 table
  G_PTE_SETUP(sv39x4, rvtest_hlvl0_pg_tbl, (PTE_V), gpa_data, LEVEL1)  // non-leaf: G VPN1 -> G L0 table
  G_PTE_SETUP(sv39x4, test_region, (PTE_D | PTE_A | PTE_U | PTE_W | PTE_R | PTE_V), gpa_data, LEVEL0)  // leaf: gpa_data -> PA(test_region) RSW=00

  // ---- vsatp Bare + hgatp ON (RV64: clear satp too) ----
  csrw vsatp, x0                                // VS Bare
  csrw satp, x0                                 // HS satp Bare (test runs HLV from HS)
  HGATP_SETUP(sv39x4)                           // hgatp = Sv39x4, PPN = G root
  hfence.vvma                                   // flush VS TLB
  hfence.gvma                                   // flush G TLB so next access rewalks

  LI(t0, 0x257A0241)                            // known SPA pattern
  la t1, test_region                            // SPA of data page
  sw t0, 0(t1)                                  // preload known pattern at SPA before guest access

  LI(t1, gpa_data)                              // t1 = GPA pointer reused by all HS HLV cases

//---------------------------------------------------------------------------------------------------------------------------------
// Test case 1: G leaf RSW=00 HS HLV | Expected: Successful
// cp_hgatp_pte_rsw bin: g_pte_rsw=00, priv_mode HS
//---------------------------------------------------------------------------------------------------------------------------------
  RVTEST_TSBI_GOTO_SMODE                       // T-SBI: ecall a0=2 → HS/S (code at PA / identity)
  LI(a3, 0)                                     // clear result register before HLV
  hlv.w a3, (t1)                                // HS load via G-stage; baseline RSW=00
  nop                                           // trap-skip padding if previous access faults
  RVTEST_TSBI_GOTO_MMODE                       // T-SBI: ecall a0=1 → M (rtn2mmode VA→PA relocate)

  test1_rsw00:
  RVTEST_SIGUPD(x2, x5, x4, a3, test1_rsw00, test1_rsw00_str)  // record result in signature

//---------------------------------------------------------------------------------------------------------------------------------
// Test case 2: G leaf RSW=11 HS HLV | Expected: Successful
// cp_hgatp_pte_rsw bin: g_pte_rsw=11
//---------------------------------------------------------------------------------------------------------------------------------
  G_PTE_SETUP(sv39x4, test_region, (PTE_D | PTE_A | PTE_U | PTE_W | PTE_R | PTE_V | PTE_SOFT), gpa_data, LEVEL0)  // set RSW[1:0]=11
  hfence.gvma                                   // flush G TLB so next access rewalks

  RVTEST_TSBI_GOTO_SMODE                       // T-SBI: ecall a0=2 → HS/S (code at PA / identity)
  LI(a6, 0)                                     // clear result register before HLV
  hlv.w a6, (t1)                                // HS load; RSW=11 must not affect access
  nop                                           // trap-skip padding if previous access faults
  RVTEST_TSBI_GOTO_MMODE                       // T-SBI: ecall a0=1 → M (rtn2mmode VA→PA relocate)

  test2_rsw11:
  RVTEST_SIGUPD(x2, x5, x4, a6, test2_rsw11, test2_rsw11_str)  // record result in signature

//---------------------------------------------------------------------------------------------------------------------------------
// Test case 3: G leaf PTE_RSVD set | Expected: Expected Fault (Sail-dependent)
// cp_hgatp_reserved_fields_rw bin: g_pte_d_reserved — illegal reserved bits in Sv39x4 leaf
//---------------------------------------------------------------------------------------------------------------------------------
  G_PTE_SETUP(sv39x4, test_region, (PTE_D | PTE_A | PTE_U | PTE_W | PTE_R | PTE_V | PTE_RSVD), gpa_data, LEVEL0)  // set RSVD pattern
  hfence.gvma                                   // flush G TLB so next access rewalks

  RVTEST_TSBI_GOTO_SMODE                       // T-SBI: ecall a0=2 → HS/S (code at PA / identity)
  LI(a4, 0)                                     // sentinel: stays 0 if trap fires
  hlv.w a4, (t1)                                // HS load; Sail may fault on reserved bits
  nop                                           // trap-skip padding if previous access faults
  RVTEST_TSBI_GOTO_MMODE                       // T-SBI: ecall a0=1 → M (rtn2mmode VA→PA relocate)

  test3_rsvd:
  RVTEST_SIGUPD(x2, x5, x4, a4, test3_rsvd, test3_rsvd_str)  // record result in signature

//---------------------------------------------------------------------------------------------------------------------------------
// Test case 4: G leaf PTE_PBMT=1 (PBMTE=1) | Expected: dump (impl-dependent)
// cp_hgatp_svpbmt_rw bin: pbmte_menvcfg=1, g_pte_d_svpbmt — memory-type encoding on G leaf
//---------------------------------------------------------------------------------------------------------------------------------
  LI(t0, MENVCFG_PBMTE)                         // load PBMTE enable mask
  csrs menvcfg, t0                              // enable PBMT checking in M-mode env
  G_PTE_SETUP(sv39x4, test_region, (PTE_D | PTE_A | PTE_U | PTE_W | PTE_R | PTE_V | _RISCV_ULL(0x1000000000000000)), gpa_data, LEVEL0)  // PBMT field non-zero
  hfence.gvma                                   // flush G TLB so next access rewalks

  RVTEST_TSBI_GOTO_SMODE                       // T-SBI: ecall a0=2 → HS/S (code at PA / identity)
  LI(a7, 0)                                     // dump register (pass or fault)
  hlv.w a7, (t1)                                // HS load; Sail behavior impl-dependent
  nop                                           // trap-skip padding if previous access faults
  RVTEST_TSBI_GOTO_MMODE                       // T-SBI: ecall a0=1 → M (rtn2mmode VA→PA relocate)

  test4_pbmt:
  RVTEST_SIGUPD(x2, x5, x4, a7, test4_pbmt, test4_pbmt_str)  // record result in signature

//---------------------------------------------------------------------------------------------------------------------------------
// Test case 5: Restore valid G leaf HS HLV | Expected: Successful
// sanity check after reserved/PBMT probes — back to legal leaf
//---------------------------------------------------------------------------------------------------------------------------------
  G_PTE_SETUP(sv39x4, test_region, (PTE_D | PTE_A | PTE_U | PTE_W | PTE_R | PTE_V), gpa_data, LEVEL0)  // clean RSW/RSVD/PBMT
  hfence.gvma                                   // flush G TLB so next access rewalks

  RVTEST_TSBI_GOTO_SMODE                       // T-SBI: ecall a0=2 → HS/S (code at PA / identity)
  LI(s2, 0)                                     // clear result register before HLV
  hlv.w s2, (t1)                                // expect 0x257A0241
  nop                                           // trap-skip padding if previous access faults
  RVTEST_TSBI_GOTO_MMODE                       // T-SBI: ecall a0=1 → M (rtn2mmode VA→PA relocate)

  test5_restore:
  RVTEST_SIGUPD(x2, x5, x4, s2, test5_restore, test5_restore_str)  // record result in signature

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
rvtest_hlvl1_pg_tbl:                          // G-stage L1 PTE storage (4 KiB)
  .zero(4096)                                  // reserve 4 KiB page-table storage
.align 12                                      // 4 KiB page align
rvtest_hlvl0_pg_tbl:                          // G-stage L0 PTE storage (4 KiB)
  .zero(4096)                                  // reserve 4 KiB page-table storage

test1_rsw00_str:   .string "\"Mismatch on HS HLV with G RSW=00 in Test Case 1!\""
test2_rsw11_str:   .string "\"Mismatch on HS HLV with G RSW=11 in Test Case 2!\""
test3_rsvd_str:    .string "\"Mismatch on HS HLV with G PTE_RSVD in Test Case 3!\""
test4_pbmt_str:    .string "\"Mismatch on HS HLV with G PTE_PBMT=1 in Test Case 4!\""
test5_restore_str: .string "\"Mismatch on HS HLV after valid G leaf restore in Test Case 5!\""

RVTEST_DATA_END
RVTEST_SIG_SETUP
