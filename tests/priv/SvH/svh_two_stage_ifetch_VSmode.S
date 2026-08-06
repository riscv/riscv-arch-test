// --------------------------------------------------------------------------------------------------------------------------------
// svh_two_stage_ifetch_VSmode.S
// Config: sail-rv32-max | VS=Sv32 + G=Sv32x4 (both ON)
// Pair:   svh_two_stage_ifetch_sv39_VSmode.S
// Coverpoints mapped (SvH_cg): two_stage_ifetch
// What this proves (one line):
//   VS instruction fetch walks GVA→GPA→SPA through both stages.
// --------------------------------------------------------------------------------------------------------------------------------
// Test cases are as follows:
// --------------------------------------------------------------------------------------------------------------------------------
//  1. VS instruction fetch through two-stage translation → Successful (a2=0x257A0011)
//
// Total Expected Faults :: 0
// --------------------------------------------------------------------------------------------------------------------------------

##### START_TEST_CONFIG #####
# REQUIRED_EXTENSIONS: [I, H, Sv32]
# MARCH: rv32ih_zicsr_zifencei
##### END_TEST_CONFIG #####

#define TEST_FILE "svh_two_stage_ifetch_VSmode.S"
#define SIGUPD_COUNT 1
#define TRAP_SIGUPD_COUNT 16
#define RVTEST_HYPERVISOR

// Mode hops (T-SBI) — return-to-M always uses RVTEST_TSBI_GOTO_MMODE (ecall a0=1;
//   handler rtn2mmode relocates EPC VA→PA). Enter:
//   • Code at PA / identity: RVTEST_TSBI_GOTO_VSMODE / _SMODE (ecall a0=4/2)
//   • Guest code VA≠PA (V_SAVE_AREA_*): RVTEST_GOTO_LOWER_MODE (mret + PA↔VA relocate)
#include "riscv_arch_test.h"

RVTEST_BEGIN

main:
  .set va_code,                 0x90000000         // GVA where VS executes this code
  .set gpa_code,                0x012000000        // GPA behind va_code (4 MiB aligned)
  .set gpa_rvtest_Vroot_pg_tbl, 0x01000A000        // GPA of VS root page table

  // ---- G-stage (hgatp Sv32x4): GPA -> PA  (walks as U-mode → U=1 on leaves) ----

  // Only code + VS-root PT maps needed — no data page; ifetch alone proves two-stage walk
  SUPERPAGE_G_PTE_SETUP(sv32x4, rvtest_code_begin, (PTE_D | PTE_A | PTE_U | PTE_X | PTE_R | PTE_V), gpa_code, LEVEL1)  // gpa_code -> PA(code); LEVEL1 = 4 MiB X leaf

  G_PTE_SETUP(sv32x4, rvtest_hlvl0_pg_tbl, (PTE_V), gpa_rvtest_Vroot_pg_tbl, LEVEL1)  // non-leaf: G VPN1 -> G L0 table
  G_PTE_SETUP(sv32x4, rvtest_Vroot_pg_tbl, (PTE_D | PTE_A | PTE_U | PTE_W | PTE_R | PTE_V), gpa_rvtest_Vroot_pg_tbl, LEVEL0)  // leaf: GPA(VS root) -> PA(VS root) R/W (PT walk)

  // ---- VS-stage (vsatp Sv32): GVA -> GPA  (X so VS may fetch; U=0) ----

  VS_PTE_SETUP(sv32, GPA, gpa_code, (PTE_D | PTE_A | PTE_X | PTE_R | PTE_V), va_code, LEVEL1)  // leaf: va_code -> gpa_code (X/R)

  csrr a0, mscratch                                // a0 = Msave_area (required by next macro)
  V_SAVE_AREA_SETUP(va_code, rvtest_code_begin, code, LEVEL1)  // framework: VS entry PC under va_code

  VSATP_SETUP(sv32, GPA)                           // vsatp = Sv32, PPN = GPA of VS root
  HGATP_SETUP(sv32x4)                              // hgatp = Sv32x4, PPN = G root
  hfence.vvma                                      // invalidate VS-stage TLB entries
  hfence.gvma                                      // invalidate G-stage TLB entries

  RVTEST_GOTO_LOWER_MODE VSmode                 // M→VSmode mret + PA↔VA relocate (guest code VA≠PA; T-SBI enter lacks relocate)

//---------------------------------------------------------------------------------------------------------------------------------
// Test case 1: VS instruction fetch through two-stage translation | Expected: Successful
//---------------------------------------------------------------------------------------------------------------------------------
  LI(a2, 0x257A0010)                               // seed; addi below proves VS fetched this insn through both stages
  addi a2, a2, 1                                   // a2 = 0x257A0011 — two_stage_ifetch bin
  nop                                              // another two-stage ifetch retire
  nop                                              // pad (trap handler may skip prior insn)
  RVTEST_TSBI_GOTO_MMODE                       // T-SBI: ecall a0=1 → M (rtn2mmode VA→PA relocate)

  test1_ifetch:
  RVTEST_SIGUPD(x2, x5, x4, a2, test1_ifetch, test1_ifetch_str)  // record case 1 ifetch result in signature

//---------------------------------------------------------------------------------------------------------------------------------
RVTEST_CODE_END
RVTEST_DATA_BEGIN

.align 12                                       // align to 4 KiB page
rvtest_hlvl0_pg_tbl:                               // G-stage level-0 PTE storage
  .zero(4096)                                   // 4 KiB page-table storage

test1_ifetch_str: .string "\"Mismatch on VS ifetch result (expect 0x257A0011) in Test Case 1!\""

RVTEST_DATA_END
RVTEST_SIG_SETUP
