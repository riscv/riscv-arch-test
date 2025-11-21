///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Vector Helper Functions
//
// Copyright (C) 2025 Harvey Mudd College, 10x Engineers, UET Lahore, Habib University
// Written: Kaden Cassidy jacassidy@hmc.edu June 3, 2025
//
// SPDX-License-Identifier: Apache-2.0
//
////////////////////////////////////////////////////////////////////////////////////////////////

function int get_vtype_vlmax(int hart, int issue, int prev);

  logic[2:0] vsew  = get_csr_val(hart, issue, prev, "vtype", "vsew") [2:0];
  logic[2:0] vlmul = get_csr_val(hart, issue, prev, "vtype", "vlmul")[2:0];

  case (vlmul)
        3'b000: begin end
        3'b001: begin end
        3'b010: begin end
        3'b011: begin end
        3'b101: begin end
        3'b110: begin end
        3'b111: begin end
        default: begin
            $error("ERROR: SystemVerilog Functional Coverage: get_vtype_vlmax lmul is undefined (%0s)", vlmul);
            $fatal(1);
        end
    endcase

    case (vsew)
        3'b000: begin end
        3'b001: begin end
        3'b010: begin end
        3'b011: begin end
        default: begin
            $error("ERROR: SystemVerilog Functional Coverage: get_vtype_vlmax sew is undefined (%0s)", vsew);
            $fatal(1);
        end
    endcase

  if(get_csr_val(hart, issue, prev, "vtype", "vill") == 1) begin
    return -1;   // make sure no coverpoint can ever be hit when vill bit is set
  end

  return get_vlmax_params(hart, issue, vsew, vlmul);
endfunction


function int get_vlmax_params(int hart, int issue, logic[2:0] vsew, logic[2:0] vlmul);

    int vlen = get_csr_val(hart, issue, 0, "vlenb", "vlenb") * 8;
    int vlen_times_lmul;
    int vlmax;

    case (vlmul)
        3'b000: vlen_times_lmul = vlen;
        3'b001: vlen_times_lmul = vlen * 2;
        3'b010: vlen_times_lmul = vlen * 4;
        3'b011: vlen_times_lmul = vlen * 8;
        3'b101: vlen_times_lmul = vlen / 8; // 1/8
        3'b110: vlen_times_lmul = vlen / 4; // 1/4
        3'b111: vlen_times_lmul = vlen / 2; // 1/2
        default: begin
          return -1;
        end
    endcase

    case (vsew)
        3'b000: vlmax = vlen_times_lmul / 8;
        3'b001: vlmax = vlen_times_lmul / 16;
        3'b010: vlmax = vlen_times_lmul / 32;
        3'b011: vlmax = vlen_times_lmul / 64;
        default: begin
          return -1;
        end
    endcase

    return vlmax;

endfunction

function logic check_vtype_sew_supported(`XLEN_BITS vsew);

    `ifdef SEW8_SUPPORTED
    if (vsew == 0) return 1'b1;
    `endif
    `ifdef SEW16_SUPPORTED
    if (vsew == 1) return 1'b1;
    `endif
    `ifdef SEW32_SUPPORTED
    if (vsew == 2) return 1'b1;
    `endif
    `ifdef SEW64_SUPPORTED
    if (vsew == 3) return 1'b1;
    `endif

    return 1'b0;
endfunction


typedef enum {
    vs_zero, //     = {(`SEW){1'b0}},
    vs_one, //      = {(`SEW-1){1'b0}, {1'b1}},
    vs_two, //      = {(`SEW-2){1'b0}, {2'b10}},
    vs_min, //      = {{1'b1}, (`SEW-1){1'b0}},
    vs_minp1, //    = {{1'b1}, (`SEW-2){1'b0}, {1'b1}},
    vs_max, //      = {{1'b0}, (`SEW-1){1'b1}},
    vs_maxm1, //    = {{1'b0}, (`SEW-2){1'b1}, {1'b0}},
    vs_ones, //     = {(`SEW){1'b1}},
    vs_onesm1, //   = {(`SEW-1){1'b1}, {1'b0}},
    vs_walkeodd, // = {(`SEW/2){2'b10}},
    vs_walkeven, // = {(`SEW/2){2'b01}},
    vs_random
} edge_vs_values_t;

