//
// In this access to the csrs without appropriate privillage mode will cause the 
// illegal instruction mcause will have the exception code 2 and for machine mode 
// it will be only applicable when  it will try to access the debug mode registers only.
// and for other privillege registers like S an U mode registers access will not give illegal instruction

#include "model_test.h"

#include "arch_test.h"

RVTEST_ISA("RV32I_Zicsr")

# Test code region
.section .text.init
.globl rvtest_entry_point
rvtest_entry_point:
RVMODEL_BOOT
RVTEST_CODE_BEGIN

#ifdef TEST_CASE_1
    RVTEST_CASE(1,"//check ISA:=regex(.*32.*); check ISA:=regex(.*I.*Zicsr.*); def rvtest_mtrap_routine=True; def TEST_CASE_1=True; mac SV32_MACROS", excp_2_M_inappropriate_mode)

RVTEST_SIGBASE( x13,signature_x13_1)

main:
#ifdef rvtest_mtrap_routine					                				// Verification of existance of rvtest_mtrap_routine
	LI a4, 0xceed
	RVTEST_SIGUPD(x13,a4)
#endif

 	ALL_MEM_PMP          		  // set the PMP permissions for the whole memory
	csrw satp, zero  		  // write satp with all zeros (bare mode)
	
	csrr t3, mstatus           // read mstatus value 
	RVTEST_SIGUPD(x13,t3)
	
	// Try to read the machine mode CSR no exception becaiuse the M is high privillege mode
	csrr t3, mcause           // read mstatus value 
	
	LI a4, 0xffff            // just to indicate that no exception raised
	RVTEST_SIGUPD(x13,a4)
	
	// Try to read the supervisor CSR then no exception because high privillege mode can access less privilege mode CSRs
	csrr t4,sstatus
	
	LI a4, 0xffff            // just to indicate that no exception raised
	RVTEST_SIGUPD(x13,a4)
	
	// Try to read the debug CSRs and then it will cause exception (illegal exception) 
	
	LI (t0, 0x1111)
	csrrs t1, dcsr, t0 // Read mstatus into t1 and set bit 3
	nop
	nop
	
	
	csrr t5,dcsr
	nop
	
	csrr a4, mcause
	RVTEST_SIGUPD(x13,a4)
	
	nop
	nop
	
#endif
//---------------------------------------------------------------------------------------------------------------------------------
RVTEST_CODE_END
RVMODEL_HALT
RVTEST_DATA_BEGIN
.align 22

//---------------------------------------------------------------------------------------------------------------------------------
//---------------------------------------------------------------------------------------------------------------------------------



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
