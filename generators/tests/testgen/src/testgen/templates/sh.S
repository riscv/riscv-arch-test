
///////////////////////////////////////////////////////////////
# Custom Test
#
# Written: mbellido@hmc.edu       June 12 2025
# SPDX-License-Identifier: Apache-2.0
#
# CUSTOM TESTS GUIDE (Short Version)
#
# - Use SIGPOINTER for all signature memory accesses.
#   Internally replaced by x{sigReg}.
#
# - After writing to signature memory, use:
#     SIG_POINTER_INCREMENT(n): Total bytes written in the test,
#       independent of instruction type. Used to track how much signature
#       space (0xdeadbeef-filled memory) is consumed, in word-aligned chunks.
#       Always add after completing a region of memory offsets.
#
# - Always write first, then increment the pointer.
#
# DO NOT MODIFY unless you also update the test generation script.
///////////////////////////////////////////////////////////////

# sh.S
# test all halfword-aligned operations
    li t1, 0x9ABCDEF0
    li t2, 0x12345678
    sw t1, 0(SIGPOINTER)  // Initialize memory
    sw t2, 4(SIGPOINTER)

    SIG_POINTER_INCREMENT(8) # number - (in bytes for words). Always add after completing a region of memory offsets.


#cp_align_hword: imm[2:1]=00
    sh t2, 0(SIGPOINTER)

#cp_align_hword: imm[2:1]=01
    sh t2, 2(SIGPOINTER)

#cp_align_hword: imm[2:1]=10
    sh t2, 4(SIGPOINTER)

#cp_align_hword: imm[2:1]=11
    sh t2, 6(SIGPOINTER)

    SIG_POINTER_INCREMENT(16) # number - (space in bytes for words). Always add after completing a region of memory offsets.
