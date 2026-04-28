        "INSTR"     : begin
            ins.add_rd(0);
            ins.add_mem_offset(1);
            ins.add_rs1_sp();
            ins.current.inst_category = INST_CAT_LOAD;
            ins.add_mem_address();
        end
