#!/usr/bin/env python3
##################################
# csrtests.py
#
# David_Harris@hmc.edu 13 October 2024
# SPDX-License-Identifier: Apache-2.0
#
# Emit tests of all supported CSRs for Zicsr functional coverage tests
##################################

import os
import sys
from random import randint, seed


def printwalk(regs):
    for reg in regs:
        if reg == "satp": # satp requires a special case to avoid accidentally turning on vmem
            continue
        if "#ifdef" in reg or "#endif" in reg:
                print(reg)
                continue
        print("\n// Testing walking zeros and ones for CSR " + reg)
        print("\tcsrr s0, " + reg + "\t# save CSR")
        #print("\tRVTEST_SIGWRITE(x3, s0)\t# save CSR to Signature")
        print("\tli t1, -1           # all 1s")
        print("\tli t0, 1            # 1 in lsb")
        print("1:  csrrc t6, " + reg + ", t1    # clear all bits")
        #print("\tRVTEST_SIGWRITE(x3, t6)\t# save CSR to Signature")
        print("\tcsrrs t6, " + reg + ", t0    # set walking 1")
        #print("\tRVTEST_SIGWRITE(x3, t6)\t# save CSR to Signature")
        print("\tslli t0, t0, 1      # walk the 1")
        print("\tbnez t0, 1b         # repeat until all bits are walked")
        print("\tli t0, 1            # 1 in lsb")
        print("1:  csrrs t6, " + reg + ", t1    # set all bits")
        #print("\tRVTEST_SIGWRITE(x3, t6)\t# save CSR to Signature")
        print("\tcsrrc t6, " + reg + ", t0    # clear walking 1")
        #print("\tRVTEST_SIGWRITE(x3, t6)\t# save CSR to Signature")
        print("\tslli t0, t0, 1      # walk the 1")
        print("\tbnez t0, 1b         # repeat until all bits are walked")
        print("\tcsrrw t6, " + reg + ", s0    # restore CSR")
        #print("\tRVTEST_SIGWRITE(x3, t6)\t# save CSR to Signature")


def csrwalk(pathname, regs, hregs):
    outfile = open(pathname, "w")
    sys.stdout = outfile
    printwalk(regs)
    if hregs:
        print("\n#if __riscv_xlen == 32")
        printwalk(hregs)
        print("#endif")
    outfile.close()


def csrtests(pathname, skipCsrs):
    outfile = open(pathname, "w")
    sys.stdout = outfile
    for i in range(4096):
        if i in skipCsrs:
            continue  # skip custom CSRs
        reg1 = randint(1, 31)
        reg2 = randint(1, 31)
        reg3 = randint(1, 31)
        while reg2 == reg1:
            reg2 = randint(1, 31)
        while reg3 == reg1 or reg3 == reg2:
            reg3 = randint(1, 31)
        reg1 = str(reg1)
        reg2 = str(reg2)
        reg3 = str(reg3)
        ih = hex(i)

        print("\n// Testing CSR " + ih)
        print("\tcsrr x" + str(reg1) + ", " + ih + "\t// Read CSR")
        print("\tli x" + reg2 + ", -1")
        print("\tcsrrw x" + reg3 + ", " + ih + ", x" + reg2 + "\t// Write all 1s to CSR")
        print("\tcsrrw x" + reg3 + ", " + ih + ", x0\t// Write all 0s to CSR")
        print("\tcsrrs x" + reg3 + ", " + ih + ", x" + reg2 + "\t// Set all CSR bits")
        print("\tcsrrc x" + reg3 + ", " + ih + ", x" + reg2 + "\t// Clear all CSR bits")
        print("\tcsrrw x" + reg3 + ", " + ih + ", x" + reg1 + "\t// Restore CSR")
    outfile.close()


