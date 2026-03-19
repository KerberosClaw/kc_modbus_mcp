"""
Modbus TCP Client 封裝 — 基於 pymodbus async client
"""

import logging

from pymodbus.client import AsyncModbusTcpClient
from pymodbus import FramerType

from .converter import registers_to_value, value_to_registers, register_count
from .profile import DeviceDef, RegisterDef

log = logging.getLogger("modbus-client")


class ModbusClientWrapper:
    """封裝 pymodbus async client，提供 profile-aware 讀寫"""

    def __init__(self):
        self._clients: dict[str, AsyncModbusTcpClient] = {}

    async def _get_client(self, host: str, port: int) -> AsyncModbusTcpClient:
        """取得或建立 client 連線"""
        key = f"{host}:{port}"
        if key in self._clients and self._clients[key].connected:
            return self._clients[key]

        client = AsyncModbusTcpClient(
            host=host,
            port=port,
            framer=FramerType.SOCKET,
            timeout=5,
        )
        await client.connect()
        if not client.connected:
            raise ConnectionError(f"Cannot connect to {host}:{port}")

        self._clients[key] = client
        log.info(f"Connected to {host}:{port}")
        return client

    async def close_all(self):
        """關閉所有連線"""
        for key, client in self._clients.items():
            client.close()
            log.info(f"Closed connection to {key}")
        self._clients.clear()

    # --- Profile 模式 ---

    async def read_profile(self, device: DeviceDef, register: RegisterDef) -> dict:
        """用 profile 讀取寄存器，回傳轉換後的值"""
        client = await self._get_client(device.host, device.port)
        fc = register.function_code
        count = register_count(register.data_type)

        if fc == 1:
            rr = await client.read_coils(register.address, count=count, device_id=device.slave_id)
        elif fc == 2:
            rr = await client.read_discrete_inputs(register.address, count=count, device_id=device.slave_id)
        elif fc == 3:
            rr = await client.read_holding_registers(register.address, count=count, device_id=device.slave_id)
        elif fc == 4:
            rr = await client.read_input_registers(register.address, count=count, device_id=device.slave_id)
        else:
            raise ValueError(f"Unsupported read function code: {fc}")

        if rr.isError():
            raise RuntimeError(f"Modbus error reading {register.name}: {rr}")

        # 取得 raw 值
        if fc in (1, 2):
            raw_values = rr.bits[:count]
        else:
            raw_values = rr.registers[:count]

        # 轉換
        value = registers_to_value(raw_values, register.data_type, device.byte_order)

        # 套用 scale
        if register.scale != 1.0 and isinstance(value, (int, float)):
            value = round(value * register.scale, 4)

        return {
            "device": device.name,
            "register": register.name,
            "value": value,
            "unit": register.unit,
            "data_type": register.data_type,
            "raw": raw_values,
        }

    async def write_profile(self, device: DeviceDef, register: RegisterDef, value) -> dict:
        """用 profile 寫入寄存器"""
        if register.access != "read_write":
            raise PermissionError(
                f"Register '{register.name}' is {register.access}, cannot write"
            )

        client = await self._get_client(device.host, device.port)
        fc = register.function_code

        if fc == 1:
            # 寫 coil
            rr = await client.write_coil(register.address, bool(value), device_id=device.slave_id)
        elif fc == 3:
            # 寫 holding register(s)
            write_value = value
            if register.scale != 1.0:
                write_value = value / register.scale

            regs = value_to_registers(write_value, register.data_type, device.byte_order)
            if len(regs) == 1:
                rr = await client.write_register(register.address, regs[0], device_id=device.slave_id)
            else:
                rr = await client.write_registers(register.address, regs, device_id=device.slave_id)
        else:
            raise ValueError(f"Cannot write to function code {fc}")

        if rr.isError():
            raise RuntimeError(f"Modbus error writing {register.name}: {rr}")

        return {
            "device": device.name,
            "register": register.name,
            "written": value,
            "unit": register.unit,
        }

    async def check_connection(self, device: DeviceDef) -> dict:
        """測試設備連線狀態"""
        try:
            client = await self._get_client(device.host, device.port)
            # 嘗試讀一個 register 確認通訊正常
            rr = await client.read_holding_registers(0, count=1, device_id=device.slave_id)
            online = not rr.isError()
        except Exception:
            online = False

        return {
            "device": device.name,
            "host": device.host,
            "port": device.port,
            "slave_id": device.slave_id,
            "online": online,
        }

    # --- Raw 模式 ---

    async def raw_read(self, host: str, port: int, slave_id: int,
                       function_code: int, address: int, count: int) -> dict:
        """Raw 寄存器讀取"""
        client = await self._get_client(host, port)

        if function_code == 1:
            rr = await client.read_coils(address, count=count, device_id=slave_id)
            values = rr.bits[:count] if not rr.isError() else None
        elif function_code == 2:
            rr = await client.read_discrete_inputs(address, count=count, device_id=slave_id)
            values = rr.bits[:count] if not rr.isError() else None
        elif function_code == 3:
            rr = await client.read_holding_registers(address, count=count, device_id=slave_id)
            values = rr.registers[:count] if not rr.isError() else None
        elif function_code == 4:
            rr = await client.read_input_registers(address, count=count, device_id=slave_id)
            values = rr.registers[:count] if not rr.isError() else None
        else:
            raise ValueError(f"Unsupported function code: {function_code}")

        if rr.isError():
            raise RuntimeError(f"Modbus error: {rr}")

        return {
            "host": host,
            "port": port,
            "slave_id": slave_id,
            "function_code": function_code,
            "address": address,
            "count": count,
            "values": values,
        }

    async def raw_write(self, host: str, port: int, slave_id: int,
                        function_code: int, address: int, values: list) -> dict:
        """Raw 寄存器寫入"""
        client = await self._get_client(host, port)

        if function_code in (1, 5):
            if len(values) == 1:
                rr = await client.write_coil(address, bool(values[0]), device_id=slave_id)
            else:
                rr = await client.write_coils(address, [bool(v) for v in values], device_id=slave_id)
        elif function_code in (3, 6, 16):
            if len(values) == 1:
                rr = await client.write_register(address, int(values[0]), device_id=slave_id)
            else:
                rr = await client.write_registers(address, [int(v) for v in values], device_id=slave_id)
        else:
            raise ValueError(f"Unsupported write function code: {function_code}")

        if rr.isError():
            raise RuntimeError(f"Modbus error: {rr}")

        return {
            "host": host,
            "port": port,
            "slave_id": slave_id,
            "function_code": function_code,
            "address": address,
            "written": values,
        }

    async def scan_registers(self, host: str, port: int, slave_id: int,
                             start: int = 0, end: int = 100) -> dict:
        """掃描位址範圍，找出有非零值的寄存器"""
        client = await self._get_client(host, port)
        found = []

        for addr in range(start, end):
            try:
                rr = await client.read_holding_registers(addr, count=1, device_id=slave_id)
                if not rr.isError() and rr.registers[0] != 0:
                    found.append({"address": addr, "value": rr.registers[0]})
            except Exception:
                continue

        return {
            "host": host,
            "port": port,
            "slave_id": slave_id,
            "scanned_range": f"{start}-{end}",
            "found": found,
        }
