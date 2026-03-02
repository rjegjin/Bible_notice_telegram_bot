import os
import sys
import json
import requests
from pathlib import Path
from dotenv import load_dotenv

# 프로젝트 루트 경로 설정
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

def load_env_centralized():
    central_secrets = Path("/home/rjegj/projects/.secrets/.env")
    if central_secrets.exists():
        load_dotenv(central_secrets)
        return True
    return False

def check_telegram_ids():
    load_env_centralized()
    token = os.getenv('TELEGRAM_TOKEN')
    
    if not token:
        print("❌ 오류: TELEGRAM_TOKEN을 찾을 수 없습니다. /.secrets/.env 설정을 확인하세요.")
        return

    url = f"https://api.telegram.org/bot{token}/getUpdates?offset=-10"
    
    try:
        response = requests.get(url)
        data = response.json()
        
        if not data.get('ok'):
            print(f"❌ API 오류: {data.get('description')}")
            return

        results = data.get('result', [])
        if not results:
            print("\nℹ️ 최근 메시지 기록이 없습니다.")
            print("👉 봇(@Daily_bible_reading_2026bot)에게 메시지를 보내거나,")
            print("👉 봇이 있는 단체방에서 아무 메시지나 보낸 후 다시 실행해주세요.")
            return

        print("\n🔍 최근 발견된 채팅방 정보:")
        print("-" * 50)
        seen = set()
        for update in results:
            # 메시지 타입 추출
            msg = update.get('message') or update.get('my_chat_member') or \
                  update.get('channel_post') or update.get('edited_message')
            
            if not msg: continue
            
            chat = msg.get('chat')
            if chat and chat['id'] not in seen:
                chat_id = chat['id']
                chat_type = chat.get('type', 'unknown')
                name = chat.get('title') or chat.get('first_name', 'Unknown')
                
                print(f"✅ ID  : {chat_id}")
                print(f"   이름: {name}")
                print(f"   타입: {chat_type}")
                print("-" * 50)
                seen.add(chat_id)
                
    except Exception as e:
        print(f"❌ 네트워크 오류: {e}")

if __name__ == "__main__":
    check_telegram_ids()
