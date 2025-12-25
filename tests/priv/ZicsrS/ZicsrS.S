///////////////////////////////////////////
// ZicsrS.S
//
// Written: vkrishna@hmc.edu 01 February 2024
//
// Purpose: Functional coverage tests for CSRs in supervisor mode
//
// SPDX-License-Identifier: Apache-2.0
///////////////////////////////////////////

// General notes:
// Use csrrw/csrrs/csrrc t6, csr, rs1    when modifying a CSR to also check the old value.

##### START_TEST_CONFIG #####
# REQUIRED_EXTENSIONS: [I, S, Zicsr, Sm]
# MARCH: rv${XLEN}i_zicsr
# CONFIG_DEPENDENT: true
##### END_TEST_CONFIG #####

#include "WALLY-init-lib.h"

main:

    # set up fast trap handler for uncompressed illegal instructions
    # because Zicsr tests will throw a lot of illegal instruction traps while attempting to access CSRs
    # This cuts the instruction count and runtime by nearly 2x
    # However, don't blindly use this handler in other privileged tests
    la t0, trap_handler_fastuncompressedillegalinstr
    csrw mtvec, t0

    # enter supervisor mode
    li a0, 1
    ecall

/////////////////////////////////
// cp_satp
/////////////////////////////////
cp_satp:
    csrr t0, satp
    li t1, -1
    csrrc t3, satp, t1      # clear all bits

    // logic to exclude mode bits
    #ifdef __riscv_xlen
        #if __riscv_xlen == 64
            li t2, 0b1111
            slli t2, t2, 60
        #elif __riscv_xlen == 32
            li t2, 0b1
            slli t2, t2, 31
        #endif
        not t2, t2
        and t1, t1, t2
    #else
        ERROR: __riscv_xlen not defined
    #endif
    csrrw t3, satp, t1 # write all 1s except mode
    csrrw t3, satp, x0 # write all 0s
    csrrs t3, satp, t1 # set all except mode
    csrrw t3, satp, t0

/////////////////////////////////
// cp_csrwalk_satp
/////////////////////////////////

cp_csrwalk_satp:
    csrr t6, satp      # save satp
    li t0, 1           # 1 in LSB
    li t1, -1          # all 1s
    #ifdef __riscv_xlen
        #if __riscv_xlen == 64
            li t2, 0b1111
            slli t2, t2, 60
        #elif __riscv_xlen == 32
            li t2, 0b1
            slli t2, t2, 31
        #endif
        not t2, t2
    #else
        ERROR: __riscv_xlen not defined
    #endif

    2:
        csrrc x0, satp, t1 # clear all bits
        csrrs t3, satp, t0 # set walking 1
        slli t0, t0, 1 # shift left
        bleu t0, t2, 2b # repeat until all bits are set

    li t0, 1
    3:
        csrrc x0, satp, t0 # clear walking 1
        slli t0, t0, 1 # walk the 1
        bleu t0, t2, 3b # repeat until all bits are set

    csrrw t3, satp, t6 # restore satp

/////////////////////////////////
// cp_scause_write
/////////////////////////////////
    csrr s0, scause     # save CSR
// with interrupt = 0: 0-64, walking 1s in bits 6-(XLEN-2)
    // with interrupt = 0: write scause with 0-64 (0 already done)
    li t1, 64           # upper bound
    mv t0, x0           # initialize loop counter
1:  csrrw t6, scause, t0     # write CSR
    beq t0, t1, cp_scause_walking1s_noint
    addi t0, t0, 1      # increment test value
    j   1b
   // with interrupt = 0: write scause with walking 1s in bits 6-(XLEN-2)"
cp_scause_walking1s_noint:
    slli t0, t0, 1      # walk 1s
    csrrw t6, scause, t0     # write CSR
    bnez t0, cp_scause_walking1s_noint  # until all 1s are gone
// with interrupt = 1: 0-15, walking 1s in bits 4-(XLEN-2)
// Now set interrupt = 1 as msb of register
    jal setmsb          # put a 1 in the msb of a0
    li t1, 16           # upper bound
    mv t0, x0           # initialize loop counter
1: or t2, t0, a0       # set interrupt = 1 withmcause msb
    csrrw t6, scause, t2    # write CSR
    beq t0, t1, cp_scause_walking1s_int
    addi t0, t0, 1      # increment test value
    j   1b
   // with interrupt = 0: write scause with walking 1s in bits 6-(XLEN-2)"
cp_scause_walking1s_int:
    slli t0, t0, 1      # walk 1s
    or t0, t0, a0       # set 1 in msb for interrupts
    csrrw t6, scause, t0     # write CSR
    bne t0, a0, cp_scause_walking1s_int  # until all 1s are gone and only interrupt bit remains
    csrrw t6, scause, s0      # restore CSR

/////////////////////////////////
// cp_sstatus_sd_write
/////////////////////////////////
    csrr s0, sstatus    # save CSR

// all 128 combinations of sd, fs, xs, vs
    jal setmsb          # put a 1 in the msb of a0 (SD)
    li a1, 0x6000       # FS: bits 14:13
    li a2, 0x18000      # XS: bits 16:15
    li a3, 0x600        # VS: bits 10:9
    not t0, a0          # zero in SD msb
    not t1, a1          # zero in FS
    not t2, a2          # zero in XS
    not t3, a3          # zero in VS
    # create a4 with all seven bits cleared
    and a4, s0, t0      # clear SD
    and a4, a4, t1      # clear FS
    and a4, a4, t2      # clear XS
    and a4, a4, t3      # clear VS

sdloop:
    # loop over SD
    li t0, 0            # initial SD value
fsloop:
    li s1, 0x2000       # initial FS value
    li t1, 0
xsloop:
    li s2, 0x8000       # initial XS value
    li t2, 0
vsloop:
    li s3, 0x200        # initial VS value
    li t3, 0
formbits:
// form the combination in t4 and merge it with other fields from a4
    or t4, t0, t1       # SD | FS
    or t4, t4, t2       # | XS
    or t4, t4, t3       # | VS
    or t4, t4, a4       # merge sstatus with SD, FS, XS, VS
    csrrw t6, sstatus, t4   # write value to sstatus

// increment VS
    add t3, t3, s3      # increment vs
    ble t3, a3, formbits    # repeat until all 4 cases of VS are covered
// increment XS
    add t2, t2, s2      # increment xs
    ble t2, a2, vsloop  # repeat until all 4 cases of XS are covered
// increment FS
    add t1, t1, s1      # increment fs
    ble t1, a1, xsloop  # repeat until all 4 cases of FS are covered
    add t0, t0, a0      # increment SD value
    bnez t0, fsloop     # repeat until both cases of SD are covered

    csrrw t6, sstatus, s0    # restore CSR

/////////////////////////////////
// cp_sprivinst
/////////////////////////////////
cp_sprivinst:
    // ecall
    li a0, 1
    ecall       # switch from supervisor mode to supervisor mode

    // ebreak
    ebreak       # take a trap, and the trap handler returns

/////////////////////////////////
// cp_mret
/////////////////////////////////
cp_mret:
// Executing mret in supervisor mode
// Should throw an illegal instruction exception
    mret

/////////////////////////////////
// cp_shadow
/////////////////////////////////
cp_shadow_mstatus:          # write to mstatus in machine mode, read back sstatus in supervisor mode
    li t3, -1
    li a0, 3
    ecall
    csrr t1, mstatus        # save the current mstatus
    csrrw t6, mstatus, x0   # write all 0s in machine mode
    li a0, 1
    ecall
    csrr t2, sstatus        # read back sstatus in supervisor mode

    li a0, 3
    ecall
    csrrw t6, mstatus, t3   # write all 1s in machine mode
    li a0, 1
    ecall
    csrr t2, sstatus        # read back sstatus in supervisor mode

    li a0, 3
    ecall
    csrrw t6, mstatus, t1   # restore original mstatus

cp_shadow_mie:              # write to mie in machine mode, read back sie in supervisor mode
    csrr t1, mie
    csrrw t6, mie, x0       # write all 0s in machine mode
    li a0, 1
    ecall
    csrr t2, sie            # read back sie in supervisor mode

    li a0, 3
    ecall
    csrrw t6, mie, t3       # write all 1s in machine mode
    li a0, 1
    ecall
    csrr t2, sie            # read back sie in supervisor mode

    li a0, 3
    ecall
    csrrw t6, mie, t1       # restore original mie

cp_shadow_mip:              # write to mip in machine mode, read back sip in supervisor mode
    csrr t1, mip
    csrrw t6, mip, x0       # write all 0s in machine mode
    li a0, 1
    ecall
    csrr t2, sip            # read back sip in supervisor mode

    li a0, 3
    ecall
    csrrw t6, mip, t3       # write all 1s in machine mode
    li a0, 1
    ecall
    csrr t2, sip            # read back sip in supervisor mode

    li a0, 3
    ecall
    csrrw t6, mip, t1       # restore original mip
    li a0, 1
    ecall

cp_shadow_sstatus:          # write to sstatus in supervisor mode, read back mstatus in machine mode
    csrr t1, sstatus
    csrrw t6, sstatus, x0   # write all 0s in supervisor mode
    li a0, 3
    ecall
    csrr t2, mstatus        # read back mstatus in machine mode
    li a0, 1
    ecall

    csrrw t6, sstatus, t3   # write all 1s in supervisor mode
    li a0, 3
    ecall
    csrr t2, mstatus        # read back mstatus in machine mode
    li a0, 1
    ecall

    csrrw t6, sstatus, t1   # restore original sstatus

cp_shadow_sie:              # write to sie in supervisor mode, read back mie in machine mode
    csrr t1, sie
    csrrw t6, sie, x0       # write all 0s in supervisor mode
    li a0, 3
    ecall
    csrr t2, mie            # read back mie in machine mode
    li a0, 1
    ecall

    csrrw t6, sie, t3       # write all 1s in supervisor mode
    li a0, 3
    ecall
    csrr t2, mie            # read back mie in machine mode
    li a0, 1
    ecall

    csrrw t6, sie, t1       # restore original sie

cp_shadow_sip:              # write to sip in supervisor mode, read back mip in machine mode
    csrr t1, sip
    csrrw t6, sip, x0       # write all 0s in supervisor mode
    li a0, 3
    ecall
    csrr t2, mip            # read back mip in machine mode
    li a0, 1
    ecall

    csrrw t6, sip, t3       # write all 1s in supervisor mode
    li a0, 3
    ecall
    csrr t2, mip            # read back mip in machine mode
    li a0, 1
    ecall

    csrrw t6, sip, t1       # restore original sip

/////////////////////////////////
// cp_sret
/////////////////////////////////
// Sweep executing sret in supervisor mode across cross-product of spp, tsr, spie, sie
cp_sret:
    li a0, 3            # switch into machine mode to save mstatus
    ecall
    csrr s10, mstatus   # save mstatus
    li a0, 1            # switch back to supervisor mode for tests
    ecall

    li a0, 0x00000000   # tsr = 0, spp = 0  spie = 0 sie = 0
    jal srettest
    li a0, 0x00000002   # tsr = 0, spp = 0  spie = 0 sie = 1
    jal srettest
    li a0, 0x00000020   # tsr = 0, spp = 0  spie = 1 sie = 0
    jal srettest
    li a0, 0x00000022   # tsr = 0, spp = 0  spie = 1 sie = 1
    jal srettest
    li a0, 0x00000100   # tsr = 0, spp = 1  spie = 0 sie = 0
    jal srettest
    li a0, 0x00000102   # tsr = 0, spp = 1  spie = 0 sie = 1
    jal srettest
    li a0, 0x00000120   # tsr = 0, spp = 1  spie = 1 sie = 0
    jal srettest
    li a0, 0x00000122   # tsr = 0, spp = 1  spie = 1 sie = 1
    jal srettest
    li a0, 0x00400000   # tsr = 1, spp = 0  spie = 0 sie = 0
    jal srettest
    li a0, 0x00400002   # tsr = 1, spp = 0  spie = 0 sie = 1
    jal srettest
    li a0, 0x00400020   # tsr = 1, spp = 0  spie = 1 sie = 0
    jal srettest
    li a0, 0x00400022   # tsr = 1, spp = 0  spie = 1 sie = 1
    jal srettest
    li a0, 0x00400100   # tsr = 1, spp = 1  spie = 0 sie = 0
    jal srettest
    li a0, 0x00400102   # tsr = 1, spp = 1  spie = 0 sie = 1
    jal srettest
    li a0, 0x00400120   # tsr = 1, spp = 1  spie = 1 sie = 0
    jal srettest
    li a0, 0x00400122   # tsr = 1, spp = 1  spie = 1 sie = 1
    jal srettest

    li a0, 3                 # switch into machine mode to restore sstatus and mstatus
    ecall
    csrrw t6, mstatus, s10   # restore mstatus
    li a0, 1                 # switch back to supervisor mode for tests
    ecall
    j postsrettest

