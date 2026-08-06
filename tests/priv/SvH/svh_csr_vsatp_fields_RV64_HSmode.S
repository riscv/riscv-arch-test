// --------------------------------------------------------------------------------------------------------------------------------
// svh_csr_vsatp_fields_RV64_HSmode.S
// Config: sail-rv64-max | HS writes vsatp; hgatp=Bare
// Pair:   svh_csr_vsatp_fields_HSmode.S
// Coverpoints mapped (SvH_cg): cp_vsatp_mode_field, cp_vsatp_ppn_field, cp_vsatp_asidlen_detect
// What this proves (one line):
//   On RV64, from HS, vsatp MODE / PPN / ASID write+read works.
// --------------------------------------------------------------------------------------------------------------------------------
// Test cases are as follows:
// --------------------------------------------------------------------------------------------------------------------------------
//  1. Set vsatp.MODE=Sv39 with PPN=0 from HS → Successful (readback)
//  2. Try vsatp.MODE encodings 0..15 (WARL walk) → Successful (each readback)
//  3. Set vsatp.MODE=1 sample → Successful (readback)
//  4. vsatp.ASID = all ones with MODE=Sv39 → Successful (ASIDLEN detect)
//  5. vsatp.PPN = all ones with MODE=Sv39 → Successful
//  6. Walking ones on vsatp.PPN bits [43:0] with MODE=Sv39 → Successful
//
// Total Expected Faults :: 0
// --------------------------------------------------------------------------------------------------------------------------------

##### START_TEST_CONFIG #####
# REQUIRED_EXTENSIONS: [I, H, Sv39]
# MARCH: rv64ih_zicsr_zifencei
##### END_TEST_CONFIG #####

#define TEST_FILE "svh_csr_vsatp_fields_RV64_HSmode.S"
#define SIGUPD_COUNT 64
#define TRAP_SIGUPD_COUNT 16
#define RVTEST_HYPERVISOR

// Mode hops (T-SBI) — return-to-M always uses RVTEST_TSBI_GOTO_MMODE (ecall a0=1;
//   handler rtn2mmode relocates EPC VA→PA). Enter:
//   • Code at PA / identity: RVTEST_TSBI_GOTO_VSMODE / _SMODE (ecall a0=4/2)
//   • Guest code VA≠PA (V_SAVE_AREA_*): RVTEST_GOTO_LOWER_MODE (mret + PA↔VA relocate)
#include "riscv_arch_test.h"

RVTEST_BEGIN

main:
  // Partner stage off (sheet: vsatp CSR tests use hgatp Bare)
  csrw hgatp, x0                                // hgatp=0 → G-stage Bare (isolate vsatp field bins)
  hfence.gvma                                   // flush old G TLB after hgatp clear
  RVTEST_TSBI_GOTO_SMODE                       // T-SBI: ecall a0=2 → HS/S (code at PA / identity)

//---------------------------------------------------------------------------------------------------------------------------------
// Test case 1: Set vsatp.MODE=Sv39, PPN=0 | Expected: Successful
//---------------------------------------------------------------------------------------------------------------------------------
  // cp_vsatp_mode_field bin: MODE=Sv39, PPN=0
  LI(t0, (SATP_MODE_SV39 << 60))                // RV64: MODE in bits [63:60]
  csrw vsatp, t0                                // write guest page-table CSR
  test1_mode:
  RVTEST_SIGUPD_CSR_READ(vsatp, a4, test1_mode, test1_mode_str)  // signature: read vsatp after MODE=Sv39 write

//---------------------------------------------------------------------------------------------------------------------------------
// Test case 2: Try vsatp.MODE encodings 0..15 | Expected: Successful
//---------------------------------------------------------------------------------------------------------------------------------
  // cp_vsatp_mode_field bin: WARL walk — try MODE encodings 0..15, read back legal value
  LI(t3, 0)                                     // bit/index = 0
mode_walk:
  sll t0, t3, 60                                // put t3 into MODE field
  csrw vsatp, t0                                // write that MODE
  test2_mode_walk:
  RVTEST_SIGUPD_CSR_READ(vsatp, a4, test2_mode_walk, test2_mode_walk_str)  // signature: read vsatp after each MODE WARL try
  addi t3, t3, 1                                // next MODE value
  LI(t4, 16)                                    // loop until 16 MODE values tried
  blt t3, t4, mode_walk                         // 16 tries

