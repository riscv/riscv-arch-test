///////////////////////////////////////////
// WALLY-init-lib.h
//
// Written: David_Harris@hmc.edu 21 March 2023
// Adapted for to support both RV32 and RV64 David_Harris@hmc.edu
// and a fork is moved from cvw/tests/coverage to riscv-arch-test/tests/priv
// because the files are diverging.
//
// Purpose: Initialize stack, handle interrupts, terminate test case
//
// Copyright (C) 2021-23 Harvey Mudd College & Oklahoma State University
//
// SPDX-License-Identifier: Apache-2.0
//
// Unless required by applicable law or agreed to in writing, any work distributed under the
// License is distributed on an “AS IS” BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
// either express or implied. See the License for the specific language governing permissions
// and limitations under the License.
////////////////////////////////////////////////////////////////////////////////////////////////

#include "model_test.h"
#include "arch_test.h"

// load code to initialize stack, handle interrupts, terminate
// The PMP tests are sensitive to the exact addresses in this code, so unfortunately
// modifying anything breaks those tests.

// Provides simple firmware services through ecall.  Place argument in a0 and issue ecall:
//  0: change to user mode
//  1: change to supervisor mode
//  3: change to machine mode
//  4: terminate program
//
// ExceptionsS.S tests for delegated ecalls from user mode to supervisor mode.
// To return back to machine mode the s_traphandler in ExceptionsS.S executes an ecall
// To signal to the machine mode trap handler that this call was issued from supervisor mode
// the a0 register inputs are 5-9.  The machine mode trap handler will then use sepc instead
// of mepc to return to the instruction that caused the exception.
// Reserved a0 values:
//   5: Change to user mode       (mret to address in sepc)
//   6: Change to supervisor mode (mret to address in sepc)
//   8: Change to machine mode    (mret to address in sepc)
//Macros
//#define ACCESS_FAULT_ADDRESS 0  //defined again in rvtest_config.h
#define CLINT_BASE_ADDR 0x02000000
#define PLIC_BASE_ADDR 0x0C000000
#define GPIO_BASE_ADDR 0x10060000

#define MTIME           (CLINT_BASE_ADDR + 0xBFF8)
#define MSIP            (CLINT_BASE_ADDR)
#define MTIMECMP        (CLINT_BASE_ADDR + 0x4000)
#define MTIMECMPH       (CLINT_BASE_ADDR + 0x4004)

#define THRESHOLD_0     (PLIC_BASE_ADDR + 0x200000)
#define THRESHOLD_1     (PLIC_BASE_ADDR + 0x201000)
#define INT_PRIORITY_3  (PLIC_BASE_ADDR + 0x00000C)
#define INT_EN_00       (PLIC_BASE_ADDR + 0x002000)
#define INT_EN_10       (PLIC_BASE_ADDR + 0x002080)

#define GPIO_OUTPUT_EN  (GPIO_BASE_ADDR + 0x08)
#define GPIO_OUTPUT_VAL (GPIO_BASE_ADDR + 0x0C)

// define load and store instruction
#ifdef __riscv_xlen
    #if __riscv_xlen == 32
        #define LREG lw
        #define SREG sw
    #else
        #define LREG ld
        #define SREG sd
    #endif
#else
    ERROR: __riscv_xlen not defined
#endif

.section .text.init
.global rvtest_entry_point

rvtest_entry_point:
    la sp, topofstack    # Initialize stack pointer (not used)
    jal reset_mtimecmp   # disable timer interrupts by setting mtimecmp to 1s (needed for Sail; Spike defaults to resetting this way)

    # Set up interrupts
    la t0, trap_handler
    csrw mtvec, t0      # Initialize MTVEC to trap_handler
    la t0, topoftrapstack
    csrw mscratch, t0   # MSCRATCH holds trap stack pointer
    csrw sscratch, t0   # SSCRATCH holds trap stack pointer
    csrw mideleg, zero  # Don't delegate interrupts
    csrw medeleg, zero  # Don't delegate exceptions
    li t0, 0x80
    csrw mie, t0        # Enable machine timer interrupt
    csrsi mstatus, 0x8  # Turn on mstatus.MIE global interrupt enable
    # set up PMP so user and supervisor mode can access full address space
    csrw pmpcfg0, 0xF   # configure PMP0 to TOR RWX
    li t0, 0xFFFFFFFF
    csrw pmpaddr0, t0   # configure PMP0 top of range to 0xFFFFFFFF to allow all 32-bit addresses
    j main              # Call main function in user test program

