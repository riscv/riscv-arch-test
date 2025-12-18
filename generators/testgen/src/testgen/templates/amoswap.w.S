# amoswap.w.S
# Test odd word-aligned amo operations
la t0, scratch
li t2, 0x9ABCDEF0
addi t0, t0, 4      # create odd alignment
sw t2, 0(t0)
li t2, 0xA5A5A5A5

# cp_align_word
amoswap.w t1, t2, (t0)

#NOTE: haven't added a signature because rs1 is misaligned and that
#      will cause an access-fault exception whenever we do a memory access
