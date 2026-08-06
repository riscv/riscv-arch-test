// --------------------------------------------------------------------------------------------------------------------------------
// svh_vs_pte_attr_RV64_VSmode.S
// Config: sail-rv64-max | VS=Sv39 ON, hgatp=Bare
// Pair:   svh_vs_pte_attr_VSmode.S
// Coverpoints mapped (SvH_cg): cp_vsatp_pte_rsw, cp_vsatp_reserved_fields, cp_vsatp_svpbmt
// What this proves (one line):
//   VS Sv39 PTE RSW succeeds; reserved/PBMT bits fault or pass per Sail (see cases 3–4).
// --------------------------------------------------------------------------------------------------------------------------------
// Test cases are as follows:
// --------------------------------------------------------------------------------------------------------------------------------
//  1. RSW=00 leaf R/W: VS lw → Successful (0x257A0301)
//  2. RSW=11 (PTE_SOFT): VS lw → Successful (0x257A0302)
//  3. PTE[60:54]|PTE_RSVD on otherwise-valid R/W leaf: VS lw → Expected Fault if Sail
//     checks reserved bits (a3 stays 0); otherwise dump whatever Sail returns
//  4. PTE_PBMT on leaf (menvcfg.PBMTE likely 0): VS lw → Expected Fault (a4 stays 0) if
//     Sail enforces PBMT without extension; otherwise dump result
//
// Total Expected Faults :: 1–2 (Sail-dependent for cases 3–4)
// --------------------------------------------------------------------------------------------------------------------------------

##### START_TEST_CONFIG #####
# REQUIRED_EXTENSIONS: [I, H, Sv39]
# MARCH: rv64ih_zicsr_zifencei
##### END_TEST_CONFIG #####

#define TEST_FILE "svh_vs_pte_attr_RV64_VSmode.S"
#define SIGUPD_COUNT 4
#define TRAP_SIGUPD_COUNT 64
#define RVTEST_HYPERVISOR

// Mode hops (T-SBI) — return-to-M always uses RVTEST_TSBI_GOTO_MMODE (ecall a0=1;
//   handler rtn2mmode relocates EPC VA→PA). Enter:
//   • Code at PA / identity: RVTEST_TSBI_GOTO_VSMODE / _SMODE (ecall a0=4/2)
//   • Guest code VA≠PA (V_SAVE_AREA_*): RVTEST_GOTO_LOWER_MODE (mret + PA↔VA relocate)
#include "riscv_arch_test.h"

RVTEST_BEGIN

