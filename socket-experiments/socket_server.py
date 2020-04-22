"""
Demonstrates the feasibility of using a Python socket server to run all scripts.
All languages (and Windows) support Unix style sockets, and languages can import
code in their own language much faster than Python execute it.

In this configuration, Running 72 scripts as fast as possible completes the round
trip in ~1700ms, so roughly 23ms per script. This can be sped up in several
ways which are outside the scope of this particular change.
"""

import ast
import selectors
import socket
import subprocess
import threading
import time
from dataclasses import dataclass

SEL = selectors.DefaultSelector()
JOBS = {
    "Python": [
        "/home/isaiah/general/dit-cli/socket-experiments/py_script.py",
        "/home/isaiah/general/dit-cli/socket-experiments/py_script2.py",
        "/home/isaiah/general/dit-cli/socket-experiments/py_script.py",
        "/home/isaiah/general/dit-cli/socket-experiments/py_script2.py",
        "/home/isaiah/general/dit-cli/socket-experiments/py_script.py",
        "/home/isaiah/general/dit-cli/socket-experiments/py_script2.py",
        "/home/isaiah/general/dit-cli/socket-experiments/py_script.py",
        "/home/isaiah/general/dit-cli/socket-experiments/py_script2.py",
        "/home/isaiah/general/dit-cli/socket-experiments/py_script.py",
        "/home/isaiah/general/dit-cli/socket-experiments/py_script2.py",
        "/home/isaiah/general/dit-cli/socket-experiments/py_script.py",
        "/home/isaiah/general/dit-cli/socket-experiments/py_script2.py",
        "/home/isaiah/general/dit-cli/socket-experiments/py_script.py",
        "/home/isaiah/general/dit-cli/socket-experiments/py_script2.py",
        "/home/isaiah/general/dit-cli/socket-experiments/py_script.py",
        "/home/isaiah/general/dit-cli/socket-experiments/py_script2.py",
        "/home/isaiah/general/dit-cli/socket-experiments/py_script.py",
        "/home/isaiah/general/dit-cli/socket-experiments/py_script2.py",
        "/home/isaiah/general/dit-cli/socket-experiments/py_script.py",
        "/home/isaiah/general/dit-cli/socket-experiments/py_script2.py",
        "/home/isaiah/general/dit-cli/socket-experiments/py_script.py",
        "/home/isaiah/general/dit-cli/socket-experiments/py_script2.py",
        "/home/isaiah/general/dit-cli/socket-experiments/py_script.py",
        "/home/isaiah/general/dit-cli/socket-experiments/py_script2.py",
        "/home/isaiah/general/dit-cli/socket-experiments/py_script.py",
        "/home/isaiah/general/dit-cli/socket-experiments/py_script2.py",
        "/home/isaiah/general/dit-cli/socket-experiments/py_script.py",
        "/home/isaiah/general/dit-cli/socket-experiments/py_script2.py",
        "/home/isaiah/general/dit-cli/socket-experiments/py_script.py",
        "/home/isaiah/general/dit-cli/socket-experiments/py_script2.py",
        "/home/isaiah/general/dit-cli/socket-experiments/py_script.py",
        "/home/isaiah/general/dit-cli/socket-experiments/py_script2.py",
        "/home/isaiah/general/dit-cli/socket-experiments/py_script.py",
        "/home/isaiah/general/dit-cli/socket-experiments/py_script2.py",
        "/home/isaiah/general/dit-cli/socket-experiments/py_script.py",
        "/home/isaiah/general/dit-cli/socket-experiments/py_script2.py",
    ],
    "Javascript": [
        "/home/isaiah/general/dit-cli/socket-experiments/js_script.js",
        "/home/isaiah/general/dit-cli/socket-experiments/js_script2.js",
        "/home/isaiah/general/dit-cli/socket-experiments/js_script.js",
        "/home/isaiah/general/dit-cli/socket-experiments/js_script2.js",
        "/home/isaiah/general/dit-cli/socket-experiments/js_script.js",
        "/home/isaiah/general/dit-cli/socket-experiments/js_script2.js",
        "/home/isaiah/general/dit-cli/socket-experiments/js_script.js",
        "/home/isaiah/general/dit-cli/socket-experiments/js_script2.js",
        "/home/isaiah/general/dit-cli/socket-experiments/js_script.js",
        "/home/isaiah/general/dit-cli/socket-experiments/js_script2.js",
        "/home/isaiah/general/dit-cli/socket-experiments/js_script.js",
        "/home/isaiah/general/dit-cli/socket-experiments/js_script2.js",
        "/home/isaiah/general/dit-cli/socket-experiments/js_script.js",
        "/home/isaiah/general/dit-cli/socket-experiments/js_script2.js",
        "/home/isaiah/general/dit-cli/socket-experiments/js_script.js",
        "/home/isaiah/general/dit-cli/socket-experiments/js_script2.js",
        "/home/isaiah/general/dit-cli/socket-experiments/js_script.js",
        "/home/isaiah/general/dit-cli/socket-experiments/js_script2.js",
        "/home/isaiah/general/dit-cli/socket-experiments/js_script.js",
        "/home/isaiah/general/dit-cli/socket-experiments/js_script2.js",
        "/home/isaiah/general/dit-cli/socket-experiments/js_script.js",
        "/home/isaiah/general/dit-cli/socket-experiments/js_script2.js",
        "/home/isaiah/general/dit-cli/socket-experiments/js_script.js",
        "/home/isaiah/general/dit-cli/socket-experiments/js_script2.js",
        "/home/isaiah/general/dit-cli/socket-experiments/js_script.js",
        "/home/isaiah/general/dit-cli/socket-experiments/js_script2.js",
        "/home/isaiah/general/dit-cli/socket-experiments/js_script.js",
        "/home/isaiah/general/dit-cli/socket-experiments/js_script2.js",
        "/home/isaiah/general/dit-cli/socket-experiments/js_script.js",
        "/home/isaiah/general/dit-cli/socket-experiments/js_script2.js",
        "/home/isaiah/general/dit-cli/socket-experiments/js_script.js",
        "/home/isaiah/general/dit-cli/socket-experiments/js_script2.js",
        "/home/isaiah/general/dit-cli/socket-experiments/js_script.js",
        "/home/isaiah/general/dit-cli/socket-experiments/js_script2.js",
        "/home/isaiah/general/dit-cli/socket-experiments/js_script.js",
        "/home/isaiah/general/dit-cli/socket-experiments/js_script2.js",
    ],
}
START = int(round(time.time() * 1000))
PREV = START
ACTIVE_JOBS: dict = {"Python": False, "Javascript": False}
KEEP_RUNNING = True
TOTAL_JOBS = 72


