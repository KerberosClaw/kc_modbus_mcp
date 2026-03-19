"""
converter 模組的單元測試

測試策略：
  - 每種 data_type 各一組 happy path
  - 驗證 registers_to_value ↔ value_to_registers 可以往返轉換 (round-trip)
  - 邊界值 & 錯誤處理
"""

import struct
import pytest
from src.converter import registers_to_value, value_to_registers, register_count


# ── registers_to_value ──────────────────────────────────────────

class TestRegistersToValue:
    def test_bool_true(self):
        assert registers_to_value([1], "bool") is True

    def test_bool_false(self):
        assert registers_to_value([0], "bool") is False

    def test_uint16(self):
        assert registers_to_value([65535], "uint16") == 65535

    def test_int16_positive(self):
        assert registers_to_value([100], "int16") == 100

    def test_int16_negative(self):
        # 0xFFFF = 65535 → 應轉為 -1
        assert registers_to_value([0xFFFF], "int16") == -1

    def test_uint32(self):
        # 70000 = 0x00011170 → high=1, low=4464
        regs = [1, 4464]
        assert registers_to_value(regs, "uint32") == 70000

    def test_int32_negative(self):
        # -1 = 0xFFFFFFFF → high=0xFFFF, low=0xFFFF
        assert registers_to_value([0xFFFF, 0xFFFF], "int32") == -1

    def test_float32(self):
        # 25.0 in IEEE 754 → 0x41C80000 → high=0x41C8, low=0x0000
        high, low = struct.unpack(">HH", struct.pack(">f", 25.0))
        result = registers_to_value([high, low], "float32")
        assert result == pytest.approx(25.0)

    def test_float32_little_endian(self):
        high, low = struct.unpack(">HH", struct.pack(">f", 25.0))
        # little endian: 傳入順序反過來
        result = registers_to_value([low, high], "float32", byte_order="little")
        assert result == pytest.approx(25.0)

    def test_32bit_too_few_registers(self):
        with pytest.raises(ValueError, match="requires 2 registers"):
            registers_to_value([1], "float32")

    def test_unsupported_type(self):
        with pytest.raises(ValueError, match="Unsupported"):
            registers_to_value([1], "float64")


# ── value_to_registers ──────────────────────────────────────────

class TestValueToRegisters:
    def test_bool(self):
        assert value_to_registers(True, "bool") == [True]

    def test_uint16(self):
        assert value_to_registers(1500, "uint16") == [1500]

    def test_int16_negative(self):
        regs = value_to_registers(-1, "int16")
        assert regs == [0xFFFF]

    def test_float32(self):
        regs = value_to_registers(25.0, "float32")
        assert len(regs) == 2

    def test_unsupported_type(self):
        with pytest.raises(ValueError, match="Unsupported"):
            value_to_registers(1, "float64")


# ── round-trip：寫入後讀回應該得到相同值 ────────────────────────

class TestRoundTrip:
    @pytest.mark.parametrize("value, data_type", [
        (True, "bool"),
        (False, "bool"),
        (0, "uint16"),
        (65535, "uint16"),
        (100, "int16"),
        (-100, "int16"),
        (70000, "uint32"),
        (-12345, "int32"),
        (25.125, "float32"),
    ])
    def test_round_trip_big_endian(self, value, data_type):
        regs = value_to_registers(value, data_type, byte_order="big")
        result = registers_to_value(regs, data_type, byte_order="big")
        if data_type == "float32":
            assert result == pytest.approx(value)
        else:
            assert result == value

    @pytest.mark.parametrize("data_type", ["uint32", "int32", "float32"])
    def test_round_trip_little_endian(self, data_type):
        value = 12345 if data_type != "float32" else 12.5
        regs = value_to_registers(value, data_type, byte_order="little")
        result = registers_to_value(regs, data_type, byte_order="little")
        if data_type == "float32":
            assert result == pytest.approx(value)
        else:
            assert result == value


# ── register_count ──────────────────────────────────────────────

class TestRegisterCount:
    @pytest.mark.parametrize("data_type, expected", [
        ("bool", 1),
        ("uint16", 1),
        ("int16", 1),
        ("uint32", 2),
        ("int32", 2),
        ("float32", 2),
    ])
    def test_known_types(self, data_type, expected):
        assert register_count(data_type) == expected

    def test_unsupported(self):
        with pytest.raises(ValueError):
            register_count("string")
