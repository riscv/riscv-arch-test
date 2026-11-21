// Wrapper for the CV32E40S in the cv32e40x-dv "core" testbench: CV32E40S, memory and
// virtual peripherals. install-cve4.sh builds it with cv32e40x-dv's tb_top, mm_ram and
// dp_ram, which are core-independent apart from the wrapper's name.
//
// Adapted from cv32e40x-dv 93ce70f tb/core/cv32e40x_tb_wrapper.sv.
// Copyright 2018 Robert Balas <balasr@student.ethz.ch>
// SPDX-License-Identifier: Apache-2.0 WITH SHL-0.51
//
// Core configuration comes from compile defines set per config by install-cve4.sh and
// follows the riscv-arch-test configs in config/cores/cve4/cv32e40s-*:
//   CV32E40S_RVB  B_EXT = ZBA_ZBB_ZBC_ZBS (else B_NONE)
//   CV32E40S_PMA  PMA_NUM_REGIONS = 1: [0x0000_0000, 0x0040_0000) main, not
//                 bufferable/cacheable/integrity (else 0 regions: all main)
//   CV32E40S_PMP  PMP_NUM_REGIONS = 16, PMP_GRANULARITY = 0, all entries OFF and
//                 mseccfg = 0 at reset (else 0 regions)
// M_EXT = M and the remaining parameters keep their cv32e40s_core defaults.
//
// The OBI parity/checksum inputs (gntpar, rvalidpar, rchk) are driven with their
// correct values, and alert_major/alert_minor are reported if they ever assert.

module cv32e40s_tb_wrapper
    #(parameter INSTR_RDATA_WIDTH = 32,
                RAM_ADDR_WIDTH    = 22,
                DM_HALTADDRESS    = 32'hF000_0800,   // inside the core's default DM region
                HART_ID           = 32'h0000_0000
    )
    (input logic         clk_i,
     input logic         rst_ni,

     input logic [31:0]  boot_addr_i,
     input logic         fetch_enable_i,
     output logic        tests_passed_o,
     output logic        tests_failed_o,
     output logic [31:0] exit_value_o,
     output logic        exit_valid_o);

    import cv32e40s_pkg::*;

    // signals connecting core to memory
    logic                         instr_req;
    logic                         instr_gnt;
    logic                         instr_rvalid;
    logic [31:0]                  instr_addr;
    logic [INSTR_RDATA_WIDTH-1:0] instr_rdata;

    logic                         data_req;
    logic                         data_gnt;
    logic                         data_rvalid;
    logic [31:0]                  data_addr;
    logic                         data_we;
    logic [3:0]                   data_be;
    logic [31:0]                  data_rdata;
    logic [31:0]                  data_wdata;

    logic                         debug_req;
    logic [31:0]                  irq;
    logic                         core_sleep;
    logic                         alert_minor, alert_major;
    logic [63:0]                  mtime;      // CLINT mtime (cv32e40s has no time_i port)

    // ---------------------------------------------------------------- configuration
`ifdef CV32E40S_RVB
    localparam b_ext_e B_EXT_CFG = ZBA_ZBB_ZBC_ZBS;
`else
    localparam b_ext_e B_EXT_CFG = B_NONE;
`endif

`ifdef CV32E40S_PMA
    localparam int       PMA_N = 1;
    localparam pma_cfg_t PMA_CFG_P[PMA_N-1:0] = '{
        '{word_addr_low  : 32'h0000_0000,
          word_addr_high : 32'h0010_0000,      // byte address 0x0040_0000
          main           : 1'b1,
          bufferable     : 1'b0,
          cacheable      : 1'b0,
          integrity      : 1'b0}};
`else
    localparam int       PMA_N = 0;
    localparam pma_cfg_t PMA_CFG_P[PMA_N-1:0] = '{default: PMA_R_DEFAULT};
`endif

`ifdef CV32E40S_PMP
    localparam int PMP_N = 16;
`else
    localparam int PMP_N = 0;