//---------------------------------------------------------------------------------------------------------------------------------
// Test case 3: Set vsatp.MODE=1 sample | Expected: Successful
//---------------------------------------------------------------------------------------------------------------------------------
  // cp_vsatp_mode_field bin: unsupported MODE=1 sample (WARL should not keep illegal encoding)
  LI(t0, (1 << 60))                             // MODE = 1 sample
  csrw vsatp, t0                                // write vsatp (guest page-table CSR)
  test3_mode1:
  RVTEST_SIGUPD_CSR_READ(vsatp, a4, test3_mode1, test3_mode1_str)  // signature: read vsatp after illegal MODE=1 sample

//---------------------------------------------------------------------------------------------------------------------------------
// Test case 4: vsatp.ASID = all ones | Expected: Successful
//---------------------------------------------------------------------------------------------------------------------------------
  // cp_vsatp_asidlen_detect bin: write all ASID bits, read back WARL-truncated value
  LI(t0, (SATP_MODE_SV39 << 60) | SATP64_ASID)  // Sv39 + every ASID bit
  csrw vsatp, t0                                // write vsatp (guest page-table CSR)
  test4_asid:
  RVTEST_SIGUPD_CSR_READ(vsatp, a4, test4_asid, test4_asid_str)  // signature: read vsatp after ASID all-ones write

//---------------------------------------------------------------------------------------------------------------------------------
// Test case 5: vsatp.PPN = all ones | Expected: Successful
//---------------------------------------------------------------------------------------------------------------------------------
  // cp_vsatp_ppn_field bin: PPN all-ones (44 bits on RV64)
  LI(t0, (SATP_MODE_SV39 << 60))                // t0 = MODE Sv39 only
  LI(t1, -1)                                    // t1 = all ones
  slli t1, t1, 20                               // shift to isolate high bits
  srli t1, t1, 20                               // keep low 44 bits = 1
  or   t0, t0, t1                               // merge MODE with PPN/bit
  csrw vsatp, t0                                // write vsatp (guest page-table CSR)
  test5_ppn_ones:
  RVTEST_SIGUPD_CSR_READ(vsatp, a4, test5_ppn_ones, test5_ppn_ones_str)  // signature: read vsatp after PPN all-ones write

//---------------------------------------------------------------------------------------------------------------------------------
// Test case 6: Walking ones on vsatp.PPN | Expected: Successful
//---------------------------------------------------------------------------------------------------------------------------------
  // cp_vsatp_ppn_field bin: walking-1 on PPN[43:0] (one bit set per iteration)
  LI(t3, 0)                                     // bit index
ppn_walk:
  LI(t0, (SATP_MODE_SV39 << 60))                // MODE only
  LI(t1, 1)                                     // t1 = 1 (will shift into one bit)
  sll t1, t1, t3                                // one PPN bit
  or  t0, t0, t1                                // merge MODE with PPN/bit
  csrw vsatp, t0                                // write vsatp (guest page-table CSR)
  test6_ppn_walk:
  RVTEST_SIGUPD_CSR_READ(vsatp, a4, test6_ppn_walk, test6_ppn_walk_str)  // signature: read vsatp after each PPN walk step
  addi t3, t3, 1                                // next bit/index
  LI(t4, 44)                                    // loop until PPN bits done (44)
  blt t3, t4, ppn_walk                          // bits 0..43

  RVTEST_TSBI_GOTO_MMODE                       // T-SBI: ecall a0=1 → M (rtn2mmode VA→PA relocate)

//---------------------------------------------------------------------------------------------------------------------------------
RVTEST_CODE_END
RVTEST_DATA_BEGIN
// PASS/FAIL message strings for signature compares

test1_mode_str:       .string "\"Mismatch on setting vsatp.MODE=Sv39 (PPN=0) in Test Case 1!\""
test2_mode_walk_str:  .string "\"Mismatch on vsatp.MODE WARL walk in Test Case 2!\""
test3_mode1_str:      .string "\"Mismatch on setting vsatp.MODE=1 in Test Case 3!\""
test4_asid_str:       .string "\"Mismatch on vsatp.ASID=all-ones in Test Case 4!\""
test5_ppn_ones_str:   .string "\"Mismatch on vsatp.PPN=all-ones in Test Case 5!\""
test6_ppn_walk_str:   .string "\"Mismatch on walking ones in vsatp.PPN in Test Case 6!\""

RVTEST_DATA_END
RVTEST_SIG_SETUP
