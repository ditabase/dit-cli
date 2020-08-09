import importlib.util
import json
import socket
import sys
import time
import traceback


def run_client():
    port = int(sys.argv[1])
    try:
        server = socket.create_connection(("127.0.0.1", port))
    except ConnectionRefusedError:
        return
    server.sendall(_encode({"type": "connect", "lang": "Python"}))

    while True:
        try:
            path = server.recv(1024).decode()
            if path:
                try:
                    name = path[path.rfind("/") + 1 :]
                    spec = importlib.util.spec_from_file_location(name, path)
                    script = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(script)
                    result: str = script.run()
                    job_mes = {"type": "job", "crash": False, "result": str(result)}
                except BaseException:
                    tb = traceback.format_exc()
                    job_mes = {"type": "job", "crash": True, "result": tb}
                finally:
                    server.sendall(_encode(job_mes))
            else:
                server.sendall(_encode({"type": "heart"}))
            time.sleep(0.001)  # Prevent pinning the CPU
        except BrokenPipeError:  # Server has closed
            server.close()
            break


def _encode(message: dict):
    return json.dumps(message).encode()


run_client()
