import io
import os
import sys
from pathlib import Path

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
import PIL.Image

DRIVE_FOLDER_ID = "1VEAWTFsr-LkdiyBtI6Nx2FmEOTFEOvfm"
SERVICE_KEY_PATH = "/home/rjegj/projects/.secrets/service_key.json"
SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]


def _get_drive_service():
    creds = Credentials.from_service_account_file(SERVICE_KEY_PATH, scopes=SCOPES)
    return build("drive", "v3", credentials=creds)


def _find_file(service, year_str, month_str, prefix):
    """폴더 안에서 연월+접두어로 파일 검색 (확장자 무관)"""
    name_fragment = f"{year_str}년_{month_str}월_{prefix}_passage"
    query = (
        f"'{DRIVE_FOLDER_ID}' in parents "
        f"and name contains '{name_fragment}' "
        f"and trashed=false"
    )
    result = service.files().list(q=query, fields="files(id, name)").execute()
    files = result.get("files", [])
    return files[0] if files else None


def _download_as_pil(service, file_id):
    """Drive 파일 ID → PIL.Image (메모리 내 처리, 임시 파일 없음)"""
    request = service.files().get_media(fileId=file_id)
    buf = io.BytesIO()
    downloader = MediaIoBaseDownload(buf, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()
    buf.seek(0)
    return PIL.Image.open(buf).copy()  # .copy()로 스트림 닫혀도 안전


def fetch_images_from_drive(year, month):
    """
    Google Drive 폴더에서 해당 월의 BR/QT 이미지를 찾아 반환.

    Returns:
        images (dict): {"BR": PIL.Image, "QT": PIL.Image}  (없으면 키 자체가 없음)
        found (list): ["BR", "QT"] 중 발견된 항목
    """
    year_str = str(year)
    month_str = str(month).zfill(2)

    try:
        service = _get_drive_service()
    except Exception as e:
        print(f"Drive 서비스 연결 실패: {e}")
        return {}, []

    images = {}
    found = []

    for prefix in ["BR", "QT"]:
        meta = _find_file(service, year_str, month_str, prefix)
        if meta:
            print(f"Drive에서 발견: {meta['name']} — 다운로드 중...")
            try:
                img = _download_as_pil(service, meta["id"])
                images[prefix] = img
                found.append(prefix)
            except Exception as e:
                print(f"{prefix} 이미지 다운로드 실패: {e}")
        else:
            print(f"Drive에 {year_str}년_{month_str}월_{prefix}_passage 파일 없음")

    return images, found
