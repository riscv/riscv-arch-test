// --------------------------------------------------------------------------------------------------------------------------------
// svh_g_walk_vs_pt_VSmode.S
// Config: sail-rv32-max | VS=Sv32 + G=Sv32x4 (both ON)
// Pair:   svh_g_walk_vs_pt_sv39_VSmode.S
// Coverpoints mapped (SvH_cg): cp_h_vm_gstagetrans
// What this proves (one line):
//   G-stage must translate VS page-table GPAs; denying them causes guest-page fault.
// --------------------------------------------------------------------------------------------------------------------------------
// Test cases are as follows:
// --------------------------------------------------------------------------------------------------------------------------------
//  1. G allows VS-PT GPA walk → VS lw succeeds (0x257A0041)
//  2. G denies VS L0 PT GPA → VS lw guest-page-faults (a4 stays 0)
//
// Total Expected Faults :: 1
// --------------------------------------------------------------------------------------------------------------------------------

##### START_TEST_CONFIG #####
# REQUIRED_EXTENSIONS: [I, H, Sv32]
# MARCH: rv32ih_zicsr_zifencei
##### END_TEST_CONFIG #####

#define TEST_FILE "svh_g_walk_vs_pt_VSmode.S"
#define SIGUPD_COUNT 2
#define TRAP_SIGUPD_COUNT 16
#define RVTEST_HYPERVISOR

#include "riscv_arch_test.h"

RVTEST_BEGIN

main:
  .set va_data,                 0x008001000     // GVA for VS lw
  .set va_code,                 0x90000000      // GVA for VS code
  .set gpa_data,                0x00C002000     // GPA behind va_data
  .set gpa_code,                0x012000000     // GPA behind va_code
  .set gpa_rvtest_Vroot_pg_tbl, 0x01000A000     // GPA of VS root (G must map)
  .set gpa_rvtest_vlvl0_pg_tbl, 0x01000B000     // GPA of VS L0   (G must map)

  // ---- G-stage (hgatp Sv32x4): must map VS PT GPAs or VS walk guest-faults ----
  SUPERPAGE_G_PTE_SETUP(sv32x4, rvtest_code_begin, (PTE_D | PTE_A | PTE_U | PTE_X | PTE_R | PTE_V), gpa_code, LEVEL1)  // map gpa_code -> PA(code) so VS can execute

  G_PTE_SETUP(sv32x4, rvtest_hlvl0_pg_tbl, (PTE_V), gpa_rvtest_Vroot_pg_tbl, LEVEL1)  // point G entry for VS root GPA to G L0 table
  G_PTE_SETUP(sv32x4, rvtest_Vroot_pg_tbl, (PTE_D | PTE_A | PTE_U | PTE_W | PTE_R | PTE_V), gpa_rvtest_Vroot_pg_tbl, LEVEL0)  // G maps VS root GPA → PA (PT walk read)
  G_PTE_SETUP(sv32x4, rvtest_vlvl0_pg_tbl, (PTE_D | PTE_A | PTE_U | PTE_W | PTE_R | PTE_V), gpa_rvtest_vlvl0_pg_tbl, LEVEL0)  // G maps VS L0 GPA → PA (PT walk read)

  G_PTE_SETUP(sv32x4, rvtest_hlvl0_pg_tbl, (PTE_V), gpa_data, LEVEL1)  // point G data entry to G L0 table
  G_PTE_SETUP(sv32x4, test_region, (PTE_D | PTE_A | PTE_U | PTE_W | PTE_R | PTE_V), gpa_data, LEVEL0)  // map gpa_data -> PA(test_region) for the actual load

  // ---- VS-stage (vsatp Sv32): PPN fields hold GPAs; G-stage translates PT walks ----
  VS_PTE_SETUP(sv32, GPA, gpa_code, (PTE_D | PTE_A | PTE_X | PTE_R | PTE_V), va_code, LEVEL1)  // map va_code -> gpa_code so VS can fetch code
  csrr a0, mscratch                             // read M save area pointer for the next macro
  V_SAVE_AREA_SETUP(va_code, rvtest_code_begin, code, LEVEL1)  // tell framework VS entry PC is under va_code

  VS_PTE_SETUP(sv32, GPA, gpa_rvtest_vlvl0_pg_tbl, (PTE_V), va_data, LEVEL1)  // point VS data entry to VS L0 table GPA
  VS_PTE_SETUP(sv32, GPA, gpa_data, (PTE_D | PTE_A | PTE_W | PTE_R | PTE_V), va_data, LEVEL0)  // map va_data -> gpa_data for the VS load

  VSATP_SETUP(sv32, GPA)                        // write vsatp so VS-stage translation is on
  HGATP_SETUP(sv32x4)                           // hgatp = Sv32x4, PPN = G root
  hfence.vvma                                   // flush VS TLB
  hfence.gvma                                   // flush G TLB so next access rewalks

  LI(t0, 0x257A0041)                            // known SPA pattern
  la t1, test_region                            // SPA of data page
  sw t0, 0(t1)                                  // preload known pattern at SPA before guest access

  LI(a5, va_data)                               // a5 = guest virtual address to load

