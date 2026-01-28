///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Standard Covergroups
//
// Written: Jordan Carlin jcarlin@hmc.edu 6 March 2025
//
// Copyright (C) 2024 Harvey Mudd College, 10x Engineers, UET Lahore
//
// SPDX-License-Identifier: Apache-2.0
//
////////////////////////////////////////////////////////////////////////////////////////////////

  // Privilege mode coverpoints
  // Uses ins.prev to check mode at end of previous instruction,
  // which is the mode the current instruction begins execution in
  priv_mode_m: coverpoint {ins.prev.mode_virt, ins.prev.mode} {
    type_option.weight = 0;
    bins M_mode = {3'b011};
  }
  // priv_mode_s and priv_mode_hs are the same, both names are available for clarity when writing crosses
  priv_mode_s: coverpoint {ins.prev.mode_virt, ins.prev.mode} {
    type_option.weight = 0;
    bins S_mode = {3'b001};
  }
  priv_mode_hs: coverpoint {ins.prev.mode_virt, ins.prev.mode} {
    type_option.weight = 0;
    bins HS_mode = {3'b001};
  }
  priv_mode_vs: coverpoint {ins.prev.mode_virt, ins.prev.mode} {
    type_option.weight = 0;
    bins VS_mode = {3'b101};
  }
  priv_mode_u: coverpoint {ins.prev.mode_virt, ins.prev.mode} {
    type_option.weight = 0;
    bins U_mode = {3'b000};
  }
  priv_mode_vu: coverpoint {ins.prev.mode_virt, ins.prev.mode} {
    type_option.weight = 0;
    bins VU_mode = {3'b100};
  }


  priv_mode_m_s: coverpoint {ins.prev.mode_virt, ins.prev.mode} {
    type_option.weight = 0;
    bins M_mode = {3'b011};
    bins S_mode = {3'b001};
  }
  priv_mode_m_vs: coverpoint {ins.prev.mode_virt, ins.prev.mode} {
    type_option.weight = 0;
    bins M_mode = {3'b011};
    bins VS_mode = {3'b101};
  }
  priv_mode_m_u: coverpoint {ins.prev.mode_virt, ins.prev.mode} {
    type_option.weight = 0;
    bins M_mode = {3'b011};
    bins U_mode = {3'b000};
  }
  priv_mode_m_vu: coverpoint {ins.prev.mode_virt, ins.prev.mode} {
    type_option.weight = 0;
    bins M_mode = {3'b011};
    bins VU_mode = {3'b100};
  }

  priv_mode_hs_vs: coverpoint {ins.prev.mode_virt, ins.prev.mode} {
    type_option.weight = 0;
    bins HS_mode = {3'b001};
    bins VS_mode = {3'b101};
  }
  priv_mode_s_u: coverpoint {ins.prev.mode_virt, ins.prev.mode} {
    type_option.weight = 0;
    bins S_mode = {3'b001};
    bins U_mode = {3'b000};
  }
  priv_mode_hs_vu: coverpoint {ins.prev.mode_virt, ins.prev.mode} {
    type_option.weight = 0;
    bins HS_mode = {3'b001};
    bins VU_mode = {3'b100};
  }

  priv_mode_vs_u: coverpoint {ins.prev.mode_virt, ins.prev.mode} {
    type_option.weight = 0;
    bins VS_mode = {3'b101};
    bins U_mode = {3'b000};
  }
  priv_mode_vs_vu: coverpoint {ins.prev.mode_virt, ins.prev.mode} {
    type_option.weight = 0;
    bins VS_mode = {3'b101};
    bins VU_mode = {3'b100};
  }

  priv_mode_u_vu: coverpoint {ins.prev.mode_virt, ins.prev.mode} {
    type_option.weight = 0;
    bins U_mode = {3'b000};
    bins VU_mode = {3'b100};
  }


  priv_mode_m_s_u: coverpoint {ins.prev.mode_virt, ins.prev.mode} {
    type_option.weight = 0;
    bins M_mode = {3'b011};
    bins S_mode = {3'b001};
    bins U_mode = {3'b000};
  }
  priv_mode_m_hs_vs: coverpoint {ins.prev.mode_virt, ins.prev.mode} {
    type_option.weight = 0;
    bins M_mode = {3'b011};
    bins HS_mode = {3'b001};
    bins VS_mode = {3'b101};
  }
  priv_mode_m_hs_vu: coverpoint {ins.prev.mode_virt, ins.prev.mode} {
    type_option.weight = 0;
    bins M_mode = {3'b011};
    bins HS_mode = {3'b001};
    bins VU_mode = {3'b100};
  }
  priv_mode_m_vs_u: coverpoint {ins.prev.mode_virt, ins.prev.mode} {
    type_option.weight = 0;
    bins M_mode = {3'b011};
    bins VS_mode = {3'b101};
    bins U_mode = {3'b000};
  }
  priv_mode_m_vs_vu: coverpoint {ins.prev.mode_virt, ins.prev.mode} {
    type_option.weight = 0;
    bins M_mode = {3'b011};
    bins VS_mode = {3'b101};
    bins VU_mode = {3'b100};
  }
  priv_mode_m_u_vu: coverpoint {ins.prev.mode_virt, ins.prev.mode} {
    type_option.weight = 0;
    bins M_mode = {3'b011};
    bins U_mode = {3'b000};
    bins VU_mode = {3'b100};
  }

  priv_mode_hs_vs_u: coverpoint {ins.prev.mode_virt, ins.prev.mode} {
    type_option.weight = 0;
    bins HS_mode = {3'b001};
    bins VS_mode = {3'b101};
    bins U_mode = {3'b000};
  }
  priv_mode_hs_vs_vu: coverpoint {ins.prev.mode_virt, ins.prev.mode} {
    type_option.weight = 0;
    bins HS_mode = {3'b001};
    bins VS_mode = {3'b101};
    bins VU_mode = {3'b100};
  }
  priv_mode_hs_u_vu: coverpoint {ins.prev.mode_virt, ins.prev.mode} {
    type_option.weight = 0;
    bins HS_mode = {3'b001};
    bins U_mode = {3'b000};
    bins VU_mode = {3'b100};
  }

  priv_mode_vs_u_vu: coverpoint {ins.prev.mode_virt, ins.prev.mode} {
    type_option.weight = 0;
    bins VS_mode = {3'b101};
    bins U_mode = {3'b000};
    bins VU_mode = {3'b100};
  }


  priv_mode_m_hs_vs_u: coverpoint {ins.prev.mode_virt, ins.prev.mode} {
    type_option.weight = 0;
    bins M_mode = {3'b011};
    bins HS_mode = {3'b001};
    bins VS_mode = {3'b101};
    bins U_mode = {3'b000};
  }
  priv_mode_m_hs_vs_vu: coverpoint {ins.prev.mode_virt, ins.prev.mode} {
    type_option.weight = 0;
    bins M_mode = {3'b011};
    bins HS_mode = {3'b001};
    bins VS_mode = {3'b101};
    bins VU_mode = {3'b100};
  }
  priv_mode_m_hs_u_vu: coverpoint {ins.prev.mode_virt, ins.prev.mode} {
    type_option.weight = 0;
    bins M_mode = {3'b011};
    bins HS_mode = {3'b001};
    bins U_mode = {3'b000};
    bins VU_mode = {3'b100};
  }
  priv_mode_m_vs_u_vu: coverpoint {ins.prev.mode_virt, ins.prev.mode} {
    type_option.weight = 0;
    bins M_mode = {3'b011};
    bins VS_mode = {3'b101};
    bins U_mode = {3'b000};
    bins VU_mode = {3'b100};
  }
  priv_mode_hs_vs_u_vu: coverpoint {ins.prev.mode_virt, ins.prev.mode} {
    type_option.weight = 0;
    bins HS_mode = {3'b001};
    bins VS_mode = {3'b101};
    bins U_mode = {3'b000};
    bins VU_mode = {3'b100};
  }


  priv_mode_m_hs_vs_u_vu: coverpoint {ins.prev.mode_virt, ins.prev.mode} {
    type_option.weight = 0;
    bins M_mode = {3'b011};
    bins HS_mode = {3'b001};
    bins VS_mode = {3'b101};
    bins U_mode = {3'b000};
    bins VU_mode = {3'b100};
  }
