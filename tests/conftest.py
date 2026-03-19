"""
共用 fixtures — 提供 ProfileManager、模擬器、Modbus client 給所有測試使用
"""

import asyncio
import textwrap
from pathlib import Path

import pytest

from src.profile import ProfileManager
from src.client import ModbusClientWrapper


# ── 測試用 YAML profile ────────────────────────────────────────

SAMPLE_YAML = textwrap.dedent("""\
    devices:
      test_device:
        host: localhost
        port: 5020
        slave_id: 1
        byte_order: big
        registers:
          temperature:
            address: 0
            function_code: 3
            data_type: float32
            scale: 1.0
            unit: "°C"
            access: read
            description: "Temperature sensor"
          motor_speed:
            address: 4
            function_code: 3
            data_type: uint16
            scale: 1.0
            unit: "RPM"
            access: read_write
            description: "Motor speed"
          pump_on:
            address: 0
            function_code: 1
            data_type: bool
            access: read_write
            description: "Pump switch"
          pressure:
            address: 0
            function_code: 4
            data_type: uint16
            unit: "kPa"
            access: read
            description: "Pipe pressure"
""")


@pytest.fixture
def sample_yaml_file(tmp_path) -> Path:
    """建立暫時的 YAML 設備描述檔"""
    f = tmp_path / "devices.yaml"
    f.write_text(SAMPLE_YAML, encoding="utf-8")
    return f


@pytest.fixture
def loaded_profile(sample_yaml_file) -> ProfileManager:
    """已載入的 ProfileManager"""
    mgr = ProfileManager()
    mgr.load(sample_yaml_file)
    return mgr


@pytest.fixture
def modbus_client():
    """ModbusClientWrapper 實例，測試結束後自動關閉"""
    client = ModbusClientWrapper()
    yield client
    # teardown: 關閉所有連線
    asyncio.get_event_loop().run_until_complete(client.close_all())
