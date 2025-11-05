///////////////////////////////////////////
// ZicsrV.S
//
// Written: ytai@hmc.edu 17 June 2025
//
// Purpose: Functional coverage tests for vector CSRs
//
// SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
///////////////////////////////////////////

// Define special purpose registers before including test_macros_vector.h
#define DATA_BASE x4
#define SIG_BASE x3
#define VLENB_CACHE x5
#define HELPER_GPR x6

#include "test_macros_vector.h"

RVTEST_ISA("RV32IMV_Zicsr, RV64IMV_Zicsr")

# Test code region
.section .text.init
.globl rvtest_entry_point
rvtest_entry_point:
RVMODEL_BOOT
RVTEST_CODE_BEGIN

#ifdef TEST_CASE_1
    RVTEST_CASE(1,"//check ISA:=regex(.*I.*M.*V.*Zicsr.*BLOCKED.*); def rvtest_mtrap_routine=True; def rvtest_strap_routine=True; def rvtest_dtrap_routine=True; def TEST_CASE_1=True",ZicsrV)

    
    RVTEST_V_ENABLE()
    RVTEST_SIGBASE(SIG_BASE, signature_base)

    // vector CSRs: vtype, vlenb, vl, vstart, vxrm, vxsat, vcsr

    ///////////////////////////////
    // cp_vcsrrswc
    // 
    // attempt read/write/clear on all vector CSRs
    // Signature: CSR values after execution
    ///////////////////////////////
    cp_csrrswc:
        li    x2, -1             // Create a all 1s mask

        // Testing CSR vtype: read-only, can only be updated by vset{i}vl{i}
        csrr  x1, vtype	         // Read CSR
        nop
        RVTEST_SIGUPD(x3, x1)

        csrrw x5, vtype, x2	     // Write all 1s to CSR
        nop
        RVTEST_SIGUPD(x3, x5)
        csrr  x1, vtype          // Read back after write
        nop
        RVTEST_SIGUPD(x3, x1)

        csrrs x5, vtype, x2	     // Set all CSR bits
        nop
        RVTEST_SIGUPD(x3, x5)
        csrr  x1, vtype          // Read back after set
        nop
        RVTEST_SIGUPD(x3, x1)

        csrrc x5, vtype, x2	     // Clear all CSR bits
        nop
        RVTEST_SIGUPD(x3, x5)
        csrr  x1, vtype          // Read back after clear
        nop
        RVTEST_SIGUPD(x3, x1)


        // Testing CSR vl: read-only, can only be updated by vset{i}vl{i}
        csrr  x1, vl   	         // Read CSR
        nop
        RVTEST_SIGUPD(x3, x1)

        csrrw x5, vl, x2	     // Write all 1s to CSR
        nop
        RVTEST_SIGUPD(x3, x5)
        csrr  x1, vl             // Read back after write
        nop
        RVTEST_SIGUPD(x3, x1)

        csrrs x5, vl, x2	     // Set all CSR bits
        nop
        RVTEST_SIGUPD(x3, x5)
        csrr  x1, vl             // Read back after set
        nop
        RVTEST_SIGUPD(x3, x1)

        csrrc x5, vl, x2	     // Clear all CSR bits
        nop
        RVTEST_SIGUPD(x3, x5)
        csrr  x1, vl             // Read back after clear
        nop
        RVTEST_SIGUPD(x3, x1)


        // Testing CSR vlenb: read-only
        csrr  x1, vlenb   	     // Read CSR
        nop
        RVTEST_SIGUPD(x3, x1)

        csrrw x5, vlenb, x2	     // Write all 1s to CSR
        nop
        RVTEST_SIGUPD(x3, x5)
        csrr  x1, vlenb          // Read back after write
        nop
        RVTEST_SIGUPD(x3, x1)

        csrrs x5, vlenb, x2	     // Set all CSR bits
        nop
        RVTEST_SIGUPD(x3, x5)
        csrr  x1, vlenb          // Read back after set
        nop
        RVTEST_SIGUPD(x3, x1)

        csrrc x5, vlenb, x2	     // Clear all CSR bits
        nop
        RVTEST_SIGUPD(x3, x5)
        csrr  x1, vlenb          // Read back after clear
        nop
        RVTEST_SIGUPD(x3, x1)


        // Testing CSR vstart: read-write
        csrr  x1, vstart	     // Read CSR
        nop
        RVTEST_SIGUPD(x3, x1)

        csrrw x5, vstart, x2	 // Write all 1s to CSR
        nop
        RVTEST_SIGUPD(x3, x5)
        csrr  x1, vstart         // Read back after write
        nop
        RVTEST_SIGUPD(x3, x1)

        csrrs x5, vstart, x2	 // Set all CSR bits
        nop
        RVTEST_SIGUPD(x3, x5)
        csrr  x1, vstart         // Read back after set
        nop
        RVTEST_SIGUPD(x3, x1)

        csrrc x5, vstart, x2	 // Clear all CSR bits
        nop
        RVTEST_SIGUPD(x3, x5)
        csrr  x1, vstart         // Read back after clear
        nop
        RVTEST_SIGUPD(x3, x1)
        

        // Testing CSR vxrm: read-write
        csrr  x1, vxrm   	      // Read CSR
        nop
        RVTEST_SIGUPD(x3, x1)

        csrrw x5, vxrm, x2	     // Write all 1s to CSR
        nop
        RVTEST_SIGUPD(x3, x5)
        csrr  x1, vxrm           // Read back after write
        nop
        RVTEST_SIGUPD(x3, x1)

        csrrs x5, vxrm, x2	     // Set all CSR bits
        nop
        RVTEST_SIGUPD(x3, x5)
        csrr  x1, vxrm           // Read back after set
        nop
        RVTEST_SIGUPD(x3, x1)

        csrrc x5, vxrm, x2	     // Clear all CSR bits
        nop
        RVTEST_SIGUPD(x3, x5)
        csrr  x1, vxrm           // Read back after clear
        nop
        RVTEST_SIGUPD(x3, x1)


        // Testing CSR vxsat: read-write
        csrr  x1, vxsat   	      // Read CSR
        nop
        RVTEST_SIGUPD(x3, x1)

        csrrw x5, vxsat, x2	     // Write all 1s to CSR
        nop
        RVTEST_SIGUPD(x3, x5)
        csrr  x1, vxsat          // Read back after write
        nop
        RVTEST_SIGUPD(x3, x1)

        csrrs x5, vxsat, x2	     // Set all CSR bits
        nop
        RVTEST_SIGUPD(x3, x5)
        csrr  x1, vxsat          // Read back after set
        nop
        RVTEST_SIGUPD(x3, x1)

        csrrc x5, vxsat, x2	     // Clear all CSR bits
        nop
        RVTEST_SIGUPD(x3, x5)
        csrr  x1, vxsat          // Read back after clear
        nop
        RVTEST_SIGUPD(x3, x1)
        

        // Testing CSR vcsr: read-write
        csrr  x1, vcsr   	     // Read CSR
        nop
        RVTEST_SIGUPD(x3, x1)

        csrrw x5, vcsr, x2	     // Write all 1s to CSR
        nop
        RVTEST_SIGUPD(x3, x5)
        csrr  x1, vcsr           // Read back after write
        nop
        RVTEST_SIGUPD(x3, x1)

        csrrs x5, vcsr, x2	     // Set all CSR bits
        nop
        RVTEST_SIGUPD(x3, x5)
        csrr  x1, vcsr           // Read back after set
        nop
        RVTEST_SIGUPD(x3, x1)

        csrrc x5, vcsr, x2	     // Clear all CSR bits
        nop
        RVTEST_SIGUPD(x3, x5)
        csrr  x1, vcsr           // Read back after clear
        nop
        RVTEST_SIGUPD(x3, x1)


    ///////////////////////////////
    // cp_vcsrs_walking1s
    //
    // Writing to each bit for all writable vector CSRs
    // Signature: CSR value after execution
    ///////////////////////////////
    cp_vcsrs_walking1s:
        // Writable vector CSRs: vstart, vxrm, vxsat, vcsr
        // Tests for vstart
        li       t2, 1                       // one-hot value starting from bit 0
        li       t1, -1                      // mask for all ones

        vstart_walk:
            csrrc    t6, vstart, t1          // clear all bits
            csrrw    t6, vstart, t2          // Write walking 1 to CSR
            csrr     x1, vstart
            RVTEST_SIGUPD(x3, x1)

            slli     t2, t2, 1               // Shift to the next walking 1
            beqz     t2, end_vstart_walk     // If t2 becomes 0, done
            j        vstart_walk

        end_vstart_walk:

        // Tests for vxrm
        li       t2, 1                       // one-hot value starting from bit 0
        li       t1, -1                      // mask for all ones
        csrrc    t6, vxrm, t1                // clear all bits

        vxrm_walk:
            csrrc    t6, vxrm, t1            // clear all bits
            csrrw    t6, vxrm, t2            // Write walking 1 to CSR
            csrr     x1, vxrm
            RVTEST_SIGUPD(x3, x1)

            slli     t2, t2, 1               // Shift to the next walking 1
            beqz     t2, end_vxrm_walk       // If t2 becomes 0, done
            j        vxrm_walk

        end_vxrm_walk:

        // Tests for vxsat
        li       t2, 1                       // one-hot value starting from bit 0
        li       t1, -1                      // mask for all ones
        csrrc    t6, vxsat, t1               // clear all bits

        vxsat_walk:
            csrrc    t6, vxsat, t1          // clear all bits
            csrrw    t6, vxsat, t2           // Write walking 1 to CSR
            csrr     x1, vxsat
            RVTEST_SIGUPD(x3, x1)

            slli     t2, t2, 1               // Shift to the next walking 1
            beqz     t2, end_vxsat_walk      // If t2 becomes 0, done
            j        vxsat_walk

        end_vxsat_walk:

        // Tests for vcsr
        li       t2, 1                       // one-hot value starting from bit 0
        li       t1, -1                      // mask for all ones
        csrrc    t6, vcsr, t1                // clear all bits

        vcsr_walk:
            csrrc    t6, vcsr, t1          // clear all bits
            csrrw    t6, vcsr, t2            // Write walking 1 to CSR
            csrr     x1, vcsr
            RVTEST_SIGUPD(x3, x1)

            slli     t2, t2, 1               // Shift to the next walking 1
            beqz     t2, end_vcsr_walk       // If t2 becomes 0, done
            j        vcsr_walk

        end_vcsr_walk:


    ///////////////////////////////
    // cp_mstatus_vs_set_dirty_arithmetic
    //
    // Test if mstatus.VS is set to dirty after a vector arithmetic instr
    // Signature: mstatus after executing arithmetic instr
    ///////////////////////////////
    cp_mstatus_vs_set_dirty_arithmetic:
        // Reset vtype to a legal setting
        vsetvli x1, x0, e8, m1, ta, ma
        // Set up clear mask for mstatus.VS (bits 9 and 10)
        li      t1, 0x600

        // Execute a vector arithmetic instruction when mstatus.VS is set to init
        la      a0, vector_random   // Load address of a random vector
        vl1r.v  v1, (a0)            // Load vector from address using whole register load
        li      t2, 0x200           // Set up init mask for mstatus.VS (VS = 01)
        csrc    mstatus, t1
        csrs    mstatus, t2
        vadd.vv v2, v1, v1          // Execute a random vector instruction
        csrr    x1, mstatus
        RVTEST_SIGUPD(x3, x1)

        // Execute a vector arithmetic instruction when mstatus.VS is set to clean
        la      a0, vector_random   // Load address of a random vector
        vl1r.v  v1, (a0)            // Load vector from address using whole register load
        li      t3, 0x400           //  Set up clean mask for mstatus.VS (VS = 10)
        csrc    mstatus, t1
        csrs    mstatus, t3
        vadd.vv v2, v1, v1          // Execute a random vector instruction
        csrr    x1, mstatus
        RVTEST_SIGUPD(x3, x1)


    ///////////////////////////////
    // cp_mstatus_vs_set_dirty_csr
    //
    // Test if mstatus.VS is set to dirty after a vset instr
    // Signature: mstatus after executing vset instr
    ///////////////////////////////
    cp_mstatus_vs_set_dirty_csr:
        // Set up clear mask for mstatus.VS (bits 9 and 10)
        li      t1, 0x600

        // Execute a vset instruction when mstatus.VS is set to init
        li      t2, 0x200                  // Set up init mask for mstatus.VS (VS = 01)
        csrc    mstatus, t1
        csrs    mstatus, t2
        vsetvli x1, x0, e16, m2, ta, ma   // Execute a random vset instruction
        csrr    x1, mstatus
        RVTEST_SIGUPD(x3, x1)

        // Execute a vset instruction when mstatus.VS is set to clean
        li      t3, 0x400                 //  Set up clean mask for mstatus.VS (VS = 10)
        csrc    mstatus, t1
        csrs    mstatus, t3
        vsetvli x1, x0, e16, m2, ta, ma   // Execute a random vset instruction
        csrr    x1, mstatus
        RVTEST_SIGUPD(x3, x1)

    ///////////////////////////////
    // cp_mstatus_vs_off_arithmetic
    //
    // Check whether a vector arithmetic instr is illgal with mstatus.VS off
    // Signature: illegal instruction, stored in mtrap_sig
    ///////////////////////////////
    cp_mstatus_vs_off_arithmetic:
        // Reset vtype to a legal setting
        vsetvli x1, x0, e8, m1, ta, ma

        // Set up vectors needed for arithmetic instruction
        la      a0, vector_random   // Load address of a random vector
        vl1r.v  v1, (a0)            // Load vector from address using whole register load

        // Set up desired CSR settings
        li      t1, 0x600             // Set up clear mask for mstatus.VS (bits 9 and 10)
        li      t2, 0x200000          // Set up mask for misa.V (bit 21)
        csrc    mstatus, t1           // Set mstatus.VS to off (VS = 00)
        csrs    misa, t2              // Enable misa.V

        // Execute arithmetic vector instruction
        vadd.vv v2, v1, v1          // Execute a random vector instruction
        nop


    ///////////////////////////////
    // cp_mstatus_vs_off_csr
    //
    // Check whether a vset instr is illgal with mstatus.VS off
    // Signature: illegal instruction, stored in mtrap_sig
    ///////////////////////////////
    cp_mstatus_vs_off_csr:
        // Set up desired CSR settings
        li      t1, 0x600             // Set up clear mask for mstatus.VS (bits 9 and 10)
        li      t2, 0x200000          // Set up mask for misa.V (bit 21)
        csrc    mstatus, t1           // Set mstatus.VS to off (VS = 00)
        csrs    misa, t2              // Enable misa.V

        // Execute CSR vector instruction
        vsetvli x1, x0, e8, m1, ta, ma
        nop


    ///////////////////////////////
    // cp_misa_v_clear_set
    //
    // Check whether misa.V is writable
    // Signature: misa.V after clearing and writing
    ///////////////////////////////
    cp_misa_v_clear_set:
        // Set up desired CSR settings
        li      t2, 0x200000          // Set up mask for misa.V (bit 21)
        csrc    misa, t2              // Attempt to clear misa.V
        csrr    x1, misa
        RVTEST_SIGUPD(x3, x1)
        
        csrs    misa, t2              // Attempt to write to misa.V
        csrr    x1, misa
        RVTEST_SIGUPD(x3, x1)

    
    ######################### vset{i}vl{i} ######################### 

    ///////////////////////////////
    // cp_sew_lmul_vset_i_vli
    //
    // Cross LMUL with SEW using vsetivli/vsetvli
    // Signature: vtype after execution
    ///////////////////////////////
    cp_sew_lmul_vset_i_vli:
        li       t1, 1                    // Set vl = 1 for vsetvli instr

        li       t2, 0x600                // Set up init mask for mstatus.VS (VS = 01)
        csrs     mstatus, t2              // Reset mstatus.VS to dirty to ensure that vset instr work

        ////////////////// SEW = 8 //////////////////
        // SEW = 8, LMUL = 1
        vsetvli  x8, t1, e8, m1, tu, mu
        csrr     x1, vtype
        RVTEST_SIGUPD(x3, x1)

        vsetivli x8, 1, e8, m1, tu, mu
        csrr     x1, vtype
        RVTEST_SIGUPD(x3, x1)

        // SEW = 8, LMUL = 2
        vsetvli  x8, t1, e8, m2, tu, mu
        csrr     x1, vtype
        RVTEST_SIGUPD(x3, x1)

        vsetivli x8, 1, e8, m2, tu, mu
        csrr     x1, vtype
        RVTEST_SIGUPD(x3, x1)

        // SEW = 8, LMUL = 4
        vsetvli  x8, t1, e8, m4, tu, mu
        csrr     x1, vtype
        RVTEST_SIGUPD(x3, x1)

        vsetivli x8, 1, e8, m4, tu, mu
        csrr     x1, vtype
        RVTEST_SIGUPD(x3, x1)

        // SEW = 8, LMUL = 8
        vsetvli  x8, t1, e8, m8, tu, mu
        csrr     x1, vtype
        RVTEST_SIGUPD(x3, x1)

        vsetivli x8, 1, e8, m8, tu, mu
        csrr     x1, vtype
        RVTEST_SIGUPD(x3, x1)

        // SEW = 8, LMUL = 1/2
        vsetvli  x8, t1, e8, mf2, tu, mu
        csrr     x1, vtype
        RVTEST_SIGUPD(x3, x1)

        vsetivli x8, 1, e8, mf2, tu, mu
        csrr     x1, vtype
        RVTEST_SIGUPD(x3, x1)

        // SEW = 8, LMUL = 1/4
        vsetvli  x8, t1, e8, mf4, tu, mu
        csrr     x1, vtype
        RVTEST_SIGUPD(x3, x1)

        vsetivli x8, 1, e8, mf4, tu, mu
        csrr     x1, vtype
        RVTEST_SIGUPD(x3, x1)

        // SEW = 8, LMUL = 1/8
        vsetvli  x8, t1, e8, mf8, tu, mu
        csrr     x1, vtype
        RVTEST_SIGUPD(x3, x1)

        vsetivli x8, 1, e8, mf8, tu, mu
        csrr     x1, vtype
        RVTEST_SIGUPD(x3, x1)

        ////////////////// SEW = 16 //////////////////
        // SEW = 16, LMUL = 1
        vsetvli  x8, t1, e16, m1, tu, mu
        csrr     x1, vtype
        RVTEST_SIGUPD(x3, x1)

        vsetivli x8, 1, e16, m1, tu, mu
        csrr     x1, vtype
        RVTEST_SIGUPD(x3, x1)

        // SEW = 16, LMUL = 2
        vsetvli  x8, t1, e16, m2, tu, mu
        csrr     x1, vtype
        RVTEST_SIGUPD(x3, x1)

        vsetivli x8, 1, e16, m2, tu, mu
        csrr     x1, vtype
        RVTEST_SIGUPD(x3, x1)

        // SEW = 16, LMUL = 4
        vsetvli  x8, t1, e16, m4, tu, mu
        csrr     x1, vtype
        RVTEST_SIGUPD(x3, x1)

        vsetivli x8, 1, e16, m4, tu, mu
        csrr     x1, vtype
        RVTEST_SIGUPD(x3, x1)

        // SEW = 16, LMUL = 8
        vsetvli  x8, t1, e16, m8, tu, mu
        csrr     x1, vtype
        RVTEST_SIGUPD(x3, x1)

        vsetivli x8, 1, e16, m8, tu, mu
        csrr     x1, vtype
        RVTEST_SIGUPD(x3, x1)

        // SEW = 16, LMUL = 1/2
        vsetvli  x8, t1, e16, mf2, tu, mu
        csrr     x1, vtype
        RVTEST_SIGUPD(x3, x1)

        vsetivli x8, 1, e16, mf2, tu, mu
        csrr     x1, vtype
        RVTEST_SIGUPD(x3, x1)

        // SEW = 16, LMUL = 1/4
        vsetvli  x8, t1, e16, mf4, tu, mu
        csrr     x1, vtype
        RVTEST_SIGUPD(x3, x1)

        vsetivli x8, 1, e16, mf4, tu, mu
        csrr     x1, vtype
        RVTEST_SIGUPD(x3, x1)

        // SEW = 16, LMUL = 1/8
        vsetvli  x8, t1, e16, mf8, tu, mu
        csrr     x1, vtype
        RVTEST_SIGUPD(x3, x1)

        vsetivli x8, 1, e16, mf8, tu, mu
        csrr     x1, vtype
        RVTEST_SIGUPD(x3, x1)

        ////////////////// SEW = 32 //////////////////
        // SEW = 32, LMUL = 1
        vsetvli  x8, t1, e32, m1, tu, mu
        csrr     x1, vtype
        RVTEST_SIGUPD(x3, x1)

        vsetivli x8, 1, e32, m1, tu, mu
        csrr     x1, vtype
        RVTEST_SIGUPD(x3, x1)

        // SEW = 32, LMUL = 2
        vsetvli  x8, t1, e32, m2, tu, mu
        csrr     x1, vtype
        RVTEST_SIGUPD(x3, x1)

        vsetivli x8, 1, e32, m2, tu, mu
        csrr     x1, vtype
        RVTEST_SIGUPD(x3, x1)

        // SEW = 32, LMUL = 4
        vsetvli  x8, t1, e32, m4, tu, mu
        csrr     x1, vtype
        RVTEST_SIGUPD(x3, x1)

        vsetivli x8, 1, e32, m4, tu, mu
        csrr     x1, vtype
        RVTEST_SIGUPD(x3, x1)

        // SEW = 32, LMUL = 8
        vsetvli  x8, t1, e32, m8, tu, mu
        csrr     x1, vtype
        RVTEST_SIGUPD(x3, x1)

        vsetivli x8, 1, e32, m8, tu, mu
        csrr     x1, vtype
        RVTEST_SIGUPD(x3, x1)

        // SEW = 32, LMUL = 1/2
        vsetvli  x8, t1, e32, mf2, tu, mu
        csrr     x1, vtype
        RVTEST_SIGUPD(x3, x1)

        vsetivli x8, 1, e32, mf2, tu, mu
        csrr     x1, vtype
        RVTEST_SIGUPD(x3, x1)

        // SEW = 32, LMUL = 1/4
        vsetvli  x8, t1, e32, mf4, tu, mu
        csrr     x1, vtype
        RVTEST_SIGUPD(x3, x1)

        vsetivli x8, 1, e32, mf4, tu, mu
        csrr     x1, vtype
        RVTEST_SIGUPD(x3, x1)
    
        // SEW = 32, LMUL = 1/8
        vsetvli  x8, t1, e32, mf8, tu, mu
        csrr     x1, vtype
        RVTEST_SIGUPD(x3, x1)

        vsetivli x8, 1, e32, mf8, tu, mu
        csrr     x1, vtype
        RVTEST_SIGUPD(x3, x1)

        ////////////////// SEW = 64 //////////////////
        // SEW = 64, LMUL = 1
        vsetvli  x8, t1, e64, m1, tu, mu
        csrr     x1, vtype
        RVTEST_SIGUPD(x3, x1)

        vsetivli x8, 1, e64, m1, tu, mu
        csrr     x1, vtype
        RVTEST_SIGUPD(x3, x1)

        // SEW = 64, LMUL = 2
        vsetvli  x8, t1, e64, m2, tu, mu
        csrr     x1, vtype
        RVTEST_SIGUPD(x3, x1)

        vsetivli x8, 1, e64, m2, tu, mu
        csrr     x1, vtype
        RVTEST_SIGUPD(x3, x1)

        // SEW = 64, LMUL = 4
        vsetvli  x8, t1, e64, m4, tu, mu
        csrr     x1, vtype
        RVTEST_SIGUPD(x3, x1)

        vsetivli x8, 1, e64, m4, tu, mu
        csrr     x1, vtype
        RVTEST_SIGUPD(x3, x1)

        // SEW = 64, LMUL = 8
        vsetvli  x8, t1, e64, m8, tu, mu
        csrr     x1, vtype
        RVTEST_SIGUPD(x3, x1)

        vsetivli x8, 1, e64, m8, tu, mu
        csrr     x1, vtype
        RVTEST_SIGUPD(x3, x1)

        // SEW = 64, LMUL = 1/2
        vsetvli  x8, t1, e64, mf2, tu, mu
        csrr     x1, vtype
        RVTEST_SIGUPD(x3, x1)

        vsetivli x8, 1, e64, mf2, tu, mu
        csrr     x1, vtype
        RVTEST_SIGUPD(x3, x1)

        // SEW = 64, LMUL = 1/4
        vsetvli  x8, t1, e64, mf4, tu, mu
        csrr     x1, vtype
        RVTEST_SIGUPD(x3, x1)

        vsetivli x8, 1, e64, mf4, tu, mu
        csrr     x1, vtype
        RVTEST_SIGUPD(x3, x1)

        // SEW = 64, LMUL = 1/8
        vsetvli  x8, t1, e64, mf8, tu, mu
        csrr     x1, vtype
        RVTEST_SIGUPD(x3, x1)

        vsetivli x8, 1, e64, mf8, tu, mu
        csrr     x1, vtype
        RVTEST_SIGUPD(x3, x1)


    ///////////////////////////////
    // cp_sew_lmul_vsetvl
    //
    // Cross LMUL with SEW using vsetvl
    // Signature: vtype after execution
    ///////////////////////////////
    cp_sew_lmul_vsetvl:
        li       t1, 1               // Set up for vl = 1 in vsetvl instructions
        
        // vtype[7:0] = vma_vta_vsew[2:0]_vlmul[2:0]

        // vtype[7:0] = 0_0_000_000 (SEW = 8, LMUL = 1) 
        li       t2, 0x00
        vsetvl   x8, t1, t2
        csrr     x1, vtype
        RVTEST_SIGUPD(x3, x1)

        // vtype[7:0] = 0_0_000_001 (SEW = 8, LMUL = 2) 
        li       t2, 0x01
        vsetvl   x8, t1, t2
        csrr     x1, vtype
        RVTEST_SIGUPD(x3, x1)

        // vtype[7:0] = 0_0_000_010 (SEW = 8, LMUL = 4) 
        li       t2, 0x02
        vsetvl   x8, t1, t2
        csrr     x1, vtype
        RVTEST_SIGUPD(x3, x1)

        // vtype[7:0] = 0_0_000_011 (SEW = 8, LMUL = 8) 
        li       t2, 0x03
        vsetvl   x8, t1, t2
        csrr     x1, vtype
        RVTEST_SIGUPD(x3, x1)

        // vtype[7:0] = 0_0_000_101 (SEW = 8, LMUL = 1/8) 
        li       t2, 0x05
        vsetvl   x8, t1, t2
        csrr     x1, vtype
        RVTEST_SIGUPD(x3, x1)

        // vtype[7:0] = 0_0_000_110 (SEW = 8, LMUL = 1/4) 
        li       t2, 0x06
        vsetvl   x8, t1, t2
        csrr     x1, vtype
        RVTEST_SIGUPD(x3, x1)

        // vtype[7:0] = 0_0_000_111 (SEW = 8, LMUL = 1/2) 
        li       t2, 0x07
        vsetvl   x8, t1, t2
        csrr     x1, vtype
        RVTEST_SIGUPD(x3, x1)

        // vtype[7:0] = 0_0_001_000 (SEW = 16, LMUL = 1) 
        li       t2, 0x08
        vsetvl   x8, t1, t2
        csrr     x1, vtype
        RVTEST_SIGUPD(x3, x1)

        // vtype[7:0] = 0_0_001_001 (SEW = 16, LMUL = 2) 
        li       t2, 0x09
        vsetvl   x8, t1, t2
        csrr     x1, vtype
        RVTEST_SIGUPD(x3, x1)

        // vtype[7:0] = 0_0_001_010 (SEW = 16, LMUL = 4) 
        li       t2, 0x0A
        vsetvl   x8, t1, t2
        csrr     x1, vtype
        RVTEST_SIGUPD(x3, x1)

        // vtype[7:0] = 0_0_001_011 (SEW = 16, LMUL = 8) 
        li       t2, 0x0B
        vsetvl   x8, t1, t2
        csrr     x1, vtype
        RVTEST_SIGUPD(x3, x1)

        // vtype[7:0] = 0_0_001_101 (SEW = 16, LMUL = 1/8) 
        li       t2, 0x0D
        vsetvl   x8, t1, t2
        csrr     x1, vtype
        RVTEST_SIGUPD(x3, x1)

        // vtype[7:0] = 0_0_001_110 (SEW = 16, LMUL = 1/4) 
        li       t2, 0x0E
        vsetvl   x8, t1, t2
        csrr     x1, vtype
        RVTEST_SIGUPD(x3, x1)

        // vtype[7:0] = 0_0_001_111 (SEW = 16, LMUL = 1/2) 
        li       t2, 0x0F
        vsetvl   x8, t1, t2
        csrr     x1, vtype
        RVTEST_SIGUPD(x3, x1)

        // vtype[7:0] = 0_0_010_000 (SEW = 32, LMUL = 1) 
        li       t2, 0x10
        vsetvl   x8, t1, t2
        csrr     x1, vtype
        RVTEST_SIGUPD(x3, x1)

        // vtype[7:0] = 0_0_010_001 (SEW = 32, LMUL = 2) 
        li       t2, 0x11
        vsetvl   x8, t1, t2
        csrr     x1, vtype
        RVTEST_SIGUPD(x3, x1)

        // vtype[7:0] = 0_0_010_010 (SEW = 32, LMUL = 4) 
        li       t2, 0x12
        vsetvl   x8, t1, t2
        csrr     x1, vtype
        RVTEST_SIGUPD(x3, x1)

        // vtype[7:0] = 0_0_010_011 (SEW = 32, LMUL = 8) 
        li       t2, 0x13
        vsetvl   x8, t1, t2
        csrr     x1, vtype
        RVTEST_SIGUPD(x3, x1)

        // vtype[7:0] = 0_0_010_101 (SEW = 32, LMUL = 1/8) 
        li       t2, 0x15
        vsetvl   x8, t1, t2
        csrr     x1, vtype
        RVTEST_SIGUPD(x3, x1)

        // vtype[7:0] = 0_0_010_110 (SEW = 32, LMUL = 1/4) 
        li       t2, 0x16
        vsetvl   x8, t1, t2
        csrr     x1, vtype
        RVTEST_SIGUPD(x3, x1)

        // vtype[7:0] = 0_0_010_111 (SEW = 32, LMUL = 1/2) 
        li       t2, 0x17
        vsetvl   x8, t1, t2
        csrr     x1, vtype
        RVTEST_SIGUPD(x3, x1)

        // vtype[7:0] = 0_0_011_000 (SEW = 64, LMUL = 1) 
        li       t2, 0x18
        vsetvl   x8, t1, t2
        csrr     x1, vtype
        RVTEST_SIGUPD(x3, x1)

        // vtype[7:0] = 0_0_011_001 (SEW = 64, LMUL = 2) 
        li       t2, 0x19
        vsetvl   x8, t1, t2
        csrr     x1, vtype
        RVTEST_SIGUPD(x3, x1)

        // vtype[7:0] = 0_0_011_010 (SEW = 64, LMUL = 4) 
        li       t2, 0x1A
        vsetvl   x8, t1, t2
        csrr     x1, vtype
        RVTEST_SIGUPD(x3, x1)

        // vtype[7:0] = 0_0_011_011 (SEW = 64, LMUL = 8) 
        li       t2, 0x1B
        vsetvl   x8, t1, t2
        csrr     x1, vtype
        RVTEST_SIGUPD(x3, x1)

        // vtype[7:0] = 0_0_011_101 (SEW = 64, LMUL = 1/8) 
        li       t2, 0x1D
        vsetvl   x8, t1, t2
        csrr     x1, vtype
        RVTEST_SIGUPD(x3, x1)

        // vtype[7:0] = 0_0_011_110 (SEW = 64, LMUL = 1/4) 
        li       t2, 0x1E
        vsetvl   x8, t1, t2
        csrr     x1, vtype
        RVTEST_SIGUPD(x3, x1)

        // vtype[7:0] = 0_0_011_111 (SEW = 64, LMUL = 1/2) 
        li       t2, 0x1F
        vsetvl   x8, t1, t2
        csrr     x1, vtype
        RVTEST_SIGUPD(x3, x1)


    ///////////////////////////////
    // cp_vill_vset_i_vli
    //
    // Running vset{i}vli instructions with vill bit set
    // Signature: vtype after execution
    ///////////////////////////////
    cp_vill_vset_i_vli:
        li       t1, 1                    // Set up for vl = 1 in vsetvl instructions

        // set the vill bit in vtype with an illegal type
        li       t2, 0x1D                 // vtype[7:0] = 0_0_011_101 (SEW = 64, LMUL = 1/8), always illegal
        vsetvl   x8, t1, t2

        // vsetvli, SEW = 8, LMUL = 8
        vsetvli  x8, t1, e8, m8, tu, mu
        csrr     x1, vtype
        RVTEST_SIGUPD(x3, x1)

        // set the vill bit in vtype with an illegal type
        li       t2, 0x1D                 // vtype[7:0] = 0_0_011_101 (SEW = 64, LMUL = 1/8), always illegal
        vsetvl   x8, t1, t2

        // vsetivli, SEW = 8, LMUL = 8
        vsetivli x8, 1, e8, m8, tu, mu
        csrr     x1, vtype
        RVTEST_SIGUPD(x3, x1)


        // set the vill bit in vtype with an illegal type
        li       t2, 0x1D                 // vtype[7:0] = 0_0_011_101 (SEW = 64, LMUL = 1/8), always illegal
        vsetvl   x8, t1, t2

        // vsetvli, SEW = 16, LMUL = 8
        vsetvli  x8, t1, e16, m8, tu, mu
        csrr     x1, vtype
        RVTEST_SIGUPD(x3, x1)

        // set the vill bit in vtype with an illegal type
        li       t2, 0x1D                 // vtype[7:0] = 0_0_011_101 (SEW = 64, LMUL = 1/8), always illegal
        vsetvl   x8, t1, t2

        // vsetivli, SEW = 16, LMUL = 8
        vsetivli x8, 1, e16, m8, tu, mu
        csrr     x1, vtype
        RVTEST_SIGUPD(x3, x1)


        // set the vill bit in vtype with an illegal type
        li       t2, 0x1D                 // vtype[7:0] = 0_0_011_101 (SEW = 64, LMUL = 1/8), always illegal
        vsetvl   x8, t1, t2

        // vsetvli, SEW = 32, LMUL = 8
        vsetvli  x8, t1, e32, m8, tu, mu
        csrr     x1, vtype
        RVTEST_SIGUPD(x3, x1)

        // set the vill bit in vtype with an illegal type
        li       t2, 0x1D                 // vtype[7:0] = 0_0_011_101 (SEW = 64, LMUL = 1/8), always illegal
        vsetvl   x8, t1, t2

        // vsetivli, SEW = 32, LMUL = 8
        vsetivli x8, 1, e32, m8, tu, mu
        csrr     x1, vtype
        RVTEST_SIGUPD(x3, x1)


        // set the vill bit in vtype with an illegal type
        li       t2, 0x1D                 // vtype[7:0] = 0_0_011_101 (SEW = 64, LMUL = 1/8), always illegal
        vsetvl   x8, t1, t2

        // vsetvli, SEW = 64, LMUL = 8
        vsetvli  x8, t1, e64, m8, tu, mu
        csrr     x1, vtype
        RVTEST_SIGUPD(x3, x1)

        // set the vill bit in vtype with an illegal type
        li       t2, 0x1D                 // vtype[7:0] = 0_0_011_101 (SEW = 64, LMUL = 1/8), always illegal
        vsetvl   x8, t1, t2

        // vsetivli, SEW = 64, LMUL = 8
        vsetivli x8, 1, e64, m8, tu, mu
        csrr     x1, vtype
        RVTEST_SIGUPD(x3, x1)


    ///////////////////////////////
    // cp_vill_vsetvl
    //
    // Running vsetvl instructions with vill bit set
    // Signature: vtype after execution
    ///////////////////////////////
    cp_vill_vsetvl:
        li       t1, 1                    // Set up for vl = 1 in vsetvl instructions

        // set the vill bit in vtype with an illegal type
        li       t2, 0x1D                 // vtype[7:0] = 0_0_011_101 (SEW = 64, LMUL = 1/8), always illegal
        vsetvl   x8, t1, t2

        // vtype[7:0] = 0_0_000_011 (SEW = 8, LMUL = 8) 
        li       t2, 0x03
        vsetvl   x8, t1, t2
        csrr     x1, vtype
        RVTEST_SIGUPD(x3, x1)


        // set the vill bit in vtype with an illegal type
        li       t2, 0x1D                 // vtype[7:0] = 0_0_011_101 (SEW = 64, LMUL = 1/8), always illegal
        vsetvl   x8, t1, t2

        // vtype[7:0] = 0_0_001_011 (SEW = 16, LMUL = 8) 
        li       t2, 0x0B
        vsetvl   x8, t1, t2
        csrr     x1, vtype
        RVTEST_SIGUPD(x3, x1)


        // set the vill bit in vtype with an illegal type
        li       t2, 0x1D                 // vtype[7:0] = 0_0_011_101 (SEW = 64, LMUL = 1/8), always illegal
        vsetvl   x8, t1, t2

        // vtype[7:0] = 0_0_010_011 (SEW = 32, LMUL = 8) 
        li       t2, 0x13
        vsetvl   x8, t1, t2
        csrr     x1, vtype
        RVTEST_SIGUPD(x3, x1)


        // set the vill bit in vtype with an illegal type
        li       t2, 0x1D                 // vtype[7:0] = 0_0_011_101 (SEW = 64, LMUL = 1/8), always illegal
        vsetvl   x8, t1, t2

        // vtype[7:0] = 0_0_011_011 (SEW = 64, LMUL = 8) 
        li       t2, 0x1B
        vsetvl   x8, t1, t2
        csrr     x1, vtype
        RVTEST_SIGUPD(x3, x1)


    ///////////////////////////////
    // cp_vill_vsetvl_rs2_vill
    //
    // Running vsetvl instructions with a valid config and vill bit set in both rs2 and vtype
    // Signature: vtype after execution
    ///////////////////////////////
    cp_vill_vsetvl_rs2_vill:
        li       t1, 1                    // Set up for vl = 1 in vsetvl instructions

        #ifdef __riscv_xlen
        #if __riscv_xlen == 32
            li       t0, 0x80000000           // Set the XLEN-1 bit to 1 (vill bit)
        #endif
        #if __riscv_xlen == 64
            li       t0, 0x8000000000000000   // Set the XLEN-1 bit to 1 (vill bit)
        #endif
        #endif

        // set the vill bit in vtype with an illegal type
        li       t2, 0x1D                 // vtype[7:0] = 0_0_011_101 (SEW = 64, LMUL = 1/8), always illegal
        vsetvl   x8, t1, t2

        // vtype[XLEN-1] = 1, vtype[7:0] = 0_0_000_011 (SEW = 8, LMUL = 8) 
        addi     t2, t0, 0x03
        vsetvl   x8, t1, t2
        csrr     x1, vtype
        RVTEST_SIGUPD(x3, x1)


        // set the vill bit in vtype with an illegal type
        li       t2, 0x1D                 // vtype[7:0] = 0_0_011_101 (SEW = 64, LMUL = 1/8), always illegal
        vsetvl   x8, t1, t2

        // vtype[XLEN-1] = 1, vtype[7:0] = 0_0_001_011 (SEW = 16, LMUL = 8) 
        addi     t2, t0, 0x0B
        vsetvl   x8, t1, t2
        csrr     x1, vtype
        RVTEST_SIGUPD(x3, x1)


        // set the vill bit in vtype with an illegal type
        li       t2, 0x1D                 // vtype[7:0] = 0_0_011_101 (SEW = 64, LMUL = 1/8), always illegal
        vsetvl   x8, t1, t2

        // vtype[XLEN-1] = 1, vtype[7:0] = 0_0_010_011 (SEW = 32, LMUL = 8) 
        addi     t2, t0, 0x13
        vsetvl   x8, t1, t2
        csrr     x1, vtype
        RVTEST_SIGUPD(x3, x1)


        // set the vill bit in vtype with an illegal type
        li       t2, 0x1D                 // vtype[7:0] = 0_0_011_101 (SEW = 64, LMUL = 1/8), always illegal
        vsetvl   x8, t1, t2

        // vtype[XLEN-1] = 1, vtype[7:0] = 0_0_011_011 (SEW = 64, LMUL = 8) 
        addi     t2, t0, 0x1B
        vsetvl   x8, t1, t2
        csrr     x1, vtype
        RVTEST_SIGUPD(x3, x1)


    ///////////////////////////////
    // cp_vsetvl_rs2_vill
    //
    // Running vsetvl instructions with vill bit set in rs2 and clear in vtype
    // Signature: vtype after execution
    ///////////////////////////////
    cp_vsetvl_rs2_vill:
        li       t1, 1                        // Set up for vl = 1 in vsetvl instructions

        #ifdef __riscv_xlen
        #if __riscv_xlen == 32
            li       t0, 0x80000000           // Set the XLEN-1 bit to 1 (vill bit)
        #endif
        #if __riscv_xlen == 64
            li       t0, 0x8000000000000000   // Set the XLEN-1 bit to 1 (vill bit)
        #endif
        #endif
        
        li          t3, 0x00                  // Register to keep count of the target SEW
        li          t5, 0x18                  // Register for vtype[7:0] = 0_0_011_000 (SEW = 64, LMUL = 1), end of loops

        // Need to loop through SEWs to attempt to clear vill bit and to execute vsetvl, 
        // since it is not definite which SEWs are supported
        rs2_vill_sew:                                 // Loop through target SEWs
            li          t2, 0x00                      // Register to keep count of the SEW used in attempt to clear vill bit (tentative SEW)

            rs2_vill_legal:
                vsetvl  x8, t1, t2                    // Attempt to clear the vill bit in vtype

                add     t4, t0, t3                    // Set vill bit and vtype[7:0] with target SEW
                vsetvl  x8, t1, t4                    // Execute vsetvl instruction with vill bit set in rs2
                csrr    x1, vtype                     // Read vtype to see if vill is set
                RVTEST_SIGUPD(x3, x1)                 // Store result

                addi    t2, t2, 0x08                  // Increment the count for tentative SEW (vtype[7:0] = 0_0_vsew[2:0]_000)
                bgt     t2, t5, end_rs2_vill_legal    // Finish this target SEW if all SEWs has been attempted to clear vtype.vill
                j       rs2_vill_legal
            
            end_rs2_vill_legal:

            addi    t3, t3, 0x08                      // Increment the count for target SEW (vtype[7:0] = 0_0_vsew[2:0]_000)
            bgt     t3, t5, end_rs2_vill_sew          // Finish if all target SEW has been attempted to execute to cover the coverpoint
            j       rs2_vill_sew

        end_rs2_vill_sew:


    ///////////////////////////////
    // cp_vtype_vill_set_vl_0
    //
    // Check that vl is set to 0 for a unsupported vtype
    // Signature: vl after execution
    ///////////////////////////////
    cp_vtype_vill_set_vl_0:
        li       t1, 1                    // Set up for vl = 1

        #ifdef __riscv_xlen
        #if __riscv_xlen == 32
            li       t0, 0x80000000           // Set the XLEN-1 bit to 1 (vill bit)
        #endif
        #if __riscv_xlen == 64
            li       t0, 0x8000000000000000   // Set the XLEN-1 bit to 1 (vill bit)
        #endif
        #endif

        vsetvl   x8, t1, t0
        csrr     x1, vl
        RVTEST_SIGUPD(x3, x1)


    ///////////////////////////////
    // cp_vsetvl_i_rd_nx0_rs1_x0
    // (cp_vsetvl_rd_nx0_rs1_x0 and cp_vsetvli_rd_nx0_rs1_x0)
    //
    // Set vl to VLMAX with vsetvl{i}
    // Signature: vl after execution
    ///////////////////////////////
    cp_vsetvl_i_rd_nx0_rs1_x0:
        #include "ZicsrV-vsetvl-Tests.h"


    ///////////////////////////////
    // cp_vsetvl_i_rd_x0_rs1_x0
    // (cp_vsetvl_rd_x0_rs1_x0 and cp_vsetvli_rd_x0_rs1_x0)
    //
    // Set vl unchanged with vsetvl{i}
    // Signature: vl after execution
    ///////////////////////////////
    cp_vsetvl_i_rd_x0_rs1_x0:
        li       t1, 1                    // Set up for vl = 1 (non-zero vl)
        vsetvli  x8, t1, e8, m1, tu, mu   // Initialize the SEW/LMUL ratio
        
        // run with vsetvli
        vsetvli  x0, x0, e8, m1, tu, mu   // Follow the same SEW/LMUL ratio to ensure that vlmax is unchanged
        csrr     x1, vl
        RVTEST_SIGUPD(x3, x1)

        // vtype[7:0] = 0_0_000_000 (SEW = 8, LMUL = 1) 
        li       t2, 0x00
        vsetvl   x0, x0, t2               // Follow the same SEW/LMUL ratio to ensure that vlmax is unchanged
        csrr     x1, vl
        RVTEST_SIGUPD(x3, x1)


    ############################# AVL #############################

    ///////////////////////////////
    // cp_vsetvl_i_avl_eq_zero
    //
    // Check vl after running vsetvl{i} instructions with AVL = 0
    // Signature: vl after execution
    ///////////////////////////////
    cp_vsetvl_i_avl_eq_zero:
        // Use SEW = 8 and LMUL = 1 for constant VLMAX
        li       t1, 0                    // Set up for vl = 0

        vsetvli  x8, t1, e8, m1, tu, mu
        csrr     x1, vl
        RVTEST_SIGUPD(x3, x1)

        li       t2, 0x00                 // vtype[7:0] = 0_0_000_000 (SEW = 8, LMUL = 1) 
        vsetvl   x8, t1, t2
        csrr     x1, vl
        RVTEST_SIGUPD(x3, x1)

        
    ///////////////////////////////
    // cp_vsetvl_i_avl_eq_vlmax
    //
    // Check vl after running vsetvl{i} instructions with AVL = VLMAX
    // Signature: vl after execution
    ///////////////////////////////
    cp_vsetvl_i_avl_eq_vlmax:
        // Use SEW = 8 and LMUL = 1 for constant VLMAX
        vsetvli  t1, x0, e8, m1, tu, mu   // Store t1 = VLMAX

        vsetvli  x8, t1, e8, m1, tu, mu
        csrr     x1, vl
        RVTEST_SIGUPD(x3, x1)

        li       t2, 0x00                 // vtype[7:0] = 0_0_000_000 (SEW = 8, LMUL = 1) 
        vsetvl   x8, t1, t2
        csrr     x1, vl
        RVTEST_SIGUPD(x3, x1)

    
    ///////////////////////////////
    // cp_vsetvl_i_avl_lt_2x_vlmax
    //
    // Check vl after running vsetvl{i} instructions with AVL < 2 * VLMAX
    // Signature: vl after execution
    ///////////////////////////////
    cp_vsetvl_i_avl_lt_2x_vlmax:
        // Use SEW = 8 and LMUL = 2 for constant VLMAX, ensuring that VLMAX >= 2
        // If VLMAX = 1, then VLMAX < AVL < (2 * VLMAX) could not be achieved
        vsetvli  t1, x0, e8, m2, tu, mu   // Store t1 = VLMAX
        addi     t1, t1, 1                // t1 = VLMAX + 1, setting VLMAX < AVL < (2 * VLMAX)

        vsetvli  x8, t1, e8, m2, tu, mu
        csrr     x1, vl
        RVTEST_SIGUPD(x3, x1)

        li       t2, 0x01                 // vtype[7:0] = 0_0_000_001 (SEW = 8, LMUL = 2) 
        vsetvl   x8, t1, t2
        csrr     x1, vl
        RVTEST_SIGUPD(x3, x1)
    

    ///////////////////////////////
    // cp_vsetvl_i_avl_eq_2x_vlmax
    //
    // Check vl after running vsetvl{i} instructions with AVL = 2 * VLMAX
    // Signature: vl after execution
    ///////////////////////////////
    cp_vsetvl_i_avl_eq_2x_vlmax:
        // Use SEW = 8 and LMUL = 2 for constant VLMAX
        vsetvli  t1, x0, e8, m2, tu, mu   // Store t1 = VLMAX
        slli     t1, t1, 1                // t1 = 2 * VLMAX, setting AVL = (2 * VLMAX)

        vsetvli  x8, t1, e8, m2, tu, mu
        csrr     x1, vl
        RVTEST_SIGUPD(x3, x1)

        li       t2, 0x01                 // vtype[7:0] = 0_0_000_001 (SEW = 8, LMUL = 2) 
        vsetvl   x8, t1, t2
        csrr     x1, vl
        RVTEST_SIGUPD(x3, x1)

    
    ///////////////////////////////
    // cp_vsetvl_i_avl_gt_2x_vlmax
    //
    // Check vl after running vsetvl{i} instructions with AVL > 2 * VLMAX
    // Signature: vl after execution
    ///////////////////////////////
    cp_vsetvl_i_avl_gt_2x_vlmax:
        // Use SEW = 8 and LMUL = 2 for constant VLMAX
        vsetvli  t1, x0, e8, m2, tu, mu   // Store t1 = VLMAX
        slli     t1, t1, 1                // t1 = 2 * VLMAX
        addi     t1, t1, 1                // t1 = 2 * VLMAX + 1, setting AVL > (2 * VLMAX)

        vsetvli  x8, t1, e8, m2, tu, mu
        csrr     x1, vl
        RVTEST_SIGUPD(x3, x1)

        li       t2, 0x01                 // vtype[7:0] = 0_0_000_001 (SEW = 8, LMUL = 2) 
        vsetvl   x8, t1, t2
        csrr     x1, vl
        RVTEST_SIGUPD(x3, x1)


    ///////////////////////////////
    // cp_vsetivli_avl_corners
    //
    // Run all 32 imm with vsetivli instructions to check AVL rules
    // Signature: vl after execution
    ///////////////////////////////
    cp_vsetivli_avl_corners:
        #include "ZicsrV-vsetivli-Tests.h"


    ############################ vstart ############################

    ///////////////////////////////
    // cp_vstart_out_of_bounds
    //
    // Check the number of writable bits for vstart
    // Signature: vstart after execution
    ///////////////////////////////
    cp_vstart_out_of_bounds:
        // Largest element index = 2^16-1, since max possible VLEN = 2^16
        li    x2, 0x10000        // Load max possible VLEN = 2^16 to x2

        csrrw x5, vstart, x2	 // Write to vstart
        nop
        RVTEST_SIGUPD(x3, x5)

