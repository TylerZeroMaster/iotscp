import errno
import socket
import logging
from select import select
from threading import Thread, Event

from . import httputil, LISTEN_TIMEOUT
from ...utils import Instant
from .serverclient import ServerClient

# Client can live for 5 minutes * 60 seconds = 300 seconds before
# the connection should be closed forcibly
CLIENT_TIMEOUT = 300

class NoHandleError(Exception):
    def __init__(self, req_type):
        self.value = "No handle for request type `%s` found" % req_type

    def __str__(self):
        return repr(self.value)

class HttpServer:
    """HttpServer(stop_event, port_int, [address_str]) -> HttpServer

    This is a very bare implementation of an HTTP/1.1 server, this class is
    meant to be used as a base class for more specific implementations. It is
    worthless on its own.
    """
    reuse_sock = True

    def __init__(self, stop, port, address=""):
        self.address = (address, port)
        self.stop = stop

    def get_handle(self, req_type):
        """get_handle(req_type_str) -> handle_func

        Attempts to get the handle associated with the req_type.

        Raises NoHandleError if there is no handle for req_type
        """
        if req_type in self.handles:
            return self.handles[req_type]
        else:
            raise NoHandleError(req_type)

    def handle_one_request(self, client, addr):
        """handle_one_request(client_sock, addr) -> keep_alive_bool

        Handle one request and return weither or not the connection should be
        kept alive. At present, this will keep the connection alive unless the
        client requests it be closed, or their HTTP version is unsupported.

        Writes --
            500 in cases where an unknown error occurs
            501 in cases where no handle is found for req_type
            505 in cases where the client is using an unsupported HTTP version
        """
        try:
            req = httputil.HttpRequest(client)
            serverclient = ServerClient(req, client, addr)
            req_type = req.req_type
            handle = self.get_handle(req_type)
            try:
                handle(serverclient)
            except Exception as e:
                logging.error("Error in handles->%s: %s" % (req_type, e))
                serverclient.write_generic_body(500)
                return True
            logging.debug("keep_alive = %s" % serverclient.keep_alive)
            return serverclient.keep_alive
        except httputil.NullRequestError:
            # This seems to be how most browsers end keep-alive sessions.
            logging.debug("Null request error")
            return False
        except httputil.VersionError:
            serverclient.keep_alive = False
            serverclient.write_generic_body(505)
            return False
        except NoHandleError as nhe:
            logging.error(nhe)
            serverclient.write_generic_body(501)
            return True

    def handlereq(self, client, addr):
        """handlereq(client_sock, addr)

        Handles requests from the client until either keep_alive is False or
        CLIENT_TIMEOUT (300 seconds/5 minutes) has passed since the connection
        was last used.
        """
        try:
            logging.debug("Connection opened: %s:%s" % addr)
            # set the socket to non-blocking mode because if everything is done
            # correctly, blocking should only occur in exceptional situations
            client.setblocking(False)
            keep_alive = True
            timeout = Instant()
            # essentially another listen loop
            while (keep_alive and not self.stop.is_set()
                    and timeout.elapsed() < CLIENT_TIMEOUT):
                rlist, _, _ = select([client], [], [], LISTEN_TIMEOUT)
                if client in rlist:
                    logging.debug("Reading from client")
                    keep_alive = self.handle_one_request(client, addr)
                    timeout.reset()
            if timeout.elapsed() >= CLIENT_TIMEOUT:
                logging.info("Forcing connection closed...")
        except socket.error as se:
            if se.errno == errno.EWOULDBLOCK:
                logging.error("Connection unexpectedly closed by client")
            else:
                logging.error(se)
        except Exception as e:
            logging.error(e)
        finally:
            client.close()
            logging.debug("Connection closed")

    def listen(self):
        """Accepts connections until `self.stop` is set"""
        while not self.stop.is_set():
            self.lsock.listen(5)
            rlist, _, _ = select([self.lsock], [], [], LISTEN_TIMEOUT)
            if self.lsock in rlist:
                Thread(target=self.handlereq, args=self.lsock.accept()).start()
        self._shutdown()

    def server_bind(self):
        """Binds the server to its address"""
        self.lsock = socket.socket()
        if self.reuse_sock:
            self.lsock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.lsock.bind(self.address)
        self.bound_to = self.lsock.getsockname()

    def start(self):
        """Starts the server, binds it, and calls `listen` on a new thread"""
        try:
            self.server_bind()
            logging.info(
                "Starting HTTP server\n"
                "\t%s:%s" % self.bound_to
            )
            self.lthread = Thread(target=self.listen, args=())
            self.lthread.name = "Listening thread"
            self.lthread.start()
        except Exception as e:
            from sys import exit
            logging.error(e)
            # No point keeping this up if we can't listen...
            exit(1)

    def _shutdown(self):
        logging.info("HTTP server %s:%s is now offline" % self.bound_to)
        self.shutdown()

    def shutdown(self):
        pass
