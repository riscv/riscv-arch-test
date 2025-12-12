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

`ifdef COVER_E
    `define NUM_REGS 16
`else
    `define NUM_REGS 32
`endif

riscvTraceData #(ILEN, XLEN, FLEN, VLEN) traceDataQ [(NHART-1):0][(RETIRE-1):0] [$:`NUM_RVVI_DATA];

function void save_rvvi_data(bit trap, int hart, int issue, string disass);
  string inst_name = get_inst_name(trap, hart, issue, disass);
  riscvTraceData #(ILEN, XLEN, FLEN, VLEN) rvviData;
  bit [31:0] mask;
  int idx;

  // Load initial prev values to use for checking register values during first (sampled) instruction
  // Todo: initial CSR values would be incorrect
  while (traceDataQ[hart][issue].size() < `NUM_RVVI_DATA) begin
    rvviData = new();
    rvviData.valid = 0;
    rvviData.order = 0;
    rvviData.insn = 0;
    rvviData.trap = 0;
    rvviData.halt = 0;
    rvviData.intr = 0;
    rvviData.mode = 0;
    rvviData.mode_virt = 0; // hypervisor bit
    rvviData.ixl = 0;
    rvviData.pc_rdata = 0;
    rvviData.pc_wdata = 0;
    rvviData.x_wdata = 0;
    rvviData.x_wb = 0;
    rvviData.f_wdata = 0;
    rvviData.f_wb = 0;
    rvviData.v_wdata = 0;
    rvviData.v_wb = 0;
    rvviData.csr = 0;
    rvviData.csr_wb = 0;
    rvviData.m_ext_intr = 0;
    rvviData.s_ext_intr = 0;
    rvviData.m_timer_intr = 0;
    rvviData.m_soft_intr = 0;
    rvviData.lrsc_cancel = 0;
    rvviData.virt_adr_i = 0;
    rvviData.virt_adr_d = 0;
    rvviData.phys_adr_i = 0;
    rvviData.phys_adr_d = 0;
    rvviData.pte_i = 0;
    rvviData.pte_d = 0;
    rvviData.ppn_i = 0;
    rvviData.ppn_d = 0;
    rvviData.page_type_i = 0;
    rvviData.page_type_d = 0;
    rvviData.read_access = 0;
    rvviData.write_access = 0;
    rvviData.execute_access = 0;
    rvviData.hart = hart;
    rvviData.issue = issue;
    rvviData.disass = "";
    rvviData.inst_name = "";
    traceDataQ[hart][issue].push_front(rvviData);
  end

  // Store signal values for this trace
  rvviData = new();
  rvviData.valid = this.rvvi.valid[hart][issue];
  rvviData.order = this.rvvi.order[hart][issue];
  rvviData.insn = this.rvvi.insn[hart][issue];
  rvviData.trap = this.rvvi.trap[hart][issue];
  rvviData.halt = this.rvvi.halt[hart][issue];
  rvviData.intr = this.rvvi.intr[hart][issue];
  rvviData.mode = this.rvvi.mode[hart][issue];
  rvviData.mode_virt = this.rvvi.mode_virt[hart][issue]; 
  rvviData.ixl = this.rvvi.ixl[hart][issue];
  rvviData.pc_rdata = this.rvvi.pc_rdata[hart][issue];
  rvviData.pc_wdata = this.rvvi.pc_wdata[hart][issue];

  // For registers, use the existing values and only update the changed ones
  // Assign current values
  rvviData.x_wb = this.rvvi.x_wb[hart][issue];
  rvviData.x_wdata = traceDataQ[hart][issue][0].x_wdata;
  // Update changed values
  if (rvviData.x_wb != 'b0) begin
    for (idx=0; idx<`NUM_REGS; idx++) begin
      mask = 1<<idx;
      if ((mask & rvviData.x_wb) != 'b0) begin
        rvviData.x_wdata[idx] = this.rvvi.x_wdata[hart][issue][idx];
      end
    end
  end

  // Assign current values
  rvviData.f_wb = this.rvvi.f_wb[hart][issue];
  rvviData.f_wdata = traceDataQ[hart][issue][0].f_wdata;
  // Update changed values
  if (rvviData.f_wb != 'b0) begin
    for (idx=0; idx<32; idx++) begin
      mask = 1<<idx;
      if ((mask & rvviData.f_wb) != 'b0) begin
        rvviData.f_wdata[idx] = this.rvvi.f_wdata[hart][issue][idx];
      end
    end
  end

  // Assign current values
  rvviData.v_wb = this.rvvi.v_wb[hart][issue];
  rvviData.v_wdata = traceDataQ[hart][issue][0].v_wdata;
  // Update changed values
  if (rvviData.v_wb != 'b0) begin
    for (idx=0; idx<32; idx++) begin
      mask = 1<<idx;
      if ((mask & rvviData.v_wb) != 'b0) begin
        rvviData.v_wdata[idx] = this.rvvi.v_wdata[hart][issue][idx];
      end
    end
  end

  // Todo: CSR values should use the current values and only update the changed ones
  rvviData.csr = this.rvvi.csr[hart][issue];
  rvviData.csr_wb = this.rvvi.csr_wb[hart][issue];

  // Store interrupt signals from the current trace
  rvviData.m_ext_intr = this.rvvi.m_ext_intr[hart][issue];
  rvviData.s_ext_intr = this.rvvi.s_ext_intr[hart][issue];
  rvviData.m_timer_intr = this.rvvi.m_timer_intr[hart][issue];
  rvviData.m_soft_intr = this.rvvi.m_soft_intr[hart][issue];

  // Store virtual memory signals from the current trace
  rvviData.virt_adr_i = this.rvvi.virt_adr_i[hart][issue];
  rvviData.virt_adr_d = this.rvvi.virt_adr_d[hart][issue];
  rvviData.phys_adr_i = this.rvvi.phys_adr_i[hart][issue];
  rvviData.phys_adr_d = this.rvvi.phys_adr_d[hart][issue];
  rvviData.pte_i = this.rvvi.pte_i[hart][issue];
  rvviData.pte_d = this.rvvi.pte_d[hart][issue];
  rvviData.ppn_i = this.rvvi.ppn_i[hart][issue];
  rvviData.ppn_d = this.rvvi.ppn_d[hart][issue];
  rvviData.page_type_i = this.rvvi.page_type_i[hart][issue];
  rvviData.page_type_d = this.rvvi.page_type_d[hart][issue];
  rvviData.read_access = this.rvvi.read_access[hart][issue];
  rvviData.write_access = this.rvvi.write_access[hart][issue];
  rvviData.execute_access = this.rvvi.execute_access[hart][issue];

  // Store additional signals from the current trace
  rvviData.lrsc_cancel = this.rvvi.lrsc_cancel[hart][issue];
  rvviData.disass = disass;
  rvviData.inst_name = inst_name;
  rvviData.hart = hart;
  rvviData.issue = issue;

  // Add new trace data to array
  if (traceDataQ[hart][issue].size() >= `NUM_RVVI_DATA) begin
    traceDataQ[hart][issue].delete(`NUM_RVVI_DATA-1);
  end
  traceDataQ[hart][issue].push_front(rvviData);
endfunction
