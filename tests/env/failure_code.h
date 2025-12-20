# failure_code.h
# riscv-arch-test assembly test failure handling code
# Jordan Carlin jcarlin@hmc.edu October 2025
# SPDX-License-Identifier: Apache-2.0

// Macro to define failure detection code (functions)
// This is instantiated after test code near the end of RVTEST_CODE_END in test_setup.h
.macro RVTEST_FAILURE_CODE
    # Log failure. x4 contains return address of jal from the failure and x5 is a vacant temporary register
    failedtest_x4_x5:
        la x5, begin_failure_scratch
        SREG x4, 32(x5) # store return address
        j failedtest_saveregs

    # Log failure. x7 contains return address of jal from the failure and x8 is a vacant temporary register
    failedtest_x7_x8:
        la x8, begin_failure_scratch
        SREG x7, 56(x8) # store return address
        SREG x4, 32(x8) # save x4
        SREG x5, 40(x8) # save x5
        mv x4, x7       # move return address into x4
        mv x5, x8       # move scratch base into x5
        # now x4 has the return address of jal from the failure and x5 is a vacant temporary register.
        j failedtest_saveregs

    # Log failure. x12 contains return address of jal from the failure and x13 is a vacant temporary register
    failedtest_x12_x13:
        la x13, begin_failure_scratch
        SREG x12, 96(x13) # store return address
        SREG x4, 32(x13)  # save x4
        SREG x5, 40(x13)  # save x5
        mv x4, x12        # move return address into x4
        mv x5, x13        # move scratch base into x5
        # now x4 has the return address of jal from the failure and x5 is a vacant temporary register.
        j failedtest_saveregs

    # for the rest of this code, x4 contains return address of jal from the failure, x5 points to scratch space
    failedtest_saveregs:
        SREG x1, 8(x5)
        SREG x2, 16(x5)
        SREG x3, 24(x5)
        # SREG x4, 32(x5)
        # SREG x5, 40(x5)
        # x4 and x5 have already been saved if relevant
        SREG x6, 48(x5)
        SREG x7, 56(x5)
        SREG x8, 64(x5)
        SREG x9, 72(x5)
        SREG x10, 80(x5)
        SREG x11, 88(x5)
        SREG x12, 96(x5)
        SREG x13, 104(x5)
        SREG x14, 112(x5)
        SREG x15, 120(x5)
        SREG x16, 128(x5)
        SREG x17, 136(x5)
        SREG x18, 144(x5)
        SREG x19, 152(x5)
        SREG x20, 160(x5)
        SREG x21, 168(x5)
        SREG x22, 176(x5)
        SREG x23, 184(x5)
        SREG x24, 192(x5)
        SREG x25, 200(x5)
        SREG x26, 208(x5)
        SREG x27, 216(x5)
        SREG x28, 224(x5)
        SREG x29, 232(x5)
        SREG x30, 240(x5)
        SREG x31, 248(x5)

    failedtest_saveresults:
        # failing instruction might be 16 or 32 bits, on a 16-byte boundary.
        # fetch with halfwords, report all 32 bits, let user figure it out
        lhu x6, -14(x4)     # get upper half of the failing instruction
        lhu x7, -16(x4)     # get lower half
        slli x6, x6, 16     # reassemble
        or x6, x6, x7
        sw x6, 256(x5)      # record 32 bits of failing instruction.  Actual instruction might be top half

        # Reconstruct and extract information from the beq
        # branch might be on 16-byte boundary, so fetch with halfword
        lhu x6, -6(x4)     # get upper half of the the beq that compared good and bad registers
        lhu x7, -8(x4)     # get lower half of the beq
        slli x6, x6, 16     # reassemble beq
        or x6, x6, x7
        # extract rs1 and rs2 from branch (beq format: rs2[24:20] rs1[19:15])
        srli x7, x6, 15
        andi x7, x7, 31     # x7 = rs1 of branch
        srli x8, x6, 20
        andi x8, x8, 31     # x8 = rs2 of branch
        sw x8, 260(x5)      # record id of failing register (rs2 of beq)
        # save bad value from rs2
        slli x6, x8, 3      # rs2 * 8
        add  x6, x5, x6     # address of scratch memory containing rs2
        LREG x6, 0(x6)      # value of rs2 (bad result of operation)
        SREG x6, 272(x5)    # record bad value

        # Reconstruct and extract information from the load
        # The ld loads from an offset of a base register, extract base register and offset
        lhu x6, -10(x4)     # get upper half of the ld instruction
        lhu x7, -12(x4)     # get lower half of the ld
        slli x6, x6, 16     # reassemble ld
        or x6, x6, x7
        # ld format: imm[11:0] at bits [31:20], rs1 at bits [19:15]
        srai x7, x6, 20     # extract immediate (sign-extended)
        srli x6, x6, 15
        andi x6, x6, 31     # extract rs1 (base register)
        # Load the value of the sigptr register from saved state
        slli x6, x6, 3      # rs1 * 8
        add x6, x5, x6      # address of sigptr register
        LREG x6, 0(x6)      # get sigptr register value
        add x6, x6, x7      # sigptr + offset = address of expected value
        LREG x6, 0(x6)      # load expected value
        SREG x6, 280(x5)    # record expected value

        # Save failing address
        addi x6, x4, -16    # address of the failing instruction (possibly including half of previous instruction)
        SREG x6, 264(x5)

        # Get pointer to failure string
        # In SELFCHECK mode, after the jal instruction there is an XLEN-sized pointer to the test name string
        # The jal returns to x4, which points to the instruction after jal (i.e., the pointer itself)
        LREG x6, 0(x4)      # load the string pointer from memory
        SREG x6, 288(x5)    # save the string pointer

    failedtest_report:
        # RVMODEL_IO_INIT(x6, x7, x8)
      print_failstr:
        LA(x9, failstr)
        RVMODEL_IO_WRITE_STR(x6, x7, x8, x9)

        # Print test name string
      print_testnamestr:
        LA(x9, testnamestr)
        RVMODEL_IO_WRITE_STR(x6, x7, x8, x9)
      print_failure_test_name_str:
        LREG x9, failure_string_ptr
        RVMODEL_IO_WRITE_STR(x6, x7, x8, x9)
      print_newline_str:
        LA(x9, newlinestr)
        RVMODEL_IO_WRITE_STR(x6, x7, x8, x9)

        # Print failing instruction (32-bit)
        LA(x9, inststr)
        RVMODEL_IO_WRITE_STR(x6, x7, x8, x9)
        lw a0, failing_instruction
        li a1, 32
        jal failedtest_hex_to_str
        LA(x9, ascii_buffer)
        RVMODEL_IO_WRITE_STR(x6, x7, x8, x9)

        # Print failing address (XLEN-bit)
        LA(x9, addrstr)
        RVMODEL_IO_WRITE_STR(x6, x7, x8, x9)
        LREG a0, failing_addr
        li a1, __riscv_xlen
        jal failedtest_hex_to_str
        LA(x9, ascii_buffer)
        RVMODEL_IO_WRITE_STR(x6, x7, x8, x9)

        # Print failing register (32-bit)
        LA(x9, regstr)
        RVMODEL_IO_WRITE_STR(x6, x7, x8, x9)
        lw a0, failing_reg
        li a1, 32
        jal failedtest_hex_to_str
        LA(x9, ascii_buffer)
        RVMODEL_IO_WRITE_STR(x6, x7, x8, x9)

        # Print failing value (XLEN-bit)
        LA(x9, badvalstr)
        RVMODEL_IO_WRITE_STR(x6, x7, x8, x9)
        LREG a0, failing_value
        li a1, __riscv_xlen
        jal failedtest_hex_to_str
        LA(x9, ascii_buffer)
        RVMODEL_IO_WRITE_STR(x6, x7, x8, x9)

        # Print expected value (XLEN-bit)
        LA(x9, expvalstr)
        RVMODEL_IO_WRITE_STR(x6, x7, x8, x9)
        LREG a0, expected_value
        li a1, __riscv_xlen
        jal failedtest_hex_to_str
        LA(x9, ascii_buffer)
        RVMODEL_IO_WRITE_STR(x6, x7, x8, x9)

        # Print end string
        LA(x9, endstr)
        RVMODEL_IO_WRITE_STR(x6, x7, x8, x9)

    failedtest_terminate:
        RVMODEL_HALT_FAIL


    # Convert hex number to ASCII string and store result in ascii_buffer
    # a0: value to convert
    # a1: number of bits (32 or 64)
    failedtest_hex_to_str:
        LA(a2, ascii_buffer)     # buffer pointer
        LI(a3, '0')
        sb a3, 0(a2)            # write '0'
        LI(a3, 'x')
        sb a3, 1(a2)            # write 'x'
        addi a2, a2, 2          # move past "0x"
        mv a3, a1               # a3 = bit count
    failedtest_hex_to_str_loop:
        addi a3, a3, -4         # move to next nibble
        srl a4, a0, a3          # shift nibble to bottom
        andi a4, a4, 15         # mask to get nibble

        # Convert nibble to ASCII
        LI(a5, 10)
        blt a4, a5, failedtest_hex_to_str_digit
        # It's a letter (A-F)
        addi a4, a4, 87         # 'a' - 10 = 87
        j failedtest_hex_to_str_write
    failedtest_hex_to_str_digit:
        # It's a digit (0-9)
        addi a4, a4, 48         # '0' = 48
    failedtest_hex_to_str_write:
        sb a4, 0(a2)            # write character to buffer
        addi a2, a2, 1          # advance buffer pointer
        bnez a3, failedtest_hex_to_str_loop

        # Add newline and null terminator
        LI(a3, 10)              # '\n'
        sb a3, 0(a2)
        sb zero, 1(a2)          # null terminator

        ret
