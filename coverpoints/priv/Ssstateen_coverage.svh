///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Covergroups
// Written by : Ayesha Anwar ayesha.anwaar2005@gmail.com
// Copyright (C) 2024 Harvey Mudd College, 10x Engineers, UET Lahore, Habib University
// SPDX-License-Identifier: Apache-2.0
//
////////////////////////////////////////////////////////////////////////////////////////////////
`define COVER_SSSTATEEN
covergroup Ssstateen_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"
    csrops: coverpoint ins.current.insn {
            wildcard bins csrw = {CSRRW};
            wildcard bins csrs = {CSRRS};
            wildcard bins csrc = {CSRRC};
    }
    sstateen_csrs: coverpoint ins.current.insn[31:20] {
            bins sstateen0 = {CSR_SSTATEEN0};
            bins sstateen1 = {CSR_SSTATEEN1};
            bins sstateen2 = {CSR_SSTATEEN2};
            bins sstateen3 = {CSR_SSTATEEN3};
    }
    sstateen_walk_csr: coverpoint ins.current.insn[31:20] {
            bins sstateen0 = {CSR_SSTATEEN0};
    }
    priv_mode_maybes_u: coverpoint {ins.prev.mode_virt, ins.prev.mode} {
            bins U_mode = {3'b000};
            `ifdef S_SUPPORTED
                    bins S_mode = {3'b001};
            `endif
    }

    `ifdef UDB_MXLEN_64
      csr_walk: coverpoint ins.current.rs1_val {
          // bits [3:63] are WPRI; bit 0 (C) is custom state (not tested)
          `ifdef ZFINX_SUPPORTED
                  wildcard bins walking1_1  = {64'b??????????????????????????????????????????????????????????????1?};
          `endif
          `ifdef ZCMT_SUPPORTED
                  wildcard bins walking1_2  = {64'b?????????????????????????????????????????????????????????????1??};
          `endif
              wildcard bins walking0_1  = {64'b??????????????????????????????????????????????????????????????0?};
              wildcard bins walking0_2  = {64'b?????????????????????????????????????????????????????????????0??};
      }
    `else
      csr_walk: coverpoint ins.current.csr[ins.current.insn[31:20]] {
          // bits [3:31] are WPRI; bit 0 (C) is custom state (not tested)
          `ifdef ZFINX_SUPPORTED
                  wildcard bins walking1_1  = {32'b??????????????????????????????1?};
          `endif
          `ifdef ZCMT_SUPPORTED
                  wildcard bins walking1_2  = {32'b?????????????????????????????1??};
          `endif
              wildcard bins walking0_1  = {32'b??????????????????????????????0?};
              wildcard bins walking0_2  = {32'b?????????????????????????????0??};
      }
    `endif

    // SE0 is bit 63 of mstateen0 on RV64, bit 31 of mstateen0h on RV32
    `ifdef UDB_MXLEN_64
        se0_one: coverpoint ins.current.csr[CSR_MSTATEEN0][63] {
                bins se0_enabled  = {1'b1};
        }
    `else
        se0_one: coverpoint ins.current.csr[CSR_MSTATEEN0H][31] {
                bins se0_enabled  = {1'b1};
        }
    `endif
    `ifdef UDB_MXLEN_64
        se0_zero: coverpoint ins.current.csr[CSR_MSTATEEN0][63] {
                bins se0_disabled  = {1'b0};
        }
    `else
        se0_zero: coverpoint ins.current.csr[CSR_MSTATEEN0H][31] {
                bins se0_disabled  = {1'b0};
        }
    `endif

    `ifdef ZFINX_SUPPORTED
        misa_F: coverpoint ins.current.csr[CSR_MISA][5] {
                bins F_set   = {1'b1};
                bins F_clear = {1'b0};
        }
        sstateen0_fcsr_bit: coverpoint ins.current.csr[CSR_SSTATEEN0][1] {
                bins fcsr_zero = {1'b0};
                bins fcsr_one  = {1'b1};
        }
        fcsr_lower_mode_csrs: coverpoint ins.current.insn[31:20] {
                wildcard bins frm    = {CSR_FRM};
                wildcard bins fflags = {CSR_FFLAGS};
                wildcard bins fcsr   = {CSR_FCSR};
        }
        fp_instrs: coverpoint ins.current.insn {
                wildcard bins fadd_s   = {FADD_S};
                wildcard bins fcvt_ws  = {FCVT_W_S};
                wildcard bins fcvt_sw  = {FCVT_S_W};
                wildcard bins fclass_s = {FCLASS_S};
        }
    `endif
    `ifdef ZCMT_SUPPORTED
        jvt_state: coverpoint ins.current.csr[CSR_SSTATEEN0][2] {
                bins jvt_disabled = {1'b0};
                bins jvt_enabled  = {1'b1};
        }
        jvt_csr: coverpoint ins.current.insn[31:20] {
                wildcard bins jvt = {CSR_JVT};
        }
    `endif
    `ifdef ZFINX_SUPPORTED
        cp_fcsr_lower: cross priv_mode_maybes_u, misa_F, se0_one, sstateen0_fcsr_bit, csrops, fcsr_lower_mode_csrs {
                ignore_bins ig1 = binsof(misa_F.F_set)   && binsof(sstateen0_fcsr_bit.fcsr_zero);
                ignore_bins ig2 = binsof(misa_F.F_clear) && binsof(sstateen0_fcsr_bit.fcsr_zero);
        }
        cp_fcsr_fp_instrs: cross priv_mode_maybes_u, misa_F, se0_one, sstateen0_fcsr_bit, fp_instrs {
                ignore_bins ig1 = binsof(misa_F.F_set)   && binsof(sstateen0_fcsr_bit.fcsr_zero);
                ignore_bins ig2 = binsof(misa_F.F_clear) && binsof(sstateen0_fcsr_bit.fcsr_zero);
        }
    `endif
    cp_mstateen0_se0_zero_controls_sstateen0: cross csrops, priv_mode_s, se0_zero, sstateen_csrs {
            ignore_bins ig1 = binsof(sstateen_csrs.sstateen1);
            ignore_bins ig2 = binsof(sstateen_csrs.sstateen2);
            ignore_bins ig3 = binsof(sstateen_csrs.sstateen3);
    }
    cp_mstateen0_se0_one_controls_sstateen0: cross csrops, priv_mode_s, se0_one, sstateen_csrs {
            ignore_bins ig1 = binsof(sstateen_csrs.sstateen1);
            ignore_bins ig2 = binsof(sstateen_csrs.sstateen2);
            ignore_bins ig3 = binsof(sstateen_csrs.sstateen3);
    }
    cp_csr_illegal_accesses: cross priv_mode_u, sstateen_csrs, csrops, se0_one;
    cp_walking_ones:         cross priv_mode_s, sstateen_walk_csr, csrops, csr_walk, se0_one;
    `ifdef ZCMT_SUPPORTED
        cp_jvt:              cross priv_mode_maybes_u, csrops, jvt_csr, jvt_state, se0_one;
    `endif
endgroup
function void ssstateen_sample(int hart, int issue, ins_t ins);
    Ssstateen_cg.sample(ins);
endfunction
