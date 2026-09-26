        "INSTR"     : begin
            ins.add_rs2(0);
            ins.add_rs1(1);
            ins.current.inst_category = INST_CAT_STORE;
            ins.add_mem_address();
        end
