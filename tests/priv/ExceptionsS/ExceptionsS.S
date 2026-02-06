///////////////////////////////////////////
// ExceptionsS.S
//
// Written: Roman De Santos rdesantos@hmc.edu 6 February 2025
//
// Purpose: Functional coverage test for Exceptions in S mode
//
// SPDX-License-Identifier: Apache-2.0
///////////////////////////////////////////


##### START_TEST_CONFIG #####
# REQUIRED_EXTENSIONS: [I, S, Zicsr, Sm]
# MARCH: rv${XLEN}i_zicsr
# CONFIG_DEPENDENT: true
##### END_TEST_CONFIG #####


.option norvc          # Do not automatically replace uncompressed instructions with compressed instructions

#include "rvtest_config.h"
#include "WALLY-init-lib.h"

main:

// Set up the trap handler
la t0, s_traphandler
csrw stvec, t0

    // Call the cp_medeleg function in the three privilege modes

    // supervisor mode test
    // covers the following coverpoints during medelg = all 0's:
    //  cp_instr_adr_misaligned_jalr
    //  cp_instr_access_fault
    //  cp_illegal_instruction
    //  cp_breakpoint
    //  cp_load_address_misaligned
    //  cp_load_access_fault
    //  cp_store_address_misaligned
    //  cp_store_access_fault
    //  cp_ecall_s
    //  cp_misaligned_priority
    // Covers the supervisor mode coverpoints from cp_stvec and cp_medeleg_msu
    // Call the cp_medeleg function
    //  a0 = 1 (supervisor mode)
    li a0, 1
    jal ra, cp_medeleg

    // Covers the user mode coverpoints from cp_stvec and cp_medeleg_msu
    // Call the cp_medeleg function
    //   a0 = 0 (user mode)
    li a0, 0
    jal ra, cp_medeleg

    // Call the cp_medeleg function
    //   a0 = 3 (machine mode)
    // Covers the machine mode coverpoints from cp_stvec and cp_medeleg_msu
    li a0, 3
    jal ra, cp_medeleg

    // Test the remaining supervisor mode coverpoints that
    // do not require different values of medeleg

    // Restore medeleg to all zeros
    // Enter machine privilege mode
    li a0, 3
    ecall

    // Write zeros to medeleg
    li a4, 0
    csrw medeleg, a4

    // Enter supervisor privilege mode
    li a0, 1
    ecall

    /////////////////////////////////
    //cp_instr_adr_misaligned_branch
    /////////////////////////////////

    li t1,1        // load a test value
    .align 2       // align the next instruction to a 4 byte boundary

    // test all six types of taken branches to a misaligned address

    beq x0, x0, .+6  // use .+6 to change PC counter to 6 bytes ahead

    // If the configuration supports compressed instruction a c.nop instruction is executed.
    // If a processor does not have the compressed extension, there will be a misaligned access exception
    .word 0x00010013 // c.nop when 2 byte accessed, addi x0, x2, 0 when 4 byte accessed

    // follow the template above for all the branches
    bne x0, t1, .+6
    .word 0x00010013

    // blt test
    blt x0, t1, .+6
    .word 0x00010013

    // bge test
    bge t1, x0, .+6
    .word 0x00010013

    // bltu test
    bltu x0, t1, .+6
    .word 0x00010013

    // bgeu test
    bgeu x0, x0, .+6
    .word 0x00010013

    /////////////////////////////////
    //cp_instr_adr_misaligned_branch_nottaken
    /////////////////////////////////

    // these branches are not taken so there should be no exception

    li t1,1        // load a test value
    .align 2       // align the next instruction to a 4 byte boundary

    beq x0, t1, .+6

    bne x0, x0, .+6

    blt t1, x0, .+6

    bge x0, t1, .+6

    bltu t1, x0, .+6

    bgeu x0, t1, .+6

    /////////////////////////////////
    //cp_instr_adr_misaligned_jal
    /////////////////////////////////
    .align 2 // Ensure jumps start aligned

    jal   x0,  .+6
    .word 0x00010013

    /////////////////////////////////
    //cp_illegal_instruction_seed
    /////////////////////////////////

    // Throws illegal instruction in machine mode
    csrrs  t1, seed, x0
    csrrc  t2, seed, x0
    csrrsi t3, seed, 0
    csrrci t4, seed, 0

    /////////////////////////////////
    //cp_illegal_instruction_csr
    /////////////////////////////////

    // Attempt to read from CSR 0x000, which is an invalid CSR address
    lui t2, 1
    csrrs t1, 0, t2
    csrrc t1, 0, t2
    csrrsi t1, 0, 1
    csrrci t1, 0, 1

    /////////////////////////////////
    //cp_xstatus_ie
    /////////////////////////////////

    // prepare masks
    li   t0, 8        // (1 << 3) bit 3 in mstatus is the MIE bit
    li   t1, 2        // (1 << 1) bit 1 in mstatus is the SIE bit

    // supervisor_mode:

    // Machine mode setup since other modes cannot modify CSRs
    li a0, 3
    ecall


    // mstatus_MIE = {0}, sstatus_SIE = {0}, medeleg_b8 = {0}
    csrc mstatus, t0
    csrc mstatus, t1
    // enter privilege mode being tested
    li a0, 1
    ecall

    // test ecall (enter machine privilege mode)
    li a0, 3
    ecall

    // mstatus_MIE = {1}, sstatus_SIE = {0}, medeleg_b8 = {0}
    csrs mstatus, t0
    csrc mstatus, t1
    // enter privilege mode being tested
    li a0, 1
    ecall

    // test ecall (enter machine privilege mode)
    li a0, 3
    ecall

    // mstatus_MIE = {0}, sstatus_SIE = {1}, medeleg_b8 = {0}
    csrc mstatus, t0
    csrs mstatus, t1
    // enter privilege mode being tested
    li a0, 1
    ecall

    // test ecall (enter machine privilege mode)
    li a0, 3
    ecall

    // mstatus_MIE = {1}, sstatus_SIE = {1}, medeleg_b8 = {0}
    csrs mstatus, t0
    csrs mstatus, t1
    // enter privilege mode being tested
    li a0, 1
    ecall

    // test ecall (enter machine privilege mode)
    li a0, 3
    ecall

    // mstatus_MIE = {0}, sstatus_SIE = {0}, medeleg_b8 = {1}
    // change medeleg bit 8 (for this and the next supervisor tests)
    li a4, 256        // (1<<8) bit 8 in medeleg is the ecallu delegation bit
    csrs medeleg, a4  // set bit 8 in medeleg

    // update mie and sie bits
    csrc mstatus, t0
    csrc mstatus, t1
    // enter privilege mode being tested
    li a0, 1
    ecall

    // test ecall (enter machine privilege mode)
    li a0, 3
    ecall

    // mstatus_MIE = {1}, sstatus_SIE = {0}, medeleg_b8 = {1}
    // update mie and sie bits
    csrs mstatus, t0
    csrc mstatus, t1
    // enter privilege mode being tested
    li a0, 1
    ecall

    // test ecall (enter machine privilege mode)
    li a0, 3
    ecall

    // mstatus_MIE = {0}, sstatus_SIE = {1}, medeleg_b8 = {1}
    // update mie and sie bits
    csrc mstatus, t0
    csrs mstatus, t1
    // enter privilege mode being tested
    li a0, 1
    ecall

    // test ecall (enter machine privilege mode)
    li a0, 3
    ecall

    // mstatus_MIE = {1}, sstatus_SIE = {1}, medeleg_b8 = {1}
    // update mie and sie bits
    csrs mstatus, t0
    csrs mstatus, t1
    // enter privilege mode being tested
    li a0, 1
    ecall

    // test ecall (enter machine privilege mode)
    li a0, 3
    ecall

    // User_mode:

    // change medeleg bit 8 (for this and the next user tests)
    li a4, 256        // (1<<8) bit 8 in medeleg is the ecallu delegation bit
    csrc medeleg, a4  // clear bit 8 in medeleg

    // mstatus_MIE = {0}, sstatus_SIE = {0}, medeleg_b8 = {0}
    csrc mstatus, t0
    csrc mstatus, t1
    // enter privilege mode being tested
    li a0, 0
    ecall

    // test ecall (enter machine privilege mode)
    li a0, 3
    ecall

    // mstatus_MIE = {1}, sstatus_SIE = {0}, medeleg_b8 = {0}
    csrs mstatus, t0
    csrc mstatus, t1
    // enter privilege mode being tested
    li a0, 0
    ecall

    // test ecall (enter machine privilege mode)
    li a0, 3
    ecall

    // mstatus_MIE = {0}, sstatus_SIE = {1}, medeleg_b8 = {0}
    csrc mstatus, t0
    csrs mstatus, t1
    // enter privilege mode being tested
    li a0, 0
    ecall

    // test ecall (enter machine privilege mode)
    li a0, 3
    ecall

    // mstatus_MIE = {1}, sstatus_SIE = {1}, medeleg_b8 = {0}
    csrs mstatus, t0
    csrs mstatus, t1
    // enter privilege mode being tested
    li a0, 0
    ecall

    // test ecall (enter machine privilege mode)
    li a0, 3
    ecall

    // mstatus_MIE = {0}, sstatus_SIE = {0}, medeleg_b8 = {1}
    // change medeleg bit 8 (for the current and following test)
    li a4, 256        //  (1<<8) bit 8 in medeleg is the ecallu delegation bit
    csrs medeleg, a4  //  set bit 8 in medeleg

    // update mie and sie bits
    csrc mstatus, t0
    csrc mstatus, t1
    // enter privilege mode being tested
    li a0, 0
    ecall

    // test ecall (enter machine privilege mode)
    li a0, 3
    ecall

    // mstatus_MIE = {1}, sstatus_SIE = {0}, medeleg_b8 = {1}
    // update mie and sie bits
    csrs mstatus, t0
    csrc mstatus, t1
    // enter privilege mode being tested
    li a0, 0
    ecall

    // test ecall (enter machine privilege mode)
    li a0, 3
    ecall

    // mstatus_MIE = {0}, sstatus_SIE = {1}, medeleg_b8 = {1}
    // update mie and sie bits
    csrc mstatus, t0
    csrs mstatus, t1
    // enter privilege mode being tested
    li a0, 0
    ecall

    // test ecall (enter machine privilege mode)
    li a0, 3
    ecall

    // mstatus_MIE = {1}, sstatus_SIE = {1}, medeleg_b8 = {1}
    // update mie and sie bits
    csrs mstatus, t0
    csrs mstatus, t1
    // enter privilege mode being tested
    li a0, 0
    ecall

    // test ecall (enter machine privilege mode)
    li a0, 3
    ecall

