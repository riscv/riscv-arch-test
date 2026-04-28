        "INSTR"     : begin
            ins.add_rd(0);
            ins.add_rs2(1);
            ins.add_rs1(2);
            ins.current.inst_category = INST_CAT_STORE;
        end
