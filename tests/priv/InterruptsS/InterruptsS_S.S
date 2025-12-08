///////////////////////////////////////////
// InterruptsS_M.S
//
// Written: Hjamal@hmc.edu       6 April 2025
//
// Purpose: Functional coverage tests for Supervisor-mode Interrupts running in Supervisor mode
//
// SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
///////////////////////////////////////////

//#include "model_test.h"

//#include "arch_test.h"

##### START_TEST_CONFIG #####
# REQUIRED_EXTENSIONS: [I, S, Zicsr]
# MARCH: rv${XLEN}i_zicsr
# CONFIG_DEPENDENT: true
##### END_TEST_CONFIG #####

#define rvtest_mtrap_routine
#define rvtest_strap_routine
#define rvtest_dtrap_routine

#define SIGUPD_COUNT 402
#include "riscv_arch_test.h"


# # Test code region
# .section .text.init
# .globl rvtest_entry_point
# rvtest_entry_point:
RVMODEL_BOOT
RVTEST_BEGIN

    ALL_MEM_PMP          		                  	                      	// set the PMP permissions for the whole memory
	csrw satp, zero  		                                        		// write satp with all zeros (bare mode)
    
    //la sp, topofstack
    la sp, scratch
    //jal reset_mtimecmp
    RVMODEL_CLR_MTIMER_INT

