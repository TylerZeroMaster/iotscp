import os
import logging

from . import WEB_PATH
from .httpbase.httpserver import HttpServer

_HELLO_URL = "/iotscp/hello"

def get_os_path(url):
    """get_os_path(url_str) -> os_path_str

    Converts the request url to an absolute OS path to a file on the local
    filesystem
    """
    parts = url.split("/")
    if '?' in parts[-1]:
        parts[-1] = parts[-1].split('?')[0]
    elif '#' in parts[-1]:
        parts[-1] = parts[-1].split('#')[0]
    if '.' not in parts[-1]:
        parts.append("index.html")
    return os.path.join(WEB_PATH, *parts)

class DeviceServer(HttpServer):
    """DeviceServer(stop_event, port_int, device_BaseDevice) -> DeviceServer

    Handles http requests made to the device.
    """
    def __init__(self, stop, port, device):
        HttpServer.__init__(self, stop, port)
        self.device = device
        self.handles = dict(
            GET=self.GET,
            POST=self.POST,
            SUBSCRIBE=self.SUBSCRIBE
        )

    def GET(self, serverclient):
        """GET(serverclient)

        This is solely used for serving files to unauthenticated hosts.

        Everyone is allowed to see the device's specification pages.

        Writes --
            404 in cases where the file is not found
        """
        path = get_os_path(serverclient.req.url)
        logging.debug(path)
        if os.path.exists(path):
            serverclient.write_file(path)
        else:
            logging.debug("404 Not Found")
            serverclient.write_generic_body(404)

    def POST(self, serverclient):
        """POST(serverclient)

        Forwards POST requests to the device for processing.

        Only authenticated hosts are allowed to control the device.

        Writes --
            401 in cases where no uuid is supplied
        """
        service_url = serverclient.req.url
        headers = serverclient.req.headers
        if "uuid" in headers:
            uuid = headers["uuid"]
            if service_url == _HELLO_URL:
                self.device.create_session(uuid, serverclient)
            else:
                self.device.handle_request(uuid, serverclient)
        else:
            serverclient.write_head(401)

    def SUBSCRIBE(self, serverclient):
        """SUBSCRIBE(serverclient)

        Forwards SUBSCRIBE requests to the device for processing.

        Only authenticated hosts are allowed to subscribe to the device.

        Writes --
            401 in cases where no uuid is supplied
        """
        headers = serverclient.req.headers
        if "uuid" in headers:
            uuid = headers["uuid"]
            self.device.add_subscriber(uuid, serverclient)
        else:
            serverclient.write_head(401)