done:
    li a0, 4            # argument to finish program
    ecall               # system call to finish program
    j self_loop         # wait forever (not taken)


.align 8                # trap handlers aligned to multiple of 2^8
trap_handler:
    nop
    nop
    nop
    nop
    nop
    nop
    nop
    nop
    nop
    nop
    nop
    nop
    nop                 # nops to allow for vectored interrupts
    # Load trap handler stack pointer tp
    csrrw tp, mscratch, tp  # swap MSCRATCH and tp
    SREG t0, 0(tp)        # Save t0, t1, and ra on the stack
    SREG t1, -8(tp)
    SREG ra, -16(tp)
    csrr t0, mcause     # Check the cause
    csrr t1, mtval      # And the trap value
    bgez t0, exception  # if msb is clear, it is an exception

interrupt:              # must be an interrupt
    jal reset_mtimecmp
    # *** following function assumes Sstc is supported
    jal reset_stimecmp

    jal reset_msip
    jal reset_external_interrupts

    li t0, 546          # 1 in bits 1, 4, and 9
    csrc mip, t0        # reset mip.STIP, SSIP, and SEIP

    j trap_return       # clean up and return

exception:
    csrr t0, mcause
    li t1, 8                 # is it an ecall trap?
    andi t0, t0, 0xFC        # if CAUSE = 8, 9, or 11
    bne t0, t1, exception_return  # ignore other exceptions

ecall:

    li t0, 5
    bge a0, t0, scallM


    li t0, 4
    beq a0, t0, write_tohost        # call 4: terminate program
    bltu a0, t0, changeprivilege    # calls 0-3: change privilege level
    j exception_return                   # ignore other ecalls


scallM:
    csrr   t0, sepc           # Load faulting instruction address from sepc

    # address was already validated by strap handler
    # move correct address to mepc
    csrw mepc, t0

    addi a0, a0, -5            #convert a0 to priv mode

changeprivilege:
    li t0, 0x00001800    # mask off mstatus.MPP in bits 11-12
    csrc mstatus, t0
    andi a0, a0, 0x00f   # only keep bottom 4 bits of argument
    slli t0, a0, 11      # move into mstatus.MPP position
    csrs mstatus, t0     # set mstatus.MPP with desired privilege

exception_return:             # add 2 or 4 to mepc for exceptions except Instruction Access Fault
    # First, check if the exception was an Instruction Access Fault
    csrr  t1, mcause              # t1 = exception cause
    addi  t1, t1, -1              # Exception cause code 1 means Instruction Access Fault
    bne   t1, x0, mepc_ret_addr   # If not an IAF, skip ra load
    mv t0, ra
    # If its an IAF then it was called with a JALR (rd = PC +4). So subtract 4 from ra to get faulting address
    addi t0, t0, -4
    j post_ret_mepc               #Use ra instead of mepc if IAF
mepc_ret_addr:
    csrr t0, mepc       # get address of instruction that caused exception if not an IAF
post_ret_mepc:
    li t1, 0x20000
    csrs mstatus, t1    # set mprv bit to fetch instruction with permission of code that trapped
    lh t0, 0(t0)        # get instruction that caused exception
    csrc mstatus, t1    # clear mprv bit to restore normal operation
    li t1, 3
    and t0, t0, t1      # mask off upper bits
    beq t0, t1, instr32 # if lower 2 bits are 11, instruction is uncompresssed
    li t0, 2            # increment PC by 2 for compressed instruction
    j updateepc
instr32:
    li t0, 4
updateepc:
    # First, check if the exception was an Instruction Access Fault
    csrr   t1, mcause            # t1 = exception cause
    addi   t1, t1, -1            # Exception cause code 1 means Instruction Access Fault
    bne    t1, x0, mepc_up_addr  # If not an IAF, skip ra load
    mv t0, ra                    # Jal already increments by 4 so its safe to overwrite t0 for an IAF
    j post_up_mepc               # Use ra instead of mepc (skips next instruction)
mepc_up_addr:
    csrr t1, mepc
post_up_mepc:
    add t1, t1, t0               # add 2 or 4 (from t0) to MEPC to determine return Address
    csrw mepc, t1