/*
    ///////////////////////////////
    // cp_trigger_mti
    //
    // With mstatus.MIE = 0, mstatus.SIE = {0/1}, mideleg = {0s/1s}, 
    // and mie = 1s, use CLINT.MTIMECMP to cause mip.MTIP to rise
    ///////////////////////////////

    cp_trigger_mti:

        li a0, 4                    # use a0 as bitfield {mideleg, mstatus.SIE}
        RVTEST_GOTO_MMODE           # start in m-mode to control CSRs

        li t0, 8
        csrrc t6, mstatus, t0       # mstatus.MIE = 0

        1:
        addi a0, a0, -1             # decrement a0 specifying bitfields to test
        li t1, -1
        csrrw t6, mie, t1           # enable all interrupts
        csrrw t6, mideleg, zero     # disable delegation
        andi t0, a0, 2              # toggle mideleg using bit 1 of a0
        beqz t0, 2f
        li t1, 0x222
        csrrw t6, mideleg, t1       # mideleg STI+SEI+SSI
        
        2:
        li t1, 2
        csrrc t6, mstatus, t1
        andi t0, a0, 1              # toggle mstatus.SIE using bit 0 of a0
        beqz t0, 3f 
        csrrs t6, mstatus, t1

        3:
        
        //jal cause_mtimer_interrupt_now   # no interrupt yet because not delegated and mstatus.MIE = 0
        RVMODEL_CAUSE_MTIMER_INT_NOW
        nop
        RVTEST_GOTO_LOWER_MODE Smode
        nop                              # Interrupt to machine mode will occur because not delegated
        RVTEST_GOTO_MMODE
        //jal reset_mtimecmp               # reset mtimecmp to avoid premature interrupt in next test
        RVMODEL_CLR_MTIMER_INT
        bnez a0, 1b


    ///////////////////////////////
    // cp_trigger_msi
    //
    // With mstatus.MIE = 0, mstatus.SIE = {0/1}, mideleg = {0s/1s}, 
    // and mie = 1s, use CLINT.MSIP to cause mip.MSIP to rise
    ///////////////////////////////

    cp_trigger_msi:

        li a0, 4                    # use a0 as bitfield {mideleg, mstatus.SIE}
        RVTEST_GOTO_MMODE           # start in m-mode to control CSRs

        li t0, 8
        csrrc t6, mstatus, t0       # mstatus.MIE = 0

        1:
        addi a0, a0, -1             # decrement a0 specifying bitfields to test
        li t1, -1
        csrrw t6, mie, t1           # enable all interrupts
        csrrw t6, mideleg, zero     # disable delegation
        andi t0, a0, 2              # toggle mideleg using bit 1 of a0
        beqz t0, 2f
        li t1, 0x222
        csrrw t6, mideleg, t1       # mideleg STI+SEI+SSI
        
        2:
        li t1, 2
        csrrc t6, mstatus, t1
        andi t0, a0, 1              # toggle mstatus.SIE using bit 0 of a0
        beqz t0, 3f 
        csrrs t6, mstatus, t1

        3:
        //jal cause_msoftware_interrupt   # no interrupt yet because not delegated and mstatus.MIE = 0
        RVMODEL_SET_MSW_INT
        nop
        RVTEST_GOTO_LOWER_MODE Smode
        nop                             # Interrupt to machine mode will occur because not delegated
        RVTEST_GOTO_MMODE
        //jal reset_msoftware_interrupt   # reset msip to avoid premature interrupt in next test
        RVMODEL_CLR_MSIP
        bnez a0, 1b

    ///////////////////////////////
    // cp_trigger_mei
    //
    // With mstatus.MIE = 0, mstatus.SIE = {0/1}, mideleg = {0s/1s}, 
    // and mie = 1s, use PLIC or other EIC to cause mip.MEIP to rise
    ///////////////////////////////

    cp_trigger_mei:
    
        li a0, 4                    # use a0 as bitfield {mideleg, mstatus.SIE}
        RVTEST_GOTO_MMODE           # start in m-mode to control CSRs

        li t0, 8
        csrrc t6, mstatus, t0       # mstatus.MIE = 0

        1:
        addi a0, a0, -1             # decrement a0 specifying bitfields to test
        li t1, -1
        csrrw t6, mie, t1           # enable all interrupts
        csrrw t6, mideleg, zero     # disable delegation
        andi t0, a0, 2              # toggle mideleg using bit 1 of a0
        beqz t0, 2f
        li t1, 0x222
        csrrw t6, mideleg, t1       # mideleg STI+SEI+SSI
        
        2:
        li t1, 2
        csrrc t6, mstatus, t1
        andi t0, a0, 1              # toggle mstatus.SIE using bit 0 of a0
        beqz t0, 3f 
        csrrs t6, mstatus, t1

        3:
        //jal cause_external_interrupt_M   # no interrupt yet because not delegated and mstatus.MIE = 0
        RVMODEL_CAUSE_MEXT_INT
        nop
        RVTEST_GOTO_LOWER_MODE Smode
        nop                              # Interrupt to machine mode will occur because not delegated
        RVTEST_GOTO_MMODE
        //jal reset_external_interrupts    # reset external interrupts to avoid premature interrupt in next test
        RVMODEL_CLR_MEXT_INT
        bnez a0, 1b

    ///////////////////////////////
    // cp_trigger_sti
    //
    // With mstatus.MIE = 0, mstatus.SIE = {0/1}, mideleg = {0s/1s}, 
    // and mie = 1s, mip.STIP=1, change to supervisor mode
    ///////////////////////////////

    // TODO - come back, 3 traps. 0 interrupts
    cp_trigger_sti:
    
        li a0, 4                    # use a0 as bitfield {mideleg, mstatus.SIE}
        RVTEST_GOTO_MMODE           # start in m-mode to control CSRs

        li t0, 8
        csrrc t6, mstatus, t0       # mstatus.MIE = 0

        1:
        addi a0, a0, -1             # decrement a0 specifying bitfields to test
        li t1, -1
        csrrw t6, mie, t1           # enable all interrupts
        csrrw t6, mideleg, zero     # disable delegation
        andi t0, a0, 2              # toggle mideleg using bit 1 of a0
        beqz t0, 2f
        li t1, 0x222
        csrrw t6, mideleg, t1       # mideleg STI+SEI+SSI
        
        2:
        li t1, 2
        csrrc t6, mstatus, t1
        andi t0, a0, 1              # toggle mstatus.SIE using bit 0 of a0
        beqz t0, 3f 
        csrrs t6, mstatus, t1

        3:
        li t1, 32
        csrrs t6, mip, t1           # write mip.SEIP
       nop
        RVTEST_GOTO_LOWER_MODE Smode
        nop                         # expect interupt to M if undelegated, S if delegated and mstatus.SIE
        nop
        nop
        RVTEST_GOTO_MMODE
        li t1, 32
        csrrc t6, mip, t1
        bnez a0, 1b

    ///////////////////////////////
    // cp_trigger_ssi_mip
    //
    // With mstatus.MIE = 0, mstatus.SIE = {0/1}, mideleg = {0s/1s}, 
    // and mie = 1s, mip.SSIP=1, change to supervisor mode
    ///////////////////////////////

    cp_trigger_ssi_mip:
    
        li a0, 4                    # use a0 as bitfield {mideleg, mstatus.SIE}
        RVTEST_GOTO_MMODE           # start in m-mode to control CSRs

        li t0, 8
        csrrc t6, mstatus, t0       # mstatus.MIE = 0

        1:
        addi a0, a0, -1             # decrement a0 specifying bitfields to test
        li t1, -1
        csrrw t6, mie, t1           # enable all interrupts
        csrrw t6, mideleg, zero     # disable delegation
        andi t0, a0, 2              # toggle mideleg using bit 1 of a0
        beqz t0, 2f
        li t1, 0x222
        csrrw t6, mideleg, t1       # mideleg STI+SEI+SSI
        
        2:
        li t1, 2
        csrrc t6, mstatus, t1
        andi t0, a0, 1              # toggle mstatus.SIE using bit 0 of a0
        beqz t0, 3f 
        csrrs t6, mstatus, t1

        3:
        li t0, 2
        csrrs t6, mip, t0           # set mip.SSIP
        nop
        RVTEST_GOTO_LOWER_MODE Smode
        nop                         # expect interupt to M if undelegated, S if delegated and mstatus.SIE
        RVTEST_GOTO_MMODE
        li t0, 2
        csrrc t6, mip, t0           # clear mip.SSIP
        bnez a0, 1b

    ///////////////////////////////
    // cp_trigger_ssi_sip
    //
    // With mstatus.MIE = 0, mstatus.SIE = {0/1}, mideleg = {0s/1s}, 
    // and mie = 1s, sip.SSIP=1, change to supervisor mode
    ///////////////////////////////
    // TODO again mb come back - traps 4 interrpts 0
    cp_trigger_ssi_sip:
    
        li a0, 4                    # use a0 as bitfield {mideleg, mstatus.SIE}
        RVTEST_GOTO_MMODE           # start in m-mode to control CSRs

        li t0, 8
        csrrc t6, mstatus, t0       # mstatus.MIE = 0

        1:
        addi a0, a0, -1             # decrement a0 specifying bitfields to test
        li t1, -1
        csrrw t6, mie, t1           # enable all interrupts
        csrrw t6, mideleg, zero     # disable delegation
        andi t0, a0, 2              # toggle mideleg using bit 1 of a0
        beqz t0, 2f
        li t1, 0x222
        csrrw t6, mideleg, t1       # mideleg STI+SEI+SSI
        
        2:
        li t1, 2
        csrrc t6, mstatus, t1
        andi t0, a0, 1              # toggle mstatus.SIE using bit 0 of a0
        beqz t0, 3f 
        csrrs t6, mstatus, t1

        3:
        RVTEST_GOTO_LOWER_MODE Smode    # expect m-mode interrupt here if mstatus.MIE=1, mideleg.SSI=1, and mstatus.SIE=0
        nop
        li t0, 2
        csrrs t6, sip, t0               # set SIP.SSIP if it exists (only if delegated)
                                        # expect nothing if undelegated, S if delegated and mstatus.SIE
        nop
        csrrc t6, sip, t0   
        RVTEST_GOTO_MMODE
        bnez a0, 1b


    ///////////////////////////////
    // cp_trigger_sei
    //
    // With mstatus.MIE = 0, mstatus.SIE = {0/1}, mideleg = {0s/1s}, 
    // and mie = 1s, use PLIC or other EIC to cause sip.SEIP to rise
    ///////////////////////////////

        li a0, 4                    # use a0 as bitfield {mideleg, mstatus.SIE}
        RVTEST_GOTO_MMODE           # start in m-mode to control CSRs

        li t0, 8
        csrrc t6, mstatus, t0       # mstatus.MIE = 0

        1:
        addi a0, a0, -1             # decrement a0 specifying bitfields to test
        li t1, -1
        csrrw t6, mie, t1           # enable all interrupts
        csrrw t6, mideleg, zero     # disable delegation
        andi t0, a0, 2              # toggle mideleg using bit 1 of a0
        beqz t0, 2f
        li t1, 0x222
        csrrw t6, mideleg, t1       # mideleg STI+SEI+SSI
        
        2:
        li t1, 2
        csrrc t6, mstatus, t1
        andi t0, a0, 1              # toggle mstatus.SIE using bit 0 of a0
        beqz t0, 3f 
        csrrs t6, mstatus, t1

        3:
        RVTEST_GOTO_LOWER_MODE Smode
        nop                         
        //jal cause_external_interrupt_S   # expect interupt to M if undelegated, S if delegated and mstatus.SIE
        RVMODEL_CAUSE_SEXT_INT
        nop
        RVTEST_GOTO_MMODE
        //jal reset_external_interrupts
        RVMODEL_CLR_SEXT_INT
        bnez a0, 1b

    ///////////////////////////////
    // cp_trigger_sei_seip
    //
    // With mstatus.MIE = 0, mstatus.SIE = {0/1}, mideleg = {0s/1s}, 
    // and mie = 1s, write mip.SEIP=1
    ///////////////////////////////

    cp_trigger_sei_seip:
    
        li a0, 4                    # use a0 as bitfield {mideleg, mstatus.SIE}
        RVTEST_GOTO_MMODE           # start in m-mode to control CSRs

        li t0, 8
        csrrc t6, mstatus, t0       # mstatus.MIE = 0

        1:
        addi a0, a0, -1             # decrement a0 specifying bitfields to test
        li t1, -1
        csrrw t6, mie, t1           # enable all interrupts
        csrrw t6, mideleg, zero     # disable delegation
        andi t0, a0, 2              # toggle mideleg using bit 1 of a0
        beqz t0, 2f
        li t1, 0x222
        csrrw t6, mideleg, t1       # mideleg STI+SEI+SSI
        
        2:
        li t1, 2
        csrrc t6, mstatus, t1
        andi t0, a0, 1              # toggle mstatus.SIE using bit 0 of a0
        beqz t0, 3f 
        csrrs t6, mstatus, t1

        3:
        li t0, 512
        csrrs t6, mip, t0  
        nop
        RVTEST_GOTO_LOWER_MODE Smode
        nop                         
        RVTEST_GOTO_MMODE
        li t0, 512
        csrrc t6, mip, t0
        bnez a0, 1b

    ///////////////////////////////
    // cp_trigger_changingtos_sti
    //
    // with mstatus.MIE=0, mstatus.SIE=0, mideleg={1s}, mie=1s, set mip.STIP, 
    // then change to supervisor mode, then write sstatus.SIE=1
    ///////////////////////////////
    // same error - 0 interrupt events

    cp_trigger_changingtos_sti:
    
        RVTEST_GOTO_MMODE
        csrrci t6, mstatus, 0b01010     # mstatus.MIE = 0, mstatus.SIE = 0
        li t1, -1
        csrrw t6, mie, t1               # enable all interrupts
        li t1, 0x222
        csrrw t6, mideleg, t1           # enable delegation of all supervisor interrupts
        li t1, 32
        csrrs t6, mip, t1               # raise stimer interrupt in M-mode, should not trigger interrupt
        RVTEST_GOTO_LOWER_MODE Smode 
        li t0, 2   
        csrrs t6, sstatus, t0           # set sstatus.SIE = 1, should not trigger interrupt
        csrrc t6, sstatus, t0           # clean up for future tests
        RVTEST_GOTO_MMODE               # return to M-mode to clear stimer interrupt pending
        li t1, 32
        csrrc t6, mip, t1


    ///////////////////////////////
    // cp_trigger_changingtos_ssi
    //
    // with mstatus.MIE=0, mstatus.SIE=0, mideleg={1s}, mie=1s, set mip.STIP,
    // then change to supervisor mode, then write sstatus.SIE=1
    ///////////////////////////////

    cp_trigger_changingtos_ssi:
    
        RVTEST_GOTO_MMODE
        csrrci t6, mstatus, 0b01010     # mstatus.MIE = 0, mstatus.SIE = 0
        li t1, -1
        csrrw t6, mie, t1               # enable all interrupts
        li t1, 0x222
        csrrw t6, mideleg, t1           # enable delegation of all supervisor interrupts
        li t0, 2
        csrrs t6, mip, t0               # raise ssoftware interrupt in M-mode, should not trigger interrupt
        RVTEST_GOTO_LOWER_MODE Smode   
        li t0, 2 
        csrrs t6, sstatus, t0           # set sstatus.SIE = 1, should not trigger interrupt
        csrrc t6, sstatus, t0           # clean up for future tests
        RVTEST_GOTO_MMODE               # return to M-mode to clear ssoftware interrupt pending
        li t0, 2
        csrrc t6, mip, t0
    

    ///////////////////////////////
    // cp_trigger_changingtos_sei
    //
    // with mstatus.MIE=0, mstatus.SIE=0, mideleg={1s}, mie=1s, set mip.STIP,
    // then change to supervisor mode, then write sstatus.SIE=1
    ///////////////////////////////

    cp_trigger_changingtos_sei:
    
        RVTEST_GOTO_MMODE
        csrrci t6, mstatus, 0b01010     # mstatus.MIE = 0, mstatus.SIE = 0
        li t1, -1
        csrrw t6, mie, t1               # enable all interrupts
        li t1, 0x222
        csrrw t6, mideleg, t1           # enable delegation of all supervisor interrupts
        li t0, 512
        csrrs t6, mip, t0               # raise sexternal interrupt in M-mode, should not trigger interrupt
        RVTEST_GOTO_LOWER_MODE Smode    
        li t0, 2
        csrrs t6, sstatus, t0           # set sstatus.SIE = 1, should not trigger interrupt
        csrrc t6, sstatus, t0           # clean up for future tests
        RVTEST_GOTO_MMODE               # return to M-mode to clear sexternal interrupt pending
        li t0, 512
        csrrc t6, mip, t0
*/

    ///////////////////////////////
    // cp_interrupts_s
    //
    // Cross of mstatus.MIE = 0, mtvec.MODE = 00, mideleg = {0s/STI+SEI+SSI},
    // 6 walking 1s in mie, 6 walking 1s in mip (2 x 6 x 6 bins)
    ///////////////////////////////

    cp_interrupts_s:

        RVTEST_GOTO_MMODE # Need to be in M-mode to set mideleg

        li t0, 8
        csrrc t6, mstatus, t0       # mstatus.MIE = 0

        li t1, 0x222
        csrrw t6, mideleg, t1       # Set mideleg to {SEI,STI,SSI}
        jal cross_interrupts_s_EP   # Try 36 combinations of enable and pending

        csrrw t6, mideleg, zero     # Set mideleg to 0s
        jal cross_interrupts_s_EP   # Try 36 combinations of enable and pending

