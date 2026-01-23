.. See LICENSE.incore for details

.. highlight:: shell

============
Quickstart
============

Install Python
==============

.. tabs::

   .. tab:: Ubuntu


      Ubuntu 17.10 and 18.04 by default come with python-3.6.9 which is sufficient for using riscv-isac.
      
      If you are are Ubuntu 16.10 and 17.04 you can directly install python3.6 using the Universe
      repository
      
      .. code-block:: shell-session

        $ sudo apt-get install python3.6
        $ pip3 install --upgrade pip
      
      If you are using Ubuntu 14.04 or 16.04 you need to get python3.6 from a Personal Package Archive 
      (PPA)
      
      .. code-block:: shell-session

        $ sudo add-apt-repository ppa:deadsnakes/ppa
        $ sudo apt-get update
        $ sudo apt-get install python3.6 -y 
        $ pip3 install --upgrade pip
      
      You should now have 2 binaries: ``python3`` and ``pip3`` available in your $PATH. 
      You can check the versions as below
      
      .. code-block:: shell-session

        $ python3 --version
        Python 3.6.9
        $ pip3 --version
        pip 20.1 from <user-path>.local/lib/python3.6/site-packages/pip (python 3.6)

   .. tab:: CentOS7

      The CentOS 7 Linux distribution includes Python 2 by default. However, as of CentOS 7.7, Python 3 
      is available in the base package repository which can be installed using the following commands
      
      .. code-block:: shell-session

        $ sudo yum update -y
        $ sudo yum install -y python3
        $ pip3 install --upgrade pip
      
      For versions prior to 7.7 you can install python3.6 using third-party repositories, such as the 
      IUS repository
      
      .. code-block:: shell-session

        $ sudo yum update -y
        $ sudo yum install yum-utils
        $ sudo yum install https://centos7.iuscommunity.org/ius-release.rpm
        $ sudo yum install python36u
        $ pip3 install --upgrade pip
      
      You can check the versions
      
      .. code-block:: shell-session

        $ python3 --version
        Python 3.6.8
        $ pip --version
        pip 20.1 from <user-path>.local/lib/python3.6/site-packages/pip (python 3.6)

Using Virtualenv for Python 
---------------------------

Many a times users face issues in installing and managing multiple python versions. This is actually 
a major issue as many gui elements in Linux use the default python versions, in which case installing
python3.6 using the above methods might break other software. We thus advise the use of **pyenv** to
install python3.6.

For Ubuntu and CentosOS, please follow the steps here: https://github.com/pyenv/pyenv#basic-github-checkout

RHEL users can find more detailed guides for virtual-env here: https://developers.redhat.com/blog/2018/08/13/install-python3-rhel/#create-env

Once you have pyenv installed do the following to install python 3.6.0::

  $ pyenv install 3.6.0
  $ pip3 install --upgrade pip
  $ pyenv shell 3.6.0
  
You can check the version in the **same shell**::

  $ python --version
  Python 3.6.0
  $ pip --version
  pip 20.1 from <user-path>.local/lib/python3.6/site-packages/pip (python 3.6)


Install RISC-V ISAC
===================
.. tabs::
    .. tab:: via git
        To install RISC-V ISA Coverage Tool, run this command in your terminal:
        
        .. code-block:: console
        
            $ python3 -m pip3 install git+https://github.com/riscv/riscv-isac.git
        
        This is the preferred method to install RISC-V ISA Coverage, as it will always install the most recent stable release.
        
        If you don't have `pip`_ installed, this `Python installation guide`_ can guide
        you through the process.
        
        .. _pip: https://pip.pypa.io
        .. _Python installation guide: http://docs.python-guide.org/en/latest/starting/installation/
    
    .. tab:: via pip

        .. note:: If you are using `pyenv` as mentioned above, make sure to enable that environment before
         performing the following steps.
        
        .. code-block:: bash
        
          $ pip3 install riscv_isac
        
        To update an already installed version of RISCV-ISAC to the latest version:
        
        .. code-block:: bash
        
          $ pip3 install -U riscv_isac
        
        To checkout a specific version of riscv_isac:
        
        .. code-block:: bash
        
          $ pip3 install riscv_isac==1.x.x

    .. tab:: for Dev

        The sources for RISC-V ISA Coverage Tool can be downloaded from the `Github repo`_.
        
        You can clone the repository:
        
        .. code-block:: console
        
            $ git clone https://github.com/riscv/riscv-isac
        
        
        Once you have a copy of the source, you can install it with:
        
        .. code-block:: console
            
            $ cd riscv_isac
            $ pip3 install --editable .
        
        
        .. _Github repo: https://github.com/riscv/riscv-isac

Test RISC-V ISAC
=================

Once you have RISCV-ISAC installed, executing ``riscv_isac --help`` should print the following on the terminal. ::

   Options:
      --version                       Show the version and exit.
      -v, --verbose [info|error|debug]
                                      Set verbose level
      --help                          Show this message and exit.
    
   Commands:
     coverage   Run Coverage analysis on tracefile.
     merge      Merge given coverage files.
     normalize  Normalize the cgf. 

RISCV-ISAC has three commands : ``coverage``, ``merge`` and ``normalize`` which are described below.
Help text for each command can be accessed by executing ``riscv_isac <command> --help``

