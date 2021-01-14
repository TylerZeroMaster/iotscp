import logging
from threading import Event, Thread
from time import sleep

import userdevice
from arg_parser import parse_args
from iotscp.http.udpserver import UDPServer
from iotscp.http.serializer import serialize
from iotscp.http.deviceserver import DeviceServer

try:
    input = raw_input
except:
    pass

def config_logging(filename, loglvl):
    logargs = {
        "format": (
            "[%(levelname)s] <%(asctime)s> %(module)s->%(funcName)s\n"
            "   %(message)s"
        ),
        "level": getattr(logging, loglvl, logging.INFO)
    }
    if filename != "":
        logargs["filename"] = filename
    logging.basicConfig(**logargs)

def start_server(args):
    config_logging(args.logfile, args.loglvl)
    stop = Event()
    device = userdevice.Device(stop)
    serialize(device)
    DeviceServer(stop, args.port, device).start()
    UDPServer(stop, args.port).start()
    Thread(target=userdevice.main, args=(device, stop)).start()
    while True:
        command = input("Type `help` for a list of commands\n")
        if command == "help":
            print("`shutdown` causes the server to shutdown")
        if command == "shutdown":
            logging.info("Shutting down; this will take some time.")
            stop.set()
            break

def get_cert(args):
    import iotscp.core.sccertificate
    iotscp.core.sccertificate.generate_certificate(*args.certsize)

def main():
    args = parse_args()
    if args.action == "start":
        start_server(args)
    elif args.action == "get_cert":
        get_cert(args)

if __name__ == "__main__":
    main()
