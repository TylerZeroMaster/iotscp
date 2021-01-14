import os
import logging
from select import select
from time import gmtime, strftime

PROTOCOL_VERSION = "HTTP/1.1"
ENCODING = ("utf-8", "replace")

RESPONSES = {
    100: "Continue",
    101: "Switching Protocols",

    200: "OK",
    201: "Created",
    202: "Accepted",
    203: "Non-Authoritative Information",
    204: "No Content",
    205: "Reset Content",
    206: "Partial Content",

    300: "Multiple Choices",
    301: "Moved Permanently",
    302: "Found",
    303: "See Other",
    304: "Not Modified",
    305: "Use Proxy",
    307: "Temporary Redirect",

    400: "Bad Request",
    401: "Unauthorized",
    402: "Payment Required",
    403: "Forbidden",
    404: "Not Found",
    405: "Method Not Allowed",
    406: "Not Acceptable",
    407: "Proxy Authentication Required",
    408: "Request Timeout",
    409: "Conflict",
    410: "Gone",
    411: "Length Required",
    412: "Precondition Failed",
    413: "Request Entity Too Large",
    414: "Request-URI Too Long",
    415: "Unsupported Media Type",
    416: "Requested Range Not Satisfiable",
    417: "Expectation Failed",

    500: "Internal Server Error",
    501: "Not Implemented",
    502: "Bad Gateway",
    503: "Service Unavailable",
    504: "Gateway Timeout",
    505: "HTTP Version Not Supported",
}

EXT_MAP = {
    ".json": "application/json",
    ".pdf": "application/pdf",
    ".torrent": "application/x-bittorrent",
    ".tgz": "application/x-compressed",
    ".gtar": "application/x-gtar",
    ".gz": "application/x-gzip",
    ".swf": "application/x-shockwave-flash",
    ".tar": "application/x-tar",
    ".zip": "application/x-zip-compressed",

    ".mid": "audio/mid",
    ".midi": "audio/mid",
    ".m4a": "audio/mp4",
    ".mp3": "audio/mpeg",
    ".aac": "audio/vnd.dlna.adts",
    ".adts": "audio/vnd.dlna.adts",
    ".adt": "audio/vnd.dlna.adts",
    ".ac3": "audio/vnd.dolby.dd-raw",
    ".wav": "audio/wav",
    ".aif": "audio/x-aiff",
    ".aiff": "audio/x-aiff",
    ".aifc": "audio/x-aiff",
    ".flac": "audio/x-flac",
    ".m3u": "audio/x-mpegurl",

    ".bmp": "image/bmp",
    ".gif": "image/gif",
    ".jpeg": "image/jpeg",
    ".jfif": "image/jpeg",
    ".jpg": "image/jpeg",
    ".png": "image/png",
    ".svg": "image/svg+xml",
    ".tiff": "image/tiff",
    ".tif": "image/tiff",
    ".ico": "image/x-icon",
    ".rgb": "image/x-rgb",

    ".css": "text/css; charset=utf-8",
    ".shtml": "text/html; charset=utf-8",
    ".html": "text/html; charset=utf-8",
    ".htm": "text/html; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".ksh": "text/plain; charset=utf-8",
    ".pl": "text/plain; charset=utf-8",
    ".py": "text/plain; charset=utf-8",
    ".jsx": "text/plain; charset=utf-8",
    ".sol": "text/plain; charset=utf-8",
    ".sor": "text/plain; charset=utf-8",
    ".bat": "text/plain; charset=utf-8",
    ".h": "text/plain; charset=utf-8",
    ".c": "text/plain; charset=utf-8",
    ".jsxbin": "text/plain; charset=utf-8",
    ".txt": "text/plain; charset=utf-8",
    ".pyw": "text/plain; charset=utf-8",
    ".rtx": "text/richtext; charset=utf-8",
    ".sct": "text/scriptlet; charset=utf-8",
    ".wsc": "text/scriptlet; charset=utf-8",
    ".tsv": "text/tab-separated-values; charset=utf-8",
    ".csv": "text/plain; charset=utf-8",
    ".htc": "text/x-component; charset=utf-8",
    ".xml": "text/xml; charset=utf-8",
    ".xsl": "text/xml; charset=utf-8",
    ".etx": "text/x-setext; charset=utf-8",
    ".sgm": "text/x-sgml; charset=utf-8",
    ".sgml": "text/x-sgml; charset=utf-8",
    ".vcf": "text/x-vcard; charset=utf-8",

    ".3gpp": "video/3gpp",
    ".3gp": "video/3gpp",
    ".3g2": "video/3gpp2",
    ".3gp2": "video/3gpp2",
    ".avi": "video/avi",
    ".mp4v": "video/mp4",
    ".m4v": "video/mp4",
    ".mp4": "video/mp4",
    ".mpeg": "video/mpeg",
    ".mpg": "video/mpeg",
    ".webm": "video/webm",
    ".flv": "video/x-flv",
    ".mkv": "video/x-matroska",
    ".asf": "video/x-ms-asf",
    ".wm": "video/x-ms-wm",
    ".wmv": "video/x-ms-wmv",
}