// Check for vector operand edge values, assuming vl = 1
function edge_vs_values_t vs_edges_check(int hart, int issue, `VLEN_BITS val, string sew_multiplier);
  `XLEN_BITS vsew = get_csr_val(hart, issue, `SAMPLE_BEFORE, "vtype", "vsew");
  int sew = 2 ** (3 + unsigned'(vsew[2:0]));
  int eew;

  case (sew_multiplier)
    "1":     eew = sew;
    "2":     eew = 2 * sew;
    "4":     eew = 4 * sew;
    "8":     eew = 8 * sew;
    "f2":    eew = sew / 2;
    "f4":    eew = sew / 4;
    "f8":    eew = sew / 8;
    "m":     eew = 8;       // vl = 8 and eew = 1 for mask (logical) instructions
    default: begin
      $error("ERROR: SystemVerilog Functional Coverage: Unsupported SEW multiplier: %s", sew_multiplier);
      $fatal(1);
    end
  endcase

  case (eew)
    8:   return vs_edges_check_eew_8(val);
    `ifdef SEW16_SUPPORTED
    16:  return vs_edges_check_eew_16(val);
    `endif
    `ifdef SEW32_SUPPORTED
    32:  return vs_edges_check_eew_32(val);
    `endif
    `ifdef SEW64_SUPPORTED
    64:  return vs_edges_check_eew_64(val);
    `endif
    default: begin
      $error("ERROR: SystemVerilog Functional Coverage: Unsupported EEW: %s", eew);
      $fatal(1);
    end
  endcase
endfunction

function edge_vs_values_t vs_edges_check_eew_1(`VLEN_BITS val);
  casez (val)
    {{(`VLEN-1){1'b?}}, {1'b1}}:  return vs_one;
    default:                      return vs_zero;
  endcase
endfunction

function edge_vs_values_t vs_edges_check_eew_8(`VLEN_BITS val);
  casez (val)
    {{(`VLEN-8){1'b?}},         {(8){1'b0}}}:            return vs_zero;
    {{(`VLEN-8){1'b?}},         {(8-1){1'b0}}, {1'b1}}:  return vs_one;
    {{(`VLEN-8){1'b?}},         {(8-2){1'b0}}, {2'b10}}: return vs_two;
    {{(`VLEN-8){1'b?}}, {1'b1}, {(8-1){1'b0}}}:          return vs_min;
    {{(`VLEN-8){1'b?}}, {1'b1}, {(8-2){1'b0}}, {1'b1}}:  return vs_minp1;
    {{(`VLEN-8){1'b?}}, {1'b0}, {(8-1){1'b1}}}        :  return vs_max;
    {{(`VLEN-8){1'b?}}, {1'b0}, {(8-2){1'b1}}, {1'b0}}:  return vs_maxm1;
    {{(`VLEN-8){1'b?}},         {(8){1'b1}}}:            return vs_ones;
    {{(`VLEN-8){1'b?}},         {(8-1){1'b1}}, {1'b0}}:  return vs_onesm1;
    {{(`VLEN-8){1'b?}},         {(8/2){2'b10}}}:         return vs_walkeodd;
    {{(`VLEN-8){1'b?}},         {(8/2){2'b01}}}:         return vs_walkeven;
    default:                                             return vs_random;
  endcase
endfunction

`ifdef SEW16_SUPPORTED
function edge_vs_values_t vs_edges_check_eew_16(`VLEN_BITS val);
  casez (val)
    {{(`VLEN-16){1'b?}},         {(16){1'b0}}}:            return vs_zero;
    {{(`VLEN-16){1'b?}},         {(16-1){1'b0}}, {1'b1}}:  return vs_one;
    {{(`VLEN-16){1'b?}},         {(16-2){1'b0}}, {2'b10}}: return vs_two;
    {{(`VLEN-16){1'b?}}, {1'b1}, {(16-1){1'b0}}}:          return vs_min;
    {{(`VLEN-16){1'b?}}, {1'b1}, {(16-2){1'b0}}, {1'b1}}:  return vs_minp1;
    {{(`VLEN-16){1'b?}}, {1'b0}, {(16-1){1'b1}}}        :  return vs_max;
    {{(`VLEN-16){1'b?}}, {1'b0}, {(16-2){1'b1}}, {1'b0}}:  return vs_maxm1;
    {{(`VLEN-16){1'b?}},         {(16){1'b1}}}:            return vs_ones;
    {{(`VLEN-16){1'b?}},         {(16-1){1'b1}}, {1'b0}}:  return vs_onesm1;
    {{(`VLEN-16){1'b?}},         {(16/2){2'b10}}}:         return vs_walkeodd;
    {{(`VLEN-16){1'b?}},         {(16/2){2'b01}}}:         return vs_walkeven;
    default:                                               return vs_random;
  endcase
endfunction
`endif
`ifdef SEW32_SUPPORTED
function edge_vs_values_t vs_edges_check_eew_32(`VLEN_BITS val);
  casez (val)
    {{(`VLEN-32){1'b?}},         {(32){1'b0}}}:            return vs_zero;
    {{(`VLEN-32){1'b?}},         {(32-1){1'b0}}, {1'b1}}:  return vs_one;
    {{(`VLEN-32){1'b?}},         {(32-2){1'b0}}, {2'b10}}: return vs_two;
    {{(`VLEN-32){1'b?}}, {1'b1}, {(32-1){1'b0}}}:          return vs_min;
    {{(`VLEN-32){1'b?}}, {1'b1}, {(32-2){1'b0}}, {1'b1}}:  return vs_minp1;
    {{(`VLEN-32){1'b?}}, {1'b0}, {(32-1){1'b1}}}        :  return vs_max;
    {{(`VLEN-32){1'b?}}, {1'b0}, {(32-2){1'b1}}, {1'b0}}:  return vs_maxm1;
    {{(`VLEN-32){1'b?}},         {(32){1'b1}}}:            return vs_ones;
    {{(`VLEN-32){1'b?}},         {(32-1){1'b1}}, {1'b0}}:  return vs_onesm1;
    {{(`VLEN-32){1'b?}},         {(32/2){2'b10}}}:         return vs_walkeodd;
    {{(`VLEN-32){1'b?}},         {(32/2){2'b01}}}:         return vs_walkeven;
    default:                                               return vs_random;
  endcase
endfunction
`endif
`ifdef SEW64_SUPPORTED
function edge_vs_values_t vs_edges_check_eew_64(`VLEN_BITS val);
  casez (val)
    {{(`VLEN-64){1'b?}},         {(64){1'b0}}}:            return vs_zero;
    {{(`VLEN-64){1'b?}},         {(64-1){1'b0}}, {1'b1}}:  return vs_one;
    {{(`VLEN-64){1'b?}},         {(64-2){1'b0}}, {2'b10}}: return vs_two;
    {{(`VLEN-64){1'b?}}, {1'b1}, {(64-1){1'b0}}}:          return vs_min;
    {{(`VLEN-64){1'b?}}, {1'b1}, {(64-2){1'b0}}, {1'b1}}:  return vs_minp1;
    {{(`VLEN-64){1'b?}}, {1'b0}, {(64-1){1'b1}}}        :  return vs_max;
    {{(`VLEN-64){1'b?}}, {1'b0}, {(64-2){1'b1}}, {1'b0}}:  return vs_maxm1;
    {{(`VLEN-64){1'b?}},         {(64){1'b1}}}:            return vs_ones;
    {{(`VLEN-64){1'b?}},         {(64-1){1'b1}}, {1'b0}}:  return vs_onesm1;
    {{(`VLEN-64){1'b?}},         {(64/2){2'b10}}}:         return vs_walkeodd;
    {{(`VLEN-64){1'b?}},         {(64/2){2'b01}}}:         return vs_walkeven;
    default:                                               return vs_random;
  endcase
endfunction
`endif


// todo: CHECK TO MAKE SURE BOOLEAN STATEMENTS WORK
// todo: ESPECIALLY REGARDING SIGNS
// todo:
// todo:
// todo:

typedef enum {
    zero,
    random_in_range,
    None
} edge_vs2_ls_values_t;

function edge_vs2_ls_values_t vs2_ls_edges_check (int hart, int issue, `VLEN_BITS val);

  logic all_values_within_range = 1'b1;

  `XLEN_BITS vsew               = get_csr_val(hart, issue, `SAMPLE_BEFORE, "vtype", "vsew");
  int vlmax                     = get_vtype_vlmax(hart, issue, `SAMPLE_BEFORE);

  if (val == 0) begin
    return zero;
  end

  //------------------------------------------
  // Walk across VAL in chunks of size SEW
  //------------------------------------------
  case (vsew)
    //--------------------------------------------------------------
    //  8-bit elements
    //--------------------------------------------------------------
    0: begin : SEW8
      for (int idx = 1; idx <= `VLEN / 8; ++idx) begin
        logic [7:0] elem = val[idx*8-1 -: 8];

        if (signed'(elem) > vlmax*2 | signed'(elem) < -vlmax*2)   all_values_within_range = 1'b0; // if out of range fail coverage
        if (signed'(elem) < 0)                                    all_values_within_range = 1'b0; // if element is negative and length is less than XLEN then fail coverage as it will be zero extended instead of treated as signed
      end
    end
    //--------------------------------------------------------------
    // 16-bit elements
    //--------------------------------------------------------------
    1: begin : SEW16
      for (int idx = 1; idx <= `VLEN / 16; ++idx) begin
        logic [15:0] elem = val[idx*16-1 -: 16];

        if (signed'(elem) > vlmax*2 | signed'(elem) < -vlmax*2)   all_values_within_range = 1'b0; // if out of range fail coverage
        `ifndef COVER_E
        if (signed'(elem) < 0)                                    all_values_within_range = 1'b0; // if element is negative and length is less than XLEN then fail coverage as it will be zero extended instead of treated as signed
        `endif
      end
    end
    //--------------------------------------------------------------
    // 32-bit elements
    //--------------------------------------------------------------
    2: begin : SEW32
      for (int idx = 1; idx <= `VLEN / 32; ++idx) begin
        logic [31:0] elem = val[idx*32-1 -: 32];

        if (signed'(elem) > vlmax*2 | signed'(elem) < -vlmax*2)   all_values_within_range = 1'b0; // if out of range fail coverage
        `ifdef XLEN64
        if (signed'(elem) < 0)                                    all_values_within_range = 1'b0; // if element is negative and length is less than XLEN then fail coverage as it will be zero extended instead of treated as signed
        `endif
      end
    end
    //--------------------------------------------------------------
    // 64-bit elements
    //--------------------------------------------------------------
    3: begin : SEW64
      for (int idx = 1; idx <= `VLEN / 64; ++idx) begin
        logic [63:0] elem = val[idx*64-1 -: 64];

        if (signed'(elem) > vlmax*2 | signed'(elem) < -vlmax*2)   all_values_within_range = 1'b0; // if out of range fail coverage
      end
    end
    //--------------------------------------------------------------
    default : begin
      $error("ERROR: SystemVerilog Functional Coverage: Unsupported VSEW: %s", vsew);
      $fatal(1);
    end
  endcase

  if (all_values_within_range) begin
    return random_in_range;
  end

  return None;
endfunction

function logic[63:0] get_vr_element_zero(int hart, int issue, `VLEN_BITS val);
    `XLEN_BITS vsew = get_csr_val(hart, issue, `SAMPLE_BEFORE, "vtype", "vsew");

    case (vsew)
    `ifdef SEW8_SUPPORTED
    2'b00:   return {56'b0, val[7:0]};
    `endif
    `ifdef SEW16_SUPPORTED
    2'b01:  return {48'b0, val[15:0]};
    `endif
    `ifdef SEW32_SUPPORTED
    2'b10:  return {32'b0, val[31:0]};
    `endif
    `ifdef SEW64_SUPPORTED
    2'b11:  return val[63:0];
    `endif
    default: begin
      $error("ERROR: SystemVerilog Functional Coverage: Unsupported SEW: %s", vsew);
      $fatal(1);
    end
  endcase
  return 0;

endfunction


typedef enum {
    mask_zero,
    mask_ones,
    mask_vlmaxm1ones,
    mask_vlmaxd2p1ones,
    mask_random
} edge_mask_values_t;

// Check for vector operand edge values, assuming vl = 1
function edge_mask_values_t mask_edges_check(int hart, int issue, `VLEN_BITS mask_val);
  int vlmax = get_vtype_vlmax(hart, issue, `SAMPLE_BEFORE);

  if      (mask_val == 0)                           return mask_zero;
  else if (mask_val == ((2 ** (vlmax)) - 1))        return mask_ones;
  else if (mask_val == ((2 ** (vlmax-1)) - 1))      return mask_vlmaxm1ones;
  else if (mask_val == ((2 ** (vlmax/2+1)) - 1))    return mask_vlmaxd2p1ones;
  else                                              return mask_random;

endfunction


typedef enum {
  vl_zero,
  vl_one,
  vl_vlmax,
  vl_legal,
  vl_illegal
} vl_t;

function vl_t vl_check(int hart, int issue);
  `XLEN_BITS vl = get_csr_val(hart, issue, `SAMPLE_BEFORE, "vl", "vl");
  `XLEN_BITS vstart = get_csr_val(hart, issue, `SAMPLE_BEFORE, "vstart", "vstart");
  int vlmax = get_vtype_vlmax(hart, issue, `SAMPLE_BEFORE);
  bit legal;
  if (vl <= vlmax & vl > vstart) legal = 1'b1; // check legal condition
  else                           legal = 1'b0;

  case(vl)
    0:         return vl_zero;
    1:         return vl_one;
    vlmax:     return vl_vlmax;
    default: begin
      if (legal) return vl_legal;
      else       return vl_illegal;
    end
  endcase
endfunction


typedef enum {
  vstart_one,
  vstart_vlmaxm1,
  vstart_vlmaxd2,
  vstart_legal,
  vstart_illegal
} vstart_t;

function vstart_t vstart_check(int hart, int issue);
  `XLEN_BITS vstart = get_csr_val(hart, issue, `SAMPLE_BEFORE, "vstart", "vstart");
  int vlmax = get_vtype_vlmax(hart, issue, `SAMPLE_BEFORE);
  bit legal;
  if (vstart < vlmax) legal = 1'b1; // check legal condition
  else                legal = 1'b0;

  case(vstart)
    1:           return vstart_one;
    vlmax-1:     return vstart_vlmaxm1;
    vlmax/2:     return vstart_vlmaxd2;
    default: begin
      if (legal) return vstart_legal;
      else       return vstart_illegal;
    end
  endcase
endfunction
