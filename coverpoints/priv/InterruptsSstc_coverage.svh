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

    stimecmp_zero: coverpoint ins.current.csr[12'h14D] {
        bins zero = {0};
    }
    mstatus_mie: coverpoint ins.prev.csr[12'h300][3]  {
        // autofill 0/1
    }
    mstatus_mie_one: coverpoint ins.prev.csr[12'h300][3] {
        bins one = {1};
    }
    mstatus_sie: coverpoint ins.current.csr[12'h300][1] {
        // autofill 0/1
    }
    mideleg_sti: coverpoint ins.current.csr[12'h303][5] {
        // autofill 0/1
    }
    mideleg_sti_zero: coverpoint ins.current.csr[12'h303][5] {
        bins zero = {0};
    }
    mideleg_sti_one: coverpoint ins.current.csr[12'h303][5] {
        bins one = {1};
    }
    mie_stie: coverpoint ins.current.csr[12'h304][5] {
        // autofill 0/1
    }
    mcounteren_tm: coverpoint ins.current.csr[12'h306][1] {
        // autofill 0/1
    }
    `ifdef XLEN64
        menvcfg_stce: coverpoint ins.current.csr[12'h30A][63] {
            // autofill 0/1
        }
        menvcfg_stce_one: coverpoint ins.current.csr[12'h30A][63] {
            bins one = {1};
        }
        menvcfg_stce_zero: coverpoint ins.current.csr[12'h30A][63] {
            bins zero = {0};
        }
    `else
        menvcfg_stce: coverpoint ins.current.csr[12'h31A][31] {
            // autofill 0/1
        }
        menvcfg_stce_one: coverpoint ins.current.csr[12'h31A][31] {
            bins one = {1};
        }
        menvcfg_stce_zero: coverpoint ins.current.csr[12'h31A][31] {
            bins zero = {0};
        }
    `endif
    csrr: coverpoint ins.current.insn[6:0] {
        bins csrr = {7'b1110011};
    }
    read_stimecmp: coverpoint ins.current.insn[31:20] {
        bins read_stimecmp = {12'h14D};
    }
    sip_stip_one: coverpoint ins.current.csr[12'h144][5]{
        bins one = {1};
    }

    // main coverpoints
    cp_machine_sti:     cross priv_mode_m, menvcfg_stce_one, mstatus_mie_one, mideleg_sti, mie_stie, stimecmp_zero;
    cp_machine_tm:      cross priv_mode_m, csrr, read_stimecmp, mcounteren_tm;
    cp_machine_stce:    cross priv_mode_m, csrr, read_stimecmp, menvcfg_stce;

    cp_supervisor_sti_deleg: cross priv_mode_s, menvcfg_stce, mstatus_mie, mstatus_sie, mideleg_sti, mie_stie, stimecmp_zero {
        // When mideleg.STI=0, the interrupt is not delegated to S-mode, so mie.STIE is irrelevant
        ignore_bins unreachable = binsof(mideleg_sti) intersect {0} && binsof(mie_stie) intersect {1};
    }
    cp_supervisor_tm:   cross priv_mode_s, csrr, read_stimecmp, mcounteren_tm;
    cp_supervisor_stce: cross priv_mode_s, csrr, read_stimecmp, menvcfg_stce;

    cp_user_sti:        cross priv_mode_u, menvcfg_stce, mstatus_mie, mstatus_sie, mideleg_sti, mie_stie, sip_stip_one {
        // If menvcfg.STCE=0, timer doesn't fire so sip.STIP can never be 1
        ignore_bins stce_disabled = binsof(menvcfg_stce) intersect {0} && binsof(sip_stip_one) intersect {1};
        // When mideleg.STI=0, interrupt not delegated to U-mode, so mie.STIE is irrelevant
        ignore_bins no_deleg = binsof(mideleg_sti) intersect {0} && binsof(mie_stie) intersect {1};
        // When MIE=0 and STIE=0, interrupt cannot fire at all so STIP cannot be 1
        ignore_bins all_masked = binsof(mstatus_mie) intersect {0} && binsof(mie_stie) intersect {0} && binsof(sip_stip_one) intersect {1};
        // When MIE=0 and SIE=0, neither M-mode nor S-mode will take interrupt
        ignore_bins both_disabled_timing = binsof(mstatus_mie) intersect {0} && binsof(mstatus_sie) intersect {0} && binsof(sip_stip_one) intersect {1};
    }
    cp_user_tm:         cross priv_mode_u, csrr, read_stimecmp, mcounteren_tm;
    cp_user_stce:       cross priv_mode_u, csrr, read_stimecmp, menvcfg_stce;

endgroup

function void interruptssstc_sample(int hart, int issue, ins_t ins);
    InterruptsSstc_cg.sample(ins);
endfunction
