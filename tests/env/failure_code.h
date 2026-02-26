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
        SREG x1, 8(DEFAULT_TEMP_REG)                # save x1 early (used for failure_type)
        sw zero, 0(DEFAULT_TEMP_REG)                # failure_type = 0 (integer)
        j failedtest_saveregs

    # Log failure. x8 contains return address of jal from the failure and x7 is a vacant temporary register
    failedtest_x8_x7:
        la x7, begin_failure_scratch
        SREG x8, 64(x7)               # store return address
        SREG DEFAULT_TEMP_REG, 32(x7) # save DEFAULT_TEMP_REG
        SREG DEFAULT_LINK_REG, 40(x7) # save DEFAULT_LINK_REG
        SREG x1, 8(x7)                # save x1 early
        sw zero, 0(x7)                # failure_type = 0 (integer)
        mv DEFAULT_TEMP_REG, x7       # move scratch base into DEFAULT_TEMP_REG
        mv DEFAULT_LINK_REG, x8       # move return address into DEFAULT_LINK_REG
        # now DEFAULT_LINK_REG has the return address of jal from the failure and DEFAULT_TEMP_REG is a vacant temporary register.
        j failedtest_saveregs

    # Log failure. x13 contains return address of jal from the failure and x12 is a vacant temporary register
    failedtest_x13_x12:
        la x12, begin_failure_scratch
        SREG x13, 104(x12)              # store return address
        SREG DEFAULT_TEMP_REG, 32(x12)  # save DEFAULT_TEMP_REG
        SREG DEFAULT_LINK_REG, 40(x12)  # save DEFAULT_LINK_REG
        SREG x1, 8(x12)                 # save x1 early
        sw zero, 0(x12)                 # failure_type = 0 (integer)
        mv DEFAULT_TEMP_REG, x12        # move scratch base into DEFAULT_TEMP_REG
        mv DEFAULT_LINK_REG, x13        # move return address into DEFAULT_LINK_REG
        # now DEFAULT_LINK_REG has the return address of jal from the failure and DEFAULT_TEMP_REG is a vacant temporary register.
        j failedtest_saveregs

#ifdef RVTEST_FP
    # FP failure entry points (failure_type = 1)
    failedtest_fp_x5_x4:
        la DEFAULT_TEMP_REG, begin_failure_scratch
        SREG DEFAULT_LINK_REG, 40(DEFAULT_TEMP_REG)
        SREG x1, 8(DEFAULT_TEMP_REG)
        li x1, 1
        sw x1, 0(DEFAULT_TEMP_REG)                  # failure_type = 1 (fp)
        j failedtest_saveregs

    failedtest_fp_x8_x7:
        la x7, begin_failure_scratch
        SREG x8, 64(x7)
        SREG DEFAULT_TEMP_REG, 32(x7)
        SREG DEFAULT_LINK_REG, 40(x7)
        SREG x1, 8(x7)
        li x1, 1
        sw x1, 0(x7)                                # failure_type = 1 (fp)
        mv DEFAULT_TEMP_REG, x7
        mv DEFAULT_LINK_REG, x8
        j failedtest_saveregs

    failedtest_fp_x13_x12:
        la x12, begin_failure_scratch
        SREG x13, 104(x12)
        SREG DEFAULT_TEMP_REG, 32(x12)
        SREG DEFAULT_LINK_REG, 40(x12)
        SREG x1, 8(x12)
        li x1, 1
        sw x1, 0(x12)                               # failure_type = 1 (fp)
        mv DEFAULT_TEMP_REG, x12
        mv DEFAULT_LINK_REG, x13
        j failedtest_saveregs

    # fflags failure entry points (failure_type = 2)
    failedtest_fflags_x5_x4:
        la DEFAULT_TEMP_REG, begin_failure_scratch
        SREG DEFAULT_LINK_REG, 40(DEFAULT_TEMP_REG)
        SREG x1, 8(DEFAULT_TEMP_REG)
        li x1, 2
        sw x1, 0(DEFAULT_TEMP_REG)                  # failure_type = 2 (fflags)
        j failedtest_saveregs

    failedtest_fflags_x8_x7:
        la x7, begin_failure_scratch
        SREG x8, 64(x7)
        SREG DEFAULT_TEMP_REG, 32(x7)
        SREG DEFAULT_LINK_REG, 40(x7)
        SREG x1, 8(x7)
        li x1, 2
        sw x1, 0(x7)                                # failure_type = 2 (fflags)
        mv DEFAULT_TEMP_REG, x7
        mv DEFAULT_LINK_REG, x8
        j failedtest_saveregs

    failedtest_fflags_x13_x12:
        la x12, begin_failure_scratch
        SREG x13, 104(x12)
        SREG DEFAULT_TEMP_REG, 32(x12)
        SREG DEFAULT_LINK_REG, 40(x12)
        SREG x1, 8(x12)
        li x1, 2
        sw x1, 0(x12)                               # failure_type = 2 (fflags)
        mv DEFAULT_TEMP_REG, x12
        mv DEFAULT_LINK_REG, x13
        j failedtest_saveregs
