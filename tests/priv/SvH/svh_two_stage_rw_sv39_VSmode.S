// --------------------------------------------------------------------------------------------------------------------------------
// svh_two_stage_rw_sv39_VSmode.S
// Config: sail-rv64-max | VS=Sv39 + G=Sv39x4 (both ON)
// Pair:   svh_two_stage_rw_VSmode.S
// Coverpoints mapped (SvH_cg): two_stage_write, two_stage_read
// What this proves (one line):
//   Same two-stage store/load on RV64 (Sv39 + Sv39x4).
// --------------------------------------------------------------------------------------------------------------------------------
// Test cases are as follows:
// --------------------------------------------------------------------------------------------------------------------------------
//  1. VS sw/lw through Sv39+Sv39x4 two-stage translation → Successful
//  2. M-mode SPA readback confirms VS store → Successful
//
// Total Expected Faults :: 0
// --------------------------------------------------------------------------------------------------------------------------------

##### START_TEST_CONFIG #####
# REQUIRED_EXTENSIONS: [I, H, Sv39]
# MARCH: rv64ih_zicsr_zifencei
##### END_TEST_CONFIG #####

#define TEST_FILE "svh_two_stage_rw_sv39_VSmode.S"
#define SIGUPD_COUNT 2
#define TRAP_SIGUPD_COUNT 16
#define RVTEST_HYPERVISOR

#include "riscv_arch_test.h"

RVTEST_BEGIN

main:
  .set va_data,                 0x0000000080010000 // GVA used by VS sw/lw (data)
  .set va_code,                 0x0000000090000000 // GVA where VS executes this code
  .set gpa_data,                0x0000000000C002000 // GPA behind va_data
  .set gpa_code,                0x0000000012000000 // GPA behind va_code (2 MiB aligned)
  .set gpa_rvtest_Vroot_pg_tbl, 0x000000001000A000 // GPA of VS root (LEVEL2) table
  .set gpa_rvtest_vlvl1_pg_tbl, 0x000000001000C000 // GPA of VS mid (LEVEL1) table
  .set gpa_rvtest_vlvl0_pg_tbl, 0x000000001000B000 // GPA of VS leaf (LEVEL0) table

  // ---- G-stage (hgatp Sv39x4): GPA -> PA  (L2 root / L1 mid|2MiB / L0 4KiB; U=1 on leaves) ----

  G_PTE_SETUP(sv39x4, rvtest_hlvl1_pg_tbl, (PTE_V), gpa_code, LEVEL2)  // non-leaf: shared VPN2 -> G L1 table
  // Code superpage: without this, VS ifetch at va_code guest-faults even if VS PTE is valid.
  SUPERPAGE_G_PTE_SETUP(sv39x4, rvtest_code_begin, (PTE_D | PTE_A | PTE_U | PTE_X | PTE_R | PTE_V), gpa_code, LEVEL1)  // gpa_code -> PA(code); LEVEL1 = 2 MiB leaf

  G_PTE_SETUP(sv39x4, rvtest_hlvl0_pg_tbl, (PTE_V), gpa_rvtest_Vroot_pg_tbl, LEVEL1)  // non-leaf: G VPN1 for VS root GPA -> G L0
  G_PTE_SETUP(sv39x4, rvtest_Vroot_pg_tbl, (PTE_D | PTE_A | PTE_U | PTE_W | PTE_R | PTE_V), gpa_rvtest_Vroot_pg_tbl, LEVEL0)  // leaf: GPA(VS root) -> PA(VS root) R/W
  G_PTE_SETUP(sv39x4, rvtest_vlvl1_pg_tbl, (PTE_D | PTE_A | PTE_U | PTE_W | PTE_R | PTE_V), gpa_rvtest_vlvl1_pg_tbl, LEVEL0)  // leaf: GPA(VS L1) -> PA(VS L1) R/W
  G_PTE_SETUP(sv39x4, rvtest_vlvl0_pg_tbl, (PTE_D | PTE_A | PTE_U | PTE_W | PTE_R | PTE_V), gpa_rvtest_vlvl0_pg_tbl, LEVEL0)  // leaf: GPA(VS L0) -> PA(VS L0) R/W

  G_PTE_SETUP(sv39x4, rvtest_hlvl0_pg_tbl, (PTE_V), gpa_data, LEVEL1)  // non-leaf: G VPN1 for data -> G L0 table
  G_PTE_SETUP(sv39x4, test_region, (PTE_D | PTE_A | PTE_U | PTE_W | PTE_R | PTE_V), gpa_data, LEVEL0)  // leaf: gpa_data -> PA(test_region) R/W

  // ---- VS-stage (vsatp Sv39): GVA -> GPA  (3 levels; leaf U=0 so VS R/W without SUM) ----

  VS_PTE_SETUP(sv39, GPA, gpa_rvtest_vlvl1_pg_tbl, (PTE_V), va_code, LEVEL2)  // non-leaf: va_code VPN2 -> VS L1 table GPA
  VS_PTE_SETUP(sv39, GPA, gpa_code, (PTE_D | PTE_A | PTE_X | PTE_R | PTE_V), va_code, LEVEL1)  // leaf: va_code -> gpa_code (X/R, 2 MiB)

  csrr a0, mscratch                             // a0 = Msave_area (required by next macro)
  V_SAVE_AREA_SETUP(va_code, rvtest_code_begin, code, LEVEL1)  // framework: VS entry PC under va_code (two-stage ifetch from first insn)

  VS_PTE_SETUP(sv39, GPA, gpa_rvtest_vlvl1_pg_tbl, (PTE_V), va_data, LEVEL2)  // non-leaf: va_data VPN2 -> VS L1 table GPA
  VS_PTE_SETUP(sv39, GPA, gpa_rvtest_vlvl0_pg_tbl, (PTE_V), va_data, LEVEL1)  // non-leaf: va_data VPN1 -> VS L0 table GPA
  VS_PTE_SETUP(sv39, GPA, gpa_data, (PTE_D | PTE_A | PTE_W | PTE_R | PTE_V), va_data, LEVEL0)  // leaf: va_data -> gpa_data (W/R, 4 KiB)

  VSATP_SETUP(sv39, GPA)                        // vsatp = Sv39, PPN = GPA of VS root
  HGATP_SETUP(sv39x4)                           // hgatp = Sv39x4, PPN = G root
  hfence.vvma                                   // invalidate VS-stage TLB entries
  hfence.gvma                                   // invalidate G-stage TLB entries

  // Known pattern at SPA before guest store (two_stage_write check from M later)
  LI(t0, 0xDEADBEEF)                            // poison value written to PA
  la t1, test_region                            // t1 = SPA of data page
  sw t0, 0(t1)                                  // SPA starts as 0xDEADBEEF

  LI(a5, va_data)                               // a5 = GVA pointer for store/load
  RVTEST_GOTO_LOWER_MODE VSmode                 // M -> VS (mret via framework)