def readandswitchmode(regs, mode):
    # helper function to switch modes when reading csr
    if mode in ("U", "S"):
        mode_num = 0 if mode == "U" else 1  # convert 'U' to 0, 'S' to 1
        print(f"\tli a0, {mode_num}     # switch to {mode}-mode")
        print(f"\tecall             # switch to {mode}-mode")
        for reg in regs:
            if reg == "satp":  # Skip satp to avoid enabling virtual memory
                continue
            if "#ifdef" in reg or "#endif" in reg:
                print(reg)
                continue
            print(f"\tcsrr t2, {reg} # read from {reg} in {mode}-mode")
        print("\tli a0, 3")
        print("\tecall             # switch back to M-mode")
    else:
        for reg in regs:
            if reg == "satp":  # Skip satp to avoid enabling virtual memory
                continue
            if "#ifdef" in reg or "#endif" in reg:
                print(reg)
                continue
            print(f"\tcsrr t2, {reg} # read from {reg} in M-mode")


def mwalk(csr, regs, mode):
    if csr == "scounteren":
        print("\nli t0, -1")
        print("\tcsrw mcounteren, t0  # enable all counters in M-mode")
    print("\n// Save the original value of csr")
    print(f"\tcsrr s0, {csr}  # save original csr value")
    print("\tli t1, -1        # mask of all 1s")
    print("\tli t0, 1         # initial bit position")
    print("\n// Walk a single 1 in M-mode")  # walk 1
    print(f"\t1: csrrc t6, {csr}, t1  # clear all bits")
    print(f"\tcsrrs t6, {csr}, t0  # set current bit")
    readandswitchmode(regs, mode)
    print("\tslli t0, t0, 1   # shift to next bit")
    print("\tbnez t0, 1b      # loop until all bits walked")
    print(f"\n// Walk a single 0 in M-mode and read from registers in {mode}-mode")  # walk 0
    print("\tli t0, 1         # reset bit position")
    print(f"\t2: csrrs t6, {csr}, t1  # set all bits")
    print(f"\tcsrrc t6, {csr}, t0  # clear current bit")
    readandswitchmode(regs, mode)
    print("\tslli t0, t0, 1   # shift to next bit")
    print("\tbnez t0, 2b      # loop until all bits walked")
    print("\n// Restore the original value of csr")
    print(f"\tcsrrw t6, {csr}, s0  # restore original csr value")


def counterenwalk(pathname, csr, regs, hregs, mode):
    with open(pathname, "w") as outfile:
        sys.stdout = outfile
        mwalk(csr, regs, mode)
        if hregs:
            print("\n#if __riscv_xlen == 32")
            mwalk(csr, hregs, mode)
            print("#endif")
    outfile.close()


def mwalkdouble(csr1, csr2, regs, mode):
    print("\n// Save the original values of csrs")
    print(f"\tcsrr s0, {csr1} \t# save {csr1}")
    print(f"\tcsrr s1, {csr2} \t# save {csr2}")
    print("\tli t1, -1           # all 1s")
    print("\tli t0, 1            # 1 in lsb")
    print("\n// Walk a single 1 in both CSRs simultaneously")
    print(f"\t1: csrrc t6, {csr1}, t1    # clear all bits in first csr")
    print(f"\tcsrrc t6, {csr2}, t1    # clear all bits in second csr")
    print(f"\tcsrrs t6, {csr1}, t0    # set walking 1 in first csr")
    print(f"\tcsrrs t6, {csr2}, t0    # set walking 1 in second csr")
    readandswitchmode(regs, mode)
    print("\tslli t0, t0, 1      # walk the 1 to the next bit")
    print("\tbnez t0, 1b         # repeat until all bits are walked")
    print(f"\n// Walk a single 0 in both CSRs and read from counter/counterh in {mode}-mode")
    print("\tli t0, 1            # reset t0 to 1")
    print(f"\t2: csrrs t6, {csr1}, t1    # set all bits in first csr")
    print(f"\tcsrrs t6, {csr2}, t1    # set all bits in second csr")
    print(f"\tcsrrc t6, {csr1}, t0    # clear walking 0 in first csr")
    print(f"\tcsrrc t6, {csr2}, t0    # clear walking 0 in second csr")
    readandswitchmode(regs, mode)
    print("\tslli t0, t0, 1      # walk the 0 to the next bit")
    print("\tbnez t0, 2b         # repeat until all bits are walked")
    print("\n// Restore the original values of csrs")
    print(f"\tcsrrw t6, {csr1}, s0    # restore first csr")
    print(f"\tcsrrw t6, {csr2}, s1    # restore second csr")


