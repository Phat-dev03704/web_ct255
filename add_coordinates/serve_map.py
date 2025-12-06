"""Simple HTTP server to serve the add_coordinates folder for the map editor.

Usage:
  python serve_map.py  # serves on http://localhost:8000
"""
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
import webbrowser
import sys

PORT = 8000
ROOT = Path(__file__).parent

if __name__ == '__main__':
    handler = SimpleHTTPRequestHandler
    # change working dir to folder containing this script
    import os
    os.chdir(str(ROOT))
    addr = ('', PORT)
    httpd = ThreadingHTTPServer(addr, handler)
    url = f'http://localhost:{PORT}/map_editor.html'
    print(f'Serving {ROOT} at {url}')
    try:
        webbrowser.open(url)
    except Exception:
        pass
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print('\nStopped')
        sys.exit(0)
