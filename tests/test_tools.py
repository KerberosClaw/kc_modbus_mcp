"""
MCP tools 模組的測試 — 驗證 tool 函數的回傳格式

Profile 模式的 tool 需要模擬器；
list_devices / list_registers 只需要 profile，不需要網路。
"""

import json
import pytest

from src.tools import init_tools, profile_mgr, list_devices, list_registers, read_device, write_device, device_status


# ── Profile-only tools (不需要模擬器) ──────────────────────────

class TestProfileOnlyTools:
    @pytest.fixture(autouse=True)
    def setup_profile(self, sample_yaml_file):
        """每個測試前重新載入 profile"""
        profile_mgr.devices.clear()
        profile_mgr.load(sample_yaml_file)

    async def test_list_devices_returns_json(self):
        result = await list_devices()
        data = json.loads(result)
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["name"] == "test_device"

    async def test_list_registers_returns_json(self):
        result = await list_registers("test_device")
        data = json.loads(result)
        assert isinstance(data, list)
        assert len(data) == 4

    async def test_list_registers_bad_device(self):
        result = await list_registers("nonexistent")
        data = json.loads(result)
        assert "error" in data

    async def test_read_device_no_simulator(self):
        """模擬器沒跑的話，read_device 應回傳 error JSON 而非 crash"""
        result = await read_device("test_device", "temperature")
        data = json.loads(result)
        # 不管成功或失敗，都應該是合法 JSON
        assert isinstance(data, dict)

    async def test_write_device_no_simulator(self):
        result = await write_device("test_device", "motor_speed", 100)
        data = json.loads(result)
        assert isinstance(data, dict)

    async def test_device_status_no_simulator(self):
        result = await device_status("test_device")
        data = json.loads(result)
        assert isinstance(data, dict)
