# rvmodel_macros.h
# RVMODEL macro definitions for XiangShan Kunminghu V2 (KunminghuV2Config, SimTop difftest emulator)
# Written against OpenXiangShan/XiangShan @ e7bab53e66dfb3c4a1d11cf9519b0396f8576cae
#   (branch kunminghu-v2) with its difftest submodule @ 3729300ae233816d332d057f170472ebe35147b0
# SPDX-License-Identifier: Apache-2.0

#ifndef _RVMODEL_MACROS_H
#define _RVMODEL_MACROS_H

# No HTIF. The simulation ends on XiangShan's trap instruction, so there is no .tohost section.
#define RVMODEL_DATA_SECTION

#define STANDARD_SM_SUPPORTED

# Simulation memory map (SimTop): the UART-lite at 0x4060_0000, the interrupt generator at
# 0x4007_0000, the CLINT-style timer at 0x3800_0000 and the PLIC at 0x3C00_0000.
#   https://github.com/OpenXiangShan/XiangShan/blob/e7bab53e66dfb3c4a1d11cf9519b0396f8576cae/src/test/scala/top/SimMMIO.scala#L44
#   https://github.com/OpenXiangShan/XiangShan/blob/e7bab53e66dfb3c4a1d11cf9519b0396f8576cae/src/main/scala/system/SoC.scala#L77
.EQU XS_UART_TX, 0x40600004
.EQU XS_INTRGEN, 0x40070000
.EQU XS_CLINT, 0x38000000
.EQU XS_PLIC, 0x3C000000

##### STARTUP #####

# The reset vector is the simulated flash at 0x1000_0000, whose default image sets
# mnstatus.NMIE, clears mstatus.MDT and jumps to 0x8000_0000.
#   https://github.com/OpenXiangShan/difftest/blob/3729300ae233816d332d057f170472ebe35147b0/src/test/csrc/common/flash.cpp#L64
# RVMODEL_BOOT only enables the IMSIC guest interrupt files (see Guest External Interrupts below).

##### TERMINATION #####

# XiangShan's simulation trap is the custom-2 encoding 0x0000006b with rs1 = code; the emulator
# reports HIT GOOD TRAP for code 0 and HIT BAD TRAP for code 1.
#   Quote: def TRAP = BitPat("b000000000000?????000000001101011")
#   https://github.com/OpenXiangShan/XiangShan/blob/e7bab53e66dfb3c4a1d11cf9519b0396f8576cae/src/main/scala/xiangshan/backend/decode/DecodeUnit.scala#L564
#define RVMODEL_HALT_PASS   \
  li a0, 0                 ;\
  .word 0x0005006b         ;\
  self_loop_pass:          ;\
    j self_loop_pass       ;

#define RVMODEL_HALT_FAIL   \
  li a0, 1                 ;\
  .word 0x0005006b         ;\
  self_loop_fail:          ;\
    j self_loop_fail       ;

##### IO #####

# A byte store to UART-lite offset 4 is written to the emulator's stdout. There is no status
# register to poll and no initialisation.
#   https://github.com/OpenXiangShan/XiangShan/blob/e7bab53e66dfb3c4a1d11cf9519b0396f8576cae/src/main/scala/device/AXI4UART.scala#L37
#define RVMODEL_IO_WRITE_STR(_R1, _R2, _R3, _STR_PTR) \
1:                           ;                        \
  lbu  _R1, 0(_STR_PTR)      ;                        \
  beqz _R1, 3f               ;                        \
  li   _R2, XS_UART_TX       ;                        \
  sb   _R1, 0(_R2)           ;                        \
  addi _STR_PTR, _STR_PTR, 1 ;                        \
  j 1b                       ;                        \
3:

##### Access Fault #####

# [0x3900_2000, 0x3A00_0000) has no read, write or execute permission in the PMA table, so
# every access raises an access fault in the core without reaching the bus.
#   https://github.com/OpenXiangShan/XiangShan/blob/e7bab53e66dfb3c4a1d11cf9519b0396f8576cae/src/main/scala/system/SoC.scala#L65
#define RVMODEL_ACCESS_FAULT_ADDRESS 0x39800000

##### Machine Timer #####

