## CGF: Cover Group Format

- Uses a simple to use and a human readable YAML format to define cover groups and cover-points for the RISC-V ISA. 
- Declares datasets separately which can be used across coverpoints:
  - Operand Addresses for a single instruction
  - Operand Value for a single instruction
  - Abstract functions like walking1s and walking0s which get unrolled by the extraction tool
- Covergroups include multiple datasets
  - Each coverpoint is defined as a boolean expression which can to be evaluated by the "eval"
    tool of python.
  - Coverpoints to use a standard set of keywords like: rs1, rs2, rd, rs1_val, rs2_val, etc
- Uses Anchors and Aliases to keep the size of the YAML file small

