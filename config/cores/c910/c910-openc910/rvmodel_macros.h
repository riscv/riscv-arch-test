# rvmodel_macros.h
# RVMODEL macro definitions for the XuanTie OpenC910 in its open-source SoC
# Written against T-head-Semi/openc910 commit b91c90914c19f114d35c8f6b73408eb241ed847c
# Copyright (c) 2026, Harvey Mudd College
# SPDX-License-Identifier: Apache-2.0

#ifndef _RVMODEL_MACROS_H
#define _RVMODEL_MACROS_H

#define RVMODEL_DATA_SECTION

#define STANDARD_SM_SUPPORTED

# Testbench addresses.  All three sit in the strongly-ordered device region
# 0x0100_0000-0x01FF_FFFF, so stores to them are never absorbed by the D-cache.
#   https://github.com/T-head-Semi/openc910/blob/b91c90914c19f114d35c8f6b73408eb241ed847c/C910_RTL_FACTORY/gen_rtl/mmu/rtl/sysmap.h
# C910_CONSOLE is the vendor testbench's character output.
#   https://github.com/T-head-Semi/openc910/blob/b91c90914c19f114d35c8f6b73408eb241ed847c/smart_run/logical/tb/tb_verilator.v#L329-L351
# C910_HALT_PASS / C910_HALT_FAIL are added by the testbench patch in
# .github/scripts/setup-c910.sh.
.EQU C910_CONSOLE,   0x01FFFFF0
.EQU C910_HALT_PASS, 0x01FFFFE0
.EQU C910_HALT_FAIL, 0x01FFFFD0

##### STARTUP #####

# (1) Clear mxstatus.THEADISAEE (bit 22) and mxstatus.MAEE (bit 21), which both reset
#     to 1.  THEADISAEE=1 makes the XuanTie custom instructions in the custom-0 opcode
#     execute instead of raising illegal instruction; MAEE=1 reinterprets Sv39 PTE bits
#     63:59 as XuanTie memory attributes.
#       https://github.com/T-head-Semi/openc910/blob/b91c90914c19f114d35c8f6b73408eb241ed847c/C910_RTL_FACTORY/gen_rtl/cp0/rtl/ct_cp0_regs.v#L2720-L2731
#       https://github.com/T-head-Semi/openc910/blob/b91c90914c19f114d35c8f6b73408eb241ed847c/C910_RTL_FACTORY/gen_rtl/mmu/rtl/ct_mmu_ptw.v#L709-L710
#     mxstatus.CLINTEE (bit 17) also resets to 1 and is left set: it routes the CLINT's
#     supervisor software and timer interrupts into sip/mip.
#       https://github.com/T-head-Semi/openc910/blob/b91c90914c19f114d35c8f6b73408eb241ed847c/C910_RTL_FACTORY/gen_rtl/cp0/rtl/ct_cp0_regs.v#L2116-L2117
#
# (2) Enable the caches and branch prediction, which reset off.  mcor (0x7C2) = 0x70011
#     invalidates the I-cache, D-cache and BTB; mhcr (0x7C1) |= 0x11fb is the setting
#     the user manual (13.1) gives for best performance, 0x11ff, without WA (bit 2).
#     With write-allocate on, fence.i does not make a prior store visible to
#     instruction fetch and Zifencei fails.  The simulation is several times faster.
#define RVMODEL_BOOT                                            \
  li   t0, (1 << 22) | (1 << 21)                               ;\
  csrc 0x7c0, t0        /* mxstatus: THEADISAEE=0, MAEE=0 */   ;\
  li   t0, 0x70011                                             ;\
  csrw 0x7c2, t0        /* mcor: invalidate I$, D$ and BTB */  ;\
  li   t0, 0x11fb                                              ;\
  csrs 0x7c1, t0        /* mhcr: caches and prediction on */   ;

##### TERMINATION #####

# A store to the pass/fail address ends the simulation and writes the verdict into
# run_case.report.
#define RVMODEL_HALT_PASS  \
  li t0, C910_HALT_PASS   ;\
  sw x0, 0(t0)            ;\
  self_loop_pass:         ;\
    j self_loop_pass      ;

