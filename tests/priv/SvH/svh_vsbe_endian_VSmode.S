// --------------------------------------------------------------------------------------------------------------------------------
// svh_vsbe_endian_VSmode.S
// Config: sail-rv32-max | VS=Sv32 ON, hgatp=Bare
// Coverpoints mapped (SvH_cg): cp_vsatp_endianess
// What this proves (one line):
//   hstatus.VSBE should flip VS endianness for guest loads/stores (Sail may hardwire VSBE=0).
// --------------------------------------------------------------------------------------------------------------------------------
// Test cases are as follows:
// --------------------------------------------------------------------------------------------------------------------------------
//  1. VSBE=0: VS lw after sw of 0xA1B2C3D4 → Successful
//  2. VSBE=0: M-mode SPA readback (LE) → Successful (0xA1B2C3D4)
//  3. VSBE=1 attempt: hstatus readback after csrs VSBE → Successful
//  4. VSBE=1 attempt: VS lw after sw → Successful
//  5. VSBE=1 attempt: M-mode SPA byte view → Successful
//
// Total Expected Faults :: 0
// --------------------------------------------------------------------------------------------------------------------------------
// Sail note (current sail-riscv):
//   legalize_hstatus() does NOT update VSBE ("We don't currently support
//   changing VSBE"). csrs hstatus,VSBE leaves the bit 0. So VSBE=1 stimulus
//   still runs LE on this model; vsbe_hstatus "set" stays ZERO until Sail
//   implements VSBE. The ELF still PASSes and exercises VSBE=0 fully.
// --------------------------------------------------------------------------------------------------------------------------------

##### START_TEST_CONFIG #####
# REQUIRED_EXTENSIONS: [I, H, Sv32]
# MARCH: rv32ih_zicsr_zifencei
##### END_TEST_CONFIG #####

#define TEST_FILE "svh_vsbe_endian_VSmode.S"
#define SIGUPD_COUNT 5
#define TRAP_SIGUPD_COUNT 16
#define RVTEST_HYPERVISOR

#include "riscv_arch_test.h"

RVTEST_BEGIN