.endm

// Macro to define failure code data section
// This should be called separately in the RVTEST_DATA_END section to avoid mixing code and data
.macro RVTEST_FAILURE_DATA
    .data
    .align 4
    begin_failure_scratch:
        .fill 32,8,0xfeedf00dbaaaaaad
    failing_instruction:
        .fill 1, 4, 0xfeedf00d
    failing_reg:
        .fill 1, 4, 0xbaaaaaad
    failing_addr:
        .fill 1, 8, 0xfeedf00dbaaaaaad
    failing_value:
        .fill 1, 8, 0xfeedf00dbaaaaaad
    expected_value:
        .fill 1, 8, 0xfeedf00dbaaaaaad
    failure_string_ptr:
        .fill 1, 8, 0xfeedf00dbaaaaaad
    ascii_buffer:
        .fill 20, 1, 0          # Buffer for hex string conversion (max "0x" + 16 hex digits + "\n" + null)
    end_failure_scratch:

    successstr:
        #ifdef SELFCHECK
            .string "\nRVCP-SUMMARY: Test File \"" TEST_FILE "\": PASSED\n"
        #else
            .string "\nRVCP-SUMMARY: Test File \"" TEST_FILE "\": SIGRUN\n"
        #endif
    failstr:
        .string "\nRVCP-SUMMARY: Test File \"" TEST_FILE "\": FAILED\nRVCP: DEBUG INFORMATION FOLLOWS\n"
    testnamestr:
        .string "RVCP: Test Info: "
    newlinestr:
        .string "\n"
    inststr:
        .string "RVCP: Instruction: "
    addrstr:
        .string "RVCP: Address: "
    regstr:
        .string "RVCP: Register: "
    badvalstr:
        .string "RVCP: Bad Value: "
    expvalstr:
        .string "RVCP: Expected Value: "
    endstr:
        .string "RVCP: END OF DEBUG INFORMATION\n\n"
.endm
