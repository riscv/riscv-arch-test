///////////////////////////////////////////
// InterruptsU.S
//
// Written: sanarayanan@hmc.edu       17 Nov 2025
//
// Purpose: Functional coverage tests for User-mode Interrupts
//
// SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
///////////////////////////////////////////


##### START_TEST_CONFIG #####
# REQUIRED_EXTENSIONS: [I, U, Zicsr]
# MARCH: rv${XLEN}i_zicsr
# CONFIG_DEPENDENT: true
##### END_TEST_CONFIG #####



#define rvtest_mtrap_routine


#define SIGUPD_COUNT 402
#define TEST_FILE "InterruptsU.S"
#include "riscv_arch_test.h"



RVTEST_BEGIN

  ALL_MEM_PMP // set the PMP permissions for the whole memory
  csrw satp, zero // write satp with all zeros (bare mode)
   //la sp, topofstack
  la sp, scratch
  //jal reset_mtimecmp
  RVMODEL_CLR_MTIMER_INT

  csrw mideleg, zero // Ensure MTI is not delegated to S-mode


  /////////////////////////////////
  // cp_user_mti
  // Undelegated MTI Interrupt
  // Cross of mtvec.MODE={00/01}, mstatus.MIE = {0/1}, mie.MTIE = 1, set MTIMECMP
  // Interrupt should trap to M-mode, regardless of MIE.
  /////////////////////////////////




  cp_user_mti:




      li s0, 3 // -> 4 combinations
    
      for_mti_cross:
          // Clear MIE and MTVEC
          li t0, 0x00000008 // MIE=1 bits
          csrrc t6, mstatus, t0
          csrrci t6, mtvec, 3




          // 1. Set MTVEC Mode (Bit 0 of s0)
          andi t0, s0, 1 // Check bit 0
          beqz t0, skip_mtvec_vectored
          csrrsi t6, mtvec, 1 // Set MTVEC to vectored (01)
          skip_mtvec_vectored:




          // 2. Set MSTATUS.MIE (Bit 1 of s0) --> like a mask
          andi t0, s0, 2 // Check bit 1
          beqz t0, skip_mstatus_mie
          csrrsi t6, mstatus, 8 // Set MIE
          skip_mstatus_mie:




          // 4. Set mie.MTIE = 1
          li t0, 0x080 // MTIE bit
          csrrs t6, mie, t0




          RVTEST_GOTO_LOWER_MODE Umode




          // Trigger the interrupt
          RVMODEL_CAUSE_MTIMER_INT_NOW
          nop // Allow time for the trap to occur
          nop
          nop
          RVTEST_GOTO_MMODE
          nop




          // clear the interrupt
          RVMODEL_CLR_MTIMER_INT




          addi s0, s0, -1
          bgez s0, for_mti_cross // Loop until all combinations are tested




    
  /////////////////////////////////
  // cp_user_msi
  // Undelegated MSI Interrupt
  // Cross of mtvec.MODE, mstatus.MIE, mie.MSIE = 1, set CLINT.MSIP
  // Interrupt should trap to M-mode, regardless of MIE.
  /////////////////////////////////




  cp_user_msi:
      // This structure is identical to cp_user_mti, replacing the trigger and MIE bit.
      li s0, 3 // 4 combinations (mie x mtvec)
    
      for_msi_cross:
          li t0, 0x00000008
          csrrc t6, mstatus, t0
          csrrci t6, mtvec, 3




          // 1. Set MTVEC Mode (Bit 0)
          andi t0, s0, 1
          beqz t0, skip_mtvec_vectored_msi
          csrrsi t6, mtvec, 1
          skip_mtvec_vectored_msi:




          // 2. Set MSTATUS.MIE (Bit 1)
          andi t0, s0, 2
          beqz t0, skip_mstatus_mie_msi
          csrrsi t6, mstatus, 8
          skip_mstatus_mie_msi:




          // 4. Set mie.MSIE = 1
          li t0, 0x008 // MSIE bit
          csrrs t6, mie, t0




          // u-mode?
          RVTEST_GOTO_LOWER_MODE Umode




          // Trigger the interrupt *after* entering U-mode
          RVMODEL_SET_MSW_INT
          nop
          nop
          nop




          RVTEST_GOTO_MMODE
          nop




          RVMODEL_CLR_MSIP




          // Clean up: M-mode trap handler must clear the interrupt and then return.
        
          addi s0, s0, -1
          bgez s0, for_msi_cross




    
  /////////////////////////////////
  // cp_user_mei
  // Undelegated MEI Interrupt
  // Cross of mtvec.MODE, mstatus.MIE, mie.MEIE = 1
  // Interrupt should trap to M-mode, regardless of MIE.
  /////////////////////////////////




  cp_user_mei:
      li s0, 3
    
      for_mei_cross:
          li t0, 0x00000008 // only bit 8 becaue of mie
          csrrc t6, mstatus, t0
          csrrci t6, mtvec, 3




          // 1. Set MTVEC Mode (Bit 0)
          andi t0, s0, 1
          beqz t0, skip_mtvec_vectored_mei
          csrrsi t6, mtvec, 1
          skip_mtvec_vectored_mei:




          // 2. Set MSTATUS.MIE (Bit 1)
          andi t0, s0, 2
          beqz t0, skip_mstatus_mie_mei
          csrrsi t6, mstatus, 8
          skip_mstatus_mie_mei:




          // 4. Set mie.MEIE = 1
          li t0, 0x800 // MEIE bit
          csrrs t6, mie, t0




          // u-mode?
          RVTEST_GOTO_LOWER_MODE Umode




          // Trigger the interrupt *after* entering U-mode
          RVMODEL_CAUSE_MEXT_INT
          nop
          nop
          nop




          RVTEST_GOTO_MMODE
          nop




          // clear interrupt
          RVMODEL_CLR_MEXT_INT
        
          addi s0, s0, -1
          bgez s0, for_mei_cross








  /////////////////////////////////
  // cp_wfi
  // Wait for Interrupt
  // Cross Product of mstatus.MIE = {0/1}, mstatus.TW = {0/1}, mie.MTIE = 1
  /////////////////////////////////




  cp_wfi:




      li s2, 3 // Iterate MIE (bit 1) and TW (bit 0). Total 4 combos.




      for_wfi:




          li t0, 0x00200008 // clear mie and tw
          csrrc t6, mstatus, t0 // Clear MIE, TW




          // Set MIE (Bit 1 of s2)
          andi t0, s2, 2
          beqz t0, case_TW_wfi
          csrrsi t6, mstatus, 8




      case_TW_wfi:
          // Set TW (Bit 0 of s2)
          andi t0, s2, 1
          beqz t0, case_end_wfi
          li t0, 0x200000 // TW bit
          csrrs t6, mstatus, t0




      case_end_wfi:      
          // 1. Set mie.MTIE = 1
          li t0, 0x080
          csrrw t6, mie, t0




          // 2. Set MTIMECMP to interrupt soon
          RVMODEL_CAUSE_MTIMER_INT_SOON




          // u mode execution
          RVTEST_GOTO_LOWER_MODE Umode




          nop
          wfi
          nop




          RVTEST_GOTO_MMODE
        
          // trap handler should interrupt + return back to the instruction WFI.
          // if TW=1 and MIE=0/1, it shld still trap on pending interrupt




          // Clean up
          RVMODEL_CLR_MTIMER_INT




          addi s2, s2, -1
          bge s2, zero, for_wfi




  /////////////////////////////////
  // cp_wfi_timeout
  // Wait for Interrupt times out
  // Cross Product of mstatus.MIE = {0/1}, mstatus.TW = 1, mie.MTIE = {0/1}
  // Set MTIMECMP = max so timeout occurs. WFI should trap to M-mode (Illegal Instruction).
  /////////////////////////////////




  cp_wfi_timeout:




      li s2, 3 // Iterate MIE (bit 1) and MTIE (bit 0). TW is fixed at 1.




      // Force TW=1 for the whole test block
      li t0, 0x200000 // TW bit
      csrrs t6, mstatus, t0




      for_wfi_timeout:




          li t0, 0x00000008
          csrrc t6, mstatus, t0 // Clear MIE




          // Set MIE (Bit 1 of s2)
          andi t0, s2, 2
          beqz t0, case_MTIE_timeout
          csrrsi t6, mstatus, 8




      case_MTIE_timeout:
          // Set mie.MTIE (Bit 0 of s2)
          andi t0, s2, 1
          li t1, 0x080
          beqz t0, case_end_timeout // Clear MTIE if bit is 0
          csrrs t6, mie, t1 // Set MTIE if bit is 1
          j case_end_timeout
          csrrc t6, mie, t1 // If bit 0 is 0, MTIE must be 0




      case_end_timeout:      
          // 1. Set MTIMECMP to a max value for a timeout
          RVMODEL_CLR_MTIMER_INT




          nop
          // Execute WFI in U-mode (assuming jump to U-mode occurs here)
          RVTEST_GOTO_LOWER_MODE Umode




          nop
          wfi
          nop




          RVTEST_GOTO_MMODE
        
          // will trap to M-mode with cause=2 (illegal instruction) happen
          // due to the WFI timeout




          // Clean up
          RVMODEL_CLR_MTIMER_INT // Clear any accidental timer interrupts




          addi s2, s2, -1
          bge s2, zero, for_wfi_timeout




      j test_end




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







