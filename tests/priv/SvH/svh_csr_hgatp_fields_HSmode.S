// --------------------------------------------------------------------------------------------------------------------------------
// svh_csr_hgatp_fields_HSmode.S
// Config: sail-rv32-max | HS writes hgatp; vsatp=Bare
// Pair:   svh_csr_hgatp_fields_RV64_HSmode.S
// Coverpoints mapped (SvH_cg): cp_hgatp_mode_field, cp_hgatp_ppn_field, cp_hgatp_vmidlen_detect, cp_hgatp_vmid_scoping
// What this proves (one line):
//   From HS, hgatp MODE / PPN / VMID can be written and read back.
// --------------------------------------------------------------------------------------------------------------------------------
// Test cases are as follows:
// --------------------------------------------------------------------------------------------------------------------------------
//  1. Set hgatp.MODE=Sv32x4 with PPN=0 from HS → Successful (readback)
//  2. hgatp.VMID = all ones with MODE=Sv32x4 → Successful (VMIDLEN + scoping readbacks)
//  3. hgatp.PPN = all ones with MODE=Sv32x4 → Successful
//  4. Walking ones on hgatp.PPN bits [21:2] with MODE=Sv32x4 → Successful
//
// Total Expected Faults :: 0
// --------------------------------------------------------------------------------------------------------------------------------

##### START_TEST_CONFIG #####
# REQUIRED_EXTENSIONS: [I, H, Sv32]
# MARCH: rv32ih_zicsr_zifencei
##### END_TEST_CONFIG #####

#define TEST_FILE "svh_csr_hgatp_fields_HSmode.S"
#define SIGUPD_COUNT 24
#define TRAP_SIGUPD_COUNT 16
#define RVTEST_HYPERVISOR

#include "riscv_arch_test.h"

RVTEST_BEGIN

main:
  // Partner stage off (sheet rule for hgatp CSR tests)
  csrw vsatp, x0                                // vsatp Bare (no VS walk; isolate hgatp field bins)
  hfence.vvma                                   // flush VS TLB after vsatp clear
  RVTEST_GOTO_LOWER_MODE HSmode                 // enter HS (hgatp writable from HS)

//---------------------------------------------------------------------------------------------------------------------------------
// Test case 1: Set hgatp.MODE=Sv32x4, PPN=0 | Expected: Successful
//---------------------------------------------------------------------------------------------------------------------------------
  // cp_hgatp_mode_field bin: MODE=Sv32x4, PPN=0
  LI(t0, (HGATP_MODE_SV32X4 << 31))             // G-stage Sv32x4 MODE, PPN clear
  csrw hgatp, t0                                // write hgatp (G-stage CSR)
  test1_mode:
  RVTEST_SIGUPD_CSR_READ(hgatp, a4, test1_mode, test1_mode_str)  // signature: read hgatp after MODE=Sv32x4 write

//---------------------------------------------------------------------------------------------------------------------------------
// Test case 2: hgatp.VMID = all ones | Expected: Successful
//---------------------------------------------------------------------------------------------------------------------------------
  // cp_hgatp_vmidlen_detect + cp_hgatp_vmid_scoping bins: VMID all-1s (two readbacks)
  LI(t0, (HGATP_MODE_SV32X4 << 31) | HGATP32_VMID)  // MODE + VMID all-1s
  csrw hgatp, t0                                // write hgatp (G-stage CSR)
  test2_vmid1:
  RVTEST_SIGUPD_CSR_READ(hgatp, a4, test2_vmid1, test2_vmid1_str)  // signature: VMIDLEN detect readback
  test2_vmid2:
  RVTEST_SIGUPD_CSR_READ(hgatp, a4, test2_vmid2, test2_vmid2_str)  // signature: VMID scoping readback

//---------------------------------------------------------------------------------------------------------------------------------
// Test case 3: hgatp.PPN = all ones | Expected: Successful
//---------------------------------------------------------------------------------------------------------------------------------
  // cp_hgatp_ppn_field bin: PPN all-ones (22 bits on RV32)
  LI(t0, (HGATP_MODE_SV32X4 << 31) | 0x3FFFFF)  // MODE + PPN all-1s
  csrw hgatp, t0                                // write hgatp (G-stage CSR)
  test3_ppn_ones:
  RVTEST_SIGUPD_CSR_READ(hgatp, a4, test3_ppn_ones, test3_ppn_ones_str)  // signature: read hgatp after PPN all-ones write

//---------------------------------------------------------------------------------------------------------------------------------
// Test case 4: Walking ones on hgatp.PPN bits [21:2] | Expected: Successful
//---------------------------------------------------------------------------------------------------------------------------------
  // cp_hgatp_ppn_field bin: walking-1 on PPN[21:2] (PPN[1:0] WARL-0 for Sv*x4 root align)
  // PPN walking-1 from bit 2..21 (bits 1:0 often forced 0)
  LI(t3, 2)                                     // start PPN walk at bit 2 (bits 1:0 often WARL-0)
ppn_walk:
  LI(t0, (HGATP_MODE_SV32X4 << 31))             // t0 = MODE Sv32x4 only
  LI(t1, 1)                                     // t1 = 1 (will shift into one bit)
  sll t1, t1, t3                                // shift 1 into bit position t3
  or  t0, t0, t1                                // merge MODE with PPN/bit
  csrw hgatp, t0                                // write hgatp (G-stage CSR)
  test4_ppn_walk:
  RVTEST_SIGUPD_CSR_READ(hgatp, a4, test4_ppn_walk, test4_ppn_walk_str)  // signature: read hgatp after each PPN walk step
  addi t3, t3, 1                                // next bit/index
  LI(t4, 22)                                    // stop after bits 2..21 (20 iterations)
  blt t3, t4, ppn_walk                          // repeat until all PPN bits tried

  RVTEST_GOTO_MMODE                             // return to M for next case / SIGUPD

//---------------------------------------------------------------------------------------------------------------------------------
RVTEST_CODE_END
RVTEST_DATA_BEGIN
// PASS/FAIL message strings for signature compares

test1_mode_str:     .string "\"Mismatch on setting hgatp.MODE=Sv32x4 (PPN=0) in Test Case 1!\""
test2_vmid1_str:    .string "\"Mismatch on hgatp.VMID=all-ones (VMIDLEN) in Test Case 2!\""
test2_vmid2_str:    .string "\"Mismatch on hgatp.VMID scoping read in Test Case 2!\""
test3_ppn_ones_str: .string "\"Mismatch on hgatp.PPN=all-ones in Test Case 3!\""
test4_ppn_walk_str: .string "\"Mismatch on walking ones in hgatp.PPN in Test Case 4!\""

RVTEST_DATA_END
RVTEST_SIG_SETUP
