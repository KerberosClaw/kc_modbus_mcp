"""
資料型別轉換器 — raw registers ↔ 工程值
"""

import struct


def registers_to_value(registers: list[int], data_type: str, byte_order: str = "big") -> int | float | bool:
    """將 raw register 值轉換為 Python 值"""
    if data_type == "bool":
        return bool(registers[0])

    if data_type == "uint16":
        return registers[0]

    if data_type == "int16":
        val = registers[0]
        return val if val < 0x8000 else val - 0x10000

    if data_type in ("uint32", "int32", "float32"):
        if len(registers) < 2:
            raise ValueError(f"{data_type} requires 2 registers, got {len(registers)}")

        high, low = registers[0], registers[1]
        if byte_order == "little":
            high, low = low, high

        raw_bytes = struct.pack(">HH", high, low)

        if data_type == "uint32":
            return struct.unpack(">I", raw_bytes)[0]
        elif data_type == "int32":
            return struct.unpack(">i", raw_bytes)[0]
        elif data_type == "float32":
            return struct.unpack(">f", raw_bytes)[0]

    raise ValueError(f"Unsupported data_type: {data_type}")


def value_to_registers(value: int | float | bool, data_type: str, byte_order: str = "big") -> list[int]:
    """將 Python 值轉換為 raw register 值"""
    if data_type == "bool":
        return [bool(value)]

    if data_type == "uint16":
        return [int(value) & 0xFFFF]

    if data_type == "int16":
        v = int(value)
        if v < 0:
            v = v + 0x10000
        return [v & 0xFFFF]

    if data_type in ("uint32", "int32", "float32"):
        if data_type == "uint32":
            raw_bytes = struct.pack(">I", int(value))
        elif data_type == "int32":
            raw_bytes = struct.pack(">i", int(value))
        elif data_type == "float32":
            raw_bytes = struct.pack(">f", float(value))

        high = int.from_bytes(raw_bytes[0:2], "big")
        low = int.from_bytes(raw_bytes[2:4], "big")

        if byte_order == "little":
            return [low, high]
        return [high, low]

    raise ValueError(f"Unsupported data_type: {data_type}")


def register_count(data_type: str) -> int:
    """回傳此資料型別需要幾個 register"""
    if data_type in ("bool", "uint16", "int16"):
        return 1
    if data_type in ("uint32", "int32", "float32"):
        return 2
    raise ValueError(f"Unsupported data_type: {data_type}")
