// --------------------------------------------------------------------------------------------------------------------------------
// svh_g_pte_attr_VSmode.S
// Config: sail-rv32-max | vsatp=Bare, hgatp=Sv32x4 ON
// Coverpoints mapped (SvH_cg): cp_hgatp_pte_rsw
// What this proves (one line):
//   G-stage leaf RSW[1:0] is preserved; VS Bare and HS HLV loads succeed.
// --------------------------------------------------------------------------------------------------------------------------------
// Test cases are as follows:
// --------------------------------------------------------------------------------------------------------------------------------
//  1. G leaf RSW=00 U=1 R/W: VS Bare lw → Successful (0x257A0211)
//  2. G leaf RSW=01 U=1 R/W: VS Bare lw → Successful (0x257A0211)
//  3. G leaf RSW=10 U=1 R/W: VS Bare lw → Successful (0x257A0211)
//  4. G leaf RSW=11 U=1 R/W: VS Bare lw → Successful (0x257A0211)
//  5. HS HLV with RSW=11 → Successful (0x257A0211)
//
// Total Expected Faults :: 0
// --------------------------------------------------------------------------------------------------------------------------------

##### START_TEST_CONFIG #####
# REQUIRED_EXTENSIONS: [I, H, Sv32]
# MARCH: rv32ih_zicsr_zifencei
##### END_TEST_CONFIG #####

#define TEST_FILE "svh_g_pte_attr_VSmode.S"
#define SIGUPD_COUNT 5
#define TRAP_SIGUPD_COUNT 16
#define RVTEST_HYPERVISOR

#include "riscv_arch_test.h"

RVTEST_BEGIN

main:
  .set gpa_data, 0x00C002000                     // GPA for data (vsatp Bare ⇒ address-as-GPA)
  .set gpa_code, 0x80000000                      // identity GPA superpage for code + G PTs at 0x8000_0000

  // ---- G-stage (hgatp Sv32x4 ON): GPA -> PA ----
  SUPERPAGE_G_PTE_SETUP(sv32x4, rvtest_code_begin, (PTE_D | PTE_A | PTE_U | PTE_X | PTE_R | PTE_V), gpa_code, LEVEL1)  // gpa_code -> PA(code); 4 MiB identity leaf

  G_PTE_SETUP(sv32x4, rvtest_hlvl0_pg_tbl, (PTE_V), gpa_data, LEVEL1)  // non-leaf: G VPN1 for data -> G L0 table
  G_PTE_SETUP(sv32x4, test_region, (PTE_D | PTE_A | PTE_U | PTE_W | PTE_R | PTE_V), gpa_data, LEVEL0)  // leaf: gpa_data -> PA(test_region) RSW=00

  // ---- vsatp Bare + hgatp ON ----
  csrw vsatp, x0                                // VS Bare (no VS translation)
  HGATP_SETUP(sv32x4)                           // hgatp = Sv32x4, PPN = G root
  hfence.vvma                                   // flush VS TLB
  hfence.gvma                                   // flush G TLB so next access rewalks

  LI(t0, 0x257A0211)                            // known SPA pattern
  la t1, test_region                            // SPA of data page
  sw t0, 0(t1)                                  // preload known pattern at SPA before guest access

  LI(a5, gpa_data)                              // a5 = GPA pointer for VS Bare lw

//---------------------------------------------------------------------------------------------------------------------------------
// Test case 1: G leaf RSW=00 | Expected: Successful
// cp_hgatp_pte_rsw bin: g_pte_rsw=00, priv_mode VS, read_write_acc
//---------------------------------------------------------------------------------------------------------------------------------
  G_PTE_SETUP(sv32x4, test_region, (PTE_D | PTE_A | PTE_U | PTE_W | PTE_R | PTE_V), gpa_data, LEVEL0)  // explicit RSW=00 (PTE_SOFT clear)
  hfence.gvma                                   // flush so lw walks fresh PTE (G_PTE_D in .rvvi)

  RVTEST_GOTO_LOWER_MODE VSmode                 // enter VS for Bare GPA load
  lw   a3, 0(a5)                                // VS load; RSW must not affect access
  nop                                           // trap-skip padding if previous access faults
  RVTEST_GOTO_MMODE                             // return to M-mode after VS case

  test1_rsw00:
  RVTEST_SIGUPD(x2, x5, x4, a3, test1_rsw00, test1_rsw00_str)  // record result in signature

