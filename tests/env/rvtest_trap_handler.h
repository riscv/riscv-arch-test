// rvtest_trap_handler.h
// RISC-V Architecture Test Framework — Trap Handler, T-SBI, and Helper Macros
//
// Copyright (c) 2020-2023. RISC-V International. All rights reserved.
// SPDX-License-Identifier: BSD-3-Clause
//
//************************************************************************************
//
//  FILE OVERVIEW
//  =============
//
//  This file is the core of the ACT4 (Architecture Compliance Test, version 4)
//  trap handling infrastructure. It is #included by test programs and provides:
//
//    1. REGISTER ALIASES        — T1..T6 mapped to x6..x11; DEFAULT_SIG/DATA/TEMP/LINK
//    2. ARCHITECTURE CONSTANTS  — interrupt/exception cause counts, masks, mode encodings
//    3. T-SBI DEFINITIONS       — Test Supervisor Binary Interface operation codes and macros
//    4. CSR RENAME MACROS       — XCSR_RENAME parameterizes CSR names by privilege mode
//    5. GOTO_MMODE / GOTO_SMODE — Legacy macros using x3==0 convention for mode switching
//    6. T-SBI CONVENIENCE MACROS— Test-facing macros for the a0-based SBI calling convention
//    7. GOTO_LOWER_MODE         — Boot-time macro to descend from M-mode to a lower mode
//    8. DEFAULT INTERRUPT MACROS— Stubs for RVMODEL interrupt set/clear if not DUT-defined
//    9. RVTEST_TRAP_PROLOG      — Per-mode initialization: xSCRATCH, xTVEC, xEDELEG, xSATP
//   10. RVTEST_TRAP_HANDLER     — Per-mode trap entry, T-SBI dispatch, signature recording,
//                                  exception/interrupt handling, and restore/return
//   11. RVTEST_TRAP_EPILOG      — Per-mode cleanup: restore xTVEC, xEDELEG, xSATP, xSCRATCH
//   12. RVTEST_TRAP_SAVEAREA    — Per-mode data: trampoline save, pointers, register save areas
//
//  MEMORY LAYOUT (per privilege mode)
//  ===================================
//
//  Each privilege mode (M, S/HS, VS) gets one "save area" of size sv_area_sz bytes,
//  allocated by RVTEST_TRAP_SAVEAREA in the .data section. The save area contains:
//
//    Offset                 | Size          | Contents
//    -----------------------|---------------|--------------------------------------------
//    0                      | tramp_sz      | Saved original trampoline (if xTVEC was not writable)
//    tramp_sz + 0*8         | 8             | code_bgn_ptr   — rvtest_code_begin address
//    tramp_sz + 1*8         | 8             | code_seg_siz   — code segment size in bytes
//    tramp_sz + 2*8         | 8             | data_bgn_ptr   — rvtest_data_begin address
//    tramp_sz + 3*8         | 8             | data_seg_siz   — data segment size in bytes
//    tramp_sz + 4*8         | 8             | sig_bgn_ptr    — rvtest_sig_begin address
//    tramp_sz + 5*8         | 8             | sig_seg_siz    — signature segment size in bytes
//    tramp_sz + 6*8         | 8             | vmem_bgn_ptr   — virtual memory region begin
//    tramp_sz + 7*8         | 8             | vmem_seg_siz   — virtual memory region size
//    tramp_sz + 8*8         | 8             | trap_sig_ptr   — current trap signature write pointer
//    tramp_sz + 9*8         | 8             | xsatp_sv       — saved xSATP value
//    tramp_sz + 10*8        | 8             | sved_misa/hgatp/mpp — shared slot, mode-dependent use
//    tramp_sz + 11*8        | 8             | tentry_sv      — common handler entry point address
//    tramp_sz + 12*8        | 8             | xedeleg_sv     — saved xEDELEG value
//    tramp_sz + 13*8        | 8             | xtvec_new      — trampoline address currently in xTVEC
//    tramp_sz + 14*8        | 8             | xtvec_save     — original xTVEC value before prolog
//    tramp_sz + 15*8        | 8             | xscratch_save  — original xSCRATCH value before prolog
//    tramp_sz + 16*8        | 8*REGWIDTH    | trapreg_sv     — T1..T6, sp, spare (handler temp regs)
//    tramp_sz + 24*8        | 8*REGWIDTH    | rvmodel_sv     — RVMODEL macro scratch + T-SBI CSR scratch
//
//  xSCRATCH always points to the top of the current mode's save area (Xtramptbl_sv).
//  On trap entry, sp is swapped with xSCRATCH so sp points to the save area.
//
//  TRAP ENTRY CONTROL FLOW
//  ========================
//
//    1. Hardware vectors to xTVEC target (trampoline or relocated copy)
//    2. Trampoline: spreader jumps (one per vectored cause) -> per-cause stub
//    3. Per-cause stub: swap sp↔xSCRATCH, save T6, jal T6 to common_Xhandler
//    4. common_Xhandler: save T5, restore xSCRATCH, load tentry_addr, jr
//    5. common_Xentry: save T4..T1, read xcause into T5
//    6. Ecall detection -> T-SBI dispatch (if ecall and SBI call) OR normal trap sig
//    7. Normal path: record trap signature (vect+mode, cause, epc/ip, tval/intID)
//    8. Exception: relocate xEPC, bump past trapping instruction
//    9. Interrupt: clear interrupt source via dispatch table
//   10. resto_Xrtn: restore T1..T6 and sp, xret to resume execution
//
//  T-SBI (TEST SUPERVISOR BINARY INTERFACE)
//  =========================================
//
//  The T-SBI enables S-mode and U-mode tests to request services from the
//  execution environment without assuming a conforming M-mode. It is a
//  lightweight alternative to the ratified SBI (OpenSBI), designed for:
//    - Minimal code footprint (no ~1MB firmware binary)
//    - RV32E compatibility (doesn't use a6/a7)
//    - Non-conforming M-mode support (via RVMODEL overrides)
//
//  Calling convention:
//    - Invoke with `ecall`
//    - a0 = operation code (see TSBI_* constants below)
//    - a1 = optional argument (e.g., CSR rs1 value)
//    - Result returned in a0
//    - x3 must be non-zero (x3==0 is reserved for legacy GOTO_MMODE)
//
//  Operations:
//    TSBI_GOTO_MMODE  (a0=1)          — Switch caller to M-mode
//    TSBI_GOTO_SMODE  (a0=2)          — Switch caller to S/HS-mode
//    TSBI_GOTO_UMODE  (a0=3)          — Switch caller to U-mode
//    TSBI_GOTO_VSMODE (a0=4)          — Switch caller to VS-mode (H required)
//    TSBI_GOTO_VUMODE (a0=5)          — Switch caller to VU-mode (H required)
//    TSBI_ECALL_TEST  (a0=0x73)       — Test ecall path; returns xEPC in a0
//    CSR_ACCESS       (a0=CSR opcode) — Execute CSR instruction; rd must be a0
//    Any other value                  — Returns -1 in a0 (TSBI_RESERVED_RET)
//
//  Dispatch hierarchy:
//    M-mode handler:  handles all operations directly
//    S-mode handler:  handles ECALL_TEST, GOTO_S/U, S-mode CSR_ACCESS locally;
//                     forwards GOTO_M/VS/VU and M-mode CSR_ACCESS to M-mode via ecall
//
//  BACKWARD COMPATIBILITY
//  =======================
//
//  The legacy x3==0 convention (RVTEST_GOTO_MMODE, RVTEST_GOTO_SMODE) is fully
//  preserved. The T-SBI dispatch only activates when x3 != 0 and a0 contains a
//  recognized operation code. Tests using the old macros continue to work unchanged.
//
//************************************************************************************

//****WARNING**** Don't put C-style macros (#define xxx) inside assembly macros;
//               C preprocessor directives are evaluated before the assembler runs.

//==============================================================================
// SECTION 1: REGISTER ALIASES
//
// The ACT4 framework uses a fixed set of register aliases for:
//   - Signature management:  DEFAULT_SIG_REG (x2) holds the signature pointer
//   - Data pointer:          DEFAULT_DATA_REG (x3) holds the test data pointer
//   - Temporaries:           DEFAULT_TEMP_REG (x4), DEFAULT_LINK_REG (x5)
//   - Handler temporaries:   T1..T6 (x6..x11) — used exclusively by trap handler
//
// IMPORTANT: T5 maps to x10 (a0) and T6 maps to x11 (a1). This means:
//   - Inside the handler, a0/a1 are used as T5/T6 (handler temporaries)
//   - BEFORE handler entry and AFTER handler exit, a0/a1 are the caller's values
//   - The T-SBI dispatch reads a0/a1 BEFORE they are overwritten by handler logic
//     (the dispatch occurs after T5 is loaded with xcause but a0's value is the
//      caller's a0, not T5, because csrr T5,xcause reads INTO T5=x10=a0)
//
// Wait — this needs clarification. T5 IS x10 IS a0. When the handler does
// "csrr T5, CSR_XCAUSE", it overwrites a0 with xcause. So by the time we
// reach the T-SBI dispatch, a0 has been destroyed.
//
// RESOLUTION: The T-SBI dispatch checks xcause (now in T5/a0) to detect ecalls,
// then needs the ORIGINAL a0 value. But a0 WAS the caller's SBI opcode... and
// it's been overwritten by xcause. This means we need to read the caller's a0
// from somewhere else. The caller's a0 is NOT saved by the handler — it's still
// in x10 at trap entry, but gets overwritten by csrr T5(=x10), CSR_XCAUSE.
//
// ACTUAL SITUATION IN THE ORIGINAL CODE: The original handler's ecall check
// uses x3 (DEFAULT_DATA_REG), not a0. x3 is NOT one of T1..T6, so it survives
// the handler's register saves. The T-SBI dispatch also uses a0... but wait:
//
// Let me re-examine. T5 = x10 = a0. When common_Xentry does:
//   csrr T5, CSR_XCAUSE     // This writes xcause into x10, destroying caller's a0
//
// So the caller's a0 IS lost. But the original code checks x3, not a0.
// For T-SBI, we need the caller's a0. We must save it before the csrr.
//
// CORRECTION: Looking at the handler flow more carefully:
//   1. trap_Xhandler stub: csrrw sp, xSCRATCH, sp (swap sp with save area ptr)
//   2. SREG T6, trap_sv_off+6*REGWIDTH(sp)         (save T6=x11=a1)
//   3. jal T6, common_Xhandler                     (T6 now has vector addr, jal link)
//   4. common_Xhandler: SREG T5, trap_sv_off+5*REGWIDTH(sp) (save T5=x10=a0 !!!)
//   5. csrrw T5, xSCRATCH, sp                      (T5 gets old xSCRATCH, sp restored? No...)
//   6. SREG T5, trap_sv_off+7*REGWIDTH(sp)          (save old sp)
//   7. LREG T5, tentry_addr_off(sp)                 (T5 = common entry point)
//   8. jr T5                                        (jump to common_Xentry)
//   9. common_Xentry: save T4, T3, T2, T1
//  10. csrr T5, CSR_XCAUSE                          (T5 = xcause, overwrites x10)
//
// So at step 4, the caller's a0 (=T5=x10) IS saved to trap_sv_off+5*REGWIDTH(sp).
// Then at step 10, T5 is overwritten with xcause.
// The ORIGINAL caller's a0 is at trap_sv_off+5*REGWIDTH(sp) in the save area!
//
// For T-SBI dispatch, we can recover the caller's a0 by loading it back:
//   LREG T3, trap_sv_off+5*REGWIDTH(sp)  // T3 = caller's original a0
//
// Similarly, the caller's a1 (=T6=x11) is saved at trap_sv_off+6*REGWIDTH(sp).
//
// This is critical for the T-SBI implementation. The dispatch code must load
// the caller's a0 from the save area, not read it directly from the a0 register.
//==============================================================================

#define DEFAULT_SIG_REG  x2                      // signature pointer register
#define DEFAULT_DATA_REG x3                      // test data pointer register; also used as ecall flag (x3==0 means GOTO_MMODE)
#define DEFAULT_TEMP_REG x4                      // general temporary for test macros
#define DEFAULT_LINK_REG x5                      // link register for test macros (jal return address)

#ifndef T1
  #define T1      x6                             // handler temporary 1
#endif
#ifndef T2
  #define T2      x7                             // handler temporary 2
#endif
#ifndef T3
  #define T3      x8                             // handler temporary 3
#endif
#ifndef T4
  #define T4      x9                             // handler temporary 4
#endif
#ifndef T5
  #define T5      x10                            // handler temporary 5 (NOTE: same as a0!)
#endif
#ifndef T6
  #define T6      x11                            // handler temporary 6 (NOTE: same as a1!)
#endif

//==============================================================================
// SECTION 2: MTVEC ALIGNMENT
//
// MTVEC_ALIGN controls the alignment of the trampoline table. The RISC-V spec
// requires the vectored mode base address to be aligned to at least 4 bytes
// times the number of supported interrupt causes. Most implementations require
// 64-byte (2^6) alignment to fit on a cache line boundary.
//
// DUTs can override this via RVMODEL_MTVEC_ALIGN if their hardware requires
// a different alignment (e.g., CLIC implementations may need 2^8).
//==============================================================================

#ifndef RVMODEL_MTVEC_ALIGN
  #define MTVEC_ALIGN 6                          // default: 2^6 = 64-byte alignment
#else
  #define MTVEC_ALIGN RVMODEL_MTVEC_ALIGN        // use DUT-specified alignment
#endif

//==============================================================================
// SECTION 3: ARCHITECTURE CONSTANTS
//
// NUM_SPECD_INTCAUSES:  number of specified interrupt causes (0..23)
// NUM_SPECD_EXCPTCAUSES: number of specified exception causes (0..23)
// INT_CAUSE_MSK:        mask for cause bits used in interrupt dispatch (5 bits)
// EXCPT_CAUSE_MSK:      mask for cause bits used in exception dispatch (5 bits)
//
// These define the sizes of the trampoline spreader region and the
// interrupt/exception dispatch tables in the handler.
//==============================================================================

#ifndef   NUM_SPECD_INTCAUSES
  #define NUM_SPECD_INTCAUSES 24                 // causes 0..23 have defined spreader entries
  #define INT_CAUSE_MSK ((1<<5)-1)               // 5-bit mask to extract cause index
#endif

#ifndef   NUM_SPECD_EXCPTCAUSES
  #define NUM_SPECD_EXCPTCAUSES 24               // causes 0..23 have defined dispatch entries
  #define EXCPT_CAUSE_MSK ((1<<5)-1)             // 5-bit mask to extract cause index
#endif

//==============================================================================
// SECTION 4: T-SBI (TEST SUPERVISOR BINARY INTERFACE) CONSTANTS
//
// These #define constants specify the operation codes passed in a0 when making
// T-SBI calls via ecall. The handler checks a0 against these values to dispatch
// the appropriate service routine.
//
// Design rationale for the operation code values:
//   - GOTO_xMODE uses small integers (1-5) for easy range checking
//   - ECALL_TEST uses the ecall instruction encoding (0x73) itself, which is
//     mnemonic and doesn't conflict with GOTO codes or CSR encodings
//   - CSR_ACCESS uses the actual CSR instruction encoding (opcode 0x73 with
//     funct3 != 0), making it self-describing — the handler doesn't need a
//     lookup table; it just executes the encoding directly
//   - The value 0 is NOT used because x3==0 is reserved for the legacy
//     GOTO_MMODE fast path
//
// Dispatch order in the handler:
//   1. If (a0-1) < 5  -> GOTO_xMODE      (a0 in range [1..5])
//   2. If a0 == 0x73  -> ECALL_TEST      (exact match on ecall encoding)
//   3. If a0[6:0]==0x73 && a0[14:12]!=0 -> CSR_ACCESS (SYSTEM opcode with funct3)
//   4. Otherwise       -> RESERVED        (return -1)
//==============================================================================

#define TSBI_GOTO_MMODE     0x00000001           // a0 value: switch to Machine mode
#define TSBI_GOTO_SMODE     0x00000002           // a0 value: switch to Supervisor (or HS) mode
#define TSBI_GOTO_UMODE     0x00000003           // a0 value: switch to User mode
#define TSBI_GOTO_VSMODE    0x00000004           // a0 value: switch to Virtual Supervisor mode (requires H)
#define TSBI_GOTO_VUMODE    0x00000005           // a0 value: switch to Virtual User mode (requires H)
#define TSBI_ECALL_TEST     0x00000073           // a0 value: test ecall trap path, returns xEPC in a0

// CSR_ACCESS is not a single #define — it's any value where:
//   bits[6:0]   == 0x73 (SYSTEM opcode)    AND
//   bits[14:12] != 0    (funct3 selects CSRRW/CSRRS/CSRRC/CSRRWI/CSRRSI/CSRRCI)
// The caller constructs this encoding. Example for "csrrs a0, mstatus, x0":
//   encoding = 0x30052573  (CSR=0x300, rs1=x0=0, funct3=010, rd=a0=x10)

#define TSBI_RESERVED_RET   (-1)                 // return value for unrecognized operations

//==============================================================================
// SECTION 5: FENCE INSTRUCTION CONFIGURATION
//
// RVMODEL_FENCEI: instruction used to synchronize the instruction stream after
// writing code to memory (e.g., when the trampoline is relocated, or when
// CSR_ACCESS writes a dynamic instruction to scratch memory).
//
// If the DUT supports Zifencei, this should be fence.i.
// If the DUT has a coherent I-cache (no explicit sync needed), this can be nop.
// If the DUT requires a custom mechanism, RVMODEL_FENCEI can be defined as a
// JAL to a routine in rvmodel_boot that performs the sync.
//
// CONSTRAINT: Must be a single instruction OR a JAL to keep code size constant.
//==============================================================================

#ifndef   RVMODEL_FENCEI
  #ifndef ZIFENCE
       #define RVMODEL_FENCEI nop                // no Zifencei: assume coherent I-cache
  #else
       #define RVMODEL_FENCEI fence.i            // Zifencei available: use fence.i
  #endif
#endif

#ifndef RVMODEL_CLEAN_SIG
  #define RVMODEL_CLEAN_SIG  RVMODEL_FENCEI      // signature region cleanup (same as fencei by default)
