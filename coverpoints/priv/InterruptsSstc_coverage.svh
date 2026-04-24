///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Covergroups
//
// Written: Corey Hickson chickson@hmc.edu 4 Mar 2025
//
// Copyright (C) 2024 Harvey Mudd College, 10x Engineers, UET Lahore, Habib University
//
// SPDX-License-Identifier: Apache-2.0
//
////////////////////////////////////////////////////////////////////////////////////////////////


`define COVER_INTERRUPTSSSTC


covergroup InterruptsSstc_cg with function sample(ins_t ins);
   option.per_instance = 0;
   `include "general/RISCV_coverage_standard_coverpoints.svh"


   // building blocks for the main coverpoints


   stimecmp_zero: coverpoint ins.current.csr[CSR_STIMECMP] {
       bins zero = {0};
   }
   // mstatus_mie uses ins.prev because the sample instruction is the stimecmp write that
   // triggers the interrupt; hardware clears MIE in ins.current when it takes the trap.
   // Sampling prev captures MIE as it was programmed before the interrupt fires.
   mstatus_mie: coverpoint ins.prev.csr[CSR_MSTATUS][3]  {
       // autofill 0/1
   }
   mstatus_mie_one: coverpoint ins.prev.csr[CSR_MSTATUS][3] {
       bins one = {1};
   }
   // mstatus_sie uses ins.current because SIE is set before the sample nop and is not
   // cleared by hardware until the interrupt is actually taken (which happens after the sample).
   mstatus_sie: coverpoint ins.current.csr[CSR_MSTATUS][1] {
       // autofill 0/1
   }
   mideleg_sti: coverpoint ins.current.csr[CSR_MIDELEG][5] {
       // autofill 0/1
   }
   mideleg_sti_zero: coverpoint ins.current.csr[CSR_MIDELEG][5] {
       bins zero = {0};
   }
   mideleg_sti_one: coverpoint ins.current.csr[CSR_MIDELEG][5] {
       bins one = {1};
   }
   mie_stie: coverpoint ins.current.csr[CSR_MIE][5] {
       // autofill 0/1
   }
   mcounteren_tm: coverpoint ins.current.csr[CSR_MCOUNTEREN][1] {
       // autofill 0/1
   }
   `ifdef XLEN64
       menvcfg_stce: coverpoint ins.current.csr[CSR_MENVCFG][63] {
           // autofill 0/1
       }
       menvcfg_stce_one: coverpoint ins.current.csr[CSR_MENVCFG][63] {
           bins one = {1};
       }
       menvcfg_stce_zero: coverpoint ins.current.csr[CSR_MENVCFG][63] {
           bins zero = {0};
       }
   `else
       menvcfg_stce: coverpoint ins.current.csr[CSR_MENVCFGH][31] {
           // autofill 0/1
       }
       menvcfg_stce_one: coverpoint ins.current.csr[CSR_MENVCFGH][31] {
           bins one = {1};
       }
       menvcfg_stce_zero: coverpoint ins.current.csr[CSR_MENVCFGH][31] {
           bins zero = {0};
       }
   `endif
   csrr: coverpoint ins.current.insn[6:0] {
       bins csrr = {7'b1110011};
   }
   read_stimecmp: coverpoint ins.current.insn[31:20] {
       bins read_stimecmp = {CSR_STIMECMP};
   }
   sip_stip_one: coverpoint ins.current.csr[CSR_SIP][5]{
       bins one = {1};
   }


   // main coverpoints
   cp_machine_sti:     cross priv_mode_m, menvcfg_stce_one, mstatus_mie_one, mideleg_sti, mie_stie, stimecmp_zero;
   cp_machine_tm:      cross priv_mode_m, csrr, read_stimecmp, mcounteren_tm;
   cp_machine_stce:    cross priv_mode_m, csrr, read_stimecmp, menvcfg_stce;


   cp_supervisor_sti_deleg: cross priv_mode_s, menvcfg_stce, mstatus_mie, mstatus_sie, mideleg_sti, mie_stie, stimecmp_zero {
       // When STCE=1, mideleg.STI=0, and STIE=1: stimecmp=0 asserts STIP, and because
       // mideleg.STI=0 the interrupt routes to M-mode. M-mode interrupts preempt S-mode
       // unconditionally (regardless of MIE), so S-mode never reaches the sample instruction
       // with stimecmp=0. When STCE=0 this ignore does not apply because STCE=0 prevents
       // STIP from asserting even when stimecmp=0, allowing S-mode to run normally.
       ignore_bins stce1_nodeleg_stie1 = binsof(menvcfg_stce) intersect {1} &&
                                         binsof(mideleg_sti) intersect {0} &&
                                         binsof(mie_stie) intersect {1};
   }
   cp_supervisor_tm:   cross priv_mode_s, csrr, read_stimecmp, mcounteren_tm;
   cp_supervisor_stce: cross priv_mode_s, csrr, read_stimecmp, menvcfg_stce;


   cp_user_sti:        cross priv_mode_u, menvcfg_stce, mstatus_mie, mstatus_sie, mideleg_sti, mie_stie, sip_stip_one {
       // With Sstc disabled (STCE=0), stimecmp cannot raise STIP; legacy mip.STIP writes
       // are not exercised here, so sip.STIP=1 is unreachable when STCE=0.
       ignore_bins stce_disabled = binsof(menvcfg_stce) intersect {0} && binsof(sip_stip_one) intersect {1};
   }
   cp_user_tm:         cross priv_mode_u, csrr, read_stimecmp, mcounteren_tm;
   cp_user_stce:       cross priv_mode_u, csrr, read_stimecmp, menvcfg_stce;


endgroup


function void interruptssstc_sample(int hart, int issue, ins_t ins);
   InterruptsSstc_cg.sample(ins);
endfunction
