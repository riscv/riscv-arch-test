# rvmodel_macros.h
# RVMODEL macro definitions for XiangShan Kunminghu V2 (DefaultConfig, SimTop + difftest emu)
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

# Nothing to program. The reset vector is the simulated flash at 0x1000_0000, whose default
# image sets mnstatus.NMIE, clears mstatus.MDT and jumps to 0x8000_0000.
#   https://github.com/OpenXiangShan/difftest/blob/3729300ae233816d332d057f170472ebe35147b0/src/test/csrc/common/flash.cpp#L64
//#define RVMODEL_BOOT

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
#define RVMODEL_MAX_CYCLES_PER_TIMER_TICK 100

##### Machine Interrupts #####

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

#endif // _RVMODEL_MACROS_H
