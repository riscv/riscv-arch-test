// //////////////////////////////////////////////////////////////////////////////////////////////////////////
// cp_vtype_walking1s
// //////////////////////////////////////////////////////////////////////////////////////////////////////////

    // Walking 1s on rs2 of vsetvl to confirm all XLEN bits are checked
    rs1_nonzero: coverpoint (ins.current.rs1_val != 0) {
        bins nonzero = {1'b1};
    }

    // Low bits [7:0] - valid vtype fields (vlmul, vsew, vta, vma)
    rs2_walking1s_low: coverpoint ins.current.rs2_val[7:0] iff (ins.current.rs1_val != 0) {
        bins bit0 = {8'h01};
        bins bit1 = {8'h02};
        bins bit2 = {8'h04};
        bins bit3 = {8'h08};
        bins bit4 = {8'h10};
        bins bit5 = {8'h20};
        bins bit6 = {8'h40};
        bins bit7 = {8'h80};
    }

    // High bits [XLEN-1:8] - reserved bits that should set vill
    `ifdef XLEN64
    rs2_walking1s_high: coverpoint ins.current.rs2_val iff (ins.current.rs1_val != 0) {
        bins bit8  = {64'h0000_0000_0000_0100};
        bins bit9  = {64'h0000_0000_0000_0200};
        bins bit10 = {64'h0000_0000_0000_0400};
        bins bit11 = {64'h0000_0000_0000_0800};
        bins bit12 = {64'h0000_0000_0000_1000};
        bins bit13 = {64'h0000_0000_0000_2000};
        bins bit14 = {64'h0000_0000_0000_4000};
        bins bit15 = {64'h0000_0000_0000_8000};
        bins bit16 = {64'h0000_0000_0001_0000};
        bins bit17 = {64'h0000_0000_0002_0000};
        bins bit18 = {64'h0000_0000_0004_0000};
        bins bit19 = {64'h0000_0000_0008_0000};
        bins bit20 = {64'h0000_0000_0010_0000};
        bins bit21 = {64'h0000_0000_0020_0000};
        bins bit22 = {64'h0000_0000_0040_0000};
        bins bit23 = {64'h0000_0000_0080_0000};
        bins bit24 = {64'h0000_0000_0100_0000};
        bins bit25 = {64'h0000_0000_0200_0000};
        bins bit26 = {64'h0000_0000_0400_0000};
        bins bit27 = {64'h0000_0000_0800_0000};
        bins bit28 = {64'h0000_0000_1000_0000};
        bins bit29 = {64'h0000_0000_2000_0000};
        bins bit30 = {64'h0000_0000_4000_0000};
        bins bit31 = {64'h0000_0000_8000_0000};
        bins bit32 = {64'h0000_0001_0000_0000};
        bins bit33 = {64'h0000_0002_0000_0000};
        bins bit34 = {64'h0000_0004_0000_0000};
        bins bit35 = {64'h0000_0008_0000_0000};
        bins bit36 = {64'h0000_0010_0000_0000};
        bins bit37 = {64'h0000_0020_0000_0000};
        bins bit38 = {64'h0000_0040_0000_0000};
        bins bit39 = {64'h0000_0080_0000_0000};
        bins bit40 = {64'h0000_0100_0000_0000};
        bins bit41 = {64'h0000_0200_0000_0000};
        bins bit42 = {64'h0000_0400_0000_0000};
        bins bit43 = {64'h0000_0800_0000_0000};
        bins bit44 = {64'h0000_1000_0000_0000};
        bins bit45 = {64'h0000_2000_0000_0000};
        bins bit46 = {64'h0000_4000_0000_0000};
        bins bit47 = {64'h0000_8000_0000_0000};
        bins bit48 = {64'h0001_0000_0000_0000};
        bins bit49 = {64'h0002_0000_0000_0000};
        bins bit50 = {64'h0004_0000_0000_0000};
        bins bit51 = {64'h0008_0000_0000_0000};
        bins bit52 = {64'h0010_0000_0000_0000};
        bins bit53 = {64'h0020_0000_0000_0000};
        bins bit54 = {64'h0040_0000_0000_0000};
        bins bit55 = {64'h0080_0000_0000_0000};
        bins bit56 = {64'h0100_0000_0000_0000};
        bins bit57 = {64'h0200_0000_0000_0000};
        bins bit58 = {64'h0400_0000_0000_0000};
        bins bit59 = {64'h0800_0000_0000_0000};
        bins bit60 = {64'h1000_0000_0000_0000};
        bins bit61 = {64'h2000_0000_0000_0000};
        bins bit62 = {64'h4000_0000_0000_0000};
        bins bit63 = {64'h8000_0000_0000_0000};
    }
    `else
    rs2_walking1s_high: coverpoint ins.current.rs2_val iff (ins.current.rs1_val != 0) {
        bins bit8  = {32'h0000_0100};
        bins bit9  = {32'h0000_0200};
        bins bit10 = {32'h0000_0400};
        bins bit11 = {32'h0000_0800};
        bins bit12 = {32'h0000_1000};
        bins bit13 = {32'h0000_2000};
        bins bit14 = {32'h0000_4000};
        bins bit15 = {32'h0000_8000};
        bins bit16 = {32'h0001_0000};
        bins bit17 = {32'h0002_0000};
        bins bit18 = {32'h0004_0000};
        bins bit19 = {32'h0008_0000};
        bins bit20 = {32'h0010_0000};
        bins bit21 = {32'h0020_0000};
        bins bit22 = {32'h0040_0000};
        bins bit23 = {32'h0080_0000};
        bins bit24 = {32'h0100_0000};
        bins bit25 = {32'h0200_0000};
        bins bit26 = {32'h0400_0000};
        bins bit27 = {32'h0800_0000};
        bins bit28 = {32'h1000_0000};
        bins bit29 = {32'h2000_0000};
        bins bit30 = {32'h4000_0000};
        bins bit31 = {32'h8000_0000};
    }
    `endif

    // vill set after instruction (expected for high bits)
    vill_after: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "vtype", "vill") {
        bins set = {1};
        bins clear = {0};
    }

    cp_vtype_walking1s_low: cross rs1_nonzero, rs2_walking1s_low, vill_after;

    cp_vtype_walking1s_high: cross rs1_nonzero, rs2_walking1s_high, vill_after;

//// end cp_vtype_walking1s ///////////////////////////////////////////////////////////////////////////
