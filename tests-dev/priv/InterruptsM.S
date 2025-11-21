///////////////////////////////////////////
// InterruptsM.S
//
// Written: David_Harris@hmc.edu 3 February 2025
//          Hjamal@hmc.edu       4 February 2025
//
// Purpose: Functional coverage tests for Interrupts in machine mode
//
// SPDX-License-Identifier: Apache-2.0
///////////////////////////////////////////

// General notes:
// Use csrrw/csrrs/csrrc t6, csr, rs1    when modifying a CSR to also check the old value.

#include "WALLY-init-lib.h"

main:
    jal reset_mtimecmp

/////////////////////////////////
// cp_trigger_mti
// With mstatus.MIE = {0/1}, and mie = 1s, use MTIMECMP to cause mip.MTIP to rise
/////////////////////////////////

cp_trigger_mti:
    li t0, -1               # all 1s
    csrrw t6, mie, t0       # enable all interrupts

    # mstatus.MIE = 0 should not take interrupt
    csrrci t6, mstatus, 8   # mstatus.MIE = 0
    jal cause_mtimer_interrupt_now
    jal reset_mtimecmp # reset mtimecmp to avoid premature interrupt in next test

    # mstatus.MIE = 1 should take interrupt
    csrrsi t6, mstatus, 8   # mstatus.MIE = 1
    jal cause_mtimer_interrupt_now # expecting timer interrupt, so interrupt handler will reset mtimecmp

/////////////////////////////////
// cp_trigger_msi
// With mstatus.MIE = {0/1}, and mie = 1s, use CLINT.MSIP to cause mip.MSIP to rise
/////////////////////////////////

cp_trigger_msi:
    li t0, -1               # all 1s
    csrrw t6, mie, t0       # enable all interrupts

    # mstatus.MIE = 0 should not take interrupt
    csrrci t6, mstatus, 8   # mstatus.MIE = 0
    jal set_msip
    jal reset_msip          # reset mip.MSIP since the trap handler will not reset it if no interrupt occurs

    # mstatus.MIE = 1 should take interrupt
    csrrsi t6, mstatus, 8   # mstatus.MIE = 1
    jal set_msip            # set mip.MSIP, expect interrupt

/////////////////////////////////
// cp_trigger_mei
// With mstatus.MIE = {0/1}, and mie = 1s, use PLIC or other EIC to cause mip.MEIP to rise
/////////////////////////////////

cp_trigger_mei:
    li t0, -1               # all 1s
    csrrw t6, mie, t0       # enable all interrupts

    # mstatus.MIE = 0 should not take interrupt
    csrrci t6, mstatus, 8   # mstatus.MIE = 0
    li a3, 0x10
    jal cause_external_interrupt_M
    jal reset_external_interrupts

    # mstatus.MIE = 1 should take interrupt
    csrrsi t6, mstatus, 8   # mstatus.MIE = 1
    li a3, 0x10
    jal cause_external_interrupt_M

/////////////////////////////////
// cp_trigger_sti
// With mstatus.MIE = {0/1}, and mie = 1s, write mip.STIP
/////////////////////////////////

cp_trigger_sti:
    li t0, -1               # all 1s
    csrrw t6, mie, t0       # enable all interrupts

    # mstatus.MIE = 0 should not take interrupt
    csrrci t6, mstatus, 8   # mstatus.MIE = 0
    li t0, 32               # 1 in bit 5
    csrrs t6, mip, t0
    csrrc t6, mip, t0       # reset mip.STIP since the trap handler will not reset it if no interrupt occurs

    # mstatus.MIE = 1 should take interrupt
    csrrsi t6, mstatus, 8   # mstatus.MIE = 1
    csrrs t6, mip, t0       # set mip.STIP, expect interrupt

/////////////////////////////////
// cp_trigger_ssi_mip
// With mstatus.MIE = {0/1}, and mie = 1s, write mip.SSIP
/////////////////////////////////

cp_trigger_ssi_mip:
    li t0, -1               # all 1s
    csrrw t6, mie, t0       # enable all interrupts

    # mstatus.MIE = 0 should not take interrupt
    csrrci t6, mstatus, 8   # mstatus.MIE = 0
    csrrsi t6, mip, 2
    csrrci t6, mip, 2       # reset mip.SSIP since the trap handler will not reset it if no interrupt occurs

    # mstatus.MIE = 1 should take interrupt
    csrrsi t6, mstatus, 8   # mstatus.MIE = 1
    csrrsi t6, mip, 2       # set mip.SSIP, expect interrupt

/////////////////////////////////
// cp_trigger_sei_plic
// With mstatus.MIE = {0/1}, and mie = 1s, use PLIC or other EIC to cause mip.SEIP to rise
/////////////////////////////////

cp_trigger_sei_plic:
    li t0, -1               # all 1s
    csrrw t6, mie, t0       # enable all interrupts

    # mstatus.MIE = 0 should not take interrupt
    csrrci t6, mstatus, 8   # mstatus.MIE = 0
    li a3, 0x10
    jal cause_external_interrupt_S
    jal reset_external_interrupts

    # mstatus.MIE = 1 should take interrupt
    csrrsi t6, mstatus, 8   # mstatus.MIE = 1
    li a3, 0x10
    jal cause_external_interrupt_S

/////////////////////////////////
// cp_trigger_sei_sie
// With mstatus.MIE = {0/1}, and mie = 1s, write mip.SEIP
/////////////////////////////////

