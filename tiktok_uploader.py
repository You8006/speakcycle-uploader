"""
SpeakCycle - TikTok Video Uploader
TikTok Sandbox API対応版

使い方:
1. 認証: python tiktok_uploader.py --auth
2. Sandbox投稿: python tiktok_uploader.py --post --sandbox
3. 本番投稿: python tiktok_uploader.py --post --date 2026-01-23
4. 状態確認: python tiktok_uploader.py --status
"""

import os
import sys
import json
import shutil
import secrets
import hashlib
import base64
import webbrowser
import urllib.parse
import argparse
from datetime import datetime, timedelta
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from typing import Optional

import requests
from dotenv import load_dotenv

# 環境変数読み込み
load_dotenv()

# === 設定 ===
TIKTOK_CLIENT_KEY = os.getenv('TIKTOK_CLIENT_KEY', '')
TIKTOK_CLIENT_SECRET = os.getenv('TIKTOK_CLIENT_SECRET', '')
REDIRECT_URI = os.getenv('TIKTOK_REDIRECT_URI', 'http://localhost:8080/callback')
SCOPES = 'user.info.basic,video.publish,video.upload'

# API URLs
# Sandbox: https://open.tiktokapis.com/v2
# Production: https://open.tiktokapis.com/v2
API_BASE = "https://open.tiktokapis.com/v2"

# ファイルパス
BASE_DIR = Path(__file__).parent
TOKENS_FILE = BASE_DIR / 'tiktok_tokens.json'
HISTORY_FILE = BASE_DIR / 'upload_history.json'
VIDEOS_DIR = BASE_DIR / 'videos'
SAMPLE_VIDEO = BASE_DIR / 'sample_video.mp4'

# 言語設定（本番用）
LANGUAGES = {
    'jp': {
        'name': '🇯🇵 日本語',
        'folder': 'japan',
        'utc_offset': 9,
        'post_hour': 18,
        'post_minute': 0,
        'hashtags': '#英語学習 #English #LearnEnglish #英語',
    },
    'kr': {
        'name': '🇰🇷 韓国語',
        'folder': 'korea',
        'utc_offset': 9,
        'post_hour': 18,
        'post_minute': 30,
        'hashtags': '#영어공부 #English #LearnEnglish #영어',
    },
    'vn': {
        'name': '🇻🇳 ベトナム語',
        'folder': 'vietnam',
        'utc_offset': 7,
        'post_hour': 18,
        'post_minute': 0,
        'hashtags': '#HọcTiếngAnh #English #LearnEnglish #TiếngAnh',
    },
    'ph': {
        'name': '🇵🇭 フィリピン語',
        'folder': 'firipin',
        'utc_offset': 8,
        'post_hour': 18,
        'post_minute': 0,
        'hashtags': '#LearnEnglish #English #EnglishLearning #Filipino',
    },
}

# PKCE用
_code_verifier: Optional[str] = None


