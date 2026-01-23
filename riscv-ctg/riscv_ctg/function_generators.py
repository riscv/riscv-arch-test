def get_cond_generator(opcode,fmt,val_vars,xlen,flen):
    def fr64_generator(req_val_comb):
        def condition(*argv):
            rs1_val = argv[0]
            rs2_val = argv[1]
            rm = argv[2]
            bin_val = '{:064b}'.format(rs1_val)
            fs1 = int(bin_val[0],2)
            fe1 = int(bin_val[1:12],2)
            fm1 = int(bin_val[12:],2)
            bin_val = '{:064b}'.format(rs2_val)
            fs2 = int(bin_val[0],2)
            fe2 = int(bin_val[1:12],2)
            fm2 = int(bin_val[12:],2)
            return eval(req_val_comb)
        return condition

    def fr32_generator(req_val_comb):
        def condition(*argv):
            rs1_val = argv[0]
            rs2_val = argv[1]
            rm = argv[2]
            bin_val = '{:032b}'.format(rs1_val)
            fs1 = int(bin_val[0],2)
            fe1 = int(bin_val[1:9],2)
            fm1 = int(bin_val[9:],2)
            bin_val = '{:032b}'.format(rs2_val)
            fs2 = int(bin_val[0],2)
            fe2 = int(bin_val[1:9],2)
            fm2 = int(bin_val[9:],2)
            return eval(req_val_comb)
        return condition
        
    def fsr64_generator(req_val_comb):
        def condition(*argv):
            rs1_val = argv[0]
            rm = argv[1]
            bin_val = '{:064b}'.format(rs1_val)
            fs1 = int(bin_val[0],2)
            fe1 = int(bin_val[1:12],2)
            fm1 = int(bin_val[12:],2)
            return eval(req_val_comb)
        return condition

    def fsr32_generator(req_val_comb):
        def condition(*argv):
            rs1_val = argv[0]
            rm = argv[1]
            bin_val = '{:032b}'.format(rs1_val)
            fs1 = int(bin_val[0],2)
            fe1 = int(bin_val[1:9],2)
            fm1 = int(bin_val[9:],2)
            return eval(req_val_comb)
        return condition   
        
    def fr4_64_generator(req_val_comb):
        def condition(*argv):
            rs1_val = argv[0]
            rs2_val = argv[1]
            rs3_val = argv[2]
            rm = argv[3]
            bin_val = '{:064b}'.format(rs1_val)
            fs1 = int(bin_val[0],2)
            fe1 = int(bin_val[1:12],2)
            fm1 = int(bin_val[12:],2)
            bin_val = '{:064b}'.format(rs2_val)
            fs2 = int(bin_val[0],2)
            fe2 = int(bin_val[1:12],2)
            fm2 = int(bin_val[12:],2)
            bin_val = '{:064b}'.format(rs3_val)
            fs3 = int(bin_val[0],2)
            fe3 = int(bin_val[1:12],2)
            fm3 = int(bin_val[12:],2)
            return eval(req_val_comb)
        return condition

    def fr4_32_generator(req_val_comb):
        def condition(*argv):
            rs1_val = argv[0]
            rs2_val = argv[1]
            rs3_val = argv[2]
            rm = argv[3]
            bin_val = '{:032b}'.format(rs1_val)
            fs1 = int(bin_val[0],2)
            fe1 = int(bin_val[1:9],2)
            fm1 = int(bin_val[9:],2)
            bin_val = '{:032b}'.format(rs2_val)
            fs2 = int(bin_val[0],2)
            fe2 = int(bin_val[1:9],2)
            fm2 = int(bin_val[9:],2)
            bin_val = '{:032b}'.format(rs3_val)
            fs3 = int(bin_val[0],2)
            fe3 = int(bin_val[1:9],2)
            fm3 = int(bin_val[9:],2)
            return eval(req_val_comb)
        return condition     

    def i_generator(req_val_comb):
        def condition(*argv):
            for var,val in zip(val_vars,argv):
                locals()[var]=val
            return eval(req_val_comb)
        return condition

    if opcode[0] == 'f' and 'fence' not in opcode:
      if fmt == 'frformat':
        if flen == 32:
            return fr32_generator
        else:
            return fr64_generator
      elif fmt == 'fsrformat':
        if flen == 32:
            return fsr32_generator
        else:
            return fsr64_generator    
      elif fmt == 'fr4format':
        if flen == 32:
            return fr4_32_generator
        else:
            return fr4_64_generator                   
    else:
        return i_generator