#define RVMODEL_HALT_FAIL \
  li t0, C910_HALT_FAIL   ;\
  sw x0, 0(t0)            ;\
  self_loop_fail:         ;\
    j self_loop_fail      ;

##### IO #####

# The testbench prints only word stores (wstrb 0xF in one of the four lanes of the
# 16-byte AXI beat), so each character goes out as an sw.  It samples the write data a
# cycle after the strobes, so a store in the next cycle would replace the character;
# the fence keeps the stores apart.
#   https://github.com/T-head-Semi/openc910/blob/b91c90914c19f114d35c8f6b73408eb241ed847c/smart_run/logical/tb/tb_verilator.v#L288-L351
#define RVMODEL_IO_WRITE_STR(_R1, _R2, _R3, _STR_PTR) \
1:                           ;                        \
  lbu  _R1, 0(_STR_PTR)      ; /* Load byte */        \
  beqz _R1, 3f               ; /* Exit if null */     \
2:                           ;                        \
  li   _R2, C910_CONSOLE     ;                        \
  sw   _R1, 0(_R2)           ;                        \
  fence                      ;                        \
  addi _STR_PTR, _STR_PTR, 1 ; /* Next char */        \
  j 1b                       ; /* Loop */             \
3:

##### Access faults #####

# The SoC's AXI interconnect routes 0x0200_0000-0x0FFF_FFFF to an error responder that
# returns SLVERR.  0x0200_0000 is outside every sail.json memory region too.
#   https://github.com/T-head-Semi/openc910/blob/b91c90914c19f114d35c8f6b73408eb241ed847c/smart_run/logical/axi/axi_interconnect128.v#L362-L363
#define RVMODEL_ACCESS_FAULT_ADDRESS 0x02000000

##### Interrupt Latency #####

#define RVMODEL_INTERRUPT_LATENCY 10
#define RVMODEL_MAX_CYCLES_PER_TIMER_TICK 1

##### Machine Timer #####

# RVMODEL_MTIME_ADDRESS and RVMODEL_MTIMECMP_ADDRESS are undefined.  The CLINT has no
# memory-mapped mtime (only the time CSR reads it), and its mtimecmp at 0xB400_4000 is
# more than 2 GB from the tests, beyond the reach of the LA macro the framework uses
# to access it.
#   https://github.com/T-head-Semi/openc910/blob/b91c90914c19f114d35c8f6b73408eb241ed847c/C910_RTL_FACTORY/gen_rtl/clint/rtl/ct_clint_func.v#L148-L168
#define RVMODEL_TIMER_INT_SOON_DELAY 10000

# The CLINT is at APB base 0xB000_0000 + 0x0400_0000.
#   https://github.com/T-head-Semi/openc910/blob/b91c90914c19f114d35c8f6b73408eb241ed847c/C910_RTL_FACTORY/gen_rtl/ciu/rtl/ct_ciu_apbif.v#L367-L375
#   https://github.com/T-head-Semi/openc910/blob/b91c90914c19f114d35c8f6b73408eb241ed847c/smart_run/logical/tb/tb_verilator.v#L53
#define CLINT_BASE_ADDRESS 0xB4000000

##### Machine Interrupts #####

# RVMODEL_MSIP_ADDRESS is undefined for the same LA-reach reason; these macros reach
# the CLINT's MSIP with li instead.
#define C910_MSIP_ADDRESS (CLINT_BASE_ADDRESS + 0x0)

#define RVMODEL_SET_MSW_INT(_R1, _R2) \
  li _R1, 1                          ;\
  li _R2, C910_MSIP_ADDRESS          ;\
  sw _R1, 0(_R2)                     ;

#define RVMODEL_CLR_MSW_INT(_R1, _R2) \
  li _R2, C910_MSIP_ADDRESS          ;\
  sw x0, 0(_R2)                      ;

##### Supervisor Interrupts #####

# RVMODEL_SET/CLR_SSW_INT are undefined, so the framework raises SSI through mip.SSIP.
# The CLINT's SSIP register rejects writes from U-mode.
#   https://github.com/T-head-Semi/openc910/blob/b91c90914c19f114d35c8f6b73408eb241ed847c/C910_RTL_FACTORY/gen_rtl/clint/rtl/ct_clint_func.v#L216-L217

#endif // _RVMODEL_MACROS_H
