// rvmodel_macros.h
// RVMODEL macro definitions for SERV, the award-winning bit-serial RISC-V CPU,
// in the `servant` reference SoC running under the stock Verilator testbench.
// Written against olofk/serv commit f200eb2ed7b69ac1c6b8eddd47654522aeee5ce8.
// SPDX-License-Identifier: Apache-2.0

#ifndef _RVMODEL_MACROS_H
#define _RVMODEL_MACROS_H

#define RVMODEL_DATA_SECTION

// SERV implements a real, if small, M-mode: mstatus (MIE only, MPP hardwired to 11),
// mie (MTIE only), mcause, and mscratch/mtvec/mepc/mtval in the register file, plus mret.
// The default RVTEST_BOOT_TO_MMODE works unmodified once the configuration declares
// Sm 1.11.0 (no mstatush), no mcountinhibit and no HPM counters, because those are the
// only boot CSRs whose addresses alias onto SERV's real ones.
// Quote: "Bits 26, 22, 21 and 20 are enough to uniquely identify the eight supported CSR regs"
// https://github.com/olofk/serv/blob/f200eb2ed7b69ac1c6b8eddd47654522aeee5ce8/rtl/serv_decode.v#L168
#define STANDARD_SM_SUPPORTED

// #### STARTUP #####

// No custom boot state is needed: there is no memory controller, no cache and no custom CSR.
//#define RVMODEL_BOOT

// Not defined: the default RVTEST_BOOT_TO_MMODE is safe for SERV with this configuration.
// If a future ACT change reintroduces an ungated write to a CSR that aliases onto mtvec,
// mstatus or mscratch, the sanctioned escape hatch is to define this macro here and touch
// only SERV's seven real CSRs, as config/spike/spike-RVI20U32/rvmodel_macros.h documents.
//#define RVMODEL_BOOT_TO_MMODE

// Not defined: SERV raises no access faults.  The Wishbone fabric has no error response and
// servile_mux decodes the entire 32-bit space into RAM, GPIO and timer with no default slave,
// so no address can produce a load or store access fault.
// Quote: "wire \t       ext = (i_wb_cpu_adr[31:30] != 2'b00);"
// https://github.com/olofk/serv/blob/f200eb2ed7b69ac1c6b8eddd47654522aeee5ce8/servile/servile_mux.v#L44
//#define RVMODEL_ACCESS_FAULT_ADDRESS

// #### TERMINATION #####

// servile_mux's simulation hooks.  A write to sim_halt_adr prints "Test complete" and calls
// $finish; a write to sim_sig_adr appends the low byte of the write data to the file named by
// +signature=, which this port uses as the console.  Both are module parameters with these
// defaults, and servant.v does not override them.
// Quote: "parameter [31:0] sim_sig_adr = 32'h80000000,
// parameter [31:0] sim_halt_adr = 32'h90000000)"
// https://github.com/olofk/serv/blob/f200eb2ed7b69ac1c6b8eddd47654522aeee5ce8/servile/servile_mux.v#L10-L11
// Quote: "if (sig_en & (f != 0)) / $fwrite(f, \"%c\", i_wb_cpu_dat[7:0]);
//          else if(halt_en) begin / $display(\"Test complete\"); / $finish;"
// https://github.com/olofk/serv/blob/f200eb2ed7b69ac1c6b8eddd47654522aeee5ce8/servile/servile_mux.v#L83-L87
.EQU SERV_SIG_ADR, 0x80000000
.EQU SERV_HALT_ADR, 0x90000000

// There is only one halt hook and it carries no status, so pass and fail differ only in the
// RVCP-SUMMARY line the test has already printed.  run-serv.sh derives the verdict from that
// line, and treats a run that reaches the +timeout without halting as a failure.
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

// One byte store per character to sim_sig_adr.  Do NOT use servant's bit-banged UART: at one
// bit per 32+ cycles on a bit-serial core, printing a line costs more simulated time than the
// test body.
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

// #### Interrupt Latency #####

// SERV takes 32+ cycles per instruction and samples the timer interrupt once per
// instruction, so a generous window is needed for an enabled interrupt to be observed.
#define RVMODEL_INTERRUPT_LATENCY 100

// #### Machine Timer #####

// Not defined, which disables all machine-timer-interrupt testing.  servant_timer is a single
// 32-bit register that cannot model mtime and mtimecmp separately: a read returns mtime and a
// write sets mtimecmp, at the same address, decoded from adr[31] alone.  It also has no high
// half, and it powers up with mtime == mtimecmp == 0 so o_irq is asserted from the first cycle
// out of reset - enabling mstatus.MIE and mie.MTIE takes an immediate timer interrupt.
// Quote: "if (i_wb_cyc & i_wb_we) / mtimecmp <= i_wb_dat[HIGH:0];
// mtime <= mtime + 'd1; / o_irq <= (mtimeslice - mtimecmp >= 0);"
// https://github.com/olofk/serv/blob/f200eb2ed7b69ac1c6b8eddd47654522aeee5ce8/servant/servant_timer.v#L27-L30
//#define RVMODEL_MTIME_ADDRESS
//#define RVMODEL_MTIMECMP_ADDRESS
#define RVMODEL_TIMER_INT_SOON_DELAY 100

// #### Machine Interrupts #####

// Stubs.  SERV has no software or external interrupt source at all: mie implements MTIE only
// and mcause can report interrupt cause 7 and nothing else.
// Quote: "During an external interrupt the exception code is set to / 7, since SERV only
// support timer interrupts"
// https://github.com/olofk/serv/blob/f200eb2ed7b69ac1c6b8eddd47654522aeee5ce8/rtl/serv_csr.v#L135-L136
#define RVMODEL_SET_MEXT_INT(_R1, _R2)
#define RVMODEL_CLR_MEXT_INT(_R1, _R2)
#define RVMODEL_SET_MSW_INT(_R1, _R2)
#define RVMODEL_CLR_MSW_INT(_R1, _R2)

// #### Supervisor Interrupts #####
// SERV is M-mode only; these can never occur but must be defined.

#define RVMODEL_SET_SEXT_INT(_R1, _R2)
#define RVMODEL_CLR_SEXT_INT(_R1, _R2)
#define RVMODEL_SET_SSW_INT(_R1, _R2)
#define RVMODEL_CLR_SSW_INT(_R1, _R2)

#endif // _RVMODEL_MACROS_H
