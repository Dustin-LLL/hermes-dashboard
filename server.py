#!/usr/bin/env python3
"""
Hermes Dashboard Server
提供 Web UI 和 API 来管理 Hermes 配置
"""
import os
import sys
import json
import subprocess
import socketserver
import asyncio
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import threading

PORT = 8765
HERMES_HOME = os.path.expanduser("~/.hermes")
os.chdir(os.path.dirname(os.path.abspath(__file__)))

class DashboardHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=HERMES_HOME + "/hermes-dashboard", **kwargs)
    
    def do_POST(self):
        if self.path == '/api/exec':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            command = data.get('command', '')
            
            # Sanitize command - only allow specific commands
            allowed_patterns = [
                'hermes config', 'hermes gateway', 'hermes status', 
                'hermes doctor', 'hermes backup', 'hermes sessions',
                'cat ~/.hermes/', 'ps aux | grep hermes',
                'tail -', 'rm -f ~/.hermes/logs/', 'echo ',
                'grep -v', 'tee ~/.hermes/.env'
            ]
            
            # For now, allow hermes commands and basic file operations
            if command.startswith('hermes ') or command.startswith('cat ') or \
               command.startswith('ps ') or command.startswith('tail ') or \
               command.startswith('grep ') or command.startswith('rm ') or \
               command.startswith('echo ') or command.startswith('systemctl ') or \
               command.startswith('head ') or command.startswith('wc ') or \
               command.startswith('mv ') or command.startswith('tee ') or \
               command.startswith('curl ') or command.startswith('gh '):
                try:
                    result = subprocess.run(
                        command, shell=True, capture_output=True, 
                        text=True, timeout=30,
                        env={**os.environ, 'HOME': os.path.expanduser('~')}
                    )
                    output = result.stdout + result.stderr
                except subprocess.TimeoutExpired:
                    output = "Command timed out"
                except Exception as e:
                    output = str(e)
            else:
                output = "Command not allowed"
            
            response = json.dumps({'output': output, 'error': None})
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(response.encode())
        elif self.path == '/api/weixin_qr':
            # WeChat QR code login - spawns background process
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            action = data.get('action', 'start')
            
            QR_STATE_FILE = HERMES_HOME + '/.weixin_qr_state.json'
            
            if action == 'start':
                # Kill any existing QR process
                subprocess.run(['pkill', '-f', 'weixin_qr.py'], stderr=subprocess.DEVNULL)
                
                # Start QR login in background
                import uuid
                session_id = str(uuid.uuid4())[:8]
                qr_script = os.path.join(os.path.dirname(__file__), 'weixin_qr.py')
                log_file = HERMES_HOME + f'/logs/weixin_qr_{session_id}.log'
                os.makedirs(HERMES_HOME + '/logs', exist_ok=True)
                
                # Save session ID for polling
                with open(QR_STATE_FILE, 'w') as f:
                    json.dump({'session_id': session_id, 'status': 'starting'}, f)
                
                # Start background process
                subprocess.Popen(
                    [sys.executable, qr_script, session_id],
                    stdout=open(log_file, 'w'),
                    stderr=subprocess.STDOUT,
                    env={**os.environ, 'HOME': os.path.expanduser('~')}
                )
                
                response = json.dumps({'status': 'started', 'session_id': session_id})
            elif action == 'status':
                # Read current QR status
                if os.path.exists(QR_STATE_FILE):
                    with open(QR_STATE_FILE, 'r') as f:
                        state = json.load(f)
                    response = json.dumps(state)
                else:
                    response = json.dumps({'status': 'no_session'})
            elif action == 'stop':
                subprocess.run(['pkill', '-f', 'weixin_qr.py'], stderr=subprocess.DEVNULL)
                if os.path.exists(QR_STATE_FILE):
                    os.remove(QR_STATE_FILE)
                response = json.dumps({'status': 'stopped'})
            else:
                response = json.dumps({'error': 'Unknown action'})
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(response.encode())
        else:
            self.send_error(404)
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
    def log_message(self, format, *args):
        print(f"[{self.log_date_time_string()}] {format % args}")

def run_server():
    with socketserver.TCPServer(("", PORT), DashboardHandler) as httpd:
        print(f"🚀 Hermes Dashboard 启动成功!")
        print(f"📱 请访问: http://localhost:{PORT}")
        print(f"🌐 局域网访问: http://$(hostname -I | awk '{{print $1}}'):{PORT}")
        print(f"\n按 Ctrl+C 停止服务器\n")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n服务器已停止")
            sys.exit(0)

if __name__ == '__main__':
    # Check if port is available
    try:
        run_server()
    except OSError as e:
        if e.errno == 98:  # Address already in use
            print(f"端口 {PORT} 已被占用，尝试其他端口...")
            PORT += 1
            run_server()
        else:
            raise
