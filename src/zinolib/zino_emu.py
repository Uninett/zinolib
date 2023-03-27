#!/usr/bin/env python3
import socket
import threading
import traceback
from time import sleep
from typing import Callable, Dict, List, Union
import sys
import os

if "emudebug" in os.environ:
    debug = 1
else:
    debug = 0


def dprint(text):
    global debug
    if debug:
        print(text)


class clientobj:
    def __init__(
        self, clientsock: socket.socket, addr: str, stop_signal: threading.Event
    ) -> None:
        self.sock = clientsock
        self._buff = ""
        self.address = addr
        self.stop_signal = stop_signal
        self.sock.settimeout(5)

    def executor(self, autodict: Dict[str, Union[str, List[str]]]) -> None:
        buff = ""
        try:
            while True:
                if self.stop_signal.is_set():
                    return
                buff += self.sock.recv(4096).decode("latin-1")
                dprint(repr(buff))
                for k in autodict.keys():
                    if k in buff:
                        dprint("EMU RECV: %s" % repr(buff))
                        # We got a match
                        if not autodict[k]:
                            return
                        self.send(autodict[k])
                        buff = ""
        except socket.timeout:
            if self.stop_signal.is_set():
                return
            dprint("EMU: executor: Timeout in buffer:      %s" % repr(buff))

    def waitfor(self, text: str):
        buff = ""
        try:
            while True:
                buff += self.sock.recv(4096).decode("latin-1")
                if text in buff:
                    dprint("EMU RECV: %s" % repr(buff))
                    buff = ""
                    return False
        except socket.timeout:
            dprint("EMU: timeout waiting for: %s" % repr(text))
            dprint("EMU: data in buffer:      %s" % repr(buff))
            try:
                pass  # self.close()
            except Exception:
                pass

                raise TimeoutError("EMU: Timeout waiting for data")

    def close(self):
        self.sock.close()

    def send(self, text: Union[str, List[str]]):
        dprint("EMU SEND: %s" % repr(text))
        if isinstance(text, list):
            for a in text:
                self.sock.send(a.encode())
        else:
            self.sock.send(text.encode())


class zinoemu:
    def __init__(
        self,
        client_callback: Callable[[clientobj], None],
        bind_ip="0.0.0.0",
        bind_port=8001,
        timeout=10,
    ) -> None:
        self.client_callback = client_callback
        self.bind_ip = bind_ip
        self.bind_port = bind_port
        self.stop_event = threading.Event()
        self.server_ready = threading.Event()
        self.exception = ""
        self.traceback = []  # type: List[str]

    def __enter__(self):
        self.serve()

    def __exit__(self, type, value, traceback):
        self.stop()
        if self.traceback:
            raise Exception(traceback)

    def serve(self):
        self.thread = threading.Thread(
            target=self.server_socket, args=(self.server_ready,)
        )
        self.thread.start()
        self.server_ready.wait(timeout=2)
        dprint("EMU: Server Started")
        sleep(0.2)

    def stop(self):
        dprint("stopping")
        self.stop_event.set()
        self.sock.close()
        if self.thread.is_alive():
            self.thread.join()

    def server_socket(self, server_ready: threading.Event):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            self.sock = sock
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind((self.bind_ip, self.bind_port))

            sock.listen(5)
            server_ready.set()

            clientsock, addr = sock.accept()
            dprint("EMU: Client connected")
            try:
                self.client_callback(clientobj(clientsock, addr, self.stop_event))
            except TimeoutError:
                print("EMU: Timed out...")
            except BrokenPipeError:
                dprint("EMU: BrokenPipe, The client closed the socket")
            except Exception as e:
                exc_type, exc_value, exc_traceback = sys.exc_info()

                print("Exception in server '{}'".format(repr(e)))
                traceback.print_exc()
                self.exception = str(e)
                self.traceback = traceback.format_tb(exc_traceback)
            clientsock.close()
            sock.close()
            dprint("Closed socket")
