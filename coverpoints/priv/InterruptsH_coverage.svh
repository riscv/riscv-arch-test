///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Covergroups
//
// Written: Neil Chulani nchulani@g.hmc.edu 30 Oct 2025
//
// Copyright (C) 2025 Harvey Mudd College
//
// SPDX-License-Identifier: Apache-2.0
//
////////////////////////////////////////////////////////////////////////////////////////////////

`define COVER_INTERRUPTSH

covergroup InterruptsH_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "coverage/RISCV_coverage_standard_coverpoints.svh"

    // Hypervisor delegation and enable/pend CSRs
    hideleg_bits: coverpoint `HCSR(12'h603)[15:0] {
        wildcard bins vs_all_zero = {16'b?????0???0???0??};
        wildcard bins vs_all_one  = {16'b?????1???1???1??};
    }
    hie_bits: coverpoint `HCSR(12'h604)[15:0] {
        wildcard bins vs_all_zero = {16'b?????0???0???0??};
        wildcard bins vs_all_one  = {16'b?????1???1???1??};
        bins exact_0444 = {16'h0444};
        bins exact_1444 = {16'h1444};
    }
    hip_bits: coverpoint `HCSR(12'h644)[15:0] {
        wildcard bins vs_all_zero = {16'b?????0???0???0??};
        wildcard bins vs_all_one  = {16'b?????1???1???1??};
        bins exact_0444 = {16'h0444};
    }
    hvip_bits: coverpoint `HCSR(12'h645)[15:0] {
        wildcard bins vs_all_zero = {16'b?????0???0???0??};
        wildcard bins vs_all_one  = {16'b?????1???1???1??};
        bins exact_0444 = {16'h0444};
    }
    mie_bits: coverpoint ins.current.csr[12'h304][15:0] {
        wildcard bins vs_all_zero = {16'b?????0???0???0??};
        wildcard bins vs_all_one  = {16'b?????1???1???1??};
        bins exact_0444 = {16'h0444};
        bins exact_1444 = {16'h1444};
    }
    mip_bits: coverpoint ins.current.csr[12'h344][15:0] {
        wildcard bins vs_all_zero = {16'b?????0???0???0??};
        wildcard bins vs_all_one  = {16'b?????1???1???1??};
        bins exact_0444 = {16'h0444};
    }

    vsie_bits: coverpoint `HCSR(12'h204)[15:0] {
        wildcard bins vs_all_zero = {16'b?????0???0???0??};
        wildcard bins vs_all_one  = {16'b?????1???1???1??};
        bins exact_0444 = {16'h0444};
    }
    vsip_bits: coverpoint `HCSR(12'h244)[15:0] {
        wildcard bins vs_all_zero = {16'b?????0???0???0??};
        wildcard bins vs_all_one  = {16'b?????1???1???1??};
        bins exact_0444 = {16'h0444};
    }

    sstatus_sie:  coverpoint ins.current.csr[12'h100][1] {
        bins zero = {0};
        bins one  = {1};
    }
    vsstatus_sie: coverpoint `HCSR(12'h200)[1] {
        bins zero = {0};
        bins one  = {1};
    }

    // Virtualization enabled indicator (macro-provided expression)
    v_enabled: coverpoint (`V_ENABLED_EXPR) {
        bins zero = {0};
        bins one  = {1};
    }

    // mstatus.MIE bit
    mstatus_mie: coverpoint ins.current.csr[12'h300][3] {
        bins zero = {0};
        bins one  = {1};
    }

    // hstatus.VGEIN (macro-provided slice). Default bins: zero vs nonzero
    hstatus_vgein: coverpoint `HCSR(12'h600)[`HSTATUS_VGEIN_SLICE] {
        bins zero    = {'0};
        bins nonzero = default;
    }

    hie_vssie: coverpoint `HCSR(12'h604)[2] {
        bins zero = {0};
        bins one  = {1};
    }
    hie_vstie: coverpoint `HCSR(12'h604)[6] {
        bins zero = {0};
        bins one  = {1};
    }
    hie_vseie: coverpoint `HCSR(12'h604)[10] {
        bins zero = {0};
        bins one  = {1};
    }

    hip_vssip: coverpoint `HCSR(12'h644)[2] {
        bins zero = {0};
        bins one  = {1};
    }
    hip_vstip: coverpoint `HCSR(12'h644)[6] {
        bins zero = {0};
        bins one  = {1};
    }
    hip_vseip: coverpoint `HCSR(12'h644)[10] {
        bins zero = {0};
        bins one  = {1};
    }
    hvip_vssip: coverpoint `HCSR(12'h645)[2] {
        bins zero = {0};
        bins one  = {1};
    }
    hvip_vstip: coverpoint `HCSR(12'h645)[6] {
        bins zero = {0};
        bins one  = {1};
    }
    hvip_vseip: coverpoint `HCSR(12'h645)[10] {
        bins zero = {0};
        bins one  = {1};
    }

    hgeie_any: coverpoint `HCSR(12'h607)[15:0] {
        bins zero = {16'h0000};
        wildcard bins any_nonzero = {16'b???????????????1,
                                     16'b??????????????1?,
                                     16'b?????????????1??,
                                     16'b????????????1???,
                                     16'b???????????1????,
                                     16'b??????????1?????,
                                     16'b?????????1??????,
                                     16'b????????1???????,
                                     16'b???????1????????,
                                     16'b??????1?????????,
                                     16'b?????1??????????,
                                     16'b????1???????????,
                                     16'b???1????????????,
                                     16'b??1?????????????,
                                     16'b?1??????????????,
                                     16'b1???????????????};
    }
    hgeip_any: coverpoint `HCSR(12'he12)[15:0] {
        bins zero = {16'h0000};
        wildcard bins any_nonzero = {16'b???????????????1,
                                     16'b??????????????1?,
                                     16'b?????????????1??,
                                     16'b????????????1???,
                                     16'b???????????1????,
                                     16'b??????????1?????,
                                     16'b?????????1??????,
                                     16'b????????1???????,
                                     16'b???????1????????,
                                     16'b??????1?????????,
                                     16'b?????1??????????,
                                     16'b????1???????????,
                                     16'b???1????????????,
                                     16'b??1?????????????,
                                     16'b?1??????????????,
                                     16'b1???????????????};
    }

    mideleg_bits: coverpoint ins.current.csr[12'h303][15:0] {
        wildcard bins vs_bits_one      = {16'b?????1???1???1??};
        wildcard bins vs_bits_zero     = {16'b?????0???0???0??};
        bins exact_0444                = {16'h0444};
    }

    hie_vsi_walking: coverpoint {`HCSR(12'h604)[10],
                                 `HCSR(12'h604)[6],
                                 `HCSR(12'h604)[2]} {
        bins vsei = {3'b100};
        bins vsti = {3'b010};
        bins vssi = {3'b001};
    }
    hip_vsi_walking: coverpoint {`HCSR(12'h644)[10],
                                 `HCSR(12'h644)[6],
                                 `HCSR(12'h644)[2]} {
        bins vsei = {3'b100};
        bins vsti = {3'b010};
        bins vssi = {3'b001};
    }

    cp_mideleg: coverpoint ins.current.csr[12'h303][15:0] {
        wildcard bins vsi_ro1      = {16'b?????1???1???1??};
        wildcard bins vsi_ro1_gei  = {16'b???1?1???1???1??};
    }

    // Following tests are done in M-mode
    cp_mie: cross mie_bits, hie_bits {
    }

    cp_mip: cross mip_bits, hip_bits {
    }

    cp_nohint_m: cross priv_mode_m, mstatus_mie, hideleg_bits, mie_bits, mip_bits {
    }

    // Following tests are done in M-mode if GILEN > 0
    cp_mie_gilen: cross mie_bits, hgeie_any {
    }
    cp_mip_gilen: cross mip_bits, hgeip_any {
    }

    // Following tests are done in HS-mode
    cp_trigger_vsei: cross priv_mode_s, sstatus_sie, hideleg_bits, hie_vseie, hvip_vseip {
    }
    cp_trigger_vsti: cross priv_mode_s, sstatus_sie, hideleg_bits, hie_vstie, hvip_vstip {
    }
    cp_trigger_vssi: cross priv_mode_s, sstatus_sie, hideleg_bits, hie_vssie, hvip_vssip {
    }

    cp_hip_write: cross hip_vssip, hvip_vssip {
    }

    cp_priority_en_vsi: cross priv_mode_s, sstatus_sie, hideleg_bits, hie_vsi_walking, hip_vsi_walking {
    }

    cp_priority_deleg_vsi: cross priv_mode_s, sstatus_sie, hideleg_bits, hip_vsi_walking {
    }

    cp_priority_s: cross priv_mode_s, sstatus_sie, hideleg_bits, hie_bits, hvip_bits, hip_vsi_walking, sip_walking, sie_ones {
    }

    cp_hie: cross hie_bits, mie_bits {
    }

    cp_hip: cross hip_bits, mip_bits {
    }

    cp_hideleg: coverpoint ins.current.csr[12'h603][15:0] {
        bins mask_444 = {16'h0444};
    }

    cp_vsie: cross hideleg_bits, hie_bits, vsie_bits {
    }

    cp_vsip: cross hideleg_bits, hip_bits, vsip_bits {
    }

    cp_vsie_from_hie: cross hideleg_bits, vsie_bits, hie_bits {
    }

    // Following tests are done in HS-mode if GILEN > 0
    cp_hie_gilen: cross hie_bits, mie_bits, hgeie_any {
    }
    cp_priority_sgei: cross priv_mode_s, sstatus_sie, hgeip_any, hgeie_any, hvip_bits, hideleg_bits, hie_bits {
    }
    cp_priority_sgei_s: cross priv_mode_s, sstatus_sie, hideleg_bits, hvip_bits, hie_bits, hgeip_any, hgeie_any, hip_bits, sie_ones, sip_walking {
    }
    cp_trigger_sgei: cross priv_mode_s, sstatus_sie, hgeip_any, hgeie_any, hie_bits {
    }
    cp_hgeie: cross hgeip_any, hgeie_any {
    }
    // Model VGEIN selection effect generically via hvip/hip and hgeip_any; explicit per-index bins depend on GEILEN
    cp_trigger_vsei_hgeip: cross sstatus_sie, hvip_bits, hideleg_bits, hie_bits, hgeip_any, hstatus_vgein {
    }
    cp_hgeip0: cross sstatus_sie, hvip_bits, hideleg_bits, hie_bits, hgeip_any, hgeie_any, hstatus_vgein {
        bins select_zero = binsof(hstatus_vgein.zero);
    }

    // Following tests are done in VS-mode
    cp_hideleg_hip_vs: cross v_enabled, hideleg_bits, hip_bits, hie_bits, vsstatus_sie {
    }
    cp_hideleg_hie_vs: cross v_enabled, hideleg_bits, hie_bits, hip_bits, vsstatus_sie {
    }
    cp_hip_hie_vs: cross v_enabled, hip_bits, hie_bits, hideleg_bits, vsstatus_sie {
    }
    cp_sie_vs: cross v_enabled, hideleg_bits, hip_bits, hie_bits, vsstatus_sie {
    }
    cp_mideleg_mip_vs: cross v_enabled, mstatus_mie, mideleg_bits, mip_bits, vsstatus_sie, mie_bits {
    }
    // Interrupt recording CSRs on interrupt entry
    cp_mtinst: coverpoint ins.current.csr[12'h34a][31:0] {
        bins zero = {32'h00000000};
    }
    cp_htinst: coverpoint ins.current.csr[12'h64a][31:0] {
        bins zero = {32'h00000000};
    }

    // Following tests are done in VU-mode
    cp_hideleg_hip_vu: cross v_enabled, hideleg_bits, hip_bits, hie_bits {
    }
    cp_hideleg_hie_vu: cross v_enabled, hideleg_bits, hie_bits, hip_bits {
    }
    cp_hip_hie_vu: cross v_enabled, hip_bits, hie_bits, hideleg_bits {
    }
    cp_mideleg_mip_vu: cross v_enabled, mstatus_mie, mideleg_bits, mip_bits, mie_bits {
    }

    // Following tests are done in U-mode
    cp_vsint_disabled_u: cross hideleg_bits, hip_bits, hie_bits, priv_mode_u {
    }
endgroup

function void interruptsh_sample(int hart, int issue, ins_t ins);
    InterruptsH_cg.sample(ins);
endfunction