// takes in the desired mstatus, sets it, and then takes an sret
//      inputs:
//          a0 = desired status bits (bit 22: mstatus.tsr, bit 8: sstatus.spp, bit 5: sstatus.spie, bit 1: sstatus.sie)
//          ra = return address (right after the call to srettest)
srettest:
    mv s0, ra               # save ra to call setmstatus
    mv s1, a0               # save sstatus
    jal setmstatus          # set mstatus
    mv a0, s1               # restore sstatus
    la t1, srettest_sepc    # load addr of srettest_sepc
    csrrw t6, sepc, t1      # return to srettest_sepc when done

    li t1, 0b1

    slli t1, t1, 1       # shift to the sstatus.sie bit mask
    and t2, t1, a0       # isolate the sstatus.sie bit
    jal writebits        # write sstatus.sie

    slli t1, t1, 4       # shift to the sstatus.spie bit mask
    and t2, t1, a0       # isolate the sstatus.spie bit
    jal writebits        # write sstatus.spie

    slli t1, t1, 3       # shift to the sstatus.spp bit mask
    and t2, t1, a0       # isolate the sstatus.spp bit
    jal writebits        # write sstatus.spp

    j postsetup

    writebits:                  # takes in t1, which is the mask, as well as t2, indicating value
        beqz t2, clearbits      # checks if bit is 0 or 1
        csrrs t6, sstatus, t1   # set bits as specified in t1
        ret
        clearbits:
            csrrc t6, sstatus, t1   # clear bits as specified in t1
            ret

    postsetup:
        mv ra, s0               # restore ra for after srettest_mepc
        sret                    # take the sret. Should go to srettest_mepc and adjust sstatus


setmstatus:                 # takes in the desired mstatus.tsr in bit 22 of a0 and sets it
    li t1, 0b1
    slli t1, t1, 22         # shift to the mstatus.tsr bit mask
    and t1, t1, a0          # isolate the mstatus.tsr bit

    li a0, 3                # switch into machine mode to set mstatus
    ecall

    csrrs t6, mstatus, t1   # set mstatus.tsr
    li a0, 1
    ecall
    ret

srettest_sepc:
    li a0, 1
    ecall                   # make sure we return to supervisor mode
    csrrw t6, sstatus, s0   # restore sstatus
    ret

postsrettest:
# switch to machine mode and set fs = 1 so we can test
    li a0, 3
    ecall

    # set fs = 1
    li t0, 0x2000
    csrrw t6, mstatus, t0

# return to supervisor mode to run tests
    li a0, 1
    ecall

///////////////////////////////////
// walking 1s and 0s for each register
///////////////////////////////////
// cp_sstatus_write_edges
// cp_scause_write_edges
// cp_sie_write_edges
// cp_stvec_write_edges
// cp_scounteren_write_edges
// cp_senvcfg_write_edges
// cp_sscratch_write_edges
// cp_sepc_write_edges
// cp_stval_write_edges
// cp_sip_write_edges
// cp_scountinhibit_write_edges
///////////////////////////////////

#include "ZicsrS-Walk.h"

finished:
    // return to machine mode
    li a0, 3
    ecall
    j done
