import socket
import logging
import re

# All the HTTP header types that should be converted to integers
NUMBER_TYPES = ["content-length"]

# The size of the byte buffers used to recv
BUFSIZE = 4096

RE_REQLINE = re.compile("(.+?)(?: )(.+?)(?: )(.+?)(?:\r\n)")
RE_HEADERS = re.compile("(.+?)(?::\s*)(.+?)(?:\r\n)")

class HeaderTypeError(Exception):
    """This error is raised in the event of a type mismatch
    For example: the header `Content-Length: 1.5` would result in this error
    """
    def __init__(self, key, _type):
        self.value = "Type mismatch for `%s`: expected %s" % (key, _type)

    def __str__(self):
        return repr(self.value)

class HTTPError(Exception):
    """This error is a catch-all general HTTP error.
    For example: this error is raised if the HTTP head contains invalid ascii
    characters
    """
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)

class NullRequestError(Exception):
    """This error is raised when the client sends "" (an empty string)"""
    def __init__(self):
        self.value = "No HTTP head found"

    def __str__(self):
        return repr(self.value)

class VersionError(Exception):
    """This error is raised when the client tries to use an HTTP version that
    the server does not support.
    """
    def __init__(self):
        self.value = "Unsupported HTTP version"

    def __str__(self):
        return repr(self.value)

def parse_number(key, n):
    """parse_number(key_str, number_str) -> number_int

    Attempts to parse an integer, raises HeaderTypeError upon encountering a
    ValueError.
    Returns parsed value.
    """
    try:
        return int(n)
    except ValueError:
        raise HeaderTypeError(key, "number")

def decode_http_head(head_u8):
    """decode_http_head(head_u8) -> head_str

    Attempts to decode a bytearray, raises HTTPError upon decoding error.
    Returns decoded value.
    """
    try:
        return head_u8.decode("ascii")
    except UnicodeDecodeError:
        raise HTTPError("HTTP head contained invalid characters")

def parse_headers(head_str):
    """parse_headers(head_str) -> headers_dict

    Finds all the headers in the HTTP head, converts them to expected types,
    and places them in a dictionary.
    Returns dictionary containing parsed headers.
    """
    headers_dict = {}
    for header in RE_HEADERS.finditer(head_str):
        k, v = header.group(1).lower(), header.group(2)
        if k in NUMBER_TYPES:
            v = parse_number(k, v)
        headers_dict[k] = v
    return headers_dict

def get_head(client):
    """get_head(client_socket) -> (head_str, body_u8)

    Create a byte buffer, recv once and check if the response filled the
    buffer. If it didn't, search for \r\n\r\n (HTTP body start). If found, split
    the byte buffer at that point and return the decoded head, and raw body.
    If it did, make another buffer to hold what we have so far, and recv
    until \r\n\r\n is found, or the arbitrary limit 65537 is reached.
    Raises --
        NullRequestError if the first recv returns 0 bytes
        HTTPError if 65537 bytes (~65 Kilobytes) are recvd before body is found
    Returns ascii decoded head and raw body
    """
    buf = bytearray(BUFSIZE)
    amt = client.recv_into(buf)
    if amt < BUFSIZE:
        if amt == 0:
            raise NullRequestError
        else:
            body_start = buf.find(b"\r\n\r\n")
            if body_start != -1:
                head, body = buf[:body_start + 2], buf[body_start + 4:amt]
                return (decode_http_head(head), body)
    logging.debug("Head overflow")
    recvd = bytearray(buf)
    while len(recvd) < 65537:
        amt = client.recv_into(buf)
        recvd.extend(buf[:amt])
        body_start = recvd.find(b"\r\n\r\n")
        if body_start != -1:
            head, body = recvd[:body_start + 2], recvd[body_start + 4:]
            return (decode_http_head(head), body)
    raise HTTPError("HTTP head too long")

class HttpHead():
    """HttpHead(client_sock) -> HttpHead

    This class does all the work of parsing an HTTP head. Its primary purpose
    is to serve as a platform for which HttpRequest and HttpResponse stand on.
    """
    headers = {}
    def __init__(self, client):
        self.head, self.body = get_head(client)
        reqline = RE_REQLINE.match(self.head)
        # if we made it this far and the reqline doesn't have three fields, then
        # it must be HTTP/0.9, which this server doesn't support
        if reqline is None:
            raise VersionError
        self.reqline = (reqline.group(1), reqline.group(2), reqline.group(3))
        self.headers = parse_headers(self.head)

    def recv_body(self, client):
        """recv_body(client_sock)

        Attempts to recv the entire request/response body. Mostly, this should
        only be called by either HttpRequest or HttpResponse, except in very
        specific cases.
        """
        if "content-length" in self.headers:
            body_len = len(self.body)
            if body_len < self.headers["content-length"]:
                logging.debug("Recving body...")
                nbytes = self.headers["content-length"] - body_len
                buf = bytearray(BUFSIZE)
                amt = 0
                while amt < nbytes:
                    amt += client.recv_into(buf)
                    self.body.extend(buf[:amt])

class HttpRequest(HttpHead):
    """HttpRequest(client_sock) -> HttpRequest

    Parse an http request, giving easy access to:
        req_type, ('GET')
        url, ('/')
        proto, ('HTTP/1.1')
        headers, (as a dictionary)
        head, (as a string)
        and body. (as a bytearray)
    """
    def __init__(self, client):
        HttpHead.__init__(self, client)
        self.req_type, self.url, self.proto = self.reqline
        if self.req_type == "POST":
            self.recv_body(client)

class HttpResponse(HttpHead):
    """HttpResponse(client_sock) -> HttpResponse

    Parse an http request, giving easy access to
        proto, ('HTTP/1.1')
        code, (200)
        message, ('OK')
        headers, (as a dictionary)
        head, (as a string)
        and body. (as a bytearray)
    """
    def __init__(self, client):
        HttpHead.__init__(self, client)
        self.proto, self.code, self.message = self.reqline
        self.code = parse_number("Response code", self.code)
        self.recv_body(client)