/*
    ///////////////////////////////
    // cp_vectored_s
    //
    // Cross of stvec.MODE = 00/01, mstatus.MIE=0, mstatus.SIE=1, mie = 1s, mideleg = 1s, 
    // 6 different interrupts walking in mip, change to supervisor mode 
    ///////////////////////////////

    cp_vectored_s:

        RVTEST_GOTO_MMODE
        csrrci t6, mstatus, 0b01000 # clear mstatus.MIE
        csrrsi t6, mstatus, 0b00010 # set   mstatus.SIE
        li t0, -1                   # load all 1s for mie and mideleg
        csrrs t6, mie, t0           # enable all interrupts
        csrrs t6, mideleg, t0       # enable delegation of all interrupts

        # Try 6 interrupts with stvec.MODE = 00
        li t0, 3
        csrrc t6, stvec, t0         # stvec.MODE = 00
        jal raise_interrupts_s      # loop through the 6 interrupts

       # Try 6 interrupts with stvec.MODE = 01
        RVTEST_GOTO_MMODE
        li t0, 3
        csrrc t6, stvec, t0
        li t0, 1
        csrrs t6, stvec, t0         # stvec.MODE = 01
        jal raise_interrupts_s      # loop through the 6 interrupts

    ///////////////////////////////
    // cp_priority_mip_m
    //
    // Cross of 2^6 permutations of mip, mie=1s, mideleg = 0s.  
    // Set up with mstatus.MIE = 0, and change to supervisor,
    // then write sstatus.SIE=1
    ///////////////////////////////

    cp_priority_mip_m: # TODO: change raising mip order to match bitfield order in mip/mie
        li a0, 63           # use a0 as bitfield for {STIP, SEIP, SSIP, MTIP, MEIP, MSIP}
        RVTEST_GOTO_MMODE   # start test in M-mode to control CSRs
        
        1:
        li t0, -1                   # load all 1s for mie
        csrrw t6, mie, t0           # enable all interrupts
        csrrw t6, mideleg, zero     # disable delegation of all interrupts
        li t0, 8
        csrrc t6, mstatus, t0       # set up with mstatus.MIE = 0

        andi t0, a0, 32             
        beqz t0, 2f                 # toggle stimer int with bit 5
        li t1, 32
        csrrs t6, mip, t1

        2:
        andi t0, a0, 16        
        beqz t0, 3f                 # toggle sext int with bit 4
        li t0, 512
        csrrs t6, mip, t0

        3:
        andi t0, a0, 8      
        beqz t0, 4f                 # toggle ssw int with bit 3
        li t0, 2
        csrrs t6, mip, t0
            
        4:
        andi t0, a0, 4        
        beqz t0, 5f                 # toggle mtimer int with bit 2
        //jal cause_mtimer_interrupt_now
        RVMODEL_CAUSE_MTIMER_INT_NOW

        5:
        andi t0, a0, 2        
        beqz t0, 6f                 # toggle mext int with bit 1
        //jal cause_external_interrupt_M
        RVMODEL_CAUSE_MEXT_INT

        6:
        andi t0, a0, 1        
        beqz t0, 7f                 # toggle msw int with bit 0
        //jal cause_msoftware_interrupt
        RVMODEL_SET_MSW_INT

        7:
        RVTEST_GOTO_LOWER_MODE Smode    # move to S-mode before attempting triggers
        li t0, 2
        csrrs t6, sstatus, t0           # write sstatus.SIE, should trigger all pending interrupts
        csrrc t6, sstatus, t0
        RVTEST_GOTO_MMODE               # return to M-mode and clean up for next test
        csrrw t6, mip, zero             # clear mip.S*IP
        //jal reset_msoftware_interrupt
        RVMODEL_CLR_MSIP
        //jal reset_mtimecmp
        RVMODEL_CLR_MTIMER_INT
        //jal reset_external_interrupts
        RVMODEL_CLR_MEXT_INT
        addi a0, a0, -1
        bgez a0, 1b                     # if no interrupts attempted, move to next coverpoint

    ///////////////////////////////
    // cp_priority_mie_m
    //
    // Cross of 2^6 permutations of mie, mip=1s, mideleg = 0s.  
    // Set up with mstatus.MIE = 0, and change to supervisor,
    // then write sstatus.SIE=1
    ///////////////////////////////

    cp_priority_mie_m:
        li a0, 63           # use a0 as bitfield
        RVTEST_GOTO_MMODE   # start test in M-mode to control CSRs

        1:
        li t0, 0x222                # 1 in SEIP, STIP, and SSIP
        csrrw t6, mideleg, zero     # disable delegation of all interrupts
        li t0, 8
        csrrc t6, mstatus, t0       # set up with mstatus.MIE = 0
        csrrw t6, mip, t0           # raise mip.S*IP
        //jal cause_mtimer_interrupt_now
        //jal cause_external_interrupt_M
        //jal cause_msoftware_interrupt
        RVMODEL_CAUSE_MTIMER_INT_NOW
        RVMODEL_CAUSE_MEXT_INT
        RVMODEL_SET_MSW_INT

        andi t0, a0, 32        
        beqz t0, 2f                 # toggle ssw int with bit 5
        li t0, 2
        csrrs t6, mie, t0

        2:
        andi t0, a0, 16        
        beqz t0, 3f                 # toggle msw int with bit 4
        li t0, 8
        csrrs t6, mie, t0

        3:
        andi t0, a0, 8      
        beqz t0, 4f                 # toggle stimer int with bit 3
        li t1, 32
        csrrs t6, mie, t1
            
        4:
        andi t0, a0, 4        
        beqz t0, 5f                 # toggle mtimer int with bit 2
        li t0, 128
        csrrs t6, mie, t0

        5:
        andi t0, a0, 2        
        beqz t0, 6f                 # toggle sext int with bit 1
        li t0, 512
        csrrs t6, mie, t0

        6:
        andi t0, a0, 1        
        beqz t0, 7f
        li t0, 2048                 # toggle mext int with bit 0
        csrrs t6, mie, t0

        7:
        RVTEST_GOTO_LOWER_MODE Smode    # move to S-mode before attempting triggers
        li t0, 2
        csrrs t6, sstatus, t0           # write sstatus.SIE, should trigger all enabled interrupts
        csrrc t6, sstatus, t0
        RVTEST_GOTO_MMODE               # return to M-mode and clean up for next test
        csrrw t6, mie, zero             # reset all interrupt enables
        addi a0, a0, -1
        bgez a0, 1b                     # if no interrupts attempted, move to next coverpoint

    ///////////////////////////////
    // cp_priority_both_m
    //
    // Cross of 2^6 permutations of mie, mip=mie, mideleg = 0s.  
    // Set up with mstatus.MIE = 0, and change to supervisor,
    // then write sstatus.SIE=1
    ///////////////////////////////

    cp_priority_both_m:
        
        li a0, 63           # use a0 as bitfield
        RVTEST_GOTO_MMODE   # start test in M-mode to control CSRs

        1:
        csrrw t6, mip, zero         # start with no interrupts pending
        csrrw t6, mideleg, zero     # disable delegation for all interrupts
        li t0, 8
        csrrc t6, mstatus, t0       # set up with mstatus.MIE = 0

        andi t0, a0, 32        
        beqz t0, 2f                 # toggle ssw int with bit 5
        li t0, 2
        csrrs t6, mie, t0
        csrrs t6, mip, t0

        2:
        andi t0, a0, 16        
        beqz t0, 3f                 # toggle msw int with bit 4
        li t0, 8
        csrrs t6, mie, t0
        //jal cause_msoftware_interrupt
        RVMODEL_SET_MSW_INT

        3:
        andi t0, a0, 8      
        beqz t0, 4f                 # toggle stimer int with bit 3
        li t1, 32
        csrrs t6, mie, t1
        csrrs t6, mip, t1
            
        4:
        andi t0, a0, 4        
        beqz t0, 5f                 # toggle mtimer int with bit 2
        li t0, 128
        csrrs t6, mie, t0
        //jal cause_mtimer_interrupt_now
        RVMODEL_CAUSE_MTIMER_INT_NOW

        5:
        andi t0, a0, 2        
        beqz t0, 6f                 # toggle sext int with bit 1
        li t0, 512
        csrrs t6, mie, t0
        csrrs t6, mip, t0

        6:
        andi t0, a0, 1        
        beqz t0, 7f                 # toggle mext int with bit 0
        li t0, 8
        csrrs t6, mstatus, t0
        li t0, 2048
        csrrs t6, mie, t0
        //jal cause_external_interrupt_M
        RVMODEL_CAUSE_MEXT_INT

        7:
        RVTEST_GOTO_LOWER_MODE Smode    # move to S-mode before attempting triggers
        li t0, 2
        csrrs t6, sstatus, t0           # write sstatus.SIE, should trigger all enabled/pending interrupts
        csrrc t6, sstatus, t0
        RVTEST_GOTO_MMODE               # return to M-mode and clean up for next test
        csrrw t6, mie, zero             # clear mip and mie
        csrrw t6, mip, zero
        //jal reset_msoftware_interrupt
        //jal reset_mtimecmp
        //jal reset_external_interrupts
        RVMODEL_CLR_MSIP
        RVMODEL_CLR_MTIMER_INT
        RVMODEL_CLR_MEXT_INT
        addi a0, a0, -1
        bgez a0, 1b                     # if no interrupts attempted, move to next coverpoint

    ///////////////////////////////
    // cp_priority_mip_s
    //
    // Cross of 2^6 permutations of mip, mie=1s, mideleg = {0s/STI+SEI+SSI}.  
    // Set up with mstatus.MIE = 0, mstatus.SIE=1, and change to supervisor
    ///////////////////////////////

    cp_priority_mip_s:
        li a0, 127                  # use a0 as bitfield
        RVTEST_GOTO_MMODE           # start test in M-mode to control CSRs
        
        0:                          # priority loop
        li t0, -1                   # load all 1s for mie
        csrrw t6, mie, t0           # enable all interrupts
        csrrci t6, mstatus, 0b01000 # set up with mstatus.MIE = 0

        li t1, -1                   # clear or set all bits of mideleg
        csrrc t6, mideleg, t1       # clear mideleg
        andi t0, a0, 64             # bit 6 controls delegation
        beqz t0, 1f
        csrrs t6, mideleg, t1       # allow delegation of all interrupts

        1:                        
        andi t0, a0, 32             
        beqz t0, 2f                 # toggle meip with bit 5
        //jal cause_external_interrupt_M
        RVMODEL_CAUSE_MEXT_INT

        2:
        andi t0, a0, 16        
        beqz t0, 3f                 # toggle seip with bit 4
        li t0, 512
        csrrs t6, mip, t0

        3:
        andi t0, a0, 8      
        beqz t0, 4f                 # toggle mtip int with bit 3
        //jal cause_mtimer_interrupt_now
        RVMODEL_CAUSE_MTIMER_INT_NOW
            
        4:
        andi t0, a0, 4        
        beqz t0, 5f                 # toggle stip int with bit 2
        li t1, 32
        csrrs t6, mip, t1

        5:
        andi t0, a0, 2        
        beqz t0, 6f                 # toggle msip int with bit 1
        //jal cause_msoftware_interrupt
        RVMODEL_SET_MSW_INT

        6:
        andi t0, a0, 1        
        beqz t0, 7f                 # toggle ssip int with bit 0
        li t0, 2
        csrrs t6, mip, t0

        7:
        csrrsi t6, sstatus, 0b00010     # mstatus.SIE = 1
        RVTEST_GOTO_LOWER_MODE Smode    # move to S-mode before attempting triggers
        nop
        RVTEST_GOTO_MMODE               # return to M-mode and clean up for next test
        csrrw t6, mip, zero             # clear mip.S*IP
        //jal reset_msoftware_interrupt
        //jal reset_mtimecmp
        //jal reset_external_interrupts
        RVMODEL_CLR_MSIP
        RVMODEL_CLR_MTIMER_INT
        RVMODEL_CLR_MEXT_INT
        addi a0, a0, -1
        bgez a0, 0b                     # if no interrupts attempted, move to next coverpoint

    ///////////////////////////////
    // cp_priority_mie_s
    //
    // Cross of 2^6 permutations of mie, mip=1s, mideleg = {0s/STI+SEI+SSI}.  
    // Set up with mstatus.MIE = 0, mstatus.SIE=1, and change to supervisor
    ///////////////////////////////

    cp_priority_mie_s:
        li a0, 127                  # use a0 as bitfield
        RVTEST_GOTO_MMODE           # start test in M-mode to control CSRs
        
        0:                          # priority loop
        csrrci t6, mstatus, 0b01000 # set up with mstatus.MIE = 0
        li t0, -1                   # load all 1s
        csrrc t6, mie, t0           # turn off all interrupt enables

        csrrw t6, mip, t0           # assert all writable interrupts
        //jal cause_mtimer_interrupt_now
        //jal cause_external_interrupt_M
        //jal cause_msoftware_interrupt
        RVMODEL_CAUSE_MTIMER_INT_NOW
        RVMODEL_CAUSE_MEXT_INT
        RVMODEL_SET_MSW_INT

        li t1, -1                   # clear or set all bits of mideleg
        csrrc t6, mideleg, t1       # clear mideleg
        andi t0, a0, 64             # bit 6 controls delegation
        beqz t0, 1f
        csrrs t6, mideleg, t1       # allow delegation of all interrupts

        1:                        
        andi t0, a0, 32             
        beqz t0, 2f                 # toggle meie with bit 5
        li t0, 2048
        csrrs t6, mie, t0

        2:
        andi t0, a0, 16        
        beqz t0, 3f                 # toggle seie with bit 4
        li t0, 512
        csrrs t6, mie, t0

        3:
        andi t0, a0, 8      
        beqz t0, 4f                 # toggle mtie int with bit 3
        li t0, 128
        csrrs t6, mie, t0
            
        4:
        andi t0, a0, 4        
        beqz t0, 5f                 # toggle stie int with bit 2
        li t0, 32
        csrrs t6, mie, t0

        5:
        andi t0, a0, 2        
        beqz t0, 6f                 # toggle msie int with bit 1
        li t0, 8
        csrrs t6, mie, t0

        6:
        andi t0, a0, 1        
        beqz t0, 7f                 # toggle ssie int with bit 0
        li t0, 2
        csrrs t6, mie, t0

        7:
        csrrsi t6, sstatus, 0b00010     # mstatus.SIE = 1
        RVTEST_GOTO_LOWER_MODE Smode    # move to S-mode before attempting triggers
        nop
        RVTEST_GOTO_MMODE               # return to M-mode and clean up for next test
        csrrw t6, mip, zero             # clear mip.S*IP
        //jal reset_msoftware_interrupt
        //jal reset_mtimecmp
        //jal reset_external_interrupts
        RVMODEL_CLR_MSIP
        RVMODEL_CLR_MTIMER_INT
        RVMODEL_CLR_MEXT_INT
        addi a0, a0, -1
        bgez a0, 0b                     # if no interrupts attempted, move to next coverpoint

    ///////////////////////////////
    // cp_priority_both_s
    //
    // Cross of 2^6 permutations of mip, mie=mip, mideleg = {0s/STI+SEI+SSI}.  
    // Set up with mstatus.MIE = 0, mstatus.SIE=1, and change to supervisor
    ///////////////////////////////

    cp_priority_both_s:
        li a0, 127                  # use a0 as bitfield
        RVTEST_GOTO_MMODE           # start test in M-mode to control CSRs
        
        0:                          # priority loop
        csrrci t6, mstatus, 0b01000 # set up with mstatus.MIE = 0

        li t1, -1                   # clear or set all bits of mideleg
        csrrc t6, mideleg, t1       # clear mideleg
        andi t0, a0, 64             # bit 6 controls delegation
        beqz t0, 1f
        csrrs t6, mideleg, t1       # allow delegation of all interrupts

        1:                        
        andi t0, a0, 32             
        beqz t0, 2f                 # toggle meip with bit 5
        //jal cause_external_interrupt_M
        RVMODEL_CAUSE_MEXT_INT

        2:
        andi t0, a0, 16        
        beqz t0, 3f                 # toggle seip with bit 4
        li t0, 512
        csrrs t6, mip, t0

        3:
        andi t0, a0, 8      
        beqz t0, 4f                 # toggle mtip int with bit 3
        //jal cause_mtimer_interrupt_now
        RVMODEL_CAUSE_MTIMER_INT_NOW
            
        4:
        andi t0, a0, 4        
        beqz t0, 5f                 # toggle stip int with bit 2
        li t1, 32
        csrrs t6, mip, t1

        5:
        andi t0, a0, 2        
        beqz t0, 6f                 # toggle msip int with bit 1
        //jal cause_msoftware_interrupt
        RVMODEL_SET_MSW_INT

        6:
        andi t0, a0, 1        
        beqz t0, 7f                 # toggle ssip int with bit 0
        li t0, 2
        csrrs t6, mip, t0

        7:
        csrr t6, mip
        csrrw t6, mie, t6               # mie = mip
        csrrsi t6, sstatus, 0b00010     # mstatus.SIE = 1
        RVTEST_GOTO_LOWER_MODE Smode    # move to S-mode before attempting triggers
        nop
        RVTEST_GOTO_MMODE               # return to M-mode and clean up for next test
        csrrw t6, mip, zero             # clear mip.S*IP
        //jal reset_msoftware_interrupt
        //jal reset_mtimecmp
        //jal reset_external_interrupts
        RVMODEL_CLR_MSIP
        RVMODEL_CLR_MTIMER_INT
        RVMODEL_CLR_MEXT_INT
        addi a0, a0, -1
        bgez a0, 0b                     # if no interrupts attempted, move to next coverpoint
*/

    ///////////////////////////////
    // cp_priority_mideleg_m
    //
    // Cross of 2^3 permutations of mideleg, mip={SEI, STI, SSI}}, mie=1s.  
    // Set up with mstatus.MIE = 0, mstatus.SIE = 1, and change to supervisor
    ///////////////////////////////

    cp_priority_mideleg_m:
/*
    New code should hit coverpoints but is thorwing an ImperasDV mismatch 
        li a0, 7                    # use a0 as bitfield
        RVTEST_GOTO_MMODE           # start test in M-mode to control CSRs
        
        0:                          # priority loop
        csrrci t6, mstatus, 0b01000 # set up with mstatus.MIE = 0
        csrrsi t6, mstatus, 0b00010 # mstatus.SIE = 1

        li t1, -1                   # clear or set all bits of mideleg
        csrrc t6, mideleg, t1       # clear mideleg

        1:                        
        andi t0, a0, 4             
        beqz t0, 2f                 # toggle mideleg.SEI with bit 2
        li t0, 0x200
        csrrs t6, mideleg, t0

        2:
        andi t0, a0, 2             
        beqz t0, 3f                 # toggle mideleg.STI with bit 1
        li t0, 0x020
        csrrs t6, mideleg, t0

        3:
        andi t0, a0, 1             
        beqz t0, 4f                 # toggle mideleg.SSI with bit 2
        li t0, 0x002
        csrrs t6, mideleg, t0
            
        4:
        li t0, -1                       
        csrrw t6, mie, t0               # mie = 1s
        li t0, 0x222
        csrrw t6, mip, t0               # mip = {SEI, STI, SSI}
        RVTEST_GOTO_LOWER_MODE Smode    # move to S-mode before attempting triggers
        nop
        RVTEST_GOTO_MMODE               # return to M-mode and clean up for next test
        csrrw t6, mip, zero             # clear mip.S*IP
        addi a0, a0, -1
        bgez a0, 0b                     # if no interrupts attempted, move to next coverpoint

*/   