def guess_type(fpath):
    """guess_type(fpath_str) -> type_str

    Tries to guess the mimetype of fpath.

    Returns application/octet-stream when the type cannot be guessed
    """
    _, ext = os.path.splitext(fpath)
    if ext in EXT_MAP:
        return EXT_MAP[ext]
    else:
        return "application/octet-stream"

def gmtime_str(timestamp=None):
    """gmtime_str(timestamp_float) -> gmtime_str

    Returns the GMTime formatted according to RFC 1123
    """
    return strftime("%a, %d %b %Y %H:%M:%S GMT", gmtime(timestamp))

class ServerClient:
    """ServerClient(req_HttpRequest, client_sock, addr) -> ServerClient

    An interface for handling HTTP/1.0 and HTTP/1.1 clients
    """
    def __init__(self, req, client, addr):
        self.keep_alive = False
        str_version = req.proto.split('/', 1)[1]
        version = tuple(int(n) for n in str_version.split('.'))
        if version >= (1, 1) and "connection" in req.headers:
            if req.headers["connection"] == "keep-alive":
                self.keep_alive = True
        self.req = req
        self.client = client
        self.ip, self.port = addr

    def make_head(self, scode, headers_dict):
        """make_head(scode_int, headers_dict) -> head_u8

        Creates the HTTP head used to respond to the client

        Includes headers --
            Server: ZeroMasterHTTP/1.0
            Date: {GMTIME}
            Connection: close or keep-alive depending on the value of
                self.keep_alive
        """
        head = bytearray(
            "%s %s %s\r\n" % (PROTOCOL_VERSION, scode, RESPONSES[scode]),
            "ascii"
        )
        head.extend(b"Cache-Control: max-age=86400\r\n")
        head.extend(b"Server: ZeroMasterHTTP/1.0\r\n")
        head.extend(("Date: %s\r\n" % gmtime_str()).encode("ascii"))
        if headers_dict is not None:
            for header in headers_dict.items():
                head.extend(("%s: %s\r\n" % header).encode("ascii"))
        if self.keep_alive:
            head.extend(b"Connection: keep-alive\r\n\r\n")
        else:
            head.extend(b"Connection: close\r\n\r\n")
        return head

    def write_file(self, fpath, other_headers=None):
        """write_file(fpath_str, other_headers_dict)

        other_headers is optional

        Attempts the send an entire file to the client.
        Upon failure, this will force keep_alive to False
        """
        with open(fpath, "rb") as fin:
            fs = os.fstat(fin.fileno())
            headers = {
                "Content-Length": str(fs[6]),
                "Last-Modified": gmtime_str(fs.st_mtime),
                "Content-Type": guess_type(fpath)
            }
            if other_headers is not None:
                headers.update(other_headers)
            self.client.send(self.make_head(200, headers))
            while True:
                buf = fin.read(8192)
                if not buf:
                    break
                # if this times out, the sent file will be corrupted
                _, wlist, _ = select([], [self.client], [], 5.0)
                if self.client in wlist:
                    self.client.sendall(buf)
                else:
                    # in that case, give up
                    logging.error("Connection with `%s` timed out" % self.ip)
                    self.keep_alive = False
                    break

    def write_body(self, scode, ctype, body, other_headers=None):
        """write_body(scode_int, ctype_str, body_u8, other_headers_dict)

        other_headers is optional
        ctype is the Content-Type header value, scode is the response code

        Writes a string originating from within Python to the client. For
        writing files, write_file should be used instead.
        """
        headers_dict = {}
        headers_dict["Content-Type"] = ctype
        headers_dict["Content-Length"] = len(body)
        if other_headers is not None:
            headers_dict.update(other_headers)
        output_u8 = self.make_head(scode, headers_dict)
        output_u8.extend(body)
        self.client.sendall(output_u8)
        logging.debug("Body sent!")

    def write_generic_body(self, scode, body=None):
        """write_body(scode_int, ctype_str, body_u8, other_headers_dict)

        scode is the response code
        body is optional. When omitted, the body will be the message tied
        scode (ex: 404 Not Found)

        writes a generic body of the form:
            <!DOCTYPE html><html><body><h1>{body}<h1></body></html>
        """
        if body is None:
            body = "%s %s" % (scode, RESPONSES[scode])
        self.write_body(
            scode,
            "text/html; charset=utf-8",
            bytearray(
                "<!DOCTYPE html><html><body><h1>%s<h1></body></html>" % body,
                *ENCODING
            )
        )

    def write_head(self, scode, headers_dict=None):
        """write_head(scode, headers_dict)

        headers_dict is optional

        Write the http head with response code `scode` to the client
        """
        output_u8 = self.make_head(scode, headers_dict)
        self.client.sendall(output_u8)