main:
  .set va_rsw0,    0x0000000080010000           // GVA for RSW=00 R/W leaf
  .set va_rsw11,   0x0000000080020000           // GVA for RSW=11 (PTE_SOFT) leaf
  .set va_rsvd,    0x0000000080030000           // GVA for reserved-bits leaf (PTE[60:54])
  .set va_pbmt,    0x0000000080040000           // GVA for PBMT-encoded leaf
  .set va_code,    0x0000000090000000           // GVA where VS executes this code

  // ---- VS-stage (vsatp Sv39): GVA -> PA  (hgatp Bare ⇒ PTE PPN fields are real PAs) ----
  VS_PTE_SETUP(sv39, PA, rvtest_vlvl1_pg_tbl, (PTE_V), va_code, LEVEL2)  // non-leaf: va_code VPN2 -> VS L1 table PA
  SUPERPAGE_VS_PTE_SETUP(sv39, rvtest_code_begin, (PTE_D | PTE_A | PTE_X | PTE_R | PTE_V), va_code, LEVEL1)  // leaf: va_code -> PA(code); LEVEL1 = 2 MiB X/R

  csrr a0, mscratch                             // a0 = Msave_area (required by next macro)
  V_SAVE_AREA_SETUP(va_code, rvtest_code_begin, code, LEVEL1)  // framework: VS entry PC is under va_code

  // RSW=00 leaf at va_rsw0
  VS_PTE_SETUP(sv39, PA, rvtest_vlvl1_pg_tbl, (PTE_V), va_rsw0, LEVEL2)  // non-leaf: va_rsw0 VPN2 -> VS L1 table PA
  VS_PTE_SETUP(sv39, PA, rvtest_vlvl0_pg_tbl, (PTE_V), va_rsw0, LEVEL1)  // non-leaf: va_rsw0 VPN1 -> VS L0 table PA
  VS_PTE_SETUP(sv39, PA, test_region0, (PTE_D | PTE_A | PTE_W | PTE_R | PTE_V), va_rsw0, LEVEL0)  // leaf: va_rsw0 -> PA(test_region0) R/W; RSW=00

  // RSW=11 leaf at va_rsw11
  VS_PTE_SETUP(sv39, PA, rvtest_vlvl1_pg_tbl, (PTE_V), va_rsw11, LEVEL2)  // non-leaf: va_rsw11 VPN2 -> VS L1 table PA
  VS_PTE_SETUP(sv39, PA, rvtest_vlvl0_pg_tbl, (PTE_V), va_rsw11, LEVEL1)  // non-leaf: va_rsw11 VPN1 -> VS L0 table PA
  VS_PTE_SETUP(sv39, PA, test_region1, (PTE_D | PTE_A | PTE_W | PTE_R | PTE_V | PTE_SOFT), va_rsw11, LEVEL0)  // leaf: va_rsw11 -> PA(test_region1) R/W; RSW=11

  // Reserved PTE[60:54] leaf at va_rsvd (otherwise valid R/W V=1)
  VS_PTE_SETUP(sv39, PA, rvtest_vlvl1_pg_tbl, (PTE_V), va_rsvd, LEVEL2)  // non-leaf: va_rsvd VPN2 -> VS L1 table PA
  VS_PTE_SETUP(sv39, PA, rvtest_vlvl0_pg_tbl, (PTE_V), va_rsvd, LEVEL1)  // non-leaf: va_rsvd VPN1 -> VS L0 table PA
  VS_PTE_SETUP(sv39, PA, test_region2, (PTE_D | PTE_A | PTE_W | PTE_R | PTE_V | PTE_RSVD), va_rsvd, LEVEL0)  // leaf: va_rsvd -> PA(test_region2); reserved bits set

  // PBMT leaf at va_pbmt
  VS_PTE_SETUP(sv39, PA, rvtest_vlvl1_pg_tbl, (PTE_V), va_pbmt, LEVEL2)  // non-leaf: va_pbmt VPN2 -> VS L1 table PA
  VS_PTE_SETUP(sv39, PA, rvtest_vlvl0_pg_tbl, (PTE_V), va_pbmt, LEVEL1)  // non-leaf: va_pbmt VPN1 -> VS L0 table PA
  VS_PTE_SETUP(sv39, PA, test_region3, (PTE_D | PTE_A | PTE_W | PTE_R | PTE_V | PTE_PBMT), va_pbmt, LEVEL0)  // leaf: va_pbmt -> PA(test_region3); PBMT encoding

  VSATP_SETUP(sv39, PA)                         // vsatp = Sv39, PPN = PA of VS root
  csrw hgatp, x0                                // hgatp = Bare (no G-stage)
  hfence.vvma                                   // invalidate VS-stage TLB entries
  hfence.gvma                                   // invalidate G-stage TLB entries (harmless with Bare)

  // Preload each SPA with distinct payloads (M-mode, before guest loads)
  LI(t0, 0x257A0301)                            // SPA pattern for RSW=00 leaf (case 1)
  la t1, test_region0                           // t1 = SPA for RSW=00 leaf
  sw t0, 0(t1)                                  // preload case 1 read target
  LI(t0, 0x257A0302)                            // SPA pattern for RSW=11 leaf (case 2)
  la t1, test_region1                           // t1 = SPA for RSW=11 leaf
  sw t0, 0(t1)                                  // preload case 2 read target
  LI(t0, 0x257A0303)                            // SPA pattern for reserved-bits leaf (case 3)
  la t1, test_region2                           // t1 = SPA for reserved-bits leaf
  sw t0, 0(t1)                                  // preload (fault case — value must not be read)
  LI(t0, 0x257A0304)                            // SPA pattern for PBMT leaf (case 4)
  la t1, test_region3                           // t1 = SPA for PBMT leaf
  sw t0, 0(t1)                                  // preload (fault case — value must not be read)

//---------------------------------------------------------------------------------------------------------------------------------
// Test case 1: RSW=00 VS lw | Expected: Successful
//---------------------------------------------------------------------------------------------------------------------------------
  LI(a5, va_rsw0)                               // a5 = GVA of RSW=00 leaf
  RVTEST_GOTO_LOWER_MODE VSmode                 // M→VSmode mret + PA↔VA relocate (guest code VA≠PA; T-SBI enter lacks relocate)
  lw   a3, 0(a5)                                // RSW=00 must not block load; expect 0x257A0301
  nop                                           // trap-skip padding after load
  RVTEST_TSBI_GOTO_MMODE                       // T-SBI: ecall a0=1 → M (rtn2mmode VA→PA relocate)

  test1_rsw00:
  RVTEST_SIGUPD(x2, x5, x4, a3, test1_rsw00, test1_rsw00_str)  // record case 1 lw result in signature

