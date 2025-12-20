# amominu.w.S
# Test odd word-aligned amo operations
la t0, scratch
li t2, 0x9ABCDEF0
addi t0, t0, 4      # create odd alignment
sw t2, 0(t0)
li t2, 0xA5A5A5A5

# cp_align_word
amominu.w t1, t2, (t0)
RVTEST_SIGUPD(SIGPOINTER, t1)
lw t3, 0(t0)              # Load updated memory
RVTEST_SIGUPD(SIGPOINTER, t3)    # Expect 0x3F190B55 (updated memory value)