trap_return:                     # don't need to update mepc for interrupts
    LREG t0, 0(tp)         # Restore t0, t1, and ra
    LREG t1, -8(tp)
    LREG ra, -16(tp)
    csrrw tp, mscratch, tp   # restore tp
    mret                     # return from trap

//write_tohost:
    // la t1, tohost
    // li t0, 1            # 1 for success, 3 for failure
    // SREG t0, 0(t1)     # write success code to tohost

write_tohost:
    li x1, 1
    la t0, tohost
    sw x1, 0(t0)
    sw x0, 4(t0)

self_loop:
    j self_loop         # wait

/////////////////////////////////
// Fast trap handler for illegal instructions (when testing writes to CSRs that may be non-existent)
// This handler processes illegal instructions by adding 4 to mepc and returning.  It only works
// for uncompressed instructions, and will behave in unpredictable ways for illegal compressed
// isntructions.  It handles other traps by calling the regular trap handler.
/////////////////////////////////

.align 4                # trap handlers must be aligned to multiple of 4
trap_handler_fastuncompressedillegalinstr:
    # Load trap handler stack pointer tp
    csrrw tp, mscratch, tp  # swap MSCRATCH and tp
    SREG t0, 0(tp)        # Save t0, t1, and ra on the stack
    SREG t1, -8(tp)
    SREG ra, -16(tp)
    csrr t0, mcause     # Check the cause
    li t1, 2            # Illegal Instruction cause
    beq t0, t1, illegalinstruction # check if this is an uncompressed illegal instruction, then return fast
othertrap:
    # Otherwise use the regular trap handler
    csrr t1, mtval      # And the trap value
    bgez t0, exception  # if msb is clear, it is an exception
    j interrupt         # otherwise interrupt.

illegalinstruction:
    csrr t0, mtval      # get the instruction that caused the exception (assumes mtval is implemented to return instruction)
    li t1, 3            # mask for uncompressed instruction op
    and t0, t0, t1      # mask off upper bits
    bne t0, t1, othertrap   # compressed instructions use regular trap handler
uncompressedillegalinstructionreturn:            # return from trap handler.  Fast because it knows instructions are 4-byte aligned
    csrr t0, mepc  # get address of instruction that caused exception
    addi t0, t0, 4
    csrw mepc, t0
    LREG t0, 0(tp)        # Restore t0, t1, and ra
    LREG t1, -8(tp)
    LREG ra, -16(tp)
    csrrw tp, mscratch, tp  # restore tp
    mret                # return from trap

/////////////////////////////////
// Fast trap to return to the next uncompressed
// This handler is just meant for speedy illegal instruction handling.
// It can't handle anything else including compressed instructions,
// so point to a regular trap handler before needing others.
/////////////////////////////////

.align 4                # trap handlers must be aligned to multiple of 4
trap_handler_returnplus4:
    csrr t0, mepc
    addi t0, t0, 4
    csrw mepc, t0
    mret

/////////////////////////////////
// Fast trap to return to the next compressed
// This handler is just meant for speedy illegal instruction handling.
// It can't handle anything else including uncompressed instructions,
// so point to a regular trap handler before needing others.
/////////////////////////////////

.align 4                # trap handlers must be aligned to multiple of 4
trap_handler_returnplus2:
    csrr t0, mepc
    addi t0, t0, 2
    csrw mepc, t0
    mret

/////////////////////////////////
// Interrupt reset routines
/////////////////////////////////

reset_msip:
    la t0, MSIP
    lw t1, 0(t0)
    andi t1, t1, -2 # clear lowest bit for hart 0 while preserving all other bits
    sw t1, 0(t0)

    ret

reset_external_interrupts:
    # set M-mode interrupt threshold to 7
    la t0, THRESHOLD_0
    li t1, 7
    sw t1, 0(t0)

    # set S-mode interrupt threshold to 7
    la t0, THRESHOLD_1
    li t1, 7
    sw t1, 0(t0)

    // disable GPIO's sufficient priority to trigger interrupt
    la t0, INT_PRIORITY_3
    sw zero, 0(t0)

    // disable interrupts from source 3 (GPIO) in M-mode
    la t0, INT_EN_00
    sw zero, 0(t0)

    // clear all interrupt enables to make sure interrupt doesn't go off prematurely
    la t0, GPIO_BASE_ADDR
    sw zero, 0x18(t0) # clear rise
    sw zero, 0x20(t0) # clear fall
    sw zero, 0x28(t0) # clear high
    sw zero, 0x30(t0) # clear low

    ret

