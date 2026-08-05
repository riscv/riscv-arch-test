// --------------------------------------------------------------------------------------------------------------------------------
// svh_stage_both_bare_sv39_VSmode.S
// Config: sail-rv64-max | vsatp=Bare + hgatp=Bare
// Pair:   svh_stage_both_bare_VSmode.S
// Coverpoints mapped (SvH_cg): stage_both_bare
// What this proves (one line):
//   Same as RV32 both_bare: both stages Bare ⇒ VA used as real PA (RV64).
// --------------------------------------------------------------------------------------------------------------------------------
// Test cases are as follows:
// --------------------------------------------------------------------------------------------------------------------------------
//  1. VS sw/lw with both stages Bare (VA==SPA) → Successful
//  2. M-mode SPA readback confirms VS store → Successful
//
// Total Expected Faults :: 0
// --------------------------------------------------------------------------------------------------------------------------------

##### START_TEST_CONFIG #####
# REQUIRED_EXTENSIONS: [I, H, Sv39]
# MARCH: rv64ih_zicsr_zifencei
##### END_TEST_CONFIG #####

#define TEST_FILE "svh_stage_both_bare_sv39_VSmode.S"
#define SIGUPD_COUNT 2
#define TRAP_SIGUPD_COUNT 16
#define RVTEST_HYPERVISOR

#include "riscv_arch_test.h"

RVTEST_BEGIN

main:
  // ---- Both stages Bare: no page tables; GVA/GPA used as real SPA ----
  csrw vsatp, x0                                // VS paging OFF
  csrw hgatp, x0                                // G paging OFF
  hfence.vvma                                   // flush VS-stage TLB (safe even when Bare)
  hfence.gvma                                   // flush G-stage TLB (safe even when Bare)

  LI(t0, 0xDEADBEEF)                            // poison SPA
  la t1, test_region                            // t1 = real address of test_region
  sw t0, 0(t1)                                  // store pattern to memory

  la a5, test_region                            // Bare: this VA is the SPA
  RVTEST_GOTO_LOWER_MODE VSmode                 // enter VS (guest)

//---------------------------------------------------------------------------------------------------------------------------------
// Test case 1: VS sw/lw with both stages Bare | Expected: Successful
//---------------------------------------------------------------------------------------------------------------------------------
  LI(a2, 0x257A0021)                            // value to store
  sw   a2, 0(a5)                                // stage_both_bare: VA==SPA store (no translation)
  nop                                           // pad (trap handler may skip prior insn)
  lw   a3, 0(a5)                                // load → a3
  nop                                           // pad (trap handler may skip prior insn)
  test1_vs:
  RVTEST_SIGUPD(x2, x5, x4, a3, test1_vs, test1_vs_str)  // record case 1 VS lw result in signature

  RVTEST_GOTO_MMODE                             // return to M-mode

//---------------------------------------------------------------------------------------------------------------------------------
// Test case 2: M-mode SPA readback | Expected: Successful
//---------------------------------------------------------------------------------------------------------------------------------
  la t1, test_region                            // t1 = real address of test_region
  lw t2, 0(t1)                                  // expect 0x257A0021
  test2_spa:
  RVTEST_SIGUPD(x2, x5, x4, t2, test2_spa, test2_spa_str)  // record case 2 SPA readback in signature

//---------------------------------------------------------------------------------------------------------------------------------
RVTEST_CODE_END
RVTEST_DATA_BEGIN

.align 12                                       // align to 4 KiB page
test_region:                                    // real memory used as VA and SPA
  .word 0                                       // data word (initially 0)
  .word 0                                       // data word (initially 0)
  .word 0                                       // data word (initially 0)
  .word 0                                       // data word (initially 0)

test1_vs_str:  .string "\"Mismatch on VS lw after sw (both Bare) in Test Case 1!\""
test2_spa_str: .string "\"Mismatch on SPA readback after VS store in Test Case 2!\""

RVTEST_DATA_END
RVTEST_SIG_SETUP
