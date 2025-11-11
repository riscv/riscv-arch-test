///////////////////////////////////////////
// ZicsrM.S
//
// Written: David_Harris@hmc.edu 13 October 2024
//
// Purpose: Functional coverage tests for CSRs in machine mode
//
// SPDX-License-Identifier: Apache-2.0
///////////////////////////////////////////

// General notes:
// Use csrrw/csrrs/csrrc t6, csr, rs1    when modifying a CSR to also check the old value.

##### START_TEST_CONFIG #####
# implemented_extensions: [I, M, A, C, F, D, S, Zicsr, Zba, Zbb, Zbs]
# MARCH: rv${XLEN}imacfd_zicsr_zba_zbb_zbs
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

    # For M-mode (ZicsrM) only, lock PMP region 0 so that all the PMP CSRs can be accessed without corrupting region 0
    li t0, 0x8F
    csrw pmpcfg0, t0   # configure PMP0 to TOR RWX locked


/////////////////////////////////
// cp_mcause_write
/////////////////////////////////
    csrr s0, mcause     # save CSR
// with interrupt = 0: 0-64, walking 1s in bits 6-(XLEN-2)
    // with interrupt = 0: write mcause with 0-64 (0 already done)
    li t1, 64           # upper bound
    mv t0, x0           # initialize loop counter
1:  csrrw t6, mcause, t0     # write CSR
    beq t0, t1, cp_mcause_walking1s_noint
    addi t0, t0, 1      # increment test value
    j   1b
   // with interrupt = 0: write mcause with walking 1s in bits 6-(XLEN-2)"
cp_mcause_walking1s_noint:
    slli t0, t0, 1      # walk 1s
    csrrw t6, mcause, t0     # write CSR
    bnez t0, cp_mcause_walking1s_noint  # until all 1s are gone
// with interrupt = 1: 0-15, walking 1s in bits 4-(XLEN-2)
// Now set interrupt = 1 as msb of register
    jal setmsb          # put a 1 in the msb of a0
    li t1, 16           # upper bound
    mv t0, x0           # initialize loop counter
1: or t2, t0, a0       # set interrupt = 1 with msb
    csrrw t6, mcause, t2    # write CSR
    beq t0, t1, cp_mcause_walking1s_int
    addi t0, t0, 1      # increment test value
    j   1b
   // with interrupt = 0: write mcause with walking 1s in bits 6-(XLEN-2)"
cp_mcause_walking1s_int:
    slli t0, t0, 1      # walk 1s
    or t0, t0, a0       # set 1 in msb for interrupts
    csrrw t6, mcause, t0     # write CSR
    bne t0, a0, cp_mcause_walking1s_int  # until all 1s are gone and only interrupt bit remains
    csrrw t6, mcause, s0      # restore CSR

/////////////////////////////////
// cp_misa_mxl_write
/////////////////////////////////
tmp:
// Write 0, 1, 2, 3 to misa.MXL
    jal setmsb          # put a 1 in the msb of a0 (XLEN-1)
    srli a1, a0, 1      # put a 1 in the second msb of a1 (XLEN-2)
    or a2, a1, a0       # put a 1 in both msbs of a2 (XLEN-1:XLEN-2)
    not a3, a2          # put 1s in all but the 2 msbs of a3
    csrr s0, misa       # read MISA
    and t0, s0, a3      # clear 2 msbs
    or t1, t0, a1       # set XLEN-2
    or t2, t0, a0       # set XLEN-1
    or t3, t0, a2       # set both msbs
    csrrc t6, misa, t0       # misa.MXL = 0
    csrrc t6, misa, t1       # misa.MXL = 1
    csrrc t6, misa, t2       # misa.MXL = 2
    csrrc t6, misa, t3       # misa.MXL = 3
    csrrw t6, misa, s0       # restore MISA

/////////////////////////////////
// cp_misa_ext_write_edges:
// and cp_misa_middle_write
/////////////////////////////////
// write all 0s to extension bits [25:0]
    li t0, 0x03FFFFFF   # 1s in bottom 26 bits
    csrrc t6, misa, t0       # try clearing all bits
// write all 0s to extension bits
    csrrs t6, misa, t0       # try setting all bits
// walking 0s and walking 1s
    li t1, 1            # 1 in lsb
    csrrw t6, misa, s0       # restore misa
1:  csrrc t6, misa, t1       # and clear the walking zero bit
    csrrs t6, misa, t1       # and set the walking zero bit
    slli t1, t1, 1      # shift walking zero
    bnez t1, 1b         # continue until zero walks off the end

