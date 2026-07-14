///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage — Vector illegal instruction coverpoints
//
// Copyright (C) 2024 Harvey Mudd College, 10x Engineers, UET Lahore, Habib University
//
// SPDX-License-Identifier: Apache-2.0
//
////////////////////////////////////////////////////////////////////////////////////////////////

    // ══════════════════════════════════════════════════════════════════
    // vset* reserved encoding coverpoints
    // ══════════════════════════════════════════════════════════════════

    // ── cp_v_vsetvl ──────────────────────────────────────────────────
    // Legal vsetvl: insn[31]=1, insn[30:25]=000000.
    // Generator template: "10EEEEERRRRRRRRRR111RRRRR1010111"
    //   insn[31:30]=10, E bits sweep insn[29:25] (the field that must be 000000
    //   for legal vsetvl — bit 30 is fixed to 0, bits[29:25] are swept).
    // Coverpoint: sample insn[29:25] when opcode=OP-V, funct3=111, insn[31:30]=10.
    v_vsetvl : coverpoint ins.current.insn[29:25]
        iff (ins.current.insn[6:0] == 7'b1010111
           & ins.current.insn[14:12] == 3'b111
           & ins.current.insn[31:30] == 2'b10) {
        // 2^5 = 32 bins; only 00000 is legal (standard vsetvl)
    }

    // ── cp_v_vsetvli_sew ─────────────────────────────────────────────
    // vsetvli with reserved SEW high bit.
    // Generator template: "0000RR1EERRRRRRRR111RRRRR1010111"
    //   insn[31]=0 (vsetvli), insn[30:28]=000 (reserved upper bits = 0),
    //   insn[25]=zimm[5]=1 (vsew[2]=1, making SEW reserved: 5,6,7),
    //   E bits sweep insn[24:23] = zimm[4:3] = vsew[1:0].
    // Coverpoint: sample insn[24:23] when vsetvli, upper reserved=0, vsew[2]=1.
    v_vsetvli_sew : coverpoint ins.current.insn[24:23]
        iff (ins.current.insn[6:0] == 7'b1010111
           & ins.current.insn[14:12] == 3'b111
           & ins.current.insn[31] == 1'b0
           & ins.current.insn[30:28] == 3'b000
           & ins.current.insn[25] == 1'b1) {
        // 2^2 = 4 bins of reserved SEW values (vsew = 100, 101, 110, 111)
    }

    // ── cp_v_vsetvli_res ─────────────────────────────────────────────
    // vsetvli with reserved upper zimm bits (zimm[10:8] != 000).
    // Generator template: "EEE0RR0RRRRRRRRRR111RRRRR1010111"
    //   insn[31]=0 (vsetvli), E bits sweep insn[30:28] = zimm[10:8],
    //   insn[25]=zimm[5]=0 (vsew[2]=0, so SEW itself is not reserved).
    //   bit[28]=0 is fixed in template to avoid overlap with vsetivli.
    // Coverpoint: sample insn[30:28] when vsetvli (bit31=0), vsew[2]=0 (bit25=0).
    v_vsetvli_res : coverpoint ins.current.insn[30:28]
        iff (ins.current.insn[6:0] == 7'b1010111
           & ins.current.insn[14:12] == 3'b111
           & ins.current.insn[31] == 1'b0
           & ins.current.insn[25] == 1'b0) {
        // 2^3 = 8 bins; only 000 is legal (reserved upper bits must be zero)
    }

    // ── cp_v_vsetivli_sew ────────────────────────────────────────────
    // vsetivli with reserved SEW high bit.
    // Generator template: "1100RR1EERRRRRRRR111RRRRR1010111"
    //   insn[31:30]=11 (vsetivli), insn[29:28]=00 (reserved upper bits = 0),
    //   insn[25]=zimm[5]=1 (vsew[2]=1, reserved), E bits sweep insn[24:23].
    // Coverpoint: sample insn[24:23] when vsetivli, upper reserved=0, vsew[2]=1.
    v_vsetivli_sew : coverpoint ins.current.insn[24:23]
        iff (ins.current.insn[6:0] == 7'b1010111
           & ins.current.insn[14:12] == 3'b111
           & ins.current.insn[31:30] == 2'b11
           & ins.current.insn[29:28] == 2'b00
           & ins.current.insn[25] == 1'b1) {
        // 2^2 = 4 bins of reserved SEW values
    }

    // ── cp_v_vsetivli_res ────────────────────────────────────────────
    // vsetivli with reserved upper zimm bits (zimm[9:8] != 00).
    // Generator template: "11EERR0RRRRRRRRRR111RRRRR1010111"
    //   insn[31:30]=11 (vsetivli), E bits sweep insn[29:28] = zimm[9:8],
    //   insn[25]=zimm[5]=0 (vsew[2]=0, so SEW is not reserved).
    // Coverpoint: sample insn[29:28] when vsetivli, vsew[2]=0.
    v_vsetivli_res : coverpoint ins.current.insn[29:28]
        iff (ins.current.insn[6:0] == 7'b1010111
           & ins.current.insn[14:12] == 3'b111
           & ins.current.insn[31:30] == 2'b11
           & ins.current.insn[25] == 1'b0) {
        // 2^2 = 4 bins; only 00 is legal
    }

    // ══════════════════════════════════════════════════════════════════
    // Vector load/store reserved encoding coverpoints
    // ══════════════════════════════════════════════════════════════════

    // ── Vector load width/mew ────────────────────────────────────────
    // Vector load opcode = 0000111.  insn[28] = mew, insn[14:12] = width.
    // Generator sweeps all {mew, width} combinations for reserved widths.
    // Coverpoint: sample {mew, width[2:0]} = {insn[28], insn[14:12]}.
    vl_width : coverpoint {ins.current.insn[28], ins.current.insn[14:12]}
        iff (ins.current.insn[6:0] == 7'b0000111) {
        // 2^4 = 16 combinations; mew=0 + width ∈ {000,101,110,111} are reserved
        // if the corresponding EEW is unsupported; mew=1 all reserved.
    }

    // ── Vector load lumop ────────────────────────────────────────────
    // Unit-stride vector loads: insn[26]=nf[0]=1 selects the lumop field.
    // Generator template: "RRR0RR1EEEEERRRRR<width>RRRRR0000111"
    //   insn[28]=0 (mew=0), insn[27:26]=00 (unit-stride), E sweeps insn[24:20].
    // Coverpoint: sample insn[24:20] (lumop/rs2 field).
    vl_lumop : coverpoint ins.current.insn[24:20]
        iff (ins.current.insn[6:0] == 7'b0000111
           & ins.current.insn[28:26] == 3'b000) {
        // 2^5 = 32 bins; only 00000(unit), 01000(whole), 01011(mask), 10000(ff) legal
    }

    // ── Vector store width/mew ───────────────────────────────────────
    // Vector store opcode = 0100111.  Same structure as loads.
    vs_width : coverpoint {ins.current.insn[28], ins.current.insn[14:12]}
        iff (ins.current.insn[6:0] == 7'b0100111) {
    }

    // ── Vector store sumop ───────────────────────────────────────────
    vs_sumop : coverpoint ins.current.insn[24:20]
        iff (ins.current.insn[6:0] == 7'b0100111
           & ins.current.insn[28:26] == 3'b000) {
        // 2^5 = 32 bins; only 00000(unit), 01000(whole) legal for stores
    }

    // ══════════════════════════════════════════════════════════════════
    // Vector arithmetic funct6 coverpoints
    // ══════════════════════════════════════════════════════════════════
    //
    // Generator template for all: "EEEEEEERRRRRRRRRR<funct3>RRRRR1010111"
    //   E bits sweep insn[31:26] = funct6; funct3 selects the category.
    //   The generator runs each template 4 times (once per SEW: e8/e16/e32/e64),
    //   preceded by vsetivli to configure the vector unit.
    //
    // The coverpoints sample funct6.  The per-SEW cross is done in the
    // mode-specific coverage file using a SEW coverpoint derived from vtype CSR.

    // OPIVV: funct3 = 000
    v_IVV_f6 : coverpoint ins.current.insn[31:26]
        iff (ins.current.insn[6:0] == 7'b1010111 & ins.current.insn[14:12] == 3'b000) {
        // Narrowing Instructions and Widening Instructions are reserved at the max SEW only, so
        // SsstrictV tests should not run them.
        `ifdef ZVE32X_SUPPORTED
            ignore_bins vnsrl        = { 6'b101100 };
            ignore_bins vnsra        = { 6'b101101 };
            ignore_bins vnclipu      = { 6'b101110 };
            ignore_bins vnclip       = { 6'b101111 };
            ignore_bins vwredsumu    = { 6'b110000 };
            ignore_bins vwredsum     = { 6'b110001 };
        `endif
    }
    // OPFVV: funct3 = 001 — all defined instructions are FP (SEW-dependent)
    v_FVV_f6 : coverpoint ins.current.insn[31:26]
        iff (ins.current.insn[6:0] == 7'b1010111 & ins.current.insn[14:12] == 3'b001) {
        // All floating point operations are reserved at SEW = 8 (if they exist in the first place),
        // and possibly other SEWs depending on the configuration.
        `ifdef ZVE32F_SUPPORTED
            ignore_bins vfadd       = { 6'b000000 };
            ignore_bins vfredusum   = { 6'b000001 };
            ignore_bins vfsub       = { 6'b000010 };
            ignore_bins vfredosum   = { 6'b000011 };
            ignore_bins vfmin       = { 6'b000100 };
            ignore_bins vfredmin    = { 6'b000101 };
            ignore_bins vfmax       = { 6'b000110 };
            ignore_bins vfredmax    = { 6'b000111 };
            ignore_bins vfsgnj      = { 6'b001000 };
            ignore_bins vfsgnjn     = { 6'b001001 };
            ignore_bins vfsgnjx     = { 6'b001010 };
            ignore_bins vwfunary0   = { 6'b010000 };
            ignore_bins vfunary0    = { 6'b010010 };
            ignore_bins vfunary1    = { 6'b010011 };
            ignore_bins vmfeq       = { 6'b011000 };
            ignore_bins vmfle       = { 6'b011001 };
            ignore_bins vmflt       = { 6'b011011 };
            ignore_bins vmfne       = { 6'b011100 };
            ignore_bins vfdiv       = { 6'b100000 };
            ignore_bins vfmul       = { 6'b100100 };
            ignore_bins vfmadd      = { 6'b101000 };
            ignore_bins vfnmadd     = { 6'b101001 };
            ignore_bins vfmsub      = { 6'b101010 };
            ignore_bins vfnmsub     = { 6'b101011 };
            ignore_bins vfmacc      = { 6'b101100 };
            ignore_bins vfnmacc     = { 6'b101101 };
            ignore_bins vfmsac      = { 6'b101110 };
            ignore_bins vfnmsac     = { 6'b101111 };
            ignore_bins vfwadd      = { 6'b110000 };
            ignore_bins vfwredusum  = { 6'b110001 };
            ignore_bins vfwsub      = { 6'b110010 };
            ignore_bins vfwredosum  = { 6'b110011 };
            ignore_bins vfwadd_w    = { 6'b110100 };
            ignore_bins vfwsub_w    = { 6'b110110 };
            ignore_bins vfwmul      = { 6'b111000 };
            ignore_bins vfwmacc     = { 6'b111100 };
            ignore_bins vfwnmacc    = { 6'b111101 };
            ignore_bins vfwmsac     = { 6'b111110 };
            ignore_bins vfwnmsac    = { 6'b111111 };
        `endif
    }
    // OPMVV: funct3 = 010
    v_MVV_f6 : coverpoint ins.current.insn[31:26]
        iff (ins.current.insn[6:0] == 7'b1010111 & ins.current.insn[14:12] == 3'b010) {
        // Narrowing Instructions and Widening Instructions are reserved at the max SEW only, so
        // SsstrictV tests should not run them.
        `ifdef ZVE32X_SUPPORTED
            ignore_bins vxunary0    = { 6'b010010 }; // These are vzext and vsext which are not defined at SEW=8
            ignore_bins vwaddu      = { 6'b110000 };
            ignore_bins vwadd       = { 6'b110001 };
            ignore_bins vwsubu      = { 6'b110010 };
            ignore_bins vwsub       = { 6'b110011 };
            ignore_bins vwaddu_w    = { 6'b110100 };
            ignore_bins vwadd_w     = { 6'b110101 };
            ignore_bins vwsubu_w    = { 6'b110110 };
            ignore_bins vwsub_w     = { 6'b110111 };
            ignore_bins vwmulu      = { 6'b111000 };
            ignore_bins vwmulsu     = { 6'b111010 };
            ignore_bins vwmul       = { 6'b111011 };
            ignore_bins vwmaccu     = { 6'b111100 };
            ignore_bins vwmacc      = { 6'b111101 };
            ignore_bins vwmaccsu    = { 6'b111111 };
        `endif
    }
    // OPIVI: funct3 = 011
    v_IVI_f6 : coverpoint ins.current.insn[31:26]
        iff (ins.current.insn[6:0] == 7'b1010111 & ins.current.insn[14:12] == 3'b011) {
        // Narrowing Instructions and Widening Instructions are reserved at the max SEW only, so
        // SsstrictV tests should not run them.
        `ifdef ZVE32X_SUPPORTED
            ignore_bins vnsrl   = { 6'b101100 };
            ignore_bins vnsra   = { 6'b101101 };
            ignore_bins vnclipu = { 6'b101110 };
            ignore_bins vnclip  = { 6'b101111 };
        `endif
    }
    // OPIVX: funct3 = 100
    v_IVX_f6 : coverpoint ins.current.insn[31:26]
        iff (ins.current.insn[6:0] == 7'b1010111 & ins.current.insn[14:12] == 3'b100) {
        // Narrowing Instructions and Widening Instructions are reserved at the max SEW only, so
        // SsstrictV tests should not run them.
        `ifdef ZVE32X_SUPPORTED
            ignore_bins vnsrl   = { 6'b101100 };
            ignore_bins vnsra   = { 6'b101101 };
            ignore_bins vnclipu = { 6'b101110 };
            ignore_bins vnclip  = { 6'b101111 };
        `endif
    }
    // OPFVF: funct3 = 101 — all defined instructions are FP (SEW-dependent)
    v_FVF_f6 : coverpoint ins.current.insn[31:26]
        iff (ins.current.insn[6:0] == 7'b1010111 & ins.current.insn[14:12] == 3'b101) {
        // All floating point operations are reserved at SEW = 8 (if they exist in the first place),
        // and possibly other SEWs depending on the configuration.
        `ifdef ZVE32F_SUPPORTED
            ignore_bins vfadd        = { 6'b000000 };
            ignore_bins vfsub        = { 6'b000010 };
            ignore_bins vfmin        = { 6'b000100 };
            ignore_bins vfmax        = { 6'b000110 };
            ignore_bins vfsgnj       = { 6'b001000 };
            ignore_bins vfsgnjn      = { 6'b001001 };
            ignore_bins vfsgnjx      = { 6'b001010 };
            ignore_bins vfslide1up   = { 6'b001110 };
            ignore_bins vfslide1down = { 6'b001111 };
            ignore_bins vrfunary0    = { 6'b010000 };
            ignore_bins vfmerge      = { 6'b010111 };
            ignore_bins vmfeq        = { 6'b011000 };
            ignore_bins vmfle        = { 6'b011001 };
            ignore_bins vmflt        = { 6'b011011 };
            ignore_bins vmfne        = { 6'b011100 };
            ignore_bins vmfgt        = { 6'b011101 };
            ignore_bins vmfge        = { 6'b011111 };
            ignore_bins vfdiv        = { 6'b100000 };
            ignore_bins vfrdiv       = { 6'b100001 };
            ignore_bins vfmul        = { 6'b100100 };
            ignore_bins vfrsub       = { 6'b100111 };
            ignore_bins vfmadd       = { 6'b101000 };
            ignore_bins vfnmadd      = { 6'b101001 };
            ignore_bins vfmsub       = { 6'b101010 };
            ignore_bins vfnmsub      = { 6'b101011 };
            ignore_bins vfmacc       = { 6'b101100 };
            ignore_bins vfnmacc      = { 6'b101101 };
            ignore_bins vfmsac       = { 6'b101110 };
            ignore_bins vfnmsac      = { 6'b101111 };
            ignore_bins vfwadd       = { 6'b110000 };
            ignore_bins vfwsub       = { 6'b110010 };
            ignore_bins vfwadd_w     = { 6'b110100 };
            ignore_bins vfwsub_w     = { 6'b110110 };
            ignore_bins vfwmul       = { 6'b111000 };
            ignore_bins vfwmacc      = { 6'b111100 };
            ignore_bins vfwnmacc     = { 6'b111101 };
            ignore_bins vfwmsac      = { 6'b111110 };
            ignore_bins vfwnmsac     = { 6'b111111 };
        `endif
    }
    // OPMVX: funct3 = 110
    v_MVX_f6 : coverpoint ins.current.insn[31:26]
        iff (ins.current.insn[6:0] == 7'b1010111 & ins.current.insn[14:12] == 3'b110) {
        // Widening Instructions are reserved at the max SEW only, so SsstrictV tests should not run them.
        `ifdef ZVE32X_SUPPORTED
            ignore_bins vwaddu      = { 6'b110000 };
            ignore_bins vwadd       = { 6'b110001 };
            ignore_bins vwsubu      = { 6'b110010 };
            ignore_bins vwsub       = { 6'b110011 };
            ignore_bins vwaddu_w    = { 6'b110100 };
            ignore_bins vwadd_w     = { 6'b110101 };
            ignore_bins vwsubu_w    = { 6'b110110 };
            ignore_bins vwsub_w     = { 6'b110111 };
            ignore_bins vwmulu      = { 6'b111000 };
            ignore_bins vwmulsu     = { 6'b111010 };
            ignore_bins vwmul       = { 6'b111011 };
            ignore_bins vwmaccu     = { 6'b111100 };
            ignore_bins vwmacc      = { 6'b111101 };
            ignore_bins vwmaccus    = { 6'b111110 };
            ignore_bins vwmaccsu    = { 6'b111111 };
        `endif
    }

    // ══════════════════════════════════════════════════════════════════
    // Vector unary instruction coverpoints
    // ══════════════════════════════════════════════════════════════════
    //
    // Unary vector instructions encode the operation type in vs1 (insn[19:15])
    // or vs2 (insn[24:20]), with the vm bit (insn[25]) as part of the encoding
    // space.  The funct6 field (insn[31:26]) identifies the unary group.
    //
    // Generator templates include the vm bit as the first E bit:
    //   "010000ERRRRREEEEE010RRRRR1010111"  — E at bit 25 (vm), E at bits [19:15]
    // So the coverpoint must include {insn[25], insn[19:15]} (6 bits) for
    // vs1-encoded types, or {insn[25], insn[24:20]} for vs2-encoded types.

    // VWRXUNARY0: funct6=010000, funct3=010 (OPMVV), type in {vm,vs1}
    // Generator: "010000ERRRRREEEEE010RRRRR1010111"
    v_VWRXUNARY0 : coverpoint {ins.current.insn[25], ins.current.insn[19:15]}
        iff (ins.current.insn[6:0] == 7'b1010111
           & ins.current.insn[14:12] == 3'b010
           & ins.current.insn[31:26] == 6'b010000) {
        // 2^6 = 64 bins
    }

    // VRXUNARY0: funct6=010000, funct3=110 (OPMVX), type in {vm,vs2}
    // Generator: "010000EEEEEERRRRR110RRRRR1010111"
    v_VRXUNARY0 : coverpoint {ins.current.insn[25], ins.current.insn[24:20]}
        iff (ins.current.insn[6:0] == 7'b1010111
           & ins.current.insn[14:12] == 3'b110
           & ins.current.insn[31:26] == 6'b010000) {
        // 2^6 = 64 bins
    }

    // VXUNARY0: funct6=010010, funct3=010 (OPMVV), type in {vm,vs1}
    // Generator: "010010ERRRRREEEEE010RRRRR1010111"
    v_VXUNARY0 : coverpoint {ins.current.insn[25], ins.current.insn[19:15]}
        iff (ins.current.insn[6:0] == 7'b1010111
           & ins.current.insn[14:12] == 3'b010
           & ins.current.insn[31:26] == 6'b010010) {
        // 2^6 = 64 bins
    }

    // VMUNARY0: funct6=010100, funct3=010 (OPMVV), type in {vm,vs1}
    // Generator: "010100ERRRRREEEEE010RRRRR1010111"
    v_VMUNARY0 : coverpoint {ins.current.insn[25], ins.current.insn[19:15]}
        iff (ins.current.insn[6:0] == 7'b1010111
           & ins.current.insn[14:12] == 3'b010
           & ins.current.insn[31:26] == 6'b010100) {
        // 2^6 = 64 bins
    }

    // VWFUNARY0: funct6=010000, funct3=001 (OPFVV), type in {vm,vs1}
    // Generator: "010000ERRRRREEEEE001RRRRR1010111"
    v_VWFUNARY0 : coverpoint {ins.current.insn[25], ins.current.insn[19:15]}
        iff (ins.current.insn[6:0] == 7'b1010111
           & ins.current.insn[14:12] == 3'b001
           & ins.current.insn[31:26] == 6'b010000) {
        // 2^6 = 64 bins
    }

    // VRFUNARY0: funct6=010000, funct3=101 (OPFVF), type in {vm,vs2}
    // Generator: "010000EEEEEERRRRR101RRRRR1010111"
    v_VRFUNARY0 : coverpoint {ins.current.insn[25], ins.current.insn[24:20]}
        iff (ins.current.insn[6:0] == 7'b1010111
           & ins.current.insn[14:12] == 3'b101
           & ins.current.insn[31:26] == 6'b010000) {
        // 2^6 = 64 bins
    }

    // VFUNARY0: funct6=010010, funct3=001 (OPFVV), type in {vm,vs1}
    // Generator: "010010ERRRRREEEEE001RRRRR1010111"
    v_VFUNARY0 : coverpoint {ins.current.insn[25], ins.current.insn[19:15]}
        iff (ins.current.insn[6:0] == 7'b1010111
           & ins.current.insn[14:12] == 3'b001
           & ins.current.insn[31:26] == 6'b010010) {
        // 2^6 = 64 bins
    }

    // VFUNARY1: funct6=010011, funct3=001 (OPFVV), type in {vm,vs1}
    // Generator: "010011ERRRRREEEEE001RRRRR1010111"
    v_VFUNARY1 : coverpoint {ins.current.insn[25], ins.current.insn[19:15]}
        iff (ins.current.insn[6:0] == 7'b1010111
           & ins.current.insn[14:12] == 3'b001
           & ins.current.insn[31:26] == 6'b010011) {
        // 2^6 = 64 bins
    }

    // ══════════════════════════════════════════════════════════════════
    // Vector crypto coverpoints
    // ══════════════════════════════════════════════════════════════════

    // OPVE (general vector crypto op6 and op3)
    // Generator: "EEEEEEERRRRRRRRRREEERRRRR1110111"
    v_vopve : coverpoint {ins.current.insn[31:25], ins.current.insn[14:12]}
        iff (ins.current.insn[6:0] == 7'b1110111) {
        // 2^7 * 2^3 = 1024 bins
    }

    // vaes.vv: funct6=101000, funct3=010 (OPMVV), type in {vm,vs1}
    // Generator: "101000ERRRRREEEEE010RRRRR1110111"
    v_vaesvv : coverpoint {ins.current.insn[25], ins.current.insn[19:15]}
        iff (ins.current.insn[6:0] == 7'b1110111
           & ins.current.insn[14:12] == 3'b010
           & ins.current.insn[31:26] == 6'b101000) {
        // 2^6 = 64 bins
    }

    // vaes.vs: funct6=101001, funct3=010 (OPMVV), type in {vm,vs1}
    // Generator: "101001ERRRRREEEEE010RRRRR1110111"
    v_vaesvs : coverpoint {ins.current.insn[25], ins.current.insn[19:15]}
        iff (ins.current.insn[6:0] == 7'b1110111
           & ins.current.insn[14:12] == 3'b010
           & ins.current.insn[31:26] == 6'b101001) {
        // 2^6 = 64 bins
    }


    // ══════════════════════════════════════════════════════════════════
    // SEW coverpoint for per-SEW crosses
    // ══════════════════════════════════════════════════════════════════
    //
    // The generator emits vsetivli x0, 1, eN, m1, ta, ma before each SEW
    // group, so the current SEW is reflected in the vtype CSR.  This
    // coverpoint reads vsew from vtype[5:3].

    current_vsew : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_CURRENT, "vtype", "vsew")[2:0] {
        bins e8  = {3'b000};
        bins e16 = {3'b001};
        bins e32 = {3'b010};
        bins e64 = {3'b011};
        // 100-111 are reserved
    }
