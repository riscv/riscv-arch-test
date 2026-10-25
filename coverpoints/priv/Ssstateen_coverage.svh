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
            bins sstateen1 = {CSR_SSTATEEN1};
            bins sstateen2 = {CSR_SSTATEEN2};
            bins sstateen3 = {CSR_SSTATEEN3};
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
      csr_walk: coverpoint ins.current.rs1_val {
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

    `ifdef UDB_MXLEN_64
        se0_one: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mstateen0", "se0")[0] {
                bins se0_enabled  = {1'b1};
        }
    `else
        se0_one: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mstateen0h", "se0")[0] {
                bins se0_enabled  = {1'b1};
        }
    `endif
    // Bit 63 (SE<n>) of the mstateen<n> matching the sstateen<n> being accessed; n is
    // the low two bits of the CSR address. On RV32 the bit is bit 31 of mstateen<n>h.
    `ifdef UDB_MXLEN_64
        mstateen_se_n_one: coverpoint get_csr_val_addr(ins.hart, ins.issue, `SAMPLE_BEFORE, int'(CSR_MSTATEEN0) + int'(ins.current.insn[21:20]), "mstateen", "mstateen")[63] {
                bins se_enabled = {1'b1};
        }
    `else
        mstateen_se_n_one: coverpoint get_csr_val_addr(ins.hart, ins.issue, `SAMPLE_BEFORE, int'(CSR_MSTATEEN0H) + int'(ins.current.insn[21:20]), "mstateenh", "mstateenh")[31] {
                bins se_enabled = {1'b1};
        }
    `endif
    `ifdef ZFINX_SUPPORTED
        misa_F: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "misa", "exts")[5] {
                bins F_set   = {1'b1};
                bins F_clear = {1'b0};
        }
        sstateen0_fcsr_bit: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "sstateen0", "fcsr")[0] {
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
        jvt_state: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "sstateen0", "jvt")[0] {
                bins jvt_disabled = {1'b0};
                bins jvt_enabled  = {1'b1};
        }
        jvt_csr: coverpoint ins.current.insn[31:20] {
                wildcard bins jvt = {CSR_JVT};
        }
    `endif
    `ifdef ZFINX_SUPPORTED
        cp_fcsr_lower: cross priv_mode_s_u, misa_F, se0_one, sstateen0_fcsr_bit, csrops, fcsr_lower_mode_csrs {
                ignore_bins ig1 = binsof(misa_F.F_set)   && binsof(sstateen0_fcsr_bit.fcsr_zero);
                ignore_bins ig2 = binsof(misa_F.F_clear) && binsof(sstateen0_fcsr_bit.fcsr_zero);
        }
        cp_fcsr_fp_instrs: cross priv_mode_s_u, misa_F, se0_one, sstateen0_fcsr_bit, fp_instrs {
                ignore_bins ig1 = binsof(misa_F.F_set)   && binsof(sstateen0_fcsr_bit.fcsr_zero);
                ignore_bins ig2 = binsof(misa_F.F_clear) && binsof(sstateen0_fcsr_bit.fcsr_zero);
        }
    `endif
    cp_csr_illegal_accesses: cross priv_mode_u, sstateen_csrs, csrops, mstateen_se_n_one;
    cp_walking_ones:         cross priv_mode_s, sstateen_walk_csr, csrops, csr_walk, mstateen_se_n_one;
    `ifdef ZCMT_SUPPORTED
        cp_jvt:              cross priv_mode_s_u, csrops, jvt_csr, jvt_state, se0_one;
    `endif
endgroup

// H group: hstateen controls access from VS-mode and VU-mode but not HS-mode.  Ssstateen comprises only the
// sstateen and hstateen CSRs, so these coverpoints do not depend on mstateen.
`ifdef H_SUPPORTED
covergroup Ssstateen_H_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"

    csrr : coverpoint ins.current.insn {
        wildcard bins csrr = {CSRR};
    }
    csrop: coverpoint ins.current.insn {
        wildcard bins csrrs = {CSRRS};
        wildcard bins csrrc = {CSRRC};
    }
    csr_access : coverpoint ins.current.insn {
        wildcard bins csrr = {CSRR};
        wildcard bins csrw = {CSRW};
        wildcard bins csrs = {CSRS} iff (ins.current.insn[19:15] != 0);
        wildcard bins csrc = {CSRC} iff (ins.current.insn[19:15] != 0);
    }
    sstateen0 : coverpoint ins.current.insn[31:20] {
        bins sstateen0 = {CSR_SSTATEEN0};
    }
    senvcfg : coverpoint ins.current.insn[31:20] {
        bins senvcfg = {CSR_SENVCFG};
    }
    hstateen0 : coverpoint ins.current.insn[31:20] {
        bins hstateen0 = {CSR_HSTATEEN0};
        `ifdef UDB_MXLEN_32
            bins hstateen0h = {CSR_HSTATEEN0H};
        `endif
    }
    stateen123 : coverpoint ins.current.insn[31:20] {
        bins sstateen1 = {CSR_SSTATEEN1};
        bins sstateen2 = {CSR_SSTATEEN2};
        bins sstateen3 = {CSR_SSTATEEN3};
        bins hstateen1 = {CSR_HSTATEEN1};
        bins hstateen2 = {CSR_HSTATEEN2};
        bins hstateen3 = {CSR_HSTATEEN3};
        `ifdef UDB_MXLEN_32
            bins hstateen1h = {CSR_HSTATEEN1H};
            bins hstateen2h = {CSR_HSTATEEN2H};
            bins hstateen3h = {CSR_HSTATEEN3H};
        `endif
    }
    // hstateen0 SE0 and ENVCFG before the instruction; they are in hstateen0h on RV32
    `ifdef UDB_MXLEN_64
        hstateen0_se0 : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hstateen0", "se0")[0] {
        }
        hstateen0_envcfg : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hstateen0", "envcfg")[0] {
        }
        hstateen0_se0_one : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hstateen0", "se0")[0] {
            bins one = {1};
        }
    `else
        hstateen0_se0 : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hstateen0h", "se0")[0] {
        }
        hstateen0_envcfg : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hstateen0h", "envcfg")[0] {
        }
        hstateen0_se0_one : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hstateen0h", "se0")[0] {
            bins one = {1};
        }
    `endif
    // Bit 63 (bit 31 of hstateen1h-3h on RV32) of the hstateen CSR that controls the sstateen CSR the instruction
    // accesses.  Bits 1:0 of the CSR number give N.
    `ifdef UDB_MXLEN_64
        hstateen123_se : coverpoint get_csr_val_addr(ins.hart, ins.issue, `SAMPLE_BEFORE,
                int'(CSR_HSTATEEN0) + int'(ins.current.insn[21:20]), "hstateen", "hstateen")[63] {
    `else
        hstateen123_se : coverpoint get_csr_val_addr(ins.hart, ins.issue, `SAMPLE_BEFORE,
                int'(CSR_HSTATEEN0H) + int'(ins.current.insn[21:20]), "hstateenh", "hstateenh")[31] {
    `endif
    }
    walking_ones: coverpoint $clog2(ins.current.rs1_val) iff ($onehot(ins.current.rs1_val)) {
        bins b_1[] = { [0:`UDB_MXLEN-1] };
    }

    // HS-mode: walk hstateen0 (and hstateen0h)
    cp_hs_hstateen0_walk: cross priv_mode_hs, csrop, hstateen0, walking_ones;
    // hstateen0 does not control HS-mode
    cp_hs_sstateen0:      cross priv_mode_hs, csrr, sstateen0, hstateen0_se0;
    cp_hs_senvcfg:        cross priv_mode_hs, csrr, senvcfg, hstateen0_envcfg;
    // hstateen bit 63 does not control HS-mode access
    cp_hs_stateen123:     cross priv_mode_hs, csr_access, stateen123;

    // VS-mode: virtual instruction when the hstateen0 bit is 0
    cp_vs_sstateen0:      cross priv_mode_vs, csrr, sstateen0, hstateen0_se0;
    cp_vs_senvcfg:        cross priv_mode_vs, csrr, senvcfg, hstateen0_envcfg;
    // Bit 63 of the matching hstateen CSR controls VS-mode access to sstateen1-3; hstateen is never accessible
    cp_vs_stateen123:     cross priv_mode_vs, csr_access, stateen123, hstateen123_se;
    cp_vs_hstateen0:      cross priv_mode_vs, csrr, hstateen0;

    // sstateen0 bits whose hstateen0 bit is 0 read as zero in VS-mode.  hstateen0 C, FCSR and JVT can be nonzero
    // only when sstateen0 has that state to control (Zcmt or Zfinx).
    hstateen0_low : coverpoint {get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hstateen0", "jvt") == 1,
                                get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hstateen0", "fcsr") == 1,
                                get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hstateen0", "c") == 1} {
        bins zero = {0};
        `ifdef ZCMT_SUPPORTED
            bins nonzero = {[1:7]};
        `elsif ZFINX_SUPPORTED
            bins nonzero = {[1:7]};
        `endif
    }
    cp_vs_sstateen0_roz:  cross priv_mode_vs, csrr, sstateen0, hstateen0_se0_one, hstateen0_low;

    // VU-mode: always virtual instruction when HS-mode could make the access
    cp_vu_sstateen0:      cross priv_mode_vu, csrr, sstateen0, hstateen0_se0;
    cp_vu_senvcfg:        cross priv_mode_vu, csrr, senvcfg, hstateen0_envcfg;
    // Virtual instruction, whatever hstateen bit 63 holds
    cp_vu_stateen123:     cross priv_mode_vu, csr_access, stateen123, hstateen123_se;
    cp_vu_hstateen0:      cross priv_mode_vu, csrr, hstateen0;
endgroup
`endif

function void ssstateen_sample(int hart, int issue, ins_t ins);
    Ssstateen_cg.sample(ins);
    `ifdef H_SUPPORTED
        Ssstateen_H_cg.sample(ins);
    `endif
endfunction
