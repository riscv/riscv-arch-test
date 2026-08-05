// --------------------------------------------------------------------------------------------------------------------------------
// svh_vs_pte_attr_VSmode.S
// Config: sail-rv32-max | VS=Sv32 ON, hgatp=Bare
// Coverpoints mapped (SvH_cg): cp_vsatp_pte_rsw
// What this proves (one line):
//   VS-stage PTE RSW[9:8] is preserved; stores/loads succeed for all RSW encodings.
// --------------------------------------------------------------------------------------------------------------------------------
// Test cases are as follows:
// --------------------------------------------------------------------------------------------------------------------------------
//  1. RSW=00 (no PTE_SOFT): VS sw/lw → Successful (0x257A0301)
//  2. RSW=01 (0x100): update PTE, VS lw → Successful (0x257A0302)
//  3. RSW=10 (0x200): update PTE, VS lw → Successful (0x257A0303)
//  4. RSW=11 (PTE_SOFT=0x300): update PTE, VS lw → Successful (0x257A0304)
//
// Total Expected Faults :: 0
// --------------------------------------------------------------------------------------------------------------------------------

##### START_TEST_CONFIG #####
# REQUIRED_EXTENSIONS: [I, H, Sv32]
# MARCH: rv32ih_zicsr_zifencei
##### END_TEST_CONFIG #####

#define TEST_FILE "svh_vs_pte_attr_VSmode.S"
#define SIGUPD_COUNT 4
#define TRAP_SIGUPD_COUNT 64
#define RVTEST_HYPERVISOR

#include "riscv_arch_test.h"

RVTEST_BEGIN

main:
  .set va_data,                 0x008001000     // GVA for R/W data leaf (same VA, varying RSW bits)
  .set va_code,                 0x90000000      // GVA where VS executes this code (U=0)

  // ---- VS-stage (vsatp Sv32): GVA -> PA  (hgatp Bare ⇒ PTE PPN fields are real PAs) ----
  SUPERPAGE_VS_PTE_SETUP(sv32, rvtest_code_begin, (PTE_D | PTE_A | PTE_X | PTE_R | PTE_V), va_code, LEVEL1)  // leaf: va_code -> PA(code); LEVEL1 = 4 MiB X/R

  csrr a0, mscratch                             // a0 = Msave_area (required by next macro)
  V_SAVE_AREA_SETUP(va_code, rvtest_code_begin, code, LEVEL1)  // framework: VS entry PC is under va_code

  VS_PTE_SETUP(sv32, PA, rvtest_vlvl0_pg_tbl, (PTE_V), va_data, LEVEL1)  // non-leaf: va_data VPN1 -> VS L0 table PA
  VS_PTE_SETUP(sv32, PA, test_region, (PTE_D | PTE_A | PTE_W | PTE_R | PTE_V), va_data, LEVEL0)  // leaf: va_data -> PA(test_region) R/W; RSW=00 initially

  VSATP_SETUP(sv32, PA)                         // vsatp = Sv32, PPN = PA of VS root
  csrw hgatp, x0                                // hgatp = Bare (no G-stage)
  hfence.vvma                                   // invalidate VS-stage TLB entries
  hfence.gvma                                   // invalidate G-stage TLB entries (harmless with Bare)

  LI(a5, va_data)                               // a5 = GVA of data leaf (reused across RSW cases)

//---------------------------------------------------------------------------------------------------------------------------------
// Test case 1: RSW=00 VS sw/lw | Expected: Successful
//---------------------------------------------------------------------------------------------------------------------------------
  LI(t0, 0x257A0301)                            // payload for case 1
  la t1, test_region                            // t1 = SPA
  sw t0, 0(t1)                                  // poison SPA before guest access (M-mode baseline)

  RVTEST_GOTO_LOWER_MODE VSmode                 // M -> VS
  sw   t0, 0(a5)                                // VS store through RSW=00 leaf
  nop                                           // trap-skip padding after store
  lw   a3, 0(a5)                                // VS load; expect 0x257A0301 (RSW must not break access)
  nop                                           // trap-skip padding after load
  RVTEST_GOTO_MMODE                             // VS -> M

  test1_rsw00:
  RVTEST_SIGUPD(x2, x5, x4, a3, test1_rsw00, test1_rsw00_str)  // record case 1 lw result in signature

