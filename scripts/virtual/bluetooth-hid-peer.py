"""Synthetic keyboard/mouse reports through the pinned official Bumble HID SDK.

Only a disposable virtual-machine fixture may run this peer. The caller owns
stdin/stdout and selects key usages; no Bluetooth protocol is implemented here.
SDK pin and virtual controller setup are supplied by the acceptance runner.
"""

import asyncio
import json
import logging
import os
import subprocess
import sys
from pathlib import Path

from bumble import hid, sdp
from bumble.device import Device
from bumble.pairing import PairingConfig, PairingDelegate
from bumble.transport import open_transport


class Reports(hid.Device.Delegate):
    def __init__(self):
        self.keyboard = bytes([1] + [0] * 8)
        self.mouse = bytes([2, 0, 0, 0])

    def get_report(self, report_type, report_id):
        if report_type == hid.ReportType.INPUT_REPORT and report_id in (1, 2):
            return (self.keyboard if report_id == 1 else self.mouse)[1:]
        raise hid.HidProtocolError(hid.HandshakeMessage.ResultCode.ERR_UNSUPPORTED_REQUEST)

    def set_report(self, report_type, data):
        if report_type != hid.ReportType.OUTPUT_REPORT:
            raise hid.HidProtocolError(hid.HandshakeMessage.ResultCode.ERR_UNSUPPORTED_REQUEST)


async def main():
    if os.geteuid() != 0 or not Path("/etc/rampi-acceptance-vm").is_file():
        raise SystemExit("Designated disposable QEMU guest required")
    subprocess.run(["systemd-detect-virt", "--vm", "--quiet"], check=True)
    async with asyncio.timeout(600):
        async with await open_transport("hci-socket:1") as transport:
            device = Device.from_config_file_with_hci(
                "/run/rampi-bumble-device.json", transport.source, transport.sink
            )
            device.classic_enabled = True
            device.le_enabled = False
            device.pairing_config_factory = lambda _: PairingConfig(
                mitm=False,
                bonding=True,
                delegate=PairingDelegate(PairingDelegate.NO_OUTPUT_NO_INPUT),
            )
            reports = Reports()
            interface = hid.Device(device, delegate=reports)
            device.sdp_service_records = {
                0x10002: hid.DeviceSdpRecord(
                    service_record_handle=0x10002, report_map=hid.DEFAULT_REPORT_MAP
                ).to_service_attributes()
            }
            # The pinned SDK uses UINT16 for ClassDescriptorType. BlueZ's existing
            # HID parser requires UINT8 (profiles/input/device.c:extract_hid_desc_data).
            # Adapt fixture metadata through the SDK's own SDP data types only.
            attributes = device.sdp_service_records[0x10002]
            attributes = [
                sdp.ServiceAttribute(
                    attribute.id,
                    sdp.DataElement.sequence(
                        [
                            sdp.DataElement.sequence(
                                [
                                    sdp.DataElement.unsigned_integer_8(0x22),
                                    sdp.DataElement(
                                        sdp.DataElement.TEXT_STRING, hid.DEFAULT_REPORT_MAP
                                    ),
                                ]
                            )
                        ]
                    )
                    if attribute.id == hid.AttributeId.DESCRIPTOR_LIST
                    else sdp.DataElement.unsigned_integer_16(0x0111)
                    if attribute.id == hid.AttributeId.PARSER_VERSION
                    else sdp.DataElement.unsigned_integer_8(0xC0)
                    if attribute.id == hid.AttributeId.DEVICE_SUBCLASS
                    else sdp.DataElement.unsigned_integer_8(0x21)
                    if attribute.id == hid.AttributeId.COUNTRY_CODE
                    else attribute.value,
                )
                for attribute in attributes
            ]
            device.sdp_service_records[0x10002] = attributes
            await device.power_on()
            await device.set_discoverable(True)
            await device.set_connectable(True)
            print(
                json.dumps({"ready": True, "address": str(device.public_address).split("/")[0]}),
                flush=True,
            )
            reader = asyncio.StreamReader()
            await asyncio.get_running_loop().connect_read_pipe(
                lambda: asyncio.StreamReaderProtocol(reader), sys.stdin
            )
            while line := await reader.readline():
                command = json.loads(line)
                if command["action"] == "state":
                    result = {
                        "channels": interface.control_channel is not None
                        and interface.interrupt_channel is not None
                    }
                elif command["action"] == "keyboard":
                    if interface.interrupt_channel is None:
                        raise RuntimeError("Real HID interrupt channel missing")
                    usage = command.get("usage", 4)
                    modifiers = command.get("modifiers", 0)
                    if type(usage) is not int or not 4 <= usage <= 0xE7:
                        raise ValueError("Invalid synthetic HID usage")
                    if type(modifiers) is not int or not 0 <= modifiers <= 255:
                        raise ValueError("Invalid synthetic HID modifiers")
                    for active in (True, False):
                        reports.keyboard = bytes(
                            [
                                1,
                                modifiers if active else 0,
                                0,
                                usage if active else 0,
                                0,
                                0,
                                0,
                                0,
                                0,
                            ]
                        )
                        interface.send_interrupt_data(reports.keyboard)
                        await asyncio.sleep(0.15)
                    result = {"sent": "keyboard", "usage": usage, "modifiers": modifiers}
                elif command["action"] == "mouse":
                    if interface.interrupt_channel is None:
                        raise RuntimeError("Real HID interrupt channel missing")
                    for report in ([2, 0, 8, 250], [2, 1, 0, 0], [2, 0, 0, 0]):
                        reports.mouse = bytes(report)
                        interface.send_interrupt_data(reports.mouse)
                        await asyncio.sleep(0.15)
                    result = {"sent": "mouse"}
                elif command["action"] == "quit":
                    break
                else:
                    raise RuntimeError("Unsupported fixture command")
                print(json.dumps(result), flush=True)


logging.basicConfig(level=logging.DEBUG, stream=sys.stderr)
asyncio.run(main())
