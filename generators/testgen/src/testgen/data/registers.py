##################################
# registers.py
#
# jcarlin@hmc.edu 5 October 2025
# SPDX-License-Identifier: Apache-2.0
##################################

"""
Register management for riscv-arch-test test generation.
"""

from __future__ import annotations

import random

from testgen.constants import INDENT


class RegisterFile:
    """Class to represent a register file and provide methods to select registers."""

    def __init__(self, reg_count: int) -> None:
        self._reg_count = reg_count
        self.reg_list: set[int] = set(range(reg_count))

    def __repr__(self) -> str:
        return f"Register File with the following registers available: {sorted(self.reg_list)}"

    def destroy(self) -> None:
        """Clean up resources used by RegisterFile."""
        if len(self.reg_list) != self._reg_count:
            raise RuntimeError(
                f"Cannot destroy RegisterFile: some registers are still in use. The current state of the register file is: {sorted(self.reg_list)}"
            )

    def copy(self) -> RegisterFile:
        """Create a deep copy of the RegisterFile object."""
        new_reg_file = RegisterFile(self._reg_count)
        new_reg_file.reg_list = self.reg_list.copy()
        return new_reg_file

    @property
    def reg_count(self) -> int:
        return self._reg_count

    def get_registers(
        self, num_regs: int, *, exclude_regs: list[int] | None = None, reg_range: list[int] | None = None
    ) -> list[int]:
        """Get a specified number of unique registers from the register file."""
        available_regs = self.reg_list
        if reg_range is not None:
            available_regs = available_regs & set(reg_range)
        if exclude_regs:
            available_regs = available_regs - set(exclude_regs)
        if num_regs > len(available_regs):
            raise ValueError(
                f"Not enough registers available to select from. Requested {num_regs}, but only {len(available_regs)} available."
            )
        selected_regs = random.sample(sorted(available_regs), num_regs)
        self.reg_list -= set(selected_regs)
        return selected_regs

    def get_register(self, *, exclude_regs: list[int] | None = None, reg_range: list[int] | None = None) -> int:
        """Get a single register from the register file."""
        return self.get_registers(1, exclude_regs=exclude_regs, reg_range=reg_range)[0]

    def return_registers(self, regs: list[int]) -> None:
        """Mark registers as available again."""
        self.reg_list.update(regs)

    def return_register(self, reg: int) -> None:
        """Mark a single register as available again."""
        self.return_registers([reg])

    def consume_registers(self, regs: list[int]) -> str | None:
        """Mark registers as used/unavailable."""
        regs_set = set(regs)
        unavailable = regs_set - self.reg_list
        if unavailable:
            raise ValueError(f"Registers {sorted(unavailable)} are already in use or not available.")
        self.reg_list -= regs_set
        return None