#endif

#ifndef _VA_SZ_
  #if XLEN==32
    #define _VA_SZ_ 32                           // RV32: 32-bit virtual address
  #else
    #define _VA_SZ_ 57                           // RV64: default to Sv57 (largest standard VA)
  #endif
#endif

//==============================================================================
// SECTION 6: MODE ENCODING CONSTANTS
//
// These constants encode privilege modes in various formats:
//   - *MODE_SIG: 2-bit mode identifier stored in trap signature word 0 (bits 1:0)
//   - MPP_*:     mstatus.MPP field values (bits 12:11)
//   - *_LSB:     bit positions of key mstatus/hstatus fields
//
// The trap signature word 0 packs: mode(1:0), entry_size(5:2), vector(10:6),
// xIE(11), xIP(12), xstatus(30:13). See RVTEST_TRAP_HANDLER for full encoding.
//==============================================================================

.set MMODE_SIG, 3                                // M-mode signature encoding (bits 1:0 = 11)
.set SMODE_SIG, 1                                // S-mode signature encoding (bits 1:0 = 01)
.set HMODE_SIG, 1                                // HS-mode signature encoding (same as S, bits 1:0 = 01)
.set VMODE_SIG, 2                                // VS-mode signature encoding (bits 1:0 = 10)

#define GVA_LSB    6                             // hstatus.GVA bit position (guest virtual address indicator)
#define MPP_LSB   11                             // mstatus.MPP LSB position (previous privilege mode, 2 bits)
#define MODE_LSB  (XLEN-4)                       // xSATP.MODE field LSB (top 4 bits on RV32, top 4 on RV64)
#define MPRV_LSB  17                             // mstatus.MPRV bit position (modify privilege for loads/stores)
#define MPV_LSB    7                             // mstatush.MPV bit position (previous virtualization mode)
#define MPP_SMODE (1<<MPP_LSB)                   // MPP value for S-mode (01 << 11 = 0x800)
#define MPP_HMODE (2<<MPP_LSB)                   // MPP value for reserved/HS (10 << 11 = 0x1000)
#define MPP_MMODE (3<<MPP_LSB)                   // MPP value for M-mode (11 << 11 = 0x1800)

//==============================================================================
// SECTION 7: TRAMPOLINE AND SAVE AREA SIZE CALCULATIONS
//
// The trampoline is the vectored interrupt entry point. It consists of:
//   1. VECTOR SPREADER: XLEN jump instructions (one per possible vector)
//      - First NUM_SPECD_INTCAUSES jump to per-cause handler stubs
//      - Remaining jump to rvtest_Xendtest (abort for impossible causes)
//   2. PER-CAUSE STUBS: 3 instructions each × NUM_SPECD_INTCAUSES
//      - csrrw sp, xSCRATCH, sp    (swap sp with save area pointer)
//      - SREG T6, offset(sp)       (save T6 in temp save area)
//      - jal T6, common_Xhandler   (jump to common handler, T6 = vector addr)
//   3. ENDTEST TRAMPOLINE: 9 instructions (long jump to rvtest_Xend)
//   4. COMMON HANDLER ENTRY: 5 instructions (save T5, restore xSCRATCH, jump)
//
// actual_tramp_sz = total bytes of trampoline code
// tramp_sz        = actual_tramp_sz rounded up to 8-byte alignment
// sv_area_sz      = total save area per mode (trampoline save + pointers + regs)
//==============================================================================

#define actual_tramp_sz ((XLEN + 3* NUM_SPECD_INTCAUSES + 9 + 5) * 4)  // total trampoline bytes
#define tramp_sz        ((actual_tramp_sz+4) & -8)                       // round up to dword alignment
#define ptr_sv_sz       (16*8)                                           // 16 pointer slots × 8 bytes each
#define reg_sv_sz       ( 8*REGWIDTH)                                    // 8 handler temp regs saved
#define model_sv_sz     ( 8*REGWIDTH)                                    // 8 slots for RVMODEL macro scratch
#define sv_area_sz      (tramp_sz + ptr_sv_sz + reg_sv_sz + model_sv_sz) // total save area per mode
#define int_hndlr_tblsz (XLEN*2*WDBYTSZ)                                // size of combined int+exception dispatch tables

//==============================================================================
// SECTION 8: SAVE AREA OFFSET DEFINITIONS
//
// These #define constants give byte offsets from the top of a mode's save area
// (Xtramptbl_sv, stored in xSCRATCH, loaded into sp on trap entry).
//
// The save area layout is:
//   [0 .. tramp_sz-1]           trampoline save (original code if xTVEC not writable)
//   [tramp_sz + 0*8]            code_bgn_off    — rvtest_code_begin phys addr
//   [tramp_sz + 1*8]            code_seg_siz    — code segment size
//   ...                         (see full layout in FILE OVERVIEW above)
//   [tramp_sz + 16*8]           trap_sv_off     — start of handler register save (T1..T6,sp,spare)
//   [tramp_sz + 24*8]           rvmodel_sv_off  — start of RVMODEL macro scratch area
//
// T-SBI CSR_ACCESS reuses rvmodel_sv_off for its dynamic instruction scratch.
// This is safe because RVMODEL macros (HALT, IO_WRITE) never execute inside
// the T-SBI dispatch path.
//==============================================================================

#define tramp_sv_off                         ( 0*8) // offset to trampoline save area
#define code_bgn_off                (tramp_sz+ 0*8) // offset to code begin address pointer
#define code_seg_siz                (tramp_sz+ 1*8) // offset to code segment size
#define data_bgn_off                (tramp_sz+ 2*8) // offset to data begin address pointer
#define data_seg_siz                (tramp_sz+ 3*8) // offset to data segment size
#define sig_bgn_off                 (tramp_sz+ 4*8) // offset to signature begin address pointer
#define sig_seg_siz                 (tramp_sz+ 5*8) // offset to signature segment size
#define vmem_bgn_off                (tramp_sz+ 6*8) // offset to virtual memory region begin
#define vmem_seg_siz                (tramp_sz+ 7*8) // offset to virtual memory region size
#define trapsig_ptr_off             (tramp_sz+ 8*8) // offset to current trap signature write pointer
#define xsatp_sv_off                (tramp_sz+ 9*8) // offset to saved xSATP value
#define sved_misa_off               (tramp_sz+10*8) // M-mode: saved misa (for misa.H changes)
#define sved_hgatp_off   (sv_area_sz+tramp_sz+10*8) // H-mode: saved hgatp (for hgatp.MODE changes)
#define sved_mpp_off   (2*sv_area_sz+tramp_sz+10*8) // S-mode: saved MPP (for MPRV tests)
#define tentry_addr_off             (tramp_sz+11*8) // offset to common handler entry point address
#define xedeleg_sv_off              (tramp_sz+12*8) // offset to saved xEDELEG value
#define xtvec_new_off               (tramp_sz+13*8) // offset to new xTVEC value (trampoline addr)
#define xtvec_sav_off               (tramp_sz+14*8) // offset to saved original xTVEC value
#define xscr_save_off               (tramp_sz+15*8) // offset to saved original xSCRATCH value
#define trap_sv_off                 (tramp_sz+16*8) // offset to handler register save area (8 regs)
#define rvmodel_sv_off              (tramp_sz+24*8) // offset to RVMODEL macro scratch area (8 regs)

// T-SBI CSR_ACCESS scratch: reuses the first 8 bytes of rvmodel_sv area
// for the dynamically-written CSR instruction (4B) + ret instruction (4B).
// This alias makes the purpose explicit in the CSR_ACCESS handler code.
#define tsbi_csr_scratch_off        rvmodel_sv_off  // T-SBI dynamic instruction scratch offset

//==============================================================================
// SECTION 9: VARIADIC ARGUMENT HELPERS
//
// These macros extract the Nth argument from a __VA_ARGS__ list.
// Used by RVTEST_SAVE_GPRS to accept an optional bitmask argument.
//==============================================================================

#define _ARG5(_1ST,_2ND, _3RD,_4TH,_5TH,...) _5TH  // extract 5th argument
#define _ARG4(_1ST,_2ND, _3RD,_4TH,...) _4TH        // extract 4th argument
#define _ARG3(_1ST,_2ND, _3RD, ...) _3RD             // extract 3rd argument
#define _ARG2(_1ST,_2ND, ...) _2ND                   // extract 2nd argument
#define _ARG1(_1ST,...) _1ST                          // extract 1st argument
#define NARG(...) _ARG5(__VA_OPT__(__VA_ARGS__,)4,3,2,1,0)  // count arguments (0-4)

//==============================================================================
// SECTION 10: INSTANTIATE_MODE_MACRO
//
// Helper macro that replicates a given macro for each supported privilege mode.
// Called as: INSTANTIATE_MODE_MACRO RVTEST_TRAP_HANDLER
// This expands to:
//   RVTEST_TRAP_HANDLER M       — always (M-mode always exists)
//   RVTEST_TRAP_HANDLER S       — if S_SUPPORTED
//   RVTEST_TRAP_HANDLER H       — if S_SUPPORTED && H_SUPPORTED
//   RVTEST_TRAP_HANDLER V       — if S_SUPPORTED && H_SUPPORTED
//
// Used for PROLOG, HANDLER, EPILOG, and SAVEAREA instantiation.
//==============================================================================

.macro INSTANTIATE_MODE_MACRO MACRO_NAME
  \MACRO_NAME M                                  // always instantiate M-mode version
  #ifdef S_SUPPORTED
    \MACRO_NAME S                                // instantiate S-mode version if supported
    #ifdef H_SUPPORTED
      \MACRO_NAME H                              // instantiate HS-mode version if hypervisor supported
      \MACRO_NAME V                              // instantiate VS-mode version if hypervisor supported
    #endif
  #endif
.endm

//==============================================================================
// SECTION 11: CSR RENAME MACROS
//
// XCSR_RENAME <MODE> sets assembler symbols (CSR_XSTATUS, CSR_XEPC, etc.)
// to the actual CSR names for the specified mode. This allows the handler
// code to be written once using CSR_X* names and instantiated per mode.
//
// Example: XCSR_RENAME M -> CSR_XEPC = CSR_MEPC, CSR_XCAUSE = CSR_MCAUSE, etc.
//          XCSR_RENAME S -> CSR_XEPC = CSR_SEPC, CSR_XCAUSE = CSR_SCAUSE, etc.
//
// Note: S and HS modes share the same CSR names (stvec, sepc, scause, etc.)
// because HS-mode uses the S-mode CSR space. VS-mode has its own CSRs
// (vstvec, vsepc, vscause, etc.)
//==============================================================================

.macro _XCSR_RENAME_V
  .set CSR_XSTATUS, CSR_VSSTATUS                // vsstatus — VS-mode status register
  .set CSR_XIE,     CSR_VSIE                    // vsie — VS-mode interrupt enable
  .set CSR_XIP,     CSR_VSIP                    // vsip — VS-mode interrupt pending
  .set CSR_XSATP,   CSR_VSATP                   // vsatp — VS-mode address translation
  .set CSR_XTVAL,   CSR_VSTVAL                  // vstval — VS-mode trap value
  .set CSR_XEDELEG, CSR_SEDELEG                 // sedeleg — VS delegates through S-mode
  .set CSR_XIDELEG, CSR_SIDELEG                 // sideleg — VS delegates through S-mode
  .set CSR_XENVCFG, CSR_SENVCFG                 // senvcfg — environment config (shared)
  .set CSR_XCOUNTEREN, CSR_SCOUNTEREN            // scounteren — counter access (shared)
  .set CSR_XTVEC,   CSR_VSTVEC                  // vstvec — VS-mode trap vector
  .set CSR_XSCRATCH,CSR_VSSCRATCH               // vsscratch — VS-mode scratch register
  .set CSR_XEPC,    CSR_VSEPC                   // vsepc — VS-mode exception PC
  .set CSR_XCAUSE,  CSR_VSCAUSE                 // vscause — VS-mode trap cause
#if (XLEN==32)
  .set CSR_XEDELEGH, CSR_SEDELEGH               // sedelegh — upper half of sedeleg (RV32 only)
#endif
.endm

.macro _XCSR_RENAME_S
  .set CSR_XSTATUS, CSR_SSTATUS                 // sstatus — S-mode status register
  .set CSR_XIE,     CSR_SIE                     // sie — S-mode interrupt enable
  .set CSR_XIP,     CSR_SIP                     // sip — S-mode interrupt pending
  .set CSR_XSATP,   CSR_SATP                    // satp — S-mode address translation
  .set CSR_XTVAL,   CSR_STVAL                   // stval — S-mode trap value
  .set CSR_XEDELEG, CSR_SEDELEG                 // sedeleg — S-mode exception delegation
  .set CSR_XIDELEG, CSR_SIDELEG                 // sideleg — S-mode interrupt delegation
  .set CSR_XENVCFG, CSR_SENVCFG                 // senvcfg — S-mode environment configuration
  .set CSR_XCOUNTEREN, CSR_SCOUNTEREN            // scounteren — S-mode counter access enable
  .set CSR_XTVEC,   CSR_STVEC                   // stvec — S-mode trap vector base
  .set CSR_XSCRATCH,CSR_SSCRATCH                // sscratch — S-mode scratch register
  .set CSR_XEPC,    CSR_SEPC                    // sepc — S-mode exception program counter
  .set CSR_XCAUSE,  CSR_SCAUSE                  // scause — S-mode trap cause
#if (XLEN==32)
  .set CSR_XEDELEGH, CSR_SEDELEGH               // sedelegh — upper half (RV32 only)
#endif
.endm

.macro _XCSR_RENAME_H
  .set CSR_XSTATUS, CSR_HSTATUS                 // hstatus — HS-mode hypervisor status
  .set CSR_XIE,     CSR_HIE                     // hie — HS-mode interrupt enable (hypervisor)
  .set CSR_XIP,     CSR_HIP                     // hip — HS-mode interrupt pending (hypervisor)
  .set CSR_XSATP,   CSR_HGATP                   // hgatp — HS-mode guest address translation
  .set CSR_XTVAL,   CSR_HTVAL                   // htval — HS-mode trap value (guest phys addr)
  .set CSR_XEDELEG, CSR_HEDELEG                 // hedeleg — HS-mode exception delegation
  .set CSR_XIDELEG, CSR_HIDELEG                 // hideleg — HS-mode interrupt delegation
  .set CSR_XENVCFG, CSR_HENVCFG                 // henvcfg — HS-mode environment configuration
  .set CSR_XCOUNTEREN, CSR_HCOUNTEREN            // hcounteren — HS-mode counter access enable
  .set CSR_XTVEC,   CSR_STVEC                   // stvec — shared with S-mode (HS uses S CSR space)
  .set CSR_XSCRATCH,CSR_SSCRATCH                // sscratch — shared with S-mode
  .set CSR_XEPC,    CSR_SEPC                    // sepc — shared with S-mode
  .set CSR_XCAUSE,  CSR_SCAUSE                  // scause — shared with S-mode
 #if (XLEN==32)
  .set CSR_XEDELEGH, CSR_HEDELEGH               // hedelegh — upper half (RV32 only)
 #endif
.endm

.macro _XCSR_RENAME_M
  .set CSR_XSTATUS, CSR_MSTATUS                 // mstatus — M-mode status register
  .set CSR_XIE,     CSR_MIE                     // mie — M-mode interrupt enable
  .set CSR_XIP,     CSR_MIP                     // mip — M-mode interrupt pending
  .set CSR_XSATP,   CSR_SATP                    // satp — address translation (M reads S-mode's)
  .set CSR_XTVAL,   CSR_MTVAL                   // mtval — M-mode trap value
  .set CSR_XEDELEG, CSR_MEDELEG                 // medeleg — M-mode exception delegation
  .set CSR_XIDELEG, CSR_MIDELEG                 // mideleg — M-mode interrupt delegation
  .set CSR_XENVCFG, CSR_MENVCFG                 // menvcfg — M-mode environment configuration
  .set CSR_XCOUNTEREN, CSR_MCOUNTEREN            // mcounteren — M-mode counter access enable
  .set CSR_XTVEC,   CSR_MTVEC                   // mtvec — M-mode trap vector base
  .set CSR_XSCRATCH,CSR_MSCRATCH                // mscratch — M-mode scratch register
  .set CSR_XEPC,    CSR_MEPC                    // mepc — M-mode exception program counter
  .set CSR_XCAUSE,  CSR_MCAUSE                  // mcause — M-mode trap cause
#if (XLEN==32)
  .set CSR_XEDELEGH, CSR_MEDELEGH               // medelegh — upper half (RV32 only)
#endif
.endm

//==============================================================================
// XCSR_RENAME dispatcher — selects the correct _XCSR_RENAME_x based on __MODE__
//==============================================================================

 .macro XCSR_RENAME __MODE__
  .ifc   \__MODE__ , M                          // if mode == M
       _XCSR_RENAME_M                           //   set CSR_X* to M-mode CSR names
  .endif
  .ifc   \__MODE__ , H                          // if mode == H (HS-mode)
       _XCSR_RENAME_H                           //   set CSR_X* to HS-mode CSR names
  .endif
  .ifc   \__MODE__ , S                          // if mode == S
       _XCSR_RENAME_S                           //   set CSR_X* to S-mode CSR names
  .endif
  .ifc  \__MODE__ ,  V                          // if mode == V (VS-mode)
       _XCSR_RENAME_V                           //   set CSR_X* to VS-mode CSR names
  .endif
.endm

//==============================================================================
// SECTION 12: RVTEST_SAVE_GPRS
//
// Debug-only macro that saves selected GPRs to the signature region.
// Used at test end to capture register state for debugging.
//
// Parameters:
//   _BR:  base register (loaded with target label address)
//   _LBL: label of the save area
//   ...:  optional bitmask selecting which registers to save (default: all)
//
// NOTE: This modifies the base register. Register values containing
//   addresses will NOT be relocated for virtual memory.
//==============================================================================

