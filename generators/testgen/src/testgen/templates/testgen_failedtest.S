

# Expects a PC16550-compatible UART.
# Change these addresses to match your memory map
.EQU UART_ENABLED, 1                     # set to 0 to not print
.EQU UART_BASE_ADDR, 0x10000000
.EQU UART_THR, (UART_BASE_ADDR + 0)
.EQU UART_RBR, (UART_BASE_ADDR + 0)
.EQU UART_LCR, (UART_BASE_ADDR + 3)
.EQU UART_LSR, (UART_BASE_ADDR + 5)

# Expects a SiFive-compatible GPIO
# Change these addresses to match your memory map
.EQU GPIO_ENABLED, 1
.EQU GPIO_BASE_ADDR, 0x10060000
.EQU GPIO_OUTPUT_EN, (GPIO_BASE_ADDR + 4)
.EQU GPIO_OUTPUT_VAL, (GPIO_BASE_ADDR + 8)

# self-checking test extracts the address of the failing test
# and the actual and expected values

# Log failure.  x31 contains return address of jal from the failure and x30 is vacant
failedtest:
    la x30, begin_signature
    SREG x31, 248(x30) # store return address
    j failedtest_saveregs

# like failedtest, but x29 contains the return address from the failure and x28 is vacant
failedtest2:
    la x28, begin_signature
    SREG x29, 232(x28) # store return address
    SREG x30, 240(x28) # save x30
    SREG x31, 248(x28) # save x31
    mv x31, x29      # move return address into x31
    la x30, begin_signature
    # now x31 has the return address of jal from the failure and x30 is vacant.
    # resume as with failedtest

# for the rest of this code, x31 contains return address of jal from the valure, x30 points to signature
failedtest_saveregs:
    SREG x1, 8(x30)
    SREG x2, 16(x30)
    SREG x3, 24(x30)
    SREG x4, 32(x30)
    SREG x5, 40(x30)
    SREG x6, 48(x30)
    SREG x7, 56(x30)
    SREG x8, 64(x30)
    SREG x9, 72(x30)
    SREG x10, 80(x30)
    SREG x11, 88(x30)
    SREG x12, 96(x30)
    SREG x13, 104(x30)
    SREG x14, 112(x30)
    SREG x15, 120(x30)
    SREG x16, 128(x30)
    SREG x17, 136(x30)
    SREG x18, 144(x30)
    SREG x19, 152(x30)
    SREG x20, 160(x30)
    SREG x21, 168(x30)
    SREG x22, 176(x30)
    SREG x23, 174(x30)
    SREG x24, 192(x30)
    SREG x25, 200(x30)
    SREG x26, 208(x30)
    SREG x27, 216(x30)
    SREG x28, 224(x30)
    SREG x29, 232(x30)
    # x30 and x31 have already been saved if relevant

# failedtest_saveresults
    # failing instruction might be 16 or 32 bits, on a 16-byte boundary.
    # fetch with halfwords, report all 32 bits, let user figure it out
    lhu t0, -10(x31)    # get upper half of the failing instruction
    lhu t1, -12(x31)     # get lower half
    slli t0, t0, 16     # reassemble
    or t0, t0, t1
    sw t0, 256(x30)     # record 32 bits of failing instruction.  Actual instruction might be top half
    # branch might be on 16-byte boundary, so fetch with halfword
    lhu t0, -6(x31)     # get upper half of the the beq that compared good and bad registers
    lhu t1, -8(x31)     # get lower half of the beq
    slli t0, t0, 16     # reassemble beq
    or t0, t0, t1
    # extract rs1 and rs2 from branch
    srli t0, x31, 15
    andi t1, t0, 31     # t1 = rs1 of branch
    sw t1, 260(x30)     # record id of failing register
    srli t0, t0, 5
    andi t2, t0, 31     # t2 = rs2 of branch
    # save bad value form rs1
    slli t0, t1, 3      # rs1 * 8
    add  t0, x30, t0    # address of signature memory containing rs1
    LREG t0, 0(t0)        # value of rs1 (bad result of operation)
    SREG t0, 272(x30)     # record bad value
    # save expected value from rs2
    slli t0, t2, 3      # rs2 * 8
    add t0, x30, t0     # address of signature memory containing rs2
    LREG t0, 0(t0)        # value of rs2 (expected result of operation)
    SREG t0, 280(x30)     # record expected value
    # Save failing address
    addi t0, x31, -12   # address of the failing instruction (possibly including half of previous instruction)
    SREG t0, 264(x30)