reset_mtimecmp:
    // resets M-mode timer compare register to prevent further M-mode timer interrupts
    li t0, -1               # set mtimecmp to biggest number so it doesn't interrupt again
    la t1, MTIMECMP
    SREG t0, 0(t1)
    #ifdef __riscv_xlen
        #if __riscv_xlen == 32
            sw t0, 4(t1)
        #endif
    #else
        ERROR: __riscv_xlen not defined
    #endif

    ret

reset_stimecmp:
    // resets S-mode timer compare register to prevent further S-mode timer interrupts
    li t0, -1
    csrw stimecmp, t0   # sets stimecmp to big number so it doesn't interrupt
    #ifdef __riscv_xlen
        #if __riscv_xlen == 32
            csrw stimecmph, t0   # for RV32 sets upper word (stimecmph) to big number so it doesn't interrupt
        #endif
    #else
        ERROR: __riscv_xlen not defined
    #endif

    ret

/////////////////////////////////
// Interrupt trigger routines
/////////////////////////////////

set_msip:
    // sets the M-mode software interrupt bit in CLINT
    la t0, MSIP
    lw t1, 0(t0)
    ori t1, t1, 1 # set lowest bit for hart 0
    sw t1, 0(t0)

    ret

cause_external_interrupt_M:
    // raises an external M-mode interrupt using GPIO
    # set M-mode interrupt threshold to 0
    la t0, THRESHOLD_0
    sw zero, 0(t0)

    # set S-mode interrupt threshold to 7
    la t0, THRESHOLD_1
    li t1, 7
    sw t1, 0(t0)

    # give GPIO sufficient priority to trigger interrupt
    la t0, INT_PRIORITY_3
    li t1, 1
    sw t1, 0(t0)

    # clear all interrupt enables to make sure interrupt doesn't go off prematurely
    la t0, GPIO_BASE_ADDR
    li t1, 1
    sw t1, 0x08(t0) # enable output on pin 1
    sw t1, 0x04(t0) # enable input on pin 1

    sw zero, 0x18(t0) # clear rise enable
    sw zero, 0x20(t0) # clear fall enable
    sw zero, 0x28(t0) # clear high enable
    sw zero, 0x30(t0) # clear low enable

    # enable interrupts from source 3 (GPIO) in M-mode
    la t0, INT_EN_00
    li t1, 0b1000
    sw t1, 0(t0)

    # enable interrupts from high output
    la t0, GPIO_BASE_ADDR
    li t1, 1
    sw t1, 0x28(t0) # enable high interrupt for pin 1
    sw t1, 0x0C(t0) # write 1 to pin 1, this should cause interrupt

    ret

cause_external_interrupt_S:
    // raises an external S-mode interrupt using GPIO
    # set M-mode interrupt threshold to 7
    la t0, THRESHOLD_0
    li t1, 7
    sw t1, 0(t0)

    # set S-mode interrupt threshold to 0
    la t0, THRESHOLD_1
    sw zero, 0(t0)

    # give GPIO sufficient priority to trigger interrupt
    la t0, INT_PRIORITY_3
    li t1, 1
    sw t1, 0(t0)

    # clear all interrupt enables to make sure interrupt doesn't go off prematurely
    la t0, GPIO_BASE_ADDR
    li t1, 1
    sw t1, 0x08(t0) # enable output on pin 1
    sw t1, 0x04(t0) # enable input on pin 1

    sw zero, 0x18(t0) # clear rise enable
    sw zero, 0x20(t0) # clear fall enable
    sw zero, 0x28(t0) # clear high enable
    sw zero, 0x30(t0) # clear low enable

    # enable interrupts from source 3 (GPIO) in S-mode
    la t0, INT_EN_10
    li t1, 0b1000
    sw t1, 0(t0)

    # enable interrupts from high output
    la t0, GPIO_BASE_ADDR
    li t1, 1
    sw t1, 0x28(t0) # enable high interrupt for pin 1
    sw t1, 0x0C(t0) # write 1 to pin 1, this should cause interrupt

    ret