#define RVTEST_SAVE_GPRS(_BR, _LBL, ...)                ;\
        .option push                                    ;\
        .option norvc                                   ;\
        .set __SV_MASK__,  -1 /* default: save all */   ;\
    .if NARG(__VA_ARGS__) == 1                          ;\
        .set __SV_MASK__,  _ARG1(__VA_OPT__(__VA_ARGS__,0)) ;\
    .endif                                              ;\
    .set offset, 0                                      ;\
    LA(_BR, _LBL)                    /* load save area base address */;\
    .if (__SV_MASK__ &        (0x2)) == 0x2             ;\
    RVTEST_SIGUPD(_BR, x1)          /* save x1  (ra) if bit 1 set */;\
    .endif                                              ;\
    .if (__SV_MASK__ &        (0x4)) == 0x4             ;\
    RVTEST_SIGUPD(_BR, x2)          /* save x2  (sp) if bit 2 set */;\
    .endif                                              ;\
    .if (__SV_MASK__ &        (0x8)) == 0x8             ;\
    RVTEST_SIGUPD(_BR, x3)          /* save x3  (gp) if bit 3 set */;\
    .endif                                              ;\
    .if (__SV_MASK__ &       (0x10)) == 0x10            ;\
    RVTEST_SIGUPD(_BR, x4)          /* save x4  (tp) if bit 4 set */;\
    .endif                                              ;\
    .if (__SV_MASK__ &       (0x20)) == 0x20            ;\
    RVTEST_SIGUPD(_BR, x5)          /* save x5  (t0) if bit 5 set */;\
    .endif                                              ;\
    .if (__SV_MASK__ &       (0x40)) == 0x40            ;\
    RVTEST_SIGUPD(_BR, x6)                              ;\
    .endif                                              ;\
    .if (__SV_MASK__ &       (0x80)) == 0x80            ;\
    RVTEST_SIGUPD(_BR, x7)                              ;\
    .endif                                              ;\
    .if (__SV_MASK__ &      (0x100)) == 0x100           ;\
    RVTEST_SIGUPD(_BR, x8)                              ;\
    .endif                                              ;\
    .if (__SV_MASK__ &      (0x200)) == 0x200           ;\
    RVTEST_SIGUPD(_BR, x9)                              ;\
    .endif                                              ;\
    .if (__SV_MASK__ &      (0x400)) == 0x400           ;\
    RVTEST_SIGUPD(_BR, x10)                             ;\
    .endif                                              ;\
    .if (__SV_MASK__ &      (0x800)) == 0x800           ;\
    RVTEST_SIGUPD(_BR, x11)                             ;\
    .endif                                              ;\
    .if (__SV_MASK__ &     (0x1000)) == 0x1000          ;\
    RVTEST_SIGUPD(_BR, x12)                             ;\
    .endif                                              ;\
    .if (__SV_MASK__ &     (0x2000)) == 0x2000          ;\
    RVTEST_SIGUPD(_BR, x13)                             ;\
    .endif                                              ;\
    .if (__SV_MASK__ &     (0x4000)) == 0x4000          ;\
    RVTEST_SIGUPD(_BR, x14)                             ;\
    .endif                                              ;\
    .if (__SV_MASK__ &     (0x8000)) == 0x8000          ;\
    RVTEST_SIGUPD(_BR, x15)                             ;\
    .endif                                              ;\
#ifndef RVTEST_E                     /* x16-x31 only exist on RV32I/RV64I, not RV32E */;\
    .if (__SV_MASK__ &    (0x10000)) == 0x10000         ;\
    RVTEST_SIGUPD(_BR, x16)                             ;\
    .endif                                              ;\
    .if (__SV_MASK__ &    (0x20000)) == 0x20000         ;\
    RVTEST_SIGUPD(_BR, x17)                             ;\
    .endif                                              ;\
    .if (__SV_MASK__ &    (0x40000)) == 0x40000         ;\
    RVTEST_SIGUPD(_BR, x18)                             ;\
    .endif                                              ;\
    .if (__SV_MASK__ &    (0x80000)) == 0x80000         ;\
    RVTEST_SIGUPD(_BR, x19)                             ;\
    .endif                                              ;\
    .if (__SV_MASK__ &   (0x100000)) == 0x100000        ;\
    RVTEST_SIGUPD(_BR, x20)                             ;\
    .endif                                              ;\
    .if (__SV_MASK__ &   (0x200000)) == 0x200000        ;\
    RVTEST_SIGUPD(_BR, x21)                             ;\
    .endif                                              ;\
    .if (__SV_MASK__ &   (0x400000)) == 0x400000        ;\
    RVTEST_SIGUPD(_BR, x22)                             ;\
    .endif                                              ;\
    .if (__SV_MASK__ &   (0x800000)) == 0x800000        ;\
    RVTEST_SIGUPD(_BR, x23)                             ;\
    .endif                                              ;\
    .if (__SV_MASK__ &  (0x1000000)) == 0x1000000       ;\
    RVTEST_SIGUPD(_BR, x24)                             ;\
    .endif                                              ;\
    .if (__SV_MASK__ &  (0x2000000)) == 0x2000000       ;\
    RVTEST_SIGUPD(_BR, x25)                             ;\
    .endif                                              ;\
    .if (__SV_MASK__ &  (0x4000000)) == 0x4000000       ;\
    RVTEST_SIGUPD(_BR, x26)                             ;\
    .endif                                              ;\
    .if (__SV_MASK__ &  (0x8000000)) == 0x8000000       ;\
    RVTEST_SIGUPD(_BR, x27)                             ;\
    .endif                                              ;\
    .if (__SV_MASK__ & (0x10000000)) == 0x10000000      ;\
    RVTEST_SIGUPD(_BR, x28)                             ;\
    .endif                                              ;\
    .if (__SV_MASK__ & (0x20000000)) == 0x20000000      ;\
    RVTEST_SIGUPD(_BR, x29)                             ;\
    .endif                                              ;\
    .if (__SV_MASK__ & (0x40000000)) == 0x40000000      ;\
    RVTEST_SIGUPD(_BR, x30)                             ;\
    .endif                                              ;\
    .if (__SV_MASK__ & (0x80000000)) == 0x80000000      ;\
    RVTEST_SIGUPD(_BR, x31)                             ;\
    .endif                                              ;\
#endif                                                  ;\
    .option pop

//==============================================================================
// SECTION 13: LEGACY MODE-SWITCHING MACROS (x3==0 convention)
//
// These macros use the ORIGINAL ACT convention where x3 is set to 0 before
// an ecall to signal "return to higher privilege mode immediately."  The trap
// handler detects x3==0, skips normal trap signature recording, and instead
// relocates the return address to return at the new privilege level.
//
// RVTEST_GOTO_MMODE:
//   - Saves x3 in t0, sets x3=0, executes ecall
//   - M-mode handler detects x3==0, returns in M-mode to instruction after ecall
//   - Restores x3 from t0
//   - WARNING: fails if medeleg delegates the ecall cause (infinite loop)
//   - Tests that set medeleg[ecall_cause] must use RVTEST_GOTO_DELEGATED_MMODE
//
// RVTEST_GOTO_DELEGATED_MMODE:
//   - Same as GOTO_MMODE but uses ALT_GOTO_M_OP (default: .word 0 = illegal inst)
//   - The illegal instruction trap is NOT delegated, so it reaches M-mode
//   - M-mode handler detects x3==0 with ALT_GOTO_M_CAUSE, returns in M-mode
//
// RVTEST_GOTO_SMODE:
//   - Used from U-mode when U-mode ecalls are delegated to S-mode
//   - Saves x3, sets x3=0, ecalls
//   - S-mode handler detects x3==0, sets SPP=1, bumps sepc+4, srets to S-mode
//   - Only available when S_SUPPORTED is defined
//
// CLOBBERS: t0 (used to save/restore x3)
// CONSTRAINT: x3 must not already be 0 when used for normal ecall handling
//==============================================================================

#ifndef GOTO_M_OP
    #define GOTO_M_OP   ecall                    // default op for GOTO_MMODE: ecall
#endif

#ifndef GOTO_S_OP
    #define GOTO_S_OP   ecall                    // default op for GOTO_SMODE: ecall
#endif

#ifndef CAUSE_SPCL_GO2MMODE_OP
    #define ALT_GOTO_M_CAUSE CAUSE_ILLEGAL_INSTRUCTION  // alt cause: illegal instruction
    #define ALT_GOTO_M_OP    .word 0                     // alt op: emit illegal instruction encoding
#endif

.macro  RVTEST_GOTO_MMODE
  .option push
  .option norvc                                  // disable compressed instructions for consistent code size
  mv   t0, x3                                   // save x3 (DEFAULT_DATA_REG) in t0
  li   x3, 0                                    // set x3=0 to signal GOTO_MMODE to handler
  GOTO_M_OP                                      // ecall: traps to M-mode handler
  mv   x3, t0                                   // restore x3 from t0 (reached after handler returns in M-mode)
  .option pop
.endm

.macro  RVTEST_GOTO_DELEGATED_MMODE
  .option push
  .option norvc                                  // disable compressed instructions
  mv   t0, x3                                   // save x3 in t0
  li   x3, 0                                    // set x3=0 to signal GOTO_MMODE
  ALT_GOTO_M_OP                                  // .word 0: triggers illegal instruction (not delegated)
  mv   x3, t0                                   // restore x3 (reached after handler returns in M-mode)
  .option pop
.endm

.macro  RVTEST_GOTO_SMODE
  .option push
  .option norvc                                  // disable compressed instructions
  #ifdef  S_SUPPORTED
    mv   t0, x3                                  // save x3 in t0
    li   x3, 0                                  // set x3=0 to signal GOTO_SMODE
    GOTO_S_OP                                    // ecall: traps to S-mode handler (if U-mode ecalls delegated)
    mv   x3, t0                                 // restore x3 (reached after handler returns in S-mode)
  #endif
  .option pop
.endm

//==============================================================================
// SECTION 14: T-SBI CONVENIENCE MACROS FOR TESTS
//
// These macros provide a clean test-facing interface for the a0-based T-SBI
// calling convention. Unlike the legacy GOTO_MMODE (which uses x3==0), these
// set a0 to the operation code and ecall. The handler distinguishes these from
// legacy calls by checking x3 != 0.
//
// Usage in tests:
//   RVTEST_TSBI_GOTO_MMODE              // switch to M-mode, clobbers a0
//   RVTEST_TSBI_GOTO_UMODE              // switch to U-mode, clobbers a0
//   RVTEST_TSBI_ECALL_TEST              // test ecall path, result in a0
//   RVTEST_TSBI_CSR_ACCESS 0x30052573, zero  // read mstatus into a0
//
// CLOBBERS: a0 (operation code / return value), a1 (CSR_ACCESS argument only)
// PRESERVES: all other registers including x3
// PRECONDITION: x3 must be non-zero (it always is during normal test execution)
//==============================================================================

// Switch to M-mode via T-SBI.
// After this macro, the processor is in M-mode and a0 is undefined.
.macro RVTEST_TSBI_GOTO_MMODE
  .option push
  .option norvc                                  // ensure consistent code size
  li   a0, TSBI_GOTO_MMODE                      // a0 = 1 (GOTO_MMODE operation code)
  ecall                                          // trap to handler; handler sets MPP=M, mrets
  .option pop
.endm

// Switch to S-mode via T-SBI.
// After this macro, the processor is in S-mode and a0 is undefined.
.macro RVTEST_TSBI_GOTO_SMODE
  .option push
  .option norvc                                  // ensure consistent code size
  li   a0, TSBI_GOTO_SMODE                      // a0 = 2 (GOTO_SMODE operation code)
  ecall                                          // trap to handler; handler sets MPP=S, mrets
  .option pop
.endm

// Switch to U-mode via T-SBI.
// After this macro, the processor is in U-mode and a0 is undefined.
.macro RVTEST_TSBI_GOTO_UMODE
  .option push
  .option norvc                                  // ensure consistent code size
  li   a0, TSBI_GOTO_UMODE                      // a0 = 3 (GOTO_UMODE operation code)
  ecall                                          // trap to handler; handler sets MPP=U, mrets
  .option pop
.endm

// Test the ecall trap path via T-SBI.
// After this macro, a0 contains the address of the ecall instruction itself.
// This verifies that the trap handler correctly entered and returned.
.macro RVTEST_TSBI_ECALL_TEST
  .option push
  .option norvc                                  // ensure consistent code size
  li   a0, TSBI_ECALL_TEST                      // a0 = 0x73 (ECALL_TEST operation code)
  ecall                                          // trap to handler; handler reads xEPC into a0
  // a0 now contains the address of the ecall instruction above
  .option pop
.endm

// Access a CSR via T-SBI (read, write, or read-modify-write).
//
// Parameters:
//   encoding: the 32-bit RISC-V CSR instruction encoding to execute.
//             The rd field MUST be a0 (x10, register 10) for reads.
//             The rs1 field SHOULD be a1 (x11, register 11) for writes.
//   arg:      value to place in a1 before the ecall (default: zero).
//             This becomes the rs1 value for csrrs/csrrc/csrrw.
//
// After this macro, a0 contains the CSR read result (if rd==a0 in encoding).
//
// Example: Read mstatus (CSR 0x300) via csrrs a0, mstatus, x0
//   Encoding: imm[31:20]=0x300, rs1[19:15]=0, funct3[14:12]=010, rd[11:7]=01010, opcode=1110011
//   Binary:   0011_0000_0000_00000_010_01010_1110011 = 0x30002573
//   Usage:    RVTEST_TSBI_CSR_ACCESS 0x30002573
//
// Example: Set mstatus.TVM via csrrs x0, mstatus, a1 (a1 has bit 20 set)
//   Encoding: imm=0x300, rs1=01011(a1), funct3=010, rd=00000(x0), opcode=1110011
//   Binary:   0011_0000_0000_01011_010_00000_1110011 = 0x3005A073
//   Usage:    li t0, (1 << 20)
//             RVTEST_TSBI_CSR_ACCESS 0x3005A073, t0
.macro RVTEST_TSBI_CSR_ACCESS encoding, arg=zero
  .option push
  .option norvc                                  // ensure consistent code size
  LI(a0, \encoding)                              // a0 = CSR instruction encoding
  mv a1, \arg                                    // a1 = argument value (for rs1 of CSR instruction)
  ecall                                          // trap to handler; handler executes CSR instr dynamically
  // a0 now contains the CSR read result (if rd==a0 in the encoding)
  .option pop
.endm

#ifdef H_SUPPORTED
// Switch to VS-mode via T-SBI. Requires hypervisor extension.
// After this macro, the processor is in VS-mode and a0 is undefined.
.macro RVTEST_TSBI_GOTO_VSMODE
  .option push
  .option norvc                                  // ensure consistent code size
  li   a0, TSBI_GOTO_VSMODE                     // a0 = 4 (GOTO_VSMODE operation code)
  ecall                                          // trap to handler; handler sets MPP=S, MPV=1, mrets
  .option pop
.endm

// Switch to VU-mode via T-SBI. Requires hypervisor extension.
// After this macro, the processor is in VU-mode and a0 is undefined.
.macro RVTEST_TSBI_GOTO_VUMODE
  .option push
  .option norvc                                  // ensure consistent code size
  li   a0, TSBI_GOTO_VUMODE                     // a0 = 5 (GOTO_VUMODE operation code)
  ecall                                          // trap to handler; handler sets MPP=U, MPV=1, mrets
  .option pop
.endm
#endif // H_SUPPORTED


//==============================================================================
// SECTION 15: RVTEST_GOTO_LOWER_MODE
//
// Boot-time macro to transition from M-mode to a lower privilege mode.
// Used by RVTEST_BOOT_TO_SMODE and RVTEST_BOOT_TO_UMODE during boot sequence.
//
// Parameters:
//   LMODE: target mode constant (HSmode=0x9, VSmode=0x5, VUmode=0x4,
//          Mmode=0x3, Smode=0x1, Umode=0x0)
//
// Mechanism:
//   1. Set/clear mstatus.MPV based on whether target is virtual (VS/VU) or not
//   2. Set mstatus.MPP to the target privilege level
//   3. Calculate the return address in the target mode's address space
//      (handles PA↔VA relocation when MMU is active)
//   4. Write the return address to mepc
//   5. mret to enter the target mode at the calculated address
//
// PRECONDITION: Must be called from M-mode
// CLOBBERS: T1, T2, T4
// NOTE: This is for BOOT-TIME use only. For run-time mode switching in tests,
//       use RVTEST_TSBI_GOTO_xMODE or RVTEST_GOTO_MMODE instead.
//==============================================================================

#define HSmode  0x9                              // HS-mode target code (H=1, S=1, V=0)
#define VSmode  0x5                              // VS-mode target code (V=1, S=1)
#define VUmode  0x4                              // VU-mode target code (V=1, U=0)
#define Mmode   0x3                              // M-mode target code
#define Smode   0x1                              // S-mode target code
#define Umode   0x0                              // U-mode target code

.macro RVTEST_GOTO_LOWER_MODE LMODE
.option push
.option norvc                                    // disable compressed for consistent code size

        //---- Step 1: Set/clear mstatus.MPV (virtualization bit) ----
   .if     ((\LMODE\()==VUmode) || (\LMODE\()==VSmode))
     LI    T2, (1<<MPV_LSB)                     // load MPV bit mask
#if (XLEN==32)
     csrs  CSR_MSTATUSH, T2                     // RV32: set MPV in mstatush
#else
     slli T2, T2, 32                            // RV64: shift to mstatus upper half position
     csrs  CSR_MSTATUS,  T2                     // RV64: set MPV in mstatus
#endif
   .elseif ((\LMODE\()==HSmode))
     LI    T2, (1<<MPV_LSB)                     // load MPV bit mask
#if (XLEN==32)
     csrc  CSR_MSTATUSH, T2                     // RV32: clear MPV in mstatush (HS is not virtual)
#else
     slli   T2, T2, 32                          // RV64: shift to mstatus upper half position
     csrc   CSR_MSTATUS, T2                     // RV64: clear MPV in mstatus