# === トークン管理 ===
def load_tokens() -> dict:
    """トークンを読み込み"""
    if TOKENS_FILE.exists():
        with open(TOKENS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def save_tokens(tokens: dict):
    """トークンを保存"""
    with open(TOKENS_FILE, 'w', encoding='utf-8') as f:
        json.dump(tokens, f, indent=2, ensure_ascii=False)


def get_access_token(account: str = 'default') -> str:
    """アクセストークンを取得"""
    tokens = load_tokens()
    if account in tokens:
        return tokens[account].get('access_token', '')
    return ''


def refresh_access_token(account: str = 'default') -> bool:
    """トークンをリフレッシュ"""
    tokens = load_tokens()
    if account not in tokens:
        return False
    
    refresh_token = tokens[account].get('refresh_token', '')
    if not refresh_token:
        return False
    
    response = requests.post(f'{API_BASE}/oauth/token/', data={
        'client_key': TIKTOK_CLIENT_KEY,
        'client_secret': TIKTOK_CLIENT_SECRET,
        'grant_type': 'refresh_token',
        'refresh_token': refresh_token,
    })
    
    if response.status_code != 200:
        return False
    
    data = response.json()
    if 'access_token' not in data:
        return False
    
    tokens[account].update({
        'access_token': data['access_token'],
        'refresh_token': data.get('refresh_token', refresh_token),
        'refreshed_at': datetime.now().isoformat(),
    })
    save_tokens(tokens)
    return True


# === 履歴管理 ===
def load_history() -> dict:
    """アップロード履歴を読み込み"""
    if HISTORY_FILE.exists():
        with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {'uploads': []}


def save_history(history: dict):
    """アップロード履歴を保存"""
    with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(history, f, indent=2, ensure_ascii=False)


def add_to_history(account: str, video_path: str, success: bool, is_sandbox: bool = False):
    """履歴に追加"""
    history = load_history()
    history['uploads'].append({
        'account': account,
        'video': str(video_path),
        'uploaded_at': datetime.now().isoformat(),
        'success': success,
        'sandbox': is_sandbox,
    })
    save_history(history)


# === OAuth認証 ===
class OAuthHTTPServer(HTTPServer):
    """OAuth用のカスタムHTTPServer"""
    auth_code: Optional[str] = None
    error: Optional[str] = None


class CallbackHandler(BaseHTTPRequestHandler):
    """OAuth コールバックハンドラー"""
    server: OAuthHTTPServer
    
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == '/callback':
            params = urllib.parse.parse_qs(parsed.query)
            
            if 'code' in params:
                self.server.auth_code = params['code'][0]
                self.send_response(200)
                self.send_header('Content-type', 'text/html; charset=utf-8')
                self.end_headers()
                html = '''
                    <!DOCTYPE html>
                    <html><body style="font-family:Arial;text-align:center;padding:50px;background:#f0f0f0;">
                    <div style="background:white;padding:40px;border-radius:10px;max-width:400px;margin:auto;">
                    <h1 style="color:#25F4EE;">✅ 認証成功!</h1>
                    <p>SpeakCycleがTikTokと正常に連携されました</p>
                    <p style="color:#888;">このウィンドウを閉じてください</p>
                    </div>
                    </body></html>
                '''
                self.wfile.write(html.encode('utf-8'))
            else:
                self.server.auth_code = None
                self.server.error = params.get('error', ['unknown'])[0]
                self.send_response(400)
                self.send_header('Content-type', 'text/html; charset=utf-8')
                self.end_headers()
                html = f'''
                    <!DOCTYPE html>
                    <html><body style="font-family:Arial;text-align:center;padding:50px;">
                    <h1 style="color:#FE2C55;">❌ 認証エラー</h1>
                    <p>エラー: {self.server.error}</p>
                    </body></html>
                '''
                self.wfile.write(html.encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()
    
    def log_message(self, *args):
        pass  # ログ抑制


def generate_pkce() -> str:
    """PKCE用のcode_verifierとcode_challengeを生成"""
    global _code_verifier
    _code_verifier = secrets.token_urlsafe(64)[:128]
    digest = hashlib.sha256(_code_verifier.encode('ascii')).digest()
    code_challenge = base64.urlsafe_b64encode(digest).decode('ascii').rstrip('=')
    return code_challenge


def authenticate(account: str = 'default') -> bool:
    """TikTokアカウントを認証"""
    global _code_verifier
    
    if not TIKTOK_CLIENT_KEY or not TIKTOK_CLIENT_SECRET:
        print("❌ 環境変数を設定してください:")
        print("   TIKTOK_CLIENT_KEY")
        print("   TIKTOK_CLIENT_SECRET")
        return False
    
    print(f"\n🔐 TikTok認証開始 (アカウント: {account})")
    print("=" * 50)
    
    # PKCE生成
    code_challenge = generate_pkce()
    
    # 認証URL生成
    params = {
        'client_key': TIKTOK_CLIENT_KEY,
        'scope': SCOPES,
        'response_type': 'code',
        'redirect_uri': REDIRECT_URI,
        'state': account,
        'code_challenge': code_challenge,
        'code_challenge_method': 'S256',
    }
    auth_url = f"https://www.tiktok.com/v2/auth/authorize/?{urllib.parse.urlencode(params)}"
    
    print(f"\n📱 ブラウザでTikTokにログインしてください...")
    print(f"   Redirect URI: {REDIRECT_URI}")
    
    # ローカルサーバー起動
    try:
        server = OAuthHTTPServer(('localhost', 8080), CallbackHandler)
    except OSError as e:
        print(f"❌ ポート8080が使用中です: {e}")
        return False
    
    server.auth_code = None
    server.error = None
    
    # ブラウザで開く
    webbrowser.open(auth_url)
    
    # コールバック待ち
    print("⏳ 認証待機中...")
    server.handle_request()
    server.server_close()
    
    if not server.auth_code:
        print(f"❌ 認証失敗: {server.error}")
        return False
    
    # トークン取得
    print("🔄 アクセストークン取得中...")
    
    response = requests.post(f'{API_BASE}/oauth/token/', data={
        'client_key': TIKTOK_CLIENT_KEY,
        'client_secret': TIKTOK_CLIENT_SECRET,
        'code': server.auth_code,
        'grant_type': 'authorization_code',
        'redirect_uri': REDIRECT_URI,
        'code_verifier': _code_verifier,
    })
    
    if response.status_code != 200:
        print(f"❌ トークン取得失敗: {response.status_code}")
        print(f"   {response.text}")
        return False
    
    data = response.json()
    if 'access_token' not in data:
        print(f"❌ トークンが見つかりません: {data}")
        return False
    
    # トークン保存
    tokens = load_tokens()
    tokens[account] = {
        'access_token': data['access_token'],
        'refresh_token': data.get('refresh_token', ''),
        'expires_in': data.get('expires_in', 0),
        'open_id': data.get('open_id', ''),
        'scope': data.get('scope', ''),
        'authenticated_at': datetime.now().isoformat(),
    }
    save_tokens(tokens)
    
    print(f"\n✅ 認証成功!")
    print(f"   Open ID: {data.get('open_id', 'N/A')[:20]}...")
    print(f"   スコープ: {data.get('scope', 'N/A')}")
    
    return True


# === 動画アップロード ===
def get_user_info(access_token: str) -> dict:
    """ユーザー情報を取得"""
    response = requests.get(
        f"{API_BASE}/user/info/",
        headers={'Authorization': f'Bearer {access_token}'},
        params={'fields': 'open_id,display_name,avatar_url'}
    )
    
    if response.status_code == 200:
        return response.json().get('data', {}).get('user', {})
    return {}


def upload_video_direct(video_path: str, caption: str, access_token: str, 
                        privacy: str = 'SELF_ONLY', is_sandbox: bool = False) -> dict:
    """
    TikTokに動画をDirect Postでアップロード
    
    privacy levels:
    - SELF_ONLY: 自分のみ（Sandboxではこれのみ）
    - MUTUAL_FOLLOW_FRIENDS: 相互フォロー
    - FOLLOWER_OF_CREATOR: フォロワー
    - PUBLIC_TO_EVERYONE: 全員（本番のみ）
    """
    video_path = Path(video_path)
    if not video_path.exists():
        return {'success': False, 'error': 'Video file not found'}
    
    video_size = video_path.stat().st_size
    
    print(f"\n📤 アップロード開始")
    print(f"   ファイル: {video_path.name}")
    print(f"   サイズ: {video_size / 1024 / 1024:.2f} MB")
    print(f"   公開設定: {privacy}")
    if is_sandbox:
        print(f"   ⚠️ Sandboxモード（視聴数制限あり）")
    
    # Step 1: Initialize upload
    print("\n1️⃣ アップロード初期化...")
    
    init_payload = {
        'post_info': {
            'title': caption[:150],
            'privacy_level': privacy,
            'disable_duet': False,
            'disable_comment': False,
            'disable_stitch': False,
            'video_cover_timestamp_ms': 1000,
        },
        'source_info': {
            'source': 'FILE_UPLOAD',
            'video_size': video_size,
            'chunk_size': min(video_size, 10 * 1024 * 1024),  # Max 10MB per chunk
            'total_chunk_count': 1,
        }
    }
    
    init_response = requests.post(
        f"{API_BASE}/post/publish/video/init/",
        headers={
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        },
        json=init_payload
    )
    
    if init_response.status_code != 200:
        error_data = init_response.json() if init_response.text else {}
        return {
            'success': False,
            'error': f"Init failed: {init_response.status_code}",
            'details': error_data
        }
    
    init_data = init_response.json()
    
    if 'error' in init_data and init_data['error'].get('code') != 'ok':
        return {
            'success': False,
            'error': init_data['error'].get('message', 'Unknown error'),
            'details': init_data
        }
    
    upload_url = init_data.get('data', {}).get('upload_url')
    publish_id = init_data.get('data', {}).get('publish_id')
    
    if not upload_url:
        return {
            'success': False,
            'error': 'No upload URL received',
            'details': init_data
        }
    
    print(f"   Publish ID: {publish_id}")
    
    # Step 2: Upload video file
    print("\n2️⃣ 動画ファイルをアップロード中...")
    
    with open(video_path, 'rb') as f:
        video_data = f.read()
    
    upload_response = requests.put(
        upload_url,
        data=video_data,
        headers={
            'Content-Type': 'video/mp4',
            'Content-Range': f'bytes 0-{video_size - 1}/{video_size}'
        }
    )
    
    if upload_response.status_code not in [200, 201]:
        return {
            'success': False,
            'error': f"Upload failed: {upload_response.status_code}",
            'details': upload_response.text
        }
    
    print("   ✅ アップロード完了!")
    
    # Step 3: Check publish status
    print("\n3️⃣ 公開ステータスを確認中...")
    
    for i in range(10):  # 最大10回チェック
        status_response = requests.post(
            f"{API_BASE}/post/publish/status/fetch/",
            headers={
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            },
            json={'publish_id': publish_id}
        )
        
        if status_response.status_code == 200:
            status_data = status_response.json()
            publish_status = status_data.get('data', {}).get('status')
            
            if publish_status == 'PUBLISH_COMPLETE':
                print("   ✅ 公開完了!")
                return {
                    'success': True,
                    'publish_id': publish_id,
                    'status': publish_status
                }
            elif publish_status == 'FAILED':
                fail_reason = status_data.get('data', {}).get('fail_reason', 'Unknown')
                return {
                    'success': False,
                    'error': f'Publish failed: {fail_reason}',
                    'publish_id': publish_id
                }
            elif publish_status in ['PROCESSING_UPLOAD', 'PROCESSING_DOWNLOAD', 'SENDING_TO_USER_INBOX']:
                print(f"   ⏳ 処理中: {publish_status}")
                import time
                time.sleep(3)
                continue
        
        import time
        time.sleep(2)
    
    return {
        'success': True,  # 送信自体は成功
        'publish_id': publish_id,
        'status': 'PROCESSING',
        'note': 'Video is being processed by TikTok'
    }


def post_sandbox_video(video_path: str = None, caption: str = None) -> bool:
    """Sandboxモードで動画を投稿（デモ用）"""
    print("\n" + "=" * 60)
    print("🧪 TikTok SANDBOX MODE")
    print("=" * 60)
    
    access_token = get_access_token('default')
    if not access_token:
        print("❌ 認証が必要です: python tiktok_uploader.py --auth")
        return False
    
    # ユーザー情報取得
    user_info = get_user_info(access_token)
    if user_info:
        print(f"\n👤 アカウント: {user_info.get('display_name', 'Unknown')}")
    
    # 動画ファイル決定
    if video_path:
        video_file = Path(video_path)
    elif SAMPLE_VIDEO.exists():
        video_file = SAMPLE_VIDEO
    else:
        # videosフォルダから探す
        if VIDEOS_DIR.exists():
            videos = list(VIDEOS_DIR.glob('*.mp4'))
            if videos:
                video_file = videos[0]
            else:
                print("❌ 動画ファイルが見つかりません")
                print(f"   {VIDEOS_DIR} に.mp4ファイルを配置してください")
                return False
        else:
            print("❌ 動画ファイルが見つかりません")
            return False
    
    # キャプション
    if not caption:
        caption = "📚 Learn English with SpeakCycle! 🎯 #English #LearnEnglish #Education"
    
    # Sandboxではprivacyは SELF_ONLY のみ
    result = upload_video_direct(
        str(video_file),
        caption,
        access_token,
        privacy='SELF_ONLY',
        is_sandbox=True
    )
    
    add_to_history('default', str(video_file), result['success'], is_sandbox=True)
    
    if result['success']:
        print("\n" + "=" * 60)
        print("✅ SANDBOX投稿成功!")
        print("=" * 60)
        print(f"   Publish ID: {result.get('publish_id')}")
        print(f"   ステータス: {result.get('status')}")
        print("\n⚠️ 注意: Sandboxモードでは動画の視聴数が制限されます")
        print("   本番承認後は --post オプションで通常投稿できます")
        return True
    else:
        print("\n" + "=" * 60)
        print("❌ SANDBOX投稿失敗")
        print("=" * 60)
        print(f"   エラー: {result.get('error')}")
        if result.get('details'):
            print(f"   詳細: {result.get('details')}")
        return False


# === 状態表示 ===
def show_status():
    """システム状態を表示"""
    tokens = load_tokens()
    
    print("\n" + "=" * 60)
    print("📊 SpeakCycle TikTok Uploader 状態")
    print("=" * 60)
    
    # 認証状態
    print("\n🔐 認証状態:")
    if not tokens:
        print("   ❌ 未認証")
    else:
        for account, data in tokens.items():
            auth_time = data.get('authenticated_at', 'N/A')
            scope = data.get('scope', 'N/A')
            print(f"   ✅ {account}")
            print(f"      認証日時: {auth_time[:19] if auth_time != 'N/A' else 'N/A'}")
            print(f"      スコープ: {scope}")
    
    # 動画フォルダ状態
    print("\n📁 動画フォルダ:")
    if VIDEOS_DIR.exists():
        videos = list(VIDEOS_DIR.glob('*.mp4'))
        print(f"   📂 {VIDEOS_DIR}")
        print(f"   📹 {len(videos)} 件の動画")
    else:
        print(f"   ❌ {VIDEOS_DIR} が存在しません")
    
    # 履歴
    history = load_history()
    recent = history.get('uploads', [])[-5:]
    if recent:
        print("\n📜 最近のアップロード:")
        for item in reversed(recent):
            status = "✅" if item.get('success') else "❌"
            mode = "🧪" if item.get('sandbox') else "📤"
            print(f"   {status} {mode} {item.get('uploaded_at', '')[:16]} - {Path(item.get('video', '')).name}")


def show_help():
    """ヘルプを表示"""
    print("""
╔════════════════════════════════════════════════════════════╗
║           SpeakCycle TikTok Video Uploader                ║
╚════════════════════════════════════════════════════════════╝

📌 使用方法

1. 認証（初回のみ）:
   python tiktok_uploader.py --auth

2. Sandbox テスト投稿:
   python tiktok_uploader.py --post --sandbox

3. 状態確認:
   python tiktok_uploader.py --status

4. 本番投稿（承認後）:
   python tiktok_uploader.py --post --video path/to/video.mp4

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📋 セットアップ手順

1. .env ファイルを作成:
   TIKTOK_CLIENT_KEY=your_client_key
   TIKTOK_CLIENT_SECRET=your_client_secret
   TIKTOK_REDIRECT_URI=http://localhost:8080/callback

2. TikTok Developer Portalで設定:
   - Redirect URI: http://localhost:8080/callback
   - Products: Login Kit, Content Posting API
   - Scopes: user.info.basic, video.publish, video.upload

3. Sandboxモードでテスト → デモ動画撮影 → 本番申請

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
""")


# === メイン ===
def main():
    parser = argparse.ArgumentParser(
        description='SpeakCycle TikTok Video Uploader',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('--auth', action='store_true', help='TikTokアカウントを認証')
    parser.add_argument('--account', type=str, default='default', help='アカウント名')
    parser.add_argument('--post', action='store_true', help='動画を投稿')
    parser.add_argument('--sandbox', action='store_true', help='Sandboxモードで投稿')
    parser.add_argument('--video', type=str, help='動画ファイルパス')
    parser.add_argument('--caption', type=str, help='キャプション')
    parser.add_argument('--status', action='store_true', help='状態を表示')
    parser.add_argument('--refresh', action='store_true', help='トークンをリフレッシュ')
    
    args = parser.parse_args()
    
    # 認証
    if args.auth:
        authenticate(args.account)
        return
    
    # トークンリフレッシュ
    if args.refresh:
        if refresh_access_token(args.account):
            print("✅ トークンをリフレッシュしました")
        else:
            print("❌ リフレッシュ失敗")
        return
    
    # 状態表示
    if args.status:
        show_status()
        return
    
    # 投稿
    if args.post:
        if args.sandbox:
            post_sandbox_video(args.video, args.caption)
        else:
            if not args.video:
                print("❌ --video オプションで動画ファイルを指定してください")
                print("   またはSandboxモードを使用: --post --sandbox")
                return
            
            access_token = get_access_token(args.account)
            if not access_token:
                print("❌ 認証が必要です: python tiktok_uploader.py --auth")
                return
            
            caption = args.caption or "📚 Learn English! #English #LearnEnglish"
            result = upload_video_direct(args.video, caption, access_token, 'PUBLIC_TO_EVERYONE')
            
            if result['success']:
                print("\n✅ 投稿成功!")
            else:
                print(f"\n❌ 投稿失敗: {result.get('error')}")
        return
    
    # ヘルプ
    show_help()
    parser.print_help()


if __name__ == "__main__":
    main()
