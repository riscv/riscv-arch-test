# fence.i.S
# custom tests for fence.i

    LI(s2, 3)         # s2 = 3
    LA(s0, adds)      # s1 = address of the replacement instruction

    # test normal fence.i
    LA(s3, selfmodify1)
    lw s1, 0(s0)      # s1 = encoded instruction "addi s2, s2, 5"
    sw s1, 0(s3)      # store it at selfmodify
    fence.i           # synchronize self-modified code so addi uses 5 rather than 1
selfmodify1:          # after modification, should compute s2 = 8 rather than s2 = 4
    addi s2, s2, 1    # original code
    RVTEST_SIGUPD(SIGPOINTER, LINKREG, TEMPREG, s2, "test_1")

    # test fence.i with nonzero rs1
    LA(s3, selfmodify2)
    lw s1, 4(s0)      # s1 = encoded instruction "addi s2, s2, 7"
    sw s1, 0(s3)      # store it at selfmodify
    .word 0x0001100f  # fence.i with nonzero rs1
selfmodify2:          # after modification, should compute s2 = 15 rather than 9
    addi s2, s2, 1    # original code
    RVTEST_SIGUPD(SIGPOINTER, LINKREG, TEMPREG, s2, "test_1")

    # test fence.i with nonzero rd
    LA(s3, selfmodify3)
    lw s1, 8(s0)      # s1 = encoded instruction "addi s2, s2, 9"
    sw s1, 0(s3)      # store it at selfmodify
    .word 0x0000108f  # fence.i with nonzero rd
selfmodify3:          # after modification, should compute s2 = 24 rather than 10
    addi s2, s2, 1    # original code
    RVTEST_SIGUPD(SIGPOINTER, LINKREG, TEMPREG, s2, "test_1")

    # test fence.i with nonzero funct12
    LA(s3, selfmodify4)
    lw s1, 12(s0)     # s1 = encoded instruction "addi s2, s2, 13"
    sw s1, 0(s3)      # store it at selfmodify
    .word 0x0010100f  # fence.i with nonzero funcs12
selfmodify4:          # after modification, should compute s2 = 37 rather than 25
    addi s2, s2, 1    # original code
    RVTEST_SIGUPD(SIGPOINTER, LINKREG, TEMPREG, s2, "test_1")



    j around

adds:
    addi s2, s2, 5  # borrow this as new code
    addi s2, s2, 7  # borrow this as new code
    addi s2, s2, 9  # borrow this as new code
    addi s2, s2, 13  # borrow this as new code

around:
