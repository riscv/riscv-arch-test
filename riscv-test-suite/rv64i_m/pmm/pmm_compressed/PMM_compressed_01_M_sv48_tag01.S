/* 
Verification Goal: Set PMM = 01 in the menvcfg and tag bits are 0x0000 with bit[47]=1,
test whether or not pointer masking with PMLEN = 16 is enabled or not in M-Mode in sv48
Description:       
If Pointer Masking is enabled, then the Effective Address will be masked accordingly, no exception will be generated,
If Pointer Masking is disabled, then the Effective Address will be invalid, exceptions will be created
due to the invalid Virtual Address,
*/

#define PMM_EXT_ENAB
#include "model_test.h"
#include "arch_test.h"

RVTEST_ISA("RV64IC_Zicsr")

# Test code region
.section .text.init
.globl rvtest_entry_point
rvtest_entry_point:
RVMODEL_BOOT
RVTEST_CODE_BEGIN
#ifdef TEST_CASE_1

    RVTEST_CASE(1,"//check ISA:=regex(.*64.*); check ISA:=regex(.*I.*C.*Zicsr.*); def rvtest_mtrap_routine=True; def rvtest_strap_routine=True; def TEST_CASE_1=True; mac PMM_MACROS",pm_compressed_M_mode_SV48_tag01)

RVTEST_SIGBASE( x13,signature_x13_1)


main:
# ------------------------ Set the PMP for all memory regions -----------------
	ALL_MEM_PMP
# ------------------------------------------------------------------------------

	csrw satp, zero								// Set satp to zero (bare mode)

# --------------------------- Define Addresses -------------------------------
	.set pa_rvtest_code_begin,  	0x8000000000039c      // 56-bit physical address of the code section
	.set pa_rvtest_data_begin,  	0x80000000003530      // 56-bit physical address of the data section
	.set pa_rvtest_sig_begin, 		0x80000000006218      // 56-bit physical address of the signature section
	.set va_rvtest_code_begin,  	0x008000000000039c    // 48-bit virtual address of the code section						
	.set va_rvtest_data_begin,  	0x0000900000000000    // 48-bit virtual address of the data section
	.set va_rvtest_sig_begin,   	0x0000900000006218    // 48-bit virtual address of the signature section
	.set  va_rvtest_vmem_begin, 	0x0000900000000000    // 48-bit virtual address of vmem

# ------------------------------------------------------------------------------

# ------------------------ Save Area Logic ------------------------------------

	/* Save virtual addresses of code and data in the S-mode save area */

	LI (t0, va_rvtest_data_begin)          // Load virtual address of data
	LA (t1, rvtest_data_begin)             // Load physical address of data
	sub t0, t0, t1                         // Calculate (VA - PA)
	addi t3, t0, sv_area_sz                // Adjust for save area size
	csrr sp, mscratch                      // Read from mscratch
	add t1, sp, t3                         // Add save area offset to stack pointer
	csrw sscratch, t1                      // Write new value to sscratch

	LI (t0, va_rvtest_code_begin)          // Load virtual address of code
	LA (t1, rvtest_code_begin)             // Load physical address of code
    sub t0, t0, t1                         // Calculate (VA - PA)
	csrr sp, mscratch                      // Read from mscratch
	LREG t1, code_bgn_off+0*sv_area_sz(sp) // Load base address of code save area
	add t2, t1, t0                         // Add offset for code
	SREG t2, code_bgn_off+1*sv_area_sz(sp) // Save adjusted code address

	LI (t0, va_rvtest_data_begin)          // Load virtual address of data
	LA (t1, rvtest_data_begin)             // Load physical address of data
	sub t0, t0, t1                         // Calculate (VA - PA)
	LREG t1, data_bgn_off+0*sv_area_sz(sp) // Load base address of data save area
	add t2, t1, t0                         // Add offset for data
	SREG t2, data_bgn_off+1*sv_area_sz(sp) // Save adjusted data address

	LI (t0, va_rvtest_sig_begin)           // Load virtual address of signature
	LA (t1, rvtest_sig_begin)              // Load physical address of signature
	sub t0, t0, t1                         // Calculate (VA - PA)
	LREG t1, sig_bgn_off+0*sv_area_sz(sp)  // Load base address of signature save area
	add t2, t1, t0                         // Add offset for signature
	SREG t2, sig_bgn_off+1*sv_area_sz(sp)  // Save adjusted signature address

	// vmem
	LI (t0, va_rvtest_vmem_begin)          // Load virtual address of vmem
	LA (t1, rvtest_data_begin)             // Load physical address of data
	sub t0, t0, t1                         // Calculate (VA - PA)
	LREG t1, vmem_bgn_off+0*sv_area_sz(sp) // Load base address of vmem save area
	add t2, t1, t0                         // Add offset for vmem
	SREG t2, vmem_bgn_off+1*sv_area_sz(sp) // Save adjusted vmem address

