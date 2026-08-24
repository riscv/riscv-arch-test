.p2align 12
.p2align (UDB_PMP_GRANULARITY)
TEST_FOR_EXECUTION_1:
    .rept 1024
    nop
    .endr

.p2align (UDB_PMP_GRANULARITY)
TEST_FOR_EXECUTION_2:
    .rept 1024
    nop
    .endr

RETURN_INSTRUCTION:
    nop
    nop
    jr ra                                                        // Get back to the point from where TEST_FOR_EXECUTION was called.
