import importlib.util
import json
import socket
import sys
import threading
import time
import traceback

DITLANG_CALLBACK = None
SERVER: socket.socket = None  # type: ignore


def run_client():
    global SERVER, DITLANG_CALLBACK
    port = int(sys.argv[1])
    SERVER = socket.create_connection(("127.0.0.1", port))
    SERVER.sendall(_encode({"type": "connect", "lang": "Python"}))

    while True:
        try:
            raw = SERVER.recv(1024)
            if raw:
                json_data = _decode(raw)
                try:
                    if json_data["type"] == "call_func":
                        path = json_data["func_path"]
                        name = path[path.rfind("/") + 1 :]
                        spec = importlib.util.spec_from_file_location(name, path)
                        script = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(script)  # type: ignore
                        threading.Thread(
                            target=_exe_ditlang_loop, args=[script], daemon=True
                        ).start()
                    elif json_data["type"] == "ditlang_callback":
                        DITLANG_CALLBACK = json_data["result"]
                    else:
                        raise NotImplementedError
                except:
                    _crash()
            else:
                SERVER.sendall(_encode({"type": "heart"}))

            time.sleep(0.001)  # Prevent pinning the CPU
        except BrokenPipeError:  # Server has closed
            SERVER.close()
            break


def _exe_ditlang_loop(script):
    global SERVER
    try:
        res = script.reserved_name(exe_ditlang)
        job_mes = {"type": "finish_func", "result": str(res)}
        SERVER.sendall(_encode(job_mes))
    except:
        _crash()


def exe_ditlang(value) -> str:
    global SERVER, DITLANG_CALLBACK
    SERVER.sendall(_encode({"type": "exe_ditlang", "result": value}))

    while True:
        if DITLANG_CALLBACK is not None:
            temp = DITLANG_CALLBACK
            DITLANG_CALLBACK = None
            return temp


def _crash():
    global SERVER
    tb = traceback.format_exc()
    job_mes = {"type": "crash", "result": tb}
    SERVER.sendall(_encode(job_mes))


def _encode(message: dict):
    return json.dumps(message).encode()


def _decode(message: bytes):
    return json.loads(message.decode())


run_client()
