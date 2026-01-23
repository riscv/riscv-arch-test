### Plugin to use Makefile.include from old framework with riscof

- This plugin facilitates the use of Makefile.include from the targets of the old framework with
  riscof and is intented to be used as a base for transition.
- The config node of the plugin can contain the following variables/
    - **makefiles** (*required*)- Comma separated paths to the makefiles. If multiple are specified, all will be
      merged in the final output makefile. Note that only the varaibles in the makefiles are written
      out into the final makefiles. Any targets or includes will be left out. Such cases can be
      handled by editing the plugin to output the relevant lines as a part of the `build` function.
    - **jobs** - The number of threads to launch parallely. (Default is `1`)
    - **ispec** (*required*)- The path to the input ISA yaml specification of the target.
    - **pspec** (*required*)- The path to the input platform yaml specification of the target.
    - **make** - The make utility to use like make,bmake,pmake etc. (Default is `make`)

- The commands in the makefiles need to be modified to make use of the following variables. The
  values for these are resolved based on the inputs from riscof and are substituted before writing
  out the final targets. An additional Makefile variable, `TARGET_DIR`, which contains the path
  where the plugin resides is written out at the starting of the makefile and can be used as an anchor
  point for resolving paths to other files.

    | Variable      | Description |
    | ------------- | ----------- |
    | `${target_dir}` | The directory where the plugin file resides. (riscof_makeplugin.py) |
    | `${asm}`        | Absolute path to the assemble test file i.e the .S file for the test. |
    | `${work_dir}`   | The absolute path to the work directory for the test. |
    | `${test_name}`  | The name of the test, for example add-01 etc. Can be used for naming any intermediate files generated. |
    | `${include}`    | The path to the directory which containts the test header files. This needs to be specified as an include path in the compile command. |
    | `${march}`      | The ISA to be used for compiling the test. This is in the format expected by march argument of gcc. |
    | `${mabi}`      | The abi to be used for compiling the test. This is in the format expected by mabi argument of gcc. |
    | `${target_isa}` | This is the ISA specified in the input ISA yaml. The idea is that it can be used to configure the model at run time via cli arguments if necessary. |
    | `${test_bin}`   | The name of the binary file to be created after compilation. Can be ignored. Custom names can be used as long as the RUN_TARGET command picks up the correct binary to execute on the target. |
    | `${signature_file}` | The absolute path to the signature file. This path cannot be changed and the signature file should be present at this path for riscof to verify at the end of testing. |
    | `${macros}`     | The macros to be defined while compilation. Currently they are in the format expected by gcc i.e.  `-D <macro-name>=<macro-value>` |


    The rewritten Makefile.include for the SAIL C Simulator from [here](https://github.com/riscv/riscv-arch-test/blob/2.4.4/riscv-target/sail-riscv-c/device/rv32i_m/I/Makefile.include) is included in the directory
    for reference(`sail.include`).

    **Note** - Value substitution for these variables happens only in the
    `COMPILE_TARGET` and `RUN_TARGET` values in the makefile. There is no resolution of makefile
    variables while substituting the values. The format of the output for each target is:
    ```
        cd <work_directory>;<COMPILE_TARGET>;<RUN_TARGET>;
    ```

- Examples

    **Correct** :

    ```
        TARGET_SIM   ?= riscv_sim_RV32 -V
        TARGET_FLAGS =
        
        RISCV_PREFIX   ?= riscv32-unknown-elf-
        RISCV_GCC      ?= $(RISCV_PREFIX)gcc
        RISCV_GCC_OPTS ?= -g -static -mcmodel=medany -fvisibility=hidden -nostdlib -nostartfiles \
                            -I$(TARGET_DIR)/env/ 
        
        COMPILE_TARGET=\
                    $$(RISCV_GCC) -march=${march} -mabi=${mabi} $$(RISCV_GCC_OPTS) \
        							-I${include} \
        							-T${target_dir}/env/link.ld \
        						    ${asm} -o ${test_bin} ${macros};
        
        RUN_TARGET=\
            $(TARGET_SIM) $(TARGET_FLAGS)\
                --test-signature=${signature_file} \
                ${test_bin} 
        
    ```

    **Wrong** :

    ```
        TARGET_SIM   ?= riscv_sim_RV32 -V
        TARGET_FLAGS =
        
        RISCV_PREFIX   ?= riscv32-unknown-elf-
        RISCV_GCC      ?= $(RISCV_PREFIX)gcc
        RISCV_GCC_OPTS ?= -g -static -mcmodel=medany -fvisibility=hidden -nostdlib -nostartfiles \
                            -I$(TARGET_DIR)/env/ -I${include} \
        
        COMPILE_TARGET=\
                    $$(RISCV_GCC) -march=${march} -mabi=${mabi} $$(RISCV_GCC_OPTS) \
        							-T${target_dir}/env/link.ld \
        						    ${asm} -o ${test_bin} ${macros};
        
        RUN_TARGET=\
            $(TARGET_SIM) $(TARGET_FLAGS)\
                --test-signature=${signature_file} \
                ${test_bin}
    ```
    The commands produced using the above makefile will result in an error when executed because the
    value of `${include}` will not be substituted in the `RISCV_GCC_OPTS` (Variable substitutions
    are performed only for the `COMPILE_TARGET` and `RUN_TARGET` commands).