finished:
    j done

// Supervisor Mode Trap Handler
// This may be replaced by the generic riscv-arch-test trap handler in the
// future to log trap signatures, but is adequate for lockstep testing
//
// Provides a simple trap handler that allows for privilege mode changes
// Place argument in a0 and issue ecall:
//  0: change to user mode
//  1: change to supervisor mode
//  3: change to machine mode
//  4: terminate program
//
// Notes on s_traphandler:
// When medeleg bit 8 is set (medeleg[8] = 1), user-level ecalls are delegated
// to the supervisor trap handler. However, if the user program requests a mode change
// to machine mode via ecall, the supervisor trap handler (using sret)
// cannot directly return to machine mode due to insufficient privileges.
//
// To resolve this, s_traphandler invokes an additional ecall, encoding (a0 + 5) in a0,
// which escalates the trap to the machine-level trap handler. The machine-level handler
// recognizes the (a0 + 5) signal as indicating that it should use sepc
// rather than mepc upon return. The machine-level handler then completes
// the privilege escalation and returns using mret, resuming execution in the desired privilege mode.
//
// Any other exception is delegated by skipping over the instruction by incrementing by 4 (assumes only
// uncompressed instructions are used).
s_traphandler:
    # Load trap handler stack pointer tp
    csrrw tp, sscratch, tp  // swap SSCRATCH and tp
    SREG t0, 0(tp)          // Save t0, t1, and ra on the stack
    SREG t1, -8(tp)
    SREG s7, -16(tp)

    csrr   s7, sepc         // Load faulting instruction address from sepc

    // Check if the exception was caused by an access fault
    csrr   t1, scause            // t1 = exception cause
    li t0, 1                     // Exception cause code 1 means Instruction Access Fault
    bne    t1, t0, IAF_skip      // If not an IAF, skip ra load
    // If it was an instruction access fault our program uses a jalr to jump to the fault address.
    // A jalr sets rd = PC +4, so we need to subtract 4 from the return address to get the address
    // of the faulting instruction.
    addi  ra, ra, -4
    csrw sepc, ra           // save ra to sepc if its an IAF
