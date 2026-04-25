#!/usr/bin/env python3
"""
Weixin QR Login Script for Dashboard
微信二维码登录 - 通过状态文件与前端通信
"""
import sys
import os
import json
import time
import asyncio

sys.path.insert(0, '/home/dustin/hermes-agent')

HERMES_HOME = os.path.expanduser('~/.hermes')
STATE_FILE = HERMES_HOME + '/.weixin_qr_state.json'
LOG_DIR = HERMES_HOME + '/logs'
os.makedirs(LOG_DIR, exist_ok=True)

def log(msg):
    """Log to both file and stdout"""
    log_file = LOG_DIR + '/weixin_qr.log'
    timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
    with open(log_file, 'a') as f:
        f.write(f'[{timestamp}] {msg}\n')
    print(f'[{timestamp}] {msg}')

async def get_qrcode(session):
    """获取二维码"""
    from gateway.platforms.weixin import ILINK_BASE_URL, EP_GET_BOT_QR, QR_TIMEOUT_MS, _api_get, _make_ssl_connector, AIOHTTP_AVAILABLE
    
    if not AIOHTTP_AVAILABLE:
        return None, "aiohttp not available"
    
    try:
        qr_resp = await _api_get(
            session,
            base_url=ILINK_BASE_URL,
            endpoint=f"{EP_GET_BOT_QR}?bot_type=3",
            timeout_ms=QR_TIMEOUT_MS,
        )
    except Exception as exc:
        return None, str(exc)
    
    qrcode_value = str(qr_resp.get("qrcode") or "")
    qrcode_url = str(qr_resp.get("qrcode_img_content") or "")
    
    if not qrcode_value:
        return None, "No QR code returned"
    
    return {"qrcode_value": qrcode_value, "qrcode_url": qrcode_url}, None

async def check_status(session, qrcode_value):
    """检查二维码扫描状态"""
    from gateway.platforms.weixin import ILINK_BASE_URL, EP_GET_QR_STATUS, QR_TIMEOUT_MS, _api_get, _make_ssl_connector
    
    try:
        status_resp = await _api_get(
            session,
            base_url=ILINK_BASE_URL,
            endpoint=f"{EP_GET_QR_STATUS}?qrcode={qrcode_value}",
            timeout_ms=QR_TIMEOUT_MS,
        )
    except Exception as exc:
        return "error", str(exc)
    
    return str(status_resp.get("status") or "wait"), status_resp

async def run_qr_login(session_id):
    """运行二维码登录流程"""
    import aiohttp
    
    log(f"Starting WeChat QR login, session: {session_id}")
    
    async with aiohttp.ClientSession(trust_env=True) as session:
        # Step 1: Get QR code
        qr_data, err = await get_qrcode(session)
        if err:
            update_state({'status': 'error', 'error': err, 'session_id': session_id})
            log(f"Failed to get QR code: {err}")
            return
        
        update_state({
            'status': 'wait',
            'qrcode_url': qr_data['qrcode_url'],
            'qrcode_value': qr_data['qrcode_value'],
            'session_id': session_id
        })
        log(f"Got QR code, URL length: {len(qr_data['qrcode_url'])}")
        
        # Step 2: Poll for scan status
        deadline = time.time() + 480  # 8 minutes timeout
        refresh_count = 0
        
        while time.time() < deadline:
            status, resp = await check_status(session, qr_data['qrcode_value'])
            log(f"Status: {status}")
            
            if status == "wait":
                update_state({'status': 'wait'})
            elif status == "scaned":
                update_state({'status': 'scaned'})
            elif status == "scaned_but_redirect":
                # Handle redirect - update base URL
                redirect_host = str(resp.get("redirect_host") or "")
                if redirect_host:
                    log(f"Redirect to: {redirect_host}")
                    update_state({'status': 'redirect', 'redirect_host': redirect_host})
            elif status == "expired":
                refresh_count += 1
                if refresh_count > 3:
                    update_state({'status': 'error', 'error': '二维码多次过期'})
                    log("QR code expired too many times")
                    return
                log(f"QR expired, refreshing ({refresh_count}/3)")
                update_state({'status': 'refreshing'})
                qr_data, err = await get_qrcode(session)
                if err:
                    update_state({'status': 'error', 'error': err})
                    return
                update_state({
                    'status': 'wait',
                    'qrcode_url': qr_data['qrcode_url'],
                    'qrcode_value': qr_data['qrcode_value']
                })
            elif status == "confirmed":
                # Login success! Extract credentials
                account_id = str(resp.get("account_id") or "")
                token = str(resp.get("token") or "")
                base_url = str(resp.get("base_url") or "")
                user_id = str(resp.get("user_id") or "")
                
                log(f"Login confirmed! account_id: {account_id}")
                
                # Save credentials to .env
                save_credentials(account_id, token, base_url)
                
                update_state({
                    'status': 'confirmed',
                    'account_id': account_id,
                    'user_id': user_id
                })
                return
            elif status == "error":
                update_state({'status': 'error', 'error': str(resp)})
            
            await asyncio.sleep(2)
        
        # Timeout
        update_state({'status': 'error', 'error': '登录超时'})
        log("QR login timeout")

def update_state(state):
    """更新状态文件"""
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, ensure_ascii=False)

def save_credentials(account_id, token, base_url):
    """保存凭证到 .env 文件"""
    env_file = HERMES_HOME + '/.env'
    
    # Read existing .env
    env_vars = {}
    if os.path.exists(env_file):
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if '=' in line:
                    key, val = line.split('=', 1)
                    env_vars[key] = val
    
    # Update with new values
    env_vars['WEIXIN_ACCOUNT_ID'] = account_id
    env_vars['WEIXIN_TOKEN'] = token
    if base_url:
        env_vars['WEIXIN_BASE_URL'] = base_url
    
    # Write back
    with open(env_file, 'w') as f:
        for key, val in env_vars.items():
            f.write(f'{key}={val}\n')
    
    log(f"Credentials saved to {env_file}")

def main():
    session_id = sys.argv[1] if len(sys.argv) > 1 else 'unknown'
    
    # Initialize state
    update_state({'status': 'starting', 'session_id': session_id})
    
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(run_qr_login(session_id))
    except KeyboardInterrupt:
        log("Interrupted by user")
        update_state({'status': 'stopped'})
    except Exception as exc:
        log(f"Error: {exc}")
        update_state({'status': 'error', 'error': str(exc)})

if __name__ == '__main__':
    main()