#define RVMODEL_MTIME_ADDRESS    (XS_CLINT + 0xBFF8)
#define RVMODEL_MTIMECMP_ADDRESS (XS_CLINT + 0x4000)
#define RVMODEL_MSIP_ADDRESS     (XS_CLINT + 0x0)

##### Interrupt Latency #####

#define RVMODEL_INTERRUPT_LATENCY 2000
#define RVMODEL_TIMER_INT_SOON_DELAY 100

##### Machine Interrupts #####

# The hart implements Smaia/Ssaia, but in SimTop a load or store to an IMSIC interrupt file (the
# M-level file at 0x3A80_0000) never completes (the AIA/IMSIC integration is in XSNoCTop, not the
# SimTop used for simulation). The PLIC still drives mip.MEIP, so machine external interrupts
# go through the PLIC, and guest external interrupts are raised through the IMSIC CSRs.
#   https://github.com/OpenXiangShan/XiangShan/issues/6366
# External interrupts: interrupt-generator bit 0 drives PLIC source 1. Context 0 is hart 0 M-mode.
# The generator applies a nonzero write after 1000 cycles and a zero write immediately.
#   https://github.com/OpenXiangShan/XiangShan/blob/e7bab53e66dfb3c4a1d11cf9519b0396f8576cae/src/main/scala/device/AXI4IntrGenerator.scala#L60
#define RVMODEL_SET_MEXT_INT(_R1, _R2)   \
  li _R2, XS_PLIC                       ;\
  li _R1, 7                             ;\
  sw _R1, 4(_R2)                        ;\
  li _R2, XS_PLIC + 0x200000            ;\
  sw zero, 0(_R2)                       ;\
  li _R2, XS_PLIC + 0x2000              ;\
  li _R1, 2                             ;\
  sw _R1, 0(_R2)                        ;\
  li _R2, XS_INTRGEN                    ;\
  li _R1, 1                             ;\
  sw _R1, 0(_R2)                        ;

#define RVMODEL_CLR_MEXT_INT(_R1, _R2)   \
  li _R2, XS_INTRGEN                    ;\
  sw zero, 0(_R2)                       ;\
  li _R2, XS_PLIC + 0x200004            ;\
  lw _R1, 0(_R2)                        ;\
  sw _R1, 0(_R2)                        ;\
  li _R2, XS_PLIC + 0x2000              ;\
  sw zero, 0(_R2)                       ;

#define RVMODEL_SET_MSW_INT(_R1, _R2)    \
  li _R2, RVMODEL_MSIP_ADDRESS          ;\
  li _R1, 1                             ;\
  sw _R1, 0(_R2)                        ;

#define RVMODEL_CLR_MSW_INT(_R1, _R2)    \
  li _R2, RVMODEL_MSIP_ADDRESS          ;\
  sw zero, 0(_R2)                       ;

##### Supervisor Interrupts #####

# Left undefined: the trap handler raises and clears supervisor software and external
# interrupts through mip.SSIP and mip.SEIP.

##### Guest External Interrupts #####

# The IMSIC guest interrupt files are reached through vsiselect and vsireg, with hstatus.VGEIN
# selecting the file, so no MMIO access is needed. GEILEN is 7. Setting identity XS_IMSIC_EIID
# in a file's eip0 register (indirect register 0x80) makes it pending, which makes hgeip bit
# VGEIN read 1 once RVMODEL_BOOT has enabled that identity (eidelivery, eithreshold, eie0).
#define XS_IMSIC_GEILEN       7
#define XS_IMSIC_EIID         1
#define XS_IMSIC_EIDELIVERY   0x70  /* indirect register numbers, AIA section 3.8 */
#define XS_IMSIC_EITHRESHOLD  0x72
#define XS_IMSIC_EIP0         0x80
#define XS_IMSIC_EIE0         0xC0

#define RVMODEL_BOOT                                                     \
  csrr t2, hstatus                                                      ;\
  li t3, 1                                                              ;\
  1: slli t0, t3, 12; csrw hstatus, t0                                  ;\
  li t0, XS_IMSIC_EIDELIVERY;  csrw vsiselect, t0; li t1, 1; csrw vsireg, t1 ;\
  li t0, XS_IMSIC_EITHRESHOLD; csrw vsiselect, t0; csrw vsireg, zero    ;\
  li t0, XS_IMSIC_EIE0;        csrw vsiselect, t0                       ;\
  li t1, 1 << XS_IMSIC_EIID;   csrs vsireg, t1                          ;\
  addi t3, t3, 1; li t0, XS_IMSIC_GEILEN; bleu t3, t0, 1b               ;\
  csrw hstatus, t2                                                      ;

