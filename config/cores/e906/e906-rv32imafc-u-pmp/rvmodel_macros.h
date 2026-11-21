# rvmodel_macros.h
# RVMODEL macro definitions for the XuanTie OpenE906 in its smart_run SoC testbench
# Written against T-head-Semi/opene906 commit c5b878958e73e0b8f324a8132943f184a7831c07
# Copyright (c) 2026, Harvey Mudd College
# SPDX-License-Identifier: Apache-2.0

#ifndef _RVMODEL_MACROS_H
#define _RVMODEL_MACROS_H

#define RVMODEL_DATA_SECTION

#define STANDARD_SM_SUPPORTED

# The testbench prints the low byte of every store to E906_CONSOLE, and ends the
# simulation when the stored word is 0xFFF (pass) or 0xEEE (fail).
#   https://github.com/T-head-Semi/opene906/blob/c5b878958e73e0b8f324a8132943f184a7831c07/smart_run/logical/tb/tb.v#L210-L248
.EQU E906_CONSOLE,   0x6000FFF8
.EQU E906_HALT_PASS, 0xFFF
.EQU E906_HALT_FAIL, 0xEEE

# Top 4 KB of the 1 MB instruction-bus SRAM, outside the linked image (see link.ld).
.EQU E906_TRAP_VECTOR, 0x000FF000

# XuanTie machine-mode CSRs written by RVMODEL_BOOT.
.EQU CSR_E906_MHCR,  0x7C1
.EQU CSR_E906_MHINT, 0x7C5

##### STARTUP #####

# (1) mtvec resets to 0, the start of the test image, and always reads back MODE = 3,
#     so the trap prolog's write never verifies and the prolog copies its trampoline to
#     the mtvec target instead.  Point mtvec at a 64-byte aligned block outside the
#     image first.
#      https://github.com/T-head-Semi/opene906/blob/c5b878958e73e0b8f324a8132943f184a7831c07/E906_RTL_FACTORY/gen_rtl/cp0/rtl/pa_cp0_trap_csr.v#L624-L644
# (2) mhcr resets to 0: caches, branch prediction, the BTB and the return stack are off.
#     Write 0x103F, the value the vendor startup code (smart_run/tests/lib/crt0.s)
#     writes: IE, DE, WA (write allocate), WB (write back), RS, BPE and BTB on.
#      https://github.com/T-head-Semi/opene906/blob/c5b878958e73e0b8f324a8132943f184a7831c07/E906_RTL_FACTORY/gen_rtl/cp0/rtl/pa_cp0_ext_csr.v#L328-L384
#      https://github.com/T-head-Semi/opene906/blob/c5b878958e73e0b8f324a8132943f184a7831c07/smart_run/tests/lib/crt0.s#L109-L112
# (3) mhint.AEE (bit 20) resets to 0, which makes bus-error access faults imprecise:
#     mepc then holds whatever instruction is in EX when the error returns, not the
#     faulting load or store (user manual 17.6.3).  Set it: load bus errors become
#     precise.  Store bus errors stay imprecise (see Access faults below).
#      https://github.com/T-head-Semi/opene906/blob/c5b878958e73e0b8f324a8132943f184a7831c07/E906_RTL_FACTORY/gen_rtl/cp0/rtl/pa_cp0_ext_csr.v#L388-L413
#define RVMODEL_BOOT              \
  li   t0, E906_TRAP_VECTOR      ;\
  csrw mtvec, t0                 ;\
  li   t0, 0x103F                ;\
  csrw CSR_E906_MHCR, t0         ;\
  li   t0, 0x100000              ;\
  csrs CSR_E906_MHINT, t0        ;

##### TERMINATION #####

#define RVMODEL_HALT_PASS  \
  li t0, E906_CONSOLE     ;\
  li t1, E906_HALT_PASS   ;\
  sw t1, 0(t0)            ;\
  self_loop_pass:         ;\
    j self_loop_pass      ;

#define RVMODEL_HALT_FAIL \
  li t0, E906_CONSOLE     ;\
  li t1, E906_HALT_FAIL   ;\
  sw t1, 0(t0)            ;\
  self_loop_fail:         ;\
    j self_loop_fail      ;

##### IO #####

#define RVMODEL_IO_WRITE_STR(_R1, _R2, _R3, _STR_PTR) \
1:                           ;                        \
  lbu  _R1, 0(_STR_PTR)      ; /* Load byte */        \
  beqz _R1, 3f               ; /* Exit if null */     \
2:                           ;                        \
  li   _R2, E906_CONSOLE     ;                        \
  sb   _R1, 0(_R2)           ;                        \
  addi _STR_PTR, _STR_PTR, 1 ; /* Next char */        \
  j 1b                       ; /* Loop */             \
3:

##### Access faults #####

# The system bus sends every address outside 0x4000_0000-0x4FFF_FFFF (APB peripherals)
# and 0x6000_0000-0x600F_FFFF (SRAM) to an error slave that answers every transfer with
# ERROR.  0x3000_0000 is above the instruction- and data-bus windows
# (0x0000_0000-0x1FFF_FFFF and 0x2000_0000-0x200F_FFFF) and outside every sail.json
# memory region.
#   https://github.com/T-head-Semi/opene906/blob/c5b878958e73e0b8f324a8132943f184a7831c07/smart_run/logical/ahb/ahb.v#L244-L249
#   https://github.com/T-head-Semi/opene906/blob/c5b878958e73e0b8f324a8132943f184a7831c07/smart_run/logical/system/err_gen.v#L77
# Stores and LR/SC are not tested: their bus errors are imprecise access faults even with
# mhint.AEE = 1 (mepc is a later instruction), which the spec allows. AEE only makes loads
# precise.
#   https://github.com/T-head-Semi/opene906/blob/c5b878958e73e0b8f324a8132943f184a7831c07/E906_RTL_FACTORY/gen_rtl/rtu/rtl/pa_rtu_retire.v#L476
#define RVMODEL_ACCESS_FAULT_ADDRESS_LOAD  0x30000000
#define RVMODEL_ACCESS_FAULT_ADDRESS_FETCH 0x30000000
#define RVMODEL_ACCESS_FAULT_ADDRESS_AMO   0x30000000

##### Interrupt Latency #####

#define RVMODEL_INTERRUPT_LATENCY 10

##### Machine Timer #####

# RVMODEL_MTIME_ADDRESS and RVMODEL_MTIMECMP_ADDRESS are undefined.  The CLINT timer
# and software interrupts reach the core only through the CLIC, and in CLIC mode mie and
# mip read 0, so the standard interrupt tests cannot run.
#   https://github.com/T-head-Semi/opene906/blob/c5b878958e73e0b8f324a8132943f184a7831c07/E906_RTL_FACTORY/gen_rtl/cp0/rtl/pa_cp0_trap_csr.v#L614
#define RVMODEL_TIMER_INT_SOON_DELAY 100

#endif // _RVMODEL_MACROS_H