#endif // RVTEST_FP

    # for the rest of this code, DEFAULT_LINK_REG contains return address of jal from the failure, DEFAULT_TEMP_REG points to scratch space
    failedtest_saveregs:
        # x1 has already been saved by all entry points
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
        # Dispatch based on failure type
        lw x9, 0(DEFAULT_TEMP_REG)       # load failure_type
#ifdef RVTEST_FP
        li x10, 1
        beq x9, x10, failedtest_saveresults_fp
        li x10, 2
        beq x9, x10, failedtest_saveresults_fflags
#endif // RVTEST_FP

    failedtest_saveresults_int:
        # --- INTEGER (type 0): extract info from beq and load instructions ---
        # Reconstruct and extract information from the beq
        # branch might be on 16-byte boundary, so fetch with halfword
        lhu x6, -6(DEFAULT_LINK_REG)     # get upper half of the beq that compared good and bad registers
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
        j failedtest_saveresults_common

#ifdef RVTEST_FP
    failedtest_saveresults_fflags:
        # Re-read fcsr for bad value (hasn't changed since failure)
        csrr x6, fcsr
        SREG x6, 272(DEFAULT_TEMP_REG)    # failing_value

        # Extract load instruction at -12 for expected value (same approach as integer)
        lhu x6, -10(DEFAULT_LINK_REG)
        lhu x7, -12(DEFAULT_LINK_REG)
        slli x6, x6, 16
        or x6, x6, x7
        srai x7, x6, 20     # extract immediate (sign-extended)
        srli x6, x6, 15
        andi x6, x6, 31     # extract rs1
        slli x6, x6, 3
        add x6, DEFAULT_TEMP_REG, x6
        LREG x6, 0(x6)      # sigptr register value
        add x6, x6, x7      # sigptr + offset
        LREG x6, 0(x6)      # expected value
        SREG x6, 280(DEFAULT_TEMP_REG)    # record expected value
        j failedtest_saveresults_common

    failedtest_saveresults_fp:
        # Extract FP register number from FSREG instruction at -20 from return address
        # FSREG is S-type: imm[11:5] | rs2[24:20] | rs1[19:15] | funct3 | imm[4:0] | opcode
        lhu x6, -18(DEFAULT_LINK_REG)     # upper half of FSREG
        lhu x7, -20(DEFAULT_LINK_REG)     # lower half of FSREG
        slli x6, x6, 16
        or x6, x6, x7
        srli x6, x6, 20
        andi x6, x6, 31                   # FP register number (rs2 of FSREG)
        sw x6, 260(DEFAULT_TEMP_REG)      # record failing_reg

        # Load bad FP value from scratch memory (written by FSREG in the sigupd macro)
        la x6, scratch
        LREG x7, 0(x6)
        SREG x7, 272(DEFAULT_TEMP_REG)    # failing_value (lower/only)
    #if FLEN > XLEN
        LREG x7, REGWIDTH(x6)
        la x8, failing_value_upper
        SREG x7, 0(x8)                    # failing_value upper half
    #endif

        # Extract sigptr base register from load instruction at -12
        # (use rs1 only, ignore immediate — we load both halves from the base)
        lhu x6, -10(DEFAULT_LINK_REG)
        lhu x7, -12(DEFAULT_LINK_REG)
        slli x6, x6, 16
        or x6, x6, x7
        srli x6, x6, 15
        andi x6, x6, 31                   # rs1 (sigptr register number)
        slli x6, x6, 3
        add x6, DEFAULT_TEMP_REG, x6
        LREG x6, 0(x6)                    # sigptr value (base of FP signature entry)
        # Load full expected FP value from signature
        LREG x7, 0(x6)
        SREG x7, 280(DEFAULT_TEMP_REG)    # expected_value (lower/only)
    #if FLEN > XLEN
        LREG x7, SIG_STRIDE(x6)
        la x8, expected_value_upper
        SREG x7, 0(x8)                    # expected_value upper half
    #endif
        j failedtest_saveresults_common
