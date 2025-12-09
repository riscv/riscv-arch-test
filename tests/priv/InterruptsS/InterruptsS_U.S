///////////////////////////////////////////
// InterruptsS_M.S
//
// Written: Hjamal@hmc.edu       6 April 2025
//
// Purpose: Functional coverage tests for Supervisor-mode Interrupts running in User mode
//
// SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
///////////////////////////////////////////


##### START_TEST_CONFIG #####
# REQUIRED_EXTENSIONS: [I, S, Zicsr]
# MARCH: rv${XLEN}i_zicsr
# CONFIG_DEPENDENT: true
##### END_TEST_CONFIG #####


#define rvtest_mtrap_routine
#define rvtest_strap_routine


#define SIGUPD_COUNT 402
#define TEST_FILE "InterruptsS_S.S"
#include "riscv_arch_test.h"



RVTEST_BEGIN


   ALL_MEM_PMP                                                             // set the PMP permissions for the whole memory
   csrw satp, zero                                                         // write satp with all zeros (bare mode)
  
   //la sp, topofstack
   la sp, scratch
   //jal reset_mtimecmp
   RVMODEL_CLR_MTIMER_INT


   RVTEST_GOTO_LOWER_MODE Smode


   ///////////////////////////////
   // cp_user_mti
   //
   // Cross of mstatus.MIE = {0/1}, mstatus.SIE = {0/1},
   // stvec.MODE={00/01}, mideleg.MTI = {0/1}, mie.MTIE = 1,
   // set MTIMECMP to trigger interrupt
   ///////////////////////////////


   cp_user_mti:
      
       li a0, 16           # use a0 as bitfield
       RVTEST_GOTO_MMODE   # start test in M-mode to set CSRs


       1:
       addi a0, a0, -1
       andi t0, a0, 8
       csrrci t6, mstatus, 8
       bnez t0, 2f             # set mstatus.MIE with bit 3 of a0
       csrrsi t6, mstatus, 8


       2:
       andi t0, a0, 4
       csrrci t6, mstatus, 2
       bnez t0, 3f             # set mstatus.SIE with bit 2 of a0
       csrrsi t6, mstatus, 2


       3:
       andi t0, a0, 2
       csrrci t6, stvec, 3
       bnez t0, 4f             # set stvec.MODE[0] with bit 1 of a0
       csrrsi t6, stvec, 1


       4:
       andi t0, a0, 1
       li t1, 128
       csrrc t6, mideleg, t1
       bnez t0, 5f             # set mideleg.MTI with bit 0 of a0
       csrrs t6, mideleg, t1


       5:
       li t1, 128
       csrrs t6, mie, t1       # set mie.MTIE = 1
       //jal cause_mtimer_interrupt_now  # set mip.MTIP = 1
       RVMODEL_CAUSE_MTIMER_INT_NOW
       RVTEST_GOTO_LOWER_MODE Umode    # switch to U-mode
       nop                             # expect interrupt if mstatus.SIE = 1
       RVTEST_GOTO_MMODE               # return to M-mode for cleanup
       //jal reset_mtimecmp              # clear mip.MTIP
       RVMODEL_CLR_MTIMER_INT
       bnez a0, 1b                     # loop to next case


   ///////////////////////////////
   // cp_user_msi
   //
   // Cross of mstatus.MIE = {0/1}, mstatus.SIE = {0/1},
   // stvec.MODE={00/01}, mideleg.MSI = {0/1}, mie.MSIE = 1,
   // set CLINT.MSIP to trigger interrupt
   ///////////////////////////////


   cp_user_msi:
      
       li a0, 16           # use a0 as bitfield
       RVTEST_GOTO_MMODE   # start test in M-mode to set CSRs


       1:
       addi a0, a0, -1
       andi t0, a0, 8
       csrrci t6, mstatus, 8
       bnez t0, 2f             # set mstatus.MIE with bit 3 of a0
       csrrsi t6, mstatus, 8


       2:
       andi t0, a0, 4
       csrrci t6, mstatus, 2
       bnez t0, 3f             # set mstatus.SIE with bit 2 of a0
       csrrsi t6, mstatus, 2


       3:
       andi t0, a0, 2
       csrrci t6, stvec, 3
       bnez t0, 4f             # set stvec.MODE[0] with bit 1 of a0
       csrrsi t6, stvec, 1


       4:
       andi t0, a0, 1
       csrrci t6, mideleg, 8
       bnez t0, 5f             # set mideleg.MSI with bit 0 of a0
       csrrsi t6, mideleg, 8


       5:
       csrrsi t6, mie, 8       # set mie.MSIE = 1
       //jal cause_msoftware_interrupt  # set mip.MSIP = 1
       RVMODEL_SET_MSW_INT
       nop
       RVTEST_GOTO_LOWER_MODE Umode    # switch to U-mode
       nop                             # expect interrupt if mstatus.SIE = 1
       RVTEST_GOTO_MMODE               # return to M-mode for cleanup
       //jal reset_msoftware_interrupt              # clear mip.MSIP
       RVMODEL_CLR_MSIP
       bnez a0, 1b                     # loop to next case


   ///////////////////////////////
   // cp_user_mei
   //
   // Cross of mstatus.MIE = {0/1}, mstatus.SIE = {0/1},
   // stvec.MODE={00/01}, mideleg.MEI = {0/1}, mie.MEIE = 1,
   // set PLIC to trigger ME interrupt
   ///////////////////////////////


   cp_user_mei:
      
       li a0, 16           # use a0 as bitfield
       RVTEST_GOTO_MMODE   # start test in M-mode to set CSRs


       1:
       addi a0, a0, -1
       andi t0, a0, 8
       csrrci t6, mstatus, 8
       bnez t0, 2f             # set mstatus.MIE with bit 3 of a0
       csrrsi t6, mstatus, 8


       2:
       andi t0, a0, 4
       csrrci t6, mstatus, 2
       bnez t0, 3f             # set mstatus.SIE with bit 2 of a0
       csrrsi t6, mstatus, 2


       3:
       andi t0, a0, 2
       csrrci t6, stvec, 3
       bnez t0, 4f             # set stvec.MODE[0] with bit 1 of a0
       csrrsi t6, stvec, 1


       4:
       andi t0, a0, 1
       li t1, 2048
       csrrc t6, mideleg, t1
       bnez t0, 5f             # set mideleg.MSI with bit 0 of a0
       csrrs t6, mideleg, t1


       5:
       li t1, 2048
       csrrs t6, mie, t1       # set mie.MEIE = 1
       //jal cause_external_interrupt_M  # set mip.MEIP = 1
       RVMODEL_CAUSE_MEXT_INT
       RVTEST_GOTO_LOWER_MODE Umode    # switch to U-mode
       nop                             # expect interrupt if mstatus.SIE = 1
       RVTEST_GOTO_MMODE               # return to M-mode for cleanup
       //jal reset_external_interrupts   # clear mip.MEIP
       RVMODEL_CLR_MEXT_INT
       bnez a0, 1b                     # loop to next case


   ///////////////////////////////
   // cp_user_sei
   //
   // Cross of mstatus.MIE = {0/1}, mstatus.SIE = {0/1},
   // stvec.MODE={00/01}, mideleg.SEI = {0/1}, mie.SEIE = 1,
   // set PLIC to trigger SE interrupt
   ///////////////////////////////


   cp_user_sei:
      
       li a0, 16           # use a0 as bitfield
       RVTEST_GOTO_MMODE   # start test in M-mode to set CSRs


       1:
       addi a0, a0, -1
       andi t0, a0, 8
       csrrci t6, mstatus, 8
       bnez t0, 2f             # set mstatus.MIE with bit 3 of a0
       csrrsi t6, mstatus, 8


       2:
       andi t0, a0, 4
       csrrci t6, mstatus, 2
       bnez t0, 3f             # set mstatus.SIE with bit 2 of a0
       csrrsi t6, mstatus, 2


       3:
       andi t0, a0, 2
       csrrci t6, stvec, 3
       bnez t0, 4f             # set stvec.MODE[0] with bit 1 of a0
       csrrsi t6, stvec, 1


       4:
       andi t0, a0, 1
       li t1, 512
       csrrc t6, mideleg, t1
       bnez t0, 5f             # set mideleg.MSI with bit 0 of a0
       csrrs t6, mideleg, t1


       5:
       li t1, 512
       csrrs t6, mie, t1       # set mie.SEIE = 1
       //jal cause_external_interrupt_S  # set mip.SEIP = 1
       RVMODEL_CAUSE_SEXT_INT
       RVTEST_GOTO_LOWER_MODE Umode    # switch to U-mode
       nop                             # expect interrupt if mstatus.SIE = 1
       RVTEST_GOTO_MMODE               # return to M-mode for cleanup
       //jal reset_external_interrupts   # clear mip.SEIP
       RVMODEL_CLR_SEXT_INT
       bnez a0, 1b                     # loop to next case


   j test_end




   cross_interrupts_s_EP:
       // helper function for crossing mie.MEIE/MSIE/MTIE with mip.MEIP/MSIP/MTIP in Interrupts tests (enables and pending)
       li s1, 5                # iterate through setting mie.M/SEIE, M/SSIE, or M/STIE (5-0)
       li t1, -1


       addi sp, sp, -8
       SREG ra, 0(sp)


       for_mie:
      
           slli t3, s1, 1      # setting mie.M/SEIE, M/SSIE, or M/STIE based on s1 value
           li t4, 2
           sll t4, t4, t3
           csrrw t6, mie, t4   # set enable for interrupt type of interest, clear all others
      
           jal raise_interrupts_s
      
           addi s1, s1, -1    
           bge s1, zero, for_mie # iterate through interrupt types to be enabled


       LREG ra, 0(sp)
       addi sp, sp, 8
          
       ret


   raise_interrupts_s:
       // raises each of mip.M/SEIP/M/SSIP/M/STIP once in sequence


       addi sp, sp, -8
       SREG ra, 0(sp)


       li s2, 5


       for_mip:
          
           # based on s2 value, attempt to trigger one of M/SEIP, M/SSIP, or M/STIP
           # includes resets in case interrupt is not triggered


           case5_vectored:
               li t3, 5
               bne s2, t3, case4_vectored
              
               li t1, 32
               csrrs t6, mip, t1
               RVTEST_GOTO_LOWER_MODE Smode
               csrrci t6, sstatus, 2
               csrrsi t6, sstatus, 2
               RVTEST_GOTO_MMODE
               li t1, 32
               csrrc t6, mip, t1


           case4_vectored:
               li t3, 4
               bne s2, t3, case3_vectored
               li t0, 512
               csrrs t6, mip, t0
               RVTEST_GOTO_LOWER_MODE Smode
               csrrci t6, sstatus, 2
               csrrsi t6, sstatus, 2
               RVTEST_GOTO_MMODE
               li t0, 512
               csrrc t6, mip, t0
          
           case3_vectored:
               li t3, 3
               bne s2, t3, case3_vectored
               csrrsi t6, mip, 2
               RVTEST_GOTO_LOWER_MODE Smode
               csrrci t6, sstatus, 2
               csrrsi t6, sstatus, 2
               RVTEST_GOTO_MMODE
               csrrci t6, mip, 2
          
           case2_vectored:
               li t3, 2
               bne s2, t3, case1_vectored      # if s2 == 2, trigger timer interrupt
               //jal cause_mtimer_interrupt_now
               RVMODEL_CAUSE_MTIMER_INT_NOW
               RVTEST_GOTO_LOWER_MODE Smode
               csrrci t6, sstatus, 2
               csrrsi t6, sstatus, 2
               RVTEST_GOTO_MMODE
               //jal reset_mtimecmp
               RVMODEL_CLR_MTIMER_INT


           case1_vectored:
               li t3, 1
               bne s2, t3, case0_vectored      # if s2 == 1, trigger external interrupt
               //jal cause_external_interrupt_M
               RVMODEL_CAUSE_MEXT_INT
               RVTEST_GOTO_LOWER_MODE Smode
               csrrci t6, sstatus, 2
               csrrsi t6, sstatus, 2
               RVTEST_GOTO_MMODE
               //jal reset_external_interrupts
               RVMODEL_CLR_MEXT_INT


           case0_vectored:
               li t3, 0
               bne s2, t3, case_end_vectored   # if s2 = 0, trigger software interrupt
               //jal cause_msoftware_interrupt
               RVMODEL_SET_MSW_INT
               RVTEST_GOTO_LOWER_MODE Smode
               csrrci t6, sstatus, 2
               csrrsi t6, sstatus, 2
               RVTEST_GOTO_MMODE
               //jal reset_msoftware_interrupt
               RVMODEL_CLR_MSIP


           case_end_vectored:
               addi s2, s2, -1
               bge s2, zero, for_mip


       LREG ra, 0(sp)
       addi sp, sp, 8


       ret




   test_end:
       li a0, 4            # argument to finish program
       ecall               # system call to finish program


// Instantiate trap handlers and other epilog code, call RVMODEL_HALT at end of test
RVTEST_CODE_END

// Create scratch data sections and label for test data
RVTEST_DATA_BEGIN

// ANY DATA THAT YOU NEED FOR YOUR TEST GOES HERE, INCLUDING FAILURE STRINGS
canary_mismatch: .string "Testcase signature canary mismatch!"

// End of test data section and model specific data
RVTEST_DATA_END

// Signature region for self-checking
RVTEST_SIG_SETUP



