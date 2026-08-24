.p2align 12
.p2align (UDB_PMP_GRANULARITY)
TEST_FOR_EXECUTION_X:
    jalr x0, x1, 0

.p2align (UDB_PMP_GRANULARITY)
TEST_FOR_EXECUTION:
    .rept (1<<(UDB_PMP_GRANULARITY))
    nop
    .endr

RETURN_INSTRUCTION:
    nop
    nop
    jr ra                                                        // Get back to the point from where TEST_FOR_EXECUTION was called.
