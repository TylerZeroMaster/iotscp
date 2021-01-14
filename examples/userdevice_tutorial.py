import logging
from time import sleep

from iotscp.core.services import (
    Service,
    ServiceArg,
    ServiceMethod,
    ServiceEvent
)
from iotscp.core.basedevice import BaseDevice

""" Service methods follow this pattern:
    def whatever_you_name_it(device, [kwargs]):
        ...
        return dict(argname=argvalue)
            or
        return {"arg name": argvalue}
"""
def get_binary_state(device):
    return dict(BinaryState=device.binarystate)

""" When defining a service, you can manually specify the `name`,
`control_url`, and `event_url`. They default to '{CLASSNAME}',
'/control/{CLASSNAME}/', and '/event/{CLASSNAME}/' respectively.
"""
class Sensor(Service):
    events = [
        ServiceEvent(
            "BinaryState",
            ServiceArg("BinaryState", bool),
            doc="Get `BinaryState` notifications when the motion sensor detects motion"
        )
    ]
    methods = [
        ServiceMethod(
            "GetBinaryState",
            get_binary_state,
            returns=ServiceArg("BinaryState", bool),
            doc="Get the `BinaryState` of the motion sensor"
        )
    ]

class Device(BaseDevice):
    name = "PiMotion"
    device_type = "Motion_Sensor"
    namespace = "NullPiProjects"
    mac_address = "01:23:45:AB:CD:EF"
    services = [Sensor()]
    # Optionally define a preferred hashing algorithm to optomize for your platform
    # in this case, the ARM processor in my RPi B+ doesn't deal with 64 bit algorithms well
    # so I made the preferred algorithm 32 bit (sha256)
    pref_alg = "sha256"
    binarystate = False

""" The main function takes two arguments: the device and a stop event.
Your main loop should terminate when the stop event is set.

In this example, a pointer to the "Sensor" service is stored in the
sensor_service variable. Next, device.services[sensor_service] is used
to obtain a reference to the service. From there, send_event takes two
args: service_name (BinaryState) and **kwargs (BinaryState=state).
It is important that the names of the kwargs match what is defined
in the service event. That's all there is to it. If you want to see
a real example, look at the PIR_Sensor example.
"""
def main(device, stop):
    from random import randint
    state = False
    sensor_service = device.get_service_ptr("Sensor")
    while not stop.is_set():
        rng = randint(0, 100)
        if rng > 0 and rng < 30:
            state = not state
            device.services[sensor_service].send_event(
                "BinaryState",
                BinaryState=state
            )
            device.binarystate = state
        sleep(2)

# To test this exmaple, rename this file to userdevice.py, and put it in the
# same directory as __main__.py