`endif

    // LFSR settings of cv32e40s-dv (uvmt_cv32e40s_base_test_constants.sv); the LFSRs
    // only feed dummy/hint instruction insertion, which is off at reset.
    localparam lfsr_cfg_t LFSR0 = '{coeffs: 32'h8000_0057, default_seed: 32'habba_cafe};
    localparam lfsr_cfg_t LFSR1 = '{coeffs: 32'h8000_0062, default_seed: 32'hbeef_1234};
    localparam lfsr_cfg_t LFSR2 = '{coeffs: 32'h8000_007a, default_seed: 32'ha5a5_a5a5};

    // OBI response checksums, as checked by cv32e40s_rchk_check (even parity per
    // byte of rdata; bit 4 covers err, which is always 0 here)
    function automatic logic [4:0] rchk(input logic [31:0] d);
        return {1'b0, ^d[31:24], ^d[23:16], ^d[15:8], ^d[7:0]};
    endfunction

    cv32e40s_core #(
        .B_EXT            ( B_EXT_CFG ),
        .M_EXT            ( M         ),
        .PMA_NUM_REGIONS  ( PMA_N     ),
        .PMA_CFG          ( PMA_CFG_P ),
        .PMP_GRANULARITY  ( 0         ),
        .PMP_NUM_REGIONS  ( PMP_N     ),
        // PMP_PMPNCFG_RV / PMP_PMPADDR_RV / PMP_MSECCFG_RV keep the core defaults,
        // which are the ACT config's values: all entries OFF, addresses 0, mseccfg 0
        .LFSR0_CFG        ( LFSR0     ),
        .LFSR1_CFG        ( LFSR1     ),
        .LFSR2_CFG        ( LFSR2     )
    ) cv32e40s_core_i (
        .clk_i                  ( clk_i                 ),
        .rst_ni                 ( rst_ni                ),
        .scan_cg_en_i           ( 1'b0                  ),

        .boot_addr_i            ( boot_addr_i           ),
        .dm_exception_addr_i    ( '0                    ),
        .dm_halt_addr_i         ( DM_HALTADDRESS        ),
        .mhartid_i              ( HART_ID               ),
        .mimpid_patch_i         ( 4'h0                  ),
        .mtvec_addr_i           ( '0                    ),

        .instr_req_o            ( instr_req             ),
        .instr_gnt_i            ( instr_gnt             ),
        .instr_rvalid_i         ( instr_rvalid          ),
        .instr_addr_o           ( instr_addr            ),
        .instr_memtype_o        (                       ),
        .instr_prot_o           (                       ),
        .instr_dbg_o            (                       ),
        .instr_rdata_i          ( instr_rdata           ),
        .instr_err_i            ( 1'b0                  ),
        .instr_reqpar_o         (                       ),
        .instr_gntpar_i         ( ~instr_gnt            ),
        .instr_rvalidpar_i      ( ~instr_rvalid         ),
        .instr_achk_o           (                       ),
        .instr_rchk_i           ( rchk(instr_rdata)     ),

        .data_req_o             ( data_req              ),
        .data_gnt_i             ( data_gnt              ),
        .data_rvalid_i          ( data_rvalid           ),
        .data_addr_o            ( data_addr             ),
        .data_be_o              ( data_be               ),
        .data_we_o              ( data_we               ),
        .data_wdata_o           ( data_wdata            ),
        .data_memtype_o         (                       ),
        .data_prot_o            (                       ),
        .data_dbg_o             (                       ),
        .data_rdata_i           ( data_rdata            ),
        .data_err_i             ( 1'b0                  ),
        .data_reqpar_o          (                       ),
        .data_gntpar_i          ( ~data_gnt             ),
        .data_rvalidpar_i       ( ~data_rvalid          ),
        .data_achk_o            (                       ),
        .data_rchk_i            ( rchk(data_rdata)      ),

        .mcycle_o               (                       ),

        .irq_i                  ( irq                   ),
        .wu_wfe_i               ( 1'b0                  ),

        .clic_irq_i             ( 1'b0                  ),
        .clic_irq_id_i          ( '0                    ),
        .clic_irq_level_i       ( 8'h0                  ),
        .clic_irq_priv_i        ( 2'h0                  ),
        .clic_irq_shv_i         ( 1'b0                  ),

        .fencei_flush_req_o     (                       ),
        .fencei_flush_ack_i     ( 1'b1                  ),

        .alert_minor_o          ( alert_minor           ),
        .alert_major_o          ( alert_major           ),

        .debug_req_i            ( debug_req             ),
        .debug_havereset_o      (                       ),
        .debug_running_o        (                       ),
        .debug_halted_o         (                       ),
        .debug_pc_valid_o       (                       ),
        .debug_pc_o             (                       ),

        .fetch_enable_i         ( fetch_enable_i        ),
        .core_sleep_o           ( core_sleep            )
    );

    // Report security alerts (never expected in these runs)
    bit alert_minor_seen, alert_major_seen;
    always_ff @(posedge clk_i) begin
        if (rst_ni && alert_major && !alert_major_seen) begin
            $display("[TESTBENCH] WARNING @ %0t: alert_major_o asserted", $time);
            alert_major_seen <= 1'b1;
        end
        if (rst_ni && alert_minor && !alert_minor_seen) begin
            $display("[TESTBENCH] WARNING @ %0t: alert_minor_o asserted", $time);
            alert_minor_seen <= 1'b1;
        end
    end

    // RAM and memory-mapped pseudo peripherals (virtual printer 0x1000_0000,
    // test status/exit 0x2000_0000/4, CLINT 0x0200_0000)
    mm_ram
        #(.RAM_ADDR_WIDTH    (RAM_ADDR_WIDTH),
          .INSTR_RDATA_WIDTH (INSTR_RDATA_WIDTH))
    ram_i
        (.clk_i          ( clk_i                                     ),
         .rst_ni         ( rst_ni                                    ),
         .dm_halt_addr_i ( DM_HALTADDRESS                            ),

         .instr_req_i    ( instr_req                                 ),
         .instr_addr_i   ( { {(32-RAM_ADDR_WIDTH){1'b0}},
                             instr_addr[RAM_ADDR_WIDTH-1:0] }         ),
         .instr_rdata_o  ( instr_rdata                               ),
         .instr_rvalid_o ( instr_rvalid                              ),
         .instr_gnt_o    ( instr_gnt                                 ),

         .data_req_i     ( data_req                                  ),
         .data_addr_i    ( data_addr                                 ),
         .data_we_i      ( data_we                                   ),
         .data_be_i      ( data_be                                   ),
         .data_wdata_i   ( data_wdata                                ),
         .data_atop_i    ( 6'b0                                      ),  // no A extension
         .data_rdata_o   ( data_rdata                                ),
         .data_exokay_o  (                                           ),
         .data_rvalid_o  ( data_rvalid                               ),
         .data_gnt_o     ( data_gnt                                  ),

         .irq_id_i       ( 5'b0                                      ),
         .irq_ack_i      ( 1'b0                                      ),  // level-sensitive irqs
         .irq_o          ( irq                                       ),

         .debug_req_o    ( debug_req                                 ),

         .pc_core_id_i   ( cv32e40s_core_i.if_id_pipe.pc             ),

         .tests_passed_o ( tests_passed_o                            ),
         .tests_failed_o ( tests_failed_o                            ),
         .exit_valid_o   ( exit_valid_o                              ),
         .exit_value_o   ( exit_value_o                              ),
         .mtime_o        ( mtime                                     ));

endmodule // cv32e40s_tb_wrapper