#endif // RVTEST_FP

    failedtest_saveresults_common:
        # After the jal instruction there are two XLEN-sized pointers: the instruction address and the test string pointer
        # The jal returns to DEFAULT_LINK_REG, which points to the data after jal  (i.e., the first pointer itself)

        # Save failing address (loaded from embedded instruction pointer after jal)
        LREG x6, 0(DEFAULT_LINK_REG)      # load the instruction address from memory
        SREG x6, 264(DEFAULT_TEMP_REG)

        # Fetch the failing instruction using INSTR_PTR address
        # Check bottom 2 bits: if inst[1:0] != 0b11, it's a 16-bit compressed instruction
        lhu x7, 0(x6)       # get lower half of the failing instruction
        andi x8, x7, 3
        li x9, 3
        bne x8, x9, 1f      # compressed: only lower half needed
        lhu x8, 2(x6)       # 32-bit: fetch upper half
        slli x8, x8, 16
        or x7, x7, x8
    1:
        sw x7, 256(DEFAULT_TEMP_REG)      # record failing instruction (16 or 32 bits)

        # Get pointer to failure string (loaded from second embedded pointer after jal)
        LREG x6, REGWIDTH(DEFAULT_LINK_REG) # load the string pointer from memory
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

        # Print failing instruction (detect 16-bit compressed vs 32-bit)
        LA(x9, inststr)
        RVMODEL_IO_WRITE_STR(x6, x7, x8, x9)
        lw a0, failing_instruction
        li a1, 32            # assume 32-bit instruction
        andi a2, a0, 3
        li a3, 3
        beq a2, a3, 2f
        li a1, 16            # compressed: print as 16-bit
    2:
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

        # Print failing register — "x<N>" for int, "f<N>" for FP, "fflags" for fflags
        LA(x9, regstr)
        RVMODEL_IO_WRITE_STR(x6, x7, x8, x9)
        lw a0, failure_type
        bnez a0, failedtest_report_not_intreg
        # Integer: write "x" + decimal register number
        li a1, 'x'
        LA(a2, ascii_buffer)
        sb a1, 0(a2)
        addi a2, a2, 1
        lw a0, failing_reg
        jal failedtest_dec_to_str
        j failedtest_report_print_regstr
    failedtest_report_not_intreg:
        li a1, 1
        beq a0, a1, failedtest_report_fpreg
        # fflags: print "fflags\n"
        LA(x9, fflagsstr)
        RVMODEL_IO_WRITE_STR(x6, x7, x8, x9)
        j failedtest_report_after_reg
    failedtest_report_fpreg:
        # FP: write "f" + decimal register number
        li a1, 'f'
        LA(a2, ascii_buffer)
        sb a1, 0(a2)
        addi a2, a2, 1
        lw a0, failing_reg
        jal failedtest_dec_to_str
    failedtest_report_print_regstr:
        LA(x9, ascii_buffer)
        RVMODEL_IO_WRITE_STR(x6, x7, x8, x9)
    failedtest_report_after_reg:

        # Print failing value — type-aware
        LA(x9, badvalstr)
        RVMODEL_IO_WRITE_STR(x6, x7, x8, x9)
        lw a0, failure_type
        li a1, 1
        bne a0, a1, failedtest_report_badval_not_fp
    #if defined(RVTEST_FP) && FLEN > XLEN
        # FP with FLEN > XLEN: combined hex "0xUPPER_LOWER"
        LREG a0, failing_value_upper
        LREG a1, failing_value
        jal failedtest_combined_hex_to_str
    #else
        # FP with FLEN <= XLEN (or FLEN not defined): standard hex
        LREG a0, failing_value
        li a1, __riscv_xlen
        jal failedtest_hex_to_str
    #endif
        j failedtest_report_badval_done
    failedtest_report_badval_not_fp:
        # Integer or fflags: standard XLEN-bit hex
        LREG a0, failing_value
        li a1, __riscv_xlen
        jal failedtest_hex_to_str
    failedtest_report_badval_done:
        LA(x9, ascii_buffer)
        RVMODEL_IO_WRITE_STR(x6, x7, x8, x9)

        # Print expected value — type-aware
        LA(x9, expvalstr)
        RVMODEL_IO_WRITE_STR(x6, x7, x8, x9)
        lw a0, failure_type
        li a1, 1
        bne a0, a1, failedtest_report_expval_not_fp
    #if defined(RVTEST_FP) && FLEN > XLEN
        # FP with FLEN > XLEN: combined hex "0xUPPER_LOWER"
        LREG a0, expected_value_upper
        LREG a1, expected_value
        jal failedtest_combined_hex_to_str
    #else
        # FP with FLEN <= XLEN (or FLEN not defined): standard hex
        LREG a0, expected_value
        li a1, __riscv_xlen
        jal failedtest_hex_to_str
    #endif
        j failedtest_report_expval_done
    failedtest_report_expval_not_fp:
        # Integer or fflags: standard XLEN-bit hex
        LREG a0, expected_value
        li a1, __riscv_xlen
        jal failedtest_hex_to_str
    failedtest_report_expval_done:
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


    # Convert register number (0-31) to decimal string with newline
    # a0: register number (0-31)
    # a2: buffer pointer (writes digits + '\n' + '\0')
    failedtest_dec_to_str:
        li a3, 10
        blt a0, a3, 1f         # single digit
        addi a0, a0, -10
        li a4, '1'
        blt a0, a3, 2f
        addi a0, a0, -10
        li a4, '2'
        blt a0, a3, 2f
        addi a0, a0, -10
        li a4, '3'
    2:  sb a4, 0(a2)            # tens digit
        addi a2, a2, 1
    1:  addi a0, a0, '0'        # ones digit
        sb a0, 0(a2)
        li a3, 10               # '\n'
        sb a3, 1(a2)
        sb zero, 2(a2)          # null terminator
        ret


