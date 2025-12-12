####################################################################################
#
# RISC-V Architectural Functional Coverage Testbench
#
# Copyright (C) 2025 Harvey Mudd College, 10x Engineers, UET Lahore
# Written: Jordan Carlin jcarlin@hmc.edu March 2025
#
# SPDX-License-Identifier: Apache-2.0
#
####################################################################################

onbreak {resume}
onerror {quit -f}

# Initialize variables
set TRACEFILELIST ${1}
set UCDB ${2}
set WKDIR ${3}
set FCOVDIR ${4}
set COVERPOINTDIR ${5}
set CONFIGDIR ${6}
set COVERAGELIST ${7}

# Create library
if [file exists ${WKDIR}] {
    vdel -lib ${WKDIR} -all
}
vlib ${WKDIR}

# Include directories and files to compile
set COVERPOINTS "+incdir+${COVERPOINTDIR} +incdir+${COVERPOINTDIR}/unpriv +incdir+${COVERPOINTDIR}/priv"
set INC_DIRS "+incdir+${CONFIGDIR} ${COVERPOINTS} +incdir+${FCOVDIR}"
set COMPILE_FILES "${FCOVDIR}/rvviTrace.sv ${FCOVDIR}/riscv_arch_test.sv ${FCOVDIR}/testbench.sv"

# Build +define+ list from COVERAGELIST (space-separated)
set DEFINE_ARGS {}
foreach def [split ${COVERAGELIST}] {
    if {$def eq ""} { continue }
    lappend DEFINE_ARGS "+define+$def"
}

# Compile
vlog -permissive -lint -work ${WKDIR} {*}${INC_DIRS} {*}${DEFINE_ARGS} {*}${COMPILE_FILES}

# Start and run simulation
vopt ${WKDIR}.testbench -work ${WKDIR} -o testbenchopt
vsim -lib ${WKDIR} testbenchopt +traceFileList=${TRACEFILELIST} -fatal 7

coverage save -onexit ${UCDB}

run -all
quit
