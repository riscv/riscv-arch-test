// --------------------------------------------------------------------------------------------------------------------------------
// svh_csr_hgatp_fields_RV64_HSmode.S
// Config: sail-rv64-max | HS writes hgatp; vsatp=Bare
// Pair:   svh_csr_hgatp_fields_HSmode.S
// Coverpoints mapped (SvH_cg): cp_hgatp_mode_field, cp_hgatp_ppn_field, cp_hgatp_vmidlen_detect, cp_hgatp_vmid_scoping
// What this proves (one line):
//   On RV64, from HS, hgatp MODE / PPN / VMID write+read works.
// --------------------------------------------------------------------------------------------------------------------------------
// Test cases are as follows:
// --------------------------------------------------------------------------------------------------------------------------------
//  1. Set hgatp.MODE=Sv39x4 with PPN=0 from HS → Successful (readback)
//  2. Try hgatp.MODE encodings 0..15 (WARL walk) → Successful (each readback)
//  3. Set hgatp.MODE=1 sample → Successful (readback)
//  4. hgatp.VMID = all ones with MODE=Sv39x4 → Successful (VMIDLEN + scoping readbacks)
//  5. hgatp.PPN = all ones (PPN[1:0]=0) with MODE=Sv39x4 → Successful
//  6. Walking ones on hgatp.PPN bits [43:2] with MODE=Sv39x4 → Successful
//
// Total Expected Faults :: 0
// --------------------------------------------------------------------------------------------------------------------------------

##### START_TEST_CONFIG #####
# REQUIRED_EXTENSIONS: [I, H, Sv39]
# MARCH: rv64ih_zicsr_zifencei
##### END_TEST_CONFIG #####

#define TEST_FILE "svh_csr_hgatp_fields_RV64_HSmode.S"
#define SIGUPD_COUNT 63
#define TRAP_SIGUPD_COUNT 16
#define RVTEST_HYPERVISOR

#include "riscv_arch_test.h"

RVTEST_BEGIN

main:
  // Partner stage off (sheet rule for hgatp CSR tests)
  csrw vsatp, x0                                // VS Bare (no VS walk; isolate hgatp field bins)
  hfence.vvma                                   // flush VS-stage TLB after vsatp clear
  RVTEST_GOTO_LOWER_MODE HSmode                 // enter HS (hgatp writable from HS)

//---------------------------------------------------------------------------------------------------------------------------------
// Test case 1: Set hgatp.MODE=Sv39x4, PPN=0 | Expected: Successful
//---------------------------------------------------------------------------------------------------------------------------------
  // cp_hgatp_mode_field bin: MODE=Sv39x4, PPN=0
  LI(t0, (HGATP_MODE_SV39X4 << 60))             // RV64 MODE in [63:60]
  csrw hgatp, t0                                // write hgatp (G-stage CSR)
  test1_mode:
  RVTEST_SIGUPD_CSR_READ(hgatp, a4, test1_mode, test1_mode_str)  // signature: read hgatp after MODE=Sv39x4 write

//---------------------------------------------------------------------------------------------------------------------------------
// Test case 2: Try hgatp.MODE encodings 0..15 | Expected: Successful
//---------------------------------------------------------------------------------------------------------------------------------
  // cp_hgatp_mode_field bin: WARL walk — try MODE encodings 0..15, read back legal value
  LI(t3, 0)                                     // bit/index = 0
mode_walk:
  sll t0, t3, 60                                // MODE = t3
  csrw hgatp, t0                                // write hgatp (G-stage CSR)
  test2_mode_walk:
  RVTEST_SIGUPD_CSR_READ(hgatp, a4, test2_mode_walk, test2_mode_walk_str)  // signature: read hgatp after each MODE WARL try
  addi t3, t3, 1                                // next MODE value
  LI(t4, 16)                                    // loop until 16 MODE values tried
  blt t3, t4, mode_walk                         // repeat until all MODE values tried

//---------------------------------------------------------------------------------------------------------------------------------
// Test case 3: Set hgatp.MODE=1 sample | Expected: Successful
//---------------------------------------------------------------------------------------------------------------------------------
  // cp_hgatp_mode_field bin: unsupported MODE=1 sample (WARL should not keep illegal encoding)
  LI(t0, (1 << 60))                             // MODE = 1 sample
  csrw hgatp, t0                                // write hgatp (G-stage CSR)
  test3_mode1:
  RVTEST_SIGUPD_CSR_READ(hgatp, a4, test3_mode1, test3_mode1_str)  // signature: read hgatp after illegal MODE=1 sample

