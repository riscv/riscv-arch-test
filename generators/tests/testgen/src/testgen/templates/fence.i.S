# fence.i.S
# custom tests for fence.i

    LI(t2, 3)         # t2 = 3
    LA(t3, selfmodify)
    LA(t1, adds)      # t1 = address of the replacement instruction
    lw t1, 0(t1)      # t1 = encoded instruction "addi t2, t2, 5"
    sw t1, 0(t3)      # store it at selfmodify
    fence.i           # synchronize self-modified code so addi uses 5 rather than 1
selfmodify:           # after modification, should compute t2 = 8 rather than t2 = 4
    addi t2, t2, 1  # original code
    RVTEST_SIGUPD(SIGPOINTER, LINKREG, TEMPREG, t2, "test_1")
    j around

adds:
    addi t2, t2, 5  # borrow this as new code

around:
