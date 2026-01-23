********************************
Performance improvements to ISAC
********************************

Coverage computation in ISAC is an iterative process where all coverpoints
are evaluated for every instruction. This causes an exponential increase in coverage
computation time as the number of coverpoints increases. Following are methods leveraged to produce
performance improvements to ISAC.

Parallelized coverage calculation
#################################

Parallelization is one way to reduce the time taken to compute the coverage.
Parallelization of coverage computation is achieved by the parallelization of ``compute_per_line()``
method in ``coverage.py`` file. The implementation resorts to the use of queues to relay statistics of hit
coverpoint back to the main process.

Usage
*****
The number of processes to be spawned for coverage computation can be provided using,
``--procs`` or ``-p`` option while running ISAC. As an example, ::
    
    riscv_isac --verbose info coverage -d -t add-01.log --parser-name c_sail --decoder-name internaldecoder -o coverage.rpt --sig-label begin_signature end_signature --test-label rvtest_code_begin rvtest_code_end -e add-01.elf -c dataset.cgf -c rv32i.cgf -x 32 -l add --procs 3

The above command partitions the supplied CGF file into three different sets based on the coverlabels. Three processes would be
spawned and are supplied with a part of the partitioned CGF file dictionary. Each of the processes are asynchronously supplied with ``instructionObject`` 
objects via independent queues. The processes compute coverage independently against the decoded ``instructionObject`` with its own set of coverlabels 
and its respective coverpoints. The updated cgf dictionary and coverpoint hit statistics are relayed back to the main process through a queue.
The cgf dictionary and the statistics are merged before continuing further.

The default number of processes spawned is 1

Removal of Hit Coverpoints from CGF Dictionary
##############################################

For architectural testing, it is enough if a coverpoint is hit just once and has impact on the signature. When this feature 
is enabled, coverpoints would be deleted from the working CGF dictionary once hit to avoid evaluating it for all subsequent
instructions. 

Usage
*****
This feature can be enabled using the ``--no-count`` option while running ISAC. As an example, ::

    riscv_isac --verbose info coverage -d -t add-01.log --parser-name c_sail --decoder-name internaldecoder -o coverage.rpt --sig-label begin_signature end_signature --test-label rvtest_code_begin rvtest_code_end -e add-01.elf -c dataset.cgf -c rv32i.cgf -x 32 -l add --no-count

When ``--no-count`` option supplied, the hit coverpoints are stored and are then deleted from the CGF dictionary at the end of every iteration

This feature is off by default.
