//
// Copyright (c) 2023 Imperas Software Ltd., www.imperas.com
// Modified February 2024, jcarlin@hmc.edu
//
// SPDX-License-Identifier: Apache-2.0 WITH SHL-2.0
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//   http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
// either express or implied.
//
// See the License for the specific language governing permissions and
// limitations under the License.
//
//

class RISCV_instruction
  #(
  parameter int ILEN   = 32,  // Instruction length in bits
  parameter int XLEN   = 32,  // GPR length in bits
  parameter int FLEN   = 32,  // FPR length in bits
  parameter int VLEN   = 512, // Vector register size in bits
  parameter int NHART  = 1,   // Number of harts reported
  parameter int RETIRE = 1    // Number of instructions that can retire during valid event
);
  string ins_str;
  ops_t ops[6];
  int hart;
  int issue;
  bit trap;
  riscvTraceData #(ILEN, XLEN, FLEN, VLEN) current;
  riscvTraceData #(ILEN, XLEN, FLEN, VLEN) prev;

  riscvTraceData #(ILEN, XLEN, FLEN, VLEN)traceDataQ[(NHART-1):0][(RETIRE-1):0][$:`NUM_RVVI_DATA];

  function new (int hart, int issue, riscvTraceData #(ILEN, XLEN, FLEN, VLEN)traceDataQ[(NHART-1):0][(RETIRE-1):0][$:`NUM_RVVI_DATA]);
    string insbin, ins_str, op[6], key, val;
    int num, i, j; // for loop counters and tracking how many operands there are
    string s;

    // Set per instruction trace data
    this.hart = hart;
    this.issue = issue;
    this.traceDataQ = traceDataQ;
    this.current = traceDataQ[hart][issue][`SAMPLE_CURRENT];
    this.prev = traceDataQ[hart][issue][`SAMPLE_PREV];
    this.trap = this.current.trap;

    // Remove commas from disassembly string
    s = this.current.disass;
    foreach (this.current.disass[c]) begin
      s[c] = (this.current.disass[c] == ",")? " " : this.current.disass[c];
    end

    // Split up instruction and operands
    num = $sscanf (s, "%s %s %s %s %s %s %s %s", insbin, ins_str, op[0], op[1], op[2], op[3], op[4], op[5]);
    this.ins_str = ins_str;

    // Check if stack reg list (used by cm.push/cm.pop) and combine full list into single operand
    if (op[0][0] == "{") begin
      int found = 0;
      for (i = 0; i < op[1].len(); i++) begin
        if (op[1][i] == "}") begin
          op[0] = {op[0],",",op[1]};
          op[1] = op[2];
          num = num - 1;
          found = 1;
        end
      end
      if (found == 0) begin
        for (i = 0; i < op[2].len(); i++) begin
          if (op[2][i] == "}") begin
            op[0] = {op[0],",",op[1],",",op[2]};
            op[1] = op[3];
            num = num - 2;
          end
        end
      end
    end

    // Check for special operands (indexed addressing, register surrounded by parentheses)
    for (i=0; i<num-2; i++) begin
      key = op[i];
      this.ops[i].key=op[i]; // in case we dont update it as special operand
      this.ops[i].val=""; // not used here
      for (j = 0; j < key.len(); j++) begin
        if (key[j] == "(" && j != 0) begin  // if indexed addressing, convert offset(rs1) to op[i].key=offset op[i+1].key=rs1
          this.ops[i].key = key.substr(0,j-1); // offset
          this.ops[i+1].key = key.substr(j+1,key.len()-2);
          i++; // step over +1
          break;
        end else if (key[j] == "(") begin  // if register surrounded by parentheses convert (rs1) to op[i].key=rs1
          if (this.ops[i].key[this.ops[i].key.len()-1] == ")") begin
            string opstr = this.ops[i].key.substr(1,this.ops[i].key.len()-2);
            this.ops[i].key = opstr;
          end
          break;
        end
      end
    end

    // Parse operands and get values of relevant registers if needed
    for (i=0; i<num-2; i++) begin
      // integer registers
      if (this.ops[i].key[0] == "x") begin
        int idx = get_gpr_num(this.ops[i].key);
        //$display("SAMPLE: %0s op[%0d]=%0s gpr(%0d)", ins_str,i, this.ops[i].key, idx);
        if (idx < 0) begin
          this.ops[i].val = this.ops[i].key; // Not a register, key (name) is the value of the operand
        end else begin
          this.ops[i].val = string'(this.current.x_wdata[idx]); //if register then value of register gets written to ops.val
        end
      // floating point registers
      end else if (this.ops[i].key[0] == "f") begin
        int idx = get_fpr_num(this.ops[i].key);
        if (idx < 0) begin
          this.ops[i].val = this.ops[i].key; // Not a register, key (name) is the value of the operand
        end else begin
          this.ops[i].val = string'(this.current.f_wdata[idx]); //if register then value of register gets written to ops.val
        end
      // vector
      end else if (this.ops[i].key[0] == "v") begin
        int idx = get_vr_num(this.ops[i].key);
        if (idx < 0) begin
          this.ops[i].val = this.ops[i].key; // Not a register, key (name) is the value of the operand
        end else begin
          this.ops[i].val = string'(this.current.v_wdata[idx]); //if register then value of register gets written to ops.val
        end
      // immediate values
      end else begin
        this.ops[i].val = this.ops[i].key;
      end
    end
  endfunction

  // Lookup integer register value
  virtual function `SIGNED_XLEN_BITS get_gpr_val(int hart, int issue, string key, int prev);
    int idx = get_gpr_num(key);
    if (idx >= 0) begin
      return traceDataQ[hart][issue][prev].x_wdata[idx];
    end
    return 0;
  endfunction

  // Lookup floating point register value
  function `SIGNED_FLEN_BITS get_fpr_val(int hart, int issue, string key, int prev);
    int idx = get_fpr_num(key);
    if (idx >= 0) begin
      return traceDataQ[hart][issue][prev].f_wdata[idx];
    end
    return 0;
  endfunction

  // Lookup vector register value
  function `SIGNED_VLEN_BITS get_vr_val(int hart, int issue, string key, int prev);
    int idx = get_vr_num(key);
    if (idx >= 0) begin
      return traceDataQ[hart][issue][prev].v_wdata[idx];
    end
    return 0;
  endfunction

  function `SIGNED_XLEN_BITS get_pc();
    return current.pc_rdata;
  endfunction

  // Works for both ABI and architectural register names
  function gpr_name_t get_gpr_reg (string key);
    case (key)
      "x0": return x0;
      "zero": return x0;
      "x1": return x1;
      "ra": return x1;
      "x2": return x2;
      "sp": return x2;
      "x3": return x3;
      "gp": return x3;
      "x4": return x4;
      "tp": return x4;
      "x5": return x5;
      "t0": return x5;
      "x6": return x6;
      "t1": return x6;
      "x7": return x7;
      "t2": return x7;
      "x8": return x8;
      "s0": return x8;
      "x9": return x9;
      "s1": return x9;
      "x10": return x10;
      "a0": return x10;
      "x11": return x11;
      "a1": return x11;
      "x12": return x12;
      "a2": return x12;
      "x13": return x13;
      "a3": return x13;
      "x14": return x14;
      "a4": return x14;
      "x15": return x15;
      "a5": return x15;
`ifndef COVER_E
      "x16": return x16;
      "a6": return x16;
      "x17": return x17;
      "a7": return x17;
      "x18": return x18;
      "s2": return x18;
      "x19": return x19;
      "s3": return x19;
      "x20": return x20;
      "s4": return x20;
      "x21": return x21;
      "s5": return x21;
      "x22": return x22;
      "s6": return x22;
      "x23": return x23;
      "s7": return x23;
      "x24": return x24;
      "s8": return x24;
      "x25": return x25;
      "s9": return x25;
      "x26": return x26;
      "s10": return x26;
      "x27": return x27;
      "s11": return x27;
      "x28": return x28;
      "t3": return x28;
      "x29": return x29;
      "t4": return x29;
      "x30": return x30;
      "t5": return x30;
      "x31": return x31;
      "t6": return x31;
`endif
      default: begin
          $error("ERROR: SystemVerilog Functional Coverage: get_gpr_reg(%0s) not found gpr", key);
          $fatal(1);
      end
    endcase
  endfunction

  // compressed register
  function gpr_reduced_name_t get_gpr_c_reg (string key);
    case (key)
      "x8": return c_x8;
      "s0": return c_x8;
      "x9": return c_x9;
      "s1": return c_x9;
      "x10": return c_x10;
      "a0": return c_x10;
      "x11": return c_x11;
      "a1": return c_x11;
      "x12": return c_x12;
      "a2": return c_x12;
      "x13": return c_x13;
      "a3": return c_x13;
      "x14": return c_x14;
      "a4": return c_x14;
      "x15": return c_x15;
      "a5": return c_x15;
      default: begin
        $error("ERROR: SystemVerilog Functional Coverage: get_gpr_c_reg(%0s) not found gpr", key);
        $fatal(1);
      end
    endcase
  endfunction

  // Convert immediate string to integer
  // Works for hex and decimal (positive or negative) values
  // NOTE: This function only works for immediate values that fit in a 32-bit integer.
  function int get_imm(string s);
    int val;
    if (s[1] == "x") begin
      s = s.substr(2,s.len()-1);
      val = s.atohex();
    end else if (s[0] == "-") begin
      s = s.substr(1,s.len()-1);
      val = 0 - s.atoi();
    end else begin
      val = s.atoi();
    end
    return val;
  endfunction

  function fpr_name_t get_fpr_reg (string key);
    case (key)
      "f0": return f0;
      "f1": return f1;
      "f2": return f2;
      "f3": return f3;
      "f4": return f4;
      "f5": return f5;
      "f6": return f6;
      "f7": return f7;
      "f8": return f8;
      "f9": return f9;
      "f10": return f10;
      "f11": return f11;
      "f12": return f12;
      "f13": return f13;
      "f14": return f14;
      "f15": return f15;
      "f16": return f16;
      "f17": return f17;
      "f18": return f18;
      "f19": return f19;
      "f20": return f20;
      "f21": return f21;
      "f22": return f22;
      "f23": return f23;
      "f24": return f24;
      "f25": return f25;
      "f26": return f26;
      "f27": return f27;
      "f28": return f28;
      "f29": return f29;
      "f30": return f30;
      "f31": return f31;
      default: begin
        $error("ERROR: SystemVerilog Functional Coverage: get_fpr_reg(%0s) not found fpr", key);
        $fatal(1);
      end
    endcase
  endfunction

  function fpr_reduced_name_t get_fpr_c_reg (string key);
    case (key)
      "f8": return c_f8;
      "f9": return c_f9;
      "f10": return c_f10;
      "f11": return c_f11;
      "f12": return c_f12;
      "f13": return c_f13;
      "f14": return c_f14;
      "f15": return c_f15;
      default: begin
        $error("ERROR: SystemVerilog Functional Coverage: get_fpr_c_reg(%0s) not found fpr", key);
        $fatal(1);
      end
    endcase
  endfunction

  // Vector register fetch

  function vr_name_t get_vr_reg (string key);
    case (key)
      "v0": return v0;
      "v1": return v1;
      "v2": return v2;
      "v3": return v3;
      "v4": return v4;
      "v5": return v5;
      "v6": return v6;
      "v7": return v7;
      "v8": return v8;
      "v9": return v9;
      "v10": return v10;
      "v11": return v11;
      "v12": return v12;
      "v13": return v13;
      "v14": return v14;
      "v15": return v15;
      "v16": return v16;
      "v17": return v17;
      "v18": return v18;
      "v19": return v19;
      "v20": return v20;
      "v21": return v21;
      "v22": return v22;
      "v23": return v23;
      "v24": return v24;
      "v25": return v25;
      "v26": return v26;
      "v27": return v27;
      "v28": return v28;
      "v29": return v29;
      "v30": return v30;
      "v31": return v31;
      default: begin
        $error("ERROR: SystemVerilog Functional Coverage: get_vr_reg(%0s) not found vr", key);
        $fatal(1);
      end
    endcase
  endfunction

  // Assign operands to appropriate instruction fields in riscvTraceData (registers, immediates, CSRs, etc.)
  virtual function void add_rd(int offset);
    current.has_rd = 1;
    current.rd = ops[offset].key;
    current.rd_val = current.x_wdata[get_gpr_num(ops[offset].key)];
    current.rd_val_pre = prev.x_wdata[get_gpr_num(ops[offset].key)];
  endfunction

  virtual function void add_rd_ra();
    current.has_rd = 1;
    current.rd = "ra";
    current.rd_val = current.x_wdata[get_gpr_num("ra")];
    current.rd_val_pre = prev.x_wdata[get_gpr_num("ra")];
  endfunction

  virtual function void add_rs1(int offset);
    current.has_rs1 = 1;
    current.rs1 = ops[offset].key;
    current.rs1_val = prev.x_wdata[get_gpr_num(ops[offset].key)];
  endfunction

  virtual function void add_rs1_sp();
    current.has_rs1 = 1;
    current.rs1 = "sp";
    current.rs1_val = prev.x_wdata[get_gpr_num("sp")];
  endfunction

  virtual function void add_rs2(int offset);
    current.has_rs2 = 1;
    current.rs2 = ops[offset].key;
    current.rs2_val = prev.x_wdata[get_gpr_num(ops[offset].key)];
  endfunction

  virtual function void add_rs3(int offset);
    current.has_rs3 = 1;
    current.rs3 = ops[offset].key;
    current.rs3_val = prev.x_wdata[get_gpr_num(ops[offset].key)];
  endfunction

  virtual function void add_imm(int offset);
    current.imm = get_imm(ops[offset].key);
  endfunction

  virtual function void add_imm2(int offset);
    current.imm2 = get_imm(ops[offset].key);
  endfunction

  virtual function void add_imm3(int offset);
    current.imm3 = get_imm(ops[offset].key);
  endfunction

  virtual function void add_cimm(int offset);
    current.cimm = get_imm(ops[offset].key);
  endfunction

  virtual function void add_imm_addr(int offset);
    current.imm = get_imm(ops[offset].key);
  endfunction

  virtual function void add_csr(int offset);
    current.imm2 = get_csr_addr(current.hart, ops[offset].key);
  endfunction

  virtual function void add_mem_offset(int offset);
    current.imm = get_imm(ops[offset].key);
  endfunction

  virtual function void add_mem_address();
    current.mem_addr = current.rs1_val + current.imm;
  endfunction

  virtual function void add_fd(int offset, int finx=0);
    current.has_fd = 1;
    current.fd = ops[offset].key;
    if (finx) begin
      current.fd_val = current.x_wdata[get_gpr_num(ops[offset].key)];
      current.fd_val_pre = prev.x_wdata[get_gpr_num(ops[offset].key)];
    end else begin
      current.fd_val = current.f_wdata[get_fpr_num(ops[offset].key)];
      current.fd_val_pre = prev.f_wdata[get_fpr_num(ops[offset].key)];
    end
  endfunction

  virtual function void add_fs1(int offset, int finx=0);
    current.has_fs1 = 1;
    current.fs1 = ops[offset].key;
    if (finx) begin
      current.fs1_val = prev.x_wdata[get_gpr_num(ops[offset].key)];
    end else begin
      current.fs1_val = prev.f_wdata[get_fpr_num(ops[offset].key)];
    end
  endfunction

  virtual function void add_fs2(int offset, int finx=0);
    current.has_fs2 = 1;
    current.fs2 = ops[offset].key;
    if (finx) begin
      current.fs2_val = prev.x_wdata[get_gpr_num(ops[offset].key)];
    end else begin
      current.fs2_val = prev.f_wdata[get_fpr_num(ops[offset].key)];
    end
  endfunction

  virtual function void add_fs3(int offset, int finx=0);
    current.has_fs3 = 1;
    current.fs3 = ops[offset].key;
    if (finx) begin
      current.fs3_val = prev.x_wdata[get_gpr_num(ops[offset].key)];
    end else begin
      current.fs3_val = prev.f_wdata[get_fpr_num(ops[offset].key)];
    end
  endfunction

  // Vector
  virtual function void add_vd(int offset);
    current.has_vd = 1;
    current.vd = ops[offset].key;
    current.vd_val = current.v_wdata[get_vr_num(ops[offset].key)];
    current.vd_val_pre = prev.v_wdata[get_vr_num(ops[offset].key)];
  endfunction

  virtual function void add_vs1(int offset);
    current.has_vs1 = 1;
    current.vs1 = ops[offset].key;
    current.vs1_val = prev.v_wdata[get_vr_num(ops[offset].key)];
  endfunction

  virtual function void add_vs2(int offset);
    current.has_vs2 = 1;
    current.vs2 = ops[offset].key;
    current.vs2_val = prev.v_wdata[get_vr_num(ops[offset].key)];
  endfunction

  virtual function void add_vs3(int offset);
    current.has_vs3 = 1;
    current.vs3 = ops[offset].key;
    current.vs3_val = prev.v_wdata[get_vr_num(ops[offset].key)];
  endfunction

  virtual function void add_v0();
    current.has_v0 = 1;
    current.v0_val = prev.v_wdata[0];
  endfunction

  virtual function void add_vm(int offset);
    current.vm = get_vm(ops[offset].key);
  endfunction

  virtual function void add_eSEW(int offset);
    current.eSEW = get_vtype_eSEW_val(ops[offset].key);
  endfunction

  virtual function void add_mLMUL(int offset);
    current.mLMUL = get_vtype_mLMUL_val(ops[offset].key);
  endfunction

  virtual function void add_ta(int offset);
    current.ta = get_vtype_ta_val(ops[offset].key);
  endfunction

  virtual function void add_ma(int offset);
    current.ma = get_vtype_ma_val(ops[offset].key);
  endfunction

endclass
