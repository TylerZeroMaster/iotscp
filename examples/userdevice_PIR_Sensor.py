import logging
from time import sleep

from iotscp.core.services import (
    Service,
    ServiceArg,
    ServiceMethod,
    ServiceEvent
)
from iotscp.core.basedevice import BaseDevice
import RPi.GPIO as io

LED = 21
PIR = 16

def motion_detected(service, device, state):
    service.send_event(BinaryState=state)
    io.output(LED, state)
    device.binarystate = state

def get_binary_state(device):
    return dict(BinaryState=device.binarystate)

class Sensor(Service):
    events = [
        ServiceEvent(
            "BinaryState",
            ServiceArg("BinaryState", bool)
        )
    ]
    methods = [
        ServiceMethod(
            "GetBinaryState",
            get_binary_state,
            returns=ServiceArg("BinaryState", bool)
        )
    ]

class Device(BaseDevice):
    name = "PiMotion"
    device_type = "Motion_Sensor"
    namespace = "NullPiProjects"
    mac_address = "01:23:45:AB:CD:EF"
    services = [Sensor()]
    binarystate = False

def main(device, stop):
    from random import randint
    io.setmode(io.BCM)
    io.setup(PIR, io.IN)
    io.setup(LED, io.OUT)
    sensor_service = device.get_service_ptr("Sensor")
    while not stop.is_set():
        if io.input(PIR):
            motion_detected(device.services[sensor_service], device, True)
            while io.input(PIR):
                sleep(2)
            motion_detected(device.services[sensor_service], device, False)
        else:
            sleep(1)
    io.output(LED, False)
    io.cleanup()
