"""
設備描述檔管理器 — 載入 YAML、解析寄存器映射
"""

from pathlib import Path
from dataclasses import dataclass, field

import yaml


@dataclass
class RegisterDef:
    """單一寄存器定義"""
    name: str
    address: int
    function_code: int
    data_type: str = "uint16"
    scale: float = 1.0
    unit: str = ""
    access: str = "read"
    description: str = ""


@dataclass
class DeviceDef:
    """單一設備定義"""
    name: str
    host: str
    port: int = 502
    slave_id: int = 1
    byte_order: str = "big"
    registers: dict[str, RegisterDef] = field(default_factory=dict)


class ProfileManager:
    """載入並管理 devices.yaml"""

    def __init__(self):
        self.devices: dict[str, DeviceDef] = {}

    def load(self, path: str | Path):
        """從 YAML 檔載入設備描述"""
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Profile not found: {path}")

        with open(path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f)

        if not raw or "devices" not in raw:
            raise ValueError(f"Invalid profile: missing 'devices' key in {path}")

        for dev_name, dev_data in raw["devices"].items():
            registers = {}
            for reg_name, reg_data in dev_data.get("registers", {}).items():
                registers[reg_name] = RegisterDef(
                    name=reg_name,
                    address=reg_data["address"],
                    function_code=reg_data["function_code"],
                    data_type=reg_data.get("data_type", "uint16"),
                    scale=reg_data.get("scale", 1.0),
                    unit=reg_data.get("unit", ""),
                    access=reg_data.get("access", "read"),
                    description=reg_data.get("description", ""),
                )

            self.devices[dev_name] = DeviceDef(
                name=dev_name,
                host=dev_data["host"],
                port=dev_data.get("port", 502),
                slave_id=dev_data.get("slave_id", 1),
                byte_order=dev_data.get("byte_order", "big"),
                registers=registers,
            )

    def get_device(self, name: str) -> DeviceDef:
        """取得設備定義"""
        if name not in self.devices:
            available = ", ".join(self.devices.keys()) or "(none)"
            raise KeyError(f"Device '{name}' not found. Available: {available}")
        return self.devices[name]

    def get_register(self, device_name: str, register_name: str) -> tuple[DeviceDef, RegisterDef]:
        """取得設備 + 寄存器定義"""
        device = self.get_device(device_name)
        if register_name not in device.registers:
            available = ", ".join(device.registers.keys()) or "(none)"
            raise KeyError(
                f"Register '{register_name}' not found on device '{device_name}'. "
                f"Available: {available}"
            )
        return device, device.registers[register_name]

    def list_devices(self) -> list[dict]:
        """列出所有設備摘要"""
        result = []
        for dev in self.devices.values():
            result.append({
                "name": dev.name,
                "host": dev.host,
                "port": dev.port,
                "slave_id": dev.slave_id,
                "register_count": len(dev.registers),
            })
        return result

    def list_registers(self, device_name: str) -> list[dict]:
        """列出設備所有寄存器"""
        device = self.get_device(device_name)
        result = []
        for reg in device.registers.values():
            result.append({
                "name": reg.name,
                "address": reg.address,
                "function_code": reg.function_code,
                "data_type": reg.data_type,
                "unit": reg.unit,
                "access": reg.access,
                "description": reg.description,
            })
        return result