def counterenwalkdouble(pathname, csr1, csr2, regs, hregs, mode):
    with open(pathname, "w") as outfile:
        sys.stdout = outfile
        mwalkdouble(csr1, csr2, regs, mode)
        if hregs:
            print("\n#if __riscv_xlen == 32")
            mwalkdouble(csr1, csr2, hregs, mode)
            print("#endif")
        sys.stdout = sys.__stdout__


def cp_vsetvl_i_rd_nx0_rs1_x0(pathname):
    with open(pathname, "w") as outfile:
        sys.stdout = outfile
        sews = ["8", "16", "32", "64"]
        lmuls = ["1", "2", "4", "8", "f2", "f4", "f8"]

        print("// Tests for cp_vsetvl_i_rd_nx0_rs1_x0")
        for sew in sews:
            for lmul in lmuls:
                print("\t// SEW = " + sew + ", LMUL = " + lmul)
                print("\tvsetvli  x8, x0, e" + sew + ", m" + lmul + ", tu, mu")
                print("\tcsrr     x1, vl")
                #print("\tRVTEST_SIGUPD(x3, x1)")
                print()

        for i in range(32):
            if i not in [4, 12, 20, 28]:  # LMUL = 3'b100 is reserved
                ih = hex(i)
                print(f"\t// vtype[7:0] = 0_0_{format(i >> 3, '03b')}_{format(i & 0b111, '03b')}")
                print("\tli       t2, " + str(ih))
                print("\tcsrr     x1, vl")
                #print("\tRVTEST_SIGUPD(x3, x1)")
                print()
    outfile.close()


def cp_vsetivli_avl_edges(pathname):
    with open(pathname, "w") as outfile:
        sys.stdout = outfile
        sews = ["8", "16", "32", "64"]

        print("// Tests for cp_vsetivli_avl_edges")
        for sew in sews:
            for i in range(32):
                print("\t// SEW = " + sew + " and LMUL = 1")
                print("\tvsetivli x8, " + str(i) + ", e" + sew + ", m1, tu, mu")
                print("\tcsrr     x1, vl")
                #print("\tRVTEST_SIGUPD(x3, x1)")
                print()
    outfile.close()


# setup
seed(0)  # make tests reproducible

# generate repetitive assembly language tests

# writable registers to test with walking 1s and 0s
mregs = [
    "mstatus",
    "mcause",
    "misa",
    "medeleg",
    "mideleg",
    "mie",
    "mtvec",
    "mcounteren",
    "mscratch",
    "mepc",
    "mtval",
    "mip",
    "menvcfg",
    "mseccfg",
]
mregsh = ["mstatush", "mseccfgh", "menvcfgh", "0x312"]  # 0x312 is medelegeh; RV64 compiler isn't accepting the name
sregs = [
    "sstatus",
    "scause",
    "sie",
    "stvec",
    "scounteren",
    "senvcfg",
    "sscratch",
    "sepc",
    "stval",
    "sip",
    "0x120",
]  # 0x120 is scountinhibit, currently unsupported
fregs = ["fflags", "frm", "fcsr"]
vregs = [
    "vtype",
    "vlenb",
    "vl",
    "vxrm",
    "vxsat",
    "vcsr",
]  # removed (, "vstart") since it is buggy in sail and caused signature mismatch

