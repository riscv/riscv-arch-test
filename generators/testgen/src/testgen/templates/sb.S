# sb.S
# test all 8 byte alignments
    li t1, 0x9ABCDEF0
    li t2, 0x12345678
    sw t1, 0(SIGPOINTER)  // Initialize memory
    sw t2, 4(SIGPOINTER)

    SIG_POINTER_INCREMENT(8) # number - (in bytes for words). Always add after completing a region of memory offsets.


# cp_align_byte: imm[2:0]=000
    sb t2, 0(SIGPOINTER)

# cp_align_byte: imm[2:0]=001
    sb t2, 1(SIGPOINTER)

# cp_align_byte: imm[2:0]=010
    sb t2, 2(SIGPOINTER)

# cp_align_byte: imm[2:0]=011
    sb t2, 3(SIGPOINTER)

# cp_align_byte: imm[2:0]=100
    sb t2, 4(SIGPOINTER)

# cp_align_byte: imm[2:0]=101
    sb t2, 5(SIGPOINTER)

# cp_align_byte: imm[2:0]=110
    sb t2, 6(SIGPOINTER)

# cp_align_byte: imm[2:0]=111
    sb t2, 7(SIGPOINTER)

    SIG_POINTER_INCREMENT(32) # number - (space in bytes for words).