/* These aren't getting coverage, and also are leaving mip bits set

        li a0, 7            # use a0 as bitfield for mideleg.{SEI, STI, SSI}
        RVTEST_GOTO_MMODE   # start test in M-mode to control CSRs

        1:
        li t0, -1                       # load all 1s for mie
        li t0, 8
        csrrc t6, mstatus, t0           # mstatus.MIE = 0
        csrrw t6, mie, t0               # mie = 1s
        li t0, 0x222                    # 1 in SEIP, STIP, SSIP
        csrrw t6, mip, t0               # mip.S*IP = 1
        //jal cause_mtimer_interrupt_now
        //jal cause_external_interrupt_M
        //jal cause_msoftware_interrupt
        RVMODEL_CAUSE_MTIMER_INT_NOW
        RVMODEL_CAUSE_MEXT_INT
        RVMODEL_SET_MSW_INT

        andi t0, a0, 4        
        beqz t0, 2f                     # toggle sext int with bit 2
        li t1, 512
        csrrs t6, mideleg, t1

        2:
        andi t0, a0, 2        
        beqz t0, 3f                     # toggle stimer int with bit 1
        li t1, 32
        csrrs t6, mideleg, t1

        3:
        andi t0, a0, 1      
        beqz t0, 4f                     # toggle ssw int with bit 0
        li t0, 2
        csrrs t6, mideleg, t0
            
        4:
        RVTEST_GOTO_LOWER_MODE Smode    # move to S-mode before attempting triggers
        li t0, 2
        csrrs t6, sstatus, t0           # write sstatus.SIE, should trigger all enabled/pending interrupts
        csrrc t6, sstatus, t0
        RVTEST_GOTO_MMODE               # return to M-mode and clean up for next test
        csrrw t6, mideleg, zero         # reset mideleg
        addi a0, a0, -1
        bgez a0, 1b                     # if no interrupts attempted, move to next coverpoint

    ///////////////////////////////
    // cp_priority_mideleg_s
    //
    // Cross of 2^3 permutations of mideleg, mie=mideleg, mip=1s.  
    // Set up with mstatus.MIE = 0, and change to supervisor,
    // then write sstatus.SIE=1
    ///////////////////////////////

    cp_priority_mideleg_s:
        li a0, 7            # use a0 as bitfield for mideleg/mie.{SEI, STI, SSI}
        RVTEST_GOTO_MMODE   # start test in M-mode to control CSRs

        1:
        li t0, 0x222                    # 1 in SEIP, STIP, SSIP
        li t0, 8
        csrrc t6, mstatus, t0           # mstatus.MIE = 0
        csrrw t6, mip, t0               # raise mip.S*IP
        //jal cause_mtimer_interrupt_now
        //jal cause_external_interrupt_M
        //jal cause_msoftware_interrupt
        RVMODEL_CAUSE_MTIMER_INT_NOW
        RVMODEL_CAUSE_MEXT_INT
        RVMODEL_SET_MSW_INT

        andi t0, a0, 4        
        beqz t0, 2f                     # toggle sext int with bit 2
        li t1, 512
        csrrs t6, mideleg, t1
        csrrs t6, mie, t1

        2:
        andi t0, a0, 2        
        beqz t0, 3f                     # toggle stimer int with bit 1
        li t1, 32
        csrrs t6, mideleg, t1
        csrrs t6, mie, t1

        3:
        andi t0, a0, 1      
        beqz t0, 4f                     # toggle ssw int with bit 0
        li t0, 2
        csrrs t6, mideleg, t0
        csrrs t6, mie, t0

        4:
        RVTEST_GOTO_LOWER_MODE Smode    # move to S-mode before attempting triggers
        li t0, 2
        csrrs t6, sstatus, t0           # write sstatus.SIE, should trigger all enabled/pending interrupts
        csrrc t6, sstatus, t0
        RVTEST_GOTO_MMODE               # return to M-mode and clean up for next test
        csrrw t6, mie, zero             # reset mie
        csrrw t6, mideleg, zero         # reset mideleg
        addi a0, a0, -1
        bgez a0, 1b                     # if no interrupts attempted, move to next coverpoint
*/

    // TODO: this is where i was, commenting it out
    ///////////////////////////////
    // cp_wfi_s
    //
    // Cross Product of mstatus.MIE = {0/1}
    // Cross Product of mstatus.SIE = {0/1}
    // Cross product of mideleg = 0s/1s
    // Cross product of mstatus.TW = {0/1}
    // mie.MTIE = 1
    // Set MTIMECMP = TIME + 0x100 to interrupt in the future
    // WFI Instruction
    ///////////////////////////////

    # cp_wfi_s:
    
    #     li a0, 15                       # use a0 as bitfield
    #     RVTEST_GOTO_MMODE               # start test in M-mode to control CSRs

    #     1:
    #     li t1, 8
    #     csrrc t6, mstatus, t1
    #     andi t0, a0, 8
    #     beqz t0, 2f                     # use bit 3 to toggle mstatus.MIE
    #     csrrs t6, mstatus, t1
        
    #     2:
    #     li t1, 2
    #     csrrc t6, mstatus, t1
    #     andi t0, a0, 4
    #     beqz t0, 3f                     # use bit 2 to toggle mstatus.SIE
    #     csrrs t6, mstatus, t1
        
    #     3:
    #     li t1, -1
    #     csrrc t6, mideleg, t1
    #     andi t0, a0, 2
    #     beqz t0, 4f                     # use bit 1 to toggle mideleg = 0s/1s
    #     csrrs t6, mideleg, t1

    #     4:
    #     li t1, 1
    #     slli t1, t1, 21
    #     csrrc t6, mstatus, t1
    #     andi t0, a0, 1
    #     beqz t0, 5f                     # use bit 0 to toggle mstatus.TW
    #     csrrs t6, mstatus, t1

    #     5:
    #     li t0, 128
    #     csrrw t6, mie, t0               # enable machine timer interrupts
    #     //jal cause_mtimer_interrupt_soon # set up mtimecmp to interrupt in 256 cycles
    #     RVMODEL_CAUSE_MTIMER_INT_SOON
    #     RVTEST_GOTO_LOWER_MODE Smode    # enter supervisor mode
    #     nop
    #     wfi                             # wait for interrupt
    #     nop
    #     RVTEST_GOTO_MMODE               # return to M-mode and clean up for next test
    #     addi a0, a0, -1                 # decrement bitfield counter
    #     bgez a0, 1b                     # loop back to next case

    // TODO: I am also commenting this out
    ///////////////////////////////
    // cp_wfi_timeout_s
    //
    // Cross Product of mstatus.MIE = {0/1}
    // Cross Product of mstatus.SIE = {0/1}
    // Cross product of mideleg = 0s/1s
    // Cross product of mstatus.TW = 1
    // mie.MTIE = {0/1}
    // Set MTIMECMP = MAX so timeout occurs
    // mode = cross product of {user, supervisor}
    // WFI Instruction
    ///////////////////////////////

    # cp_wfi_timeout_s:
    
    #     li a0, 16           # use a0 as bitfield
    #     li a1, 3            # use a3 as index variable for priv mode
    #     RVTEST_GOTO_MMODE   # start test in M-mode to control CSRs

    #     1:
    #     addi a0, a0, -1
    #     li t0, 8
    #     csrrc t6, mstatus, t0
    #     andi t0, a0, 8
    #     beqz t0, 2f                         # use bit 3 to toggle mstatus.MIE
    #     li t0, 8
    #     csrrs t6, mstatus, t0
        
    #     2:
    #     li t0, 2
    #     csrrc t6, mstatus, t0
    #     andi t0, a0, 4
    #     beqz t0, 3f                         # use bit 2 to toggle mstatus.SIE
    #     li t0, 2
    #     csrrs t6, mstatus, t0
        
    #     3:
    #     li t1, -1
    #     csrrc t6, mideleg, t1
    #     andi t0, a0, 2
    #     beqz t0, 4f                         # use bit 1 to toggle mideleg = 0s/1s
    #     csrrs t6, mideleg, t1

    #     4:
    #     li t1, 128
    #     csrrc t6, mie, t1
    #     andi t0, a0, 1
    #     beqz t0, 5f                         # use bit 0 to toggle mie.MTIE
    #     csrrs t6, mie, t1

    #     5:
    #     li t1, 1
    #     slli t1, t1, 21
    #     csrrc t6, mstatus, t1               # always use mstatus.TW = 1
    #     //jal reset_mtimecmp                  # set mtimecmp = MAX so timer interrupt will never trigger
    #     RVMODEL_CLR_MTIMER_INT

    #     RVTEST_GOTO_LOWER_MODE Smode        # run wfi in S-mode by default
    #     addi a1, a1, -1
    #     li t0, 1
    #     bne a1, t0, 6f                      # if a1 = 1, run in U-mode instead
    #     RVTEST_GOTO_LOWER_MODE Umode

    #     6:
    #     wfi                 # wfi instruction, expect timeout trap
    #     RVTEST_GOTO_MMODE   # go back to M-mode after test cases to allow access to CSRs
    #     bnez a0, 1b         # loop to next case

    j test_end

    ///////////////////////////////
    // helper functions
    ///////////////////////////////

    //#include "trickbox.S"

    cross_interrupts_s_EP:
        // helper function for crossing mie.MEIE/SEIE/M/STIE/M/SSIE with mip.M/SEIP/MTIP/MSIP in Interrupts tests (enables and pending)
        li s0, 5                # iterate through setting mie.MEIE (5), SEIE (4), MTIE (3), STIE (2), MSIE (1), or SSIE (0)

        addi sp, sp, -8         # save ra before next function call
        SREG ra, 0(sp)

        for_mie_s:
        
            slli t3, s0, 1      # setting mie.M/SEIE, M/STIE, or M/SSIE based on s0 value
            li t4, 2
            sll t4, t4, t3      # put a 1 in bit (1+(2*s0))
            csrrw t6, mie, t4   # set enable for interrupt type of interest, clear all others
        
            jal raise_interrupts_s
        
            addi s0, s0, -1     
            bge s0, zero, for_mie_s # iterate through interrupt types to be enabled

        
        LREG ra, 0(sp)              # restore ra
        addi sp, sp, 8

        ret

    raise_interrupts_s:
        // raises each of mip.M/SEIP/M/SSIP/M/STIP once in sequence

        addi sp, sp, -16     # store return address to stack
        csrr t6, mie         # save mie on stack because trap handler may reset it
        SREG t6, 8(sp)
        SREG ra, 0(sp)

        li s2, 5            # RVTEST_GOTO_LOWER_MODE macro wipes s1 so use s2 instead

        for_mip_s:
            
            # based on s2 value, set mip.MEIP (5), SEIP (4), MTIP (3), STIP (2), MSIP (1), or SSIP (0)
            # includes clearing mip in case interrupt is not triggered
            # To trigger interrupts in S-mode, raise mstatus.SIE and switch to S-mode 

            for_mip_s_meip:
                li t3, 5
                bne s2, t3, for_mip_s_seip      # if s2 == 5, trigger mexternal interrupt
                //jal cause_external_interrupt_M  # set mip.MEIP
                RVMODEL_CAUSE_MEXT_INT
                li t0, 2
                csrs mstatus, t0                # set mstatus.SIE
                RVTEST_GOTO_LOWER_MODE Smode    # t6 is preserved by mode changes, expect interrupt here
                nop
                RVTEST_GOTO_MMODE
                li t0, 2
                csrc mstatus, t0                # clear mstatus.SIE
                //jal reset_external_interrupts
                RVMODEL_CLR_MEXT_INT

            for_mip_s_seip:
                li t3, 4
                bne s2, t3, for_mip_s_mtip      # if s2 == 4, trigger sexternal interrupt
                li t0, 512
                csrs mip, t0                    # set mip.SEIP
                li t0, 2
                csrs mstatus, t0                # set mstatus.SIE
                RVTEST_GOTO_LOWER_MODE Smode    # t6 is preserved by mode changes, expect interrupt here
                nop
                RVTEST_GOTO_MMODE
                li t0, 2
                csrc mstatus, t0                # clear mstatus.SIE
                li t0, 512
                csrrc t6, mip, t0
            
            for_mip_s_mtip:
                li t3, 3
                bne s2, t3, for_mip_s_stip      # if s2 == 3, trigger mtimer interrupt
                //jal cause_mtimer_interrupt_now  # set mip.MTIP
                RVMODEL_CAUSE_MTIMER_INT_NOW
                li t0, 2
                csrs mstatus, t0                # set mstatus.SIE
                RVTEST_GOTO_LOWER_MODE Smode    # t6 is preserved by mode changes, expect interrupt here
                nop
                RVTEST_GOTO_MMODE
                li t0, 2
                csrc mstatus, t0                # clear mstatus.SIE
                //jal reset_mtimecmp
                RVMODEL_CLR_MTIMER_INT

            for_mip_s_stip:
                li t3, 2
                bne s2, t3, for_mip_s_msip      # if s2 == 2, trigger stimer interrupt
                li t1, 32
                csrs mip, t1                    # set mip.STIP
                li t0, 2
                csrs mstatus, t0                # set mstatus.SIE
                RVTEST_GOTO_LOWER_MODE Smode    # t6 is preserved by mode changes, expect interrupt here
                nop
                RVTEST_GOTO_MMODE
                li t0, 2
                csrc mstatus, t0                # clear mstatus.SIE
                li t1, 32
                csrrc t6, mip, t1

            for_mip_s_msip:
                li t3, 1
                bne s2, t3, for_mip_s_ssip      # if s2 = 1, trigger msoftware interrupt
                //jal cause_msoftware_interrupt   # set mip.MSIP
                RVMODEL_SET_MSW_INT
                li t0, 2
                csrs mstatus, t0                # set mstatus.SIE
                RVTEST_GOTO_LOWER_MODE Smode    # t6 is preserved by mode changes, expect interrupt here
                nop
                RVTEST_GOTO_MMODE
                li t0, 2
                csrc mstatus, t0                # clear mstatus.SIE
                //jal reset_msoftware_interrupt
                RVMODEL_CLR_MSIP

            for_mip_s_ssip:
                li t3, 0
                bne s2, t3, for_mip_s_end      # if s2 = 0, trigger ssoftware interrupt
                li t0, 2
                csrs mip, t0                    # set mip.SSIP
                csrs mstatus, t0                # set mstatus.SIE
                RVTEST_GOTO_LOWER_MODE Smode    # t6 is preserved by mode changes, expect interrupt here
                nop
                RVTEST_GOTO_MMODE
                li t0, 2
                csrc mstatus, t0                # clear mstatus.SIE
                li t0, 2
                csrrc t6, mip, t0
            
            for_mip_s_end:
                LREG t6, 8(sp)                  # restore mie value for next test
                csrw mie, t6                    # restore mie value for next test
                addi s2, s2, -1                 # decrement loop counter
                bgez s2, for_mip_s

        LREG ra, 0(sp)      # restore return address from stack
        addi sp, sp, 16

        ret



    test_end:
        li a0, 4            # argument to finish program
        ecall               # system call to finish program

    # RVMODEL_IO_WRITE_STR(x30, "# Test part A - test InterruptsS\n");

    # RVMODEL_IO_WRITE_STR(x30, "# Test End\n")


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