#endif
   .endif                                       // S and U modes: leave MPV unchanged

        //---- Step 2: Set mstatus.MPP to target privilege level ----
    LI(    T4, MSTATUS_MPP)                      // load full MPP field mask (bits 12:11)
  .if (\LMODE\()==Mmode)
    csrs   CSR_MSTATUS, T4                       // set MPP=11 (M-mode) — set both bits
  .else
    csrc   CSR_MSTATUS, T4                       // clear MPP first (needed before setting to S or U)
    .if (   !((\LMODE\()==VUmode) || (\LMODE\()==Umode)))  // skip for U-mode (MPP=00 already)
      .if    ((\LMODE\()==HSmode) || (\LMODE\()==VSmode) || (\LMODE\()==Smode))
  #ifdef S_SUPPORTED
     LI(  T4, MPP_SMODE)                         // MPP=01 for S-mode
  #else
     LI(  T4, MPP_MMODE)                         // no S-mode: stay in M-mode (fallback)
  #endif
        csrs CSR_MSTATUS, T4                     // set MPP to S-mode (01)
      .endif
    .endif
  .endif

        //---- Step 3: Calculate return address with PA↔VA relocation ----
        csrr   T2, CSR_MSCRATCH                  // load M-mode save area base pointer
        addi   T2, T2, code_bgn_off+sv_area_sz   // point past M-mode save area to next mode's area

        // Load code_bgn_ptr from the target mode's save area
        // The offset depends on how many save areas we need to skip
  .if     ((\LMODE\() == VSmode) || (\LMODE\() == VUmode))
        LREG    T1, 2*sv_area_sz(T2)             // VS/VU: 3 areas from M (M->HS->S->VS)

  #ifdef S_SUPPORTED
    #ifdef H_SUPPORTED
      .elseif (\LMODE\() == Smode)
            LREG    T1,  1*sv_area_sz(T2)         // S-mode with H: 2 areas from M (M->HS->S)
      .elseif (\LMODE\() == HSmode || \LMODE\() == Umode)
            LREG    T1, 0*sv_area_sz(T2)          // HS/U with H: 1 area from M (M->HS)
    #else
      .elseif (\LMODE\() == Smode || \LMODE\() == Umode)
            LREG    T1,  0*sv_area_sz(T2)         // S/U without H: 1 area from M (M->S)
    #endif
  #endif

  .else
        LREG    T1, -1*sv_area_sz(T2)            // M-mode: 0 areas (M itself)
  .endif

        LREG  T4,   -1*sv_area_sz(T2)            // load M-mode code_bgn_ptr for relocation calc
        sub   T1, T1, T4                          // calc address delta between M-mode and target mode
        addi  T1, T1, 4*WDBYTSZ                  // bias by instruction count from auipc to mret+4
1:      auipc T4, 0                               // T4 = current PC (address of this instruction)
        add   T4, T4, T1                          // T4 = PC + delta = return address in target mode's VM
        csrw  CSR_MEPC, T4                        // set mepc to return address in target mode
        mret                                      // transition: enter target mode at mepc
2:   .option pop
.endm

//==============================================================================
// SECTION 16: DEFAULT INTERRUPT MACROS
//
// If the DUT does not define RVMODEL_SET/CLR_xxx_INT macros, these defaults
// are used. The default action is to jump to cleanup_epilogs, which terminates
// the test. This ensures that if an unexpected interrupt fires for an
// undefined interrupt type, the test fails cleanly rather than hanging.
//
// DUTs that support specific interrupt types must define the corresponding
// RVMODEL macros in their rvmodel_macros.h to actually set/clear the interrupt.
//==============================================================================

#define RVTEST_DFLT_INT_HNDLR      j cleanup_epilogs  // default: abort test on unexpected interrupt

// M-mode interrupt defaults
#ifndef RVMODEL_SET_MSW_INT
        #define  RVMODEL_SET_MSW_INT     RVTEST_DFLT_INT_HNDLR  // M-mode SW interrupt set: abort
#endif
#ifndef RVMODEL_CLR_MSW_INT
        #define  RVMODEL_CLR_MSW_INT     RVTEST_DFLT_INT_HNDLR  // M-mode SW interrupt clear: abort
#endif
#ifndef RVMODEL_CLR_MEXT_INT
        #define  RVMODEL_CLR_MEXT_INT    RVTEST_DFLT_INT_HNDLR  // M-mode ext interrupt clear: abort
#endif

// S-mode interrupt defaults
#ifndef RVMODEL_SET_SSW_INT
        #define  RVMODEL_SET_SSW_INT     RVTEST_DFLT_INT_HNDLR  // S-mode SW interrupt set: abort
#endif
#ifndef RVMODEL_CLR_SSW_INT
        #define  RVMODEL_CLR_SSW_INT     RVTEST_DFLT_INT_HNDLR  // S-mode SW interrupt clear: abort
#endif
#ifndef RVMODEL_CLR_STIMER_INT
        #define  RVMODEL_CLR_STIMER_INT  RVTEST_DFLT_INT_HNDLR  // S-mode timer interrupt clear: abort
#endif
#ifndef RVMODEL_CLR_SEXT_INT
        #define  RVMODEL_CLR_SEXT_INT    RVTEST_DFLT_INT_HNDLR  // S-mode ext interrupt clear: abort
#endif

// VS-mode interrupt defaults
#ifndef RVMODEL_SET_VSW_INT
        #define  RVMODEL_SET_VSW_INT     RVTEST_DFLT_INT_HNDLR  // VS-mode SW interrupt set: abort
#endif
#ifndef RVMODEL_CLR_VSW_INT
        #define  RVMODEL_CLR_VSW_INT     RVTEST_DFLT_INT_HNDLR  // VS-mode SW interrupt clear: abort
#endif
#ifndef RVMODEL_CLR_VTIMER_INT
        #define  RVMODEL_CLR_VTIMER_INT  RVTEST_DFLT_INT_HNDLR  // VS-mode timer interrupt clear: abort
#endif
#ifndef RVMODEL_CLR_VEXT_INT
        #define  RVMODEL_CLR_VEXT_INT    RVTEST_DFLT_INT_HNDLR  // VS-mode ext interrupt clear: abort
#endif


//==============================================================================
//==============================================================================
//
//  SECTION 17: RVTEST_TRAP_PROLOG
//
//  Per-mode trap handler initialization. Called once per mode during boot.
//  Sets up:
//    - xSCRATCH with pointer to this mode's save area
//    - Timer comparator to max value (prevent premature timer interrupts)
//    - xEDELEG saved and cleared (prevent delegation during init)
//    - xSATP saved and set to identity-mapped page table (if not M-mode)
//    - xTVEC pointed to trampoline (or trampoline copied to xTVEC target)
//
//  Parameters:
//    __MODE__: M, S, H, or V
//
//  Register usage: T1..T6 (all available, called during boot in M-mode)
//  Precondition: Running in M-mode, T1..T6 are free
//  Postcondition: xSCRATCH -> save area, xTVEC -> trampoline, CSRs saved
//
//  The prolog handles two cases for xTVEC:
//    Case 1 (writable): Write trampoline address directly to xTVEC. Done.
//    Case 2 (read-only): Save the code at the xTVEC target, copy our
//           trampoline code over it, and use fence.i to sync. On epilog,
//           the original code is restored from the save area.
//
//==============================================================================
//==============================================================================

.macro  RVTEST_TRAP_PROLOG __MODE__
.option push
.option norvc                                    // no compressed instructions in handler code

.global \__MODE__\()trampoline                   // make trampoline label globally visible
        XCSR_RENAME \__MODE__                    // set CSR_X* aliases for this mode

        LA(     T1, \__MODE__\()tramptbl_sv)     // T1 = address of this mode's save area in .data

//---------- Initialize xSCRATCH ----------
init_\__MODE__\()scratch:
        csrrw   T3, CSR_XSCRATCH, T1            // swap: xSCRATCH ← save area ptr, T3 ← old xSCRATCH
        SREG    T3, xscr_save_off(T1)            // save original xSCRATCH value in save area

//---------- Initialize timer comparator ----------
#ifdef RVMODEL_MTIMECMP_BASE
init_\__MODE__\()timecmp:
        LI(  T2,  -1)                            // T2 = 0xFFFF...FFFF (max value)
        LI(  T4,  RVMODEL_MTIMECMP_BASE)         // T4 = mtimecmp address
        SREG T2,  0(T4)                           // write max to mtimecmp low word (prevent timer int)
  .if (XLEN==32)
        SREG T2,  4(T4)                           // RV32: also write max to mtimecmp high word
  .endif
        nop                                       // padding to keep code size constant vs #else branch
#else
        nop                                       // no timer: 5 nops to match the #ifdef branch size
        nop
        nop
  .if (XLEN==32)
        nop                                       // extra nop for RV32 branch size matching
  .endif
        nop
#endif

//---------- Save and clear exception delegation ----------
init_\__MODE__\()edeleg:
        li      T2, 0                             // T2 = 0 (value to write to xedeleg)
  .ifc \__MODE__ , M
    #ifdef S_SUPPORTED
        csrrw   T2, CSR_XEDELEG, T2              // M-mode: save medeleg, write 0 (no delegation during init)
    #endif
  .endif
  .ifc \__MODE__ , H
        csrrw   T2, CSR_XEDELEG, T2              // H-mode: save hedeleg, write 0
  .endif
       SREG    T2, xedeleg_sv_off(T1)            // store saved xedeleg in save area

//---------- Save and set xSATP (non-M-mode only) ----------
init_\__MODE__\()satp:
.ifnc \__MODE__ , M                              // M-mode doesn't use xSATP for its own address translation
        LA(     T4, rvtest_\__MODE__\()root_pg_tbl) // T4 = address of identity-mapped page table
        srli T4, T4, 12                           // convert to PPN (physical page number)
      #if (XLEN==32)
        LI(T3, SATP32_MODE)                       // RV32: SV32 mode bits
      #elseif (_VA_SZ_ == 39)
        LI(T3, (SATP64_MODE) & (SATP_MODE_SV39 << 60))  // RV64 SV39
      #elseif (_VA_SZ_ == 48)
        LI(T3, (SATP64_MODE) & (SATP_MODE_SV48 << 60))  // RV64 SV48
      #elseif (_VA_SZ_ == 57)
        LI(T3, (SATP64_MODE) & (SATP_MODE_SV57 << 60))  // RV64 SV57
      #endif
        or      T4, T4, T3                        // combine MODE bits with PPN
        csrrw   T4, CSR_XSATP, T4                 // write new xSATP, get old value in T4
        SREG    T4, xsatp_sv_off(T1)              // save old xSATP in save area
.endif

//---------- Save and set xTVEC ----------
init_\__MODE__\()tvec:
        csrr    T3, CSR_XTVEC                     // T3 = current xTVEC value (address + mode bits)
        SREG    T3, xtvec_sav_off(T1)              // save original xTVEC in save area
        andi    T2, T3, WDBYTMSK                   // T2 = mode bits from original xTVEC (bits 1:0)
        LREG    T4, tentry_addr_off(T1)            // T4 = common entry point (end of trampoline)
        addi    T4, T4, -actual_tramp_sz           // T4 = start of trampoline (entry point - tramp size)
        or      T2, T4, T2                         // T2 = trampoline start + original mode bits
        SREG    T2, xtvec_new_off(T1)              // save new xTVEC value in save area
        csrw    CSR_XTVEC, T2                      // attempt to write trampoline address to xTVEC

        csrr    T5, CSR_XTVEC                      // read back xTVEC to verify it was written
#ifndef HANDLER_TESTCODE_ONLY
        beq     T5, T2, rvtest_\__MODE__\()prolog_done  // if readback matches, xTVEC is writable. Done!
#endif
        // xTVEC is NOT fully writable — need to copy trampoline to xTVEC target
        csrw    CSR_XTVEC, T3                      // restore original xTVEC (we'll overwrite its target)
        beqz    T3, abort\__MODE__\()test           // if xTVEC was 0 (uninitialized), can't proceed — abort
        SREG    T3, xtvec_new_off(T1)               // update tvec_new with the original (now-in-use) xTVEC

//---------- Copy trampoline to fixed xTVEC target ----------
init_\__MODE__\()tramp:
        andi    T2, T3, ~WDBYTMSK                 // T2 = xTVEC target address (clear mode bits)
        addi    T3, T2, actual_tramp_sz            // T3 = end of target area
        mv      sp, T1                             // sp = save area base (for saving original code)

overwt_tt_\__MODE__\()loop:
        lw      T6, 0(T2)                          // read original instruction at xTVEC target
        sw      T6, 0(T1)                          // save it in trampoline save area
        lw      T5, 0(T4)                          // read our trampoline instruction
        sw      T5, 0(T2)                          // write it to xTVEC target
        lw      T6, 0(T2)                          // read back to verify write succeeded
        bne     T6, T5, endcopy_\__MODE__\()tramp  // if readback failed, target not writable — stop
#ifdef HANDLER_TESTCODE_ONLY
        csrr    T5, CSR_XSCRATCH                   // test-only: check if we've gone too far
        addi    T5, T5,256                          // artificial limit for testing
        bgt     T5, T1, endcopy_\__MODE__\()tramp   // pretend it wasn't writable
#endif
        addi    T2, T2, WDBYTSZ                    // advance xTVEC target pointer
        addi    T1, T1, WDBYTSZ                    // advance save area pointer
        addi    T4, T4, WDBYTSZ                    // advance trampoline source pointer
        bne     T3, T2, overwt_tt_\__MODE__\()loop  // loop until end of trampoline

endcopy_\__MODE__\()tramp:
        RVMODEL_FENCEI                              // sync icache: we just wrote code to the xTVEC target
        csrr    T1, CSR_XSCRATCH                    // reload save area ptr from xSCRATCH (may have been modified)
        SREG    T4, tentry_addr_off(T1)              // update common entry point address (may differ if partial copy)
        beq     T3,T2, rvtest_\__MODE__\()prolog_done  // if full copy completed, prolog is done
abort\__MODE__\()test:
        mv      T3, T2                              // save copy progress for epilog cleanup
        LA(     T6, exit_\__MODE__\()cleanup)        // load address of cleanup label
        jr      T6                                   // long jump to cleanup (may be too far for branch)

rvtest_\__MODE__\()prolog_done:
        nop                                          // prevent label from collapsing with next section

.option pop
.endm                                               // end of RVTEST_TRAP_PROLOG

//==============================================================================
//==============================================================================
//
//  SECTION 18: RVTEST_TRAP_HANDLER
//
//  The main trap handler macro. This is the heart of the ACT4 framework.
//  One copy is instantiated per supported privilege mode (M, S, H, V).
//
//  STRUCTURE:
//    1. Trampoline table       — XLEN jump instructions for vectored entry
//    2. Per-cause stubs        — save sp+T6, jump to common handler
//    3. Common handler         — save T5, restore xSCRATCH, jump to entry
//    4. Common entry           — save T1-T4, read xcause
//    5. T-SBI dispatch (NEW)   — check for ecall + dispatch SBI operations
//    6. Trap signature update  — record trap info in signature region
//    7. Exception handler      — relocate xEPC, bump past instruction
//    8. Interrupt handler      — clear interrupt source via dispatch table
//    9. Restore and return     — restore T1-T6+sp, xret
//
//  T-SBI DISPATCH (NEW CODE):
//    Inserted between ecall detection and normal trap signature recording.
//    M-mode handler:  full dispatch (ECALL_TEST, CSR_ACCESS, GOTO_xMODE)
//    S-mode handler:  partial dispatch + forwarding to M-mode for privileged ops
//
//  REGISTER STATE AT T-SBI DISPATCH POINT:
//    sp     = pointer to current mode's save area (Xtramptbl_sv)
//    T5     = xcause value (MSB=1 for interrupts)
//    T4     = masked cause (cause[11:0] only, int bit cleared)
//    T3     = available (used in preceding comparisons)
//    T2     = available
//    T1     = saved at trap_sv_off+1*REGWIDTH(sp)
//    T6     = saved at trap_sv_off+6*REGWIDTH(sp)
//    orig sp= saved at trap_sv_off+7*REGWIDTH(sp)
//
//  CALLER'S a0/a1 RECOVERY:
//    Since T5=x10=a0 and T6=x11=a1, the handler's csrr T5,xcause overwrites
//    the caller's a0. But the caller's a0 was saved EARLIER in the handler
//    entry sequence (step 2 above: SREG T5, trap_sv_off+5*REGWIDTH(sp) saves
//    the ORIGINAL T5/a0 before it's overwritten with xcause).
//    Similarly, the caller's a1/T6 is saved at trap_sv_off+6*REGWIDTH(sp).
//
//    Therefore, to recover the caller's SBI operation code:
//      LREG T3, trap_sv_off+5*REGWIDTH(sp)  // T3 = caller's original a0
//    And to recover the caller's SBI argument:
//      LREG T2, trap_sv_off+6*REGWIDTH(sp)  // T2 = caller's original a1
//
//==============================================================================
//==============================================================================

.macro RVTEST_TRAP_HANDLER __MODE__
.option push
.option rvc                                      // temporarily allow compressed for alignment padding
.align MTVEC_ALIGN                               // align to required boundary (typically 64 bytes)
.option pop                                      // restore to norvc

  XCSR_RENAME \__MODE__                          // set CSR_X* aliases for this mode's CSRs

.global \__MODE__\()trampoline                   // make trampoline globally visible (used by prolog)
.global common_\__MODE__\()entry                 // make common entry globally visible
.option push
.option norvc                                    // all handler code must be uncompressed (32-bit instructions)

//---------- Vector Spreader Region ----------
// XLEN jump instructions, one per possible vectored interrupt/exception cause.
// Each jumps to the corresponding per-cause handler stub.
// For causes beyond NUM_SPECD_INTCAUSES, jump to endtest (impossible cause).

\__MODE__\()trampoline:                          // GLOBAL: start of trampoline table
   .set  value, 0                                // offset accumulator for per-cause stubs
  .rept NUM_SPECD_INTCAUSES                      // for each valid interrupt cause (0..23):
        j    trap_\__MODE__\()handler+ value     //   jump to per-cause stub at handler_base + offset
        .set value, value + 12                   //   each stub is 3 instructions = 12 bytes
  .endr

  .rept XLEN-NUM_SPECD_INTCAUSES                 // for each impossible cause (24..XLEN-1):
        j rvtest_\__MODE__\()endtest             //   jump to end-of-test handler (abort)
  .endr

