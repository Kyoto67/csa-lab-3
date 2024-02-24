from __future__ import annotations

import logging
from collections import namedtuple
from typing import ClassVar

from machine.datapath import DataPath, Enum, Selector
from machine.isa import HaltError, Instruction, Opcode, Port, TypesOfAddressing

microcode_fields_name = [
    "latch_cr",
    "sel_ip",
    "latch_ip",
    "sel_ar",
    "latch_ar",
    "sel_oe",
    "signal_oe",
    "sel_dr",
    "latch_dr",
    "latch_left_op",
    "latch_right_op",
    "signal_calculate",
    "check_flags",
    "sel_acc",
    "latch_acc",
    "sel_wr",
    "signal_wr",
    "sel_sp",
    "latch_sp",
    "latch_out",
    "mux_port",
    "latch_in",
    "mux_mPC",
    "latch_mPC",
]
signals_to_data_path = [
    "latch_cr",
    "latch_ip",
    "latch_ar",
    "signal_oe",
    "sel_dr",
    "latch_dr",
    "latch_left_op",
    "latch_right_op",
    "signal_calculate",
    "latch_acc",
    "signal_wr",
    "latch_sp",
    "latch_in",
    "latch_out",
]
selectors_for_data_path = {
    "latch_ip": "sel_ip",
    "latch_ar": "sel_ar",
    "signal_oe": "sel_oe",
    "latch_dr": "sel_dr",
    "latch_acc": "sel_acc",
    "signal_wr": "sel_wr",
    "latch_sp": "sel_sp",
    "latch_in": "mux_port",
    "latch_out": "mux_port",
    "latch_mPC": "mux_mPC",
}


class MicrocodeSelector(Enum):
    INCREMENT = "INCREMENT"
    DECODE_OP_FETCH = "DECODE"
    DECODE_COMMAND = "DECODE_COMMAND"
    RESET = "RESET"


Microcode = namedtuple("Microcode", microcode_fields_name)


class MicrocodeMemory:
    def __init__(self):
        self.memory: ClassVar[list] = []

        all_microcode_instruction = [
            [{"latch_cr": 1, "sel_ip": Selector.FROM_IP, "latch_ip": 1}, MicrocodeSelector.DECODE_OP_FETCH],
            # instruction Fetch
            [{"sel_dr": Selector.FROM_CR, "latch_dr": 1}, MicrocodeSelector.DECODE_COMMAND],  # Direct Operand Fetch
            [{"sel_ar": Selector.FROM_CR, "latch_ar": 1}],  # Absolut Operand Fetch
            [{"sel_dr": Selector.FROM_MEMORY, "latch_dr": 1}, MicrocodeSelector.DECODE_COMMAND],
            [{"sel_ar": Selector.FROM_CR, "latch_ar": 1}],  # Relative Operand Fetch
            [{"sel_ar": Selector.FROM_MEMORY, "latch_ar": 1}],
            [{"sel_dr": Selector.FROM_MEMORY, "latch_dr": 1}, MicrocodeSelector.DECODE_COMMAND],
            [{}, MicrocodeSelector.DECODE_COMMAND],  # Non Address Command
            [
                {
                    "latch_left_op": 1,
                    "latch_right_op": 1,
                    "signal_calculate": 1,
                    "sel_acc": Selector.FROM_ALU,
                    "latch_acc": 1,
                },
                MicrocodeSelector.RESET,
            ],  # Math Command
            [{"check_flags": 1}],  # JA, JE, JNE, JB
            [{"sel_ip": Selector.FROM_DR, "latch_ip": 1}, MicrocodeSelector.RESET],  # Jump command
            [{}, MicrocodeSelector.RESET],
            [{"sel_acc": Selector.FROM_DR, "latch_acc": 1}, MicrocodeSelector.RESET],  # LD
            [{"sel_wr": Selector.FROM_AR, "signal_wr": 1}, MicrocodeSelector.RESET],  # ST
            [
                {"sel_wr": Selector.FROM_SP, "signal_wr": 1, "sel_sp": Selector.SEL_DEC, "latch_sp": 1},
                MicrocodeSelector.RESET,
            ],  # PUSH
            [
                {"sel_sp": Selector.SEL_INC, "latch_sp": 1},
            ],  # POP
            [{"sel_dr": Selector.FROM_SP, "latch_dr": 1}],
            [{"sel_acc": Selector.FROM_DR, "latch_acc": 1}, MicrocodeSelector.RESET],
            [{"latch_left_op": 1, "latch_right_op": 1, "signal_calculate": 1}, MicrocodeSelector.RESET],  # CMP
            [{"mux_port": Port.BUFFER_IN, "latch_in": 1}],  # Read
            [{"sel_acc": Selector.FROM_INPUT, "latch_acc": 1}, MicrocodeSelector.RESET],
            [{"mux_port": Port.OUT, "latch_out": 1}, MicrocodeSelector.RESET],  # Print
        ]

        for option in all_microcode_instruction:
            self.memory.append(
                self.load_microinstruction(option[0], option[1] if len(option) > 1 else MicrocodeSelector.INCREMENT)
            )

    def get_micro_instruction(self, mpc: int) -> Microcode:
        assert 0 <= mpc < len(self.memory)
        return self.memory[mpc]

    def load_microinstruction(
        self, options: dict, mux_mpc: MicrocodeSelector = MicrocodeSelector.INCREMENT
    ) -> Microcode:
        options["mux_mPC"] = mux_mpc
        options["latch_mPC"] = 1
        tmp = [0] * (len(microcode_fields_name))
        for key in options.keys():
            tmp[microcode_fields_name.index(key)] = options.get(key)
        return Microcode._make(tmp)


