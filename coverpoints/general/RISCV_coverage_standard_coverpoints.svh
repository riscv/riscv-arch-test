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
  priv_mode_m: coverpoint ins.prev.mode {
    type_option.weight = 0;
    bins M_mode = {2'b11};
  }
  priv_mode_s: coverpoint ins.prev.mode {
    type_option.weight = 0;
    bins S_mode = {2'b01};
  }
  priv_mode_u: coverpoint ins.prev.mode {
    type_option.weight = 0;
    bins U_mode = {2'b00};
  }
  priv_mode_ms: coverpoint ins.prev.mode {
    type_option.weight = 0;
    bins M_mode = {2'b11};
    bins S_mode = {2'b01};
  }
  priv_mode_mu: coverpoint ins.prev.mode {
    type_option.weight = 0;
    bins M_mode = {2'b11};
    bins U_mode = {2'b00};
  }
  priv_mode_su: coverpoint ins.prev.mode {
    type_option.weight = 0;
    bins S_mode = {2'b01};
    bins U_mode = {2'b00};
  }
  priv_mode_msu: coverpoint ins.prev.mode {
    type_option.weight = 0;
    bins M_mode = {2'b11};
    bins S_mode = {2'b01};
    bins U_mode = {2'b00};
  }
