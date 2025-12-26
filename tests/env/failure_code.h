# failure_code.h
# riscv-arch-test assembly test failure handling code
# Jordan Carlin jcarlin@hmc.edu October 2025
# SPDX-License-Identifier: Apache-2.0

// Macro to define failure detection code (functions)
// This is instantiated after test code near the end of RVTEST_CODE_END in test_setup.h
.macro RVTEST_FAILURE_CODE
    # Log failure. DEFAULT_LINK_REG (x5) contains return address of jal from the failure and DEFAULT_TEMP_REG (x4) is a vacant temporary register
    failedtest_x5_x4:
        la DEFAULT_TEMP_REG, begin_failure_scratch
        SREG DEFAULT_LINK_REG, 40(DEFAULT_TEMP_REG) # store return address
        j failedtest_saveregs

    # Log failure. x8 contains return address of jal from the failure and x7 is a vacant temporary register
    failedtest_x8_x7:
        la x7, begin_failure_scratch
        SREG x8, 64(x7)               # store return address
        SREG DEFAULT_TEMP_REG, 32(x7) # save DEFAULT_LINK_REG
        SREG DEFAULT_LINK_REG, 40(x7) # save DEFAULT_TEMP_REG
        mv DEFAULT_TEMP_REG, x7       # move scratch base into DEFAULT_TEMP_REG
        mv DEFAULT_LINK_REG, x8       # move return address into DEFAULT_LINK_REG
        # now DEFAULT_LINK_REG has the return address of jal from the failure and DEFAULT_TEMP_REG is a vacant temporary register.
        j failedtest_saveregs

    # Log failure. x13 contains return address of jal from the failure and x12 is a vacant temporary register
    failedtest_x13_x12:
        la x12, begin_failure_scratch
        SREG x13, 104(x12) # store return address
        SREG DEFAULT_TEMP_REG, 32(x12)  # save DEFAULT_LINK_REG
        SREG DEFAULT_LINK_REG, 40(x12)  # save DEFAULT_TEMP_REG
        mv DEFAULT_TEMP_REG, x12        # move scratch base into DEFAULT_TEMP_REG
        mv DEFAULT_LINK_REG, x13        # move return address into DEFAULT_LINK_REG
        # now DEFAULT_LINK_REG has the return address of jal from the failure and DEFAULT_TEMP_REG is a vacant temporary register.
        j failedtest_saveregs

    # for the rest of this code, DEFAULT_LINK_REG contains return address of jal from the failure, DEFAULT_TEMP_REG points to scratch space
    failedtest_saveregs:
        SREG x1, 8(DEFAULT_TEMP_REG)
        SREG x2, 16(DEFAULT_TEMP_REG)
        SREG x3, 24(DEFAULT_TEMP_REG)
        # SREG x4, 32(DEFAULT_TEMP_REG)
        # SREG x5, 40(DEFAULT_TEMP_REG)
        # x4 and x5 have already been saved if relevant (default temp and link regs)
        SREG x6, 48(DEFAULT_TEMP_REG)
        SREG x7, 56(DEFAULT_TEMP_REG)
        SREG x8, 64(DEFAULT_TEMP_REG)
        SREG x9, 72(DEFAULT_TEMP_REG)
        SREG x10, 80(DEFAULT_TEMP_REG)
        SREG x11, 88(DEFAULT_TEMP_REG)
        SREG x12, 96(DEFAULT_TEMP_REG)
        SREG x13, 104(DEFAULT_TEMP_REG)
        SREG x14, 112(DEFAULT_TEMP_REG)
        SREG x15, 120(DEFAULT_TEMP_REG)
        SREG x16, 128(DEFAULT_TEMP_REG)
        SREG x17, 136(DEFAULT_TEMP_REG)
        SREG x18, 144(DEFAULT_TEMP_REG)
        SREG x19, 152(DEFAULT_TEMP_REG)
        SREG x20, 160(DEFAULT_TEMP_REG)
        SREG x21, 168(DEFAULT_TEMP_REG)
        SREG x22, 176(DEFAULT_TEMP_REG)
        SREG x23, 184(DEFAULT_TEMP_REG)
        SREG x24, 192(DEFAULT_TEMP_REG)
        SREG x25, 200(DEFAULT_TEMP_REG)
        SREG x26, 208(DEFAULT_TEMP_REG)
        SREG x27, 216(DEFAULT_TEMP_REG)
        SREG x28, 224(DEFAULT_TEMP_REG)
        SREG x29, 232(DEFAULT_TEMP_REG)
        SREG x30, 240(DEFAULT_TEMP_REG)
        SREG x31, 248(DEFAULT_TEMP_REG)

    failedtest_saveresults:
        # failing instruction might be 16 or 32 bits, on a 16-byte boundary.
        # fetch with halfwords, report all 32 bits, let user figure it out
        lhu x6, -14(DEFAULT_LINK_REG)     # get upper half of the failing instruction
        lhu x7, -16(DEFAULT_LINK_REG)     # get lower half
        slli x6, x6, 16     # reassemble
        or x6, x6, x7
        sw x6, 256(DEFAULT_TEMP_REG)      # record 32 bits of failing instruction.  Actual instruction might be top half

        # Reconstruct and extract information from the beq
        # branch might be on 16-byte boundary, so fetch with halfword
        lhu x6, -6(DEFAULT_LINK_REG)     # get upper half of the the beq that compared good and bad registers
        lhu x7, -8(DEFAULT_LINK_REG)     # get lower half of the beq
        slli x6, x6, 16     # reassemble beq
        or x6, x6, x7
        # extract rs1 and rs2 from branch (beq format: rs2[24:20] rs1[19:15])
        srli x7, x6, 15
        andi x7, x7, 31     # x7 = rs1 of branch
        srli x8, x6, 20
        andi x8, x8, 31     # x8 = rs2 of branch
        sw x8, 260(DEFAULT_TEMP_REG)      # record id of failing register (rs2 of beq)
        # save bad value from rs2
        slli x6, x8, 3      # rs2 * 8
        add  x6, DEFAULT_TEMP_REG, x6     # address of scratch memory containing rs2
        LREG x6, 0(x6)      # value of rs2 (bad result of operation)
        SREG x6, 272(DEFAULT_TEMP_REG)    # record bad value

        # Reconstruct and extract information from the load
        # The ld loads from an offset of a base register, extract base register and offset
        lhu x6, -10(DEFAULT_LINK_REG)     # get upper half of the ld instruction
        lhu x7, -12(DEFAULT_LINK_REG)     # get lower half of the ld
        slli x6, x6, 16     # reassemble ld
        or x6, x6, x7
        # ld format: imm[11:0] at bits [31:20], rs1 at bits [19:15]
        srai x7, x6, 20     # extract immediate (sign-extended)
        srli x6, x6, 15
        andi x6, x6, 31     # extract rs1 (base register)
        # Load the value of the sigptr register from saved state
        slli x6, x6, 3      # rs1 * 8
        add x6, DEFAULT_TEMP_REG, x6      # address of sigptr register
        LREG x6, 0(x6)      # get sigptr register value
        add x6, x6, x7      # sigptr + offset = address of expected value
        LREG x6, 0(x6)      # load expected value
        SREG x6, 280(DEFAULT_TEMP_REG)    # record expected value

        # Save failing address
        addi x6, DEFAULT_LINK_REG, -16    # address of the failing instruction (possibly including half of previous instruction)
        SREG x6, 264(DEFAULT_TEMP_REG)

        # Get pointer to failure string
        # In SELFCHECK mode, after the jal instruction there is an XLEN-sized pointer to the test name string
        # The jal returns to DEFAULT_LINK_REG, which points to the instruction after jal (i.e., the pointer itself)
        LREG x6, 0(DEFAULT_LINK_REG)      # load the string pointer from memory
        SREG x6, 288(DEFAULT_TEMP_REG)    # save the string pointer

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