//---------------------------------------------------------------------------------------------------------------------------------
// Test case 2: RSW=01 (0x100) VS lw | Expected: Successful
//---------------------------------------------------------------------------------------------------------------------------------
  VS_PTE_SETUP(sv32, PA, test_region, (PTE_D | PTE_A | PTE_W | PTE_R | PTE_V | 0x100), va_data, LEVEL0)  // leaf: same VA, RSW=01 (bits [9:8]=01)
  hfence.vvma                                   // flush TLB so guest sees updated RSW bits

  LI(t0, 0x257A0302)                            // payload for case 2
  la t1, test_region                            // t1 = SPA
  sw t0, 0(t1)                                  // poison SPA with new expected value

  RVTEST_GOTO_LOWER_MODE VSmode                 // M -> VS
  sw   t0, 0(a5)                                // VS store through RSW=01 leaf
  nop                                           // trap-skip padding after store
  lw   a4, 0(a5)                                // VS load; expect 0x257A0302
  nop                                           // trap-skip padding after load
  RVTEST_GOTO_MMODE                             // VS -> M

  test2_rsw01:
  RVTEST_SIGUPD(x2, x5, x4, a4, test2_rsw01, test2_rsw01_str)  // record case 2 lw result in signature

//---------------------------------------------------------------------------------------------------------------------------------
// Test case 3: RSW=10 (0x200) VS lw | Expected: Successful
//---------------------------------------------------------------------------------------------------------------------------------
  VS_PTE_SETUP(sv32, PA, test_region, (PTE_D | PTE_A | PTE_W | PTE_R | PTE_V | 0x200), va_data, LEVEL0)  // leaf: same VA, RSW=10 (bits [9:8]=10)
  hfence.vvma                                   // flush TLB after PTE rewrite

  LI(t0, 0x257A0303)                            // payload for case 3
  la t1, test_region                            // t1 = SPA
  sw t0, 0(t1)                                  // poison SPA with new expected value

  RVTEST_GOTO_LOWER_MODE VSmode                 // M -> VS
  sw   t0, 0(a5)                                // VS store through RSW=10 leaf
  nop                                           // trap-skip padding after store
  lw   a6, 0(a5)                                // expect 0x257A0303
  nop                                           // trap-skip padding after load
  RVTEST_GOTO_MMODE                             // VS -> M

  test3_rsw10:
  RVTEST_SIGUPD(x2, x5, x4, a6, test3_rsw10, test3_rsw10_str)  // record case 3 lw result in signature

//---------------------------------------------------------------------------------------------------------------------------------
// Test case 4: RSW=11 (PTE_SOFT=0x300) VS lw | Expected: Successful
//---------------------------------------------------------------------------------------------------------------------------------
  VS_PTE_SETUP(sv32, PA, test_region, (PTE_D | PTE_A | PTE_W | PTE_R | PTE_V | PTE_SOFT), va_data, LEVEL0)  // leaf: same VA, RSW=11 via PTE_SOFT
  hfence.vvma                                   // flush TLB after final RSW encoding

  LI(t0, 0x257A0304)                            // payload for case 4
  la t1, test_region                            // t1 = SPA
  sw t0, 0(t1)                                  // poison SPA with new expected value

  RVTEST_GOTO_LOWER_MODE VSmode                 // M -> VS
  sw   t0, 0(a5)                                // VS store through RSW=11 leaf
  nop                                           // trap-skip padding after store
  lw   a7, 0(a5)                                // expect 0x257A0304
  nop                                           // trap-skip padding after load
  RVTEST_GOTO_MMODE                             // VS -> M

  test4_rsw11:
  RVTEST_SIGUPD(x2, x5, x4, a7, test4_rsw11, test4_rsw11_str)  // record case 4 lw result in signature

//---------------------------------------------------------------------------------------------------------------------------------
RVTEST_CODE_END
RVTEST_DATA_BEGIN

.align 12                                       // 4 KiB page align
test_region:                                    // real PA backing va_data (RSW probe target)
  .word 0                                       // data word (initially 0)
  .word 0                                       // data word (initially 0)
  .word 0                                       // data word (initially 0)
  .word 0                                       // data word (initially 0)

.align 12                                       // align to 4 KiB page
rvtest_vlvl0_pg_tbl:                            // VS-stage level-0 PTE storage
  .zero(4096)                                   // 4 KiB page-table storage

test1_rsw00_str: .string "\"Mismatch on RSW=00 VS lw in Test Case 1!\""
test2_rsw01_str: .string "\"Mismatch on RSW=01 VS lw in Test Case 2!\""
test3_rsw10_str: .string "\"Mismatch on RSW=10 VS lw in Test Case 3!\""
test4_rsw11_str: .string "\"Mismatch on RSW=11 VS lw in Test Case 4!\""

RVTEST_DATA_END
RVTEST_SIG_SETUP