IAF_skip:

    csrr t0, scause
    li t1, 8                 // is it an ecall trap?
    andi t0, t0, 0xFC        // if CAUSE = 8, 9, or 11
    bne t0, t1, s_trap_ecall_skip  // ignore other exceptions

    // Restore registers before going into machine trap handler
    LREG t0, 0(tp)          // Restore t0, t1, and s7
    LREG t1, -8(tp)
    LREG s7, -16(tp)
    csrrw tp, sscratch, tp   // Restore tp

    addi   a0, a0, 5        // Changes inputs to 5, 6, 7, or 8 (signals that it was an ecall from the s_traphandler)
    ecall                   // Trap to M-mode, where the privilege change is handled

s_trap_ecall_skip:

    csrr t1, sepc
    addi t1, t1, 4         // Add 4 to sepc kip over uncompressed instruction
    csrw sepc, t1

    // Restore t0, t1, and ra
    LREG t0, 0(tp)
    LREG t1, -8(tp)
    LREG s7, -16(tp)
    csrrw tp, sscratch, tp   // restore tp

    sret

// Function: cp_medeleg
// Tests instructions when medeleg = all 1's, all 0's, and walking 1's.
// Only includes cover points that need to be tested with different values of medeleg.
//
// a0: Sets the privilege mode to test (0 = user, 1 = supervisor, 3 = machine).

