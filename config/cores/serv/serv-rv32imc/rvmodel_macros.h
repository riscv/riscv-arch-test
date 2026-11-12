// rvmodel_macros.h
// RVMODEL macro definitions for SERV in the servant SoC under the stock Verilator testbench,
// olofk/serv commit f200eb2ed7b69ac1c6b8eddd47654522aeee5ce8.
// Copyright (c) 2026, Harvey Mudd College
// SPDX-License-Identifier: Apache-2.0

#ifndef _RVMODEL_MACROS_H
#define _RVMODEL_MACROS_H

// Device addresses, interrupt timings and STANDARD_SM_SUPPORTED are in the
// dut_environment block of the config's UDB yaml. Only the driver library
// (librvmodel.a) is built from this file; test objects never see it.

#define RVMODEL_DATA_SECTION

// The default RVTEST_BOOT_TO_MMODE, limited to the CSRs SERV implements.  SERV decodes a CSR
// address from instruction bits 26, 22, 21 and 20 only, so the default boot's writes to
// mhpmevent3..31 land on mtvec, mstatus, mie and mcause, and zeroing mtvec breaks every trap.
// https://github.com/olofk/serv/blob/f200eb2ed7b69ac1c6b8eddd47654522aeee5ce8/rtl/serv_decode.v#L168-L202
#define RVMODEL_BOOT_TO_MMODE          \
  rvtest_boot_to_mmode:               ;\
  csrw mie, zero                      ;\
  csrw mip, zero                      ;\
  csrw mepc, zero                     ;\
  csrw mtval, zero                    ;\
  csrw mcause, zero                   ;\
  RVTEST_TRAP_PROLOG M                ;\
  rvtest_boot_to_mmode_csr_init:      ;\
  LI(t0, MSTATUS_MPP)                 ;\
  csrw mstatus, t0

// #### TERMINATION #####

// servile_mux simulation hooks: a store to 0x9000_0000 prints "Test complete" and calls $finish;
// a byte stored to 0x8000_0000 is appended to the +signature= file, used here as the console.
// https://github.com/olofk/serv/blob/f200eb2ed7b69ac1c6b8eddd47654522aeee5ce8/servile/servile_mux.v#L10-L11
.EQU SERV_SIG_ADR, 0x80000000
.EQU SERV_HALT_ADR, 0x90000000

// The halt hook carries no status; run-serv.sh takes the verdict from the RVCP-SUMMARY line.
#define RVMODEL_HALT_PASS \
  li t0, SERV_HALT_ADR    ;\
  sw t0, 0(t0)            ;\
  self_loop_pass:         ;\
    j self_loop_pass      ;

#define RVMODEL_HALT_FAIL \
  li t0, SERV_HALT_ADR    ;\
  sw t0, 0(t0)            ;\
  self_loop_fail:         ;\
    j self_loop_fail      ;

// #### IO #####

#define RVMODEL_IO_WRITE_STR(_R1, _R2, _R3, _STR_PTR) \
1:                           ;                        \
  lbu  _R1, 0(_STR_PTR)      ; /* Load byte */        \
  beqz _R1, 3f               ; /* Exit if null */     \
2:                           ;                        \
  li   _R2, SERV_SIG_ADR     ;                        \
  sb   _R1, 0(_R2)           ;                        \
  addi _STR_PTR, _STR_PTR, 1 ; /* Next char */        \
  j 1b                       ; /* Loop */             \
3:

// #### Interrupts #####

#endif // _RVMODEL_MACROS_H