mcntrs = [
    "mcycle",
    "mcountinhibit",
    "minstret",
    "#ifdef ZIHPM_SUPPORTED",
    "mhpmcounter3",
    "mhpmcounter4",
    "mhpmcounter5",
    "mhpmcounter6",
    "mhpmcounter7",
    "mhpmcounter8",
    "mhpmcounter9",
    "mhpmcounter10",
    "mhpmcounter11",
    "mhpmcounter12",
    "mhpmcounter13",
    "mhpmcounter14",
    "mhpmcounter15",
    "mhpmcounter16",
    "mhpmcounter17",
    "mhpmcounter18",
    "mhpmcounter19",
    "mhpmcounter20",
    "mhpmcounter21",
    "mhpmcounter22",
    "mhpmcounter23",
    "mhpmcounter24",
    "mhpmcounter25",
    "mhpmcounter26",
    "mhpmcounter27",
    "mhpmcounter28",
    "mhpmcounter29",
    "mhpmcounter30",
    "mhpmcounter31",
    "mhpmevent3",
    "mhpmevent4",
    "mhpmevent5",
    "mhpmevent6",
    "mhpmevent7",
    "mhpmevent8",
    "mhpmevent9",
    "mhpmevent10",
    "mhpmevent11",
    "mhpmevent12",
    "mhpmevent13",
    "mhpmevent14",
    "mhpmevent15",
    "mhpmevent16",
    "mhpmevent17",
    "mhpmevent18",
    "mhpmevent19",
    "mhpmevent20",
    "mhpmevent21",
    "mhpmevent22",
    "mhpmevent23",
    "mhpmevent24",
    "mhpmevent25",
    "mhpmevent26",
    "mhpmevent27",
    "mhpmevent28",
    "mhpmevent29",
    "mhpmevent30",
    "mhpmevent31",
    "#endif",
]
mcntrsh = [
    "mcycleh",
    "minstreth",
    "#ifdef ZIHPM_SUPPORTED",
    "mhpmcounter3h",
    "mhpmcounter4h",
    "mhpmcounter5h",
    "mhpmcounter6h",
    "mhpmcounter7h",
    "mhpmcounter8h",
    "mhpmcounter9h",
    "mhpmcounter10h",
    "mhpmcounter11h",
    "mhpmcounter12h",
    "mhpmcounter13h",
    "mhpmcounter14h",
    "mhpmcounter15h",
    "mhpmcounter16h",
    "mhpmcounter17h",
    "mhpmcounter18h",
    "mhpmcounter19h",
    "mhpmcounter20h",
    "mhpmcounter21h",
    "mhpmcounter22h",
    "mhpmcounter23h",
    "mhpmcounter24h",
    "mhpmcounter25h",
    "mhpmcounter26h",
    "mhpmcounter27h",
    "mhpmcounter28h",
    "mhpmcounter29h",
    "mhpmcounter30h",
    "mhpmcounter31h",
    "mhpmevent3h",
    "mhpmevent4h",
    "mhpmevent5h",
    "mhpmevent6h",
    "mhpmevent7h",
    "mhpmevent8h",
    "mhpmevent9h",
    "mhpmevent10h",
    "mhpmevent11h",
    "mhpmevent12h",
    "mhpmevent13h",
    "mhpmevent14h",
    "mhpmevent15h",
    "mhpmevent16h",
    "mhpmevent17h",
    "mhpmevent18h",
    "mhpmevent19h",
    "mhpmevent20h",
    "mhpmevent21h",
    "mhpmevent22h",
    "mhpmevent23h",
    "mhpmevent24h",
    "mhpmevent25h",
    "mhpmevent26h",
    "mhpmevent27h",
    "mhpmevent28h",
    "mhpmevent29h",
    "mhpmevent30h",
    "mhpmevent31h",
    "#endif",
]
cntrs = [
    "cycle",
    "time",
    "instret",
    "#ifdef ZIHPM_SUPPORTED",
    "hpmcounter3",
    "hpmcounter4",
    "hpmcounter5",
    "hpmcounter6",
    "hpmcounter7",
    "hpmcounter8",
    "hpmcounter9",
    "hpmcounter10",
    "hpmcounter11",
    "hpmcounter12",
    "hpmcounter13",
    "hpmcounter14",
    "hpmcounter15",
    "hpmcounter16",
    "hpmcounter17",
    "hpmcounter18",
    "hpmcounter19",
    "hpmcounter20",
    "hpmcounter21",
    "hpmcounter22",
    "hpmcounter23",
    "hpmcounter24",
    "hpmcounter25",
    "hpmcounter26",
    "hpmcounter27",
    "hpmcounter28",
    "hpmcounter29",
    "hpmcounter30",
    "hpmcounter31",
    "#endif",
]
cntrsh = [
    "cycleh",
    "timeh",
    "instreth",
    "#ifdef ZIHPM_SUPPORTED",
    "hpmcounter3h",
    "hpmcounter4h",
    "hpmcounter5h",
    "hpmcounter6h",
    "hpmcounter7h",
    "hpmcounter8h",
    "hpmcounter9h",
    "hpmcounter10h",
    "hpmcounter11h",
    "hpmcounter12h",
    "hpmcounter13h",
    "hpmcounter14h",
    "hpmcounter15h",
    "hpmcounter16h",
    "hpmcounter17h",
    "hpmcounter18h",
    "hpmcounter19h",
    "hpmcounter20h",
    "hpmcounter21h",
    "hpmcounter22h",
    "hpmcounter23h",
    "hpmcounter24h",
    "hpmcounter25h",
    "hpmcounter26h",
    "hpmcounter27h",
    "hpmcounter28h",
    "hpmcounter29h",
    "hpmcounter30h",
    "hpmcounter31h",
    "#endif",
]