cp_medeleg:
    mv a5, ra                  // Save return address
    mv a3, a0                  // Save test mode

    //--- Test: Loop over all-zero, all-ones, and 17 walking-1 values in medeleg ---
    // Total iterations = 19 (skips iterations 9-11):
    //   Iteration  0:    medeleg = all zeros
    //   Iterations 1-18: a walking 1 in the upper 32 bits (skips reserved bits 9-11)
    //   Iteration  19:   medeleg = all ones
    li   a1, 0                // Loop counter
    li   a2, 20               // Total iterations + 1 (0's + 1's+ 17 walking ones)
    li   a4, 0                // Initialize test value to 0 (all zeros test)

cp_medeleg_loop:
    bge  a1, a2, cp_medeleg_end   // Exit loop when a1 >= 19

    // Enter machin mode
    li a0, 3
    ecall

    // write walking 1 to medeleg
    csrw medeleg, a4

    // Enter test mode (stored in a3)
    mv   a0, a3
    ecall

    /////////////////////////////////
    //cp_instr_adr_misaligned_jalr AND cp_stvec
    /////////////////////////////////

    .align 2 // Ensure jumps start aligned

    // test offset[1:0] = 00, odd multiple of 2, rs1[1:0] = 00
    auipc   t0, 0
    addi    t0, t0, 8       // 8 mod 4 = 0, so lower two bits become 00
    jalr    t1, t0, 8       // offset 8 mod = 0, so lower two bits become 00
    .word   0x00010013

    // test offset[1:0] = 00, odd multiple of 2+1, rs1[1:0] = 01
    auipc   t0, 0
    addi    t0, t0, 5       // t0 now has lower two bits 01
    jalr    t1, t0, 8       // lower bits of offset 00
    nop
    .word   0x00010013

    // test offset[1:0] = 00, odd multiple of 2, rs1[1:0] = 10
    auipc   t1, 0
    addi    t1, t1, 6       // 6 mod 4 = 2, so lower two bits become 10
    jalr    t1, t1, 8
    .word   0x00010013

    // test offset[1:0] = 00, odd multiple of 2+1, rs1[1:0] = 11
    auipc   t1, 0
    addi    t1, t1, 7       // lower two bits become 11
    jalr    t1, t1, 8       // lower bits of offset 00
    nop
    .word   0x00010013

    // test offset[1:0] = 01, odd multiple of 2, rs1[1:0] = 00
    auipc   t1, 0
    addi    t1, t1, 8      // 8 mod 4 = 0, so lower two bits become 00
    jalr    t1, t1, 5
    .word   0x00010013

    // test offset[1:0] = 01, odd multiple of 2+1, rs1[1:0] = 01
    auipc   t1, 0
    addi    t1, t1, 5      // lower two bits become 11
    jalr    t1, t1, 5
    nop
    .word   0x00010013

    // test offset[1:0] = 01, odd multiple of 2, rs1[1:0] = 10
    auipc   t1, 0
    addi    t1, t1, 6       // 6 mod 4 = 2, so lower two bits are 10
    jalr    t1, t1, 5
    .word   0x00010013

    // test offset[1:0] = 01, odd multiple of 2+1, rs1[1:0] = 11
    auipc   t1, 0
    addi    t1, t1, 7      // lower two bits are 11
    jalr    t1, t1, 5
    nop
    .word   0x00010013

    // test offset[1:0] = 10, odd multiple of 2, rs1[1:0] = 00
    auipc   t1, 0
    addi    t1, t1, 8       // 8 mod 4 = 0, so rs1[1:0] becomes 00
    jalr    t1, t1, 6
    .word   0x00010013

    // test offset[1:0] = 10, odd multiple of 2+1, rs1[1:0] = 01
    auipc   t1, 0
    addi    t1, t1, 5       // rs1[1:0] = 01
    jalr    t1, t1, 6
    nop
    .word   0x00010013

    // test offset[1:0] = 10, odd multiple of 2, rs1[1:0] = 10
    auipc   t1, 0
    addi    t1, t1, 6      // 6 mod 4 = 2, so rs1[1:0] becomes 10
    jalr    t1, t1, 6
    .word   0x00010013

    // test offset[1:0] = 10, odd multiple of 2+1, rs1[1:0] = 11
    auipc   t1, 0
    addi    t1, t1, 7      // rs1[1:0] = 11
    jalr    t1, t1, 6
    nop
    .word   0x00010013

    // test offset[1:0] = 11, odd multiple of 2, rs1[1:0] = 00
    auipc   t1, 0
    addi    t1, t1, 8      // 8 mod 4 = 0, so rs1[1:0] becomes 00
    jalr    t1, t1, 7
    .word   0x00010013

    // test offset[1:0] = 11, odd multiple of 2+1, rs1[1:0] = 01
    auipc   t1, 0
    addi    t1, t1, 5      // rs1[1:0] = 01
    jalr    t1, t1, 7
    nop
    .word   0x00010013

    // test offset[1:0] = 11, odd multiple of 2, rs1[1:0] = 10
    auipc   t1, 0
    addi    t1, t1, 6       // 6 mod 4 = 2, so rs1[1:0] becomes 10
    jalr    t1, t1, 7
    .word   0x00010013

    // test offset[1:0] = 11, odd multiple of 2+1, rs1[1:0] = 11
    auipc   t1, 0
    addi    t1, t1, 7       // rs1[1:0] = 11
    jalr    t1, t1, 7
    nop
    .word   0x00010013


    /////////////////////////////////
    //cp_instr_access_fault
    /////////////////////////////////

    li    t1, RVMODEL_ACCESS_FAULT_ADDRESS       // Load the fault address into t0
    jalr  ra, t1, 0                      // Jump to the fault address (return address must be in ra)
    nop

    /////////////////////////////////
    //cp_breakpoint
    /////////////////////////////////

    mv a0, a3 // Move stored return privilege mode to a0
    ebreak

    /////////////////////////////////
    //cp_load_address_misaligned
    /////////////////////////////////

    // Load scratch address
    la      t4, scratch

    // Initialize loop counter (offset) from 0 to 7
    li      t0, 0         // t0 = loop index (offset)
    li      t5, 8         // loop limit (offsets 0 through 7)

