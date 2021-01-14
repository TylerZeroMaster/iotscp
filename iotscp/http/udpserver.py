import socket
import logging
from struct import pack
from select import select
from threading import Thread
from time import gmtime, strftime

from .httpbase import httputil, LISTEN_TIMEOUT
from ..utils import get_address

MCAST_ADDR = "239.255.255.250"
MCAST_PORT = 1900

"""
Example of IOTSCP discovery HTTP head

IOT-SEARCH * HTTP/1.1
Host: 239.255.255.250:1900
Return: device; type=basedevice
SV: iotscp:discover

"""

# This is bare bones right now. In the future, I want the
# return header to be more useful as a query operator
# for example: "supports; method=setbinarystate" to get devices
# that implement `setbinarystate`
def should_respond(head_str):
    """should_respond(head_str) -> should_respond_bool

    Determines, based on information in the response head, weither or not the
    UDPServer should respond to a client
    """
    reqline = httputil.RE_REQLINE.match(head_str)
    if reqline is not None and reqline.group(1) == "IOT-SEARCH":
        headers = httputil.parse_headers(head_str)
        if "host" in headers and "sv" in headers and "return" in headers:
            return (headers["host"] == "239.255.255.250:1900"
                    and headers["sv"] == "iotscp:discover"
                    and headers["return"] == "device; type=basedevice")
    return False

class UDPServer():
    """UDPServer(server_port, stop_event, [interface_str]) -> UDPServer

    This class is used to listen for discovery requests made on
    `MCAST_ADDR`:`MCAST_PORT`. When a valid request is made, the server responds
    with information about this device, including the location of its setup file
    (setup.json)
    """
    def __init__(self, stop, server_port, interface=""):
        self.stop = stop
        self.interface = interface
        self.response = "\r\n".join((
            "HTTP/1.1 200 OK",
            "Date: {}",
            "Location: http://%s:%s/setup.json" % (get_address(), server_port),
            "Server: ZeroMasterUDP/1.0, IOTSCP/1.0",
            "",
            ""
        ))

    def bind(self):
        """Add this udp socket to the multicast group for listening"""
        self.udpsock = socket.socket(
            socket.AF_INET,
            socket.SOCK_DGRAM,
            socket.IPPROTO_UDP
        )
        self.udpsock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.udpsock.bind((self.interface, MCAST_PORT))
        self.udpsock.setsockopt(
            socket.IPPROTO_IP,
            socket.IP_ADD_MEMBERSHIP,
            pack("4sl", socket.inet_aton(MCAST_ADDR), socket.INADDR_ANY)
        )

    def listen(self):
        """Accepts requests until `self.stop` is set"""
        while not self.stop.is_set():
            rlist, _, _ = select([self.udpsock], [], [], LISTEN_TIMEOUT)
            if self.udpsock in rlist:
                try:
                    data, addr = self.udpsock.recvfrom(4096)
                    if should_respond(data.decode("ascii")):
                        response_str = self.response.format(
                            strftime("%a, %d %b %Y %H:%M:%S GMT", gmtime())
                        )
                        self.udpsock.sendto(
                            bytearray(response_str, "ascii"),
                            addr
                        )
                except Exception as e:
                    logging.error(e)
        self._shutdown()

    def start(self):
        """Starts the server, binds it, and calls `listen` on a new thread"""
        self.bind()
        logging.info("Statring UDP server")
        self.lthread = Thread(target=self.listen, args=())
        self.lthread.name = "UDP listening thread"
        self.lthread.start()

    def _shutdown(self):
        logging.info("UDP server offline")
        self.shutdown()

    def shutdown(self):
        pass