# print results
    jal failedtest_uartinit
    la a0, failstr  # print failure
    jal failedtest_printstr
    la a0, failing_instruction
    jal failedtest_printhexln
    la a0, failing_addr
    jal failedtest_printhexln32
    la a0, failing_reg
    jal failedtest_printhexln32
    la a0, failing_value
    jal failedtest_printhexln
    la a0, expected_value
    jal failedtest_printhexln

# raise GPIO
# ideally the startup code would do OUTPUT_EN and set the pins low
# and write_tohost would show success by setting them to 01
    li t0, GPIO_ENABLED
    beqz t0, 1f             # skip if not enabled
    li t0, GPIO_OUTPUT_EN   # address of OUTPUT_EN register
    li t1, 3
    sw t1, 0(t0)            # enable GPIO pins 0 and 1
    li t0, GPIO_OUTPUT_VAL  # address of OUTPUT_VAL register
    sw t1, 0(t0)            # set GPIO pins 0 and 1 high to indicate failure
1:

write_tohost_failure:
    la t1, tohost
    li t0, 3 # failure code
    sw t0, 0(t1)
    sw zero, 4(t1)
    j self_loop

# simple printing routines.  Stack isn't set up, so use dedicated variables

# a0: pointer to null-terminated string to print
failedtest_printstr:
    lb a1, 0(a0)    # fetch a character
    beqz a1, 1f     # terminate if null
    jal a2, failedtest_putch   # print the character
    addi a1, a1, 1  # move to next character
    j failedtest_printstr
1:  ret             # return from function call

# a0: pointer to XLEN-sized number to print in hexadecimal form
failedtest_printhexln:
    li t0, __riscv_xlen     # 32 or 64
failedtest_printhexlnnibble:
    addi t0, t0, -4         # move over one nibble
    srl t1, a0, t0          # shift nibble into bottom bits
    andi t1, t1, 15         # mask upper bits
    li t2, 10               # check if this is a letter
    blt t2, t1, failedtest_printhexlnnumber
    addi t2, t1, 55         # convert letter to ASCII
    j failedtest_printhexlnputch
failedtest_printhexlnnumber:
    addi t0, t0, 48         # convert number to ASCII
failedtest_printhexlnputch:
    jal a2, failedtest_putch  # print the character
    bnez t0, failedtest_printhexlnnibble # repeat until done
    la a1, 10               # print \n character at end
    jal a2, failedtest_putch
    ret

# a0: pointer to 32-bit number to print in hexadecimal form
failedtest_printhexln32:
    li t0, 32               # 32 bits
    j failedtest_printhexlnnibble  # same as above

# Initialize UART
failedtest_uartinit:
    li t0, UART_ENABLED
    beqz t0, 1f             # skip if UART is not enabled
    li t0, UART_LCR
    li t1, 3                # 8-bit characters, 1 stop bit, no parity
    sb t1, 0(t0)
1:
    ret

# a1: character to print
# a2: return address
failedtest_putch:
    li t0, UART_ENABLED
    beqz t0, 1f             # skip if UART is not enabled
    li t0, UART_LSR
failedtest_waituartbusy:
    lbu t1, 0(t0)
    andi t1, t1, 0x20 # check line status register bit 5
    beqz t1, failedtest_waituartbusy # wait until Transmit Holding Register Empty is set

    li t0, UART_THR     # transmit character
    sb a1, 0(t0)
1:  jr a2               # return

.data

.align 4
begin_signature:
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
end_signature:


successstr:
    .string "Tests succeeded\n"
failstr:
    .string "Test failed: Instruction, Address, Register, Bad Value, Expected Value\n"