load_loop:
    // Compute effective address = base (t4) + current offset (t0)
    add     t1, t4, t0    // t1 = effective address with 3 LSBs = t0

    // The following five load instructions will use the same effective address.
    // Depending on the current offset, some of these accesses are misaligned
    // relative to the load's natural alignment. In such cases, the processor
    // will trigger a load misaligned exception, caught by trap_handler.

    lh      t2, 0(t1)
    lhu     t2, 0(t1)
    lw      t2, 0(t1)
    lb      t2, 0(t1)
    lbu     t2, 0(t1)

   // Attempt to load doubleword for RV64
    #ifdef __riscv_xlen
        #if __riscv_xlen == 64
            lwu     t2, 0(t1)
            ld      t2, 0(t1)
        #endif
    #endif

    // Increment loop counter and iterate if less than 8
    addi    t0, t0, 1
    blt     t0, t5, load_loop

    /////////////////////////////////
    //cp_load_access_fault
    /////////////////////////////////

    // load the illegal address into a register
    li    t0, RVMODEL_ACCESS_FAULT_ADDRESS

    lb t1, 0(t0)

    lbu t2, 0(t0)

    lh t3, 0(t0)

    lhu t4, 0(t0)

    lw t5, 0(t0)

    // RV64 load instructions
    #ifdef __riscv_xlen
        #if __riscv_xlen == 64
            lwu  t6, 0(t0)
            ld   t6, 0(t0)
        #endif
    #endif

    /////////////////////////////////
    //cp_store_address_misaligned
    /////////////////////////////////

    // load scratch data address
    la      t4, scratch

    // Initialize loop counter (offset) from 0 to 7
    li      t0, 0         // t0 = loop index (offset)
    li      t5, 8         // loop limit (we will test offsets 0 through 7)