cause_mtimer_interrupt_now:
    // raises an M-mode timer interrupt using CLINT, interrupt is raised as soon as the function writes to MTIMECMP(H)

    la t0, MTIME
    la t1, MTIMECMP
    LREG t2, 0(t0) # read MTIME
    SREG t2, 0(t1) # set MTIMECMP = MTIME to cause timer interrupt

    #ifdef __riscv_xlen
        #if __riscv_xlen == 32
                lw t2, 4(t0) # high word of MTIME
                sw t2, 4(t1) # MTIMECMP high word = MTIME high word
        #endif
    #else
        ERROR: __riscv_xlen not defined
    #endif

    ret

cause_mtimer_interrupt_soon:
    // raises an M-mode timer interrupt using CLINT, interrupt is raised 256 (255) cycles after write to MTIMECMP(H)
    la t0, MTIME
    la t4, MTIMECMP

    #ifdef __riscv_xlen
        #if __riscv_xlen == 64
                ld t0, 0(t0)                    # read MTIME

                addi t0, t0, 0x100              # create a delay

                sd t0, 0(t4)         # set MTIMECMP = MTIME + 0x100 to cause timer interrupt later

        #elif __riscv_xlen == 32
                lw t1, 0(t0)                    # low word of MTIME
                lw t2, 4(t0)                    # high word of MTIME

                addi t3, t1, 0x100              # add 0x100 to MTIME value
                bgtu t1, t3, MTIME_overflow     # if overflow occurred, carry the 1 to MTIME high word
                j write_MTIMECMP                # otherwise, leave MTIME high word untouched

                MTIME_overflow:
                addi t2, t2, 1

                write_MTIMECMP:
                sw t3, 0(t4)          # MTIMECMP = MTIME + 0x100
                sw t2, 4(t4)
        #endif
    #else
        ERROR: __riscv_xlen not defined
    #endif
    ret

cross_interrupts_m_EP:
    // helper function for crossing mie.MEIE/MSIE/MTIE with mip.MEIP/MSIP/MTIP in Interrupts tests (enables and pending)
    li s1, 2                # iterate through setting mie.MEIE, MSIE, or MTIE (2-0)
    li t1, -1

    addi sp, sp, -8
    SREG ra, 0(sp)

    for_mie:

        slli t3, s1, 2      # setting mie.MEIE, MSIE, or MTIE based on s1 value
        li t4, 8
        sll t4, t4, t3
        csrrw t6, mie, t4   # set enable for interrupt type of interest, clear all others

        jal raise_interrupts_m

        addi s1, s1, -1
        bge s1, zero, for_mie # iterate through interrupt types to be enabled

    LREG ra, 0(sp)
    addi sp, sp, 8

    ret

raise_interrupts_m:
    // raises each of mip.MEIP/MSIP/MTIP once in sequence

    addi sp, sp, -8
    SREG ra, 0(sp)

    li s2, 2

    for_mip:

        # based on s2 value, attempt to trigger one of MEIP, MSIP, or MTIP
        # includes resets in case interrupt is not triggered

        case2_vectored:
            li t3, 2
            bne s2, t3, case1_vectored      # if s2 == 2, trigger timer interrupt
            jal cause_mtimer_interrupt_now
            jal reset_mtimecmp

        case1_vectored:
            li t3, 1
            bne s2, t3, case0_vectored      # if s2 == 1, trigger external interrupt
            jal cause_external_interrupt_M
            jal reset_external_interrupts

        case0_vectored:
            li t3, 0
            bne s2, t3, case_end_vectored   # if s2 = 0, trigger software interrupt
            jal set_msip
            jal reset_msip

        case_end_vectored:
            addi s2, s2, -1
            bge s2, zero, for_mip

    LREG ra, 0(sp)
    addi sp, sp, 8

    ret

// utility routines

# put a 1 in msb of a0 (position XLEN-1); works for both RV32 and RV64
setmsb:
    li a0, 0x80000000   # 1 in bit 31
    #ifdef __riscv_xlen
        #if __riscv_xlen == 64
            slli a0, a0, 32     # shift a0 to have 1 in bit 63
        #endif
    #else
        ERROR: __riscv_xlen not defined
    #endif
    ret                 # return to caller

.section .tohost
tohost:                 # write to HTIF
    .dword 0
fromhost:
    .dword 0

//.EQU XLEN,64
begin_signature:
    .fill 6*(XLEN/32),4,0xdeadbeef    #
end_signature:

scratch:
    .fill 4,4,0x0

# Initialize stack with room for 512 bytes
.bss
    .space 512
topofstack:
# And another stack for the trap handler
.bss
    .space 512
topoftrapstack:

.align 4
.section .text.main
