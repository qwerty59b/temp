#!/usr/bin/python3.9
# Extremely simple webserver made with the stdlib just for testing purposes

import sys
from http.server import BaseHTTPRequestHandler, HTTPServer

class MyServer(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(bytes("It's working...", "utf-8"))


webServer = HTTPServer(("0.0.0.0", 10000), MyServer)
webServer.serve_forever()