uCsrSkip = list(range(0x800, 0x900)) + list(range(0xCC0, 0xD00))
sCsrSkip = (
    list(range(0x5C0, 0x600))
    + list(range(0x6C0, 0x700))
    + list(range(0x9C0, 0xA00))
    + list(range(0xAC0, 0xB00))
    + list(range(0xDC0, 0xE00))
    + list(range(0xEC0, 0xF00))
)
mCsrSkip = (
    list(range(0x7A0, 0x7B0)) + list(range(0x7C0, 0x800)) + list(range(0xBC0, 0xC00)) + list(range(0xFC0, 0x1000))
)

ARCH_VERIF = os.path.abspath(os.path.join(os.path.dirname(sys.argv[0]), "..", "..", ".."))

pathname = f"{ARCH_VERIF}/tests/priv/headers/SsstrictSm-CSR-Tests.h"
csrtests(pathname, mCsrSkip + sCsrSkip + uCsrSkip)

pathname = f"{ARCH_VERIF}/tests/priv/headers/SsstrictS-CSR-Tests.h"
csrtests(pathname, sCsrSkip + uCsrSkip + [0x180])  # 0x180 is the satp register

pathname = f"{ARCH_VERIF}/tests/priv/headers/SsstrictU-CSR-Tests.h"
csrtests(pathname, uCsrSkip)

pathname = f"{ARCH_VERIF}/tests/priv/headers/ZicsrS-Walk.h"
csrwalk(pathname, sregs, [])

pathname = f"{ARCH_VERIF}/tests/priv/headers/ZicsrUF-Walk.h"
csrwalk(pathname, fregs, [])

pathname = f"{ARCH_VERIF}/tests/priv/headers/Zicntr-MWalkU.h"
counterenwalk(pathname, "mcounteren", cntrs, cntrsh, "U")

pathname = f"{ARCH_VERIF}/tests/priv/headers/Zicntr-MWalkM.h"
counterenwalk(pathname, "mcounteren", cntrs, cntrsh, "M")

pathname = f"{ARCH_VERIF}/tests/priv/headers/Zicntr-MWalkS.h"
counterenwalk(pathname, "mcounteren", cntrs, cntrsh, "S")

pathname = f"{ARCH_VERIF}/tests/priv/headers/Zicntr-MSWalkU.h"
counterenwalkdouble(pathname, "scounteren", "mcounteren", cntrs, cntrsh, "U")

pathname = f"{ARCH_VERIF}/tests/priv/headers/Zicntr-SWalkM.h"
counterenwalk(pathname, "scounteren", cntrs, cntrsh, "M")

pathname = f"{ARCH_VERIF}/tests/priv/headers/Zicntr-SWalkS.h"
counterenwalk(pathname, "scounteren", cntrs, cntrsh, "S")

pathname = f"{ARCH_VERIF}/tests/priv/headers/Zicntr-SWalkU.h"
counterenwalk(pathname, "scounteren", cntrs, cntrsh, "U")

pathname = f"{ARCH_VERIF}/tests/priv/headers/ZicsrV-vsetvl-Tests.h"
cp_vsetvl_i_rd_nx0_rs1_x0(pathname)

pathname = f"{ARCH_VERIF}/tests/priv/headers/ZicsrV-vsetivli-Tests.h"
cp_vsetivli_avl_edges(pathname)
