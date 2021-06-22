"""All scripts are run via the command line (subprocess.Popen),
which is slow to start up (50-100ms)
This daemon runs a socket connection to a client in each language.
When a script is needed, it just asks the client to run the code instead.
This is roughly 50% faster, and can be made much faster still."""
import json
import selectors
import socket
import subprocess
from dataclasses import dataclass
from threading import Thread
from typing import List, Optional

from dit_cli.exceptions import d_CodeError, d_MissingPropError
from dit_cli.oop import GuestDaemonJob, JobType, d_Func, d_Lang

"""Dev note: much of this is copied from https://realpython.com/python-sockets/
It's a little crude, and was intended for working with many clients that
all have jobs at once, whereas this runs only 1 job at a time, linearly.
It's good enough to solve the critical performance issue (subprocess.Popen ~= 100ms)
and can be redesigned to send multiple jobs at once,
when jobs are no longer processed linearly.
You could also run make this multiprocessing, and have guest langs be multiprocessing
but this is probably a long ways off."""


@dataclass
class d_Client:
    """Contains information about a guest language, including the Popen object
    and the selector key, so that it can be destroyed."""

    lang: d_Lang
    process: subprocess.Popen
    addr: Optional[int] = None
    key: Optional[selectors.SelectorKey] = None


PORT: Optional[int] = None
CLIENTS: List[d_Client] = []
JOB: Optional[GuestDaemonJob] = None
SELECTOR: Optional[selectors.DefaultSelector] = None


def start_daemon():
    """Starts the language daemon thread,
    which will manage all clients in other languages."""
    Thread(target=_daemon_loop, daemon=True).start()


def kill_all():
    global CLIENTS, SELECTOR
    if len(CLIENTS) != 0:
        for client in CLIENTS:
            if client.key is not None and SELECTOR is not None:
                SELECTOR.unregister(client.key.fileobj)
            else:
                raise NotImplementedError
            client.process.kill()
        CLIENTS = []
    if SELECTOR is not None:
        selectors = list(SELECTOR.get_map().items())
        if len(selectors) != 1:
            # The lang_daemon itself should still be registered.
            raise NotImplementedError


def run_job(job: GuestDaemonJob) -> GuestDaemonJob:
    global CLIENTS, PORT, JOB
    if job.type_ == JobType.CALL_FUNC or job.type_ == JobType.DITLANG_CALLBACK:
        if job.func.lang not in [client.lang for client in CLIENTS]:
            while True:
                if PORT is not None:
                    _start_guest(job.func.lang)
                    break
        JOB = job
        while True:
            if JOB.type_ == JobType.FINISH_FUNC or JOB.type_ == JobType.EXE_DITLANG:
                job = JOB
                job.active = False
                JOB = None
                return job
            elif JOB.crash is not None:
                raise JOB.crash
    raise NotImplementedError


def _start_guest(lang: d_Lang):
    global PORT, CLIENTS
    file_extension = lang.get_prop("file_extension")
    daemon_path = "/tmp/dit/" + lang.name + "_guest_daemon." + file_extension
    daemon_body = lang.find_attr("guest_daemon")
    if daemon_body is None or not isinstance(daemon_body, d_Func):
        raise d_MissingPropError(lang.name, "guest_daemon")
    open(daemon_path, "w").write(bytes(daemon_body.view).decode())
    path = lang.get_prop("executable_path")
    cmd: List[str] = [
        path,
        daemon_path,
        str(PORT),
    ]
    proc = subprocess.Popen(cmd)
    CLIENTS.append(d_Client(lang, proc))


def _daemon_loop():
    """Starts the socket server and runs the main event loop"""
    global PORT, SELECTOR
    # Sending port 0 will get a random open port
    with socket.create_server(("127.0.0.1", 0)) as daemon:
        daemon.listen()
        daemon.setblocking(False)
        SELECTOR = selectors.DefaultSelector()
        SELECTOR.register(daemon, selectors.EVENT_READ, data=None)
        # Assign the port so it can be sent to clients
        PORT = daemon.getsockname()[1]

        while True:  # This while will be destroyed only when the thread exits
            events = SELECTOR.select(timeout=None)
            for key, mask in events:
                if key.data is None:
                    _accept_client(key.fileobj)  # type: ignore
                else:
                    _service_client(key, mask)


def _accept_client(sock: socket.socket):
    """Accept a connection from a client lang socket"""
    global SELECTOR, CLIENTS
    conn, addr = sock.accept()
    # { "type": "connect", "lang": "JavaScript"}
    recv_data = _decode(conn.recv(1024))
    if recv_data["type"] == "connect":
        if SELECTOR is None:
            raise NotImplementedError
        conn.setblocking(False)
        client = _get_client(recv_data["lang"])
        events = selectors.EVENT_READ | selectors.EVENT_WRITE
        key = SELECTOR.register(conn, events, data=client.lang.name)
        client.addr = addr
        client.key = key


def _get_client(lang: str) -> d_Client:
    global CLIENTS
    for client in CLIENTS:
        if client.lang.name == lang:
            return client
    raise NotImplementedError
    # TODO: I have gotten this error with Lua, I assume it was a race condition.
    # It was only when purposely crashing lua in debug.
    # This may not ever happen in the CLI.
    # It has now occurred twice in JavaScript, but only while debugging
    # and when the job did not finish because of correctly handled dit error
    # I just got this error to occur outside debug, in the CLI.


def _service_client(key: selectors.SelectorKey, mask: int):
    """Send or receive message from a guest lang."""
    global JOB
    conn: socket.socket = key.fileobj  # type: ignore
    client: d_Client = _get_client(key.data)
    if JOB and mask & selectors.EVENT_READ:
        recv_data = conn.recv(1024)
        if recv_data:
            data = _decode(recv_data)
            if data["type"] == JobType.HEART.value:
                pass
            elif data["type"] == JobType.CRASH.value:
                JOB.crash = d_CodeError(
                    data["result"], JOB.func.lang.name, JOB.func.guest_func_path
                )
            elif data["type"] == JobType.EXE_DITLANG.value:
                JOB.result = data["result"]
                JOB.type_ = JobType.EXE_DITLANG
            elif data["type"] == JobType.FINISH_FUNC.value:
                JOB.type_ = JobType.FINISH_FUNC
                JOB.active = False

    elif mask & selectors.EVENT_WRITE:
        if (
            JOB is not None
            and not JOB.active
            and JOB.func.lang == client.lang
            and JOB.type_
            in [JobType.CALL_FUNC, JobType.DITLANG_CALLBACK, JobType.CLOSE]
        ):
            global PORT
            mes = JOB.get_json()
            conn.sendall(mes)
            JOB.active = True


def _decode(raw: bytes) -> dict:
    """Convert client messages into dictionaries"""
    return json.loads(raw.decode())