#if defined(RVTEST_FP) && FLEN > XLEN
    # Convert two XLEN-wide values to combined hex string: "0xUPPER_LOWER\n\0"
    # a0: upper XLEN-bit value
    # a1: lower XLEN-bit value
    failedtest_combined_hex_to_str:
        LA(a2, ascii_buffer)     # buffer pointer
        LI(a3, '0')
        sb a3, 0(a2)
        LI(a3, 'x')
        sb a3, 1(a2)
        addi a2, a2, 2          # past "0x"
        # Convert upper half nibbles
        li a3, __riscv_xlen
    failedtest_combined_upper_loop:
        addi a3, a3, -4
        srl a4, a0, a3
        andi a4, a4, 15
        LI(a5, 10)
        blt a4, a5, failedtest_combined_upper_digit
        addi a4, a4, 87         # 'a' - 10
        j failedtest_combined_upper_write
    failedtest_combined_upper_digit:
        addi a4, a4, 48         # '0'
    failedtest_combined_upper_write:
        sb a4, 0(a2)
        addi a2, a2, 1
        bnez a3, failedtest_combined_upper_loop
        # Convert lower half nibbles
        mv a0, a1
        li a3, __riscv_xlen
    failedtest_combined_lower_loop:
        addi a3, a3, -4
        srl a4, a0, a3
        andi a4, a4, 15
        LI(a5, 10)
        blt a4, a5, failedtest_combined_lower_digit
        addi a4, a4, 87         # 'a' - 10
        j failedtest_combined_lower_write
    failedtest_combined_lower_digit:
        addi a4, a4, 48         # '0'
    failedtest_combined_lower_write:
        sb a4, 0(a2)
        addi a2, a2, 1
        bnez a3, failedtest_combined_lower_loop
        # Add newline and null terminator
        LI(a3, 10)              # '\n'
        sb a3, 0(a2)
        sb zero, 1(a2)          # null terminator
        ret
#endif
.endm

// Macro to define failure code data section
// This should be called separately in the RVTEST_DATA_END section to avoid mixing code and data
.macro RVTEST_FAILURE_DATA
    .data
    .align 4
    failure_type:                # 0=int, 1=fp, 2=fflags (reuses x0 slot at offset 0)
    begin_failure_scratch:
        .fill 64, 4, 0xfeedf00dbaaaaaad
    failing_instruction:
        .fill 1, 4, 0xfeedf00d
    failing_reg:
        .fill 1, 4, 0xbaaaaaad
    failing_addr:
        .fill 2, 4, 0xfeedf00dbaaaaaad
    failing_value:
        .fill 2, 4, 0xfeedf00dbaaaaaad
    expected_value:
        .fill 2, 4, 0xfeedf00dbaaaaaad
    failure_string_ptr:
        .fill 2, 4, 0xfeedf00dbaaaaaad
#if defined(RVTEST_FP) && FLEN > XLEN
    failing_value_upper:
        .fill 2, 4, 0xfeedf00dbaaaaaad
    expected_value_upper:
        .fill 2, 4, 0xfeedf00dbaaaaaad
#endif
    ascii_buffer:
        .fill 40, 1, 0          # Buffer for hex string conversion (max "0x" + 16 + 16 + "\n" + null)
    end_failure_scratch:

    successstr:
        // Sequence of .ascii and .asciz is used to create a multi-part string with a single null terminator
        // clang does not allow implicit string concatenation with .string directives
        #ifdef RVTEST_SELFCHECK
            .ascii "\nRVCP-SUMMARY: Test File \""
            .ascii TEST_FILE
            .asciz "\": PASSED\n\n"
        #else
            .ascii "\nRVCP-SUMMARY: Test File \""
            .ascii TEST_FILE
            .asciz "\": SIGRUN\n"
        #endif
    failstr:
        .ascii "\nRVCP-SUMMARY: Test File \""
        .ascii TEST_FILE
        .asciz "\": FAILED\nRVCP: DEBUG INFORMATION FOLLOWS\n"
    abortstr:
        .string "\"The trap handler aborted the test before normal completion!\"";
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
    fflagsstr:
        .string "fflags\n"
.endm
