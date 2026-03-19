"""
profile 模組的單元測試 — 純 YAML 解析，不需要網路連線
"""

import pytest
from src.profile import ProfileManager, DeviceDef, RegisterDef


class TestProfileLoad:
    def test_load_success(self, loaded_profile):
        assert "test_device" in loaded_profile.devices

    def test_load_file_not_found(self):
        mgr = ProfileManager()
        with pytest.raises(FileNotFoundError):
            mgr.load("/nonexistent/path.yaml")

    def test_load_invalid_yaml(self, tmp_path):
        f = tmp_path / "bad.yaml"
        f.write_text("just_a_string: true\n")
        mgr = ProfileManager()
        with pytest.raises(ValueError, match="missing 'devices'"):
            mgr.load(f)

    def test_load_empty_file(self, tmp_path):
        f = tmp_path / "empty.yaml"
        f.write_text("")
        mgr = ProfileManager()
        with pytest.raises(ValueError, match="missing 'devices'"):
            mgr.load(f)


class TestDeviceParsing:
    def test_device_fields(self, loaded_profile):
        dev = loaded_profile.get_device("test_device")
        assert dev.host == "localhost"
        assert dev.port == 5020
        assert dev.slave_id == 1
        assert dev.byte_order == "big"

    def test_device_default_port(self, tmp_path):
        """沒指定 port 時應該預設 502"""
        yaml_content = "devices:\n  dev1:\n    host: 10.0.0.1\n    registers: {}\n"
        f = tmp_path / "d.yaml"
        f.write_text(yaml_content)
        mgr = ProfileManager()
        mgr.load(f)
        assert mgr.get_device("dev1").port == 502

    def test_register_count(self, loaded_profile):
        dev = loaded_profile.get_device("test_device")
        assert len(dev.registers) == 4


class TestRegisterParsing:
    def test_register_fields(self, loaded_profile):
        _, reg = loaded_profile.get_register("test_device", "temperature")
        assert reg.address == 0
        assert reg.function_code == 3
        assert reg.data_type == "float32"
        assert reg.unit == "°C"
        assert reg.access == "read"

    def test_register_defaults(self, tmp_path):
        """未指定的欄位應有預設值"""
        yaml_content = (
            "devices:\n  dev1:\n    host: x\n    registers:\n"
            "      reg1:\n        address: 0\n        function_code: 3\n"
        )
        f = tmp_path / "d.yaml"
        f.write_text(yaml_content)
        mgr = ProfileManager()
        mgr.load(f)
        _, reg = mgr.get_register("dev1", "reg1")
        assert reg.data_type == "uint16"
        assert reg.scale == 1.0
        assert reg.unit == ""
        assert reg.access == "read"


class TestGetDevice:
    def test_get_existing(self, loaded_profile):
        dev = loaded_profile.get_device("test_device")
        assert isinstance(dev, DeviceDef)

    def test_get_missing(self, loaded_profile):
        with pytest.raises(KeyError, match="not found"):
            loaded_profile.get_device("nonexistent")

    def test_get_missing_shows_available(self, loaded_profile):
        with pytest.raises(KeyError, match="test_device"):
            loaded_profile.get_device("nonexistent")


class TestGetRegister:
    def test_get_existing(self, loaded_profile):
        dev, reg = loaded_profile.get_register("test_device", "motor_speed")
        assert isinstance(dev, DeviceDef)
        assert isinstance(reg, RegisterDef)
        assert reg.access == "read_write"

    def test_get_missing_register(self, loaded_profile):
        with pytest.raises(KeyError, match="not found"):
            loaded_profile.get_register("test_device", "nonexistent_reg")

    def test_get_missing_device(self, loaded_profile):
        with pytest.raises(KeyError, match="not found"):
            loaded_profile.get_register("bad_device", "temperature")


class TestListMethods:
    def test_list_devices(self, loaded_profile):
        devices = loaded_profile.list_devices()
        assert len(devices) == 1
        assert devices[0]["name"] == "test_device"
        assert devices[0]["register_count"] == 4

    def test_list_registers(self, loaded_profile):
        regs = loaded_profile.list_registers("test_device")
        assert len(regs) == 4
        names = {r["name"] for r in regs}
        assert names == {"temperature", "motor_speed", "pump_on", "pressure"}

    def test_list_registers_bad_device(self, loaded_profile):
        with pytest.raises(KeyError):
            loaded_profile.list_registers("nonexistent")
