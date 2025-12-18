# sc.w.S
# custom tests for store conditional

# cp_custom_aqrl
# test acquire and release modifiers
    la t0, scratch
    li t2, 0xF2345678
    sc.w t1, t2, (t0)
    sc.w.rl t3, t2, (t0)
    sc.w.aqrl t4, t2, (t0)
    RVTEST_SIGUPD(SIGPOINTER, t1)
    RVTEST_SIGUPD(SIGPOINTER, t3)
    RVTEST_SIGUPD(SIGPOINTER, t4)

# cp_custom_sc_lrsc
    li t3, 0x23456789
    li t4, 0x3456789A

    # should succeed
    lr.w t1, (t0)
    sc.w t2, t3, (t0)
    RVTEST_SIGUPD(SIGPOINTER, t2)

    # should fail because of intervening sc
    lr.w t1, (t0)
    sc.w t2, t3, (t0) # succeeds
    sc.w t5, t4, (t0) # fails
    RVTEST_SIGUPD(SIGPOINTER, t2)
    RVTEST_SIGUPD(SIGPOINTER, t5)


# cp_custom_sc_after_store
    # should not care about intervening stores
    lr.w t1, (t0)
    sb t3, 3(t0)      # store byte
    sc.w t5, t4, (t0) # succeeds
    RVTEST_SIGUPD(SIGPOINTER, t5)

    lr.w t1, (t0)
    sh t3, 2(t0)      # store half
    sc.w t5, t4, (t0) # succeeds
    RVTEST_SIGUPD(SIGPOINTER, t5)

    lr.w t1, (t0)
    sw t3, 0(t0)      # store word
    sc.w t5, t4, (t0) # succeeds
    RVTEST_SIGUPD(SIGPOINTER, t5)

    #ifdef __riscv_xlen
        #if __riscv_xlen == 64
            lr.w t1, (t0)
            sd t3, 0(t0)      # store double
            sc.w t5, t4, (t0) # succeeds
            RVTEST_SIGUPD(SIGPOINTER, t5)
        #endif
    #else
        ERROR: __riscv_xlen not defined
    #endif

