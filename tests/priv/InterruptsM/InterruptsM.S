// macro version
///////////////////////////////////////////
// InterruptsM.S
//
// Written: Hjamal@hmc.edu       6 April 2025
//
// Purpose: Functional coverage tests for Machine-mode Interrupts
//
// SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
///////////////////////////////////////////

##### START_TEST_CONFIG #####
# implemented_extensions: [I, S, Zicsr]
# params:
#   M_MODE_ENDIANNESS: dynamic
# MARCH: rv${XLEN}i_zicsr
# CONFIG_DEPENDENT: true
##### END_TEST_CONFIG #####


#define rvtest_mtrap_routine
#define rvtest_strap_routine
#define rvtest_dtrap_routine



# #define ACCESS_FAULT_ADDRESS 0


# # include "model_test.h"
# # include "arch_test.h"
# #include "WALLY-init-lib.h"

#define SIGUPD_COUNT 402
#include "riscv_arch_test.h"


# Test code region
# .section .text.init
# .globl rvtest_entry_point
# rvtest_entry_point:
RVMODEL_BOOT
#RVTEST_CODE_BEGIN
RVTEST_BEGIN

# main:
    la sp, scratch
    // jal reset_mtimecmp
    RVMODEL_CLR_MTIMER_INT

    /////////////////////////////////
    // cp_trigger_mti
    // With mstatus.MIE = {0/1}, and mie = 1s, use MTIMECMP to cause mip.MTIP to rise
    /////////////////////////////////

    cp_trigger_mti:
        li t0, -1               # all 1s
        csrrw t6, mie, t0       # enable all interrupts

        # mstatus.MIE = 0 should not take interrupt
        csrrci t6, mstatus, 8   # mstatus.MIE = 0
        //jal cause_mtimer_interrupt_now
        RVMODEL_CAUSE_MTIMER_INT_NOW
        # NOTE: interrupt is not taken, so it will return here:
        //jal reset_mtimecmp # reset mtimecmp to avoid premature interrupt in next test
        RVMODEL_CLR_MTIMER_INT
        # mstatus.MIE = 1 should take interrupt
        csrrsi t6, mstatus, 8   # mstatus.MIE = 1
        // jal cause_mtimer_interrupt_now # expecting timer interrupt, so interrupt handler will reset mtimecmp
        RVMODEL_CAUSE_MTIMER_INT_NOW

    /////////////////////////////////
    // cp_trigger_msi
    // With mstatus.MIE = {0/1}, and mie = 1s, use CLINT.MSIP to cause mip.MSIP to rise
    /////////////////////////////////

    cp_trigger_msi:
        li t0, -1               # all 1s
        csrrw t6, mie, t0       # enable all interrupts

        # mstatus.MIE = 0 should not take interrupt
        csrrci t6, mstatus, 8   # mstatus.MIE = 0
        // jal set_msip
        RVMODEL_SET_MSW_INT
        // jal reset_msip          # reset mip.MSIP since the trap handler will not reset it if no interrupt occurs
        RVMODEL_CLR_MSIP

        # mstatus.MIE = 1 should take interrupt
        csrrsi t6, mstatus, 8   # mstatus.MIE = 1
        // jal set_msip            # set mip.MSIP, expect interrupt
        RVMODEL_SET_MSW_INT

    /////////////////////////////////
    // cp_trigger_mei
    // With mstatus.MIE = {0/1}, and mie = 1s, use PLIC or other EIC to cause mip.MEIP to rise
    /////////////////////////////////

    cp_trigger_mei:
        li t0, -1               # all 1s
        csrrw t6, mie, t0       # enable all interrupts

        # mstatus.MIE = 0 should not take interrupt
        csrrci t6, mstatus, 8   # mstatus.MIE = 0
        li a3, 0x10 // TODO: why are we loading into a3
        // jal cause_external_interrupt_M
        RVMODEL_CAUSE_MEXT_INT
        // jal reset_external_interrupts
        RVMODEL_CLR_MEXT_INT

        # mstatus.MIE = 1 should take interrupt
        csrrsi t6, mstatus, 8   # mstatus.MIE = 1
        li a3, 0x10 // TODO: why are we loading into a3
        // jal cause_external_interrupt_M
        RVMODEL_CAUSE_MEXT_INT

    /////////////////////////////////
    // cp_trigger_sti
    // With mstatus.MIE = {0/1}, and mie = 1s, write mip.STIP 
    /////////////////////////////////

    cp_trigger_sti:
        li t0, -1               # all 1s
        csrrw t6, mie, t0       # enable all interrupts

        # mstatus.MIE = 0 should not take interrupt
        csrrci t6, mstatus, 8   # mstatus.MIE = 0
        li t0, 32               # 1 in bit 5
        csrrs t6, mip, t0
        csrrc t6, mip, t0       # reset mip.STIP since the trap handler will not reset it if no interrupt occurs

        # mstatus.MIE = 1 should take interrupt
        csrrsi t6, mstatus, 8   # mstatus.MIE = 1
        csrrs t6, mip, t0       # set mip.STIP, expect interrupt

    /////////////////////////////////
    // cp_trigger_ssi_mip
    // With mstatus.MIE = {0/1}, and mie = 1s, write mip.SSIP
    /////////////////////////////////

    cp_trigger_ssi_mip:
        li t0, -1               # all 1s
        csrrw t6, mie, t0       # enable all interrupts

        # mstatus.MIE = 0 should not take interrupt
        csrrci t6, mstatus, 8   # mstatus.MIE = 0
        csrrsi t6, mip, 2
        csrrci t6, mip, 2       # reset mip.SSIP since the trap handler will not reset it if no interrupt occurs

        # mstatus.MIE = 1 should take interrupt
        csrrsi t6, mstatus, 8   # mstatus.MIE = 1
        csrrsi t6, mip, 2       # set mip.SSIP, expect interrupt

    /////////////////////////////////
    // cp_trigger_sei_plic
    // With mstatus.MIE = {0/1}, and mie = 1s, use PLIC or other EIC to cause mip.SEIP to rise
    /////////////////////////////////

    cp_trigger_sei_plic: // TODO: NOTE: why haven't we set mideleg bit to 1, because otherwise how can it get delegated to S-mode if we are in M-mode?
        li t0, -1               # all 1s
        csrrw t6, mie, t0       # enable all interrupts

        # mstatus.MIE = 0 should not take interrupt
        csrrci t6, mstatus, 8   # mstatus.MIE = 0
        li a3, 0x10
        // jal cause_external_interrupt_S
        RVMODEL_CAUSE_SEXT_INT
        // jal reset_external_interrupts
        RVMODEL_CLR_SEXT_INT

        # mstatus.MIE = 1 should take interrupt
        csrrsi t6, mstatus, 8   # mstatus.MIE = 1
        li a3, 0x10
        // jal cause_external_interrupt_S
        RVMODEL_CAUSE_SEXT_INT

    /////////////////////////////////
    // cp_trigger_sei_sie
    // With mstatus.MIE = {0/1}, and mie = 1s, write mip.SEIP
    /////////////////////////////////

    cp_trigger_sei_sie:
        li t0, -1               # all 1s
        csrrw t6, mie, t0       # enable all interrupts

        # mstatus.MIE = 0 should not take interrupt
        csrrci t6, mstatus, 8   # mstatus.MIE = 0
        li t0, 512              # 1 in bit 9
        csrrs t6, mip, t0       # set mip.SEIP
        csrrc t6, mip, t0       # reset mip.SEIP since the trap handler will not reset it if no interrupt occurs

        # mstatus.MIE = 1 should take interrupt
        csrrsi t6, mstatus, 8   # mstatus.MIE = 1
        csrrs t6, mip, t0       # set mip.SEIP, expect interrupt

    /////////////////////////////////
    // cp_interrupts
    // Cross of mstatus.MIE = {0/1}, mtvec.MODE = 00, 3 walking 1s in mip.MTIP/MSIP/MEIP, 
    // 3 walking 1s in mie.MTIE/MSIE/MEIE (2 x 3 x 3 bins)
    /////////////////////////////////

    cp_interrupts:

        li s0, 1 # iterate through mstatus.MIE values 0-1

        csrrci t6, mtvec, 3 # mtvec.MODE = 00

        for_mstatus:

            bnez s0, set_mstatus
            csrrci t6, mstatus, 8   # if s0 == 0, clear mstatus.MIE
            j cross_interrupts

            set_mstatus:
            csrrsi t6, mstatus, 8 # if s0 == 1, set mstatus.MIE
            
            cross_interrupts:
            jal cross_interrupts_m_EP
            
            addi s0, s0, -1
            bgez s0, for_mstatus # iterate through mstatus.MIE values (1-0)

    /////////////////////////////////
    // cp_vectored
    // Cross of mtvec.MODE = 01, mstatus.MIE=1, all 3 of mie.MTIE/MSIE/MEIE,
    // 3 walking 1s in mip.MTIP/MSIP/MEIP (3 bins)
    /////////////////////////////////

    cp_vectored:

        csrrci t6, mtvec, 3
        csrrsi t6, mtvec, 1 # mtvec.MODE = 01

        csrrsi t6, mstatus, 8 # mstatus.MIE = 1
        csrrw t6, mie, zero     # clear all interrupt enables

        li s1, 0x0888
        csrrs t6, mie, s1       # set mie.MEIE/MTIE/MSIE

        jal raise_interrupts_m

    /////////////////////////////////
    // cp_priority
    // With mstatus.MIE = 1, write cross product of 8 values of mie.{MSIE/MTIE/MEIE}
    // with hardware events giving the 8 values of mip.{MSIP/MTIP/MEIP} and check that
    // the proper interrupt occurs (8 x 8 bins)
    /////////////////////////////////

    cp_priority:

        csrrsi t6, mstatus, 8 # mstatus.MIE = 1

        li s1, 7

        for_mie_priority:

            csrrw t6, mie, zero # clear all interrupt enables to start fresh

            andi t0, s1, 4 # check bit 2
            slli t0, t0, 9 # set mie.MEIE based on bit 2 value
            mv s3, t0

            andi t0, s1, 2  # check bit 1
            slli t0, t0, 6  # set mie.MTIE based on bit 1 value
            or s3, s3, t0 

            andi t0, s1, 1  # check bit 0
            slli t0, t0, 3  # set mie.MSIE based on bit 1 value
            or s3, s3, t0 

            li s2, 7

            for_mip_priority:

                case2_priority:
                    andi t0, s2, 4  # check bit 2
                    beqz t0, case1_priority # set mie.MEIP based on s2 bit 2 value
                    // jal cause_external_interrupt_M
                    RVMODEL_CAUSE_MEXT_INT

                case1_priority:
                    andi t0, s2, 2  # check bit 1
                    beqz t0, case0_priority # set mie.MTIP based on s2 bit 1 value
                     // jal cause_mtimer_interrupt_now
                    RVMODEL_CAUSE_MTIMER_INT_NOW

                case0_priority:
                    andi t0, s2, 1  # check bit 0
                    beqz t0, case_end_priority # set mie.MSIP based on s2 bit 0 value
                    // jal set_msip
                    RVMODEL_SET_MSW_INT

                case_end_priority:
                    
                    csrrs t6, mie, s3   # write to enable certain machine interrupts, should trigger highest-priority pending interrupt
                    csrrc t6, mie, s3   # write to disable those machine interrupts before next test case
                    
                    # add in resets in case s1 == 0
                     //jal reset_external_interrupts
                    RVMODEL_CLR_MEXT_INT
                     // jal reset_mtimecmp
                    RVMODEL_CLR_MTIMER_INT
                    //jal reset_msip
                    RVMODEL_CLR_MSIP
                    
                    addi s2, s2, -1
                    bge s2, zero, for_mip_priority

            addi s1, s1, -1
            bge s1, zero, for_mie_priority

    /////////////////////////////////
    // cp_wfi
    // Cross Product of mstatus.MIE = {0/1},  mstatus.TW = {0/1}, mie.MTIE = 1
    // Set MTIMECMP = TIME + 0x100 to interrupt in the future
    // WFI instruction
    /////////////////////////////////

    cp_wfi:

        li s2, 3

        for_wfi:

            li t0, 0x20000A
            csrrc t6, mstatus, t0 # clear mstatus.TW, MIE, SIE

            case_MIE:
                andi t0, s2, 2  # check bit 1
                beqz t0, case_TW # set mstatus.MIE based on s2 bit 1 value
                csrrsi t6, mstatus, 8 # set mstatus.MIE

            case_TW:
                andi t0, s2, 1  # check bit 0
                beqz t0, case_end_wfi # set mstatus.TW based on s2 bit 0 value
                la t0, 0x200000
                csrrs t6, mstatus, t0 # set mstatus.TW

            case_end_wfi:        
                li t0, 0x080
                csrrw t6, mie, t0 # trap handler clears mie, so set mie.MTIE = 1 just before triggering interrupt
                //jal cause_mtimer_interrupt_soon
                RVMODEL_CAUSE_MTIMER_INT_SOON
                nop
                wfi
                nop
                addi s2, s2, -1
                bge s2, zero, for_wfi

    j test_end

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
        li t0, -1               # set mtimecmp to biggest number so it doesnt interrupt again
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
        csrw stimecmp, t0   # sets stimecmp to big number so it doesnt interrupt
        #ifdef __riscv_xlen
            #if __riscv_xlen == 32
                csrw stimecmph, t0   # for RV32 sets upper word (stimecmph) to big number so it doesnt interrupt
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
        // helper function for crossing mie.MEIE/MTIE/MSIE with mip.MEIP/MTIP/MSIP in Interrupts tests (enables and pending)
        
        addi sp, sp, -8         # save return address to the stack
        SREG ra, 0(sp)
        
        li s1, 2                # iterate through setting mie.MEIE, MTIE, or MSIE (2-0)
        li t1, -1

        for_mie:
        
            slli t3, s1, 2      # setting mie.MEIE, MTIE, or MSIE based on s1 value = {2,1,0}
            li t4, 8
            sll t4, t4, t3      # put a 1 in bit (3+s1*4) of mie
            csrrw t6, mie, t4   # set enable for interrupt type of interest, clear all others
        
            jal raise_interrupts_m
        
            addi s1, s1, -1     
            bge s1, zero, for_mie # iterate through interrupt types to be enabled

        LREG ra, 0(sp)
        addi sp, sp, 8
            
        ret

    raise_interrupts_m:
        // raises each of mip.MEIP/MTIP/MSIP once in sequence

        addi sp, sp, -8
        SREG ra, 0(sp)

        li s2, 2

        for_mip:
            
            # based on s2 value, attempt to trigger one of MEIP (s2=2), MTIP (s2=1), or MSIP (s2=0)
            # includes resets in case interrupt is not triggered
            
            for_mip_meip:
                li t3, 2
                bne s2, t3, for_mip_mtip        # if s2 == 2, trigger external interrupt
                csrr t6, mie            # if interrupt is raised, mie will be cleared, so save it
                //jal cause_external_interrupt_M
                RVMODEL_CAUSE_MEXT_INT
                // jal reset_external_interrupts
                RVMODEL_CLR_MEXT_INT
                csrw mie, t6                    # restore mie to test next cases

            for_mip_mtip:
                li t3, 1
                bne s2, t3, for_mip_msip        # if s2 == 1, trigger timer interrupt
                csrr t6, mie            # if interrupt is raised, mie will be cleared, so save it
                // jal cause_mtimer_interrupt_now
                RVMODEL_CAUSE_MTIMER_INT_NOW
                // jal reset_mtimecmp
                RVMODEL_CLR_MTIMER_INT
                csrw mie, t6                    # restore mie to test next cases

            for_mip_msip:
                li t3, 0
                bne s2, t3, for_mip_end         # if s2 = 0, trigger software interrupt
                csrr t6, mie            # if interrupt is raised, mie will be cleared, so save it
                // jal set_msip
                RVMODEL_SET_MSW_INT
                // jal reset_msip
                RVMODEL_CLR_MSIP
                csrw mie, t6                    # restore mie to test next cases

            for_mip_end:
                addi s2, s2, -1
                bge s2, zero, for_mip

        LREG ra, 0(sp)
        addi sp, sp, 8

        ret

    test_end:
        li a0, 4            # argument to finish program
        ecall               # system call to finish program
    #     j done
    
    # done:
    #     li a0, 4            # argument to finish program
    #     ecall               # system call to finish program
    #     j self_loop         # wait forever (not taken)

        # RVMODEL_IO_WRITE_STR(x30, "# Test part A - test M-mode interrupts\n");

        # RVMODEL_IO_WRITE_STR(x30, "# Test End\n")

