    cmp_fd_fs1 : coverpoint ins.get_fpr_reg(ins.current.fd)  iff (ins.current.fd == ins.current.fs1 & ins.trap == 0 )  {
        // FD and FS1 register (assignment) WAR Hazard
    }