def get_filter_generator(opcode,fmt,val_vars,xlen,flen):
    def fr64_generator(argv):
        bin_val1 = '{:064b}'.format(argv[0])
        bin_val2 = '{:064b}'.format(argv[1])
        local = {
        'rs1_val': argv[0]
        ,'rs2_val': argv[1]
        ,'rm': argv[2]
        ,'fs1': int(bin_val1[0],2)
        ,'fe1': int(bin_val1[1:12],2)
        ,'fm1': int(bin_val1[12:],2)
        ,'fs2': int(bin_val2[0],2)
        ,'fe2': int(bin_val2[1:12],2)
        ,'fm2': int(bin_val2[12:],2)
        }
        def filter_func(cond):
            return eval(cond,{},local)
        return filter_func

    def fr32_generator(argv):
        bin_val1 = '{:032b}'.format(argv[0])
        bin_val2 = '{:032b}'.format(argv[1])
        local = {
        'rs1_val': argv[0]
        ,'rs2_val': argv[1]
        ,'rm': argv[2]
        ,'fs1': int(bin_val1[0],2)
        ,'fe1': int(bin_val1[1:9],2)
        ,'fm1': int(bin_val1[9:],2)
        ,'fs2': int(bin_val2[0],2)
        ,'fe2': int(bin_val2[1:9],2)
        ,'fm2': int(bin_val2[9:],2)
        }
        def filter_func(cond):
            return eval(cond,{},local)
        return filter_func

    def fsr64_generator(argv):
        bin_val1 = '{:064b}'.format(argv[0])
        local = {
        'rs1_val': argv[0]
        ,'rm': argv[1]
        ,'fs1': int(bin_val1[0],2)
        ,'fe1': int(bin_val1[1:12],2)
        ,'fm1': int(bin_val1[12:],2)
        }
        def filter_func(cond):
            return eval(cond,{},local)
        return filter_func

    def fsr32_generator(argv):
        bin_val1 = '{:032b}'.format(argv[0])
        local = {
        'rs1_val': argv[0]
        ,'rm': argv[1]
        ,'fs1': int(bin_val1[0],2)
        ,'fe1': int(bin_val1[1:9],2)
        ,'fm1': int(bin_val1[9:],2)
        }
        def filter_func(cond):
            return eval(cond,{},local)
        return filter_func

    def fr4_64_generator(argv):
        bin_val1 = '{:064b}'.format(argv[0])
        bin_val2 = '{:064b}'.format(argv[1])
        bin_val3 = '{:064b}'.format(argv[2])
        local = {
        'rs1_val': argv[0]
        ,'rs2_val': argv[1]
        ,'rs3_val': argv[2]
        ,'rm': argv[3]
        ,'fs1': int(bin_val1[0],2)
        ,'fe1': int(bin_val1[1:12],2)
        ,'fm1': int(bin_val1[12:],2)
        ,'fs2': int(bin_val2[0],2)
        ,'fe2': int(bin_val2[1:12],2)
        ,'fm2': int(bin_val2[12:],2)
        ,'fs3': int(bin_val3[0],2)
        ,'fe3': int(bin_val3[1:12],2)
        ,'fm3': int(bin_val3[12:],2)
        }
        def filter_func(cond):
            return eval(cond,{},local)
        return filter_func

    def fr4_32_generator(argv):
        bin_val1 = '{:032b}'.format(argv[0])
        bin_val2 = '{:032b}'.format(argv[1])
        bin_val3 = '{:032b}'.format(argv[2])
        local = {
        'rs1_val': argv[0]
        ,'rs2_val': argv[1]
        ,'rs3_val': argv[2]
        ,'rm': argv[3]
        ,'fs1': int(bin_val1[0],2)
        ,'fe1': int(bin_val1[1:9],2)
        ,'fm1': int(bin_val1[9:],2)
        ,'fs2': int(bin_val2[0],2)
        ,'fe2': int(bin_val2[1:9],2)
        ,'fm2': int(bin_val2[9:],2)
        ,'fs3': int(bin_val3[0],2)
        ,'fe3': int(bin_val3[1:9],2)
        ,'fm3': int(bin_val3[9:],2)
        }
        def filter_func(cond):
            return eval(cond,{},local)
        return filter_func


    def i_generator(argv):
        local = {}
        for var,val in zip(val_vars,argv):
            local[var]=val
        def condition(req_val_comb):
            return eval(req_val_comb,{},local)
        return condition

    if opcode[0] == 'f' and 'fence' not in opcode:
      if fmt == 'frformat':
        if flen == 32:
            return fr32_generator
        else:
            return fr64_generator
      elif fmt == 'fsrformat':
        if flen == 32:
            return fsr32_generator
        else:
            return fsr64_generator    
      elif fmt == 'fr4format':
        if flen == 32:
            return fr4_32_generator
        else:
            return fr4_64_generator                   
    else:
        return i_generator

