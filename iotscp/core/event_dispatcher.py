import json
import socket
import logging
from select import select
from threading import Thread

from .mpsc import Channel
from ..utils import Instant
from ..http.httpbase import httputil

SUB_TIMEOUT = 180

def should_keep_alive(res):
    if res.code != 200:
        return False
    elif "connection" not in res.headers:
        str_version = res.proto.split('/', 1)[1]
        version = tuple(map(int, str_version.split('.', 1)))
        if version < (1, 1):
            return False
    elif res.headers["connection"] == "close":
        return False
    return True

def make_notification(sub_addr, event):
    """make_notification(sub_addr, event_dict) -> http_event_u8

    Create a HTTP notification message for the event.
    """
    str_event = json.dumps(event)
    return bytearray("\r\n".join((
        "NOTIFY / HTTP/1.1",
        "Host: %s:%s" % sub_addr,
        "NT: iotscp:event; event-name=%s" % event["name"],
        "Content-Type: application/json",
        "Content-Length: %s" % len(str_event),
        "Connection: keep-alive",
        "",
        str_event
    )), "utf-8")

def poke(sub_addr, sub_sock):
    """poke(sub_addr, sub_sock) -> keep_alive_bool

    Create a HTTP notification to keep this connection alive by 'poking' the
    host
    """
    keep_alive_msg = bytearray("\r\n".join((
        "NOTIFY / HTTP/1.1",
        "Host: %s:%s" % sub_addr,
        "Connection: keep-alive",
        "",
        ""
    )), "ascii")
    try:
        logging.debug("Sending keep-alive message")

        _, wlist, _ = select([], [sub_sock], [], 5.0)
        if sub_sock not in wlist:
            logging.error("Connection timed out")
            return False
        sub_sock.send(keep_alive_msg)
        # give the server 5 seconds to respond
        rlist, _, _ = select([sub_sock], [], [], 5.0)
        if sub_sock not in rlist:
            logging.error("Connection timed out")
            return False
        res = httputil.HttpResponse(sub_sock)
        return should_keep_alive(res)
    except Exception as e:
        logging.error("%s:%s->%s" % (sub_addr[0], sub_addr[1], e))
        return False


def send_event_http(event, sub_addr, sub_sock):
    """send_event_http(event_dict, sub_addr, sub_sock) -> keep_alive_bool

    Sends a notification and determines if the connection should be kept alive.
    """
    try:
        logging.debug("Sending notification")

        req = make_notification(sub_addr, event)
        _, wlist, _ = select([], [sub_sock], [], 5.0)
        if sub_sock not in wlist:
            logging.error("Connection timed out")
            return False
        sub_sock.send(req)
        # give the server 5 seconds to respond
        rlist, _, _ = select([sub_sock], [], [], 5.0)
        if sub_sock not in rlist:
            logging.error("Connection timed out")
            return False
        res = httputil.HttpResponse(sub_sock)
        return should_keep_alive(res)
    except Exception as e:
        logging.error("%s:%s->%s" % (sub_addr[0], sub_addr[1], e))
        return False

class EventDispatcher():
    """EventDispatcher(stop_event) -> EventDispatcher

    This class forms a pyramid/funnel:
          Host
      --Services--
    -----Events-----
    where each host has one connection to this device. All notifications that
    the host is subscribed to are sent over that single connection. When dealing
    with multiple hosts, this will form a star network with the device in the
    middle.
    """
    def __init__(self, stop_event):
        self.stop_event = stop_event
        self.subscribers = {}
        self.event_loops = {}

    def add_subscriber(self, event_url, sub_addr):
        """add_subscriber(event_url_str, sub_addr)

        Add a subscriber to this event dispatcher
        """
        if event_url in self.subscribers:
            if sub_addr not in self.subscribers[event_url]:
                self.subscribers[event_url].append(sub_addr)
        # the chance of an unsupported subscription is handled by the device
        else:
            self.subscribers[event_url] = [sub_addr]

    def _event_loop(self, rx, sub_addr, sub_sock):
        """_event_loop(rx_channel, sub_addr, sub_sock)

        Loop while the connection remains open, wait for input from the channel.
        """
        keep_alive = True
        timeout = Instant()
        while keep_alive and not self.stop_event.is_set():
            for event in rx.get_iter(15.0):
                keep_alive = send_event_http(event, sub_addr, sub_sock)
                timeout.reset()
            if timeout.elapsed() >= SUB_TIMEOUT:
                # try to keep the connection alive
                if poke(sub_addr, sub_sock):
                    timeout.reset()
                else:
                    break
        # close this channel
        logging.debug("Closing connection")
        del self.event_loops[sub_addr]
        for subs in self.subscribers.values():
            if sub_addr in subs:
                subs.remove(sub_addr)
        logging.debug(self.subscribers)

    def _send_event(self, sub_addr, event):
        """_send_event(sub_addr, event_dict)

        Check for connection with host: if one does not exist, create one. Upon
        connection creation, check for keep_alive support. If supported, begin a
        new event loop with a multi-producer-single-consumer channel and save it
        for later.
        """
        if sub_addr not in self.event_loops:
            sub_sock = socket.socket()
            sub_sock.connect(sub_addr)
            sub_sock.setblocking(False)
            keep_alive = send_event_http(event, sub_addr, sub_sock)
            if keep_alive:
                tx = rx = Channel()
                self.event_loops[sub_addr] = tx
                Thread(
                    target=self._event_loop,
                    args=(rx, sub_addr, sub_sock)
                ).start()
        else:
            self.event_loops[sub_addr].send(event)

    def send_event(self, event_url, event):
        """send_event(event_url_str, event_dict)

        Sends the event to all hosts that are subscribed to the service
        """
        subscribers = self.subscribers[event_url]
        i = 0
        while i < len(subscribers):
            try:
                sub_addr = subscribers[i]
                self._send_event(sub_addr, event)
                i += 1
            except Exception as e:
                logging.error(e)
                del subscribers[i]