/////////////////////////////////
// cp_misa_ext_disable / enable
/////////////////////////////////
    csrrw t6, misa, s0       # restore misa

    // A bit
    li t0, 1            # 1 in A bit
    csrrc t6, misa, t0       # clear A bit
    la t1, scratch      # scratch memory location
    lr.w t2, (t1)       # try an A (Zalrsc) instruction
    amoadd.w t2, s0, (t1)   # try an A (Zaamo) instruction
    csrrs t6, misa, t0       # set A bit
    lr.w t2, (t1)       # try an A (Zalrsc) instruction
    amoadd.w t2, s0, (t1)   # try an A (Zaamo) instruction

    // B bit
    li t0, 2            # 1 in B bit
    csrrc t6, misa, t0       # clear B bit
    sh1add t2, x0, t0   # try a Zba instruction
    min t2, x0, t0      # try a Zbb instruction
    bset t2, x0, t0     # try a Zbs instruction
    csrrs t6, misa, t0       # set B bit
    sh1add t2, x0, t0   # try a Zba instruction
    min t2, x0, t0      # try a Zbb instruction
    bset t2, x0, t0     # try a Zbs instruction

    // C bit
    li t0, 4            # 1 in C bit
    csrrc t6, misa, t0       # clear C bit
    .word 0x00019396    # try C instructions: c.add x7, x5 = 0x9396; c.nop = 0x0001
    csrrs t6, misa, t0       # set C bit
    .word 0x00019396    # try C instructions: c.add x7, x5 = 0x9396; c.nop = 0x0001

    // F bit
    li t0, 0x2000       # 1 in bit 13
    csrrs t6, mstatus, t0    # turn on FS to enable floating-point
    li t0, 0x20         # 1 in F bit
    csrrc t6, misa, t0       # clear F bit
    fcvt.s.w f0, t0     # try a F instruction
    csrrs t6, misa, t0       # set F bit
    fcvt.s.w f0, t0     # try a F instruction

    // D bit (with F already on, if possible)
    li t0, 0x08         # 1 in D bit
    csrrc t6, misa, t0       # clear D bit
    fcvt.d.w f0, t0     # try a D instruction
    csrrs t6, misa, t0       # set D bit
    fcvt.d.w f0, t0     # try a D instruction

    // I bit
    li t0, 0x100        # 1 in I bit
    csrrc t6, misa, t0       # clear I bit
    add t2, t0, t0      # try a I instruction
    csrrs t6, misa, t0       # set I bit
    add t2, t0, t0      # try a I instruction

    // M bit
    li t0, 0x1000       # 1 in M bit
    csrrc t6, misa, t0       # clear M bit
    mul t2, t0, t0      # try a M instruction
    csrrs t6, misa, t0       # set M bit
    mul t2, t0, t0      # try a M instruction

    // Restore MISA
    csrrw t6, misa, s0       # restore saved value


/////////////////////////////////
// cp_mststaus_tsr_write
// cp_mstatus_tw_write
// cp_mstatus_tvm_write
// cp_mstatus_mxr_write
// cp_mstatus_sum_write
// cp_mstatus_mprv_write
// cp_mstatus_xs_write
// cp_mstatus_fs_write
// cp_mstatus_vs_write
// cp_mstatus_spp_write
// cp_mstatus_mpie_write
// cp_mstatus_ube_write
// cp_mstatus_spie_write
// cp_mstatus_wpri*cp_mie_write
// cp_mstatus_mie_write
// cp_mstatus_sie_write
/////////////////////////////////
// use a pattern of walking zeros and walking 1s relative to the initial value of mstatus
// Also apply 00 and 11 to the 2-bit fields

    csrr s0, mstatus    # save CSR
    li t0, 1            # 1 in lsb
1:  csrrc t6, mstatus, t0    # walk a zero
    csrrs t6, mstatus, t0    # walk a one
    csrrw t6, mstatus, s0   # restore mstatus
    slli t0, t0, 1      # walk the 1
    bnez t0, 1b         # repeat until all bits are walked

    li t0, 0x1800       # MPP: bits 12:11
    csrrc t6, mstatus, t0   # mstatus.MPP = 00
    csrrs t6, mstatus, t0   # mstatus.MPP = 11
    csrrw t6, mstatus, s0   # restore MPP

/////////////////////////////////
// cp_mstatus_sd_write
/////////////////////////////////
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
    or t4, t4, a4       # merge mstatus with SD, FS, XS, VS
    csrrw t6, mstatus, t4   # write value to mstatus

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

    csrrw t6, mstatus, s0    # restore CSR

/////////////////////////////////
// cp_privinst
/////////////////////////////////

    // ecall
    li a0, 3
    ecall       # switch from machine mode to machine mode

    // ebreak
    ebreak       # take a trap, and the trap handler returns