class IntegerRegisterFile(RegisterFile):
    """
    Class to represent an integer register file.

    Automatically handles special registers like signature pointer and link register.
    """

    default_sig_reg = 2
    default_data_reg = 3
    default_temp_reg = 4
    temp_regs = (4, 7, 13)  # Limit legal temp/link registers to simplify failure handler
    link_temp_regs = (4, 5, 7, 8, 13, 14)  # Valid temp/link register pairs

    def __init__(self, e_register_file: bool = False) -> None:
        # Use default RegisterFile functions but set register count based on E
        reg_count = 16 if e_register_file else 32
        super().__init__(reg_count)
        # Default special registers
        self._sig_reg = self.default_sig_reg
        self._data_reg = self.default_data_reg
        self._temp_reg = self.default_temp_reg
        self._link_reg = self._temp_reg + 1  # link register is always the next register after the temp register
        super().consume_registers([self._sig_reg, self._data_reg, self._link_reg, self._temp_reg])

    def destroy(self) -> None:
        self.return_registers([self._sig_reg, self._data_reg, self._link_reg, self._temp_reg])
        super().destroy()

    def copy(self) -> IntegerRegisterFile:
        """Create a deep copy of the IntegerRegisterFile object."""
        new_reg_file = IntegerRegisterFile(self._reg_count == 16)
        new_reg_file.reg_list = self.reg_list.copy()
        new_reg_file._sig_reg = self._sig_reg
        new_reg_file._data_reg = self._data_reg
        new_reg_file._temp_reg = self._temp_reg
        new_reg_file._link_reg = self._link_reg
        return new_reg_file

    # Access to special registers
    @property
    def sig_reg(self) -> int:
        return self._sig_reg

    @property
    def data_reg(self) -> int:
        return self._data_reg

    @property
    def temp_reg(self) -> int:
        return self._temp_reg

    @property
    def link_reg(self) -> int:
        return self._link_reg

    def get_register_pair(self, *, exclude_regs: list[int] | None = None, reg_range: list[int] | None = None) -> int:
        """Get an even register where both it and the following odd register are available.

        For register pair instructions, the even register is specified in the instruction
        but both registers are used.

        Returns:
            The even register number of the pair.
        """
        exclude_set = set(exclude_regs) if exclude_regs else set()
        range_set = set(reg_range) if reg_range is not None else None

        # Find even registers where both the even and odd register are available
        available_pairs: list[int] = []
        for reg in sorted(self.reg_list):
            is_even = reg % 2 == 0
            odd_available = (reg + 1) in self.reg_list
            not_excluded = reg not in exclude_set and (reg + 1) not in exclude_set
            in_range = range_set is None or (reg in range_set and (reg + 1) in range_set)
            if is_even and odd_available and not_excluded and in_range:
                available_pairs.append(reg)

        if not available_pairs:
            raise ValueError("No register pairs available")

        even_reg = random.choice(available_pairs)
        self.reg_list.discard(even_reg)
        self.reg_list.discard(even_reg + 1)
        return even_reg

    def consume_register_pair(self, even_reg: int) -> str:
        """Mark a register pair as used/unavailable, handling special register conflicts.

        Args:
            even_reg: The even register number of the pair.

        Returns:
            Assembly code needed to relocate any conflicting special registers.
        """
        if even_reg % 2 != 0:
            raise ValueError(f"Register {even_reg} is not an even register for a pair")
        return self.consume_registers([even_reg, even_reg + 1])

    def return_register_pair(self, even_reg: int) -> None:
        """Mark a register pair as available again.

        Args:
            even_reg: The even register number of the pair.
        """
        if even_reg % 2 != 0:
            raise ValueError(f"Register {even_reg} is not an even register for a pair")
        self.return_registers([even_reg, even_reg + 1])

    def move_sig_reg(self, new_reg: int) -> str:
        """Move the signature register to a specified register.

        Args:
            new_reg: The register number to move the signature pointer to.

        Returns:
            The assembly code needed to move the value from the old register to the new one.
        """
        if new_reg == 0:
            raise ValueError("Cannot move signature register to x0.")

        old_sig_reg = self._sig_reg
        self.return_register(self._sig_reg)
        if new_reg in self.reg_list:
            self.consume_registers([new_reg])
        self._sig_reg = new_reg
        asm_code = f"mv x{self._sig_reg}, x{old_sig_reg} # move signature pointer register"
        return asm_code

    def move_data_reg(self, new_reg: int) -> str:
        """Move the data register to a specified register.

        Args:
            new_reg: The register number to move the signature pointer to.

        Returns:
            The assembly code needed to move the value from the old register to the new one.
        """
        if new_reg == 0:
            raise ValueError("Cannot move data register to x0.")

        old_data_reg = self._data_reg
        self.return_register(self._data_reg)
        if new_reg in self.reg_list:
            self.consume_registers([new_reg])
        self._data_reg = new_reg
        asm_code = f"mv x{self._data_reg}, x{old_data_reg} # move data pointer register"
        return asm_code

    def reset_special_registers(self) -> str:
        """Reset special registers to their default locations.

        Returns:
            The assembly code needed to move the values back to the default registers.
        """
        lines: list[str] = []
        # Reset signature register
        if self._sig_reg != self.default_sig_reg:
            lines.append(self.move_sig_reg(self.default_sig_reg))
        # Reset data register
        if self._data_reg != self.default_data_reg:
            lines.append(self.move_data_reg(self.default_data_reg))
        # Reset link and temp registers
        if self._temp_reg != self.default_temp_reg:
            old_temp_reg = self._temp_reg
            old_link_reg = self._link_reg
            self.return_register(self._temp_reg)
            self.return_register(self._link_reg)
            self._temp_reg = self.default_temp_reg
            self._link_reg = self.default_temp_reg + 1
            # Use super to avoid recursive checking for special reg conflicts
            super().consume_registers([self._link_reg, self._temp_reg])
            lines.append(f"{INDENT}mv x{self._temp_reg}, x{old_temp_reg} # reset temp register to default")
            lines.append(f"{INDENT}mv x{self._link_reg}, x{old_link_reg} # reset link register to default")
        if lines:
            lines.insert(0, "# Reset special registers to default locations")
        return "\n".join(lines)

    def consume_registers(self, regs: list[int]) -> str:
        """Mark registers as used/unavailable, handling special register conflicts.

        If any of the requested registers conflict with special registers (sig_reg, link_reg),
        this method will automatically relocate the special registers and return the necessary
        assembly code to perform the move.
        """
        lines: list[str] = []

        # Check for conflicts with special registers
        sig_conflict = self._sig_reg in regs
        data_conflict = self._data_reg in regs
        temp_conflict = self._temp_reg in regs
        link_conflict = self._link_reg in regs
        old_sig_reg = -1
        old_data_reg = -1
        old_link_reg = -1
        old_temp_reg = -1

        # Return special registers to pool if they conflict
        if sig_conflict:
            old_sig_reg = self._sig_reg
            self.return_register(self._sig_reg)

        if data_conflict:
            old_data_reg = self._data_reg
            self.return_register(self._data_reg)

        if temp_conflict or link_conflict:
            old_temp_reg = self._temp_reg
            old_link_reg = self._link_reg
            self.return_register(self._temp_reg)
            self.return_register(self._link_reg)

        # Consume requested registers
        super().consume_registers(regs)

        # Reallocate special registers to new locations
        if sig_conflict:
            self._sig_reg = self.get_register(exclude_regs=[0, *self.link_temp_regs])
            lines.append(
                f"mv x{self._sig_reg}, x{old_sig_reg} # switch signature pointer register to avoid conflict with test"
            )

        if data_conflict:
            self._data_reg = self.get_register(exclude_regs=[0, *self.link_temp_regs])
            lines.append(
                f"mv x{self._data_reg}, x{old_data_reg} # switch data pointer register to avoid conflict with test"
            )

        if temp_conflict or link_conflict:
            # Restrict link register to specific set
            available_temp_regs = [reg for reg in self.temp_regs if reg + 1 in self.reg_list]
            self._temp_reg = self.get_register(reg_range=available_temp_regs)
            self._link_reg = self._temp_reg + 1  # link register is always the next register after the temp register
            # Use super to avoid recursive checking for special reg conflicts
            super().consume_registers([self._link_reg])
            lines.append(f"mv x{self._temp_reg}, x{old_temp_reg} # switch temp register to avoid conflict with test")
            lines.append(
                f"mv x{self._link_reg}, x{old_link_reg} # switch link pointer register to avoid conflict with test"
            )

        return "\n".join(lines)


