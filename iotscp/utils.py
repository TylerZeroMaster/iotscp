from time import time
from datetime import timedelta

def verify_str(_str, str_name, blacklist=None, whitelist=None):
    """verify_str(str_str, str_name_str, blacklist_set, whitelist_set)
    Ensures that a string only contains a certain subset of characters.

    Raises ValueError if an illegal character is found
    """
    allowed = set(
        "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_.-"
    )
    if whitelist is not None:
        allowed.update(whitelist)
    if blacklist is not None:
        allowed -= blacklist
    for c in _str:
        if c not in allowed:
            raise ValueError("`%s` is not allowed in %s" % (c, str_name))

def get_algorithms():
    """Returns an organized list of this machine's hashing algorithms
    (Ideally organized by strength, but I am not a cryptography expert)
    """
    try:
        from hashlib import algorithms
    except ImportError:
        from hashlib import algorithms_available as algorithms
    sorted_algs = [
        "sha512", "SHA512",
        "sha384", "SHA384",
        "whirlpool", "WHIRLPOOL",
        "sha256", "SHA256",
        "sha224", "SHA224",
        "ripemd160", "RIPEMD160",
        "sha", "SHA",
        "md5", "MD5",
        "sha1", "SHA1",
        "dsa", "DSA",
        "md4", "MD4"
    ]
    return [alg for alg in sorted_algs if alg in algorithms]

def get_address():
    """Get this machine's address on the LAN"""
    import socket
    try:
        hostname = socket.gethostname()
        # check if we have a specific domain name
        if '.' not in hostname:
            # if not, append .local, else we may get a loopback address
            hostname = '.'.join((hostname, "local"))
        address = socket.gethostbyname(hostname)
    except:
        address = ""
    # if all else fails, "connect" to Google DNS and get the name of that socket
    if not address or address.startswith("127."):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 0))
        address = s.getsockname()[0]
    return address

class Instant():
    """Instant() -> Instant

    This class is used to keep track of the passing of time.
    """
    def __init__(self):
        self.start = time()

    def elapsed(self):
        """Returns the amount of time, in seconds, since the start of Instant"""
        return time() - self.start

    def reset(self):
        """Sets the current time to the starting time of the Instant"""
        self.start = time()

    def __str__(self):
        return str(timedelta(seconds=self.elapsed()))

    def __repr__(self):
        return repr(timedelta(seconds=self.elapsed()))
