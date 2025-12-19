# fence.S
# custom tests for fence

# cp_custom_fence
    fence
    fence.tso
    fence rw, rw
    .word 0x0331000f    # fence with nonzero rs1 behaves normally
    .word 0x0330008f    # fence with nonzero rd  behaves normally
    .word 0x1330000f    # fence with reserved fm behaves as fence
    .word 0x8110000f    # fence.TSO with R,R rather than RW, RW behaves as fence