//---------- Per-Cause Handler Stubs ----------
// 3 instructions per cause, repeated NUM_SPECD_INTCAUSES times.
// Purpose: save minimal state and jump to common handler with vector info.

 trap_\__MODE__\()handler:                       // start of per-cause stub array
  .rept NUM_SPECD_INTCAUSES                      // for each valid cause:
        csrrw   sp, CSR_XSCRATCH, sp            //   swap sp with save area ptr from xSCRATCH
        SREG    T6, trap_sv_off+6*REGWIDTH(sp)  //   save T6 (=x11=a1) in handler reg save area
        jal     T6, common_\__MODE__\()handler  //   jump to common handler; T6 = return addr = vector ID
  .endr

//---------- End-of-test trampoline ----------
// Reached for impossible/unhandled interrupt causes.
// Long-jumps to rvtest_Xend which is the epilog cleanup entry.

rvtest_\__MODE__\()endtest:                      // impossible cause landed here
        LA(     T1, rvtest_\__MODE__\()end)      // load epilog cleanup address (may be far away)
        jr      T1                                // long jump to epilog cleanup

//---------- Common Handler ----------
// Entered via jal from per-cause stub. T6 has the stub's return address
// (which encodes the vector offset). This code saves additional state and
// jumps to the common entry point (which may be at a different address if
// the trampoline was relocated).

common_\__MODE__\()handler:                      // entered with T6 = vector addr, sp = save area
        SREG    T5, trap_sv_off+5*REGWIDTH(sp)  // save T5 (=x10=a0=CALLER'S ORIGINAL a0) ***CRITICAL***
        csrrw   T5, CSR_XSCRATCH, sp            // T5 = old xSCRATCH value (= orig sp before swap)
        SREG    T5, trap_sv_off+7*REGWIDTH(sp)  // save original sp in handler reg save area
        LREG    T5, tentry_addr_off(sp)          // T5 = common_Xentry address (from save area)
        jr      T5                                // jump to common entry (handles relocated trampoline case)

//---------- Common Entry Point ----------
// Saves remaining handler temporaries and reads xcause.
// After this point:
//   sp     -> save area
//   T5     = xcause
//   T1..T4 saved in save area
//   T5 (original a0) saved at trap_sv_off+5*REGWIDTH(sp) (by common_Xhandler above)
//   T6 (original a1) saved at trap_sv_off+6*REGWIDTH(sp) (by per-cause stub above)
//   orig sp saved at trap_sv_off+7*REGWIDTH(sp)

common_\__MODE__\()entry:                        // common entry for all traps in this mode
        SREG    T4, trap_sv_off+4*REGWIDTH(sp)  // save T4 (x9)
        SREG    T3, trap_sv_off+3*REGWIDTH(sp)  // save T3 (x8)
        SREG    T2, trap_sv_off+2*REGWIDTH(sp)  // save T2 (x7)
        SREG    T1, trap_sv_off+1*REGWIDTH(sp)  // save T1 (x6)
        csrr    T5, CSR_XCAUSE                   // T5 = xcause (OVERWRITES x10/a0 — caller's a0 already saved)

//==============================================================================
// T-SBI DISPATCH — M-MODE
//
// CONTROL FLOW:
//   1. Check for ALT_GOTO_M_CAUSE (alternate illegal instruction path) with x3==0 -> rtn2mmode
//   2. Check if cause is an ecall (causes 8..11) -> if not, go to normal trap sig
//   3. Check x3==0 (legacy GOTO_MMODE fast path) -> rtn2mmode
//   4. NEW: Recover caller's a0 from save area, dispatch on a0:
//      a. a0 in [1..5] -> GOTO_xMODE (set MPP/MPV, bump mepc, mret)
//      b. a0 == 0x73   -> ECALL_TEST (return xEPC in a0, bump mepc)
//      c. a0[6:0]==0x73 && a0[14:12]!=0 -> CSR_ACCESS (execute dynamic CSR instr)
//      d. Otherwise    -> RESERVED (return -1 in a0)
//   5. If not an SBI call: fall through to normal trap signature recording
//
// REGISTER STATE:
//   T5 = xcause, T4/T3/T2 = available temporaries
//   sp = save area ptr, caller's a0 at trap_sv_off+5*REGWIDTH(sp)
//                        caller's a1 at trap_sv_off+6*REGWIDTH(sp)
//==============================================================================

  .ifc \__MODE__ ,  M                           // ----- BEGIN M-MODE ONLY SECTION -----

spcl_\__MODE__\()2mmode_test:                    // Step 1: Check for ALT_GOTO_M_CAUSE (alternate ecall path)
        LI(T4,(1<<(XLEN-1))+((1<<12)-1))        // T4 = mask: MSB + cause[11:0] (strips CLIC extension bits)
        and     T4, T4, T5                        // T4 = masked xcause (int bit + cause[11:0] only)

spcl_\__MODE__\()chk4alt:                        // Check if cause matches ALT_GOTO_M_CAUSE (e.g., illegal instr)
        addi    T3,T4, -ALT_GOTO_M_CAUSE         // T3 = masked_cause - ALT_CAUSE (0 if match)
        bnez    T3, spcl_\__MODE__\()chk4ecall   // not the alt cause -> check for standard ecall

spcl_\__MODE__\()param_chk:                      // ALT_GOTO_M cause detected — check if it's a GOTO_MMODE request
        beqz    x3, \__MODE__\()rtn2mmode         // x3==0 -> this IS a GOTO_MMODE request via alt path -> handle it
        j           \__MODE__\()trapsig_ptr_upd   // x3!=0 -> normal trap (alt cause happened naturally) -> record sig

spcl_\__MODE__\()chk4ecall:                      // Step 2: Check if cause is an ecall (causes 8, 9, 10, or 11)
        addi    T3, T4, -CAUSE_USER_ECALL         // T3 = masked_cause - 8 (maps ecall causes 8..11 to 0..3)
        srli    T3, T3, 2                          // T3 = (cause-8) >> 2 (0 only if cause was 8,9,10, or 11)
        bnez    T3, \__MODE__\()trapsig_ptr_upd   // not an ecall -> go to normal trap signature recording

   .endif                                        // end of M-mode ALT check (S/H/V modes skip this)

// ----- Legacy x3==0 fast path (GOTO_MMODE / GOTO_SMODE) -----
// This handles the ORIGINAL RVTEST_GOTO_MMODE convention.
// Tests using the old macros set x3=0 before ecall. The handler detects
// this and returns in M-mode without recording a trap signature.

.ifc \__MODE__ ,  M                              // M-mode: check x3==0 for GOTO_MMODE

\__MODE__\()goto_mchk:                           // Step 3: Is this a legacy GOTO_MMODE? (x3==0)
        beqz    x3, \__MODE__\()rtn2mmode         // x3==0 -> legacy GOTO_MMODE -> jump to rtn2mmode handler

        //==============================================================
        // Step 4: T-SBI DISPATCH — a0-based operation dispatch (M-mode)
        //
        // We've confirmed: this IS an ecall, and x3 IS NOT 0.
        // So this is a T-SBI call. Recover the caller's a0 from the
        // save area (it was saved before xcause overwrote it).
        //
        // Available registers: T2, T3, T4 (T5 = xcause, T1/T6 saved)
        // Caller's a0: at trap_sv_off+5*REGWIDTH(sp)
        // Caller's a1: at trap_sv_off+6*REGWIDTH(sp)
        //==============================================================

tsbi_\__MODE__\()dispatch:
        LREG    T3, trap_sv_off+5*REGWIDTH(sp)   // T3 = caller's original a0 (SBI operation code)

        // --- Check for GOTO_xMODE (a0 == 1..5) ---
        addi    T4, T3, -1                        // T4 = caller_a0 - 1 (maps [1..5] to [0..4])
        li      T2, 5                              // T2 = 5 (upper bound)
        bltu    T4, T2, tsbi_\__MODE__\()goto_mode // if (a0-1) < 5 -> a0 in [1..5] -> GOTO_xMODE dispatch

        // --- Check for ECALL_TEST (a0 == 0x00000073) ---
        LI(     T2, TSBI_ECALL_TEST)              // T2 = 0x73 (ECALL_TEST operation code)
        beq     T3, T2, tsbi_\__MODE__\()ecall_test // if caller_a0 == 0x73 -> ECALL_TEST handler

        // --- Check for CSR_ACCESS: opcode[6:0] == 0x73 AND funct3[14:12] != 0 ---
        andi    T2, T3, 0x7F                       // T2 = caller_a0[6:0] (extract opcode field)
        LI(     T4, 0x73)                           // T4 = 0x73 (SYSTEM opcode)
        bne     T2, T4, tsbi_\__MODE__\()reserved   // opcode != SYSTEM -> not a CSR instruction -> reserved

        srli    T2, T3, 12                          // T2 = caller_a0 >> 12 (shift funct3 to LSBs)
        andi    T2, T2, 0x7                         // T2 = funct3 field (bits 14:12)
        beqz    T2, tsbi_\__MODE__\()reserved       // funct3==0 -> ecall/ebreak/etc, not CSR -> reserved
        j       tsbi_\__MODE__\()csr_access         // funct3!=0 -> valid CSR instruction -> CSR_ACCESS handler

        //--------------------------------------------------------------
        // T-SBI RESERVED handler
        // Reached when a0 doesn't match any known operation.
        // Returns -1 in a0 and advances mepc past the ecall.
        //--------------------------------------------------------------
tsbi_\__MODE__\()reserved:
        li      a0, TSBI_RESERVED_RET             // a0 = -1 (error: unrecognized operation)
        csrr    T3, CSR_XEPC                       // T3 = mepc (address of the ecall instruction)
        addi    T3, T3, 4                           // T3 = mepc + 4 (skip past the 4-byte ecall)
        csrw    CSR_XEPC, T3                        // mepc = mepc + 4 (so mret returns after ecall)
        j       resto_\__MODE__\()rtn              // restore regs and mret

        //--------------------------------------------------------------
        // T-SBI ECALL_TEST handler (M-mode)
        //
        // Purpose: Verify that the ecall trap path is functional.
        // Returns the xEPC value (address of the ecall instruction) in a0.
        // This lets the test confirm that the handler was entered correctly.
        //
        // On return: a0 = address of the ecall instruction that triggered this trap
        //--------------------------------------------------------------
tsbi_\__MODE__\()ecall_test:
        csrr    a0, CSR_XEPC                       // a0 = mepc = address of the ecall instruction
        csrr    T3, CSR_XEPC                        // T3 = mepc (read again for bump calculation)
        addi    T3, T3, 4                            // T3 = mepc + 4 (skip past ecall)
        csrw    CSR_XEPC, T3                         // mepc = mepc + 4
        j       resto_\__MODE__\()rtn               // restore regs and mret (a0 carries the return value)

        //--------------------------------------------------------------
        // T-SBI GOTO_xMODE handler (M-mode)
        //
        // Purpose: Switch the caller to a different privilege mode.
        // The caller's a0 value (recovered from save area into T3) determines the target:
        //   1 = M-mode    2 = S-mode    3 = U-mode    4 = VS-mode    5 = VU-mode
        //
        // Mechanism: Set mstatus.MPP and optionally mstatus.MPV, bump mepc+4,
        //   then mret. The mret instruction transitions to the mode specified by MPP/MPV
        //   and jumps to mepc (which is now the instruction after the caller's ecall).
        //
        // Note: For GOTO_MMODE, we reuse the existing rtn2mmode path which handles
        //   EPC relocation across address spaces. The simpler GOTO_S/U/VS/VU paths
        //   don't need relocation because they set MPP/MPV and let mret handle it.
        //--------------------------------------------------------------
tsbi_\__MODE__\()goto_mode:
        // First, bump mepc past the ecall instruction
        csrr    T4, CSR_XEPC                        // T4 = mepc (caller's ecall address)
        addi    T4, T4, 4                            // T4 = mepc + 4 (instruction after ecall)
        csrw    CSR_XEPC, T4                         // mepc = mepc + 4

        // Dispatch based on caller's a0 (still in T3 from tsbi_Mdispatch)
        li      T2, TSBI_GOTO_MMODE                  // T2 = 1
        beq     T3, T2, tsbi_\__MODE__\()goto_m     // a0==1 -> GOTO_MMODE
        li      T2, TSBI_GOTO_SMODE                  // T2 = 2
        beq     T3, T2, tsbi_\__MODE__\()goto_s     // a0==2 -> GOTO_SMODE
        li      T2, TSBI_GOTO_UMODE                  // T2 = 3
        beq     T3, T2, tsbi_\__MODE__\()goto_u     // a0==3 -> GOTO_UMODE
  #ifdef H_SUPPORTED
        li      T2, TSBI_GOTO_VSMODE                 // T2 = 4
        beq     T3, T2, tsbi_\__MODE__\()goto_vs    // a0==4 -> GOTO_VSMODE
        li      T2, TSBI_GOTO_VUMODE                 // T2 = 5
        beq     T3, T2, tsbi_\__MODE__\()goto_vu    // a0==5 -> GOTO_VUMODE
  #endif
        li      a0, TSBI_RESERVED_RET                // shouldn't reach here (range checked above), but return -1
        j       resto_\__MODE__\()rtn               // restore and mret

        //--- GOTO M-mode: set MPP=11 (M), clear MPV ---
tsbi_\__MODE__\()goto_m:
        LI(     T4, MSTATUS_MPP)                     // T4 = MPP field mask (bits 12:11)
        csrs    CSR_MSTATUS, T4                       // set MPP = 11 (M-mode): sets both bits
  #ifdef H_SUPPORTED
        LI(     T2, (1<<MPV_LSB))                    // T2 = MPV bit mask
    #if (XLEN==32)
        csrc    CSR_MSTATUSH, T2                      // RV32: clear MPV in mstatush (not virtual)
    #else
        slli    T2, T2, 32                            // RV64: shift MPV to upper half of mstatus
        csrc    CSR_MSTATUS, T2                       // RV64: clear MPV in mstatus
    #endif
  #endif
        j       resto_\__MODE__\()rtn               // restore T1..T6, sp; mret -> returns in M-mode

        //--- GOTO S-mode: set MPP=01 (S), clear MPV ---
tsbi_\__MODE__\()goto_s:
        LI(     T4, MSTATUS_MPP)                     // T4 = MPP field mask
        csrc    CSR_MSTATUS, T4                       // clear MPP bits first (to 00)
        LI(     T4, MPP_SMODE)                        // T4 = 01 << 11 (S-mode MPP value)
        csrs    CSR_MSTATUS, T4                       // set MPP = 01 (S-mode)
  #ifdef H_SUPPORTED
        LI(     T2, (1<<MPV_LSB))                    // T2 = MPV bit mask
    #if (XLEN==32)
        csrc    CSR_MSTATUSH, T2                      // RV32: clear MPV (not virtual)
    #else
        slli    T2, T2, 32                            // RV64: shift to upper half
        csrc    CSR_MSTATUS, T2                       // RV64: clear MPV
    #endif
  #endif
        j       resto_\__MODE__\()rtn               // mret -> returns in S-mode at mepc

        //--- GOTO U-mode: set MPP=00 (U), clear MPV ---
tsbi_\__MODE__\()goto_u:
        LI(     T4, MSTATUS_MPP)                     // T4 = MPP field mask
        csrc    CSR_MSTATUS, T4                       // clear MPP = 00 (U-mode)
  #ifdef H_SUPPORTED
        LI(     T2, (1<<MPV_LSB))                    // T2 = MPV bit mask
    #if (XLEN==32)
        csrc    CSR_MSTATUSH, T2                      // RV32: clear MPV (not virtual)
    #else
        slli    T2, T2, 32                            // RV64: shift to upper half
        csrc    CSR_MSTATUS, T2                       // RV64: clear MPV
    #endif
  #endif
        j       resto_\__MODE__\()rtn               // mret -> returns in U-mode at mepc

  #ifdef H_SUPPORTED
        //--- GOTO VS-mode: set MPP=01 (S), set MPV=1 (virtual) ---
tsbi_\__MODE__\()goto_vs:
        LI(     T4, MSTATUS_MPP)                     // T4 = MPP field mask
        csrc    CSR_MSTATUS, T4                       // clear MPP first
        LI(     T4, MPP_SMODE)                        // T4 = S-mode MPP value (VS uses S-mode MPP with MPV=1)
        csrs    CSR_MSTATUS, T4                       // set MPP = 01 (S-mode)
        LI(     T2, (1<<MPV_LSB))                    // T2 = MPV bit mask
    #if (XLEN==32)
        csrs    CSR_MSTATUSH, T2                      // RV32: set MPV=1 in mstatush (virtualized)
    #else
        slli    T2, T2, 32                            // RV64: shift to upper half
        csrs    CSR_MSTATUS, T2                       // RV64: set MPV=1 in mstatus
    #endif
        j       resto_\__MODE__\()rtn               // mret -> returns in VS-mode (MPP=S + MPV=1) at mepc

        //--- GOTO VU-mode: set MPP=00 (U), set MPV=1 (virtual) ---
tsbi_\__MODE__\()goto_vu:
        LI(     T4, MSTATUS_MPP)                     // T4 = MPP field mask
        csrc    CSR_MSTATUS, T4                       // clear MPP = 00 (U-mode)
        LI(     T2, (1<<MPV_LSB))                    // T2 = MPV bit mask
    #if (XLEN==32)
        csrs    CSR_MSTATUSH, T2                      // RV32: set MPV=1 in mstatush (virtualized)
    #else
        slli    T2, T2, 32                            // RV64: shift to upper half
        csrs    CSR_MSTATUS, T2                       // RV64: set MPV=1 in mstatus
    #endif
        j       resto_\__MODE__\()rtn               // mret -> returns in VU-mode (MPP=U + MPV=1) at mepc
  #endif // H_SUPPORTED

        //--------------------------------------------------------------
        // T-SBI CSR_ACCESS handler (M-mode)
        //
        // Purpose: Execute an arbitrary CSR instruction on behalf of a
        //   lower-privilege caller. This enables S/U-mode tests to read/write
        //   M-mode CSRs without direct access.
        //
        // Mechanism:
        //   1. The caller's a0 contains the 32-bit CSR instruction encoding
        //      (recovered from save area into T3 at dispatch entry)
        //   2. Write this encoding to scratch memory (rvmodel_sv area in save area)
        //   3. Write a "ret" (jalr x0, x1, 0 = 0x00008067) immediately after it
        //   4. fence.i to sync the instruction cache with the new code
        //   5. Restore caller's a1 (for rs1) from save area
        //   6. jalr ra into the scratch location — this executes the CSR instruction
        //      and the ret returns to the next instruction here
        //   7. a0 now contains the CSR read result (if rd==a0 in the encoding)
        //   8. Bump xEPC+4, restore handler regs, mret
        //
        // CONSTRAINTS:
        //   - The CSR encoding's rd field MUST be a0 (x10) for reads, so the
        //     result lands in a0 for return to the caller
        //   - The CSR encoding's rs1 field SHOULD be a1 (x11) for writes
        //   - The scratch area must be executable (it's in .data — assumes no W^X)
        //   - The scratch area is 8 bytes at rvmodel_sv_off in the save area
        //
        // EXAMPLE: Read mstatus (CSR 0x300) using csrrs a0, mstatus, x0
        //   Instruction encoding: 0x30002573
        //     imm[31:20] = 0x300 (CSR address: mstatus)
        //     rs1[19:15] = 00000 (x0: read-only, no side effects)
        //     funct3[14:12] = 010 (CSRRS)
        //     rd[11:7] = 01010 (a0 = x10: result goes here)
        //     opcode[6:0] = 1110011 (SYSTEM)
        //--------------------------------------------------------------
