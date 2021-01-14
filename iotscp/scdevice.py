import json
import socket

from .core.scsession import SCSession
from .http.httpbase.httputil import HttpResponse

try:
    from hashlib import algorithms
except ImportError:
    from hashlib import algorithms_available as algorithms

_HELLO_URL = "/iotscp/hello"

class SCDeviceError(Exception):
    """Raised as a catch-all to describe errors in the SCDevice class"""
    def __init__(self, value):
        self.value = "%s: %s" % (self.__class__.__name__, value)
    def __str__(self):
        return repr(self.value)

class SCDevice():
    """SCDevice(addr_tuple, dev_json_dict, cert_SCCertificate) -> SCDevice

    This is the base class for creating device interfaces on the host server.
    """
    def __init__(self, addr, dev_json, cert):
        self.addr = addr
        self.cert = cert
        self.session = self.__get_session()
        for k, v in dev_json.items():
            setattr(self, k, v)

    def __send(self, msg):
        sock = socket.socket()
        sock.connect(self.addr)
        sock.sendall(msg)
        return HttpResponse(sock)

    def __get_session(self):
        """Starts an authenticated session with the device

        Raises --
            SCDeviceError when the device responds with an unsupported hashing
                algorithm (only a MITM should cause this, so beware!)
        """
        cert = self.cert
        data = json.dumps(dict(
            offset=cert.offset,
            algorithms=algorithms
        ))
        req = "\r\n".join((
            "POST %s HTTP/1.1" % _HELLO_URL,
            "uuid: %s" % cert.uuid,
            "Content-Type: application/json",
            "Content-Length: %d" % len(data),
            "Connection: close",
            "",
            data
        ))
        res = self.__send(req)
        if res.code == 200:
            algorithm = res.body.decode("utf-8")
            if algorithm not in algorithms:
                raise SCDeviceError(
                    "Algorithm %s is not available" % algorithm)
            return SCSession(cert, algorithm)
        else:
            raise SCDeviceError("Device responded with %d" % res.code)

    def make_req(self, control_url, method_name, args=None):
        """make_req(control_url_str, method_name_str, [args_dict]) -> r_dict

        Executes the service method found at `control_url`/`method_name` on the
        device and returns the result, or None if the method doesn't return.

        Raises --
            SCDeviceError when the response code is not 200 OK
        """
        data = self.session.encrypt(json.dumps([method_name, args or {}]))
        req = bytearray("\r\n".join((
            "POST %s HTTP/1.1" % control_url,
            "uuid: %s" % self.cert.uuid,
            "Content-Type: application/json",
            "Content-Length: %d" % len(data),
            "Connection: close",
            "", ""
        )), "ascii")
        req.extend(data)
        res = self.__send(req)
        if res.code == 200:
            self.session.update_key()
            body = self.session.decrypt(res.body)
            return json.loads(body)
        else:
            raise SCDeviceError("Device responded with %d" % res.code)

    def subscribe(self, event_url, port):
        """subscribe(event_url_str, port_int)

        Subscribes to `event_url` and has all event notifcations sent to this
        host's IP address on port `port`

        Raises --
            SCDeviceError when the response code is not 200 OK
        """
        data = self.session.encrypt(json.dumps(dict(port=port)))
        req = bytearray("\r\n".join((
            "SUBSCRIBE %s HTTP/1.1" % event_url,
            "uuid: %s" % self.cert.uuid,
            "Content-Type: application/json",
            "Content-Length: %d" % len(data),
            "Connection: close",
            "", ""
        )), "ascii")
        req.extend(data)
        res = self.__send(req)
        if res.code == 200:
            self.session.update_key()
        else:
            raise SCDeviceError("Device responded with %d" % res.code)
