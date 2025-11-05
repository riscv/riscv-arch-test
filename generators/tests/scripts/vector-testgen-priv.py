#!/usr/bin/env python3
##################################
# vector-testgen-priv.py
#
# Georgia Tai ytai@hmc.edu 26 June 2025
# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
#
# Generate directed privilaged tests for functional coverage of the vector extension
##################################

##################################
# libraries
##################################
import filecmp
import math
import os
from random import randint, seed

import vector_testgen_common as common
from vector_testgen_common import (
    ARCH_VERIF,
    flen,
    genVMaskCorners,
    getBaseSuiteTestCount,
    getInstructionArguments,
    getLengthLmul,
    getLengthSuiteTestCount,
    getSigSpace,
    insertTemplate,
    loadScalarReg,
    maxVLEN,
    myhash,
    prepVstart,
    randomizeMask,
    randomizeVectorInstructionData,
    readTestplans,
    setExtension,
    setXlen,
    whole_register_move,
    writeVecTest,
)


def writeLine(argument: str, comment = ""):
    tab_over_distance = 50

    argument = str(argument)

    if comment != "":
        padding = max(0, tab_over_distance - len(argument))
        comment = " " * padding + str(comment)

    f.write(argument + comment +"\n")

#####################################       test for each coverpoint      #####################################

def make_vill(instruction):
    description = "cp_vill"
    instruction_data = randomizeVectorInstructionData(instruction, "SEWMIN", getBaseSuiteTestCount(), vd = 8, vs2 = 16, vs1 = 24, rd = 5, rs2 = 6, rs1 = 7,
                                                      vd_val_pointer = "vector_random", vs2_val_pointer = "vector_random", vs1_val_pointer = "vector_random")

    writePrivTestPrep(description, instruction)
    writeLine("vsetivli  x8, 1, e64, mf8, tu, mu",  "# SEW = 64 and LMUL = 1/8, illegal config which sets vill = 1")
    writePrivTestLine(instruction, instruction_data)


def make_vstart(instruction, sew, maxlmul = 8):
    vstartvals = ["one", "vlmaxm1", "vlmaxd2", "random"]
    for vstartval in vstartvals:
        lmul = 2 ** randint(1, int(math.log2(maxlmul))) # pick random integer LMUL to ensure that coverpoints are hit

        maskval = randomizeMask(instruction)
        no_overlap = [['vs1', 'v0'], ['vs2', 'v0'], ['vd', 'v0']] if maskval is not None else None

        description = f"cp_vstart (vstart = {vstartval})"
        instruction_data = randomizeVectorInstructionData(instruction, "SEWMIN", getLengthSuiteTestCount(), suite = "length", lmul = lmul,
                                                          vd = 8, vs2 = 16, vs1 = 24, rd = 5, rs2 = 6, rs1 = 7,
                                                          vd_val_pointer = "vector_random", vs2_val_pointer = "vector_random", vs1_val_pointer = "vector_random",
                                                          additional_no_overlap=no_overlap)

        writePrivTestPrep(description, instruction, lmul = lmul, vl = "vlmax")
        prepVstart(vstartval)
        writePrivTestLine(instruction, instruction_data, lmul = lmul, vl = "vlmax", maskval = maskval)

def make_vstart_gt_vl(instruction):
    randvl = randint(1, maxVLEN)
    randvstart = randint(1, maxVLEN)
    description = "cp_vstart_gt_vl"
    instruction_data = randomizeVectorInstructionData(instruction, "SEWMIN", getBaseSuiteTestCount(), vd = 8, vs2 = 16, vs1 = 24, rd = 5, rs2 = 6, rs1 = 7,
                                                      vd_val_pointer = "vector_random", vs2_val_pointer = "vector_random", vs1_val_pointer = "vector_random")

    writePrivTestPrep(description, instruction, lmul = 4, vl = "vlmax", vstart = True)
    writeLine(f"li a0, {randvl}",            "# load random number to a0, place holder for vl")
    writeLine(f"li a0, {randvstart}",        "# load random number to a1, place holder for vstart")
    writeLine("jal cp_vstart_gt_vl_setup",  "# jump to set up vstart and vl for the test")
    writePrivTestLine(instruction, instruction_data, vl = "vlmax", lmul = 4)

#####################################           test generation           #####################################

def makeTest(coverpoints, instruction):
    writeLine("\n")
    writeLine("///////////////////////////////////////////")
    writeLine(f"// ExceptionsV tests for {instruction}")
    writeLine("///////////////////////////////////////////")
    for coverpoint in coverpoints:
        # produce a deterministic seed for repeatable random numbers distinct for each instruction and coverpoint
        testname = instruction + coverpoint
        hashval = myhash(testname)
        seed(hashval)

        if   ((coverpoint in ['RV32', 'RV64', 'EFFEW8', 'EFFEW16', 'EFFEW32', 'EFFEW64']) or
              ("sample" in coverpoint))                      : pass
        elif (coverpoint == "cp_vill")                       : make_vill(instruction)
        elif (coverpoint == "cp_vstart")                     : make_vstart(instruction)
        elif (coverpoint == "cp_vstart_gt_vl")               : make_vstart_gt_vl(instruction)
        else:
            print("Warning: " + coverpoint + " not implemented yet for " + instruction)