//---------------------------------------------------------------------------------------------------------------------------------
// Test case 1: VS sw/lw through two-stage translation | Expected: Successful
//---------------------------------------------------------------------------------------------------------------------------------
  LI(a2, 0x257A0005)                            // value to store
  sw   a2, 0(a5)                                // two_stage_write: GVA->GPA->PA store
  nop                                           // trap-skip padding after store
  lw   a3, 0(a5)                                // two_stage_read: GVA->GPA->PA load
  nop                                           // trap-skip padding after load
  RVTEST_GOTO_MMODE                             // VS -> M via ecall to test handler

  test1_vs:
  RVTEST_SIGUPD(x2, x5, x4, a3, test1_vs, test1_vs_str)  // record case 1 VS lw result in signature

//---------------------------------------------------------------------------------------------------------------------------------
// Test case 2: M-mode SPA readback | Expected: Successful
//---------------------------------------------------------------------------------------------------------------------------------
  // M-mode: SPA must show guest store (stronger than VS lw alone)
  la t1, test_region                            // t1 = SPA again
  lw t2, 0(t1)                                  // t2 expect 0x257A0005 (not DEADBEEF)
  test2_spa:
  RVTEST_SIGUPD(x2, x5, x4, t2, test2_spa, test2_spa_str)  // record case 2 SPA readback in signature

//---------------------------------------------------------------------------------------------------------------------------------
RVTEST_CODE_END
RVTEST_DATA_BEGIN

.align 12                                       // 4 KiB page align
test_region:                                    // real PA backing gpa_data
  .word 0                                       // data word (initially 0)
  .word 0                                       // data word (initially 0)
  .word 0                                       // data word (initially 0)
  .word 0                                       // data word (initially 0)

.align 12                                       // align to 4 KiB page
rvtest_hlvl1_pg_tbl:                            // G-stage level-1 PTE storage
  .zero(4096)                                   // 4 KiB page-table storage
.align 12                                       // align to 4 KiB page
rvtest_hlvl0_pg_tbl:                            // G-stage level-0 PTE storage
  .zero(4096)                                   // 4 KiB page-table storage
.align 12                                       // align to 4 KiB page
rvtest_vlvl1_pg_tbl:                            // VS-stage level-1 PTE storage
  .zero(4096)                                   // 4 KiB page-table storage
.align 12                                       // align to 4 KiB page
rvtest_vlvl0_pg_tbl:                            // VS-stage level-0 PTE storage
  .zero(4096)                                   // 4 KiB page-table storage

test1_vs_str:  .string "\"Mismatch on VS lw after two-stage sw in Test Case 1!\""
test2_spa_str: .string "\"Mismatch on SPA readback after two-stage store in Test Case 2!\""

RVTEST_DATA_END
RVTEST_SIG_SETUP
