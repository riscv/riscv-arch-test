#!/usr/bin/env python3
##################################
# illegalinstrtests.py
#
# David_Harris@hmc.edu 28 November 2024
# SPDX-License-Identifier: Apache-2.0
#
# Emit tests of illegal instructions
# Some fields are deterministic, others are swept over a range, and the rest are randomized
##################################

import os
import sys
from random import randint, seed


def gen(comment, template, length=32, exclusion=None):
    if exclusion is None:
        exclusion = []
    ebits = template.count("E")
    print("\n// " + comment + " with 2^" + str(ebits) + " exhaustive bits\n// Template: " + template)
    # Find out how many exhaustive bits are needed
    instr = ["0"] * length
    for j in range(0, 2**ebits):
        # Create string with exhaustive, random, and fixed bits
        e = ebits - 1
        for i in range(length):
            #            print("i = "+str(i)+", template[i] = "+template[i])
            if template[i] == "R":
                instr[i] = str(randint(0, 1))
            elif template[i] == "E":
                bit = j >> e
                instr[i] = str(bit & 1)
                e = e - 1
            elif template[i] == "0":
                instr[i] = "0"
            elif template[i] == "1":
                instr[i] = "1"
        instrstr = "".join(instr)

        anymatch = 0
        for exclude in exclusion:
            match = 1
            for i in range(length):
                if exclude[i] != "X" and exclude[i] != instrstr[i]:
                    match = 0
            anymatch = anymatch or match
        if length == 32:
            keyword = "word"
        elif length == 16:
            keyword = "hword"
        else:
            keyword = "length should be 16 or 32"
        if not anymatch:  # print the instruction if it isn't on exclusion list
            print("     ." + keyword + " 0b" + instrstr)
        else:
            print("#     ." + keyword + " 0b" + instrstr + " // excluded by " + str(exclusion))


