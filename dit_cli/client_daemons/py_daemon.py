import importlib.util
import json
import socket
import sys
import traceback


def run_client():
    port = int(sys.argv[1])
    with socket.create_connection(("127.0.0.1", port)) as server:
        server.sendall(f'{{"lang": "Python"}}'.encode())

        while True:
            path = server.recv(1024).decode()
            if path:
                try:
                    name = path[path.rfind("/") + 1 :]
                    spec = importlib.util.spec_from_file_location(name, path)
                    script = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(script)
                    result: str = script.run()
                    job_mes = json.dumps({"crash": False, "result": str(result)})
                except BaseException:
                    tb = traceback.format_exc()
                    job_mes = json.dumps({"crash": True, "result": tb})
                finally:
                    server.sendall(job_mes.encode())


run_client()