# Guest external interrupt _GEI (a register, 1 to GEILEN): set or clear identity XS_IMSIC_EIID in
# eip0 of guest file _GEI, then restore hstatus. The _M flavors reach the CSRs directly and also
# restore vsiselect. The others run in any mode and go through T-SBI, which takes its operands in
# a1 and a2 and returns in a0 (the framework passes _GEI, _R1 and _R2 in a0, a1 and a2); they
# leave vsiselect selecting eip0.
#define XS_GUEST_EIP0_M(_OP, _GEI, _R1, _R2)  \
  csrr _R1, hstatus                          ;\
  li _R2, HSTATUS_VGEIN                      ;\
  csrc hstatus, _R2                          ;\
  slli _R2, _GEI, 12                         ;\
  csrs hstatus, _R2                          ;\
  csrr _GEI, vsiselect                       ;\
  li _R2, XS_IMSIC_EIP0                      ;\
  csrw vsiselect, _R2                        ;\
  li _R2, 1 << XS_IMSIC_EIID                 ;\
  _OP vsireg, _R2                            ;\
  csrw vsiselect, _GEI                       ;\
  csrw hstatus, _R1                          ;

#define XS_GUEST_EIP0(_TSBI_OP, _GEI)                              \
  slli a2, _GEI, 12        /* a2 = _GEI in the VGEIN field */     ;\
  RVTEST_TSBI_CSR_READ(CSR_HSTATUS)  /* a0 = hstatus */           ;\
  li a1, ~HSTATUS_VGEIN                                           ;\
  and a1, a0, a1                                                  ;\
  or a1, a1, a2            /* a1 = hstatus with VGEIN = _GEI */   ;\
  mv a2, a0                /* a2 = hstatus to restore */          ;\
  RVTEST_TSBI_CSR_WRITE_A1(CSR_HSTATUS)                           ;\
  RVTEST_TSBI_CSR_WRITE(CSR_VSISELECT, XS_IMSIC_EIP0)             ;\
  _TSBI_OP(CSR_VSIREG, 1 << XS_IMSIC_EIID)                        ;\
  mv a1, a2                                                       ;\
  RVTEST_TSBI_CSR_WRITE_A1(CSR_HSTATUS)                           ;

#define RVMODEL_SET_GUEST_EXT_INT_M(_GEI, _R1, _R2) XS_GUEST_EIP0_M(csrs, _GEI, _R1, _R2)
#define RVMODEL_CLR_GUEST_EXT_INT_M(_GEI, _R1, _R2) XS_GUEST_EIP0_M(csrc, _GEI, _R1, _R2)
#define RVMODEL_SET_GUEST_EXT_INT(_GEI, _R1, _R2)   XS_GUEST_EIP0(RVTEST_TSBI_CSR_SET, _GEI)
#define RVMODEL_CLR_GUEST_EXT_INT(_GEI, _R1, _R2)   XS_GUEST_EIP0(RVTEST_TSBI_CSR_CLEAR, _GEI)

##### Sscofpmf #####

# mhpmcounter3-10 count frontend events, 11-18 backend, 19-26 MemBlock and 27-31 L2
# (NewCSR/NewCSR.scala:1293-1296). mhpmevent[9:0] selects the first event of the counter's set,
# and the zero op fields OR it with the empty event 0 (utility/HardwarePerfMonitor.scala:52-74).
# Backend event 55 is rob_commitInstrLoad, a committed load (backend/Backend.scala:939-955; the
# index is printed as "backend perfEvents Set" during elaboration). The Sail reference counts
# EV_FENCE for the same selector (sail.json) and triggers it with a fence (sail_macros.h).
#define RVMODEL_HPM_COUNTER 11
#define RVMODEL_MHPMEVENT_VAL 55
#define RVMODEL_MHPMEVENT_CODE(_R1, _R2) \
    lw _R2, 0(_R1)

#endif // _RVMODEL_MACROS_H
