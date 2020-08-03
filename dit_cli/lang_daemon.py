"""All scripts are run via the command line (os.subprocess), which by itself is slow.
This daemon runs a socket connection to a client in each language.
When a script is needed, it just asks the client to run the code instead.
This is roughly 50% faster, and can be made much faster still."""
import json
import selectors
import socket
import time
from ast import literal_eval
from dataclasses import dataclass
from subprocess import Popen
from threading import Thread
from typing import Union

from dit_cli import CONFIG
from dit_cli.data_classes import ScriptEvalJob
from dit_cli.exceptions import CodeError


"""Dev note: much of this is copied from https://realpython.com/python-sockets/
It's a little crude, and was intended for working with many clients that
all have jobs at once, whereas this runs only 1 script at a time, linearly.
It's good enough to solve the critical performance issue (subprocess.Popen ~= 100ms)
and can be redesigned to send multiple jobs at once,
when jobs are no longer processed linearly.
You could also run multiple eval processes, and multiple daemon clients,
but this is probably a long ways off."""


@dataclass
class ClientInfo:
    """Contains the address (addr) and language (lang) of a client daemon"""

    addr: int
    lang: str


JOB: ScriptEvalJob = None
CLIENTS = []
PORT = None


def start_daemon():
    """Starts the language daemon thread, 
    which will manage all client daemons in other languages."""
    Thread(target=_daemon_loop, daemon=True).start()


def start_client(lang: str):
    """Start a client daemon for a specific language.
    Will not start duplicate clients"""

    def _thread_client(cmd: list):
        Popen(cmd)

    global CLIENTS, PORT
    if lang not in CLIENTS:  # Don't start a second client for a lang
        while True:
            if PORT:  # Wait for port to be assigned
                CLIENTS.append(lang)
                cmd = [CONFIG[lang]["path"], CONFIG[lang]["socket"], str(PORT)]
                Thread(target=_thread_client, daemon=True, args=(cmd,)).start()
                break


def run_script(job: ScriptEvalJob) -> ScriptEvalJob:
    """Send a job to the client daemons and get the response."""
    global JOB
    JOB = job
    while True:
        if job.result:  # Wait for job to finish, is assigned in _service_client
            JOB = None
            return job


def _daemon_loop():
    """Starts the socket server and runs the main event loop"""
    global PORT
    # Sending port 0 will get a random open port
    with socket.create_server(("127.0.0.1", 0), family=socket.AF_INET) as daemon:
        daemon.listen()
        daemon.setblocking(False)
        sel = selectors.DefaultSelector()
        sel.register(daemon, selectors.EVENT_READ, data=None)
        # Assign the port so it can be sent to clients
        PORT = daemon.getsockname()[1]

        while True:  # This while will be destroyed only when the thread exits
            events = sel.select(timeout=None)
            for key, mask in events:
                if key.data is None:
                    _accept_client(key.fileobj, sel)
                else:
                    _service_client(key, mask)


def _accept_client(daemon: socket.socket, sel: selectors.DefaultSelector):
    """Accept a connection from a client daemon"""
    client, addr = daemon.accept()
    recv_data = _decode(client.recv(1024))
    client.setblocking(False)
    data = ClientInfo(addr, recv_data["lang"])
    events = selectors.EVENT_READ | selectors.EVENT_WRITE
    sel.register(client, events, data=data)


def _service_client(key: selectors.SelectorKey, mask: int):
    """Send or receive message from a client daemon."""
    global JOB
    client: socket.socket = key.fileobj
    info: ClientInfo = key.data
    if mask & selectors.EVENT_READ:
        recv_data = client.recv(1024)
        if recv_data:
            data = _decode(recv_data)
            JOB.crash = data["crash"]
            JOB.result = data["result"]
    elif mask & selectors.EVENT_WRITE:
        # Job is for this language, and the job has not already been assigned
        if JOB and JOB.lang == info.lang and not JOB.active:
            client.sendall(JOB.file_path.encode())
            JOB.active = True


def _decode(raw: bytes) -> dict:
    """Convert client messages into dictionaries"""
    return json.loads(raw.decode())