#endif

 # ---------------------------------------------------------------------------------------------
    # HALT

RVTEST_CODE_END
RVMODEL_HALT

RVTEST_DATA_BEGIN
# Input data section.
    .data
    .align 4

vector_random:
    .word 0x3d3ee949
    .word 0xd3f44233
    .word 0x7bdfb57f
    .word 0x0440e10a
    .word 0x6edc028a
    .word 0x3d71a037
    .word 0xe24fd533
    .word 0x793399e4
    .word 0x7f7d4396
    .word 0x3f1ea97a
    .word 0xcd8101d5
    .word 0x430ce576
    .word 0xa61363d8
    .word 0x213dfea9
    .word 0xc30fbe7b
    .word 0xff00595a

RVTEST_DATA_END

# Output data section.
RVMODEL_DATA_BEGIN
rvtest_sig_begin:
sig_begin_canary:
CANARY;

    .align 3
signature_base:
    .fill 1000*(XLEN/32),4,0xdeadbeef

test_A_res:
    .fill 2, 4, 0xdeadbeef

mtrap_sigptr:
  .fill 1000, 4, 0xdeadbeef

#ifdef rvtest_gpr_save
gpr_save:
  .fill 32*(XLEN/32), 4, 0xdeadbeef
#endif

sig_end_canary:
CANARY;
rvtest_sig_end:
RVMODEL_DATA_END

scratch:
.fill 4,4,0x0

# Initialize stack with room for 512 bytes
.bss
    .space 512
topofstack: