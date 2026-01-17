# Path: api/launcher.py
# Version: 20.1
# Description: Управление сервером. Добавлен метод is_running.

import uvicorn
import threading
import socket
from .server import app

class ServerThread(threading.Thread):
    def __init__(self, host="0.0.0.0", port=8000):
        super().__init__()
        self.host = host
        self.port = port
        self.server = None
        self.daemon = True 

    def run(self):
        config = uvicorn.Config(app, host=self.host, port=self.port, log_level="warning")
        self.server = uvicorn.Server(config)
        self.server.run()

    def stop(self):
        if self.server:
            self.server.should_exit = True

class SyncManager:
    _thread = None
    _last_url = ""
    
    @staticmethod
    def get_local_ip():
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return "127.0.0.1"

    @staticmethod
    def is_running():
        return SyncManager._thread is not None and SyncManager._thread.is_alive()

    @staticmethod
    def start_server(port=8000):
        if SyncManager.is_running():
            return SyncManager._last_url
        
        SyncManager._thread = ServerThread(port=port)
        SyncManager._thread.start()
        
        ip = SyncManager.get_local_ip()
        SyncManager._last_url = f"http://{ip}:{port}"
        return SyncManager._last_url

    @staticmethod
    def stop_server():
        if SyncManager._thread:
            SyncManager._thread.stop()
            SyncManager._thread = None
            return "Stopped"
        return "Not running"