class Decoder:
    microcode: ClassVar[list] = []

    def decode_command(self, instruction: Instruction) -> int:
        opcode = instruction.opcode
        if opcode == Opcode.HALT:
            raise HaltError
        if opcode in [Opcode.ADD, Opcode.SUB, Opcode.MUL, Opcode.DIV, Opcode.INC]:
            return 8
        if opcode in [Opcode.JA, Opcode.JB, Opcode.JE, Opcode.JNE]:
            return 9
        microcode_pointers = {
            Opcode.JUMP: 10,
            Opcode.LD: 12,
            Opcode.ST: 13,
            Opcode.PUSH: 14,
            Opcode.POP: 15,
            Opcode.CMP: 18,
            Opcode.READ: 19,
            Opcode.PRINT: 21,
        }
        return microcode_pointers.get(opcode)

    def decode_operand_fetch(self, instruction: Instruction) -> int:
        microcode_pointers = {
            None: 7,
            TypesOfAddressing.DIRECT.value: 1,
            TypesOfAddressing.ABSOLUT.value: 2,
            TypesOfAddressing.RELATIVE.value: 4,
        }
        return microcode_pointers.get(instruction.arg1)


class ControlUnit:
    def __init__(self, data_path: DataPath, tick_limit: int):
        self.data_path = data_path
        self.tick_counter = 0
        self.tick_limit = tick_limit
        self.microcode_memory = MicrocodeMemory()
        self.decoder = Decoder()
        self.microcode_ip = 0

    def process_tick(self):
        self.tick_counter += 1
        current_microcode = self.microcode_memory.get_micro_instruction(self.microcode_ip)
        for signal_name in current_microcode._fields:
            if getattr(current_microcode, signal_name) != 1:
                continue
            if signal_name in signals_to_data_path:
                self.send_signal_to_data_path(signal_name)
            if signal_name == "latch_mPC":
                self.microcode_handler(signal_name)
            if signal_name == "check_flags":
                self.check_flags()

    def send_signal_to_data_path(self, signal_name: str):
        assert signal_name in signals_to_data_path, "incorrect signal to DataPath"
        if selectors_for_data_path.get(signal_name):
            sel = self.get_selector(signal_name)
            getattr(self.data_path, signal_name)(sel)
        else:
            getattr(self.data_path, signal_name)()

    def microcode_handler(self, signal_name: str):
        sel = self.get_selector(signal_name)
        if sel == MicrocodeSelector.INCREMENT:
            self.microcode_ip += 1
        if sel == MicrocodeSelector.DECODE_OP_FETCH:
            self.microcode_ip = self.decoder.decode_operand_fetch(self.data_path.cr)
        if sel == MicrocodeSelector.DECODE_COMMAND:
            self.microcode_ip = self.decoder.decode_command(self.data_path.cr)
        if sel == MicrocodeSelector.RESET:
            logging.debug(self.__repr__())
            self.microcode_ip = 0

    def check_flags(self):
        zero_flag, negative_flag = self.data_path.get_flags()
        if not (
            self.data_path.cr.opcode == Opcode.JE
            and zero_flag == 1
            or self.data_path.cr.opcode == Opcode.JA
            and (negative_flag == 0)
            or self.data_path.cr.opcode == Opcode.JB
            and (negative_flag == 1 or zero_flag == 1)
            or self.data_path.cr.opcode == Opcode.JNE
            and zero_flag == 0
        ):
            self.microcode_ip += 1

    def get_selector(self, signal_name: str) -> Selector:
        return getattr(
            self.microcode_memory.get_micro_instruction(self.microcode_ip), selectors_for_data_path.get(signal_name)
        )

    def __repr__(self):
        return "INSTRUCTION {:>15} | TICK: {:10d} | IP: {:10d} | DR {:10d} | AR: {:10d} | ACC: {:10d} | SP: {:10d}".format(
            self.data_path.cr.opcode,
            self.tick_counter,
            self.data_path.ip,
            self.data_path.dr,
            self.data_path.ar,
            self.data_path.acc,
            self.data_path.sp,
        )
