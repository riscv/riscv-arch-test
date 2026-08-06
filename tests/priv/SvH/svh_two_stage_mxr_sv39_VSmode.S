// --------------------------------------------------------------------------------------------------------------------------------
// svh_two_stage_mxr_sv39_VSmode.S
// Config: sail-rv64-max | VS=Sv39 + G=Sv39x4 (both ON)
// Pair:   svh_two_stage_mxr_VSmode.S
// Coverpoints mapped (SvH_cg): cp_two_stage_mxr
// What this proves (one line):
//   Same two-stage MXR X-only load check on RV64.
// --------------------------------------------------------------------------------------------------------------------------------
// Test cases are as follows:
// --------------------------------------------------------------------------------------------------------------------------------
//  1. VS lw of X-only page with MXR=0 → Expected Fault (a3 stays 0)
//  2. VS lw of X-only page with MXR=1 → Successful (0x257A0101)
//
// Total Expected Faults :: 1
// --------------------------------------------------------------------------------------------------------------------------------

##### START_TEST_CONFIG #####
# REQUIRED_EXTENSIONS: [I, H, Sv39]
# MARCH: rv64ih_zicsr_zifencei
##### END_TEST_CONFIG #####

#define TEST_FILE "svh_two_stage_mxr_sv39_VSmode.S"
#define SIGUPD_COUNT 2
#define TRAP_SIGUPD_COUNT 16
#define RVTEST_HYPERVISOR

// Mode hops (T-SBI) — return-to-M always uses RVTEST_TSBI_GOTO_MMODE (ecall a0=1;
//   handler rtn2mmode relocates EPC VA→PA). Enter:
//   • Code at PA / identity: RVTEST_TSBI_GOTO_VSMODE / _SMODE (ecall a0=4/2)
//   • Guest code VA≠PA (V_SAVE_AREA_*): RVTEST_GOTO_LOWER_MODE (mret + PA↔VA relocate)
#include "riscv_arch_test.h"

RVTEST_BEGIN

main:
  .set va_data,                 0x0000000080010000 // GVA for the VS load from X-only data
  .set va_code,                 0x0000000090000000 // GVA where VS executes this code
  .set gpa_data,                0x0000000000C002000 // GPA behind va_data
  .set gpa_code,                0x0000000012000000 // GPA behind va_code (2 MiB aligned)
  .set gpa_rvtest_Vroot_pg_tbl, 0x000000001000A000 // GPA of VS root (LEVEL2) table
  .set gpa_rvtest_vlvl1_pg_tbl, 0x000000001000C000 // GPA of VS mid (LEVEL1) table
  .set gpa_rvtest_vlvl0_pg_tbl, 0x000000001000B000 // GPA of VS leaf (LEVEL0) table

  // ---- G-stage (hgatp Sv39x4): GPA -> PA; U=1 on leaves (G walk is U-mode) ----
  G_PTE_SETUP(sv39x4, rvtest_hlvl1_pg_tbl, (PTE_V), gpa_code, LEVEL2)  // non-leaf: shared VPN2 -> G L1 table
  SUPERPAGE_G_PTE_SETUP(sv39x4, rvtest_code_begin, (PTE_D | PTE_A | PTE_U | PTE_X | PTE_R | PTE_V), gpa_code, LEVEL1)  // gpa_code -> PA(code) so VS can execute

  G_PTE_SETUP(sv39x4, rvtest_hlvl0_pg_tbl, (PTE_V), gpa_rvtest_Vroot_pg_tbl, LEVEL1)  // point G entry for VS root GPA to G L0 table
  G_PTE_SETUP(sv39x4, rvtest_Vroot_pg_tbl, (PTE_D | PTE_A | PTE_U | PTE_W | PTE_R | PTE_V), gpa_rvtest_Vroot_pg_tbl, LEVEL0)  // map GPA(VS root) -> PA(VS root) for page-table walks
  G_PTE_SETUP(sv39x4, rvtest_vlvl1_pg_tbl, (PTE_D | PTE_A | PTE_U | PTE_W | PTE_R | PTE_V), gpa_rvtest_vlvl1_pg_tbl, LEVEL0)  // map GPA(VS L1) -> PA(VS L1) for page-table walks
  G_PTE_SETUP(sv39x4, rvtest_vlvl0_pg_tbl, (PTE_D | PTE_A | PTE_U | PTE_W | PTE_R | PTE_V), gpa_rvtest_vlvl0_pg_tbl, LEVEL0)  // map GPA(VS L0) -> PA(VS L0) for page-table walks

  // G-stage data leaf: X-only (R=0,X=1), U=1 — load without MXR must fault
  G_PTE_SETUP(sv39x4, rvtest_hlvl0_pg_tbl, (PTE_V), gpa_data, LEVEL1)  // point G-stage data entry to G L0 table
  G_PTE_SETUP(sv39x4, test_region, (PTE_D | PTE_A | PTE_U | PTE_X | PTE_V), gpa_data, LEVEL0)  // map gpa_data -> PA(test_region) as execute-only

  // ---- VS-stage (vsatp Sv39): GVA -> GPA; 3-level X-only data leaf ----
  VS_PTE_SETUP(sv39, GPA, gpa_rvtest_vlvl1_pg_tbl, (PTE_V), va_code, LEVEL2)  // point VS code VPN2 to VS L1 table GPA
  VS_PTE_SETUP(sv39, GPA, gpa_code, (PTE_D | PTE_A | PTE_X | PTE_R | PTE_V), va_code, LEVEL1)  // map va_code -> gpa_code so VS can fetch code
  csrr a0, mscratch                             // read M save area pointer for the next macro
  V_SAVE_AREA_SETUP(va_code, rvtest_code_begin, code, LEVEL1)  // tell framework VS entry PC is under va_code

  // VS leaf: execute-only (R=0, X=1)
  VS_PTE_SETUP(sv39, GPA, gpa_rvtest_vlvl1_pg_tbl, (PTE_V), va_data, LEVEL2)  // point VS data VPN2 to VS L1 table GPA
  VS_PTE_SETUP(sv39, GPA, gpa_rvtest_vlvl0_pg_tbl, (PTE_V), va_data, LEVEL1)  // point VS data VPN1 to VS L0 table GPA
  VS_PTE_SETUP(sv39, GPA, gpa_data, (PTE_D | PTE_A | PTE_X | PTE_V), va_data, LEVEL0)  // map va_data -> gpa_data as execute-only

  VSATP_SETUP(sv39, GPA)                        // write vsatp so VS-stage translation is on
  HGATP_SETUP(sv39x4)                           // write hgatp so G-stage translation is on
  hfence.vvma                                   // clear stale VS-stage translations
  hfence.gvma                                   // clear stale G-stage translations

  LI(t0, 0x257A0101)                            // expected data value for successful MXR=1 load
  la t1, test_region                            // t1 = real PA backing gpa_data
  sw t0, 0(t1)                                  // store the expected value in real memory

  LI(a5, va_data)                               // a5 = guest virtual address to load