tsbi_\__MODE__\()csr_access:
        // T3 still has caller's a0 (the CSR encoding) from tsbi_Mdispatch
        mv      T4, T3                             // T4 = CSR instruction encoding (copy from T3)

        addi    T2, sp, tsbi_csr_scratch_off       // T2 -> scratch location in save area's rvmodel_sv

        sw      T4, 0(T2)                          // write CSR instruction to scratch[0:3]

        LI(     T3, 0x00008067)                    // T3 = encoding of "ret" (jalr x0, ra, 0)
        sw      T3, 4(T2)                          // write ret instruction to scratch[4:7]

        RVMODEL_FENCEI                              // sync icache: we just wrote executable code to data memory

        // Restore caller's a1 from save area before executing the CSR instruction.
        // The CSR encoding may use rs1=a1, so a1 must contain the caller's argument.
        LREG    a1, trap_sv_off+6*REGWIDTH(sp)     // a1 = caller's original a1 (T6 was saved here)

        // Execute the CSR instruction by calling into scratch memory.
        // jalr with ra: the ret in scratch returns to the instruction after this jalr.
        // a0 will be overwritten with the CSR read result (if rd==a0 in the encoding).
        jalr    ra, T2, 0                          // call scratch: execute CSR instr, ret back here

        // a0 now holds the CSR read result (if rd was a0 in the encoding)
        csrr    T3, CSR_XEPC                        // T3 = mepc (ecall address)
        addi    T3, T3, 4                            // T3 = mepc + 4 (skip past ecall)
        csrw    CSR_XEPC, T3                         // update mepc for return
        j       resto_\__MODE__\()rtn               // restore handler regs, mret to caller with result in a0

.endif  // --------- END M-MODE T-SBI DISPATCH ---------

//==============================================================================
// T-SBI DISPATCH — S-MODE
//
// The S-mode handler receives ecalls delegated from U-mode (when medeleg[8]=1).
// It implements a subset of T-SBI operations locally and forwards the rest
// to M-mode by making another ecall.
//
// LOCAL HANDLING (S-mode can service these directly):
//   - ECALL_TEST:  return sepc in a0 (sepc = U-mode ecall address)
//   - GOTO_SMODE:  set sstatus.SPP=1 (return to S-mode via sret)
//   - GOTO_UMODE:  set sstatus.SPP=0 (return to U-mode via sret)
//   - CSR_ACCESS for S/U-mode CSRs: execute locally (CSR addr[9:8] != 11)
//
// FORWARDED TO M-MODE (requires M-mode privileges):
//   - GOTO_MMODE:  needs M-mode to set MPP
//   - GOTO_VSMODE: needs M-mode to set MPV
//   - GOTO_VUMODE: needs M-mode to set MPV
//   - CSR_ACCESS for M-mode CSRs: needs M-mode privilege (CSR addr[9:8] == 11)
//
// FORWARDING MECHANISM:
//   The S-mode handler restores all handler temporary registers, then executes
//   ecall. This traps to M-mode with cause=CAUSE_SUPERVISOR_ECALL (9).
//   The caller's a0/a1/x3 pass through unchanged because:
//   - a0/a1 (=T5/T6) are restored from the save area before the ecall
//   - x3 is never modified by the handler
//   M-mode's T-SBI dispatch sees the S-mode ecall, detects x3!=0 and a0 as
//   a valid SBI op, and handles it directly.
//
// CALLER's a0/a1 RECOVERY:
//   Same as M-mode: caller's a0 saved at trap_sv_off+5*REGWIDTH(sp),
//   caller's a1 saved at trap_sv_off+6*REGWIDTH(sp).
//==============================================================================

.ifc \__MODE__ ,  S                              // ----- BEGIN S-MODE ONLY SECTION -----

\__MODE__\()goto_schk:                           // S-mode ecall check entry
        LI(T4,(1<<(XLEN-1))+((1<<12)-1))        // T4 = int_bit + cause[11:0] mask
        and     T4, T4, T5                        // T4 = masked xcause
        addi    T3, T4, -CAUSE_USER_ECALL          // T3 = masked_cause - 8 (U-mode ecall = cause 8)
        bnez    T3, \__MODE__\()trapsig_ptr_upd   // not a U-mode ecall -> normal trap sig recording
        beqz    x3, \__MODE__\()rtn2smode          // x3==0 -> legacy GOTO_SMODE -> rtn2smode handler

        //--- T-SBI dispatch: recover caller's a0 and dispatch ---
tsbi_\__MODE__\()dispatch:
        LREG    T3, trap_sv_off+5*REGWIDTH(sp)   // T3 = caller's original a0 (SBI operation code)

        // Check for GOTO_xMODE (a0 == 1..5)
        addi    T4, T3, -1                         // T4 = a0 - 1
        li      T2, 5                               // T2 = 5
        bltu    T4, T2, tsbi_\__MODE__\()goto_mode // a0 in [1..5] -> GOTO dispatch

        // Check for ECALL_TEST (a0 == 0x73)
        LI(     T2, TSBI_ECALL_TEST)              // T2 = 0x73
        beq     T3, T2, tsbi_\__MODE__\()ecall_test // match -> ECALL_TEST handler

        // Check for CSR_ACCESS
        andi    T2, T3, 0x7F                       // T2 = a0[6:0]
        LI(     T4, 0x73)                           // T4 = SYSTEM opcode
        bne     T2, T4, tsbi_\__MODE__\()reserved   // not SYSTEM -> reserved
        srli    T2, T3, 12                          // T2 = a0[14:12]
        andi    T2, T2, 0x7                         // T2 = funct3
        beqz    T2, tsbi_\__MODE__\()reserved       // funct3==0 -> not CSR -> reserved
        j       tsbi_\__MODE__\()csr_access         // valid CSR encoding -> CSR_ACCESS

tsbi_\__MODE__\()reserved:                        // Unrecognized SBI operation
        li      a0, TSBI_RESERVED_RET              // a0 = -1 (error)
        csrr    T3, CSR_XEPC                        // T3 = sepc
        addi    T3, T3, 4                            // skip ecall
        csrw    CSR_XEPC, T3                         // sepc += 4
        j       resto_\__MODE__\()rtn              // sret to caller with a0 = -1

        //--- S-mode ECALL_TEST ---
tsbi_\__MODE__\()ecall_test:
        csrr    a0, CSR_XEPC                       // a0 = sepc = U-mode ecall address
        csrr    T3, CSR_XEPC                        // T3 = sepc (for bump)
        addi    T3, T3, 4                            // skip ecall
        csrw    CSR_XEPC, T3                         // sepc += 4
        j       resto_\__MODE__\()rtn              // sret to caller with a0 = ecall address

        //--- S-mode GOTO_xMODE dispatch ---
tsbi_\__MODE__\()goto_mode:
        csrr    T4, CSR_XEPC                        // T4 = sepc (caller's ecall address)
        addi    T4, T4, 4                            // skip ecall
        csrw    CSR_XEPC, T4                         // sepc += 4

        // T3 still has caller's a0 from dispatch entry
        li      T2, TSBI_GOTO_MMODE                  // can't handle GOTO_MMODE from S-mode
        beq     T3, T2, tsbi_\__MODE__\()forward_to_m // -> forward to M-mode

        li      T2, TSBI_GOTO_SMODE                  // GOTO_SMODE: return to S-mode
        beq     T3, T2, tsbi_\__MODE__\()goto_s

        li      T2, TSBI_GOTO_UMODE                  // GOTO_UMODE: return to U-mode
        beq     T3, T2, tsbi_\__MODE__\()goto_u

  #ifdef H_SUPPORTED
        li      T2, TSBI_GOTO_VSMODE                 // GOTO_VSMODE: needs M-mode
        beq     T3, T2, tsbi_\__MODE__\()forward_to_m
        li      T2, TSBI_GOTO_VUMODE                 // GOTO_VUMODE: needs M-mode
        beq     T3, T2, tsbi_\__MODE__\()forward_to_m
  #endif

        li      a0, TSBI_RESERVED_RET                // shouldn't reach here, return -1
        j       resto_\__MODE__\()rtn

tsbi_\__MODE__\()goto_s:                          // Return to S-mode via sret
        LI(     T3, SSTATUS_SPP)                   // T3 = SPP bit mask (bit 8)
        csrs    CSR_XSTATUS, T3                     // set sstatus.SPP = 1 (sret -> S-mode)
        j       resto_\__MODE__\()rtn              // sret returns to S-mode at sepc

tsbi_\__MODE__\()goto_u:                          // Return to U-mode via sret
        LI(     T3, SSTATUS_SPP)                   // T3 = SPP bit mask
        csrc    CSR_XSTATUS, T3                     // clear sstatus.SPP = 0 (sret -> U-mode)
        j       resto_\__MODE__\()rtn              // sret returns to U-mode at sepc

        //--- S-mode forwarding to M-mode ---
        // Restore all handler regs and ecall. M-mode handler processes the request.
tsbi_\__MODE__\()forward_to_m:
        LREG    T1, trap_sv_off+1*REGWIDTH(sp)    // restore T1 (x6)
        LREG    T2, trap_sv_off+2*REGWIDTH(sp)    // restore T2 (x7)
        LREG    T3, trap_sv_off+3*REGWIDTH(sp)    // restore T3 (x8)
        LREG    T4, trap_sv_off+4*REGWIDTH(sp)    // restore T4 (x9)
        LREG    T5, trap_sv_off+5*REGWIDTH(sp)    // restore T5/a0 = caller's original a0 (SBI opcode)
        LREG    T6, trap_sv_off+6*REGWIDTH(sp)    // restore T6/a1 = caller's original a1 (SBI argument)
        LREG    sp, trap_sv_off+7*REGWIDTH(sp)    // restore original sp (undo the xSCRATCH swap)
        ecall                                      // trap to M-mode with a0/a1/x3 intact
        // For GOTO_MMODE: M-mode's rtn2mmode returns directly to caller in M-mode (never returns here)
        // For GOTO_VS/VU: M-mode sets MPP/MPV and mrets to target (never returns here)
        // For CSR_ACCESS: M-mode executes CSR, mrets back to S-mode handler (here), which srets to caller
        sret                                       // if M-mode returned here: sret back to U-mode caller

        //--- S-mode CSR_ACCESS ---
tsbi_\__MODE__\()csr_access:
        // T3 has caller's a0 (CSR instruction encoding)
        // Check if CSR address indicates M-mode CSR: addr bits [11:10] in encoding bits [31:30]
        srli    T2, T3, 28                          // T2 = encoding[31:28] (top 4 bits)
        andi    T2, T2, 0x3                         // T2 = CSR_addr[11:10] (2 MSBs of CSR address)
        li      T4, 3                               // T4 = 3 (M-mode CSR indicator: addr[11:10]==11)
        beq     T2, T4, tsbi_\__MODE__\()forward_to_m // M-mode CSR -> must forward to M-mode handler

        // S-mode or U-mode CSR: can handle locally using scratch execution
        mv      T4, T3                             // T4 = CSR instruction encoding
        addi    T2, sp, tsbi_csr_scratch_off       // T2 -> scratch memory in rvmodel_sv area
        sw      T4, 0(T2)                          // write CSR instruction to scratch[0:3]
        LI(     T3, 0x00008067)                    // T3 = "ret" encoding (jalr x0, ra, 0)
        sw      T3, 4(T2)                          // write ret instruction to scratch[4:7]
        RVMODEL_FENCEI                              // sync icache after writing code to data memory
        LREG    a1, trap_sv_off+6*REGWIDTH(sp)     // restore caller's a1 (may be rs1 for the CSR instruction)
        jalr    ra, T2, 0                          // execute CSR instruction + ret (result in a0 if rd=a0)
        csrr    T3, CSR_XEPC                        // T3 = sepc
        addi    T3, T3, 4                            // skip past ecall
        csrw    CSR_XEPC, T3                         // sepc += 4
        j       resto_\__MODE__\()rtn              // sret to caller with CSR result in a0

.endif  // --------- END S-MODE T-SBI DISPATCH ---------

//==============================================================================
// M-MODE FORWARDED ECALL HANDLING (TODO)
//
// When M-mode receives an ecall from S-mode (cause 9) with x3!=0,
// it could be the S-mode handler forwarding a T-SBI request.
// The M-mode dispatch code above (tsbi_Mdispatch) handles the a0 value
// regardless of which mode the ecall came from. However, for forwarded
// GOTO operations, mepc points to the S-mode handler's ecall instruction,
// not the original U-mode caller's ecall. This needs special handling:
//
// For forwarded GOTOs: M-mode should set mepc = sepc (the original
// caller's return address, already bumped by the S-mode handler)
// so that mret goes directly to the original caller.
//
// This is currently a TODO — it works correctly when medeleg[8]=0
// (U-mode ecalls go directly to M-mode, so there's no forwarding).
// It will be completed when medeleg is updated to delegate U-mode ecalls.
//==============================================================================

.ifc \__MODE__ , M
tsbi_\__MODE__\()handle_forwarded:
        nop                                        // placeholder for future forwarded ecall handling
.endif

//==============================================================================
// NORMAL TRAP HANDLING (unchanged from original)
//
// Reached when the trap is NOT a T-SBI call (either not an ecall,
// or an ecall with x3==0 that was already handled by the legacy path,
// or a genuine ecall exception that should be recorded in the signature).
//
// This section:
//   1. Calculates the trap signature entry size (3, 4, or 6 words)
//   2. Pre-increments the trap signature pointer
//   3. Records: vect+mode word, xcause, xepc/xip, xtval/intID
//   4. For exceptions: relocates xEPC and bumps past the trapping instruction
//   5. For interrupts: dispatches to interrupt clearing routines
//   6. Checks for trap signature overrun
//   7. Restores registers and returns via xret
//==============================================================================

\__MODE__\()trapsig_ptr_upd:                     // pre-update trap signature pointer
        li      T2, 4*REGWIDTH                    // T2 = default entry size (4 words for exceptions)
        bgez    T5, \__MODE__\()xcpt_sig_sv       // if xcause MSB=0 -> exception, keep 4-word size

\__MODE__\()int_sig_sv:                          // interrupt path: determine 3 or 4 word entry
        slli    T3, T5, 1                          // T3 = xcause << 1 (remove MSB)
        addi    T3, T3, -(IRQ_M_TIMER)<<1          // compare against timer interrupt threshold
        bgez    T3, \__MODE__\()trap_sig_sv        // if cause >= timer -> external int (4 words, keep T2)
        li      T2, 3*REGWIDTH                    // cause < timer -> SW or timer int (3 words)
        j       \__MODE__\()trap_sig_sv            // go to pointer update

\__MODE__\()xcpt_sig_sv:                          // exception: check for hypervisor (6-word entry)
.ifc \__MODE__ , M
#ifdef H_SUPPORTED
        csrr    T1, CSR_MISA                       // read misa to check for H extension
        slli    T1, T1, XLEN-8                     // shift H bit (bit 7) to MSB
        bgez    T1, \__MODE__\()trap_sig_sv        // H not set -> standard 4-word exception entry
        li      T2, 6*REGWIDTH                    // H set -> 6-word entry (includes mtval2, mtinst)
#endif
.else
  .ifc \__MODE__ , H
        li      T2, 6*REGWIDTH                    // HS-mode: always 6-word exception entries
  .endif
.endif

\__MODE__\()trap_sig_sv:                          // compute pointer offset to M-mode's shared trap_sigptr
        .set sv_area_off, (+1*sv_area_sz)          // default: M-mode (1 area offset from sp)
.ifc \__MODE__ , H
        .set sv_area_off, ( 0*sv_area_sz)          // HS: 0 areas offset
.else
   .ifc \__MODE__ , S
     #ifdef H_SUPPORTED
        .set sv_area_off, (-1*sv_area_sz)          // S with H: -1 area offset
     #else
        .set sv_area_off, ( 0*sv_area_sz)          // S without H: 0 areas offset
     #endif
   .else
      .ifc \__MODE__ , V
        .set sv_area_off, (-2*sv_area_sz)          // VS: -2 areas offset
      .endif
    .endif
.endif
        addi    sp, sp, -1*sv_area_sz              // temporarily adjust sp to avoid large offset overflow
        LREG    T1, trapsig_ptr_off+sv_area_off(sp) // T1 = current trap sig write pointer (from M-mode area)
        add     T4, T1, T2                          // T4 = T1 + entry_size (new pointer after this entry)
        SREG    T4, trapsig_ptr_off+sv_area_off(sp) // store updated pointer back (atomic pre-increment)
        LREG    T3, sig_bgn_off+sv_area_off(sp)    // T3 = M-mode signature begin address
        sub     T1, T1, T3                          // T1 = offset from M-mode sig begin to current ptr
        addi    sp, sp, 1*sv_area_sz               // undo sp adjustment
        LREG    T3, sig_bgn_off+          0(sp)    // T3 = this mode's signature begin address
        add     T1, T1, T3                          // T1 = this mode's current trap sig write address

