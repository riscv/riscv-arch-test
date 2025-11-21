///////////////////////////////////////////////////////////////
# Custom Test
#
# Written: mbellido@hmc.edu       June 10 2025
# SPDX-License-Identifier: Apache-2.0
#
# CUSTOM TESTS GUIDE (Short Version)
#
# - Use SIGPOINTER for all signature memory accesses.
#   Internally replaced by x{sigReg}.
#
# - After writing to signature memory, use:
#     SIG_POINTER_INCREMENT(n)
#   where n = number of **bytes** written (not instructions).
#
# - Always write first, then increment the pointer.
#
# DO NOT MODIFY unless you also update the test generation script.
///////////////////////////////////////////////////////////////

# sw.S
# Test word-aligned sw operations
    li t2, 0x12345678
    li t3, 0x9ABCDEF0

    # cp_align_word: imm[2]=0 (aligned store)
    sw t2, 0(SIGPOINTER)
    sw t3, 4(SIGPOINTER)
    # increment pointer after since we are storing two words using offset 0 and 4.
    # the offset would be off, if the increments were added in between
    SIG_POINTER_INCREMENT(8) # number - total amount of space used (in bytes) by all of the instructions being tested