/////////////////////////////////
// cp_mret
/////////////////////////////////
// Sweep executing mret in machine mode across cross-product of mpp, mprv, mpie, mie

    csrr s0, mstatus    # save mstatus

    li a0, 0x00000000   # mpp = 00  mprv = 0  mpie = 0 mie = 0
    jal mrettest
    li a0, 0x00000008   # mpp = 00  mprv = 0  mpie = 0 mie = 1
    jal mrettest
    li a0, 0x00000080   # mpp = 00  mprv = 0  mpie = 1 mie = 0
    jal mrettest
    li a0, 0x00000088   # mpp = 00  mprv = 0  mpie = 1 mie = 1
    jal mrettest
    li a0, 0x00020000   # mpp = 00  mprv = 1  mpie = 0 mie = 0
    jal mrettest
    li a0, 0x00020008   # mpp = 00  mprv = 1  mpie = 0 mie = 1
    jal mrettest
    li a0, 0x00020080   # mpp = 00  mprv = 1  mpie = 1 mie = 0
    jal mrettest
    li a0, 0x00020088   # mpp = 00  mprv = 1  mpie = 1 mie = 1
    jal mrettest
    li a0, 0x00000800   # mpp = 01  mprv = 0  mpie = 0 mie = 0
    jal mrettest
    li a0, 0x00000808   # mpp = 01  mprv = 0  mpie = 0 mie = 1
    jal mrettest
    li a0, 0x00000880   # mpp = 01  mprv = 0  mpie = 1 mie = 0
    jal mrettest
    li a0, 0x00000888   # mpp = 01  mprv = 0  mpie = 1 mie = 1
    jal mrettest
    li a0, 0x00020800   # mpp = 01  mprv = 1  mpie = 0 mie = 0
    jal mrettest
    li a0, 0x00020808   # mpp = 01  mprv = 1  mpie = 0 mie = 1
    jal mrettest
    li a0, 0x00020880   # mpp = 01  mprv = 1  mpie = 1 mie = 0
    jal mrettest
    li a0, 0x00020888   # mpp = 01  mprv = 1  mpie = 1 mie = 1
    jal mrettest
    li a0, 0x00001800   # mpp = 11  mprv = 0  mpie = 0 mie = 0
    jal mrettest
    li a0, 0x00001808   # mpp = 11  mprv = 0  mpie = 0 mie = 1
    jal mrettest
    li a0, 0x00001880   # mpp = 11  mprv = 0  mpie = 1 mie = 0
    jal mrettest
    li a0, 0x00001888   # mpp = 11  mprv = 0  mpie = 1 mie = 1
    jal mrettest
    li a0, 0x00021800   # mpp = 11  mprv = 1  mpie = 0 mie = 0
    jal mrettest
    li a0, 0x00021808   # mpp = 11  mprv = 1  mpie = 0 mie = 1
    jal mrettest
    li a0, 0x00021880   # mpp = 11  mprv = 1  mpie = 1 mie = 0
    jal mrettest
    li a0, 0x00021888   # mpp = 11  mprv = 1  mpie = 1 mie = 1
    jal mrettest
    j sretsetup

mrettest:
    la t1, mrettest_mepc
    csrrw t6, mepc, t1      # return to mrettest_mepc when done
    csrrw t6, mstatus, a0   # preload mstatus with argument
    mret                    # take the mret. Should go to mrettest_mepc and adjust mstatus
    nop                     # should be skipped

mrettest_mepc:
    li a0, 3
    ecall                   # make sure we return to machine mode
    csrrw t6, mstatus, s0   # restore mstatus
    ret

sretsetup:

/////////////////////////////////
// cp_sret
/////////////////////////////////
// Sweep executing sret in machine mode across cross-product of spp, mprv, tsr, spie, sie

    csrr s0, mstatus    # save mstatus

    li a0, 0x00000000   # tsr = 0, mprv = 0, spp = 0  spie = 0 sie = 0
    jal srettest
    li a0, 0x00000002   # tsr = 0, mprv = 0, spp = 0  spie = 0 sie = 1
    jal srettest
    li a0, 0x00000020   # tsr = 0, mprv = 0, spp = 0  spie = 1 sie = 0
    jal srettest
    li a0, 0x00000022   # tsr = 0, mprv = 0, spp = 0  spie = 1 sie = 1
    jal srettest
    li a0, 0x00000100   # tsr = 0, mprv = 0, spp = 1  spie = 0 sie = 0
    jal srettest
    li a0, 0x00000102   # tsr = 0, mprv = 0, spp = 1  spie = 0 sie = 1
    jal srettest
    li a0, 0x00000120   # tsr = 0, mprv = 0, spp = 1  spie = 1 sie = 0
    jal srettest
    li a0, 0x00000122   # tsr = 0, mprv = 0, spp = 1  spie = 1 sie = 1
    jal srettest
    li a0, 0x00020000   # tsr = 0, mprv = 1, spp = 0  spie = 0 sie = 0
    jal srettest
    li a0, 0x00020002   # tsr = 0, mprv = 1, spp = 0  spie = 0 sie = 1
    jal srettest
    li a0, 0x00020020   # tsr = 0, mprv = 1, spp = 0  spie = 1 sie = 0
    jal srettest
    li a0, 0x00020022   # tsr = 0, mprv = 1, spp = 0  spie = 1 sie = 1
    jal srettest
    li a0, 0x00020100   # tsr = 0, mprv = 1, spp = 1  spie = 0 sie = 0
    jal srettest
    li a0, 0x00020102   # tsr = 0, mprv = 1, spp = 1  spie = 0 sie = 1
    jal srettest
    li a0, 0x00020120   # tsr = 0, mprv = 1, spp = 1  spie = 1 sie = 0
    jal srettest
    li a0, 0x00020122   # tsr = 0, mprv = 1, spp = 1  spie = 1 sie = 1
    jal srettest
    li a0, 0x00400000   # tsr = 1, mprv = 0, spp = 0  spie = 0 sie = 0
    jal srettest
    li a0, 0x00400002   # tsr = 1, mprv = 0, spp = 0  spie = 0 sie = 1
    jal srettest
    li a0, 0x00400020   # tsr = 1, mprv = 0, spp = 0  spie = 1 sie = 0
    jal srettest
    li a0, 0x00400022   # tsr = 1, mprv = 0, spp = 0  spie = 1 sie = 1
    jal srettest
    li a0, 0x00400100   # tsr = 1, mprv = 0, spp = 1  spie = 0 sie = 0
    jal srettest
    li a0, 0x00400102   # tsr = 1, mprv = 0, spp = 1  spie = 0 sie = 1
    jal srettest
    li a0, 0x00400120   # tsr = 1, mprv = 0, spp = 1  spie = 1 sie = 0
    jal srettest
    li a0, 0x00400122   # tsr = 1, mprv = 0, spp = 1  spie = 1 sie = 1
    jal srettest
    li a0, 0x00420000   # tsr = 1, mprv = 1, spp = 0  spie = 0 sie = 0
    jal srettest
    li a0, 0x00420002   # tsr = 1, mprv = 1, spp = 0  spie = 0 sie = 1
    jal srettest
    li a0, 0x00420020   # tsr = 1, mprv = 1, spp = 0  spie = 1 sie = 0
    jal srettest
    li a0, 0x00420022   # tsr = 1, mprv = 1, spp = 0  spie = 1 sie = 1
    jal srettest
    li a0, 0x00420100   # tsr = 1, mprv = 1, spp = 1  spie = 0 sie = 0
    jal srettest
    li a0, 0x00420102   # tsr = 1, mprv = 1, spp = 1  spie = 0 sie = 1
    jal srettest
    li a0, 0x00420120   # tsr = 1, mprv = 1, spp = 1  spie = 1 sie = 0
    jal srettest
    li a0, 0x00420122   # tsr = 1, mprv = 1, spp = 1  spie = 1 sie = 1
    jal srettest
    j postsrettest

srettest:
    la t1, srettest_sepc
    csrrw t6, sepc, t1      # return to mrettest_mepc when done
    csrrw t6, mstatus, a0   # preload mstatus with argument
    sret                    # take the mret. Should go to mrettest_mepc and adjust mstatus
    nop                     # should be skipped
    nop                     # should be skipped

srettest_sepc:
    li a0, 3
    ecall                   # make sure we return to machine mode
    csrrw t6, mstatus, s0   # restore mstatus
    ret

postsrettest:

/////////////////////////////////
// walking 1s and 0s for each register, also 11 in 2-bit fields
/////////////////////////////////
// cp_medeleg_write_edges
// cp_mideleg_write_edges
// cp_mie_write_edges
// cp_mepc_write_edges
// cp_mtval_write_edges
// cp_mseccfg_write_edges
// cp_menvcfg_write_edges
// cp_mip_write_edges
// cp_mtvec_base_write_edges
// cp_mtvec_mode_write
// cp_mstatus_sxl_write
// cp_mstatus_uxl_write
/////////////////////////////////

#include "ZicsrM-Walk.h"

finished:
    j done