def writePrivTestPrep(description, instruction, lmul = 1, vl = 1, vstart = False):
    instruction_arguments = getInstructionArguments(instruction)

    writeLine("\n# Testcase " + str(description))

    if (vstart):
        writeLine("csrw vstart, 0",                        "# initialize vstart  = 0 for preparing")

    if (vl == "vlmax"):
      writeLine(f"vsetvli x8, x0, SEWSIZE, m{lmul}, tu, mu",  "# initialize vl = VLMAX, LMUL = 1, SEW = SEWMIN")
    else:
      writeLine(f"vsetivli x8, {vl}, SEWSIZE, m{lmul}, tu, mu",  f"# initialize vl = {vl}, LMUL = 1, SEW = SEWMIN")

    writeLine("la x2, random_mask_0",                      "# load a random vector ") # TODO: change back to vector_random
    if ("vd" in instruction_arguments):
        writeLine("VLESEWMIN v8, (x2)",                    "# load to initialize vd (v8) ")
    if ("vs2" in instruction_arguments):
        writeLine("VLESEWMIN v16, (x2)",                   "# load to initialize vs2 (v16)")
    if ("vs1" in instruction_arguments):
        writeLine("VLESEWMIN v24, (x2)",                   "# load to initialize vs1 (v24)")

def writePrivTestLine(instruction, instruction_data, vl=1, lmul=1, maskval=None):
    instruction_arguments = getInstructionArguments(instruction)
    [vector_register_data, scalar_register_data, floating_point_register_data, imm_val] = instruction_data

    testline = instruction + " "

    for argument in instruction_arguments:
        if   argument == 'vm':
            if maskval is not None:
                testline = testline + "v0.t"
            else:
                testline = testline[:-2] # remove the ", " since theres no argument
        elif argument == 'v0':
            testline = testline + "v0"
        elif argument == 'imm':
            testline = testline + f"{imm_val}"
        elif argument[0] == 'v':
            testline = testline + f"v{vector_register_data[argument]['reg']}"
        elif argument[0] == 'r':
            loadScalarReg(argument, scalar_register_data)
            testline = testline + f"x{scalar_register_data[argument]['reg']}"
        elif argument[0] == 'f':
            testline = testline + f"f{floating_point_register_data[argument]['reg']}"
        else:
            raise TypeError(f"Instruction Argument type not supported: '{argument}'")

        testline = testline + ", "

    testline = testline[:-2] # remove the ", " at the end of the test

    if vector_register_data['vd']['reg_type'] == "mask" or vector_register_data['vd']['reg_type'] == "scalar":
        sig_whole_register_store = True
        sig_lmul = 1
    elif instruction in whole_register_move:
        sig_whole_register_store = True
        sig_lmul= getLengthLmul(instruction) # will return <nf> for whole register moves
    else:
        sig_whole_register_store = False
        sig_lmul = lmul


    vd = vector_register_data ['vd'] ['reg']
    rd = scalar_register_data ['rd'] ['reg']

    if (maskval is not None) or (vl is not None):
        writeVecTest(vd, "SEWMIN", testline, test=instruction, rd=rd, vl=vl, sig_lmul = sig_lmul, sig_whole_register_store = sig_whole_register_store, priv = True)
    else:
        writeVecTest(vd, "SEWMIN", testline, test=instruction, rd=rd, sig_lmul = sig_lmul, sig_whole_register_store = sig_whole_register_store, priv = True)



#####################################                main                 #####################################

if __name__ == '__main__':
    common.writeLine        = writeLine
    common.mtrap_sig_count  = 2000  # TODO: check if hard code
    signatureWords          = 10000  # TODO: check if hard code


    author = "David_Harris@hmc.edu"
    xlens = [32, 64]
    maxXLEN = 64
    numrand = 3
    corners = []
    fcorners = []

    # setup
    seed(0) # make tests reproducible

    testplans = readTestplans(priv=True)
    extensions = list(testplans.keys())

    for extension in extensions:
        setExtension(extension)
        setXlen(maxXLEN)
        instructions = list(testplans[extension].keys())

        pathname = f"{ARCH_VERIF}/tests/priv/vector"

        cmd = "mkdir -p " + pathname # make directory
        os.system(cmd)

        basename = extension
        fname = pathname + "/" + basename + ".S"
        tempfname = pathname + "/" + basename + "_temp.S"

        print("Generating tests for " + fname)

        ############################### starting test file ###############################
        # print custom header part
        f = open(tempfname, "w")
        line = "///////////////////////////////////////////\n"
        f.write(line)
        line = "// "+fname+ "\n// " + author + "\n"
        f.write(line)

        # insert generic header
        insertTemplate(basename, 0, "testgen_header_vector_priv.S")

        ###############################     test body      ###############################
        for instruction in instructions:
            coverpoints = list(testplans[extension][instruction])
            makeTest(coverpoints, instruction)

        insertTemplate(basename, 0, "cp_vstart_gt_vl_setup.S")

        ###############################  ending test file  ###############################
        # print footer (before DATA)
        insertTemplate(basename, 0, "testgen_footer_vector1.S")

        # generate vector data (random and corners)
        genVMaskCorners() # TODO: change to generate a good random (vector_random)

        # print footer (after DATA)
        signatureWords = getSigSpace(maxXLEN, flen) #figure out how many words are needed for signature
        insertTemplate(basename, signatureWords, "testgen_footer_vector2.S")

        # Finish
        f.close()
        # if new file is different from old file, replace old file with new file
        if os.path.exists(fname):
            if filecmp.cmp(fname, tempfname): # files are the same
                os.system(f"rm {tempfname}") # remove temp file
            else:
                os.system(f"mv {tempfname} {fname}")
                print("Updated " + fname)
        else:
            os.system(f"mv {tempfname} {fname}")
