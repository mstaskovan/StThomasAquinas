from argparse import ArgumentParser
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from ipaddress import ip_address
from pathlib import Path
import socket


class LibraryHandler(SimpleHTTPRequestHandler):
    extensions_map = {**SimpleHTTPRequestHandler.extensions_map, ".epub": "application/epub+zip"}


def serve():
    parser = ArgumentParser()
    parser.add_argument("--lan", action="store_true")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    folder = Path(__file__).resolve().parent / "docs"
    handler = partial(LibraryHandler, directory=folder)
    bind = "0.0.0.0" if args.lan else "127.0.0.1"
    with ThreadingHTTPServer((bind, args.port), handler) as server:
        port = server.server_port
        print(f"Na tomto PC: http://127.0.0.1:{port}/", flush=True)
        if args.lan:
            addresses = socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET)
            for address in sorted({entry[4][0] for entry in addresses}):
                ip = ip_address(address)
                if not (ip.is_loopback or ip.is_link_local):
                    print(f"Na mobile cez rovnaku Wi-Fi: http://{address}:{port}/", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    serve()
