/* // These tests are for the exceptions in S mode
//    Link for google sheet https://docs.google.com/spreadsheets/d/1DgGykqadQtCyoczNUWkySfBb_CxZE5UGZXaQB8Q_NVU/edit?usp=sharing
//
//    Developed by: Maria Rehman
//
//    These below tests are written for the S mode and they covers the environment call exception, 
//    illegal instruction exception and address misaligned exception for the scenerios stated in google sheet mentioned above
// */

#include "model_test.h"

#include "arch_test.h"

// RVTEST_ISA("RV32I_Zicsr,RV32IFD_Zicsr,RV32EF_Zicsr,RV32EFD_Zicsr")
RVTEST_ISA("RV32IF_Zicsr,RV32IFD_Zicsr,RV64IF_Zicsr,RV64IFD_Zicsr,RV32EF_Zicsr,RV32EFD_Zicsr,RV64EF_Zicsr,RV64EFD_Zicsr")

# Test code region
.section .text.init
.globl rvtest_entry_point
rvtest_entry_point:
RVMODEL_BOOT
RVTEST_CODE_BEGIN

#ifdef TEST_CASE_1
    RVTEST_CASE(1,"//check ISA:=regex(.*32.*); check ISA:=regex(.*I.*Zicsr.*); def rvtest_mtrap_routine=True; def rvtest_strap_routine=True; def TEST_CASE_1=True ", cp_S_ecall,cp_S_excp_illegal, cp_S_load_addr_misaligned, cp_S_store_addr_misaligned) 

RVTEST_SIGBASE( x13,signature_x13_1)

main:
#ifdef rvtest_mtrap_routine	// Verification of existance of rvtest_mtrap_routine
	LI (a4, 0xceed)
	RVTEST_SIGUPD(x13,a4)
#endif

#ifdef rvtest_strap_routine	// Verification of existance of rvtest_mtrap_routine
	LI (a4, 0xbeed)
	RVTEST_SIGUPD(x13,a4)
#endif

	ALL_MEM_PMP          		  // set the PMP permissions for the whole memory
	csrw satp, zero  		  // write satp with all zeros (bare mode)
	
	
	RVTEST_GOTO_LOWER_MODE Smode      // goto S mode 
	nop
	nop

// In S- mode execute the ecall instruction,  MXLEN-1 bit of mcause will become zero and the 
// the exception code will be "9" for the environment call from "S" mode, mepc register will 
// get the address of the ecall instruction and then verify by checking signatures
// If S mode is implemented then will be used

	// supervisor ecall 
	ecall
	nop
	nop
	
	LI (a4, 0x0001)  // this signature will give information that test for ecall has successfully returned from the trap handler
	RVTEST_SIGUPD(x13,a4)

// If we try to access the non existinfg CSR and the instruction is csrr  
// 0xfff in S mode so it will cause the illegal instruction and will update the mcause 
// with the exception code 2, mepc will point to the address of the illegal 
// instruction, mtval will contain the binary representation of illegal instruction

	
	LI (a4, 3)     
	csrrc t1,0xFFF,a4  // accessing non existing CSR will generate the illegal instruction exception
	nop
	nop
		
	LI (a4, 0x0002) // this signature will give information that test for accessing "non existing csr" has successfully returned from the trap handler
	RVTEST_SIGUPD(x13,a4)	
	
	
// In this access to the csr without appropriate privillage mode will cause the illegal 
// instruction mcause will have the exception code 2 like if try to access the mepc and 
// mstatus register then will cause illegal instruction

	// try to access the in appropriate csr 
	LI (t0, 0x1111)
	csrrs t1, mstatus, t0 // Read mstatus into t1 and set the bits as indicated in t0
	nop
	nop
	
	LI (a4, 0x0003) // this signature will give information that test for accessing another mode csr has successfully returned from the trap handler
	RVTEST_SIGUPD(x13,a4)

// This test will check if try to write to the read onlty register then 
// it will also cause the illegal instruction and mcasue will have exception 
// code 2 and the mepc will have the address of the illegal instruction .
// e.g storing any value in the mvendorid register which is read only.
	
	// Try to write the supervisor mode  "read only CSR" then exception in the S mode will occur
	LI (a4, 3)
	csrrw t1, 0xDC0, a4      // this will give an illegal instruction as trying to write the read only register of supervisor mode
	nop
	nop   
 
	
	LI (a4, 0x0004)   
	RVTEST_SIGUPD(x13, a4)   // this signature will give information that test for accessing "read only CSR" has successfully returned from the trap handler
	
	
	RVTEST_GOTO_MMODE    // so that we can set the value of TVM bit
	nop
	nop
		