# setup
seed(0)  # make tests reproducible
ARCH_VERIF = os.path.abspath(os.path.join(os.path.dirname(sys.argv[0]), "..", "..", ".."))
pathname = f"{ARCH_VERIF}/tests/priv/headers/ExceptionInstr-Tests.h"
outfile = open(pathname, "w")
sys.stdout = outfile
# gen("Illegal op2",  "RRRRRRRRRRRRRRRRRRRRRRRRR0001011") # custom-0
gen("Illegal op7", "RRRRRRRRRRRRRRRRRRRRRRRRR0011111")
# gen("Illegal op10", "RRRRRRRRRRRRRRRRRRRRRRRRR0101011") # custom-1
gen("Illegal op15", "RRRRRRRRRRRRRRRRRRRRRRRRR0111111")
gen("Illegal op21", "RRRRRRRRRRRRRRRRRRRRRRRRR1010111")
# gen("Illegal op22", "RRRRRRRRRRRRRRRRRRRRRRRRR1011011") # custom-2 / rv128
gen("Illegal op23", "RRRRRRRRRRRRRRRRRRRRRRRRR1011111")
gen("Illegal op26", "RRRRRRRRRRRRRRRRRRRRRRRRR1101011")
gen("Illegal op29", "RRRRRRRRRRRRRRRRRRRRRRRRR1110111")
# gen("Illegal op30", "RRRRRRRRRRRRRRRRRRRRRRRRR1111011") # custom-3 / rv128
gen("Illegal op31", "RRRRRRRRRRRRRRRRRRRRRRRRR1111111")
gen("cp_load", "RRRRRRRRRRRRRRRRREEERRRRR0000011")
gen("cp_fload", "RRRRRRRRRRRRRRRRREEERRRRR0000111")
gen("cp_fence_cbo", "RRRRRRRRRRRRRRRRREEERRRRR0001111")
gen("cp_cbo_immediate", "EEEEEEEEEEEE00000010000000001111")  # tie rs1 = 0 to avoid overwriting program on cbo.zero
gen("cp_cbo_rd", "00000000000RRRRRR010EEEEE0001111")
gen("cp_Itype", "EEEEEEEEEEEERRRRRE01RRRRR0010011")
gen("cp_llAItype", "RRRRRRRRRRRRRRRRREEERRRRR0010011")
gen("cp_aes64ks1i", "0011000EEEEERRRRR001RRRRR0010011")
gen("cp_IWtype", "RRRRRRRRRRRRRRRRREEERRRRR0011011")
gen("cp_IWshift", "EEEEEEERRRRRRRRRRE01RRRRR0011011")
gen("cp_store", "RRRRRRRRRRRR00000EEERRRRR0100011")  # use rs1 = 0 for stores to avoid overwriting program
gen("cp_fstore", "RRRRRRRRRRRR00000EEERRRRR0100111")  # use rs1 = 0 for stores to avoid overwriting program
gen("cp_atomic_funct3", "RRRRRRRRRRRR00000EEERRRRR0101111")  # use rs1 = 0 for atomics to avoid overwriting program
gen("cp_atomic_funct7", "EEEEERRRRRRR0000001ERRRRR0101111")  # use rs1 = 0 for atomics to avoid overwriting program
gen("cp_lrsc", "00010RREEEEE0000001ERRRRR0101111")
gen("cp_rtype", "EEEEEEERRRRRRRRRREEERRRRR0110011")
gen("cp_rwtype", "EEEEEEERRRRRRRRRREEERRRRR0111011")
gen("cp_ftype", "EEEEERRRRRRRRRRRREEERRRRR1010011")
gen("cp_fsqrt", "0101100EEEEERRRRRRRRRRRRR1010011")
gen("cp_fclass", "1110000EEEEERRRRR001RRRRR1010011")
gen("cp_fcvtif", "1100000EEE00RRRRR000RRRRR1010011")
gen("cp_fcvtif_fmt", "11000EE000EERRRRR000RRRRR1010011")
gen("cp_fcvtfi", "1101000EEER00RRRR000RRRRR1010011")
gen("cp_fcvtfi_fmt", "11010EE000EERRRRR000RRRRR1010011")
gen("cp_fcvtff", "0100000EEER00RRRR000RRRRR1010011")
gen("cp_fcvtff_fmt", "01000EEEEEEERRRRR000RRRRR1010011")
gen("cp_fmvif", "11100EEEEEEERRRRR000RRRRR1010011")
gen("cp_fmvfi", "11110EEEEEEERRRRR000RRRRR1010011")
gen("cp_fli", "11110EEEEEEERRRRR000RRRRR1010011")
gen("cp_fmvh", "11100EEEEEEERRRRR000RRRRR1010011")
gen("cp_fmvp", "10110EERRRRRRRRRR000RRRRR1010011")
gen("cp_fcvtmodwd", "11000EEEEEEERRRRR001RRRRR1010011")
gen("cp_branch2", "RRRRRRRRRRRRRRRRR010RRRRR1100011")
gen("cp_branch3", "RRRRRRRRRRRRRRRRR011RRRRR1100011")
gen("cp_jalr0", "RRRRRRRRRRRRRRRRREE1RRRRR1100111")
gen("cp_jalr1", "RRRRRRRRRRRRRRRRR010RRRRR1100111")
gen("cp_jalr2", "RRRRRRRRRRRRRRRRR100RRRRR1100111")
gen("cp_jalr3", "RRRRRRRRRRRRRRRRR110RRRRR1100111")
gen("cp_privileged_f3", "00000000000100000EEE000001110011")
gen(
    "cp_privileged_000",
    "EEEEEEEEEEEE00000000000001110011",
    32,
    [
        "1XXX11XXXXXX00000000000001110011",  # exclude custom system instructions
        "00X10000001000000000000001110011",  # exclude mret and sret because there is no trap to return from
        "00000000000000000000000001110011",  # exclude ecalls, may cause unwanted behavior based on random a0 value
        "00010000010100000000000001110011",
    ],
)  # exclude wfi because it may not wake up
gen(
    "cp_privileged_rd", "00000000000000000000EEEEE1110011", 32, ["00000000000000000000000001110011"]
)  # exclude ecalls, may cause unwanted behavior based on random a0 value
gen(
    "cp_privileged_rs2", "000000000000EEEEE000000001110011", 32, ["00000000000000000000000001110011"]
)  # exclude ecalls, may cause unwanted behavior based on random a0 value
gen("cp_reserved_fma", "RRRRRRRRRRRRRRRRREEERRRRR100EE11")  # various reserved_rm*_fma*
gen("cp_reserved_fence_fm_tso", "EEEE00000000RRRRR000RRRRR0001111")  # reserved fm and ts0 for fence instruction
gen("cp_reserved_fence_rs1", "00001111111100001000RRRRE0001111")  # reserved rs1 for fence instruction
gen("cp_reserved_fence_rd", "000011111111RRRRE000000010001111")  # reserved rd for fence instruction
outfile.close()

