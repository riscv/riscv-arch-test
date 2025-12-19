# lr.d.S
# custom tests for load reserved

# cp_custom_aqrl
# test acquire and release modifiers
    la t0, scratch
    li t2, 0x123456789ABCDEF0
    sd t2, 0(t0)
    lr.d t1, (t0)
    lr.d.aq t2, (t0)
    lr.d.aqrl t3, (t0)
    RVTEST_SIGUPD(SIGPOINTER, t1)
    RVTEST_SIGUPD(SIGPOINTER, t2)
    RVTEST_SIGUPD(SIGPOINTER, t3)

# cp_custom_rd_edges
    li t4, 0x0
    sd t4, 0(t0)
    lr.d t1, (t0)   # lr t1 = 0
    RVTEST_SIGUPD(SIGPOINTER, t1)

    li t4, 0x1
    sd t4, 0(t0)
    lr.d t1, (t0)   # lr t1 = 1
    RVTEST_SIGUPD(SIGPOINTER, t1)

    li t4, 0x00000000FFFFFFFF
    sd t4, 0(t0)
    lr.d t1, (t0)   # lr t1 = 00000000FFFFFFFF
    RVTEST_SIGUPD(SIGPOINTER, t1)

    li t4, 0xFFFFFFFFFFFFFFFF
    sd t4, 0(t0)
    lr.d t1, (t0)   # lr t1 = FFFFFFFFFFFFFFFF
    RVTEST_SIGUPD(SIGPOINTER, t1)
