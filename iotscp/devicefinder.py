import socket
import logging
import json

from .utils import Instant
from .scdevice import SCDevice
from .http.httpbase.httputil import parse_headers, HttpResponse

try:
    from urlparse import urlparse
except ImportError:
    from urllib.parse import urlparse

class SCFinder:
    """SCFinder(cert_SCCertificate) -> SCFinder

    This class is a tool for discovering devices on the LAN
    """
    def __init__(self, cert):
        self.cert = cert

    def make_device(self, location):
        """make_device(location_str) -> SCDevice

        Creates a SCDevice given `location` as a str.
        `location` should take the form http://{ip}:{port}/setup.json
        """
        purl = urlparse(location)
        addr = (purl.hostname, purl.port)
        sock = socket.socket()
        msg = bytearray("\r\n".join((
            "GET {p.path} HTTP/1.1",
            "Host: {p.netloc}",
            "Accept: application/json",
            "Connection: close",
            "",
            ""
        )).format(p=purl), "ascii")
        try:
            sock.settimeout(1.0)
            sock.connect(addr)
            sock.sendall(msg)
            res = HttpResponse(sock)
            if res.code == 200:
                dev_json = json.loads(res.body.decode("utf-8"))
                return SCDevice(addr, dev_json, self.cert)
        except Exception as e:
            logging.error(e)
        return None

    def find_devices(self, return_type="device; type=basedevice"):
        """find_devices([return_type_str]) -> devices_list[SCDevice]

        Searchs the multicast group for devices.
        return_type is the type of device you are searching for. There is
        currently only one supported return_type(device; type=basedevice),
        but in the future, additional query options will be available.
        """
        locations = []
        devices = []
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        mcast_addr = ("239.255.255.250", 1900)
        msg = bytearray("\r\n".join((
            "IOT-SEARCH * HTTP/1.1",
            "Host: 239.255.255.250:1900",
            "Return: %s" % return_type,
            "SV: iotscp:discover",
            "", ""
        )), "ascii")
        timeout = Instant()
        try:
            sock.sendto(msg, mcast_addr)
            sock.settimeout(5.0)
            while timeout.elapsed() < 5.0:
                try:
                    res, address = sock.recvfrom(400)
                    headers = parse_headers(res)
                    location = headers["location"] # http://ip:port/setup.json
                    if location not in locations:
                        locations.append(location)
                        device = self.make_device(location)
                        if device is not None:
                            devices.append(device)
                            logging.debug("Device found!")
                except socket.timeout:
                    pass
                except Exception as e:
                    logging.error(repr(e))
        except Exception as e:
            logging.error(e)
        return devices