# #endif

 # ---------------------------------------------------------------------------------------------
    # HALT

# RVTEST_CODE_END
# RVMODEL_HALT

# RVTEST_DATA_BEGIN
# # Input data section.
#     .data
#     .align 4
# RVTEST_DATA_END

# # Output data section.
# RVMODEL_DATA_BEGIN
# rvtest_sig_begin:
# sig_begin_canary:
# CANARY;

# test_A_res:
#     .fill 2, 4, 0xdeadbeef

# mtrap_sigptr:
#   .fill 4, 4, 0xdeadbeef

# #ifdef rvtest_gpr_save
# gpr_save:
#   .fill 32*(XLEN/32), 4, 0xdeadbeef
# #endif

# sig_end_canary:
# CANARY;
# rvtest_sig_end:
# RVMODEL_DATA_END

# scratch:
# .fill 4,4,0x0

# # Initialize stack with room for 512 bytes
# .bss
#     .space 512
# topofstack:


// Instantiate trap handlers and other epilog code, call RVMODEL_HALT at end of test
RVTEST_CODE_END

// Create scratch data sections and label for test data
RVTEST_DATA_BEGIN

// Insert test data here
// @TEST_DATA@ // TODO: Load test data from here instead of using LI

// End of test data section and model specific data
RVTEST_DATA_END

// Signature region for self-checking
RVTEST_SIG_SETUP