//---------- Trap Signature Word 0: vect+mode+status ----------
// Packed format:
//   bits  1: 0 = mode (MMODE_SIG=3, SMODE_SIG=1, HMODE_SIG=1, VMODE_SIG=2)
//   bits  5: 2 = entry size in words
//   bits 10: 6 = vector number (compressed from 12*N to 5 bits)
//   bit    11 = xIE[cause] (interrupt enable for this cause)
//   bit    12 = xIP[cause] (interrupt pending for this cause)
//   bits 30:13 = xstatus[17:0] (filtered: XS,FS,VS cleared)

sv_\__MODE__\()vect:
        LREG    T3, xtvec_new_off(sp)              // T3 = actual trampoline table address
        sub     T6, T6, T3                          // T6 = vector stub address - trampoline base = spreader offset
        slli    T4, T6, 1                           // T4 = offset * 2 (part of compression: multiply by 3)
        add     T6, T6, T4                          // T6 = offset * 3
        srli    T6, T6, 5                           // T6 = (offset*3) >> 5 (compress to ~5 bits)
        slli    T6, T6, 6                           // T6 = compressed_vector << 6 (position in bits 10:6)
        or      T6, T6, T2                          // merge entry_size into bits 5:2
        addi    T6, T6, \__MODE__\()MODE_SIG       // merge mode into bits 1:0

        bgez    T5, 1f                              // if exception (MSB=0) -> skip IE/IP extraction
        li      T3, 0xf                             // T3 = mask for cause[3:0]
        and     T3, T5, T3                          // T3 = cause number (low 4 bits)
        csrr    T4, CSR_XIE                         // T4 = xIE register
        srl     T4, T4, T3                          // shift xIE so cause bit is at position 0
        andi    T4, T4, 1                           // T4 = xIE[cause] (0 or 1)
        slli    T4, T4, 11                          // position at bit 11
        or      T6, T6, T4                          // merge xIE bit

        csrr    T4, CSR_XIP                         // T4 = xIP register
        srl     T4, T4, T3                          // shift xIP so cause bit is at position 0
        andi    T4, T4, 1                           // T4 = xIP[cause] (0 or 1)
        slli    T4, T4, 12                          // position at bit 12
        or      T6, T6, T4                          // merge xIP bit

        1:
        csrr    T2, CSR_XSTATUS                     // T2 = xstatus
        slli    T2, T2, XLEN-17                     // shift status[16:0] to MSB area
        srli    T2, T2, XLEN-17-13                  // reposition to bits 30:13
        LI(     T3, 0x219FE5)                       // T3 = filter mask (clears XS, FS, VS, and unused bits)
        xori    T3, T3, -1                           // invert mask
        and     T3, T2, T3                           // apply filter
        or      T3, T6, T3                           // merge with vector+mode+IE+IP bits

// Merge mstatush/hstatus bits for M/H mode traps (MPV, GVA, SPVP)
.ifc \__MODE__ , M
  #if (XLEN==64)
        srli    T4, T4, XLEN-32                     // RV64: align mstatus upper bits to mstatush position
  #else
        csrr    T4, CSR_MSTATUSH                     // RV32: read mstatush directly
  #endif
.else
  .ifc \__MODE__ , H
        csrr    T4, CSR_HSTATUS                      // HS-mode: read hstatus for SPVP, MPV, GVA
  .endif
.endif
        andi    T4, T4, 0x1C0                        // extract bits 8:6 (SPVP?, MPV, GVA)
        slli    T4, T4, 14-6                         // position at bits 16:14
        or      T3, T3, T4                           // merge into word 0
        TRAP_SIGUPD(T4, T3, 0, sv_\__MODE__\()vect, sv_\__MODE__\()vect_str) // write word 0 to trap sig

//---------- Trap Signature Word 1: xcause ----------
sv_\__MODE__\()cause:
        mv      T3, T5                               // T3 = xcause (for TRAP_SIGUPD)
        TRAP_SIGUPD(T4, T3, 1, sv_\__MODE__\()cause, sv_\__MODE__\()cause_str) // write word 1

        bltz    T5, common_\__MODE__\()int_handler   // if MSB=1 -> interrupt -> branch to int handler

//==============================================================================
// EXCEPTION HANDLER (unchanged from original)
// Handles EPC relocation, tval recording, and instruction skipping.
//==============================================================================

common_\__MODE__\()excpt_handler:
        csrr    T3, CSR_XEPC                         // T3 = xEPC (faulting instruction address)
        mv      T4, sp                               // T4 = this mode's save area (for relocation lookup)

// --- EPC relocation logic ---
// Determines whether xEPC needs to be offset-adjusted based on the trapping
// mode's address translation state. If virtual memory is active (xSATP.MODE != bare),
// xEPC is a virtual address and should NOT be relocated. If bare mode, it's a
// physical address and needs relocation relative to code/data/vmem segment starts.

.ifc \__MODE__ , M
 #ifndef S_SUPPORTED
        j       vmem_adj_\__MODE__\()epc            // no S-mode -> always PA, always relocate
 #else
        csrr    T6, CSR_MSTATUS                       // T6 = mstatus
        slli    T2, T6, XLEN-MPRV_LSB-1              // put MPRV bit into MSB
        bgez    T2, 1f                                // MPRV=0 -> use current MPP
        LI(     T6, sved_mpp_off)                     // MPRV=1 -> use saved MPP (from before MPRV was set)
        add     T6, T6, sp
        LREG    T6, 0(T6)                             // T6 = saved mstatus with original MPP

1:      srli    T2, T6,  MPP_LSB                     // extract MPP[1:0]
        andi    T2, T2,  MMODE_SIG                   // T2 = MPP value
        addi    T2, T2, -MMODE_SIG                   // compare to M-mode (3)
        beqz    T2, vmem_adj_\__MODE__\()epc         // MPP=M -> PA -> relocate

        csrr    T2, CSR_SATP                          // check satp.MODE
#ifdef H_SUPPORTED
        csrr    T6, CSR_MISA                          // check misa.H
        slli    T6, T6, XLEN-7-1                     // H bit to MSB
        bgez    T6, 1f                                // no H -> use SATP
        csrr    T2, CSR_HGATP                         // H -> use HGATP instead
1:
#endif
        srli    T2, T2, MODE_LSB                      // extract MODE field
        addi    T4, sp, 1*sv_area_sz                  // T4 -> HS/S mode save area
        bnez    T2, sv_\__MODE__\()epc               // MODE != bare -> VA -> skip relocation

        #if (XLEN==64)
                csrr    T6, CSR_MSTATUS               // check MPV
        #else
                csrr    T6, CSR_MSTATUSH
        #endif
        slli    T2, T6, WDSZ-MPV_LSB-1               // MPV to MSB
        bgez    T2, vmem_adj_\__MODE__\()epc         // MPV=0 -> bare at both levels -> relocate

        csrr    T2, CSR_VSATP                         // check VS-level translation
        srli    T2, T2, MODE_LSB
        LI(     T4, 3*sv_area_sz)                     // VS/VU save area
        add     T4, T4, sp
        bnez    T2, sv_\__MODE__\()epc               // VS MODE != bare -> VA -> skip relocation
  #endif
.endif

 .ifc \__MODE__ ,  H
        csrr    T2, CSR_HGATP                         // check guest address translation
        srli    T2, T2, MODE_LSB
        bnez    T2, sv_\__MODE__\()epc               // VA -> skip
        csrr    T2, CSR_HSTATUS                       // check SPV (second-level)
        slli    T2, T2, XLEN-MPV_LSB-1
        bgez    T2, vmem_adj_\__MODE__\()epc         // no second level -> relocate
        csrr    T2, CSR_VSATP
        srli    T2, T2, MODE_LSB
        LI(     T4, 2*sv_area_sz)
        add     T4, T4, sp
        bnez    T2, sv_\__MODE__\()epc               // VS VA -> skip
.endif

.ifc \__MODE__ ,  S
        csrr    T2, CSR_SATP
        srli    T2, T2, MODE_LSB
        bnez    T2, sv_\__MODE__\()epc               // VA -> skip
.endif

.ifc \__MODE__ ,  V
        csrr    T2, CSR_SATP
        srli    T2, T2, MODE_LSB
        bnez    T2, sv_\__MODE__\()epc
        LREG    T2, sved_hgatp_off(sp)
        srli    T2, T2, MODE_LSB
        bnez    T2, sv_\__MODE__\()epc
  .endif

// --- Offset adjustment for physical addresses ---
vmem_adj_\__MODE__\()epc:
#ifdef SKIP_MEPC
        #ifdef RVMODEL_ACCESS_FAULT_ADDRESS
                LI(     T2, RVMODEL_ACCESS_FAULT_ADDRESS)
                beq     T3, T2, sv_\__MODE__\()epc
                addi    T2, T2, 2
                beq     T3, T2, sv_\__MODE__\()epc
        #endif
#endif
        LREG    T2, vmem_bgn_off(T4)                  // check if EPC is in vmem segment
        LREG    T6, vmem_seg_siz(T4)
        add     T6, T6, T2
        bgeu    T3, T6, code_adj_\__MODE__\()epc
        bgeu    T3, T2,      adj_\__MODE__\()epc

code_adj_\__MODE__\()epc:
        LREG    T2, code_bgn_off(T4)                  // check if EPC is in code segment
        LREG    T6, code_seg_siz(T4)
        add     T6, T6, T2
        bgeu    T3, T6, data_adj_\__MODE__\()epc
        bgeu    T3, T2,      adj_\__MODE__\()epc

data_adj_\__MODE__\()epc:
        LREG    T2, data_bgn_off(T4)                  // check if EPC is in data segment
        LREG    T6, data_seg_siz(T4)
        add     T6, T6, T2
        bgeu    T3, T6, abort_test                    // EPC beyond all known segments -> abort
        bltu    T3, T2, abort_test                    // EPC before data segment -> abort

adj_\__MODE__\()epc:
        sub     T3, T3, T2                            // T3 = EPC - segment_begin (relocated offset)

sv_\__MODE__\()epc:
        TRAP_SIGUPD(T4, T3, 2, sv_\__MODE__\()epc, sv_\__MODE__\()epc_str) // write word 2: xEPC
        csrr    T3, CSR_XEPC                          // re-read xEPC (T3 was modified by relocation)

#ifdef SKIP_MEPC
        LI(     T6, 0xACCE)
        bne     x4, T6, adj_\__MODE__\()epc_rtn
        csrr    T2, CSR_XCAUSE
        LI(     T6, CAUSE_FETCH_PAGE_FAULT)
        beq     T2, T6, 1f
        LI(     T6, CAUSE_FETCH_ACCESS)
        beq     T2, T6, 1f
        LI(     T6, CAUSE_FETCH_GUEST_PAGE_FAULT)
        bne     T2, T6, adj_\__MODE__\()epc_rtn
1:      csrw    CSR_XEPC, ra
        j skp_adj_\__MODE__\()epc
#endif

adj_\__MODE__\()epc_rtn:
        andi    T3, T3, ~WDBYTMSK                    // align EPC to 4-byte boundary
        addi    T3, T3,  2*WDBYTSZ                   // advance past trapping instruction (with padding)
        csrw    CSR_XEPC, T3                          // write adjusted EPC (will resume after the faulting instr)

skp_adj_\__MODE__\()epc:
        csrr    T3, CSR_XTVAL                         // T3 = xtval (trap value: faulting addr or instruction)

sv_\__MODE__\()tval:
        TRAP_SIGUPD(T4, T3, 3, sv_\__MODE__\()tval, sv_\__MODE__\()tval_str) // write word 3: xtval

skp_\__MODE__\()tval:

// --- Hypervisor-specific fields: mtval2 and mtinst (words 4-5) ---
  .ifc \__MODE__ , M
        csrr    T3, CSR_MISA
        slli    T3, T3, XLEN-7-1
        bgez    T3, 1f                                // skip if H not in misa
  .endif
  .ifnc \__MODE__ , S
    .ifnc \__MODE__ , V
      #ifdef H_SUPPORTED
        sv_\__MODE__\()Mtval2:
        csrr    T3, CSR_MTVAL2
        TRAP_SIGUPD(T4, T3, 4, sv_\__MODE__\()Mtval2, sv_Mtval2_str) // write word 4: mtval2
        sv_\__MODE__\()Mtinst:
        csrr    T3, CSR_MTINST
        TRAP_SIGUPD(T4, T3, 5, sv_\__MODE__\()Mtinst, sv_Mtinst_str) // write word 5: mtinst
      #endif
    .endif
  .endif

1:
// --- Check for trap signature overrun ---
chk_\__MODE__\()trapsig_overrun:
        addi    sp, sp, -1*sv_area_sz              // temp adjust sp
        LREG    T4, sv_area_off+trapsig_ptr_off(sp) // T4 = updated trap sig ptr
        LREG    T2, sv_area_off+sig_bgn_off(sp)    // T2 = sig begin
        LREG    T1, sv_area_off+sig_seg_siz(sp)    // T1 = sig size
        addi    sp, sp, 1*sv_area_sz               // undo adjustment

        add     T1, T1, T2                          // T1 = sig end address
        bgtu    T4, T1, abort_test                  // if trap sig ptr > sig end -> overrun -> abort

        li      T2, int_hndlr_tblsz                // T2 = offset to exception dispatch table
        j       spcl_\__MODE__\()handler           // jump to special handler dispatcher

//==============================================================================
// RESTORE AND RETURN
// Restores T1-T6 and sp from the save area, then xret to resume execution.
//==============================================================================

 resto_\__MODE__\()rtn:
        LREG    T1, trap_sv_off+1*REGWIDTH(sp)    // restore T1 (x6)
        LREG    T2, trap_sv_off+2*REGWIDTH(sp)    // restore T2 (x7)
        LREG    T3, trap_sv_off+3*REGWIDTH(sp)    // restore T3 (x8)
        LREG    T4, trap_sv_off+4*REGWIDTH(sp)    // restore T4 (x9)
        LREG    T5, trap_sv_off+5*REGWIDTH(sp)    // restore T5 (x10/a0)
        LREG    T6, trap_sv_off+6*REGWIDTH(sp)    // restore T6 (x11/a1)
        LREG    sp, trap_sv_off+7*REGWIDTH(sp)    // restore original sp (undo xSCRATCH swap)

  .ifc \__MODE__ , M
        mret                                       // return from M-mode trap (uses mepc, restores MPP)
  .else
        sret                                       // return from S/HS/VS-mode trap (uses sepc, restores SPP)
  .endif

//==============================================================================
// INTERRUPT HANDLER
// Clears the interrupt source and records xIP in the trap signature.
//==============================================================================

common_\__MODE__\()int_handler:
        li      T3, 1                               // T3 = 1 (for creating single-bit mask)
        andi    T2, T5, INT_CAUSE_MSK                // T2 = cause[4:0] (interrupt cause index)
        sll     T3, T3, T2                           // T3 = 1 << cause (bit mask for this interrupt)
        csrrc   T4, CSR_XIE, T3                      // read xIE, then clear this interrupt's enable bit
        csrrc   T3, CSR_XIP, T3                      // read xIP, then attempt to clear pending bit

sv_\__MODE__\()ip:
        TRAP_SIGUPD(T4, T3, 2, sv_\__MODE__\()ip, sv_\__MODE__\()ip_str) // write word 2: xIP

        LI(     T2, 0)                               // T2 = 0 (offset for interrupt dispatch table)

//==============================================================================
// SPECIAL HANDLER DISPATCHER
// Indexes into the interrupt or exception dispatch table and jumps to the
// appropriate clearing/handling routine.
//==============================================================================

spcl_\__MODE__\()handler:
        auipc   T3, 0                               // T3 = PC of this instruction
        addi    T3, T3, 15*4                         // T3 = PC + 60 = address of clrint_Xtbl (15 instrs ahead)
        add     T3, T3, T2                           // add int/exception table offset
        slli    T2, T5, 3                            // T2 = cause * 8 (dword-aligned index)
        add     T3, T3, T2                           // T3 = table_base + cause*8
        andi    T3, T3, -8                           // align to dword boundary
        LREG    T3, 0(T3)                            // T3 = dispatch table entry (handler addr or special value)

spcl_\__MODE__\()dispatch_handling:
        beqz    T3, 1f                               // entry==0 -> impossible cause -> abort test
        slli    T2, T3, XLEN-1                       // check LSB by shifting it to MSB
        bge     T2, x0, spcl_\__MODE__\()dispatch   // LSB=0 (even) -> entry is a handler address -> jump to it
        srli    T3, T3,1                             // LSB=1 (odd) -> entry = (cause*2)+1, normalize
        beq     T5, T3, resto_\__MODE__\()rtn        // if cause matches -> default handler (just return)
1:      j       abort_test                           // mismatch or zero -> abort

spcl_\__MODE__\()dispatch:
        jr      T3                                   // jump to handler routine (clr_Msw_int, etc.)

//==============================================================================
// INTERRUPT DISPATCH TABLES
// Two tables of XLEN dword entries each:
//   1. clrint_Xtbl:      interrupt clearing routines (indexed by int cause)
//   2. excpt_Xhndlr_tbl: exception handling routines (indexed by exception cause)
//
// Entry encoding:
//   0:            impossible cause -> abort test
//   odd value:    (cause*2+1) -> default (just return, no special handling)
//   even nonzero: address of handler routine -> jump to it
//==============================================================================

        .align 3                                     // dword-align the dispatch table

clrint_\__MODE__\()tbl:
#if defined(H_SUPPORTED)
        .dword  0                                    // cause  0: reserved -> abort
        .dword  \__MODE__\()clr_Ssw_int              // cause  1: S-mode software interrupt
        .dword  \__MODE__\()clr_Vsw_int              // cause  2: VS-mode software interrupt
        .dword  \__MODE__\()clr_Msw_int              // cause  3: M-mode software interrupt
        .dword  0                                    // cause  4: reserved -> abort
        .dword  \__MODE__\()clr_Stmr_int             // cause  5: S-mode timer interrupt
        .dword  \__MODE__\()clr_Vtmr_int             // cause  6: VS-mode timer interrupt
        .dword  \__MODE__\()clr_Mtmr_int             // cause  7: M-mode timer interrupt
        .dword  0                                    // cause  8: reserved -> abort
        .dword  \__MODE__\()clr_Sext_int             // cause  9: S-mode external interrupt
        .dword  \__MODE__\()clr_Vext_int             // cause 10: VS-mode external interrupt
        .dword  \__MODE__\()clr_Mext_int             // cause 11: M-mode external interrupt