store_loop:
    // Compute effective address = base (t4) + current offset (t0)
    add     t1, t4, t0    // t1 = effective address with 3 LSBs = t0

    // Prepare a test value to store
    li      t2, 0xDECAFCAB

    // Attempt store instructions at the misaligned effective address
    sb      t2, 0(t1)
    sh      t2, 0(t1)
    sw      t2, 0(t1)

    // RV64 store instructions
    #ifdef __riscv_xlen
        #if __riscv_xlen == 64
            sd      t2, 0(t1)
        #endif
    #endif

    // Increment loop counter and iterate if less than 8
    addi    t0, t0, 1
    blt     t0, t5, store_loop

    /////////////////////////////////
    //cp_store_access_fault
    /////////////////////////////////

    // Load the illegal address into a register
    la t0, RVMODEL_ACCESS_FAULT_ADDRESS

    // Attempt to store byte
    li t1, 0xAB
    sb t1, 0(t0)

    // Attempt to store halfword
    li t2, 0xBEAD
    sh t2, 0(t0)

    // Attempt to store word
    li t3, 0xADDEDCAB
    sw t3, 0(t0)

    #ifdef __riscv_xlen
        #if __riscv_xlen == 64

            li t4, 0xDEADBEEFDEADBEEF
            sd t4, 0(t0)
        #endif
    #endif

    /////////////////////////////////
    //cp_ecall_s
    /////////////////////////////////

    // test an ecall
    mv a0, a3 // move stored return privilege mode to a0
    ecall

    /////////////////////////////////
    //cp_illegal_instruction
    /////////////////////////////////

    // ExceptionsInstr.S tests all other illegal instructions exhaustively

    // Attempt to execute illegal instructions
    .word 0x00000000
    .word 0xFFFFFFFF

    /////////////////////////////////
    //cp_misaligned_priority
    /////////////////////////////////

    // Test misaligned priority for load instructions

    // load Instruction fault address
    la      t4, RVMODEL_ACCESS_FAULT_ADDRESS

    // Initialize loop counter (offset) from 0 to 7
    li      t0, 0         // t0 = loop index (offset)
    li      t5, 8         // loop limit (we will test offsets 0 through 7)

