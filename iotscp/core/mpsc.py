from threading import Condition
from collections import deque
from time import sleep

class Channel():
    """This class is a multi-producer, single-consumer FIFO queue, providing
    message-based blocking communcations over channels 
    """
    def __init__(self):
        self.cond = Condition()
        self.queue = deque([])

    def has_data(self):
        return len(self.queue) > 0

    def send(self, obj):
        """Used by the sending half of the channel to send information"""
        with self.cond:
            self.queue.append(obj)
            self.cond.notify_all()

    def recv(self, timeout=None):
        """recv(timeout_float) -> msg_obj

        Waits `timeout` seconds for a message. Returns None if timeout occurs
        otherwise returns the first object in the channel's buffer
        """
        with self.cond:
            if not self.has_data():
                self.cond.wait(timeout)
        if self.has_data():
            return self.queue.popleft()
        else:
            return None

    def get_iter(self, timeout=None):
        """get_iter(timeout_float) -> msg_obj_iter

        Waits `timeout` seconds for a message. Returns None if timeout occurs
        otherwise returns an iterator over all objects in the channel's buffer
        """
        with self.cond:
            if not self.has_data():
                self.cond.wait(timeout)
        while self.has_data():
            yield self.queue.popleft()
