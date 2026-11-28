// rvmodel_macros.h
// RVMODEL macro definitions for BlackParrot (e_bp_unicore_cfg) in its bp_tethered testbench
// Copyright (c) 2026, Harvey Mudd College
// SPDX-License-Identifier: Apache-2.0
//
// Addresses are from black-parrot @ 18bad897633ffd57394746cfc31496e26d20ff0a:
//   host device (bp_nonsynth_host): bp_common/src/include/bp_common_host_pkgdef.svh
//   CLINT: bp_common/src/include/bp_common_clint_pkgdef.svh, bp_me/src/v/dev/bp_me_clint_slice.sv

#ifndef _RVMODEL_MACROS_H
#define _RVMODEL_MACROS_H

// Device addresses, interrupt timings and STANDARD_SM_SUPPORTED are in the
// dut_environment block of the config's UDB yaml. Only the driver library
// (librvmodel.a) is built from this file; test objects never see it.

#define RVMODEL_DATA_SECTION \
        .pushsection .tohost,"aw",@progbits;                \
        .balign 8; .global tohost; tohost: .dword 0;         \
        .balign 8; .global fromhost; fromhost: .dword 0;     \
        .popsection;

// STARTUP //

// The testbench's configuration loader sets the reset PC to DRAM (0x8000_0000) and unfreezes
// the core; no other boot state is needed.
//#define RVMODEL_BOOT

// TERMINATION //

// The host device ends the simulation on a write to the finish register:
//   "else if (finish_w_v_li && ~|data_lo[0+:byte_width_gp]) ... [BSG-PASS] ... $finish;"
//   https://github.com/black-parrot/black-parrot/blob/18bad897633ffd57394746cfc31496e26d20ff0a/bp_top/test/common/bp_nonsynth_host.sv#L107-L119
// finish_base_addr_gp = 0x0_2000 in the host device at 0x0010_0000.
#define BP_HOST_PUTCHAR_ADDR 0x00101000
#define BP_HOST_FINISH_ADDR  0x00102000

#define RVMODEL_HALT_PASS  \
  fence                   ;\
  li t0, BP_HOST_FINISH_ADDR ;\
  sd x0, 0(t0)            ;\
  self_loop_pass:         ;\
    j self_loop_pass      ;\

#define RVMODEL_HALT_FAIL \
  fence                   ;\
  li t0, BP_HOST_FINISH_ADDR ;\
  li x1, 1                ;\
  sd x1, 0(t0)            ;\
  self_loop_fail:         ;\
    j self_loop_fail      ;\

// IO //

// Each byte stored to the putchar register is printed with $write:
//   "else if (putchar_w_v_li) begin $write("%c", data_lo[0+:byte_width_gp]); ..."
//   https://github.com/black-parrot/black-parrot/blob/18bad897633ffd57394746cfc31496e26d20ff0a/bp_top/test/common/bp_nonsynth_host.sv#L92-L96
#define RVMODEL_IO_WRITE_STR(_R1, _R2, _R3, _STR_PTR) \
  li _R2, BP_HOST_PUTCHAR_ADDR ;                       \
1:                           ;                       \
  lbu _R1, 0(_STR_PTR)       ;/* Load byte */        \
  beqz _R1, 2f               ;/* Exit if null */     \
  sb _R1, 0(_R2)             ;                       \
  addi _STR_PTR, _STR_PTR, 1 ;/* Next char */        \
  j 1b                       ;                       \
2:

// Access Fault //

// Interrupt Latency //

// Machine Timer //

#define CLINT_BASE_ADDRESS 0x00300000

// Machine Interrupts //

// The CLINT holds msip at offset 0 and two software-settable external-interrupt bits at
// 0xC000 (M) and 0xC008 (S):
//   "assign m_external_irq_o = plic_r[0]; assign s_external_irq_o = plic_r[1];"
//   https://github.com/black-parrot/black-parrot/blob/18bad897633ffd57394746cfc31496e26d20ff0a/bp_me/src/v/dev/bp_me_clint_slice.sv#L196-L197
#define BP_MEIP_ADDRESS      (CLINT_BASE_ADDRESS + 0xC000)
#define BP_SEIP_ADDRESS      (CLINT_BASE_ADDRESS + 0xC008)

#define RVMODEL_SET_MSW_INT(_R1, _R2) \
  li _R1, 1                   ;\
  li _R2, RVMODEL_MSIP_ADDRESS ;\
  sd _R1, 0(_R2)              ;

#define RVMODEL_CLR_MSW_INT(_R1, _R2) \
  li _R2, RVMODEL_MSIP_ADDRESS ;\
  sd x0, 0(_R2)               ;

#define RVMODEL_SET_MEXT_INT(_R1, _R2) \
  li _R1, 1                   ;\
  li _R2, BP_MEIP_ADDRESS     ;\
  sd _R1, 0(_R2)              ;

#define RVMODEL_CLR_MEXT_INT(_R1, _R2) \
  li _R2, BP_MEIP_ADDRESS     ;\
  sd x0, 0(_R2)               ;

// Supervisor Interrupts //

#define RVMODEL_SET_SEXT_INT(_R1, _R2) \
  li _R1, 1                   ;\
  li _R2, BP_SEIP_ADDRESS     ;\
  sd _R1, 0(_R2)              ;

#define RVMODEL_CLR_SEXT_INT(_R1, _R2) \
  li _R2, BP_SEIP_ADDRESS     ;\
  sd x0, 0(_R2)               ;

// RVMODEL_SET_SSW_INT / RVMODEL_CLR_SSW_INT are left undefined: there is no supervisor software
// interrupt device, so the test environment uses mip.SSIP.

#endif // _RVMODEL_MACROS_H
