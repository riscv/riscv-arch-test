// --------------------------------------------------------------------------------------------------------------------------------
// svh_hgatp_bare_trans_VSmode.S
// Config: sail-rv32-max | VS=Sv32 ON, hgatp=Bare
// Pair:   svh_hgatp_bare_trans_sv39_VSmode.S
// Coverpoints mapped (SvH_cg): cp_hgatp_bare_trans
// What this proves (one line):
//   With hgatp Bare, VS Sv32 alone turns GVA into the real physical address.
// --------------------------------------------------------------------------------------------------------------------------------
// Test cases are as follows:
// --------------------------------------------------------------------------------------------------------------------------------
//  1. VS sw/lw through VS paging with hgatp=Bare (GVA→GPA→SPA) → Successful
//  2. M-mode SPA readback confirms VS store → Successful
//  3. hgatp readback still Bare → Successful
//
// Total Expected Faults :: 0
// --------------------------------------------------------------------------------------------------------------------------------

##### START_TEST_CONFIG #####
# REQUIRED_EXTENSIONS: [I, H, Sv32]
# MARCH: rv32ih_zicsr_zifencei
##### END_TEST_CONFIG #####

#define TEST_FILE "svh_hgatp_bare_trans_VSmode.S"
#define SIGUPD_COUNT 3
#define TRAP_SIGUPD_COUNT 16
#define RVTEST_HYPERVISOR

// Mode hops (T-SBI) — return-to-M always uses RVTEST_TSBI_GOTO_MMODE (ecall a0=1;
//   handler rtn2mmode relocates EPC VA→PA). Enter:
//   • Code at PA / identity: RVTEST_TSBI_GOTO_VSMODE / _SMODE (ecall a0=4/2)
//   • Guest code VA≠PA (V_SAVE_AREA_*): RVTEST_GOTO_LOWER_MODE (mret + PA↔VA relocate)
#include "riscv_arch_test.h"

RVTEST_BEGIN

main:
  .set va_data, 0x008001000                     // guest VA for data
  .set va_code, 0x90000000                      // guest VA for code

  // ---- VS-stage (vsatp Sv32): GVA -> GPA; hgatp Bare ⇒ GPA==SPA ----
  // PTE targets are real PAs (not GPAs) because G-stage is off
  SUPERPAGE_VS_PTE_SETUP(sv32, rvtest_code_begin, (PTE_D | PTE_A | PTE_X | PTE_R | PTE_V), va_code, LEVEL1)  // map va_code → PA(code), 4 MiB leaf

  csrr a0, mscratch                             // a0 = M save area (needed by next macro)
  V_SAVE_AREA_SETUP(va_code, rvtest_code_begin, code, LEVEL1)  // VS entry PC under va_code

  VS_PTE_SETUP(sv32, PA, rvtest_vlvl0_pg_tbl, (PTE_V), va_data, LEVEL1)  // non-leaf → L0 table (PA)
  VS_PTE_SETUP(sv32, PA, test_region, (PTE_D | PTE_A | PTE_W | PTE_R | PTE_V), va_data, LEVEL0)  // leaf: va_data → PA(test_region)

  VSATP_SETUP(sv32, PA)                         // turn on VS Sv32 (root at PA)
  csrw hgatp, x0                                // G Bare — GPA from VS walk used directly as SPA
  hfence.vvma                                   // flush VS TLB
  hfence.gvma                                   // flush G TLB (hgatp changed to Bare)

  LI(t0, 0xDEADBEEF)                            // poison SPA
  la t1, test_region                            // SPA of data page
  sw t0, 0(t1)                                  // preload poison at SPA before guest access

  LI(a5, va_data)                               // a5 = guest VA pointer
  RVTEST_GOTO_LOWER_MODE VSmode                 // M→VSmode mret + PA↔VA relocate (guest code VA≠PA; T-SBI enter lacks relocate)

//---------------------------------------------------------------------------------------------------------------------------------
// Test case 1: VS sw/lw with hgatp=Bare | Expected: Successful
//---------------------------------------------------------------------------------------------------------------------------------
  LI(a2, 0x257A0031)                            // value to store
  sw   a2, 0(a5)                                // cp_hgatp_bare_trans: GVA→GPA (VS only; GPA==SPA)
  nop                                           // trap-skip padding if previous access faults
  lw   a3, 0(a5)                                // load back through VS paging
  nop                                           // trap-skip padding if previous access faults
  RVTEST_TSBI_GOTO_MMODE                       // T-SBI: ecall a0=1 → M (rtn2mmode VA→PA relocate)

  test1_vs:
  RVTEST_SIGUPD(x2, x5, x4, a3, test1_vs, test1_vs_str)  // record result in signature

//---------------------------------------------------------------------------------------------------------------------------------
// Test case 2: M-mode SPA readback | Expected: Successful
//---------------------------------------------------------------------------------------------------------------------------------
  la t1, test_region                            // SPA of data page
  lw t2, 0(t1)                                  // SPA expect 0x257A0031
  test2_spa:
  RVTEST_SIGUPD(x2, x5, x4, t2, test2_spa, test2_spa_str)  // record result in signature

//---------------------------------------------------------------------------------------------------------------------------------
// Test case 3: hgatp readback still Bare | Expected: Successful
//---------------------------------------------------------------------------------------------------------------------------------
  test3_hgatp:
  RVTEST_SIGUPD_CSR_READ(hgatp, a4, test3_hgatp, test3_hgatp_str)  // record hgatp CSR in signature

//---------------------------------------------------------------------------------------------------------------------------------
RVTEST_CODE_END
RVTEST_DATA_BEGIN

.align 12                                      // 4 KiB page align
test_region:                                  // SPA backing for va_data leaf
  .word 0                                     // payload word (initially poisoned in M)
  .word 0                                     // padding in same page
  .word 0                                     // padding in same page
  .word 0                                     // padding in same page

.align 12                                      // 4 KiB page align
rvtest_vlvl0_pg_tbl:                          // VS-stage L0 PTE storage (4 KiB)
  .zero(4096)                                  // reserve 4 KiB page-table storage

test1_vs_str:    .string "\"Mismatch on VS lw after sw (hgatp Bare) in Test Case 1!\""
test2_spa_str:   .string "\"Mismatch on SPA readback after VS store in Test Case 2!\""
test3_hgatp_str: .string "\"Mismatch on hgatp readback (expect Bare) in Test Case 3!\""

RVTEST_DATA_END
RVTEST_SIG_SETUP
