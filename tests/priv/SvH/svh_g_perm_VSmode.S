// --------------------------------------------------------------------------------------------------------------------------------
// svh_g_perm_VSmode.S
// Config: sail-rv32-max | vsatp=Bare, hgatp=Sv32x4 ON
// Coverpoints mapped (SvH_cg): cp_hgatp_perm_checks, cp_hgatp_pte_g_bit
// What this proves (one line):
//   G-stage leaf U/R/W perm checks (VS Bare GPA) and G-bit on HS HLV.
// --------------------------------------------------------------------------------------------------------------------------------
// Test cases are as follows:
// --------------------------------------------------------------------------------------------------------------------------------
//  1. G leaf U=1 R/W+G: VS Bare lw/sw → Successful (0x257A0201)
//  2. G leaf U=0 R/W: VS Bare lw → Expected Fault (a4 stays 0)
//  3. G leaf U=1 X-only: VS Bare lw → Expected Fault (a6 stays 0)
//  4. Restore U=1 R/W+G: VS Bare lw → Successful (0x257A0201)
//  5. HS HLV of G leaf with G=1 → Successful (0x257A0201)
//
// Total Expected Faults :: 2
// --------------------------------------------------------------------------------------------------------------------------------

##### START_TEST_CONFIG #####
# REQUIRED_EXTENSIONS: [I, H, Sv32]
# MARCH: rv32ih_zicsr_zifencei
##### END_TEST_CONFIG #####

#define TEST_FILE "svh_g_perm_VSmode.S"
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
  .set gpa_data, 0x00C002000                     // GPA for data (vsatp Bare ⇒ address used as GPA directly)
  .set gpa_code, 0x80000000                      // identity GPA superpage: code + G PTs map GPA≈PA at 0x8000_0000

  // ---- G-stage (hgatp Sv32x4 ON): GPA -> PA  (walks as U-mode → U=1 on leaves) ----
  // Identity superpage at gpa_code lets guest code/PT pages execute without a separate G walk for every VPN.
  SUPERPAGE_G_PTE_SETUP(sv32x4, rvtest_code_begin, (PTE_D | PTE_A | PTE_U | PTE_X | PTE_R | PTE_V), gpa_code, LEVEL1)  // gpa_code -> PA(code); 4 MiB leaf

  G_PTE_SETUP(sv32x4, rvtest_hlvl0_pg_tbl, (PTE_V), gpa_data, LEVEL1)  // non-leaf: G VPN1 for data -> G L0 table
  G_PTE_SETUP(sv32x4, test_region, (PTE_D | PTE_A | PTE_U | PTE_W | PTE_R | PTE_V | PTE_G), gpa_data, LEVEL0)  // leaf: gpa_data -> PA(test_region) U=1 R/W+G

  // ---- vsatp Bare + hgatp ON: no VS translation, only G-stage applies ----
  csrw vsatp, x0                                // VS Bare (VA used as GPA)
  HGATP_SETUP(sv32x4)                           // hgatp = Sv32x4, PPN = G root
  hfence.vvma                                   // flush VS TLB
  hfence.gvma                                   // flush G TLB so next access rewalks

  LI(t0, 0x257A0201)                            // known SPA pattern for readback checks
  la t1, test_region                            // SPA of data page
  sw t0, 0(t1)                                  // preload known pattern at SPA before guest access

  LI(a5, gpa_data)                              // a5 = GPA pointer for VS accesses (Bare ⇒ same numeric address)

//---------------------------------------------------------------------------------------------------------------------------------
// Test case 1: G leaf U=1 R/W+G VS lw/sw | Expected: Successful
// cp_hgatp_perm_checks_rw bin: g_pte_uxwr_perm_d with U=1 R/W; cp_hgatp_pte_g_bit_rw: G=1 set
//---------------------------------------------------------------------------------------------------------------------------------
  LI(a2, 0x257A0201)                            // value to store through G-stage
  RVTEST_TSBI_GOTO_VSMODE                      // T-SBI: ecall a0=4 → VS (code at PA / identity)
  sw   a2, 0(a5)                                // VS store through G-stage (U=1 R/W leaf)
  nop                                           // trap-skip padding if previous access faults
  hfence.gvma                                   // flush G TLB so next lw walks PTE (G_PTE_D visible in .rvvi)
  lw   a3, 0(a5)                                // VS load; expect 0x257A0201
  nop                                           // trap-skip padding if previous access faults
  RVTEST_TSBI_GOTO_MMODE                       // T-SBI: ecall a0=1 → M (rtn2mmode VA→PA relocate)

  test1_u1_rw:
  RVTEST_SIGUPD(x2, x5, x4, a3, test1_u1_rw, test1_u1_rw_str)  // record result in signature

