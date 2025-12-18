# lr.w.S
# custom tests for load reserved

# cp_custom_aqrl
# test acquire and release modifiers
    la t0, scratch
    li t2, 0x12345678
    sw t2, 0(t0)
    lr.w t1, (t0)
    lr.w.aq t2, (t0)
    lr.w.aqrl t3, (t0)
    RVTEST_SIGUPD(SIGPOINTER, t1)
    RVTEST_SIGUPD(SIGPOINTER, t2)
    RVTEST_SIGUPD(SIGPOINTER, t3)

   # cp_custom_rd_edges
    li t4, 0x0
    sw t4, 0(t0)
    sw zero, 4(t0)
    lr.w t1, (t0)   # lr t1 = 0
    RVTEST_SIGUPD(SIGPOINTER, t1)

    li t4, 0x1
    sw t4, 0(t0)
    lr.w t1, (t0)   # lr t1 = 1
    RVTEST_SIGUPD(SIGPOINTER, t1)

    li t4, 0xFFFFFFFF
    sw t4, 0(t0)
    lr.w t1, (t0)   # lr t1 = FFFFFFFF (sign-extended in RV64)
    RVTEST_SIGUPD(SIGPOINTER, t1)
