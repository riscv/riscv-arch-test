// --------------------------------------------------------------------------------------------------------------------------------
// svh_csr_vsatp_fields_HSmode.S
// Config: sail-rv32-max | HS writes vsatp; hgatp=Bare
// Pair:   svh_csr_vsatp_fields_RV64_HSmode.S
// Coverpoints mapped (SvH_cg): cp_vsatp_mode_field, cp_vsatp_ppn_field, cp_vsatp_asidlen_detect
// What this proves (one line):
//   From HS, vsatp MODE / PPN / ASID can be written and read back.
// --------------------------------------------------------------------------------------------------------------------------------
// Test cases are as follows:
// --------------------------------------------------------------------------------------------------------------------------------
//  1. Set vsatp.MODE=Sv32 with PPN=0 from HS → Successful (readback)
//  2. vsatp.ASID = all ones with MODE=Sv32 → Successful (ASIDLEN detect)
//  3. vsatp.PPN = all ones with MODE=Sv32 → Successful
//  4. Walking ones on vsatp.PPN bits [21:0] with MODE=Sv32 → Successful
//
// Total Expected Faults :: 0
// --------------------------------------------------------------------------------------------------------------------------------

##### START_TEST_CONFIG #####
# REQUIRED_EXTENSIONS: [I, H, Sv32]
# MARCH: rv32ih_zicsr_zifencei
##### END_TEST_CONFIG #####

#define TEST_FILE "svh_csr_vsatp_fields_HSmode.S"
#define SIGUPD_COUNT 25
#define TRAP_SIGUPD_COUNT 16
#define RVTEST_HYPERVISOR

#include "riscv_arch_test.h"

RVTEST_BEGIN

main:
  // Partner stage off (sheet: vsatp CSR tests use hgatp Bare)
  csrw hgatp, x0                                // hgatp=0 → G-stage Bare (isolate vsatp field bins)
  hfence.gvma                                   // flush old G TLB after hgatp clear
  RVTEST_GOTO_LOWER_MODE HSmode                 // HS can write vsatp (not VS)

//---------------------------------------------------------------------------------------------------------------------------------
// Test case 1: Set vsatp.MODE=Sv32, PPN=0 | Expected: Successful
//---------------------------------------------------------------------------------------------------------------------------------
  // cp_vsatp_mode_field bin: MODE=Sv32, PPN=0
  LI(t0, (SATP_MODE_SV32 << 31))                // RV32: MODE bit 31, PPN clear
  csrw vsatp, t0                                // write guest page-table CSR
  test1_mode:
  RVTEST_SIGUPD_CSR_READ(vsatp, a4, test1_mode, test1_mode_str)  // signature: read vsatp after MODE=Sv32 write

//---------------------------------------------------------------------------------------------------------------------------------
// Test case 2: vsatp.ASID = all ones | Expected: Successful
//---------------------------------------------------------------------------------------------------------------------------------
  // cp_vsatp_asidlen_detect bin: write all ASID bits, read back WARL-truncated value
  LI(t0, (SATP_MODE_SV32 << 31) | SATP32_ASID)  // MODE + every ASID bit
  csrw vsatp, t0                                // write vsatp with MODE + all ASID bits (ASIDLEN detect)
  test2_asid:
  RVTEST_SIGUPD_CSR_READ(vsatp, a4, test2_asid, test2_asid_str)  // signature: read vsatp after ASID all-ones write

//---------------------------------------------------------------------------------------------------------------------------------
// Test case 3: vsatp.PPN = all ones | Expected: Successful
//---------------------------------------------------------------------------------------------------------------------------------
  // cp_vsatp_ppn_field bin: PPN all-ones (22 bits on RV32)
  LI(t0, (SATP_MODE_SV32 << 31) | 0x3FFFFF)     // MODE + PPN ones (22 bits)
  csrw vsatp, t0                                // write vsatp with MODE + PPN all-ones
  test3_ppn_ones:
  RVTEST_SIGUPD_CSR_READ(vsatp, a4, test3_ppn_ones, test3_ppn_ones_str)  // signature: read vsatp after PPN all-ones write

//---------------------------------------------------------------------------------------------------------------------------------
// Test case 4: Walking ones on vsatp.PPN | Expected: Successful
//---------------------------------------------------------------------------------------------------------------------------------
  // cp_vsatp_ppn_field bin: walking-1 on PPN[21:0] (one bit set per iteration)
  LI(t3, 0)                                     // bit index
ppn_walk:
  LI(t0, (SATP_MODE_SV32 << 31))                // MODE only
  LI(t1, 1)                                     // t1 = 1 (will shift into one PPN bit)
  sll t1, t1, t3                                // t1 = 1 << bit
  or  t0, t0, t1                                // merge MODE with this walking-1 PPN bit
  csrw vsatp, t0                                // write vsatp with MODE + one PPN bit
  test4_ppn_walk:
  RVTEST_SIGUPD_CSR_READ(vsatp, a4, test4_ppn_walk, test4_ppn_walk_str)  // signature: read vsatp after each PPN walk step
  addi t3, t3, 1                                // next PPN bit index
  LI(t4, 22)                                    // stop after bits 0..21 (22 iterations)
  blt t3, t4, ppn_walk                          // bits 0..21

  RVTEST_GOTO_MMODE                             // return to M for next case / SIGUPD

//---------------------------------------------------------------------------------------------------------------------------------
RVTEST_CODE_END
RVTEST_DATA_BEGIN
// PASS/FAIL message strings for signature compares

test1_mode_str:     .string "\"Mismatch on setting vsatp.MODE=Sv32 (PPN=0) in Test Case 1!\""
test2_asid_str:     .string "\"Mismatch on vsatp.ASID=all-ones in Test Case 2!\""
test3_ppn_ones_str: .string "\"Mismatch on vsatp.PPN=all-ones in Test Case 3!\""
test4_ppn_walk_str: .string "\"Mismatch on walking ones in vsatp.PPN in Test Case 4!\""

RVTEST_DATA_END
RVTEST_SIG_SETUP
