import sys
import os
import json
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/drive.file"
]

def main():
    print("=" * 60)
    print(" Google Drive OAuth 2.0 Token Generator")
    print("=" * 60)
    print("Vui lòng nhập Client ID và Client Secret từ Google Cloud Console:")
    print("(Loại: OAuth 2.0 Client ID -> Application type: Desktop app)\n")
    
    client_id = input("Client ID: ").strip()
    client_secret = input("Client Secret: ").strip()
    
    if not client_id or not client_secret:
        print("❌ Lỗi: Client ID và Client Secret không được để trống!")
        return

    client_config = {
        "installed": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": ["urn:ietf:wg:oauth:2.0:oob", "http://localhost"]
        }
    }

    flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
    
    # Generate auth url
    auth_url, _ = flow.authorization_url(
        access_type="offline",
        prompt="consent",
        include_granted_scopes="true"
    )
    
    print("\n" + "=" * 60)
    print("1. Mở đường link sau trong trình duyệt của bạn:")
    print("=" * 60)
    print(auth_url)
    print("=" * 60)
    print("\n2. Đăng nhập tài khoản Google của bạn và bấm 'Cho phép (Allow)'.")
    print("3. Copy mã Authorization Code hoặc URL trả về và dán vào đây:\n")
    
    code = input("Nhập mã Code / URL: ").strip()
    if not code:
        print("❌ Không có mã code được nhập.")
        return
        
    if "code=" in code:
        # User pasted full redirect url
        code = code.split("code=")[1].split("&")[0]

    try:
        flow.fetch_token(code=code)
        credentials = flow.credentials
        refresh_token = credentials.refresh_token
        
        print("\n" + "🎉" * 20)
        print(" LẤY TOKEN THÀNH CÔNG!")
        print("=" * 60)
        print(f"GDRIVE_CLIENT_ID:      {client_id}")
        print(f"GDRIVE_CLIENT_SECRET: {client_secret}")
        print(f"GDRIVE_REFRESH_TOKEN: {refresh_token}")
        print("=" * 60)
        
        # Save to local configs (ignored by git)
        configs_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "configs")
        os.makedirs(configs_dir, exist_ok=True)
        out_file = os.path.join(configs_dir, "oauth_credentials.json")
        with open(out_file, "w") as f:
            json.dump({
                "client_id": client_id,
                "client_secret": client_secret,
                "refresh_token": refresh_token
            }, f, indent=2)
            
        print(f" Đã lưu file cấu hình cục bộ tại: {out_file}")
        print(" Bạn hãy copy 3 giá trị trên vào GitHub Secrets:")
        print("  - GDRIVE_CLIENT_ID")
        print("  - GDRIVE_CLIENT_SECRET")
        print("  - GDRIVE_REFRESH_TOKEN")
        print("=" * 60)
    except Exception as e:
        print(f"❌ Lỗi khi đổi token: {e}")

if __name__ == "__main__":
    main()