def _status(message: str, stamp: int = None) -> str:
    global PREV
    if not stamp:
        stamp = int(round(time.time() * 1000))
    print(
        f"{stamp}   {(stamp - START):04}ms   +{(stamp - PREV):03}ms   {message}",
        flush=True,
    )
    PREV = stamp


print("\nTimestamp       Elapsed  Step     Event")
_status("Starting up.")


@dataclass
class ClientInfo:
    addr: int
    lang: str


def _decode(raw: bytes) -> dict:
    return ast.literal_eval(raw.decode())


def accept_client(server: socket.socket):
    client, addr = server.accept()
    start_mes = _decode(client.recv(1024))
    _status(f'{start_mes["lang"]} client connected ({addr})', stamp=start_mes["stamp"])
    client.setblocking(False)
    data = ClientInfo(addr, start_mes["lang"])
    events = selectors.EVENT_READ | selectors.EVENT_WRITE
    SEL.register(client, events, data=data)


def service_client(key, mask):
    global JOBS, ACTIVE_JOBS, TOTAL_JOBS
    client: socket.socket = key.fileobj
    info: ClientInfo = key.data
    if mask & selectors.EVENT_READ:
        recv_data = client.recv(1024)
        if recv_data:
            job = _decode(recv_data)
            if job["type"] == "start":
                pass
                # _status(f'{info.lang} job started', stamp=job['stamp'])
            else:
                # _status(f'{info.lang} job result: {job["result"]}', stamp=job['stamp'])
                ACTIVE_JOBS[info.lang] = False
                TOTAL_JOBS -= 1
        else:
            _status(f"{info.lang} daemon closed connection unexpectedly")
            SEL.unregister(client)
            client.close()
    if mask & selectors.EVENT_WRITE:
        if not ACTIVE_JOBS[info.lang]:
            if len(JOBS[info.lang]) == 0:
                _status(f"Closing connection to {info.lang}")
                client.sendall("CLOSE_CONNECTION".encode())
                client.close()
                SEL.unregister(client)
            for index, job in enumerate(JOBS[info.lang]):
                # _status(f'Sending new job to {info.lang}')
                client.sendall(job.encode())
                del JOBS[info.lang][index]
                ACTIVE_JOBS[info.lang] = True
                break


def start_server():
    global TOTAL_JOBS, CLIENTS
    with socket.create_server(("127.0.0.1", 5500), family=socket.AF_INET) as server:
        server.listen()
        _status("Listening for connections.")
        server.setblocking(False)
        SEL.register(server, selectors.EVENT_READ, data=None)
        CLIENTS.start()

        try:
            while True:
                events = SEL.select(timeout=None)
                for key, mask in events:
                    if key.data is None:
                        accept_client(key.fileobj)
                    else:
                        service_client(key, mask)
                if TOTAL_JOBS == 0:
                    _status("All jobs complete.")
                    break
                if not KEEP_RUNNING:
                    _status("Error with subprocess, stopping server.")
                    break
        except KeyboardInterrupt:
            _status("Keyboard interupt.")
        except BaseException as err:
            _status(err)
        finally:
            _status("Shutting down.")
            SEL.close()


def start_client(cmd, lang):
    global KEEP_RUNNING
    _status(f"Activating {lang} daemon")
    try:
        subprocess.Popen(cmd)
    except BaseException as err:
        _status(err)
        KEEP_RUNNING = False
        raise err


def start_clients():
    start_client(
        [
            "/usr/bin/python",
            "/home/isaiah/general/dit-cli/socket-experiments/py_daemon.py",
        ],
        "Python",
    )
    start_client(
        [
            "/usr/bin/node",
            "/home/isaiah/general/dit-cli/socket-experiments/js_daemon.js",
        ],
        "Javascript",
    )


CLIENTS = threading.Thread(target=start_clients, daemon=True)
start_server()
