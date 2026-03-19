"""
client 模組的整合測試 — 需要模擬器在 localhost:5020 執行

執行方式：
  1. 先啟動模擬器: uv run python simulator.py &
  2. 跑測試: uv run python -m pytest tests/test_client.py -v

如果模擬器沒跑，這些測試會被自動 skip。
"""

import asyncio
import pytest
from pymodbus.client import AsyncModbusTcpClient

from src.client import ModbusClientWrapper
from src.profile import DeviceDef, RegisterDef


# ── 偵測模擬器是否在線 ──────────────────────────────────────────

def _check_simulator() -> bool:
    async def _probe():
        try:
            client = AsyncModbusTcpClient(host="localhost", port=5020, timeout=2)
            await client.connect()
            available = client.connected
            client.close()
            return available
        except Exception:
            return False
    return asyncio.run(_probe())

SIMULATOR_UP = _check_simulator()
requires_simulator = pytest.mark.skipif(
    not SIMULATOR_UP, reason="Simulator not running on localhost:5020"
)


# ── Fixtures ────────────────────────────────────────────────────

@pytest.fixture
def device() -> DeviceDef:
    return DeviceDef(
        name="test_device",
        host="localhost",
        port=5020,
        slave_id=1,
        byte_order="big",
    )


@pytest.fixture
def temp_register() -> RegisterDef:
    return RegisterDef(
        name="temperature",
        address=0,
        function_code=3,
        data_type="float32",
        unit="°C",
        access="read",
    )


@pytest.fixture
def motor_register() -> RegisterDef:
    return RegisterDef(
        name="motor_speed",
        address=4,
        function_code=3,
        data_type="uint16",
        unit="RPM",
        access="read_write",
    )


@pytest.fixture
def pump_register() -> RegisterDef:
    return RegisterDef(
        name="pump_on",
        address=0,
        function_code=1,
        data_type="bool",
        access="read_write",
    )


@pytest.fixture
def pressure_register() -> RegisterDef:
    return RegisterDef(
        name="pressure",
        address=0,
        function_code=4,
        data_type="uint16",
        unit="kPa",
        access="read",
    )


@pytest.fixture
async def client():
    c = ModbusClientWrapper()
    yield c
    await c.close_all()


# ── Profile 模式讀取 ────────────────────────────────────────────

@requires_simulator
class TestProfileRead:
    async def test_read_float32(self, client, device, temp_register):
        result = await client.read_profile(device, temp_register)
        assert result["device"] == "test_device"
        assert result["register"] == "temperature"
        assert result["unit"] == "°C"
        # 模擬器溫度範圍 20~30°C
        assert 15.0 <= result["value"] <= 35.0

    async def test_read_uint16_input_register(self, client, device, pressure_register):
        result = await client.read_profile(device, pressure_register)
        assert result["register"] == "pressure"
        assert result["unit"] == "kPa"
        assert isinstance(result["value"], int)

    async def test_read_coil(self, client, device, pump_register):
        result = await client.read_profile(device, pump_register)
        assert result["register"] == "pump_on"
        assert isinstance(result["value"], bool)


# ── Profile 模式寫入 ────────────────────────────────────────────

@requires_simulator
class TestProfileWrite:
    async def test_write_uint16(self, client, device, motor_register):
        # 寫入
        write_result = await client.write_profile(device, motor_register, 1500)
        assert write_result["written"] == 1500

        # 讀回驗證
        read_result = await client.read_profile(device, motor_register)
        assert read_result["value"] == 1500

    async def test_write_coil(self, client, device, pump_register):
        await client.write_profile(device, pump_register, True)
        result = await client.read_profile(device, pump_register)
        assert result["value"] is True

        await client.write_profile(device, pump_register, False)
        result = await client.read_profile(device, pump_register)
        assert result["value"] is False

    async def test_write_readonly_rejected(self, client, device, temp_register):
        with pytest.raises(PermissionError, match="cannot write"):
            await client.write_profile(device, temp_register, 99.0)


# ── 連線測試 ────────────────────────────────────────────────────

@requires_simulator
class TestConnection:
    async def test_check_connection_online(self, client, device):
        result = await client.check_connection(device)
        assert result["online"] is True

    async def test_check_connection_offline(self, client):
        offline_device = DeviceDef(name="offline", host="localhost", port=59999)
        result = await client.check_connection(offline_device)
        assert result["online"] is False

    async def test_connection_caching(self, client, device, temp_register):
        """連續兩次讀取應複用同一個 client"""
        await client.read_profile(device, temp_register)
        await client.read_profile(device, temp_register)
        assert len(client._clients) == 1


# ── Raw 模式 ────────────────────────────────────────────────────

@requires_simulator
class TestRawMode:
    async def test_raw_read_holding(self, client):
        result = await client.raw_read("localhost", 5020, 1, 3, 0, 2)
        assert result["function_code"] == 3
        assert len(result["values"]) == 2

    async def test_raw_write_and_read(self, client):
        await client.raw_write("localhost", 5020, 1, 3, 4, [2000])
        result = await client.raw_read("localhost", 5020, 1, 3, 4, 1)
        assert result["values"] == [2000]

    async def test_raw_read_coils(self, client):
        result = await client.raw_read("localhost", 5020, 1, 1, 0, 2)
        assert len(result["values"]) == 2

    async def test_raw_unsupported_fc(self, client):
        with pytest.raises(ValueError, match="Unsupported"):
            await client.raw_read("localhost", 5020, 1, 99, 0, 1)

    async def test_scan_registers(self, client):
        # 先寫入一個已知值
        await client.raw_write("localhost", 5020, 1, 3, 4, [999])
        result = await client.scan_registers("localhost", 5020, 1, start=0, end=10)
        assert result["scanned_range"] == "0-10"
        # 至少能找到 temperature 的 float32 register 和 motor_speed
        assert len(result["found"]) > 0