cp_trigger_sei_sie:
    li t0, -1               # all 1s
    csrrw t6, mie, t0       # enable all interrupts

    # mstatus.MIE = 0 should not take interrupt
    csrrci t6, mstatus, 8   # mstatus.MIE = 0
    li t0, 512              # 1 in bit 9
    csrrs t6, mip, t0       # set mip.SEIP
    csrrc t6, mip, t0       # reset mip.SEIP since the trap handler will not reset it if no interrupt occurs

    # mstatus.MIE = 1 should take interrupt
    csrrsi t6, mstatus, 8   # mstatus.MIE = 1
    csrrs t6, mip, t0       # set mip.SEIP, expect interrupt

/////////////////////////////////
// cp_interrupts
// Cross of mstatus.MIE = {0/1}, mtvec.MODE = 00, 3 walking 1s in mip.MTIP/MSIP/MEIP,
// 3 walking 1s in mie.MTIE/MSIE/MEIE (2 x 3 x 3 bins)
/////////////////////////////////

cp_interrupts:

    li s0, 1 # iterate through mstatus.MIE values 0-1

    csrrci t6, mtvec, 3 # mtvec.MODE = 00

    for_mstatus:

        bnez s0, set_mstatus
        csrrci t6, mstatus, 8   # if s0 == 0, clear mstatus.MIE
        j cross_interrupts

        set_mstatus:
        csrrsi t6, mstatus, 8 # if s0 == 1, set mstatus.MIE

        cross_interrupts:
        jal cross_interrupts_m_EP

        addi s0, s0, -1
        beqz s0, for_mstatus # iterate through mstatus.MIE values (1-0)

/////////////////////////////////
// cp_vectored
// Cross of mtvec.MODE = 01, mstatus.MIE=1, all 3 of mie.MTIE/MSIE/MEIE,
// 3 walking 1s in mip.MTIP/MSIP/MEIP (3 bins)
/////////////////////////////////

cp_vectored:

    csrrci t6, mtvec, 3
    csrrsi t6, mtvec, 1 # mtvec.MODE = 01

    csrrsi t6, mstatus, 8 # mstatus.MIE = 1
    csrrw t6, mie, zero     # clear all interrupt enables

    li s1, 0x0888
    csrrs t6, mie, s1       # set mie.MEIE/MTIE/MSIE

    jal raise_interrupts_m

/////////////////////////////////
// cp_priority
// With mstatus.MIE = 1, write cross product of 8 values of mie.{MSIE/MTIE/MEIE}
// with hardware events giving the 8 values of mip.{MSIP/MTIP/MEIP} and check that
// the proper interrupt occurs (8 x 8 bins)
/////////////////////////////////

cp_priority:

    csrrsi t6, mstatus, 8 # mstatus.MIE = 1

    li s1, 7

    for_mie_priority:

        csrrw t6, mie, zero # clear all interrupt enables to start fresh

        andi t0, s1, 4 # check bit 2
        slli t0, t0, 9 # set mie.MEIE based on bit 2 value
        mv s3, t0

        andi t0, s1, 2  # check bit 1
        slli t0, t0, 6  # set mie.MTIE based on bit 1 value
        or s3, s3, t0

        andi t0, s1, 1  # check bit 0
        slli t0, t0, 3  # set mie.MSIE based on bit 1 value
        or s3, s3, t0

        li s2, 7

        for_mip_priority:

            case2_priority:
                andi t0, s2, 4  # check bit 2
                beqz t0, case1_priority # set mie.MEIP based on s2 bit 2 value
                jal cause_external_interrupt_M

            case1_priority:
                andi t0, s2, 2  # check bit 1
                beqz t0, case0_priority # set mie.MTIP based on s2 bit 1 value
                jal cause_mtimer_interrupt_now

            case0_priority:
                andi t0, s2, 1  # check bit 0
                beqz t0, case_end_priority # set mie.MSIP based on s2 bit 0 value
                jal set_msip

            case_end_priority:

                csrrs t6, mie, s3   # write to enable certain machine interrupts, should trigger highest-priority pending interrupt
                csrrc t6, mie, s3   # write to disable those machine interrupts before next test case

                # add in resets in case s1 == 0
                jal reset_external_interrupts
                jal reset_mtimecmp
                jal reset_msip

                addi s2, s2, -1
                bge s2, zero, for_mip_priority

        addi s1, s1, -1
        bge s1, zero, for_mie_priority

/////////////////////////////////
// cp_wfi
// Cross Product of mstatus.MIE = {0/1}, mstatus.SIE = {0/1}, mstatus.TW = {0/1}, mie.MTIE = 1
// Set MTIMECMP = TIME + 0x100 to interrupt in the future
// WFI instruction
/////////////////////////////////

cp_wfi:

    li t0, 0x080
    csrrw t6, mie, t0 # mie.MTIE = 1

    li s2, 7

    for_wfi:

        li t0, 0x20000A
        csrrc t6, mstatus, t0 # clear mstatus.TW, MIE, SIE

        case_MIE:
            andi t0, s2, 4  # check bit 2
            beqz t0, case_SIE # set mstatus.MIE based on s2 bit 2 value
            csrrsi t6, mstatus, 8 # set mstatus.MIE

        case_SIE:
            andi t0, s2, 2  # check bit 1
            beqz t0, case_TW # set mstatus.SIE based on s2 bit 1 value
            csrrsi t6, mstatus, 2 # set mstatus.SIE

        case_TW:
            andi t0, s2, 1  # check bit 0
            beqz t0, case_end_wfi # set mstatus.TW based on s2 bit 0 value
            li t0, 0x200000
            csrrs t6, mstatus, t0 # set mstatus.TW

        case_end_wfi:
            jal cause_mtimer_interrupt_soon
            wfi
            addi s2, s2, -1
            bge s2, zero, for_wfi

j done
