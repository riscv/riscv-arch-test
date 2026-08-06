// --------------------------------------------------------------------------------------------------------------------------------
// svh_vsatp_fault_VSmode.S
// Config: sail-rv32-max | VS=Sv32 ON, hgatp=Bare
// Coverpoints mapped (SvH_cg): cp_vsatp_invalid_pte, cp_vsatp_nonleaf_lvl0
// What this proves (one line):
//   VS faults on V=0 leaf and L0 non-leaf; HS HLV with SPVP=1 also faults invalid PTE.
// --------------------------------------------------------------------------------------------------------------------------------
// Test cases are as follows:
// --------------------------------------------------------------------------------------------------------------------------------
//  1. VS lw of V=0 leaf (D|A|U|W|R, no V) at va_inv → Expected Fault (a3 stays 0)
//  2. VS lw of L0 non-leaf (only PTE_V) at va_nleaf → Expected Fault (a4 stays 0)
//  3. HS hlv.w with hstatus.SPVP=1 on V=0 leaf at va_inv → Expected Fault (a6 stays 0)
//  4. Restore valid leaf at va_ok; VS lw → Successful (0x257A0310)
//
// Total Expected Faults :: 3
// --------------------------------------------------------------------------------------------------------------------------------

##### START_TEST_CONFIG #####
# REQUIRED_EXTENSIONS: [I, H, Sv32]
# MARCH: rv32ih_zicsr_zifencei
##### END_TEST_CONFIG #####

#define TEST_FILE "svh_vsatp_fault_VSmode.S"
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
  .set va_ok,     0x008001000                    // GVA for valid R/W leaf (case 4 baseline)
  .set va_inv,    0x008002000                    // GVA for V=0 invalid leaf (cases 1 and 3)
  .set va_nleaf,  0x008003000                    // GVA for L0 non-leaf PTE (case 2)
  .set va_code,   0x90000000                     // GVA where VS executes this code

  // ---- VS-stage (vsatp Sv32): GVA -> PA  (hgatp Bare ⇒ PTE PPN fields are real PAs) ----
  SUPERPAGE_VS_PTE_SETUP(sv32, rvtest_code_begin, (PTE_D | PTE_A | PTE_X | PTE_R | PTE_V), va_code, LEVEL1)  // leaf: va_code -> PA(code); LEVEL1 = 4 MiB X/R

  csrr a0, mscratch                             // a0 = Msave_area (required by next macro)
  V_SAVE_AREA_SETUP(va_code, rvtest_code_begin, code, LEVEL1)  // framework: VS entry PC is under va_code

  // Shared L1 non-leaf for all data VAs (same VPN1, different VPN0 slots)
  VS_PTE_SETUP(sv32, PA, rvtest_vlvl0_pg_tbl, (PTE_V), va_ok, LEVEL1)  // non-leaf: data VPN1 -> VS L0 table PA

  // Valid leaf installed up front (case 4 baseline; faults run against other VAs first)
  VS_PTE_SETUP(sv32, PA, test_region_ok, (PTE_D | PTE_A | PTE_W | PTE_R | PTE_V), va_ok, LEVEL0)  // leaf: va_ok -> PA(test_region_ok) R/W

  // V=0 leaf: permissions look fine but Valid bit clear → must fault on access
  VS_PTE_SETUP(sv32, PA, test_region_inv, (PTE_D | PTE_A | PTE_U | PTE_W | PTE_R), va_inv, LEVEL0)  // leaf: va_inv -> PA(test_region_inv); V=0 invalid

  // L0 non-leaf: only PTE_V set (XWR=000) at level 0 → must fault (cannot load through pointer PTE)
  VS_PTE_SETUP(sv32, PA, test_region_nleaf, (PTE_V), va_nleaf, LEVEL0)  // non-leaf at L0: va_nleaf -> PA(test_region_nleaf); not a data leaf

  VSATP_SETUP(sv32, PA)                         // vsatp = Sv32, PPN = PA of VS root
  csrw hgatp, x0                                // hgatp = Bare (no G-stage)
  hfence.vvma                                   // invalidate VS-stage TLB entries
  hfence.gvma                                   // invalidate G-stage TLB entries (harmless with Bare)

  LI(t0, 0x257A0310)                            // payload for successful case 4
  la t1, test_region_ok                         // t1 = SPA of valid leaf
  sw t0, 0(t1)                                  // preload SPA so case 4 has known data

//---------------------------------------------------------------------------------------------------------------------------------
// Test case 1: VS lw of V=0 leaf | Expected: Expected Fault
//---------------------------------------------------------------------------------------------------------------------------------
  LI(a5, va_inv)                                // a5 = GVA of V=0 leaf
  LI(a3, 0)                                     // a3 stays 0 if lw is skipped by trap handler
  RVTEST_GOTO_LOWER_MODE VSmode                 // M→VSmode mret + PA↔VA relocate (guest code VA≠PA; T-SBI enter lacks relocate)
  lw   a3, 0(a5)                                // V=0 leaf → load-page-fault; insn skipped
  nop                                           // trap-skip padding after load
  RVTEST_TSBI_GOTO_MMODE                       // T-SBI: ecall a0=1 → M (rtn2mmode VA→PA relocate)

  test1_v0:
  RVTEST_SIGUPD(x2, x5, x4, a3, test1_v0, test1_v0_str)  // record case 1 fault sentinel in signature