//---------------------------------------------------------------------------------------------------------------------------------
// Test case 1: MXR=0 load of X-only page | Expected: Expected Fault
//---------------------------------------------------------------------------------------------------------------------------------
  // MXR=0 on both HS and VS: X-only leaf rejects load through both stages
  LI(t0, SSTATUS_MXR)                           // t0 = bit mask for MXR
  csrc sstatus, t0                              // clear HS MXR setting
  csrc vsstatus, t0                             // clear VS MXR setting
  LI(a3, 0)                                     // a3 stays 0 if the load faults and is skipped
  RVTEST_GOTO_LOWER_MODE VSmode                 // M→VSmode mret + PA↔VA relocate (guest code VA≠PA; T-SBI enter lacks relocate)
  lw   a3, 0(a5)                                // expect fault -> skipped
  nop                                           // trap-skip padding after load
  RVTEST_TSBI_GOTO_MMODE                       // T-SBI: ecall a0=1 → M (rtn2mmode VA→PA relocate)

  test1_mxr0:
  RVTEST_SIGUPD(x2, x5, x4, a3, test1_mxr0, test1_mxr0_str)  // record case 1 fault sentinel in signature

//---------------------------------------------------------------------------------------------------------------------------------
// Test case 2: MXR=1 load of X-only page | Expected: Successful
//---------------------------------------------------------------------------------------------------------------------------------
  // MXR=1: VS may load from X-only pages; hfence.vvma after status change
  LI(t0, SSTATUS_MXR)                           // t0 = bit mask for MXR
  csrs sstatus, t0                              // set HS MXR setting
  csrs vsstatus, t0                             // set VS MXR setting
  hfence.vvma                                   // status change may affect TLB perm cache; flush VS TLB
  LI(a4, 0)                                     // a4 should receive the real memory value
  RVTEST_GOTO_LOWER_MODE VSmode                 // M→VSmode mret + PA↔VA relocate (guest code VA≠PA; T-SBI enter lacks relocate)
  lw   a4, 0(a5)                                // expect 0x257A0101
  nop                                           // trap-skip padding after load
  RVTEST_TSBI_GOTO_MMODE                       // T-SBI: ecall a0=1 → M (rtn2mmode VA→PA relocate)

  test2_mxr1:
  RVTEST_SIGUPD(x2, x5, x4, a4, test2_mxr1, test2_mxr1_str)  // record case 2 lw result in signature

//---------------------------------------------------------------------------------------------------------------------------------
RVTEST_CODE_END
RVTEST_DATA_BEGIN

.align 12                                      // 4 KiB page align
test_region:                                   // real PA backing the X-only guest data page
  .word 0                                      // data slot used by the load
  .word 0                                      // padding in the same page
  .word 0                                      // padding in the same page
  .word 0                                      // padding in the same page
.align 12                                       // align to 4 KiB page
rvtest_hlvl1_pg_tbl:                           // G-stage level-1 PTE storage
  .zero(4096)                                  // reserve one page for G L1 table
.align 12                                       // align to 4 KiB page
rvtest_hlvl0_pg_tbl:                           // G-stage level-0 PTE storage
  .zero(4096)                                  // reserve one page for G L0 table
.align 12                                       // align to 4 KiB page
rvtest_vlvl1_pg_tbl:                           // VS-stage level-1 PTE storage
  .zero(4096)                                  // reserve one page for VS L1 table
.align 12                                       // align to 4 KiB page
rvtest_vlvl0_pg_tbl:                           // VS-stage level-0 PTE storage
  .zero(4096)                                  // reserve one page for VS L0 table

test1_mxr0_str: .string "\"Mismatch on MXR=0 X-only load (expect fault) in Test Case 1!\""
test2_mxr1_str: .string "\"Mismatch on MXR=1 X-only load in Test Case 2!\""

RVTEST_DATA_END
RVTEST_SIG_SETUP
