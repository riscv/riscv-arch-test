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

class riscvTraceData
#(
  parameter int ILEN   = 32,  // Instruction length in bits
  parameter int XLEN   = 32,  // GPR length in bits
  parameter int FLEN   = 32,  // FPR length in bits
  parameter int VLEN   = 512  // Vector register size in bits
);
  `ifdef COVER_E
    localparam NUM_REGS = 16;
  `else
    localparam NUM_REGS = 32;
  `endif
  //
  // RVVI values
  //
  logic                      valid;   // Retired instruction
  logic [63:0]               order;   // Unique event order count (no gaps or reuse)
  logic [(ILEN-1):0]         insn ;   // Instruction bit pattern
  logic                      trap ;   // Trapped instruction (State update without instruction retirement)
  logic                      halt ;   // Halted  instruction
  logic                      intr ;   // (RVFI Legacy) Flag first instruc
  logic [1:0]                mode ;   // Privilege mode of operation
  logic                 mode_virt ;   // Hypercisor virtualization
  logic [1:0]                ixl  ;   // XLEN mode 32/64 bit

  logic [(XLEN-1):0]         pc_rdata;   // PC of insn
  logic [(XLEN-1):0]         pc_wdata;   // PC of next instruction

  // X Registers
  logic [NUM_REGS-1:0][(XLEN-1):0]   x_wdata;   // X data value
  logic [NUM_REGS-1:0]               x_wb   ;   // X data writeback (change) flag

  // F Registers
  logic [31:0][(FLEN-1):0]   f_wdata;   // F data value
  logic [31:0]               f_wb   ;   // F data writeback (change) flag

  // V Registers
  logic [31:0][(VLEN-1):0]   v_wdata;   // V data value
  logic [31:0]               v_wb   ;   // V data writeback (change) flag

  // Control & State Registers
  logic [4095:0][(XLEN-1):0] csr   ;   // Full CSR Address range
  logic [4095:0]             csr_wb;   // CSR writeback (change) flag

  // Interrupts
  logic                      m_ext_intr;    // Machine external interrupt
  logic                      s_ext_intr;    // Supervisor external interrupt
  logic                      m_timer_intr;  // Machine timer interrupt
  logic                      m_soft_intr;   // Machine software interrupt

  logic                      lrsc_cancel;   // Implementation defined cancel

// Virtual Memory signals for verification
  localparam PA_BITS = (XLEN==32 ? 32'd34 : 32'd56);
  localparam PPN_BITS = (XLEN==32 ? 32'd22 : 32'd44);

  logic [(XLEN-1):0]     virt_adr_i;         // Instruction virtual address
  logic [(XLEN-1):0]     virt_adr_d;         // Data virtual address
  logic [(PA_BITS-1):0]  phys_adr_i;           // Instruction physical address
  logic [(PA_BITS-1):0]  phys_adr_d;           // Data physical address
  logic [(XLEN-1):0]     pte_i;         // Instruction page table entry
  logic [(XLEN-1):0]     pte_d;         // Data page table entry
  logic [(PPN_BITS-1):0] ppn_i;         // Instruction physical page number
  logic [(PPN_BITS-1):0] ppn_d;         // Data physical page number
  logic [1:0]            page_type_i;    // Instruction page type
  logic [1:0]            page_type_d;    // Data page type
  logic                  read_access;    // Read access
  logic                  write_access;   // Write access
  logic                  execute_access; // Execute access


  int                         hart;
  int                         issue;
  // Decoded instruction info
  string                      disass;
  string                      inst_name;

  int                         inst_category;

  bit                       has_rd;
  bit                       has_rs1;
  bit                       has_rs2;
  bit                       has_rs3;
  bit                       has_fd;
  bit                       has_fs1;
  bit                       has_fs2;
  bit                       has_fs3;
  bit                       has_vd;
  bit                       has_vs1;
  bit                       has_vs2;
  bit                       has_vs3;
  bit                       has_v0;

  string                    rd;
  string                    rs1;
  string                    rs2;
  string                    rs3;

  string                    fd;
  string                    fs1;
  string                    fs2;
  string                    fs3;

  string                    vd;
  string                    vs1;
  string                    vs2;
  string                    vs3;

  bit [(XLEN-1):0]          rd_val;
  bit [(XLEN-1):0]          rd_val_pre;
  bit [(XLEN-1):0]          rs1_val;
  bit [(XLEN-1):0]          rs2_val;
  bit [(XLEN-1):0]          rs3_val;

  bit [(FLEN-1):0]          fd_val;
  bit [(FLEN-1):0]          fd_val_pre;
  bit [(FLEN-1):0]          fs1_val;
  bit [(FLEN-1):0]          fs2_val;
  bit [(FLEN-1):0]          fs3_val;

  bit [(VLEN-1):0]          vd_val;
  bit [(VLEN-1):0]          vd_val_pre;
  bit [(VLEN-1):0]          vs1_val;
  bit [(VLEN-1):0]          vs2_val;
  bit [(VLEN-1):0]          vs3_val;
  bit [(VLEN-1):0]          v0_val;
  bit                       vm;

  bit [(XLEN-1):0]          imm;
  bit [(XLEN-1):0]          imm2;
  bit [(XLEN-1):0]          imm3;
  bit [(XLEN-1):0]          mem_addr;

  bit [2:0]                 eSEW;
  bit [2:0]                 mLMUL;
  bit                       ta;
  bit                       ma;
endclass
