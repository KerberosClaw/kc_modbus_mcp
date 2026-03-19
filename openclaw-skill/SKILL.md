---
name: modbus
description: "Read and write Modbus TCP device registers via MCP Server. Control PLCs, sensors, and actuators by name."
version: 1.0.0
---

# Modbus TCP Control

You have access to a Modbus TCP MCP Server that can read/write industrial device registers.

## Available Commands

- `modbus list` — List all configured devices
- `modbus status <device>` — Check if a device is online
- `modbus read <device> <register>` — Read a register value
- `modbus write <device> <register> <value>` — Write a value to a register
- `modbus registers <device>` — List all registers of a device

## Examples

```
modbus list
modbus status factory_sensor
modbus read factory_sensor temperature
modbus write factory_sensor motor_speed 1500
modbus read factory_sensor pump_on
modbus write factory_sensor pump_on true
```

## Notes

- Device names and register names are defined in `devices.yaml`
- Read-only registers cannot be written to
- Values are automatically converted to the correct data type and scale
