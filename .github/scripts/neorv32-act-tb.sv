// neorv32-act-tb.sv
// ACT testbench for the NEORV32 processor under Verilator: runs one self-checking ELF.
// Copyright (c) 2026, Harvey Mudd College
// SPDX-License-Identifier: Apache-2.0
//
// The DUT is neorv32-act-top.vhd converted to Verilog by `ghdl synth`. Its internal IMEM and DMEM
// are disabled, so every access outside the processor's internal IO region
// (0xFFE00000-0xFFFFFFFF) reaches this testbench on the external bus (XBUS):
//
//   0x80000000 + MEM_BYTES  RAM, loaded from +MEM=<file> (one 32-bit hex word per line)
//   0xF0000000              console: a store prints its low byte
//   0xF0000004              exit: a store ends the run; 0 = pass, anything else = fail
//   0xF0000008              bit 0 drives the machine external interrupt (irq_mei_i)
//   anything else           bus error, so loads, stores and fetches raise access faults
//
// The RAM acknowledges every strobe in the next cycle, so it also serves the instruction cache's
// burst reads. The run prints "[TB] PASS" after a store of 0 to the exit register, "[TB] FAIL" after
// any other exit value, and "[TB] TIMEOUT" when +MAX_CYCLES=<n> (default 20000000) cycles pass
// without an exit.

`timescale 1ns / 1ps

module neorv32_act_tb;
  localparam int MEM_BYTES = 4 * 1024 * 1024;  // must match link.ld and sail.json
  localparam int MEM_WORDS = MEM_BYTES / 4;

  logic clk = 1'b0;
  logic rstn = 1'b0;
  logic [31:0] adr, dat_o, dat_i;
  logic [3:0] sel;
  logic we, stb, cyc, ack, err, mei;

  logic [31:0] mem[MEM_WORDS];
  longint unsigned cycles = 0;
  longint unsigned max_cycles = 64'd20_000_000;
  string mem_file;

  neorv32_act_top dut (
    .clk_i     (clk),
    .rstn_i    (rstn),
    .xbus_adr_o(adr),
    .xbus_dat_o(dat_o),
    .xbus_we_o (we),
    .xbus_sel_o(sel),
    .xbus_stb_o(stb),
    .xbus_cyc_o(cyc),
    .xbus_dat_i(dat_i),
    .xbus_ack_i(ack),
    .xbus_err_i(err),
    .irq_mei_i (mei)
  );

  initial begin
    if (!$value$plusargs("MEM=%s", mem_file)) begin
      $display("[TB] no +MEM=<file> given");
      $fatal(1);
    end
    void'($value$plusargs("MAX_CYCLES=%d", max_cycles));
    $readmemh(mem_file, mem);
    #100 rstn = 1'b1;
  end

  always #5 clk = ~clk;  // 100 MHz

  always @(posedge clk) begin
    ack   <= 1'b0;
    err   <= 1'b0;
    dat_i <= '0;
    cycles <= cycles + 1;
    if (cycles >= max_cycles) begin
      $display("\n[TB] TIMEOUT after %0d cycles", cycles);
      $finish;
    end
    if (rstn && cyc && stb) begin
      ack <= 1'b1;
      if (adr[31:28] == 4'h8 && adr[27:0] < MEM_BYTES) begin
        if (we) begin
          for (int i = 0; i < 4; i++) if (sel[i]) mem[adr[27:2]][8*i+:8] <= dat_o[8*i+:8];
        end else begin
          dat_i <= mem[adr[27:2]];
        end
      end else if (adr == 32'hF000_0000 && we) begin
        $write("%c", dat_o[7:0]);
        $fflush();
      end else if (adr == 32'hF000_0004 && we) begin
        if (dat_o == 32'h0) begin
          $display("\n[TB] PASS after %0d cycles", cycles);
          $finish;
        end else begin
          $display("\n[TB] FAIL: exit code 0x%08x after %0d cycles", dat_o, cycles);
          $finish;
        end
      end else if (adr == 32'hF000_0008) begin
        if (we) mei <= dat_o[0];
        else dat_i <= {31'b0, mei};
      end else begin
        err <= 1'b1;
      end
    end
  end

  initial mei = 1'b0;
endmodule