class FloatRegisterFile(RegisterFile):
    """Class to represent a floating point register file."""

    default_temp_reg = 4
    temp_regs = (4, 7, 13)  # Limit legal temp registers to simplify failure handler

    def __init__(self) -> None:
        # There are always 32 floating point registers
        super().__init__(32)
        self._temp_reg = self.default_temp_reg
        super().consume_registers([self._temp_reg])

    def destroy(self) -> None:
        self.return_register(self._temp_reg)
        super().destroy()

    def copy(self) -> FloatRegisterFile:
        """Create a deep copy of the FloatRegisterFile object."""
        new_reg_file = FloatRegisterFile()
        new_reg_file.reg_list = self.reg_list.copy()
        new_reg_file._temp_reg = self._temp_reg
        return new_reg_file

    @property
    def temp_reg(self) -> int:
        return self._temp_reg

    def consume_registers(self, regs: list[int]) -> None:
        """Mark registers as used/unavailable, handling special register conflicts.

        If any of the requested registers conflict with special registers (temp_reg),
        this method will automatically relocate the special registers and return the
        necessary assembly code to perform the move.
        """

        # Check for conflicts with special registers
        temp_conflict = self._temp_reg in regs

        # Return special registers to pool if they conflict
        if temp_conflict:
            self.return_register(self._temp_reg)
        # Consume requested registers
        super().consume_registers(regs)

        # Reallocate special registers to new locations
        if temp_conflict:
            # Restrict link register to specific set
            self._temp_reg = self.get_register(reg_range=list(self.temp_regs))


