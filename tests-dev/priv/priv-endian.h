///////////////////////////////////////////
// priv-endian.h
//
// Written: mbellido@hmc.edu 18 february 2025
// Adapted for to support both RV32 and RV64 mbellido@hmc.edu
//
// Purpose: has the functions to store and load for endianness
// Feed in: provide the endianness for the reads the writes and the privilege
//
// Copyright (C) 2021-23 Harvey Mudd College & Oklahoma State University
//
// SPDX-License-Identifier: Apache-2.0
//
// Registers used:
//   s1: a 1 in bit specific to SBE or UBE to set/clear mstatus, mstatush or status
//   s3: scratch address
//   s4: endianness for write test
//   s5: endianness for read test
//   s6: return address for calls to endiantest
//   s7: return address for calls to endianaccess
//   s8: stored endianness value
//   s10: 0 to set/clear sstatus.UBE  (any other value otherwisse )
//   s11: To switch back to running privilege mode once set/clear endianness
////////////////////////////////////////////////////////////////////////////////////////////////
// Library used for EndianU, EndianM and EndianS
// will store and load using the provided read and write endianness

endiantest: //Write to memory function
    # Try each size of stores with the write endianness, and then the loads with the read endianness
    mv s8, s4       # setEndianness(write)
    jal setendianness
    # Test storing bytes
    li t0, 0x01
    sb t0, 0(s3)
    li t0, 0x02
    sb t0, 1(s3)
    li t0, 0x03
    sb t0, 2(s3)
    li t0, 0x04
    sb t0, 3(s3)
    li t0, 0x05
    sb t0, 4(s3)
    li t0, 0x06
    sb t0, 5(s3)
    li t0, 0x07
    sb t0, 6(s3)
    li t0, 0x08
    sb t0, 7(s3)
    jal s7, endianaccess
    mv s8, s4       # setEndianness(write)
    jal setendianness
    li t0, 0x1112
    sh t0, 0(s3)
    li t0, 0x1314
    sh t0, 2(s3)
    li t0, 0x1516
    sh t0, 4(s3)
    li t0, 0x1718
    sh t0, 6(s3)
    jal s7, endianaccess
    mv s8, s4       # setEndianness(write)
    jal setendianness
    li t0, 0x21222324
    sw t0, 0(s3)
    li t0, 0x25262728
    sw t0, 4(s3)
    jal s7, endianaccess
    #ifdef __riscv_xlen
        #if __riscv_xlen == 64
            mv s8, s4       # setEndianness(write)
            jal setendianness
            li t0, 0x3132333435363738
            sd t0, 0(s3)            # sd only in RV64
            jal s7, endianaccess
        #endif
    #else
        ERROR: __riscv_xlen not defined
    #endif
    jr s6   # return (return address was stored in s6)



setendianness:  //function to set/clear the bits depending on the endianness specified in the covergroups
    beq s10, x0, onlysstatus3 //branch if endianness is given from sstatus (3 bc used by 3rd cp in endianS)

    // if s8 = 1, bigendian, otherwise littleendian
    li a0, 3         # a0 = 3, change to Machine mode
    ecall            # Make a system call to enter Machine mode
    beqz s8, littleendian      # little endian
    #ifdef __riscv_xlen
        #if __riscv_xlen == 64
            csrrs t6, mstatus, s1   # for RV64, set mstatus
        #elif __riscv_xlen == 32
            csrrs t6, mstatush, s1  # for RV32, set mstatush
        #endif
    #else
        ERROR: __riscv_xlen not defined
    #endif
    j change
littleendian:
    #ifdef __riscv_xlen
        #if __riscv_xlen == 64
            csrrc t6, mstatus, s1   # for RV64, clear mstatus
        #elif __riscv_xlen == 32
            csrrc t6, mstatush, s1  # for RV32, clear mstatush
        #endif
    #else
        ERROR: __riscv_xlen not defined
    #endif
    j change


onlysstatus3: //used for 3rd EndianS coverpoint: cp_sstatus_ube_endianness_*
              // endianness given in sstatus.UBE
    li a0, 1         # a0 = 1, change to supervisor mode ->to write to sstatus
    ecall            # Make a system call
    beqz s8, littleendian3      # little endian
    csrrs t6, sstatus, s1   # set sstatus.UBE
    j change
littleendian3:
    csrrc t6, sstatus, s1   # clear sstatus.UBE
    j change

change:
    // Switch privilege mode
    mv a0, s11       # s11 has privilege mode
    ecall            # Make a system call
    ret


endianaccess:
    // Try all the accesses to make sure they work for the endianness
     mv s8, s5   # setEndianness(read)
    jal setendianness
    lb  t3, 0(s3)
    lb  t3, 1(s3)
    lb  t3, 2(s3)
    lb  t3, 3(s3)
    lb  t3, 4(s3)
    lb  t3, 5(s3)
    lb  t3, 6(s3)
    lb  t3, 7(s3)
    lbu t3, 0(s3)
    lbu t3, 1(s3)
    lbu t3, 2(s3)
    lbu t3, 3(s3)
    lbu t3, 4(s3)
    lbu t3, 5(s3)
    lbu t3, 6(s3)
    lbu t3, 7(s3)
    lh  t3, 0(s3)
    lh  t3, 2(s3)
    lh  t3, 4(s3)
    lh  t3, 6(s3)
    lhu t3, 0(s3)
    lhu t3, 2(s3)
    lhu t3, 4(s3)
    lhu t3, 6(s3)
    lw  t3, 0(s3)
    lw  t3, 4(s3)
    #ifdef __riscv_xlen
        #if __riscv_xlen == 64
            lwu t3, 0(s3) # long loads for RV64
            lwu t3, 4(s3)
            ld t3, 0(s3)
        #endif
    #else
        ERROR: __riscv_xlen not defined
    #endif
    jr s7   # return (return address was stored in s7)
