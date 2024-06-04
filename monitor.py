import os
import psutil
import json
from http.server import SimpleHTTPRequestHandler, HTTPServer
from threading import Thread
from time import sleep
import subprocess
from datetime import timedelta

def get_temperature():
    try:
        temp = os.popen("vcgencmd measure_temp").readline()
        return float(temp.replace("temp=", "").replace("'C\n", ""))
    except Exception as e:
        return None

def get_cpu_usage():
    return psutil.cpu_percent(interval=1)

def get_ram_usage():
    mem = psutil.virtual_memory()
    total_gb = mem.total / (1024 ** 3)
    available_gb = mem.available / (1024 ** 3)
    used_percent = mem.percent
    return total_gb, available_gb, used_percent

def get_swap_usage():
    swap = psutil.swap_memory()
    total_gb = swap.total / (1024 ** 3)
    used_gb = swap.used / (1024 ** 3)
    return total_gb, used_gb

def format_uptime(seconds):
    days = seconds // 86400
    hours = (seconds % 86400) // 3600
    minutes = (seconds % 3600) // 60
    return f"{days} days, {hours} hours, {minutes} minutes"

def get_uptime():
    uptime_seconds = float(os.popen("awk '{print $1}' /proc/uptime").readline())
    uptime_string = format_uptime(int(uptime_seconds))
    return uptime_string

def get_network_latency(host='speedtest.tele2.net'):
    try:
        output = subprocess.check_output(["ping", "-c", "1", host], timeout=2)
        latency = float(output.decode().split('time=')[1].split(' ms')[0])
        return latency
    except subprocess.TimeoutExpired:
        return None
    except Exception as e:
        return None

def get_disk_usage(path):
    try:
        usage = psutil.disk_usage(path)
        total_gb = usage.total / (1024 ** 3)
        used_gb = usage.used / (1024 ** 3)
        return total_gb, used_gb
    except Exception as e:
        return None, None

def get_status():
    print("Estado")
    temperature = get_temperature()
    cpu_usage = get_cpu_usage()
    total_ram, available_ram, ram_usage_percent = get_ram_usage()
    swap_total, swap_used = get_swap_usage()
    uptime = get_uptime()
    latency = get_network_latency('speedtest.tele2.net')  # Servidor en Madrid
    usb1_total, usb1_used = get_disk_usage('/mnt/usb1/')
    usb2_total, usb2_used = get_disk_usage('/mnt/usb2/')
    mmcblk0p2_total, mmcblk0p2_used = get_disk_usage('/')
    status = {
        'temperature': temperature,
        'cpu_usage': cpu_usage,
        'total_ram': total_ram,
        'available_ram': available_ram,
        'ram_usage_percent': ram_usage_percent,
        'swap_total': swap_total,
        'swap_used': swap_used,
        'uptime': uptime,
        'latency': latency,
        'usb1_total': usb1_total,
        'usb1_used': usb1_used,
        'usb2_total': usb2_total,
        'usb2_used': usb2_used,
        'mmcblk0p2_total': mmcblk0p2_total,
        'mmcblk0p2_used': mmcblk0p2_used
    }
    return status

class RequestHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/status':
            try:
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                status = get_status()
                self.wfile.write(json.dumps(status).encode())
            except Exception as e:
                self.send_response(502)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'error': 'Bad Gateway', 'message': str(e)}).encode())
        elif self.path == '/':
            try:
                self.send_response(200)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                with open('/mnt/usb2/monitor/index.html', 'r') as f:
                    self.wfile.write(f.read().encode())
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'error': 'Internal Server Error', 'message': str(e)}).encode())

    def do_POST(self):
        if self.path == '/restart':
            try:
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'status': 'restarting'}).encode())
                os.system('sudo reboot')
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'error': 'Internal Server Error', 'message': str(e)}).encode())

def run_server():
    server_address = ('', 5000)
    httpd = HTTPServer(server_address, RequestHandler)
    print(f'Starting httpd on port 5000...')
    httpd.serve_forever()

if __name__ == '__main__':
    # Start the server in a separate thread
    server_thread = Thread(target=run_server)
    server_thread.daemon = True
    server_thread.start()

    # Keep the main thread alive
    while True:
        sleep(1)