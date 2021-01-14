from time import time
from math import ceil
from datetime import timedelta
from hashlib import pbkdf2_hmac

import logging

from ..utils import Instant, get_algorithms

ALGORITHMS = get_algorithms()
# the amount of time, in seconds, that a key is allowed to live
KEY_TTL = 5

def clamp_to(n, clamp):
    """A step function where n = clamp * int(n / clamp) + clamp"""
    return n - (n % clamp) + clamp

def get_common_algorithm(external, prefered=None):
    """Get either this device's prefered algorithm, or the best one shared
    between the device and the other host.
    """
    if prefered is not None:
        if prefered in external:
            return prefered
    for alg in ALGORITHMS:
        if alg in external:
            return alg
    raise ValueError("No common algorithm found")

class SCSession():
    """SCSession(cert_SCCertificate, hashtype_str) -> SCSession

    This class represents a session between two hosts. The session uses
    a symetrical key to encrypt and decrypt data.
    """

    def __init__(self, cert, hashtype):
        self.cert = cert
        self.__hashtype = hashtype
        self.cipher = bytearray(range(256))
        self.__prev_key = self.__fresh_key()
        self.__start = Instant()
        self.__new_key = self.__derived_key()

    def __get_next_segment_time(self):
        t = self.__start.elapsed()
        logging.debug("Elapsed: %d" % int(clamp_to(ceil(t), KEY_TTL)))
        return int(clamp_to(ceil(t), KEY_TTL))

    def __fresh_key(self):
        return bytearray(
            pbkdf2_hmac(
                self.__hashtype,
                self.cert.get_key_segment(),
                str(clamp_to(ceil(time()), KEY_TTL)),
                10000,
                256
            )
        )

    # generate a new key from the old one and how long the session has been alive
    def __derived_key(self):
        return bytearray(
            pbkdf2_hmac(
                self.__hashtype,
                self.__prev_key,
                str(self.__get_next_segment_time()),
                100,
                256
            )
        )

    def __get_key(self):
        key = self.__derived_key()
        self.__new_key = key
        return key

    def __randomize(self):
        key = self.__get_key()
        cipher = self.cipher
        i = 0
        while i < 256:
            old = cipher[i]
            cipher[i] = cipher[key[i]]
            cipher[key[i]] = old
            i += 1

    def get_hashtype(self):
        """returns the best hash type that both server and device supported"""
        return self.__hashtype

    def encrypt(self, input_u8):
        """Encrypt a bytearray or str using this session's key generator

        Encryption is based on a direct translation to the class's internally
        kept block cipher, followed by a XOR between input[n] and cipher[n]

        returns a bytearray
        """
        if self.__prev_key == self.__new_key:
            self.__randomize()
        if not isinstance(input_u8, bytearray):
            input_u8 = bytearray(input_u8, "utf-8")
        i = 0
        while i < len(input_u8):
            input_u8[i] = self.cipher[input_u8[i]] ^ self.cipher[i%256]
            i += 1
        return input_u8

    def decrypt(self, input_u8):
        """Decrypt a bytearray using this session's key generator

        Do the reverse of what the encryption did: XOR input[n] and cipher[n],
        then that byte's index in the cipher is the original byte

        returns a utf-8 str
        """
        if self.__prev_key == self.__new_key:
            self.__randomize()
        key_map = {b:i for i, b in enumerate(self.cipher)}
        i = 0
        while i < len(input_u8):
            input_u8[i] = key_map[input_u8[i] ^ self.cipher[i%256]]
            i += 1
        return input_u8.decode("utf-8")

    # in the future it may be a good idea to integrate this into a
    # contextmanager
    def update_key(self):
        """Update the key that the session uses to randomize its cipher
        This should always be called before encrypting a message. For the sake
        of simplicity, this should always be called twice whenever the session
        is used
        """
        self.__prev_key = self.__new_key
