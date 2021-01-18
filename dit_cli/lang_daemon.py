"""All scripts are run via the command line (os.subprocess), which by itself is slow.
This daemon runs a socket connection to a client in each language.
When a script is needed, it just asks the client to run the code instead.
This is roughly 50% faster, and can be made much faster still."""
import json
import selectors
import socket
import subprocess
import sys
import time
from dataclasses import dataclass
from threading import Thread
from typing import List, Optional

from dit_cli.exceptions import MissingLangPropertyError
from dit_cli.oop import GuestDaemonJob, JobType, d_Func, d_Lang

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


PORT: Optional[int] = None
CLIENTS: List[d_Lang] = []
JOB: Optional[GuestDaemonJob] = None
CONTINUE: bool = True


def start_daemon():
    """Starts the language daemon thread,
    which will manage all client daemons in other languages."""
    Thread(target=_daemon_loop, daemon=True).start()


def run_job(job: GuestDaemonJob) -> Optional[GuestDaemonJob]:
    global CLIENTS, PORT, JOB
    if job.type_ == JobType.CALL_FUNC:
        if job.func.lang not in CLIENTS:
            CLIENTS.append(job.func.lang)
            while True:
                if PORT is not None:
                    _start_guest(job.func.lang)
                    break
        JOB = job
        while True:
            if JOB.type_ == JobType.FINISH_FUNC:
                job = JOB
                JOB = None
                return job
            elif JOB.type_ == JobType.EXE_DITLANG:
                raise NotImplementedError


def _start_guest(lang: d_Lang):
    global PORT
    file_extension = lang.get_prop("file_extension")
    daemon_path = "/tmp/dit/" + lang.name + "_guest_daemon." + file_extension
    daemon_body = lang.find_attr("guest_daemon")
    if daemon_body is None or not isinstance(daemon_body, d_Func):
        raise MissingLangPropertyError("A lang had no guest_daemon function")
    open(daemon_path, "w").write(bytes(daemon_body.view).decode())
    path = lang.get_prop("executable_path")
    cmd: List[str] = [path, daemon_path, str(PORT)]
    subprocess.Popen(cmd, stdout=sys.stdout)


def _daemon_loop():
    """Starts the socket server and runs the main event loop"""
    global PORT
    # Sending port 0 will get a random open port
    with socket.create_server(("127.0.0.1", 0)) as daemon:
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
                    _accept_client(key.fileobj, sel)  # type: ignore
                else:
                    _service_client(key, mask)


def _accept_client(daemon: socket.socket, sel: selectors.DefaultSelector):
    """Accept a connection from a client daemon"""
    client, addr = daemon.accept()
    recv_data = _decode(client.recv(1024))
    if recv_data["type"] == "connect":
        client.setblocking(False)
        data = ClientInfo(addr, recv_data["lang"])
        events = selectors.EVENT_READ | selectors.EVENT_WRITE
        sel.register(client, events, data=data)


def _service_client(key: selectors.SelectorKey, mask: int):
    """Send or receive message from a client daemon."""
    global JOB
    client: socket.socket = key.fileobj  # type: ignore
    info: ClientInfo = key.data
    if JOB and mask & selectors.EVENT_READ:
        recv_data = client.recv(1024)
        if recv_data:
            data = _decode(recv_data)
            if data["type"] == JobType.CRASH.value:
                raise NotImplementedError
            elif data["type"] == JobType.EXE_DITLANG.value:
                raise NotImplementedError
            elif data["type"] == JobType.FINISH_FUNC.value:
                JOB.type_ = JobType.FINISH_FUNC
                JOB.active = False

    elif mask & selectors.EVENT_WRITE:
        if (
            JOB is not None
            and not JOB.active
            and JOB.func.lang.name == info.lang
            and JOB.type_ in [JobType.CALL_FUNC, JobType.DITLANG_CALLBACK]
        ):
            mes = JOB.get_json()
            client.sendall(mes)
            JOB.active = True


def _decode(raw: bytes) -> dict:
    """Convert client messages into dictionaries"""
    return json.loads(raw.decode())