class VectorRegisterFile(RegisterFile):
    """Class to represent a vector register file"""

    def __init__(self) -> None:
        # There are always 32 Vector Registers
        super().__init__(32)

        # The allocations are more involved with the vector registers because of lmul and potential overlaps,
        # so these values are both necessary to have
        self.allocation_map: dict[int, int] = {}
        self.operand_map: dict[str, tuple[int, int]] = {}

    def get_registers(
        self,
        num_regs: int,
        *,
        lmul: int = 1,
        segments: int = 1,
        exclude_regs: list[int] | None = None,
        reg_range: list[int] | None = None,
    ) -> list[int]:
        """
        Gets num_regs free registers from the register file, taking into account the desired lmul, number of segments,
        register exclusions, and a list of desired registers.

        Args:
            num_regs: The number of registers (not accounting for lmul) to be taken from the register file

        Optional Args:
            lmul: The lmul that the registers must be aligned to
            segments: The number of segments to allocate in one allocation. (e.g. with lmul = 2, and segments = 3, this
                allocates 6 registers at a time, aligned to multiples of 2)
            exclude_regs: A list of registers not to use
            reg_range: A list of registers specifically to use
        """
        registers_available_to_lmul = set()
        for register in range(0, 32, lmul):
            group = set(range(register, register + (lmul * segments)))
            if len(self.reg_list & group) == len(group):
                registers_available_to_lmul.add(register)

        reg_range_set = set(reg_range) if reg_range is not None else set(self.reg_list)
        reg_range_set &= registers_available_to_lmul

        registers = super().get_registers(num_regs, exclude_regs=exclude_regs, reg_range=list(reg_range_set))
        for register in registers:
            self.allocation_map[register] = lmul * segments
            self.consume_registers(list(range(register + 1, register + lmul * segments)))

        return registers

    def get_register(
        self,
        *,
        lmul: int = 1,
        segments: int = 1,
        exclude_regs: list[int] | None = None,
        reg_range: list[int] | None = None,
    ) -> int:
        """
        Gets a single register from the register file (accounting for lmul)

        Optional Args:
            lmul: The lmul that the registers must be aligned to
            segments: The number of segments to allocate in one allocation. (e.g. with lmul = 2, and segments = 3, this
                allocates 6 registers at a time, aligned to multiples of 2)
            exclude_regs: A list of registers not to use
            reg_range: A list of registers specifically to use
        """
        return self.get_registers(1, lmul=lmul, segments=segments, exclude_regs=exclude_regs, reg_range=reg_range)[0]

    def free_registers(self, lmul: int, segments: int) -> set[int]:
        """
        Returns a set of free registers available to a given lmul and number of segments.
        """
        registers_available_to_lmul = set()
        for register in range(0, 32, lmul):
            group = set(range(register, register + (lmul * segments)))
            if len(self.reg_list & group) == len(group):
                registers_available_to_lmul.add(register)

        return self.reg_list & registers_available_to_lmul

    def allocate_operand(self, name: str, register: int, width: int, *, suppress_overlap: bool = False) -> None:
        """
        Make a register allocation tied to the name of an operand. This means that an operand can be safely returned
        to the register file (through deallocate_operand) even if it has an overlap.

        Args:
            name: The name of the operand (e.g. vd, vs1, vs2)
            register: The number register to be used (satisfactory registers can be found through free_registers)
            width: The number of registers in this group (normally lmul * segments)

        Optional Args:
            suppress_overlap: If the allocation would result in double allocation of a register, this normally throws an
                error, but when this argument is set no errors are thrown on overlaps.
        """
        allocated = []
        for reg in range(register, register + width):
            if reg in self.reg_list:
                self.consume_registers([reg])
                allocated.append(reg)
            elif not suppress_overlap or reg >= self.reg_count:
                self.return_registers(allocated)
                raise ValueError(f"Unable to Allocate Registers for Operand {name}, v{register} with width {width}")
        self.operand_map[name] = (register, width)

    def deallocate_operand(self, name: str) -> None:
        """
        Deallocate an operand allocated through allocate_operand. This respects the other known active allocations and does
        not return registers that are otherwise still in use.
        """
        if not name in self.operand_map:
            return

        register, width = self.operand_map.pop(name)

        for attempt_deallocate in range(register, register + width):
            # Check for an overlap with anything else currently allocated
            overlap = False
            for register2, width2 in self.allocation_map.items():
                if register2 <= attempt_deallocate < register2 + width2:
                    overlap = True

            for register2, width2 in self.operand_map.values():
                if register2 <= attempt_deallocate < register2 + width2:
                    overlap = True

            if not overlap:
                self.return_register(attempt_deallocate)

    def deallocate_operands(self) -> None:
        """
        Deallocates all operands.
        """
        for name in list(self.operand_map.keys()):
            self.deallocate_operand(name)

    def return_registers(self, regs: list[int]) -> None:
        """Return all registers in a list to the register file, accounting for the lmul that they were allocated at"""
        reg_groups = []
        for reg in regs:
            # assert reg in self.allocation_map, "Deallocating Vector Registers Must go Through the Base Register"
            if reg in self.allocation_map:
                reg_groups.extend(range(reg, reg + self.allocation_map[reg]))
                self.allocation_map.pop(reg)
            else:
                reg_groups.append(reg)

        return super().return_registers(reg_groups)

    def return_register(self, reg: int) -> None:
        """Return a register to the register file, accounting for the lmul it was allocated at"""
        return self.return_registers([reg])

    def copy(self) -> VectorRegisterFile:
        """Create a deep copy of the VectorRegisterFile object."""
        new_reg_file = VectorRegisterFile()
        new_reg_file.reg_list = self.reg_list.copy()
        new_reg_file.allocation_map = self.allocation_map.copy()
        new_reg_file.operand_map = self.operand_map.copy()
        return new_reg_file