# cp_custom_sc_after_load
    # should not care about intervening loads

    lr.w t1, (t0)
    lb t3, 3(t0)      # load byte
    sc.w t5, t4, (t0) # succeeds
    RVTEST_SIGUPD(SIGPOINTER, t5)

    lr.w t1, (t0)
    lb t3, 128(t0)      # load byte
    sc.w t5, t4, (t0) # succeeds
    RVTEST_SIGUPD(SIGPOINTER, t5)

    lr.w t1, (t0)
    lbu t3, 2(t0)      # load byte unsigned
    sc.w t5, t4, (t0) # succeeds
    RVTEST_SIGUPD(SIGPOINTER, t5)

    lr.w t1, (t0)
    lbu t3, 128(t0)      # load byte unsigned
    sc.w t5, t4, (t0) # succeeds
    RVTEST_SIGUPD(SIGPOINTER, t5)

    lr.w t1, (t0)
    lh t3, 2(t0)      # load half
    sc.w t5, t4, (t0) # succeeds
    RVTEST_SIGUPD(SIGPOINTER, t5)

    lr.w t1, (t0)
    lh t3, 128(t0)      # load half
    sc.w t5, t4, (t0) # succeeds
    RVTEST_SIGUPD(SIGPOINTER, t5)

    lr.w t1, (t0)
    lhu t3, 0(t0)      # load half unsigned
    sc.w t5, t4, (t0) # succeeds
    RVTEST_SIGUPD(SIGPOINTER, t5)

    lr.w t1, (t0)
    lhu t3, 128(t0)      # load half unsigned
    sc.w t5, t4, (t0) # succeeds
    RVTEST_SIGUPD(SIGPOINTER, t5)

    lr.w t1, (t0)
    lw t3, 0(t0)      # load word
    sc.w t5, t4, (t0) # succeeds
    RVTEST_SIGUPD(SIGPOINTER, t5)

    lr.w t1, (t0)
    lw t3, 128(t0)      # load word
    sc.w t5, t4, (t0) # succeeds
    RVTEST_SIGUPD(SIGPOINTER, t5)

    #ifdef __riscv_xlen
        #if __riscv_xlen == 64
            lr.w t1, (t0)
            lwu t3, 0(t0)      # load word unsigned
            sc.w t5, t4, (t0) # succeeds
            RVTEST_SIGUPD(SIGPOINTER, t5)

            lr.w t1, (t0)
            lwu t3, 128(t0)      # load word unsigned
            sc.w t5, t4, (t0) # succeeds
            RVTEST_SIGUPD(SIGPOINTER, t5)

            lr.w t1, (t0)
            ld t3, 0(t0)      # load double
            sc.w t5, t4, (t0) # succeeds
            RVTEST_SIGUPD(SIGPOINTER, t5)

            lr.w t1, (t0)
            ld t3, 128(t0)      # load double
            sc.w t5, t4, (t0) # succeeds
            RVTEST_SIGUPD(SIGPOINTER, t5)

        #endif
    #else
        ERROR: __riscv_xlen not defined
    #endif

 #cp_custom_sc_addresses
    # cp_address_difference

    li t3, 0x12345678

    addi t1, t0, 8 # address difference of 8
    lr.w t2, (t0)
    sc.w t4, t3, (t1)
    RVTEST_SIGUPD(SIGPOINTER, t4)

    addi t1, t0, 16 # address difference of 16
    lr.w t2, (t0)
    sc.w t4, t3, (t1)
    RVTEST_SIGUPD(SIGPOINTER, t4)

    addi t1, t0, 24 # address difference of 24
    lr.w t2, (t0)
    sc.w t4, t3, (t1)
    RVTEST_SIGUPD(SIGPOINTER, t4)

    addi t1, t0, 32 # address difference of 32
    lr.w t2, (t0)
    sc.w t4, t3, (t1)
    RVTEST_SIGUPD(SIGPOINTER, t4)

    addi t1, t0, 40 # address difference of 40
    lr.w t2, (t0)
    sc.w t4, t3, (t1)
    RVTEST_SIGUPD(SIGPOINTER, t4)

    addi t1, t0, 48 # address difference of 48
    lr.w t2, (t0)
    sc.w t4, t3, (t1)
    RVTEST_SIGUPD(SIGPOINTER, t4)

    addi t1, t0, 56 # address difference of 56
    lr.w t2, (t0)
    sc.w t4, t3, (t1)
    RVTEST_SIGUPD(SIGPOINTER, t4)

    addi t1, t0, 64 # address difference of 64
    lr.w t2, (t0)
    sc.w t4, t3, (t1)
    RVTEST_SIGUPD(SIGPOINTER, t4)

    addi t1, t0, 72 # address difference of 72
    lr.w t2, (t0)
    sc.w t4, t3, (t1)
    RVTEST_SIGUPD(SIGPOINTER, t4)

    addi t1, t0, 80 # address difference of 80
    lr.w t2, (t0)
    sc.w t4, t3, (t1)
    RVTEST_SIGUPD(SIGPOINTER, t4)

    addi t1, t0, 88 # address difference of 88
    lr.w t2, (t0)
    sc.w t4, t3, (t1)
    RVTEST_SIGUPD(SIGPOINTER, t4)

    addi t1, t0, 96 # address difference of 96
    lr.w t2, (t0)
    sc.w t4, t3, (t1)
    RVTEST_SIGUPD(SIGPOINTER, t4)

    addi t1, t0, 104 # address difference of 104
    lr.w t2, (t0)
    sc.w t4, t3, (t1)
    RVTEST_SIGUPD(SIGPOINTER, t4)

    addi t1, t0, 112 # address difference of 112
    lr.w t2, (t0)
    sc.w t4, t3, (t1)
    RVTEST_SIGUPD(SIGPOINTER, t4)

    addi t1, t0, 120 # address difference of 120
    lr.w t2, (t0)
    sc.w t4, t3, (t1)
    RVTEST_SIGUPD(SIGPOINTER, t4)


# cp_custom_sc_after_sc
    li x29, 0xbb6e9d42 # initialize rs2
    li x28, 0xa4c321f4 # initialize rs2
    la t0, scratch # rs1 = base address
    lr.w t2, (t0)
    sc.w x7, x29, (t0) # perform operation
    sc.w x8, x28, (t0) # perform operation
    RVTEST_SIGUPD(SIGPOINTER, x7)
    RVTEST_SIGUPD(SIGPOINTER, x8)