#else
  #if defined(S_SUPPORTED)
        .dword  0                                    // cause  0: reserved
        .dword  \__MODE__\()clr_Ssw_int              // cause  1: S-mode SW int
        .dword  1                                    // cause  2: no VS-mode -> default return
        .dword  \__MODE__\()clr_Msw_int              // cause  3: M-mode SW int
        .dword  0                                    // cause  4: reserved
        .dword  \__MODE__\()clr_Stmr_int             // cause  5: S-mode timer int
        .dword  1                                    // cause  6: no VS-mode -> default return
        .dword  \__MODE__\()clr_Mtmr_int             // cause  7: M-mode timer int
        .dword  0                                    // cause  8: reserved
        .dword  \__MODE__\()clr_Sext_int             // cause  9: S-mode ext int
        .dword  1                                    // cause 10: no VS-mode -> default return
        .dword  \__MODE__\()clr_Mext_int             // cause 11: M-mode ext int
  #else
        .dword  0                                    // cause  0: reserved
        .dword  1                                    // cause  1: no S-mode
        .dword  1                                    // cause  2: no VS-mode
        .dword  \__MODE__\()clr_Msw_int              // cause  3: M-mode SW int
        .dword  0                                    // cause  4: reserved
        .dword  1                                    // cause  5: no S-mode
        .dword  1                                    // cause  6: no VS-mode
        .dword  \__MODE__\()clr_Mtmr_int             // cause  7: M-mode timer int
        .dword  0                                    // cause  8: reserved
        .dword  1                                    // cause  9: no S-mode
        .dword  1                                    // cause 10: no VS-mode
        .dword  \__MODE__\()clr_Mext_int             // cause 11: M-mode ext int
  #endif
#endif

 .rept NUM_SPECD_INTCAUSES-0xC
        .dword  1                                    // causes 12..23: reserved -> default return
 .endr
 .rept XLEN-NUM_SPECD_INTCAUSES
        .dword  0                                    // causes 24+: impossible -> abort
 .endr

excpt_\__MODE__\()hndlr_tbl:
 .set causeidx, 0
 .rept NUM_SPECD_EXCPTCAUSES
        .dword  causeidx*2+1                         // default: (cause*2+1) -> just return
        .set    causeidx, causeidx+1
 .endr
 .rept XLEN-NUM_SPECD_EXCPTCAUSES
        .dword  0                                    // impossible causes -> abort
 .endr

//==============================================================================
// INTERRUPT CLEARING ROUTINES (in .text.rvmodel section)
// Placed in .text.rvmodel so RVMODEL macro size differences between DUT and
// reference don't affect .text.rvtest size.
//==============================================================================

.pushsection .text.rvmodel, "ax"

\__MODE__\()clr_Msw_int:                             // M-mode software interrupt: invoke RVMODEL macro
        RVMODEL_CLR_MSW_INT(T2, T5)
        j       resto_\__MODE__\()rtn

\__MODE__\()clr_Mtmr_int:                            // M-mode timer interrupt: write max to mtimecmp
        li T5, -1
        #ifdef RVMODEL_MTIMECMP_ADDRESS
                la T2, RVMODEL_MTIMECMP_ADDRESS
                SREG T5, 0(T2)
        #endif
        #if __riscv_xlen == 32
                sw T5, 4(T2)
        #endif
        j       resto_\__MODE__\()rtn

\__MODE__\()clr_Mext_int:                            // M-mode external interrupt: clear + save intID
        RVMODEL_CLR_MEXT_INT(T2, T5)
        TRAP_SIGUPD(T4, T3, 3, \__MODE__\()clr_Mext_int, \__MODE__\()clr_Mext_int_str)
        j       resto_\__MODE__\()rtn

\__MODE__\()clr_Ssw_int:                             // S-mode software interrupt
        .ifc \__MODE__ , M
            li T2, 2                                  // SSIP bit
            csrc mip, T2                              // M-mode: clear via mip (sip.SSIP is read-only from M)
            RVMODEL_CLR_SSW_INT(T2, T5)
        .else
                .ifc \__MODE__ , S
                        li T2, 2
                        csrc sip, T2                  // S-mode: clear via sip (writable when delegated)
                        RVMODEL_CLR_SSW_INT(T2, T5)
                .else
                        li T2, 2
                        csrc sip, T2
                        RVMODEL_CLR_SSW_INT(T2, T5)
                .endif
        .endif
        j       resto_\__MODE__\()rtn

\__MODE__\()clr_Stmr_int:                            // S-mode timer interrupt
        .ifc \__MODE__ , M
            RVTEST_CLR_STIMER_INT
        .else
                .ifc \__MODE__ , S
                        RVTEST_CLR_STIMER_INT
                .else
                        RVTEST_CLR_STIMER_INT
                .endif
        .endif
        j       resto_\__MODE__\()rtn

\__MODE__\()clr_Sext_int:                            // S-mode external interrupt: clear + save intID
        RVMODEL_CLR_SEXT_INT(T2, T5)
        TRAP_SIGUPD(T4, T3, 3, \__MODE__\()clr_Sext_int, \__MODE__\()clr_Sext_int_str)
        j       resto_\__MODE__\()rtn

\__MODE__\()clr_Vsw_int:                             // VS-mode software interrupt
        RVMODEL_CLR_VSW_INT
        j       resto_\__MODE__\()rtn

\__MODE__\()clr_Vtmr_int:                            // VS-mode timer interrupt
        RVMODEL_CLR_VTIMER_INT
        j       resto_\__MODE__\()rtn

\__MODE__\()clr_Vext_int:                            // VS-mode external interrupt: clear + save intID
        RVMODEL_CLR_VEXT_INT
        TRAP_SIGUPD(T4, T3, 3, \__MODE__\()clr_Vext_int, \__MODE__\()clr_Vext_int_str)
        j       resto_\__MODE__\()rtn

.popsection                                          // end of .text.rvmodel section

//==============================================================================
// GOTO_MMODE RETURN HANDLER (M-mode only, legacy x3==0 path)
//==============================================================================

.ifc \__MODE__ , M

\__MODE__\()rtn2mmode:
        csrr    T2, CSR_MSTATUS                       // read mstatus to determine caller's mode
        srli    T4, T2,  MPP_LSB                      // extract MPP
        andi    T4, T4,  MMODE_SIG                    // T4 = MPP value
        addi    T3, T4, -MMODE_SIG                    // T3 = 0 if caller was in M-mode
        csrr    T2, CSR_MEPC                           // T2 = mepc (ecall address)
        li      T4, 0                                 // T4 = 0 (relocation offset for M-mode)
        beqz    T3, rtn_fm_mmode                      // if already M-mode -> skip relocation

        addi    sp, sp, sv_area_sz                    // adjust sp to access other save areas

  #if (XLEN==32)
        csrr    T2, CSR_MSTATUSH                      // RV32: check MPV in mstatush
  #else
        csrr    T2, CSR_MSTATUS                        // RV64: MPV in upper mstatus
  #endif
        slli    T2, T2, WDSZ-1-MPV_LSB               // put MPV into MSB
        bgez    T2, from_hs_u                         // MPV=0 -> came from HS or U mode
from_vs:
        addi    sp, sp, sv_area_sz                    // VS: need extra offset
        LREG    T6, code_bgn_off+1*sv_area_sz(sp)    // load VS code_begin
        addi    sp, sp, -sv_area_sz                   // undo extra offset
        j       1f
from_hs_u:
  #ifdef S_SUPPORTED
        LREG    T6, code_bgn_off+0*sv_area_sz(sp)    // load HS/S code_begin
  #else
        LREG    T6, code_bgn_off-1*sv_area_sz(sp)    // M-only: use M-mode's code_begin
  #endif
1:
        csrr    T2, CSR_MEPC                           // re-read mepc
        sub     T2, T2, T6                             // T2 = mepc - caller_code_begin (relative offset)
        addi    sp, sp, -sv_area_sz                    // undo sp adjustment
        LREG    T4, code_bgn_off-0*sv_area_sz(sp)     // T4 = M-mode code_begin

rtn_fm_mmode:
        add     T2, T4, T2                             // T2 = M-mode code_begin + relative offset = return addr

        LREG    T1, trap_sv_off+1*REGWIDTH(sp)        // restore T1
        LREG    T3, trap_sv_off+3*REGWIDTH(sp)        // restore T3
        LREG    T4, trap_sv_off+4*REGWIDTH(sp)        // restore T4
        LREG    T5, trap_sv_off+5*REGWIDTH(sp)        // restore T5/a0
        LREG    T6, trap_sv_off+6*REGWIDTH(sp)        // restore T6/a1
        LREG    sp, trap_sv_off+7*REGWIDTH(sp)        // restore original sp
        jr      4(T2)                                  // jump to ecall+4 in M-mode address space

.endif  // end of M-mode rtn2mmode

//==============================================================================
// GOTO_SMODE RETURN HANDLER (S-mode only, legacy x3==0 path)
//==============================================================================

.ifc \__MODE__ , S

\__MODE__\()rtn2smode:                               // U-mode ecall with x3==0 -> return in S-mode
        csrr    T3, CSR_XEPC                          // T3 = sepc (U-mode ecall address)
        addi    T3, T3, 4                              // skip past ecall
        csrw    CSR_XEPC, T3                           // sepc = ecall_addr + 4
        LI(T3, SSTATUS_SPP)                           // T3 = SPP bit mask
        csrs    CSR_XSTATUS, T3                        // set sstatus.SPP = 1 (sret -> S-mode)
        j       resto_\__MODE__\()rtn                 // restore regs and sret
.endif

.option pop
.endm                                                 // end of RVTEST_TRAP_HANDLER

//==============================================================================
//==============================================================================
//
//  SECTION 19: RVTEST_TRAP_EPILOG
//
//  Per-mode cleanup, run after test completion.
//  Restores xEDELEG, xSATP, xSCRATCH, xTVEC, and any relocated trampoline code.
//
//  Parameters: __MODE__ (M, S, H, or V)
//  Precondition: running in M-mode (entered via GOTO_MMODE at test end)
//  Uses: T1..T6, mscratch to find the correct save area
//
//==============================================================================
//==============================================================================

.macro RVTEST_TRAP_EPILOG __MODE__
.option push
.option norvc

        XCSR_RENAME \__MODE__                     // set CSR aliases for this mode
        LI(T3, actual_tramp_sz)                   // T3 = trampoline size (used as loop bound)

exit_\__MODE__\()cleanup:                         // entry point (also used by abort path)
        csrr  T1, mscratch                        // T1 = M-mode save area base (from mscratch)
      .ifc \__MODE__ , H
        addi T1, T1, 1*sv_area_sz                 // H: offset to HS save area
      .else
        .ifc \__MODE__ , S
          addi T1, T1, 2*sv_area_sz               // S: offset to S save area
        .else
          .ifc \__MODE__ , V
             addi T1, T1, 1*sv_area_sz            // V: offset in two steps (3*sv_area_sz too large)
             addi T1, T1, 2*sv_area_sz            // V: total offset = 3*sv_area_sz
          .endif
        .endif
      .endif

// --- Restore xEDELEG ---
resto_\__MODE__\()edeleg:
        LREG    T2,   xedeleg_sv_off(T1)          // load saved xedeleg
#if (XLEN==32)
        LREG    T4, 4+xedeleg_sv_off(T1)          // RV32: load upper half
#endif
.ifnc \__MODE__ , S
  .ifnc \__MODE__ , V
#ifdef S_SUPPORTED
        csrw    CSR_XEDELEG,  T2                   // restore xedeleg (only for M and H modes)
    .ifc \_MODE__ , M
      #if (XLEN==32)
        csrw    CSR_XEDELEGH, T4                   // RV32 M-mode: restore upper half
      #endif
    .endif
#endif
  .endif
.endif

// --- Restore xSATP ---
resto_\__MODE__\()satp:
        LREG    T2, xsatp_sv_off(T1)              // load saved xsatp
.ifc \__MODE__ , H
        csrw    CSR_HGATP,  T2                     // H: restore hgatp
.else
  .ifc \__MODE__ , S
        csrw    CSR_SATP,   T2                     // S: restore satp
  .endif
        .endif

// --- Restore xSCRATCH ---
resto_\__MODE__\()scratch:
        LREG    T4, xscr_save_off(T1)             // load saved xscratch
        csrw    CSR_XSCRATCH, T4                    // restore xscratch

// --- Restore xTVEC (and original trampoline code if it was overwritten) ---
resto_\__MODE__\()xtvec:
        LREG    T4, xtvec_sav_off(T1)             // T4 = saved original xtvec
        csrrw   T2, CSR_XTVEC, T4                  // restore xtvec, T2 = current xtvec
        andi    T4, T4, ~WDBYTMSK                  // clear mode bits from saved xtvec
        andi    T2, T2, ~WDBYTMSK                  // clear mode bits from current xtvec
        bne     T4, T2, 1f                          // if saved != current -> trampoline wasn't overwritten, skip

resto_\__MODE__\()tramp:                           // trampoline WAS overwritten -> restore original code
        addi    T4, T1, tramp_sv_off               // T4 = saved trampoline code in save area

resto_\__MODE__\()loop:
        lw      T6, 0(T4)                          // read saved original instruction
        sw      T6, 0(T2)                          // write it back to xtvec target
        addi    T2, T2, WDBYTSZ                    // advance target pointer
        addi    T4, T4, WDBYTSZ                    // advance source pointer
        blt     T2, T3, resto_\__MODE__\()loop     // continue until end of trampoline
  1:
        RVMODEL_FENCEI                              // sync icache after restoring code

.global rvtest_\__MODE__\()end                     // make end label globally visible
rvtest_\__MODE__\()end:                            // epilog is done for this mode

#ifdef HANDLER_TESTCODE_ONLY
#endif
 .option pop
 .endm                                             // end of RVTEST_TRAP_EPILOG

//==============================================================================
//==============================================================================
//
//  SECTION 20: RVTEST_TRAP_SAVEAREA
//
//  Allocates and initializes the per-mode save area in the .data section.
//  One copy per supported mode (M, S/HS, VS), instantiated by
//  INSTANTIATE_MODE_MACRO RVTEST_TRAP_SAVEAREA.
//
//  Layout: See SAVE AREA OFFSET DEFINITIONS (Section 8) for the full structure.
//
//  The rvmodel_sv area (8 REGWIDTH entries at offset rvmodel_sv_off) serves
//  dual purpose:
//    1. Scratch space for RVMODEL macros that need temporary storage
//    2. T-SBI CSR_ACCESS scratch: first 8 bytes hold the dynamically-written
//       CSR instruction (4B) + ret instruction (4B)
//  These uses never overlap because RVMODEL macros are not active during SBI calls.
//
//==============================================================================
//==============================================================================

.macro RVTEST_TRAP_SAVEAREA __MODE__

.option push
.option norvc
.global \__MODE__\()tramptbl_sv                    // make save area label global

\__MODE__\()tramptbl_sv:                           // TOP OF SAVE AREA — stored in xSCRATCH
.rept (tramp_sz>>2)                                // trampoline save: space for original code (if xTVEC fixed)
        j       .+0                                // initialized with prototype jump instructions
.endr

\__MODE__\()save_area:                             // start of pointer/metadata section
\__MODE__\()code_bgn_ptr:  .dword rvtest_code_begin                          // code segment begin address
\__MODE__\()code_seg_sz:   .dword rvtest_code_end-rvtest_code_begin          // code segment size
\__MODE__\()data_bgn_ptr:  .dword rvtest_data_begin                          // data segment begin address
\__MODE__\()data_seg_sz:   .dword rvtest_data_end-rvtest_data_begin          // data segment size
\__MODE__\()sig_bgn_ptr:   .dword rvtest_sig_begin                           // signature begin address
\__MODE__\()sig_seg_sz:    .dword rvtest_sig_end-rvtest_sig_begin            // signature segment size
\__MODE__\()vmem_bgn_ptr:  .dword rvtest_code_begin                          // vmem begin (default=code begin)
\__MODE__\()vmem_seg_sz:   .dword rvtest_code_end-rvtest_code_begin          // vmem size (default=code size)

\__MODE__\()trap_sig:      .dword  trap_sigptr                               // current trap signature write ptr
\__MODE__\()satp_sv:       .dword 0                                          // saved xSATP value
\__MODE__\()sved_misa:                             // M-mode: saved misa (when misa.H changes)
\__MODE__\()sved_hgatp:                            // H-mode: saved hgatp (when hgatp.MODE changes)
\__MODE__\()sved_mpp:                              // S-mode: saved MPP (for MPRV tests)
\__MODE__\()unused:        .dword  0                                         // shared/unused slot
\__MODE__\()tentry_sv:     .dword  \__MODE__\()trampoline + actual_tramp_sz  // common entry point addr
\__MODE__\()edeleg_sv:     .dword  0                                         // saved xEDELEG
\__MODE__\()tvec_new:      .dword  0                                         // current xTVEC value (trampoline)
\__MODE__\()tvec_save:     .dword  0                                         // original xTVEC before prolog
\__MODE__\()scratch_save:  .dword  0                                         // original xSCRATCH before prolog
\__MODE__\()trapreg_sv:    .fill   8, REGWIDTH, 0xdeadbeef                   // handler reg save: T1..T6, sp, spare

// rvmodel_sv: scratch area for RVMODEL macros AND T-SBI CSR_ACCESS.
// T-SBI CSR_ACCESS writes a CSR instruction (4B) + ret (4B) to the first 8 bytes,
// then executes it via jalr. See tsbi_Xcsr_access in the HANDLER macro.
\__MODE__\()rvmodel_sv:    .fill   8, REGWIDTH, 0xdeadbeef                   // RVMODEL/T-SBI scratch area
\__MODE__\()sv_area_end:                           // end marker (used for size calculation assertions)

.option pop
.endm                                              // end of RVTEST_TRAP_SAVEAREA
