from __future__ import annotations

import json
from enum import Enum

MEMORY_SIZE = 8096
MAX_INSTRUCTIONS_SIZE = 4096


class HaltError(Exception):
    pass


class EndOfBufferError(Exception):
    pass


class Port(Enum):
    BUFFER_IN = 1
    OUT = 2


class Opcode(Enum):
    ST = "ST"
    LD = "LD"
    ADD = "ADD"
    SUB = "SUB"
    MUL = "MUL"
    DIV = "DIV"
    JUMP = "JUMP"
    PUSH = "PUSH"
    CMP = "CMP"
    JE = "JE"
    JNE = "JNE"
    JA = "JA"
    JB = "JB"
    POP = "POP"
    HALT = "HALT"
    INC = "INC"
    NOP = "NOP"
    READ = "READ"
    PRINT = "PRINT"


class Register(Enum):
    ACC = "ACC"
    IP = "IP"
    AR = "AR"
    DR = "DR"
    SP = "SP"
    CR = "CR"


class Instruction:
    index: int
    opcode: Opcode
    arg1: int | str
    arg2: int | str

    def __init__(self, index: int, opcode: Opcode, arg1: int | str, arg2: int | str):
        self.index = index
        self.opcode = opcode
        self.arg1 = arg1
        self.arg2 = arg2

    def __str__(self):
        return f"{self.index} [{self.opcode} arg1:{self.arg1} arg2: {self.arg2}]"

    def __dict__(self):
        return {"index": self.index, "opcode": str(self.opcode), "arg1": self.arg1, "arg2": self.arg2}

    def __format__(self, format_spec):
        return self.arg1


class TypesOfAddressing(Enum):
    ABSOLUT = "="
    RELATIVE = "~"
    DIRECT = "#"


def read_code(source: str) -> list[Instruction]:
    instructions = []
    with open(source, encoding="utf-8") as f:
        code = json.loads(f.read())
        for instr in code:
            index = instr["index"]
            opcode = Opcode(str(instr["opcode"])[7:])
            arg1 = instr["arg1"]
            arg2 = instr["arg2"]
            instructions.append(Instruction(index, opcode, arg1, arg2))
    return instructions


def write_code(target: str, code: list[Instruction]) -> None:
    with open(target, "w", encoding="utf-8") as f:
        json_code = []
        for instr in code:
            json_code.append(json.dumps(instr.__dict__()))
        f.write("[" + ",\n".join(json_code) + "]")
        json_code.clear()
