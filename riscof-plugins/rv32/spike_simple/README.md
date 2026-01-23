### Riscof Plugin for SPIKE RISC-V ISA Simulator

- Using the SPIKE RISC-V ISA Simulator

The [Spike, RISC-V ISA Simulator](https://github.com/riscv/riscv-isa-sim) implements a functional 
model of one or more RISC-V Harts. It can be used as a target for running tests using riscof.

- Config file entry
```
# Name of the Plugin. All entries are case sensitive. Including the name.
[spike_simple]

#path to the directory where the plugin is present. (required)
pluginpath=<path-to-plugin>

#path where the riscv-isa-sim binary is available. (optional)
#if this value is absent, it is assumed that the binaries are available as executables by default
PATH=<path-to-binaries>

#path to the ISA config file. (required)
ispec=<path-to-isa-config>

#path to the Platform config file. (required)
pspec=<path-to-platform-config>
```

- Export command
```
pwd=pwd;export PYTHONPATH=$pwd:$PYTHONPATH;
```