//---------------------------------------------------------------------------------------------------------------------------------
// Test case 4: hgatp.VMID = all ones | Expected: Successful
//---------------------------------------------------------------------------------------------------------------------------------
  // cp_hgatp_vmidlen_detect + cp_hgatp_vmid_scoping bins: VMID all-1s (two readbacks)
  LI(t0, (HGATP_MODE_SV39X4 << 60) | HGATP64_VMID)  // MODE + VMID all-1s
  csrw hgatp, t0                                // write hgatp (G-stage CSR)
  test4_vmid1:
  RVTEST_SIGUPD_CSR_READ(hgatp, a4, test4_vmid1, test4_vmid1_str)  // signature: VMIDLEN detect readback
  test4_vmid2:
  RVTEST_SIGUPD_CSR_READ(hgatp, a4, test4_vmid2, test4_vmid2_str)  // signature: VMID scoping readback

//---------------------------------------------------------------------------------------------------------------------------------
// Test case 5: hgatp.PPN = all ones (PPN[1:0]=0) | Expected: Successful
//---------------------------------------------------------------------------------------------------------------------------------
  // cp_hgatp_ppn_field bin: PPN all-ones with PPN[1:0]=0 (Sv*x4 root alignment)
  // PPN all-1s but clear [1:0] (Sv*x4 root align)
  LI(t0, (HGATP_MODE_SV39X4 << 60))             // t0 = MODE Sv39x4 only
  LI(t1, -1)                                    // t1 = all ones
  slli t1, t1, 20                               // shift to isolate high bits
  srli t1, t1, 20                               // low 44 bits
  andi t1, t1, -4                               // force PPN[1:0]=0
  or   t0, t0, t1                               // merge MODE with PPN/bit
  csrw hgatp, t0                                // write hgatp (G-stage CSR)
  test5_ppn_ones:
  RVTEST_SIGUPD_CSR_READ(hgatp, a4, test5_ppn_ones, test5_ppn_ones_str)  // signature: read hgatp after PPN all-ones write

//---------------------------------------------------------------------------------------------------------------------------------
// Test case 6: Walking ones on hgatp.PPN bits [43:2] | Expected: Successful
//---------------------------------------------------------------------------------------------------------------------------------
  // cp_hgatp_ppn_field bin: walking-1 on PPN[43:2] (PPN[1:0] WARL-0 for Sv*x4 root align)
  // PPN walking-1 bits 2..43
  LI(t3, 2)                                     // start PPN walk at bit 2 (bits 1:0 often WARL-0)
ppn_walk:
  LI(t0, (HGATP_MODE_SV39X4 << 60))             // t0 = MODE Sv39x4 only
  LI(t1, 1)                                     // t1 = 1 (will shift into one bit)
  sll t1, t1, t3                                // shift 1 into bit position t3
  or  t0, t0, t1                                // merge MODE with PPN/bit
  csrw hgatp, t0                                // write hgatp (G-stage CSR)
  test6_ppn_walk:
  RVTEST_SIGUPD_CSR_READ(hgatp, a4, test6_ppn_walk, test6_ppn_walk_str)  // signature: read hgatp after each PPN walk step
  addi t3, t3, 1                                // next bit/index
  LI(t4, 44)                                    // stop after bits 2..43 (42 iterations)
  blt t3, t4, ppn_walk                          // repeat until all PPN bits tried

  RVTEST_GOTO_MMODE                             // return to M for next case / SIGUPD

//---------------------------------------------------------------------------------------------------------------------------------
RVTEST_CODE_END
RVTEST_DATA_BEGIN
// PASS/FAIL message strings for signature compares

test1_mode_str:       .string "\"Mismatch on setting hgatp.MODE=Sv39x4 (PPN=0) in Test Case 1!\""
test2_mode_walk_str:  .string "\"Mismatch on hgatp.MODE WARL walk in Test Case 2!\""
test3_mode1_str:      .string "\"Mismatch on setting hgatp.MODE=1 in Test Case 3!\""
test4_vmid1_str:      .string "\"Mismatch on hgatp.VMID=all-ones (VMIDLEN) in Test Case 4!\""
test4_vmid2_str:      .string "\"Mismatch on hgatp.VMID scoping read in Test Case 4!\""
test5_ppn_ones_str:   .string "\"Mismatch on hgatp.PPN=all-ones in Test Case 5!\""
test6_ppn_walk_str:   .string "\"Mismatch on walking ones in hgatp.PPN in Test Case 6!\""

RVTEST_DATA_END
RVTEST_SIG_SETUP
