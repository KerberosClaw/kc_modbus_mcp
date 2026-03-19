"""
MCP Tool 定義 — Profile 模式 + Raw 模式
"""

import json

from fastmcp import FastMCP

from .profile import ProfileManager
from .client import ModbusClientWrapper

mcp = FastMCP("kc-modbus-mcp")
profile_mgr = ProfileManager()
modbus_client = ModbusClientWrapper()


def init_tools(profile_path: str):
    """初始化 profile 並回傳 mcp 實例"""
    profile_mgr.load(profile_path)
    return mcp


# ============================================================
# Profile 模式
# ============================================================

@mcp.tool()
async def list_devices() -> str:
    """List all configured Modbus devices from the profile.
    列出所有已配置的 Modbus 設備。"""
    devices = profile_mgr.list_devices()
    return json.dumps(devices, indent=2, ensure_ascii=False)


@mcp.tool()
async def list_registers(device: str) -> str:
    """List all registers of a device with metadata.
    列出設備所有寄存器及其 metadata。

    Args:
        device: Device name from profile (e.g. "factory_sensor")
    """
    try:
        registers = profile_mgr.list_registers(device)
        return json.dumps(registers, indent=2, ensure_ascii=False)
    except KeyError as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
async def read_device(device: str, register: str) -> str:
    """Read a named register from a device. Returns converted value with unit.
    讀取設備的命名寄存器，回傳轉換後的值與單位。

    Args:
        device: Device name from profile (e.g. "factory_sensor")
        register: Register name (e.g. "temperature")
    """
    try:
        dev, reg = profile_mgr.get_register(device, register)
        result = await modbus_client.read_profile(dev, reg)
        return json.dumps(result, indent=2, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
async def write_device(device: str, register: str, value: float) -> str:
    """Write a value to a named register on a device.
    寫入值到設備的命名寄存器。

    Args:
        device: Device name from profile (e.g. "factory_sensor")
        register: Register name (e.g. "motor_speed")
        value: Value to write
    """
    try:
        dev, reg = profile_mgr.get_register(device, register)
        result = await modbus_client.write_profile(dev, reg, value)
        return json.dumps(result, indent=2, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
async def device_status(device: str) -> str:
    """Check if a device is online and reachable.
    檢查設備是否在線。

    Args:
        device: Device name from profile (e.g. "factory_sensor")
    """
    try:
        dev = profile_mgr.get_device(device)
        result = await modbus_client.check_connection(dev)
        return json.dumps(result, indent=2, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)})


# ============================================================
# Raw 模式
# ============================================================

@mcp.tool()
async def read_registers(host: str, port: int, slave_id: int,
                         function_code: int, address: int, count: int = 1) -> str:
    """Raw read: Read Modbus registers by address.
    Raw 模式：直接讀取 Modbus 寄存器。

    Args:
        host: Modbus device IP
        port: Modbus device port (usually 502)
        slave_id: Modbus slave/unit ID
        function_code: 1=coils, 2=discrete inputs, 3=holding, 4=input
        address: Starting register address
        count: Number of registers to read
    """
    try:
        result = await modbus_client.raw_read(host, port, slave_id, function_code, address, count)
        return json.dumps(result, indent=2, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
async def write_registers(host: str, port: int, slave_id: int,
                          function_code: int, address: int, values: list[int]) -> str:
    """Raw write: Write values to Modbus registers.
    Raw 模式：直接寫入 Modbus 寄存器。

    Args:
        host: Modbus device IP
        port: Modbus device port
        slave_id: Modbus slave/unit ID
        function_code: 1/5=coils, 3/6/16=holding registers
        address: Starting register address
        values: List of values to write
    """
    try:
        result = await modbus_client.raw_write(host, port, slave_id, function_code, address, values)
        return json.dumps(result, indent=2, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
async def scan_registers(host: str, port: int, slave_id: int,
                         start: int = 0, end: int = 100) -> str:
    """Scan a range of holding registers for non-zero values.
    掃描 holding register 位址範圍，找出有值的寄存器。

    Args:
        host: Modbus device IP
        port: Modbus device port
        slave_id: Modbus slave/unit ID
        start: Start address
        end: End address
    """
    try:
        result = await modbus_client.scan_registers(host, port, slave_id, start, end)
        return json.dumps(result, indent=2, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)})
