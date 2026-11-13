// rvmodel_macros.h
// RVMODEL macro definitions for the LiteX VexRiscv "imac" netlist in the ACT Verilator testbench
// (.github/scripts/vexriscv-tb.cpp). Netlist: pythondata_cpu_vexriscv/verilog/VexRiscv_IMAC.v in
// litex-hub/pythondata-cpu-vexriscv commit 642ecfed1c84460555d6d803d660cc60cfc1ecb6.
// Copyright (c) 2026, Harvey Mudd College
// SPDX-License-Identifier: Apache-2.0

#ifndef _RVMODEL_MACROS_H
#define _RVMODEL_MACROS_H

#define RVMODEL_DATA_SECTION

#define STANDARD_SM_SUPPORTED

// Testbench I/O registers (vexriscv-tb.cpp). The I/O window is uncached: the netlist treats
// every address with bit 31 set as I/O.
.EQU VEX_IO_CONSOLE,     0xF0000000
.EQU VEX_IO_EXIT,        0xF0000004
.EQU VEX_IO_EXTINT,      0xF0000008

##### STARTUP #####

// The netlist routes machine external interrupts through VexRiscv's ExternalInterruptArrayPlugin:
// mip.MEIP is the OR of externalInterruptArray AND a mask in the custom CSR 0xBC0, which resets
// to 0. LiteX's interrupt code sets the mask bit of each source it uses; enable source 0, which
// the testbench drives from VEX_IO_EXTINT.
//   https://github.com/litex-hub/pythondata-cpu-vexriscv/blob/642ecfed1c84460555d6d803d660cc60cfc1ecb6/pythondata_cpu_vexriscv/verilog/src/main/scala/vexriscv/GenCoreDefault.scala#L252-L259
#define RVMODEL_BOOT \
  li   t0, 1                              ;\
  csrw 0xBC0, t0                          ;

// RVMODEL_ACCESS_FAULT_ADDRESS is not defined: no address raises an access fault. The core has
// no PMA or PMP checks, and its Wishbone bridges ignore ERR (rsp.error := False in
// InstructionCache.toWishbone and DataCache.toWishbone), so a bus error is never reported.
//   https://github.com/SpinalHDL/VexRiscv/blob/b6118e5cc2a33323425df6455697139021d50c72/src/main/scala/vexriscv/ip/DataCache.scala#L377
//   https://github.com/SpinalHDL/VexRiscv/blob/b6118e5cc2a33323425df6455697139021d50c72/src/main/scala/vexriscv/ip/InstructionCache.scala#L250

##### TERMINATION #####

// The word written to VEX_IO_EXIT is the testbench's exit status.
#define RVMODEL_HALT_PASS  \
  li t0, VEX_IO_EXIT      ;\
  sw x0, 0(t0)            ;\
  self_loop_pass:         ;\
    j self_loop_pass      ;

#define RVMODEL_HALT_FAIL \
  li t0, VEX_IO_EXIT      ;\
  li t1, 1                ;\
  sw t1, 0(t0)            ;\
  self_loop_fail:         ;\
    j self_loop_fail      ;

##### IO #####

#define RVMODEL_IO_WRITE_STR(_R1, _R2, _R3, _STR_PTR) \
1:                           ;                        \
  lbu  _R1, 0(_STR_PTR)      ; /* Load byte */        \
  beqz _R1, 3f               ; /* Exit if null */     \
  li   _R2, VEX_IO_CONSOLE   ;                        \
  sb   _R1, 0(_R2)           ;                        \
  addi _STR_PTR, _STR_PTR, 1 ; /* Next char */        \
  j 1b                       ; /* Loop */             \
3:

##### Interrupt Latency #####

// mip.MTIP/MSIP/MEIP are registered copies of the inputs, and the testbench updates the inputs
// every cycle, so an interrupt reaches mip within a few cycles of the store that raises it.
#define RVMODEL_INTERRUPT_LATENCY 100

##### Machine Timer #####

// CLINT-style timer in the testbench, at LiteX's CLINT offsets. mtime advances once every 10
// cycles; reading time through the emulation trap handler then takes a few ticks.
#define RVMODEL_MTIME_ADDRESS     0xF001BFF8
#define RVMODEL_MTIMECMP_ADDRESS  0xF0014000
#define RVMODEL_MSIP_ADDRESS      0xF0010000

#define RVMODEL_TIMER_INT_SOON_DELAY 200

##### Machine Interrupts #####

#define RVMODEL_SET_MEXT_INT(_R1, _R2)                                        \
    li _R1, VEX_IO_EXTINT              ;                                      \
    li _R2, 1                          ;                                      \
    sw _R2, 0(_R1)

#define RVMODEL_CLR_MEXT_INT(_R1, _R2)                                        \
    li _R1, VEX_IO_EXTINT              ;                                      \
    sw zero, 0(_R1)

#endif // _RVMODEL_MACROS_H