.. tabs::

  .. tab:: Coverage

    .. code-block:: console

        Usage: riscv_isac coverage [OPTIONS]
        
          Run Coverage analysis on tracefile.
        
        Options:
          -e, --elf PATH                  ELF file
          -t, --trace-file PATH           Instruction trace file to be analyzed
                                          [required]

          -h, --header-file PATH          YAML macro file to include
          -cm, --cgf-macro CGF MACROS     CGF macros to consider for this run.

          -c, --cgf-file PATH             Coverage Group File(s). Multiple allowed.
                                          [required]
        
          -d, --detailed                  Select detailed mode of  coverage printing
          --parser-name NAME              Parser plugin name. Parsers shipped with
                                          ISAC - [c_sail, spike]  [default: c_sail]
        
          --decoder-name NAME             Decoder plugin name. Decoders shipped with
                                          ISAC - [internaldecoder]  [default:
                                          internaldecoder]
        
          --parser-path PATH              Parser file path
          --decoder-path PATH             Decoder file path
          -o, --output-file PATH          Coverage Group File
          --test-label LABEL_START LABEL_END
                                          Pair of labels denoting start and end points
                                          of the test region(s). Multiple allowed.
        
          --sig-label LABEL_START LABEL_END
                                          Pair of labels denoting start and end points
                                          of the signature region(s). Multiple
                                          allowed.
        
          --dump PATH                     Dump Normalized Coverage Group File
          -l, --cov-label COVERAGE LABEL  Coverage labels to consider for this run.
          -x, --xlen [32|64]              XLEN value for the ISA.
          --help                          Show this message and exit.
    

  .. tab:: Merge

    .. code-block:: console

      Usage: riscv_isac merge [OPTIONS] [FILES]...
      
        Merge given coverage files.
      
      Options:
        -d, --detailed          Select detailed mode of  coverage printing
        -p                      Number of processes
        -c, --cgf-file PATH     Coverage Group File  [required]
        -o, --output-file PATH  Coverage Group File.
        --help                  Show this message and exit.

  .. tab:: Normalize

    .. code-block:: console

      Usage: riscv_isac normalize [OPTIONS]
      
        Normalize the cgf.
      
      Options:
        -c, --cgf-file PATH     Coverage Group File  [required]
        -o, --output-file PATH  Coverage Group File  [required]
        -x, --xlen [32|64]      XLEN value for the ISA.
        --help                  Show this message and exit.

Running RISC-V ISAC
===================

There are 3 different operations which can be performed by RISC-V ISAC namely,

    1. coverage - Calculate the coverage of a test using the given log and cgf file(s).
    2. merge - Merge different coverage reports to produce a single report with all statistics.
    3. normalize - Dump a cgf file without any yaml anchors and abstract functions. The output file will contain the elaborated coverpoints as specified by the input cgf file(s).


The CGF file(s) used in these examples can be obtained from `here <Cgf files_>`_. 

.. _Cgf files: https://github.com/riscv/riscv-ctg/tree/master/sample_cgfs 

Example usage of each of the commands are given below:

.. tabs ::

    .. tab:: Coverage

        RISC-V ISAC is shipped with the following standard plugins.

        1. Parser Plugins:
            - `SAIL C Model <SAIL_>`_ ``c_sail``: Parser for execution logs from the C model generated by SAIL. 
            - `SPIKE`_ ``spike``: Parser for execution logs from riscv-isa-sim.
        
        2. Decoder Plugins:
            - Native Python Decoder ``internaldecoder``: A decoder for the RISC-V isa written in python.

        The ``c_sail`` and the ``internaldecoder`` plugins are used by default. To use custom
        plugins with RISC-V ISAC refer :ref:`here<Custom Plugin Usage>`.
        
        For a log file generated after running a test from the `Architecture Test Suite`_ on the SAIL
        C Model, the following command can be used to compute coverage for the test:

        .. code-block:: console

            riscv_isac --verbose info coverage -d -t add-01.log --parser-name c_sail --decoder-name internaldecoder -o coverage.rpt --sig-label begin_signature end_signature --test-label rvtest_code_begin rvtest_code_end -e add-01.elf -c dataset.cgf -c rv32i.cgf -x 32 -l add

        .. note:: The command assumes that the cgf files are in the same directory. Modify paths to the ``-c`` argument accordingly.

        .. note:: The command assumes that the coverage is calculated for the add test. Modify paths to the ``-e`` and ``-t`` arguments accordingly. The label should also be changed based on requirements. 

        .. note:: To use the spike parser use ``--parser-name spike``.

        .. warning:: Coverage reported by ISAC is based on the instructions reported in the trace file. Hence it is imperative that all instructions are reported in the trace file. Currently the coverage reporting using the SPIKE model is inaccurate because instructions which trap are not reported in the trace file. It is advisable to use the SAIL model for accurate coverage reporting.

    .. tab:: Merge

        Sample command to merge different coverage reports to a single report.

        .. code-block:: console

            riscv_isac --verbose info merge -c dataset.cgf -c rv32i.cgf -o merged_report 1.rpt 2.rpt 3.rpt

        .. note:: The command assumes that the cgf files are in the same directory. Modify paths to the ``-c`` argument accordingly.

        .. note:: Modify the paths `*.rpt` if the report files are not in the same directory.

    .. tab:: Normalize

        Sample command to normalize CGF file(s).

        .. code-block:: console
            
            riscv_isac --verbose info normalize -c dataset.cgf -c rv32i.cgf -o normalized.cgf -x 32

        .. note:: The command assumes that the cgf files are in the same directory. Modify paths to the ``-c`` argument accordingly.

.. _SPIKE: https://github.com/riscv/riscv-isa-sim 
.. _SAIL: https://github.com/rems-project/sail-riscv 
.. _Architecture Test Suite: https://github.com/riscv/riscv-arch-test 

    



