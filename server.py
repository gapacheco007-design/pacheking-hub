import http.server
import socketserver
import json
import psutil
import shutil
import urllib.request
import os

PORT = 5000

class HubHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def do_GET(self):
        if self.path == '/api/stats':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()

            # CPU
            cpu_pct = psutil.cpu_percent(interval=None)
            
            # RAM
            mem = psutil.virtual_memory()
            ram_used_gb = round((mem.total - mem.available) / (1024**3), 1)
            ram_total_gb = round(mem.total / (1024**3), 1)
            ram_pct = mem.percent

            # DISCO
            disk = shutil.disk_usage('/opt/downloader-stack')
            disk_used_gb = round((disk.total - disk.free) / (1024**3), 1)
            disk_total_gb = round(disk.total / (1024**3), 1)
            disk_pct = round(((disk.total - disk.free) / disk.total) * 100, 1)

            # NET I/O (Oracle outbound)
            net = psutil.net_io_counters()
            bytes_sent_gb = round(net.bytes_sent / (1024**3), 1)

            # Contenedores / Servicios
            services = [
                {"name": "Aria2 Engine", "port": 6800, "status": "Online", "url": "https://eye-tucson-thread-assured.trycloudflare.com"},
                {"name": "AriaNg Web", "port": 6880, "status": "Online", "url": "https://eye-tucson-thread-assured.trycloudflare.com"},
                {"name": "MeTube (YouTube)", "port": 8081, "status": "Online", "url": "https://privacy-responsibilities-buttons-frankfurt.trycloudflare.com"},
                {"name": "FileBrowser", "port": 8080, "status": "Online", "url": "https://leaving-velvet-period-mind.trycloudflare.com"}
            ]

            # Aria2 Active Downloads
            downloads = []
            try:
                rpc_data = json.dumps({
                    "jsonrpc": "2.0",
                    "id": "hub",
                    "method": "aria2.tellActive",
                    "params": ["token:1d0d8b3a3a52f684e6740180b134d6d8"]
                }).encode('utf-8')
                req = urllib.request.Request('http://127.0.0.1:6800/jsonrpc', data=rpc_data, headers={'Content-Type': 'application/json'})
                with urllib.request.urlopen(req, timeout=1) as resp:
                    res = json.loads(resp.read().decode('utf-8'))
                    for item in res.get('result', []):
                        name = "Descarga Directa"
                        if item.get('bittorrent', {}).get('info', {}).get('name'):
                            name = item['bittorrent']['info']['name']
                        elif item.get('files') and len(item['files']) > 0:
                            path = item['files'][0].get('path', '')
                            if path:
                                name = os.path.basename(path)
                        
                        total = int(item.get('totalLength', 0))
                        completed = int(item.get('completedLength', 0))
                        speed = int(item.get('downloadSpeed', 0))
                        pct = round((completed / total * 100), 1) if total > 0 else 0
                        speed_str = f"{round(speed / (1024*1024), 1)} MB/s" if speed > 1024*1024 else f"{round(speed / 1024, 1)} KB/s"
                        size_str = f"{round(total / (1024**3), 1)} GB" if total > 1024**3 else f"{round(total / (1024*1024), 1)} MB"

                        downloads.append({
                            "name": name,
                            "progress": pct,
                            "speed": speed_str,
                            "size": size_str,
                            "eta": "--"
                        })
            except Exception:
                pass

            data = {
                "cpu": {"percent": cpu_pct},
                "ram": {"percent": ram_pct, "used": ram_used_gb, "total": ram_total_gb},
                "disk": {"percent": disk_pct, "used": disk_used_gb, "total": disk_total_gb},
                "oracle_out": {"used_gb": bytes_sent_gb, "limit_tb": 10},
                "services": services,
                "downloads": downloads
            }
            self.wfile.write(json.dumps(data).encode('utf-8'))
        else:
            super().do_GET()

if __name__ == '__main__':
    os.chdir('/opt/downloader-stack/dashboard')
    with socketserver.TCPServer(("", PORT), HubHandler) as httpd:
        httpd.serve_forever()