//---------------------------------------------------------------------------------------------------------------------------------
// Test case 2: RSW=11 (PTE_SOFT) VS lw | Expected: Successful
//---------------------------------------------------------------------------------------------------------------------------------
  LI(a5, va_rsw11)                              // a5 = GVA of RSW=11 leaf
  RVTEST_GOTO_LOWER_MODE VSmode                 // M→VSmode mret + PA↔VA relocate (guest code VA≠PA; T-SBI enter lacks relocate)
  lw   a4, 0(a5)                                // RSW=11 (software bits) must not block load; expect 0x257A0302
  nop                                           // trap-skip padding after load
  RVTEST_TSBI_GOTO_MMODE                       // T-SBI: ecall a0=1 → M (rtn2mmode VA→PA relocate)

  test2_rsw11:
  RVTEST_SIGUPD(x2, x5, x4, a4, test2_rsw11, test2_rsw11_str)  // record case 2 lw result in signature

//---------------------------------------------------------------------------------------------------------------------------------
// Test case 3: Reserved PTE[60:54] VS lw | Expected: Expected Fault (Sail-dependent)
//---------------------------------------------------------------------------------------------------------------------------------
  LI(a5, va_rsvd)                               // a5 = GVA of reserved-bits leaf
  LI(a6, 0)                                     // a6 stays 0 if Sail faults on PTE_RSVD (insn skipped)
  RVTEST_GOTO_LOWER_MODE VSmode                 // M→VSmode mret + PA↔VA relocate (guest code VA≠PA; T-SBI enter lacks relocate)
  lw   a6, 0(a5)                                // reserved PTE bits → load-page-fault if enforced
  nop                                           // trap-skip padding after load
  RVTEST_TSBI_GOTO_MMODE                       // T-SBI: ecall a0=1 → M (rtn2mmode VA→PA relocate)

  test3_rsvd:
  RVTEST_SIGUPD(x2, x5, x4, a6, test3_rsvd, test3_rsvd_str)  // record case 3 fault/result in signature

//---------------------------------------------------------------------------------------------------------------------------------
// Test case 4: PTE_PBMT VS lw | Expected: Expected Fault (Sail-dependent)
//---------------------------------------------------------------------------------------------------------------------------------
  LI(a5, va_pbmt)                               // a5 = GVA of PBMT leaf
  LI(a7, 0)                                     // a7 stays 0 if Sail faults without menvcfg.PBMTE (insn skipped)
  RVTEST_GOTO_LOWER_MODE VSmode                 // M→VSmode mret + PA↔VA relocate (guest code VA≠PA; T-SBI enter lacks relocate)
  lw   a7, 0(a5)                                // PBMT without extension → load-page-fault if enforced
  nop                                           // trap-skip padding after load
  RVTEST_TSBI_GOTO_MMODE                       // T-SBI: ecall a0=1 → M (rtn2mmode VA→PA relocate)

  test4_pbmt:
  RVTEST_SIGUPD(x2, x5, x4, a7, test4_pbmt, test4_pbmt_str)  // record case 4 fault/result in signature

//---------------------------------------------------------------------------------------------------------------------------------
RVTEST_CODE_END
RVTEST_DATA_BEGIN

.align 12                                       // 4 KiB page align
test_region0:                                   // real PA backing va_rsw0 (RSW=00)
  .word 0                                       // data word (initially 0)
  .word 0                                       // padding in same page
  .word 0                                       // padding in same page
  .word 0                                       // padding in same page
.align 12                                       // 4 KiB page align
test_region1:                                   // real PA backing va_rsw11 (RSW=11 / PTE_SOFT)
  .word 0                                       // data word (initially 0)
  .word 0                                       // padding in same page
  .word 0                                       // padding in same page
  .word 0                                       // padding in same page
.align 12                                       // 4 KiB page align
test_region2:                                   // real PA backing va_rsvd (PTE_RSVD set)
  .word 0                                       // data word (initially 0)
  .word 0                                       // padding in same page
  .word 0                                       // padding in same page
  .word 0                                       // padding in same page
.align 12                                       // 4 KiB page align
test_region3:                                   // real PA backing va_pbmt (PTE_PBMT set)
  .word 0                                       // data word (initially 0)
  .word 0                                       // padding in same page
  .word 0                                       // padding in same page
  .word 0                                       // padding in same page
.align 12                                       // align to 4 KiB page
rvtest_vlvl1_pg_tbl:                            // VS-stage level-1 PTE storage (Sv39 VPN2)
  .zero(4096)                                   // 4 KiB page-table storage
.align 12                                       // align to 4 KiB page
rvtest_vlvl0_pg_tbl:                            // VS-stage level-0 PTE storage (Sv39 VPN1)
  .zero(4096)                                   // 4 KiB page-table storage

test1_rsw00_str: .string "\"Mismatch on RSW=00 VS lw in Test Case 1!\""
test2_rsw11_str: .string "\"Mismatch on RSW=11 VS lw in Test Case 2!\""
test3_rsvd_str:  .string "\"Mismatch on reserved PTE VS lw in Test Case 3!\""
test4_pbmt_str:  .string "\"Mismatch on PBMT PTE VS lw in Test Case 4!\""

RVTEST_DATA_END
RVTEST_SIG_SETUP