main:
  .set va_data,                 0x008001000     // GVA for endian probe data page
  .set va_code,                 0x90000000      // GVA where VS executes this code

  // ---- VS-stage (vsatp Sv32): GVA -> PA  (hgatp Bare ⇒ PTE PPN fields are real PAs) ----
  SUPERPAGE_VS_PTE_SETUP(sv32, rvtest_code_begin, (PTE_D | PTE_A | PTE_X | PTE_R | PTE_V), va_code, LEVEL1)  // leaf: va_code -> PA(code); LEVEL1 = 4 MiB X/R

  csrr a0, mscratch                             // a0 = Msave_area (required by next macro)
  V_SAVE_AREA_SETUP(va_code, rvtest_code_begin, code, LEVEL1)  // framework: VS entry PC is under va_code

  // Data leaf XWR=111 (coverpoint vs_pte_xwr111_d = 8'b11??1111); U=0 is fine here
  VS_PTE_SETUP(sv32, PA, rvtest_vlvl0_pg_tbl, (PTE_V), va_data, LEVEL1)  // non-leaf: va_data VPN1 -> VS L0 table PA
  VS_PTE_SETUP(sv32, PA, test_region, (PTE_D | PTE_A | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL0)  // leaf: va_data -> PA(test_region) R/W/X

  VSATP_SETUP(sv32, PA)                         // vsatp = Sv32, PPN = PA of VS root
  csrw hgatp, x0                                // hgatp = Bare (no G-stage)
  hfence.vvma                                   // invalidate VS-stage TLB entries
  hfence.gvma                                   // invalidate G-stage TLB entries (harmless with Bare)

  LI(a5, va_data)                               // a5 = GVA pointer for guest stores/loads
  LI(s1, 0xA1B2C3D4)                            // known pattern — byte order reveals endianness

//---------------------------------------------------------------------------------------------------------------------------------
// Test case 1: VSBE=0 VS lw after sw | Expected: Successful
//---------------------------------------------------------------------------------------------------------------------------------
  LI(t0, HSTATUS_VSBE)                          // t0 = VSBE bit mask (hstatus[7])
  csrc hstatus, t0                              // clear VSBE → guest loads/stores are little-endian
  la t1, test_region                            // t1 = SPA (M-mode always sees LE byte order)
  sw x0, 0(t1)                                  // zero SPA before guest store (baseline)

  RVTEST_GOTO_LOWER_MODE VSmode                 // M -> VS
  sw   s1, 0(a5)                                // VS LE store of 0xA1B2C3D4 into SPA
  nop                                           // trap-skip padding after store
  RVTEST_GOTO_MMODE                             // VS -> M
  hfence.vvma                                   // re-walk for next VS load (coverpoint sampling)
  RVTEST_GOTO_LOWER_MODE VSmode                 // M -> VS again
  lw   a3, 0(a5)                                // VS LE load; architectural value expect 0xA1B2C3D4
  nop                                           // trap-skip padding after load
  RVTEST_GOTO_MMODE                             // VS -> M

  test1_vsbe0_lw:
  RVTEST_SIGUPD(x2, x5, x4, a3, test1_vsbe0_lw, test1_vsbe0_lw_str)  // record case 1 VS lw result in signature

//---------------------------------------------------------------------------------------------------------------------------------
// Test case 2: VSBE=0 M-mode SPA readback (LE) | Expected: Successful
//---------------------------------------------------------------------------------------------------------------------------------
  // M-mode: confirm bytes landed in SPA as little-endian
  la t1, test_region                            // t1 = SPA of data page
  lw t2, 0(t1)                                  // M (LE) read; expect 0xA1B2C3D4
  test2_vsbe0_spa:
  RVTEST_SIGUPD(x2, x5, x4, t2, test2_vsbe0_spa, test2_vsbe0_spa_str)  // record case 2 SPA readback in signature

//---------------------------------------------------------------------------------------------------------------------------------
// Test case 3: VSBE=1 hstatus readback | Expected: Successful
//---------------------------------------------------------------------------------------------------------------------------------
  LI(t0, HSTATUS_VSBE)                          // t0 = VSBE bit mask (hstatus[7])
  csrs hstatus, t0                              // try to set VSBE (Sail may WARL it back to 0)
  test3_vsbe1_hstatus:
  RVTEST_SIGUPD_CSR_READ(hstatus, a4, test3_vsbe1_hstatus, test3_vsbe1_hstatus_str)  // record hstatus after VSBE set attempt

//---------------------------------------------------------------------------------------------------------------------------------
// Test case 4: VSBE=1 attempt VS lw after sw | Expected: Successful
//---------------------------------------------------------------------------------------------------------------------------------
  la t1, test_region                            // t1 = SPA
  sw x0, 0(t1)                                  // clear SPA again for a clean BE/LE comparison

  RVTEST_GOTO_LOWER_MODE VSmode                 // M -> VS (VSBE may still be 0 on Sail)
  sw   s1, 0(a5)                                // VS store under current hstatus.VSBE
  nop                                           // trap-skip padding after store
  RVTEST_GOTO_MMODE                             // VS -> M
  hfence.vvma                                   // re-walk for next VS load
  RVTEST_GOTO_LOWER_MODE VSmode                 // M -> VS
  lw   a4, 0(a5)                                // VS load — same architectural value if BE not implemented
  nop                                           // trap-skip padding after load
  RVTEST_GOTO_MMODE                             // VS -> M

  test4_vsbe1_lw:
  RVTEST_SIGUPD(x2, x5, x4, a4, test4_vsbe1_lw, test4_vsbe1_lw_str)  // record case 4 VS lw result in signature

//---------------------------------------------------------------------------------------------------------------------------------
// Test case 5: VSBE=1 attempt M-mode SPA byte view | Expected: Successful
//---------------------------------------------------------------------------------------------------------------------------------
  // M-mode raw SPA view: if VSBE=1 worked, bytes would appear as 0xD4C3B2A1
  la t1, test_region                            // t1 = SPA
  lw t3, 0(t1)                                  // M LE view of stored bytes
                                                // Ideal VSBE=1: 0xD4C3B2A1; Sail today: 0xA1B2C3D4
  test5_vsbe1_spa:
  RVTEST_SIGUPD(x2, x5, x4, t3, test5_vsbe1_spa, test5_vsbe1_spa_str)  // record case 5 SPA byte view in signature

  // Leave VSBE clear for any follow-on tests in the harness
  LI(t0, HSTATUS_VSBE)                          // t0 = VSBE bit mask (hstatus[7])
  csrc hstatus, t0                              // clear VSBE

//---------------------------------------------------------------------------------------------------------------------------------
RVTEST_CODE_END
RVTEST_DATA_BEGIN

.align 12                                       // 4 KiB page align
test_region:                                    // real PA backing va_data (endian probe target)
  .word 0                                       // data word (initially 0)
  .word 0                                       // data word (initially 0)
  .word 0                                       // data word (initially 0)
  .word 0                                       // data word (initially 0)

.align 12                                       // align to 4 KiB page
rvtest_vlvl0_pg_tbl:                            // VS-stage level-0 PTE storage
  .zero(4096)                                   // 4 KiB page-table storage

test1_vsbe0_lw_str:       .string "\"Mismatch on VSBE=0 VS lw in Test Case 1!\""
test2_vsbe0_spa_str:      .string "\"Mismatch on VSBE=0 SPA LE readback in Test Case 2!\""
test3_vsbe1_hstatus_str:  .string "\"Mismatch on hstatus after VSBE set attempt in Test Case 3!\""
test4_vsbe1_lw_str:       .string "\"Mismatch on VSBE=1 attempt VS lw in Test Case 4!\""
test5_vsbe1_spa_str:      .string "\"Mismatch on VSBE=1 attempt SPA byte view in Test Case 5!\""

RVTEST_DATA_END
RVTEST_SIG_SETUP