# --------------------- Set the Level 3 PTE for SV48 -------------------------

	// Set level 3 PTE for the code area (PA: 0x200000000000 -> VA: 0x80000000000000)
	LI (a0, pa_rvtest_code_begin)          // Load physical address of code
	LI (a1, (PTE_V | PTE_A | PTE_W | PTE_R | PTE_D | PTE_X| PTE_U)) // Set permission bits
	PTE_SETUP_RV64(a0, a1, t0, t1, va_rvtest_code_begin, LEVEL3, sv48) // Set up level 3 PTE

	// Set level 3 PTE for the data area
	LI (a0, pa_rvtest_code_begin)
	LI (a1, (PTE_V | PTE_A | PTE_W | PTE_R | PTE_D | PTE_X| PTE_U))
	PTE_SETUP_RV64(a0, a1, t0, t1, va_rvtest_data_begin, LEVEL3, sv48)

# --------------------- Set the Level 3 PTE for Signature ---------------------
	// Set level 3 PTE for the signature area
	LI (a0, pa_rvtest_code_begin)          // Load physical address of signature area
	LI (a1, (PTE_V | PTE_A | PTE_W | PTE_R | PTE_D | PTE_X| PTE_U)) // Set permission bits
	PTE_SETUP_RV64(a0, a1, t0, t1, va_rvtest_sig_begin, LEVEL3, sv48) // PTE setup

	LI (t0, va_rvtest_sig_begin)           // Load virtual address of signature
	LI (t1, pa_rvtest_sig_begin)           // Load physical address of signature
	sub t0, t0, t1                         // Calculate (VA - PA)
	add x13, x13, t0                       // Adjust signature register

# -------------------- Set SATP for Virtualization ----------------------------

	sfence.vma                             // Flush the TLB
satp_setup:
	SATP_SETUP_RV64(sv48)                  // Set SATP for SV48 mode

# -------------------- Enter and Exit M Mode ----------------------------------
	# li x8, va_rvtest_data_begin
	ENABLE_VIRT_MMODE()

# -------------------- Test PMM (Pointer Masking) without Masking --------------

vm_en:
	nop
	li x8, va_rvtest_data_begin
	nop
	sfence.vma
	c.lw x9, 0(x8)                                                            // test the load access
	nop
	nop                                             
	nop                                             
	sfence.vma
	c.sw x9, 0(x8)                                                            // test the store access
	nop
	nop                                             
	nop
	sfence.vma
	c.ld x9, 0(x8)                                                            // test the load access
	nop
	nop                                             
	nop       
	sfence.vma                                      
	c.sd x9, 0(x8)                                                            // test the store access
	nop
	nop                                             
	nop
	sfence.vma
	LI (x2, va_rvtest_data_begin)
	nop
	sfence.vma
	c.lwsp x9, 0(x2)                                                          // test the load access
	nop
	nop                                             
	nop       
	sfence.vma                                      
	c.swsp x9, 0(x2)                                                          // test the store access
	nop
	nop                                             
	nop       
	sfence.vma                                      
	c.ldsp x9, 0(x2)                                                          // test the load access
	nop
	nop                                             
	nop       
	sfence.vma                                      
	c.sdsp x9, 0(x2)                                                          // test the store access
	nop
	nop                                             
	nop                                             