//---------------------------------------------------------------------------------------------------------------------------------
// Test case 2: VS lw of L0 non-leaf | Expected: Expected Fault
//---------------------------------------------------------------------------------------------------------------------------------
  LI(a5, va_nleaf)                              // a5 = GVA pointing at L0 non-leaf PTE
  LI(a4, 0)                                     // a4 stays 0 if lw is skipped by trap handler
  RVTEST_GOTO_LOWER_MODE VSmode                 // M→VSmode mret + PA↔VA relocate (guest code VA≠PA; T-SBI enter lacks relocate)
  lw   a4, 0(a5)                                // non-leaf at L0 → load-page-fault; insn skipped
  nop                                           // trap-skip padding after load
  RVTEST_TSBI_GOTO_MMODE                       // T-SBI: ecall a0=1 → M (rtn2mmode VA→PA relocate)

  test2_nleaf:
  RVTEST_SIGUPD(x2, x5, x4, a4, test2_nleaf, test2_nleaf_str)  // record case 2 fault sentinel in signature

//---------------------------------------------------------------------------------------------------------------------------------
// Test case 3: HS hlv.w on V=0 leaf with SPVP=1 | Expected: Expected Fault
//---------------------------------------------------------------------------------------------------------------------------------
  LI(t0, HSTATUS_SPVP)                          // t0 = SPVP bit mask (hstatus[8])
  csrs hstatus, t0                              // SPVP=1 → HLV uses VS-stage translation (same as guest)
  LI(a5, va_inv)                                // a5 = GVA of same V=0 leaf as case 1
  LI(a6, 0)                                     // a6 stays 0 if hlv.w is skipped by trap handler
  RVTEST_GOTO_LOWER_MODE HSmode                 // M→HSmode mret + PA↔VA relocate (guest code VA≠PA; T-SBI enter lacks relocate)
  hlv.w a6, (a5)                                // HS hypervisor load through vsatp → same invalid PTE fault
  nop                                           // trap-skip padding after hlv.w
  RVTEST_TSBI_GOTO_MMODE                       // T-SBI: ecall a0=1 → M (rtn2mmode VA→PA relocate)

  LI(t0, HSTATUS_SPVP)                          // t0 = SPVP bit mask (hstatus[8])
  csrc hstatus, t0                              // clear SPVP (tidy for harness)

  test3_hlv:
  RVTEST_SIGUPD(x2, x5, x4, a6, test3_hlv, test3_hlv_str)  // record case 3 fault sentinel in signature

//---------------------------------------------------------------------------------------------------------------------------------
// Test case 4: Valid leaf VS lw | Expected: Successful
//---------------------------------------------------------------------------------------------------------------------------------
  LI(a5, va_ok)                                  // a5 = GVA of valid R/W leaf
  RVTEST_GOTO_LOWER_MODE VSmode                 // M→VSmode mret + PA↔VA relocate (guest code VA≠PA; T-SBI enter lacks relocate)
  lw   a7, 0(a5)                                // valid leaf → load succeeds; expect 0x257A0310
  nop                                           // trap-skip padding after load
  RVTEST_TSBI_GOTO_MMODE                       // T-SBI: ecall a0=1 → M (rtn2mmode VA→PA relocate)

  test4_ok:
  RVTEST_SIGUPD(x2, x5, x4, a7, test4_ok, test4_ok_str)  // record case 4 lw result in signature

//---------------------------------------------------------------------------------------------------------------------------------
RVTEST_CODE_END
RVTEST_DATA_BEGIN

.align 12                                       // 4 KiB page align
test_region_ok:                                 // real PA backing va_ok (valid R/W leaf)
  .word 0                                       // data word (initially 0)
  .word 0                                       // padding in same page
  .word 0                                       // padding in same page
  .word 0                                       // padding in same page
.align 12                                       // 4 KiB page align
test_region_inv:                                // real PA behind V=0 leaf (access must fault before read)
  .word 0                                       // data word (initially 0)
  .word 0                                       // padding in same page
  .word 0                                       // padding in same page
  .word 0                                       // padding in same page
.align 12                                       // 4 KiB page align
test_region_nleaf:                              // PTE storage misused as L0 non-leaf target (not data)
  .word 0                                       // data word (initially 0)
  .word 0                                       // padding in same page
  .word 0                                       // padding in same page
  .word 0                                       // padding in same page
.align 12                                       // align to 4 KiB page
rvtest_vlvl0_pg_tbl:                            // VS-stage level-0 PTE storage
  .zero(4096)                                   // 4 KiB page-table storage

test1_v0_str:    .string "\"Mismatch on VS lw of V=0 leaf (expect fault) in Test Case 1!\""
test2_nleaf_str: .string "\"Mismatch on VS lw of L0 non-leaf (expect fault) in Test Case 2!\""
test3_hlv_str:   .string "\"Mismatch on HS hlv.w of V=0 leaf (expect fault) in Test Case 3!\""
test4_ok_str:    .string "\"Mismatch on VS lw of valid leaf in Test Case 4!\""

RVTEST_DATA_END
RVTEST_SIG_SETUP