//---------------------------------------------------------------------------------------------------------------------------------
// Test case 2: G leaf U=0 R/W | Expected: Expected Fault
// cp_hgatp_perm_checks_rw bin: U=0 on G data leaf → guest-page fault (G walks as U-mode)
//---------------------------------------------------------------------------------------------------------------------------------
  G_PTE_SETUP(sv32x4, test_region, (PTE_D | PTE_A | PTE_W | PTE_R | PTE_V | PTE_G), gpa_data, LEVEL0)  // strip U bit; keep R/W+G
  hfence.gvma                                   // flush G TLB so next access rewalks

  LI(a4, 0)                                     // sentinel: stays 0 if trap fires
  RVTEST_TSBI_GOTO_VSMODE                      // T-SBI: ecall a0=4 → VS (code at PA / identity)
  hfence.gvma                                   // force fresh G walk for updated U=0 PTE
  lw   a4, 0(a5)                                // expect guest-page fault; a4 unchanged
  nop                                           // trap-skip padding if previous access faults
  RVTEST_TSBI_GOTO_MMODE                       // T-SBI: ecall a0=1 → M (rtn2mmode VA→PA relocate)

  test2_u0_rw:
  RVTEST_SIGUPD(x2, x5, x4, a4, test2_u0_rw, test2_u0_rw_str)  // record result in signature

//---------------------------------------------------------------------------------------------------------------------------------
// Test case 3: G leaf U=1 X-only | Expected: Expected Fault
// cp_hgatp_perm_checks_rw bin: X-only leaf, VS tries load → perm fault
//---------------------------------------------------------------------------------------------------------------------------------
  G_PTE_SETUP(sv32x4, test_region, (PTE_D | PTE_A | PTE_U | PTE_X | PTE_V | PTE_G), gpa_data, LEVEL0)  // U=1 but X-only (no R/W)
  hfence.gvma                                   // flush G TLB so next access rewalks

  LI(a6, 0)                                     // sentinel: stays 0 if trap fires
  RVTEST_TSBI_GOTO_VSMODE                      // T-SBI: ecall a0=4 → VS (code at PA / identity)
  hfence.gvma                                   // force G walk with X-only PTE
  lw   a6, 0(a5)                                // load without R → fault
  nop                                           // trap-skip padding if previous access faults
  RVTEST_TSBI_GOTO_MMODE                       // T-SBI: ecall a0=1 → M (rtn2mmode VA→PA relocate)

  test3_xonly:
  RVTEST_SIGUPD(x2, x5, x4, a6, test3_xonly, test3_xonly_str)  // record result in signature

//---------------------------------------------------------------------------------------------------------------------------------
// Test case 4: Restore U=1 R/W+G VS lw | Expected: Successful
// cp_hgatp_perm_checks_rw bin: back to legal U=1 R/W perm
//---------------------------------------------------------------------------------------------------------------------------------
  G_PTE_SETUP(sv32x4, test_region, (PTE_D | PTE_A | PTE_U | PTE_W | PTE_R | PTE_V | PTE_G), gpa_data, LEVEL0)  // restore U=1 R/W+G
  hfence.gvma                                   // flush G TLB so next access rewalks

  LI(a7, 0)                                     // clear result register before load
  RVTEST_TSBI_GOTO_VSMODE                      // T-SBI: ecall a0=4 → VS (code at PA / identity)
  hfence.gvma                                   // force walk on restored leaf
  lw   a7, 0(a5)                                // expect 0x257A0201 again
  nop                                           // trap-skip padding if previous access faults
  RVTEST_TSBI_GOTO_MMODE                       // T-SBI: ecall a0=1 → M (rtn2mmode VA→PA relocate)

  test4_restore:
  RVTEST_SIGUPD(x2, x5, x4, a7, test4_restore, test4_restore_str)  // record result in signature

//---------------------------------------------------------------------------------------------------------------------------------
// Test case 5: HS HLV of G leaf with G=1 | Expected: Successful
// cp_hgatp_pte_g_bit_rw bin: HS HLV read with G=1 on data leaf (global mapping)
//---------------------------------------------------------------------------------------------------------------------------------
  RVTEST_TSBI_GOTO_SMODE                       // T-SBI: ecall a0=2 → HS/S (code at PA / identity)
  LI(s2, 0)                                     // clear result register before HLV
  LI(t1, gpa_data)                              // t1 = GPA pointer (Bare VS ⇒ load uses GPA directly)
  hlv.w s2, (t1)                                // HS hypervisor load via G-stage; G=1 leaf still valid
  nop                                           // trap-skip padding if previous access faults
  RVTEST_TSBI_GOTO_MMODE                       // T-SBI: ecall a0=1 → M (rtn2mmode VA→PA relocate)

  test5_hlv:
  RVTEST_SIGUPD(x2, x5, x4, s2, test5_hlv, test5_hlv_str)  // record result in signature

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

test1_u1_rw_str:  .string "\"Mismatch on VS lw/sw with G U=1 R/W+G in Test Case 1!\""
test2_u0_rw_str:  .string "\"Mismatch on VS lw with G U=0 R/W (expect fault) in Test Case 2!\""
test3_xonly_str:  .string "\"Mismatch on VS lw with G X-only (expect fault) in Test Case 3!\""
test4_restore_str:.string "\"Mismatch on VS lw after G perm restore in Test Case 4!\""
test5_hlv_str:    .string "\"Mismatch on HS HLV of G leaf with G=1 in Test Case 5!\""

RVTEST_DATA_END
RVTEST_SIG_SETUP