//---------------------------------------------------------------------------------------------------------------------------------
// Test case 1: G allows VS-PT GPA walk | Expected: Successful
//---------------------------------------------------------------------------------------------------------------------------------
  RVTEST_GOTO_LOWER_MODE VSmode                 // enter VS mode to run the guest load
  lw   a3, 0(a5)                                // cp_h_vm_gstagetrans: VS walk hits G-mapped VS L0 PT GPA
  nop                                           // trap-skip padding if previous access faults
  RVTEST_GOTO_MMODE                             // return from VS to M-mode test code

  test1_allow:
  RVTEST_SIGUPD(x2, x5, x4, a3, test1_allow, test1_allow_str)  // record result in signature

//---------------------------------------------------------------------------------------------------------------------------------
// Test case 2: G denies VS L0 PT GPA | Expected: Expected Fault
//---------------------------------------------------------------------------------------------------------------------------------
  // Invalidate VS L0 PT GPA in G-stage (V=0) → guest-page fault on VS page-table walk
  G_PTE_SETUP(sv32x4, rvtest_vlvl0_pg_tbl, (PTE_D | PTE_A | PTE_U | PTE_W | PTE_R), gpa_rvtest_vlvl0_pg_tbl, LEVEL0)  // V=0: G denies VS L0 PT walk
  hfence.vvma                                   // flush VS TLB before retry
  hfence.gvma                                   // flush G TLB so next access rewalks

  LI(a4, 0)                                     // sentinel: stays 0 if trap fires
  RVTEST_GOTO_LOWER_MODE VSmode                 // enter VS mode to retry the load
  lw   a4, 0(a5)                                // expect guest-page fault (handler skips)
  nop                                           // trap-skip padding if previous access faults
  RVTEST_GOTO_MMODE                             // return from VS to M-mode test code

  test2_deny:
  RVTEST_SIGUPD(x2, x5, x4, a4, test2_deny, test2_deny_str)  // record result in signature

//---------------------------------------------------------------------------------------------------------------------------------
RVTEST_CODE_END
RVTEST_DATA_BEGIN

.align 12                                      // 4 KiB page align
test_region:                                  // SPA backing for gpa_data leaf
  .word 0                                     // payload word (preloaded in M)
  .word 0                                     // padding in same page
  .word 0                                     // padding in same page
  .word 0                                     // padding in same page

.align 12                                      // 4 KiB page align
rvtest_hlvl0_pg_tbl:                          // G-stage L0 PTE storage (4 KiB)
  .zero(4096)                                  // reserve 4 KiB page-table storage
.align 12                                      // 4 KiB page align
rvtest_vlvl0_pg_tbl:                          // VS-stage L0 PTE storage (4 KiB)
  .zero(4096)                                  // reserve 4 KiB page-table storage

test1_allow_str: .string "\"Mismatch on VS lw with G allowing VS-PT walk in Test Case 1!\""
test2_deny_str:  .string "\"Mismatch on VS lw with G denying VS-PT walk in Test Case 2!\""

RVTEST_DATA_END
RVTEST_SIG_SETUP