# -------------------- Disable Virtualization ---------------------------------

	RVTEST_GOTO_MMODE                     // Switch back to Machine mode

# -------------------- Enable Pointer Masking (PMM) ---------------------------

	LI a3, 0x300000000
	csrs mseccfg, a3                      // Enable pointer masking with PMLEN = 16

# -------------------- Set SATP for Virtualization ----------------------------


	ENABLE_VIRT_MMODE()
	csrr t0, satp
# -------------------- Test PMM with Masking Enabled --------------------------

vm_en_with_pointer_masking:
	nop
	li x8, va_rvtest_data_begin
	nop
	sfence.vma
	c.lw x9, 0(x8)                                                            // test the load access
	nop
	nop                                             
	nop                                             
	sfence.vma
	c.sw x9, 0(x8)                                                            // test the store access
	nop
	nop                                             
	nop
	sfence.vma
	c.ld x9, 0(x8)                                                            // test the load access
	nop
	nop                                             
	nop       
	sfence.vma                                      
	c.sd x9, 0(x8)                                                            // test the store access
	nop
	nop                                             
	nop
	sfence.vma
	LI (x2, va_rvtest_data_begin)
	nop
	sfence.vma
	c.lwsp x9, 0(x2)                                                          // test the load access
	nop
	nop                                             
	nop       
	sfence.vma                                      
	c.swsp x9, 0(x2)                                                          // test the store access
	nop
	nop                                             
	nop       
	sfence.vma                                      
	c.ldsp x9, 0(x2)                                                          // test the load access
	nop
	nop                                             
	nop       
	sfence.vma                                      
	c.sdsp x9, 0(x2)                                                          // test the store access
	nop
	nop                                             
	nop                                             


# -------------------- Disable Pointer Masking (PMM) ---------------------------

	LI a3, 0x000000000
	csrw mseccfg, a3                      // Enable pointer masking with PMLEN = 16

# -------------------- Disable Virtualization ---------------------------------

	RVTEST_GOTO_MMODE                     // Switch back to Machine mode

# -------------------- Signature Update ---------------------------------------

	LI (t0, va_rvtest_sig_begin)           // Load virtual address of signature
	LA (t1, rvtest_sig_begin)              // Load physical address of signature
	sub t0, t0, t1                         // Calculate (VA - PA)
	sub x13, x13, t0                       // Update signature register
	addi x13, x13, REGWIDTH                // Adjust for register width
	nop

	LI (a4, 0x123)
	RVTEST_SIGUPD(x13, a4)                 // Verify signature after virtualization disabled

#endif

# -----------------------------------------------------------------------------

RVTEST_CODE_END
RVMODEL_HALT

RVTEST_DATA_BEGIN
.align 12
rvtest_data:
	.dword 0xdeadbeefdeadbeef
	.dword 0xdeadbeefdeadbeef
	.dword 0xdeadbeefdeadbeef
	.dword 0xdeadbeefdeadbeef
#ifdef rvtest_strap_routine
.align 12
rvtest_slvl1_pg_tbl:
        RVTEST_PTE_IDENT_MAP(0,LVLS,RVTEST_ALLPERMS)	
rvtest_slvl2_pg_tbl:
        RVTEST_PTE_IDENT_MAP(0,LVLS,RVTEST_ALLPERMS)
rvtest_slvl3_pg_tbl:
        RVTEST_PTE_IDENT_MAP(0,LVLS,RVTEST_ALLPERMS)
rvtest_slvl4_pg_tbl:
        RVTEST_PTE_IDENT_MAP(0,LVLS,RVTEST_ALLPERMS)	        
#endif
RVTEST_DATA_END
RVMODEL_DATA_BEGIN
rvtest_sig_begin:
sig_begin_canary:
CANARY;
// test signatures initialization
signature_x13_1:
    .fill 256*(XLEN/64),4,0xcafebeef

// trap signatures initialization
#ifdef rvtest_mtrap_routine
mtrap_sigptr:
    .fill 256*(XLEN/64),4,0xdeadbeef
#endif

sig_end_canary:
CANARY;
rvtest_sig_end:
RVMODEL_DATA_END