//---------------------------------------------------------------------------------------------------------------------------------
// Test case 2: G leaf RSW=01 | Expected: Successful
// cp_hgatp_pte_rsw bin: g_pte_rsw=01
//---------------------------------------------------------------------------------------------------------------------------------
  G_PTE_SETUP(sv32x4, test_region, (PTE_D | PTE_A | PTE_U | PTE_W | PTE_R | PTE_V | (PTE_SOFT & 0x100)), gpa_data, LEVEL0)  // set RSW bit 8
  hfence.gvma                                   // flush G TLB so next access rewalks

  RVTEST_GOTO_LOWER_MODE VSmode                 // enter VS for Bare GPA load
  lw   a4, 0(a5)                                // VS load; RSW=01 must not affect access
  nop                                           // trap-skip padding if previous access faults
  RVTEST_GOTO_MMODE                             // return to M-mode after VS case

  test2_rsw01:
  RVTEST_SIGUPD(x2, x5, x4, a4, test2_rsw01, test2_rsw01_str)  // record result in signature

//---------------------------------------------------------------------------------------------------------------------------------
// Test case 3: G leaf RSW=10 | Expected: Successful
// cp_hgatp_pte_rsw bin: g_pte_rsw=10
//---------------------------------------------------------------------------------------------------------------------------------
  G_PTE_SETUP(sv32x4, test_region, (PTE_D | PTE_A | PTE_U | PTE_W | PTE_R | PTE_V | (PTE_SOFT & 0x200)), gpa_data, LEVEL0)  // set RSW bit 9
  hfence.gvma                                   // flush G TLB so next access rewalks

  RVTEST_GOTO_LOWER_MODE VSmode                 // enter VS for Bare GPA load
  lw   a6, 0(a5)                                // VS load; RSW=10 must not affect access
  nop                                           // trap-skip padding if previous access faults
  RVTEST_GOTO_MMODE                             // return to M-mode after VS case

  test3_rsw10:
  RVTEST_SIGUPD(x2, x5, x4, a6, test3_rsw10, test3_rsw10_str)  // record result in signature

//---------------------------------------------------------------------------------------------------------------------------------
// Test case 4: G leaf RSW=11 | Expected: Successful
// cp_hgatp_pte_rsw bin: g_pte_rsw=11
//---------------------------------------------------------------------------------------------------------------------------------
  G_PTE_SETUP(sv32x4, test_region, (PTE_D | PTE_A | PTE_U | PTE_W | PTE_R | PTE_V | PTE_SOFT), gpa_data, LEVEL0)  // RSW both bits set
  hfence.gvma                                   // flush G TLB so next access rewalks

  RVTEST_GOTO_LOWER_MODE VSmode                 // enter VS for Bare GPA load
  lw   a7, 0(a5)                                // VS load; RSW=11 must not affect access
  nop                                           // trap-skip padding if previous access faults
  RVTEST_GOTO_MMODE                             // return to M-mode after VS case

  test4_rsw11:
  RVTEST_SIGUPD(x2, x5, x4, a7, test4_rsw11, test4_rsw11_str)  // record result in signature

//---------------------------------------------------------------------------------------------------------------------------------
// Test case 5: HS HLV with RSW=11 | Expected: Successful
// cp_hgatp_pte_rsw bin: priv_mode HS, read_write_acc with RSW=11
//---------------------------------------------------------------------------------------------------------------------------------
  RVTEST_GOTO_LOWER_MODE HSmode                 // enter HS for hypervisor load
  LI(s2, 0)                                     // clear result register before HLV
  LI(t1, gpa_data)                              // t1 = GPA pointer for HLV (vsatp Bare ⇒ GPA is the address)
  hlv.w s2, (t1)                                // HS hypervisor load; RSW is software-reserved, must not fault
  nop                                           // trap-skip padding if previous access faults
  RVTEST_GOTO_MMODE                             // return to M-mode after HS case

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

test1_rsw00_str: .string "\"Mismatch on VS lw with G RSW=00 in Test Case 1!\""
test2_rsw01_str: .string "\"Mismatch on VS lw with G RSW=01 in Test Case 2!\""
test3_rsw10_str: .string "\"Mismatch on VS lw with G RSW=10 in Test Case 3!\""
test4_rsw11_str: .string "\"Mismatch on VS lw with G RSW=11 in Test Case 4!\""
test5_hlv_str:   .string "\"Mismatch on HS HLV with G RSW=11 in Test Case 5!\""

RVTEST_DATA_END
RVTEST_SIG_SETUP
