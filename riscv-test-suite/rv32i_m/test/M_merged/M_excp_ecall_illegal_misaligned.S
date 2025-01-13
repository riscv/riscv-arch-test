/* // These tests are for the exceptions in M mode
//    Link for google sheet https://docs.google.com/spreadsheets/d/1DgGykqadQtCyoczNUWkySfBb_CxZE5UGZXaQB8Q_NVU/edit?usp=sharing
//
//    Developed by: Maria Rehman
//
//    These below tests are written for the M mode and they covers the environment call exception, 
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
    RVTEST_CASE(1,"//check ISA:=regex(.*32.*); check ISA:=regex(.*I.*Zicsr.*); def rvtest_mtrap_routine=True; def TEST_CASE_1=True ",cp_M_excp_illegal, cp_M_ecall, cp_M_load_addr_misaligned, cp_M_store_addr_misaligned) 

RVTEST_SIGBASE( x13,signature_x13_1)

main:
#ifdef rvtest_mtrap_routine	// Verification of existance of rvtest_mtrap_routine
	LI (a4, 0xceed)
	RVTEST_SIGUPD(x13,a4)
#endif

// In M- mode execute the ecall instruction,  MXLEN-1 bit of mcause will become zero and the 
// the exception code will be 11(b) for the environment call from M mode, mepc register will 
// get the address of the ecall instruction verify by checking both registers values

	// machine ecall  
	ecall
	nop
	nop
	
	LI (a4, 0x0001)  // this signature will give information that test for ecall has successfully returned from the trap handler
	RVTEST_SIGUPD(x13,a4)
	

// If we try to access the non existinfg CSR and the instruction is csrw 
// 0xFFF, t1 so it will cause the illegal instruction and will update the mcause 
// with the exception code 2, mepc will point to the address of the illegal 
// instruction, mtval will contain the binary representation of illegal instruction
	
	LI (t1, 0xdead)
	csrw 0xFFF, t1      // accessing non existing CSR will generate the illegal instruction exception
	nop
	nop
		
	LI (a4, 0x0002) // this signature will give information that test for accessing "non existing csr" has successfully returned from the trap handler
	RVTEST_SIGUPD(x13,a4)	
	
	
//
// In this access to the csrs without appropriate privillage mode will cause the 
// illegal instruction mcause will have the exception code 2 and for machine mode 
// it will be only applicable when  it will try to access the debug mode registers only.
// and for other privillege registers like S an U mode registers access will not give illegal instruction

	// try to access the in appropriate csr 
	LI (t0, 0x1111)
	csrrs t1, dcsr, t0 // Read dcsr into t1 and set bit 3
	nop
	nop
	
	LI (a4, 0x0003) // this signature will give information that test for accessing another mode csr has successfully returned from the trap handler
	RVTEST_SIGUPD(x13,a4)
	
// This test will check if try to write to the read onlty register then 
// it will also cause the illegal instruction and mcasue will have exception 
// code 2 and the mepc will have the address of the illegal instruction .
// e.g storing any value in the mvendorid register which is read only.
	
	// Try to write the machine mode  "read only CSR" then exception in the M mode 
	LI (a4, 1234)
	csrrc t1, mvendorid, a4   // this will give an illegal instruction as trying to write the read only register
	nop
	nop      
	
	LI (a4, 0x0004)   
	RVTEST_SIGUPD(x13, a4)   // this signature will give information that test for accessing "read only CSR" has successfully returned from the trap handler
	
	
// THis test will check that If TVM bit of mstatus is set, read and write access to 
// the satp and SFENCE.VMA will raise illegal instruction exception in S-mode. 
// Check scause contains the exception code 2 of illegal instruction exception. 
// sepc register will have the virtual address of the instruction at which the trap occured
        
       	LI (t4, MSTATUS_TVM)    
	csrw mstatus, t4	// set mstatus with TVM bit
	nop
	csrr t3,mstatus
	
	LI (a4, 2)																
	csrw satp, a4           // writing satp  no exceptions will occur here
	csrr t3,satp
	nop
	nop
	
	sfence.vma              // using sfence.vma but no faults occur
	nop
	
	LI (a4, 0x0005)         // this signature will give information that test for enabling tvm does not effect anything in M mode

	RVTEST_SIGUPD(x13, a4) 

	
// This test will check that when there is exception in M mode then it will be handled in 
// the M mode because traps never transition from a more-privileged mode to a less-privileged mode. 
// When a trap occurs, mtvec will hold the address of the respective trap handler. 
// This test verifies whether the system returns to the correct state after handling the trap. 
// It checks the value of mcause before entering the trap handler and after handling the trap 
// to ensure it reflects the expected values for different exceptions. Additionally, 
// it confirms that mtval contains the correct values for various exceptions.
	
	LI (a4, CSR_MEDELEG)  
	csrw medeleg, a4
	
	ecall               // This exception will be handled in the machine mode 
	nop
	nop
	
	LI (a4, 0x0006)   
	RVTEST_SIGUPD(x13, a4)    // this signature will give information that test for trap handler delegation for ecall has successfullty completed
	
	
// M mode 
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
    
 /*   
// This test will check that in machine mode, a load address misaligned exception will be raised 
// when we try to attempt to load data from a misaligned memory address.For this we will check 
// the log file that either it is giving the expected exception at that point and value of the 
// mcause exception code will be  "4" in U mode
*/

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

sig_end_canary:
CANARY;
rvtest_sig_end:
RVMODEL_DATA_END