// This test will check that If TVM bit of mstatus is set, read and write access 
// to the satp and SFENCE.VMA will raise illegal instruction exception in S-mode. 
// Check scause contains the exception code 2 of illegal instruction exception. 
// sepc register will have the virtual address of the instruction at which the trap occured
        
       	LI (t4, MSTATUS_TVM)    
	csrw mstatus, t4	// set mstatus with TVM bit
	nop
	csrr t3,mstatus
	
	RVTEST_GOTO_LOWER_MODE Smode    // goto S mode and try to write the satp and executr sfence.vma
	                                // will cause illegal instruction exception
	nop
	
	LI (a4, 2)																
	csrw satp, a4           // writing satp exceptions will occur here
	csrr t3,satp
	nop
	nop
	
	sfence.vma              // using sfence.vma but no faults occur
	nop
	
	LI (a4, 0x0005)         // this signature will give information that test for enabling tvm give exception when accessing satp and executing sfence.vma

	RVTEST_SIGUPD(x13, a4) 

	
	RVTEST_GOTO_MMODE
	nop
	nop
	
// This test will check that when M mode has delegated the illegal instruction exception to S mode, 
// and S mode executes an illegal instruction then trap is taken in S mode, So after delegation 
// we will check that wheather it is being handled by expected handler if delegation is not done 
// then trap will be handled in the M mode. When a trap occurs, stvec will hold the address of the 
// respective trap handler. This test also check whether the system returns to the correct state 
// after handling the trap. It checks the value of scause before entering the trap handler and 
// after handling the trap to ensure it shows the expected values for different exceptions. 
// Additionally, it confirms that stval contains the correct values for various exceptions.
	
	LI (a4, CSR_MEDELEG)  
	csrw medeleg, a4
	
	RVTEST_GOTO_LOWER_MODE Smode
	nop
	nop
	
	ecall               // This exception will be handled in the Supervisor mode 
	nop
	nop
	
	LI (a4, 0x0006)   
	RVTEST_SIGUPD(x13, a4)    // this signature will give information that test for trap handler delegation 
				  // for ecall has successfullty returned from trap handler
	
	
 
// This test checks that if an extension is turned off (e.g., FS bits [13 and 14] in mstatus 
// are 00), trying to access it will cause an illegal instruction error. 


 RVTEST_FP_DISABLE()  // this will set the FS bit in mstatsus to 00 means off
   // Load immediate values into integer registers
    li t0, 0x3FC00000    //  Hex representation of 1.5 in IEEE-754 single-precision
    li t1, 0x40200000    // Hex representation of 2.5 in IEEE-754 single-precision

    // Move these values into floating-point registers
    fmv.w.x f0, t0      // Move 1.5 into f0   // will give illegal instruction exception 
    nop
    nop
    
    fmv.w.x f1, t1      // Move 2.5 into f1   // will give illegal instruction exception 
    nop
    nop

    // Perform floating-point addition
    fadd.s f2, f0, f1    // f2 = f0 + f1      // will give illegal instruction exception 
    nop
    nop
    
    LI (a4, 0x0007)   
    RVTEST_SIGUPD(x13, a4)    // this signature will give information that test for FS extension off has successfullty completed
   
    
    
    /* When we try to jump to the misaligned address then instead of instruction misaligned adddress it gives the illegal instruction exception */
    
    
// This test will check that in machine mode, a load address misaligned exception will be raised 
// when we try to attempt to load data from a misaligned memory address.For this we will check 
// the log file that either it is giving the expected exception at that point and value of the 
// mcause exception code will be  "4" in U mode

	LI (a4, 0x0008) 
   	LA(x17,rvtest_data)
	lw x5,3(x17)
	nop  
    	RVTEST_SIGUPD(x13, a4)    // this signature will give information that test for loas address misaligned has successfullty returned from trap
    
       
// This test will check that in machine mode, a store address misaligned exception is raised when we try 
// to attempt to store data to a misaligned memory address. For this we will check the log file 
// that either it is giving the expected exception at that point and value of the mcause is "6" in M mode
	
	
	
	LA(x17,rvtest_data)
	sw t1,0(x17)    // will not give any exception
	sw t2,3(x17)    // will cause the exception
	nop
	nop
	
        LI (a4, 0x0009)   
    	RVTEST_SIGUPD(x13, a4)     // this signature will give information that test for store address misaligned has successfullty returned from trap
    
	
#endif
//---------------------------------------------------------------------------------------------------------------------------------
RVTEST_CODE_END
RVMODEL_HALT
RVTEST_DATA_BEGIN
.align 4
// -------------------------------------------------------------------------------------------------------------------------------
rvtest_data:
.word 0xbabecafe
.word 0xbabecafe
.word 0xbabecafe
.word 0xbabecafe

RVTEST_DATA_END                
.align 12
RVMODEL_DATA_BEGIN
rvtest_sig_begin:
sig_begin_canary:
CANARY;

// test signatures initialization
signature_x13_1:
    .fill 64*(XLEN/32),4,0xcafebeef

// trap signatures initialization
#ifdef rvtest_mtrap_routine
mtrap_sigptr:
    .fill 64*(XLEN/32),4,0xdeadbeef
#endif

#ifdef rvtest_strap_routine
strap_sigptr:
    .fill 64*(XLEN/32),4,0xdeadbeef
#endif

sig_end_canary:
CANARY;
rvtest_sig_end:
RVMODEL_DATA_END