load_loop_priority:
    // Compute effective address = base (t4) + current offset (t0)
    add     t1, t4, t0    // t1 = effective address with 3 LSBs = t0

    // The following five load instructions will use the same base address.
    // Depending on the current offset, these accesses are misaligned and on a fault access
    // In such cases, the processor will trigger a load misaligned exception.

    lh      t2, 0(t1)
    lhu     t2, 0(t1)
    lw      t2, 0(t1)
    lb      t2, 0(t1)
    lbu     t2, 0(t1)

   // Attempt to load doubleword for RV64
    #ifdef __riscv_xlen
        #if __riscv_xlen == 64
            lwu     t2, 0(t1)
            ld      t2, 0(t1)
        #endif
    #endif

    // Increment loop counter and iterate if less than 8
    addi    t0, t0, 1
    blt     t0, t5, load_loop_priority

    // store priority misaligned test

    // Initialize loop counter (offset) from 0 to 7
    li      t0, 0         // t0 = loop index (offset)
    li      t5, 8         // loop limit (we will test offsets 0 through 7)


    // Test misaligned priority for store instructions

    // Load access fault address
    la      t4, RVMODEL_ACCESS_FAULT_ADDRESS

    // Initialize loop counter (offset) from 0 to 7
    li      t0, 0         // t0 = loop index (offset)
    li      t5, 8         // loop limit (we will test offsets 0 through 7)

store_loop_priority:
    // Compute misaligned address
    add     t1, t4, t0    // t1 = base address with 3 LSBs = t0

    // Prepare a test value to store
    li      t2, 0xDECAFCAB

    // Attempt store instructions at the misaligned effective address
    sb      t2, 0(t1)
    sh      t2, 0(t1)
    sw      t2, 0(t1)

    // Attempt to store doubleword on RV64
    #ifdef __riscv_xlen
        #if __riscv_xlen == 64
            sd      t2, 0(t1)
        #endif
    #endif

    // Increment loop counter and iterate if less than 8
    addi    t0, t0, 1
    blt     t0, t5, store_loop_priority

    // Update the medeleg value for the next iteration:
    // For iteration  0,     medeleg is all zeros
    // For iteration  1,     initialize walking 1 in medeleg
    // For iterations 2-7,   shift medeleg value left by 1
    // For iteration  8,     shift medeleg left by 4 to skip bits 9-11
    // For iterations 12-17, shift medeleg value left by 1
    // For iteration 18,     set all applicable medeleg bits to 1

    // Check if program is at iteration 0
    beq  a1, zero, update_first

    // Check if program's iteration is 9 (skip reserved medeleg bits)
    li a6, 9
    beq  a6, a1, update_9

    // At the end of walks set applicable bits to 1 (first 11 writable bits)
    li a6, 18
    beq  a6, a1, ones_update

    // For iterations after the first, shift medeleg's value left by 1
    slli a4, a4, 1
    j    update_done

    // Initialize walking 1 in medeleg after testing all zeros in medeleg
update_first:
    li a4, 1

update_done:
    addi a1, a1, 1          // Increment loop counter
    j    cp_medeleg_loop    // Loop back

//skip over bits 9 (s ecall trap), 10 (reserved), and 11 (reserved) of medeleg
update_9:
    slli a4, a4, 4
    addi a1, a1, 4
    j    cp_medeleg_loop    // Loop back

ones_update:
    // Delegating ecalls is excluded since this would make
    // it impossible to raise privilege level to machine mode.
    // All reserved Medeleg bits are excluded.
    // The LSB is excluded since it is only writable
    // when extension ZCA is enabled.
    li  a4, 0b1011000111111110
    addi a1, a1, 1
    j  cp_medeleg_loop

cp_medeleg_end:
    mv   ra, a5             // Restore return address
    ret