pathname = f"{ARCH_VERIF}/tests/priv/headers/ExceptionInstrCompressed-Tests.h"
outfile = open(pathname, "w")
sys.stdout = outfile
gen(
    "compressed00",
    "EEEEEEEEEEEEEE00",
    16,
    [
        "X01XXXXXXXXXXX00",  # skip c.fld and c.fsd  because they throw  exceptions for bad address
        "X10XXXXXXXXXXX00",  # skip c.lw and c.sw because they throw exceptions for bad address
        "10000XXXXXXXXX00",  # skip c.lbu, c.lh, c.lhu because they throw exceptions for bad address
        "100010XXXXXXXX00",  # skip c.sb because they throw exceptions for bad address
        "100011XXX0XXXX00",  # skip c.sh because they throw exceptions for bad address
    ],
)
gen(
    "compressed01",
    "EEEEEEEEEEEEEE01",
    16,
    [
        "101XXXXXXXXXXX01",  # skip c.j because it causes the test program to go to a random place
        "11XXXXXXXXXXXX01",  # skip c.beqz and c.bnez because they cause program to go to a random place
        "001XXXXXXXXXXX01",  # skip c.jr because it causes the test program to go to a random place
    ],
)
gen(
    "compressed10",
    "EEEEEEEEEEEEEE10",
    16,
    [
        "1000XXXXX0000010",  # skip c.jr because it causes the test program to go to a random place
        "1001XXXXX0000010",  # skip c.jalr because it causes the test program to go to a random place
        "X01XXXXXXXXXXX10",  # skip c.fldsp / c.fsdsp because they throw exceptions for bad address
        "X10XXXXXXXXXXX10",  # skip c.swsp and c.lwsp because it throws exceptions for bad address
        "1001000000000010",  # skip c.ebreak, which is legal and tested elsewhere
    ],
)

# The following memory instructions were excluded to prevent a bunch of bad addresses.  Test one for sanity.
print("\t.hword 0b0010000000000000 # test one c.fld")
print("\t.hword 0b1010000000000000 # test one c.fsd")
print("\t.hword 0b0100000000000000 # test one c.lw")
print("\t.hword 0b1100000000000000 # test one c.sw")
print("\t.hword 0b1000000000000000 # test one c.lbu")
print("\t.hword 0b1000010000000000 # test one c.lhu")
print("\t.hword 0b1000010001000000 # test one c.lh")
print("\t.hword 0b1000100000000000 # test one c.sb")
print("\t.hword 0b1000110000000000 # test one c.sh")
print("\t.hword 0b0100100000000010 # test one c.lwsp")
print("\t.hword 0b1100000000000010 # test one c.swsp")
print("\t.hword 0b0010000000000010 # test one c.fldsp")
print("\t.hword 0b1010000000000010 # test one c.fsdsp")

print("\t.hword 0b1000000000000010 # almost a c.jr but rs1 = 0 so should be illegal")
print(
    "#\t.hword 0b1001000000000010 # almost a c.jalr but rs1 = 0 so this is an ebreak instead, which is tested elsewhere"
)
outfile.close()
