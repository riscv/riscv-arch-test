// --------------------------------------------------------------------------------------------------------------------------------
// svh_csr_satp_mode_VSmode.S
// Config: sail-rv64-max | VS writes satp MODE; hgatp=Bare
// Coverpoints mapped (SvH_cg): cp_satp_mode_field
// What this proves (one line):
//   In VS, satp.MODE is WARL; satp and vsatp stay aliases.
// --------------------------------------------------------------------------------------------------------------------------------
// Test cases are as follows:
// --------------------------------------------------------------------------------------------------------------------------------
//  1. Read satp/vsatp alias with MODE=Sv39 in VS → Successful
//  2. Walk satp.MODE 0..15 (restore Sv39 each iter); dump last WARL sample → Successful
//  3. Final satp read after MODE walk → Successful
//
// Total Expected Faults :: 0
// --------------------------------------------------------------------------------------------------------------------------------

##### START_TEST_CONFIG #####
# REQUIRED_EXTENSIONS: [I, H, Sv39]
# MARCH: rv64ih_zicsr_zifencei
##### END_TEST_CONFIG #####

#define TEST_FILE "svh_csr_satp_mode_VSmode.S"
#define SIGUPD_COUNT 4
#define TRAP_SIGUPD_COUNT 32
#define RVTEST_HYPERVISOR

// Mode hops (T-SBI) — return-to-M always uses RVTEST_TSBI_GOTO_MMODE (ecall a0=1;
//   handler rtn2mmode relocates EPC VA→PA). Enter:
//   • Code at PA / identity: RVTEST_TSBI_GOTO_VSMODE / _SMODE (ecall a0=4/2)
//   • Guest code VA≠PA (V_SAVE_AREA_*): RVTEST_GOTO_LOWER_MODE (mret + PA↔VA relocate)
#include "riscv_arch_test.h"

RVTEST_BEGIN

main:
  // ---- VS-stage map: keep code reachable while satp.MODE is flipped in VS ----
  // Keep PC mapped while we change MODE: VA 0x80000000 → real code PA
  .set va_code, 0x0000000080000000              // GVA where VS executes this test code

  VS_PTE_SETUP(sv39, PA, rvtest_code_begin, (PTE_D | PTE_A | PTE_X | PTE_R | PTE_W | PTE_V), va_code, LEVEL2)  // map code so MODE flips cannot unmap us
  csrr a0, mscratch                             // needed by V_SAVE_AREA_SETUP
  V_SAVE_AREA_SETUP(va_code, rvtest_code_begin, code, LEVEL2)  // tell framework: VS entry PC = va_code
  VSATP_SETUP(sv39, PA)                         // turn on VS paging (root at PA)
  csrw hgatp, x0                                // G Bare (isolate satp/vsatp alias test)
  hfence.vvma                                   // flush VS-stage TLB after vsatp write
  hfence.gvma                                   // flush G-stage TLB (hgatp Bare)

//---------------------------------------------------------------------------------------------------------------------------------
// Test case 1: Read satp/vsatp alias with MODE=Sv39 | Expected: Successful
//---------------------------------------------------------------------------------------------------------------------------------
  // cp_satp_mode_field bin: satp and vsatp are aliases in VS (both must read Sv39)
  RVTEST_GOTO_LOWER_MODE VSmode                 // M→VSmode mret + PA↔VA relocate (guest code VA≠PA; T-SBI enter lacks relocate)
  csrr a3, satp                                 // guest sees satp (should be Sv39)
  csrr a4, vsatp                                // vsatp must match (alias)
  RVTEST_TSBI_GOTO_MMODE                       // T-SBI: ecall a0=1 → M (rtn2mmode VA→PA relocate)

  test1_satp:
  RVTEST_SIGUPD(x2, x5, x4, a3, test1_satp, test1_satp_str)  // signature: satp read in VS (Sv39)
  test1_vsatp:
  RVTEST_SIGUPD(x2, x5, x4, a4, test1_vsatp, test1_vsatp_str)  // signature: vsatp alias must match satp

//---------------------------------------------------------------------------------------------------------------------------------
// Test case 2: Walk satp.MODE 0..15 | Expected: Successful
//---------------------------------------------------------------------------------------------------------------------------------
  // cp_satp_mode_field bin: WARL walk 0..15; restore Sv39 each iter so PC stays mapped
  // Walk MODE 0..15 but keep same PPN; restore Sv39 each time so PC stays mapped
  RVTEST_GOTO_LOWER_MODE VSmode                 // M→VSmode mret + PA↔VA relocate (guest code VA≠PA; T-SBI enter lacks relocate)
  csrr t2, satp                                 // save current satp
  li   t0, ~((0xF) << 60)                       // mask to clear MODE nibble
  and  t2, t2, t0                               // strip MODE; keep PPN/ASID
  LI(t3, 0)                                     // bit/index = 0
mode_walk:
  sll  t0, t3, 60                               // candidate MODE
  or   t1, t2, t0                               // combine kept PPN/ASID with MODE
  csrw satp, t1                                 // try that MODE (WARL may rewrite illegal values)
  csrr a5, satp                                 // last WARL sample kept in a5 for signature
  li   t0, (SATP_MODE_SV39 << 60)               // put Sv39 back before next ifetch
  or   t1, t2, t0                               // combine kept PPN/ASID with MODE
  csrw satp, t1                                 // restore so next fetch works
  addi t3, t3, 1                                // next bit/index
  LI(t4, 16)                                    // loop until 16 MODE values tried
  blt  t3, t4, mode_walk                        // repeat until all MODE values tried
  RVTEST_TSBI_GOTO_MMODE                       // T-SBI: ecall a0=1 → M (rtn2mmode VA→PA relocate)

  test2_mode_walk:
  RVTEST_SIGUPD(x2, x5, x4, a5, test2_mode_walk, test2_mode_walk_str)  // signature: last WARL MODE sample from walk

//---------------------------------------------------------------------------------------------------------------------------------
// Test case 3: Final satp read after MODE walk | Expected: Successful
//---------------------------------------------------------------------------------------------------------------------------------
  RVTEST_GOTO_LOWER_MODE VSmode                 // M→VSmode mret + PA↔VA relocate (guest code VA≠PA; T-SBI enter lacks relocate)
  csrr a6, satp                                 // final satp after loop
  RVTEST_TSBI_GOTO_MMODE                       // T-SBI: ecall a0=1 → M (rtn2mmode VA→PA relocate)

  test3_final:
  RVTEST_SIGUPD(x2, x5, x4, a6, test3_final, test3_final_str)  // signature: final satp after MODE walk

//---------------------------------------------------------------------------------------------------------------------------------
RVTEST_CODE_END
RVTEST_DATA_BEGIN
// PASS/FAIL message strings for signature compares

test1_satp_str:       .string "\"Mismatch on satp read (Sv39) in Test Case 1!\""
test1_vsatp_str:      .string "\"Mismatch on vsatp alias read in Test Case 1!\""
test2_mode_walk_str:  .string "\"Mismatch on satp.MODE WARL walk in Test Case 2!\""
test3_final_str:      .string "\"Mismatch on final satp read in Test Case 3!\""

RVTEST_DATA_END
RVTEST_SIG_SETUP
