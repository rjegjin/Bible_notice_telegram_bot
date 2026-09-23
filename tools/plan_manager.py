"""월별 성경 plan을 안전하게 조회·수정·검증·배포하는 CLI/TUI."""

from __future__ import annotations

import argparse
import copy
import difflib
import json
import logging
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable
from zoneinfo import ZoneInfo

from PIL import Image, UnidentifiedImageError
from tools.quiet_time_docs import upsert_quiet_time_tab

from tools.plan_parser import (
    generate_monthly_plan,
    is_hwpx_parsing_enabled,
    set_hwpx_parsing_enabled,
    validate_monthly_plan,
)


BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_PLANS_DIR = BASE_DIR / "data" / "plans"
DEFAULT_STANDBY_DIR = DEFAULT_PLANS_DIR / "standby"
DEFAULT_ASSETS_DIR = BASE_DIR / "assets"
FIELD_INDEX = {
    "nt": 0,
    "ot": 1,
    "psalms": 2,
    "proverbs": 3,
    "qt": 4,
}
FIELD_LABELS = {
    "nt": "신약",
    "ot": "구약",
    "psalms": "시편",
    "proverbs": "잠언",
    "qt": "QT",
}


@dataclass(frozen=True)
class SaveResult:
    path: Path
    backup_path: Path | None
    diff: str


@dataclass(frozen=True)
class PublishResult:
    path: Path
    backup_path: Path | None
    diff: str
    changed: bool
    test_sent: bool


def import_plan_images(
    year: int,
    month: int,
    *,
    br_path: Path | str | None = None,
    qt_path: Path | str | None = None,
    assets_dir: Path | str = DEFAULT_ASSETS_DIR,
    replace: bool = False,
) -> dict[str, Path]:
    """임의 파일명의 BR/QT 이미지를 검사하고 표준 asset 이름으로 가져온다."""
    if br_path is None and qt_path is None:
        raise ValueError("BR 또는 QT 이미지 경로를 하나 이상 지정해야 합니다.")

    year = int(year)
    month = int(month)
    if not 1 <= month <= 12:
        raise ValueError(f"월은 1~12여야 합니다: {month}")

    assets_dir = Path(assets_dir)
    assets_dir.mkdir(parents=True, exist_ok=True)
    imported = {}

    for kind, raw_path in (("BR", br_path), ("QT", qt_path)):
        if raw_path is None:
            continue
        source = Path(raw_path).expanduser().resolve()
        if not source.is_file():
            raise FileNotFoundError(f"{kind} 이미지가 없습니다: {source}")
        suffix = source.suffix.lower()
        if suffix not in {".png", ".jpg", ".jpeg"}:
            raise ValueError(f"{kind}는 PNG/JPG/JPEG 이미지만 지원합니다: {source.name}")
        try:
            with Image.open(source) as image:
                image.verify()
        except (UnidentifiedImageError, OSError) as error:
            raise ValueError(f"{kind} 파일이 유효한 이미지가 아닙니다: {source}") from error

        stem = f"{year:04d}년_{month:02d}월_{kind}_passage"
        destination = assets_dir / f"{stem}{suffix}"
        existing = [
            assets_dir / f"{stem}{extension}"
            for extension in (".png", ".jpg", ".jpeg")
            if (assets_dir / f"{stem}{extension}").exists()
        ]
        if source == destination.resolve():
            imported[kind] = destination
            continue
        if existing and not replace:
            names = ", ".join(path.name for path in existing)
            raise FileExistsError(
                f"{kind} asset이 이미 있습니다: {names} (--replace로 교체)"
            )

        with tempfile.NamedTemporaryFile(
            dir=assets_dir,
            prefix=f".{stem}.",
            suffix=suffix,
            delete=False,
        ) as temporary:
            temporary_path = Path(temporary.name)
        try:
            shutil.copy2(source, temporary_path)
            os.replace(temporary_path, destination)
        finally:
            temporary_path.unlink(missing_ok=True)
        for old_path in existing:
            if old_path != destination:
                old_path.unlink()
        imported[kind] = destination

    return imported


def stage_plan_image(
    year: int,
    month: int,
    kind: str,
    image_path: Path | str,
    *,
    assets_dir: Path | str = DEFAULT_ASSETS_DIR,
    standby_dir: Path | str = DEFAULT_STANDBY_DIR,
) -> Path | None:
    """한 종류의 asset을 저장하고 BR/QT가 모두 모이면 검증된 standby JSON을 만든다."""
    kind = kind.upper()
    if kind not in {"BR", "QT"}:
        raise ValueError(f"종류는 BR 또는 QT여야 합니다: {kind}")
    import_plan_images(
        year,
        month,
        br_path=image_path if kind == "BR" else None,
        qt_path=image_path if kind == "QT" else None,
        assets_dir=assets_dir,
        replace=True,
    )
    assets_dir = Path(assets_dir)
    stem = f"{int(year):04d}년_{int(month):02d}월"
    if not all(any(assets_dir.glob(f"{stem}_{required}_passage.*")) for required in ("BR", "QT")):
        return None
    standby_dir = Path(standby_dir)
    plan = generate_monthly_plan(int(year), int(month), output_dir=standby_dir)
    if plan is None:
        raise RuntimeError("OCR 또는 월 전체 validation에 실패했습니다.")
    return standby_dir / f"{int(year):04d}_{int(month):02d}.json"


class PlanManager:
    def __init__(
        self,
        plans_dir: Path | str = DEFAULT_PLANS_DIR,
        validator: Callable[[dict, int, int], None] = validate_monthly_plan,
    ):
        self.plans_dir = Path(plans_dir)
        self.validator = validator

    def plan_path(self, year: int, month: int) -> Path:
        year = int(year)
        month = int(month)
        if not 1 <= month <= 12:
            raise ValueError(f"월은 1~12여야 합니다: {month}")
        return self.plans_dir / f"{year:04d}_{month:02d}.json"

    def list_months(self) -> list[tuple[int, int]]:
        if not self.plans_dir.exists():
            return []
        months = []
        for path in self.plans_dir.iterdir():
            match = re.fullmatch(r"(\d{4})_(\d{2})\.json", path.name)
            if match:
                months.append((int(match.group(1)), int(match.group(2))))
        return sorted(months)

    def load(self, year: int, month: int) -> dict:
        path = self.plan_path(year, month)
        if not path.exists():
            raise FileNotFoundError(f"월별 plan이 없습니다: {path}")
        with path.open(encoding="utf-8") as file:
            plan = json.load(file)
        if not isinstance(plan, dict):
            raise ValueError(f"plan 최상위 값은 object여야 합니다: {path}")
        return plan

    @staticmethod
    def _serialize(plan: dict) -> str:
        return json.dumps(plan, ensure_ascii=False, indent=4) + "\n"

    def validate(self, year: int, month: int, plan: dict | None = None) -> dict:
        target = plan if plan is not None else self.load(year, month)
        self.validator(target, int(year), int(month))
        return target

    def create_backup(self, year: int, month: int) -> Path | None:
        path = self.plan_path(year, month)
        if not path.exists():
            return None
        backup_dir = self.plans_dir / "backups"
        backup_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(ZoneInfo("Asia/Seoul")).strftime("%Y%m%d_%H%M%S_%f")
        backup_path = backup_dir / f"{path.stem}_{timestamp}.json"
        shutil.copy2(path, backup_path)
        return backup_path

    def save(self, year: int, month: int, plan: dict) -> SaveResult:
        year = int(year)
        month = int(month)
        self.validate(year, month, plan)

        path = self.plan_path(year, month)
        old_text = path.read_text(encoding="utf-8") if path.exists() else ""
        new_text = self._serialize(plan)
        diff = "".join(
            difflib.unified_diff(
                old_text.splitlines(keepends=True),
                new_text.splitlines(keepends=True),
                fromfile=f"{path.name} (before)",
                tofile=f"{path.name} (after)",
            )
        )
        if old_text == new_text:
            return SaveResult(path=path, backup_path=None, diff="")

        backup_path = self.create_backup(year, month)
        self.plans_dir.mkdir(parents=True, exist_ok=True)
        temp_name = None
        try:
            with tempfile.NamedTemporaryFile(
                "w",
                encoding="utf-8",
                dir=self.plans_dir,
                prefix=f".{path.stem}.",
                suffix=".tmp",
                delete=False,
            ) as temp_file:
                temp_file.write(new_text)
                temp_file.flush()
                os.fsync(temp_file.fileno())
                temp_name = temp_file.name
            os.replace(temp_name, path)
        finally:
            if temp_name and os.path.exists(temp_name):
                os.unlink(temp_name)

        return SaveResult(path=path, backup_path=backup_path, diff=diff)

    def update_day(
        self,
        year: int,
        month: int,
        day: int,
        updates: dict[str, str],
    ) -> SaveResult:
        unknown = sorted(set(updates) - set(FIELD_INDEX))
        if unknown:
            raise ValueError(f"지원하지 않는 필드: {', '.join(unknown)}")
        if not updates:
            raise ValueError("수정할 필드가 없습니다.")

        plan = copy.deepcopy(self.load(year, month))
        day_key = str(int(day))
        if day_key not in plan:
            raise ValueError(f"{year}년 {month}월에 {day}일이 없습니다.")
        row = plan[day_key]
        if not isinstance(row, list) or len(row) != 5:
            raise ValueError(f"{day}일 데이터가 5열 형식이 아닙니다.")

        for field, value in updates.items():
            row[FIELD_INDEX[field]] = str(value).strip()
        return self.save(year, month, plan)

    def render(self, year: int, month: int, day: int | None = None) -> str:
        plan = self.load(year, month)
        days = [str(int(day))] if day is not None else sorted(plan, key=int)
        lines = [f"=== {int(year)}년 {int(month):02d}월 말씀 plan ==="]
        for day_key in days:
            if day_key not in plan:
                raise ValueError(f"{day_key}일 데이터가 없습니다.")
            nt, ot, psalms, proverbs, qt = (plan[day_key] + [""] * 5)[:5]
            lines.append(
                f"{int(day_key):2d}일 | 신약 {nt or '-'} | 구약 {ot or '-'} | "
                f"시편 {psalms or '-'} | 잠언 {proverbs or '-'} | QT {qt or '-'}"
            )
        return "\n".join(lines)


def preview_day(manager: PlanManager, year: int, month: int, day: int, lang: str) -> str:
    from core.bible_sender import format_summary

    plan = manager.load(year, month)
    day_key = str(int(day))
    if day_key not in plan:
        raise ValueError(f"{day}일 데이터가 없습니다.")
    date_display = f"{int(year):04d}/{int(month):02d}/{int(day):02d}"
    languages = ("KO", "EN", "MN") if lang == "ALL" else (lang,)
    return "\n\n".join(
        format_summary(plan[day_key], language, date_display)
        for language in languages
    )


def deploy_plan(
    manager: PlanManager,
    year: int,
    month: int,
    host: str,
    remote_project: str,
) -> None:
    manager.validate(year, month)
    path = manager.plan_path(year, month)
    remote_path = f"{remote_project.rstrip('/')}/data/plans/{path.name}"
    subprocess.run(["rsync", "-av", str(path), f"{host}:{remote_path}"], check=True)

    remote_check = (
        f"cd {shlex.quote(remote_project)} && "
        f"/home/mh_bot/projects/unified_venv/bin/python -c "
        f"'import json; from tools.plan_parser import validate_monthly_plan; "
        f"p=json.load(open(\"data/plans/{path.name}\", encoding=\"utf-8\")); "
        f"validate_monthly_plan(p,{int(year)},{int(month)}); "
        f"print(\"remote validation: OK\")'"
    )
    subprocess.run(["ssh", host, remote_check], check=True)


def send_publish_test(
    manager: PlanManager,
    year: int,
    month: int,
    day: int | None = None,
) -> None:
    """운영 호스트에서 owner 개인방으로 publish 결과 1건을 시험 발송한다."""
    from common.bot_common import send_telegram
    from core.recipient_config import resolve_owner_recipient

    now = datetime.now(ZoneInfo("Asia/Seoul"))
    if day is None:
        day = now.day if (now.year, now.month) == (int(year), int(month)) else 1
    plan = manager.load(year, month)
    day_key = str(int(day))
    if day_key not in plan:
        raise ValueError(f"publish test 대상 {day}일 데이터가 없습니다.")
    nt, ot, psalms, proverbs, qt = (plan[day_key] + [""] * 5)[:5]

    lines = [
        "✅ MydailyBibleBot 말씀 plan publish 테스트",
        f"대상: {int(year)}년 {int(month):02d}월 {int(day)}일",
        f"신약: {nt or '-'}",
        f"구약: {ot or '-'}",
        f"시편: {psalms or '-'}",
    ]
    if proverbs:
        lines.append(f"잠언: {proverbs}")
    lines.append(f"QT: {qt or '-'}")

    token = os.getenv("TELEGRAM_TOKEN")
    if not token:
        raise RuntimeError("TELEGRAM_TOKEN이 없어 publish test를 보낼 수 없습니다.")
    recipient, source = resolve_owner_recipient()
    logging.getLogger("httpx").setLevel(logging.WARNING)
    send_telegram(
        "\n".join(lines),
        token=token,
        chat_id=recipient,
        parse_mode=None,
    )
    print(f"✅ owner Telegram publish test 전송 완료 ({source})")


def notify_remote_owner(
    host: str,
    remote_project: str,
    year: int,
    month: int,
) -> None:
    command = (
        f"cd {shlex.quote(remote_project)} && "
        f"/home/mh_bot/projects/unified_venv/bin/python main.py plan notify "
        f"{int(year)} {int(month)}"
    )
    subprocess.run(["ssh", host, command], check=True)


def publish_plan(
    manager: PlanManager,
    year: int,
    month: int,
    host: str,
    remote_project: str,
    send_test: bool = True,
    *,
    generator: Callable[[int, int], dict | None] = generate_monthly_plan,
    deployer: Callable[..., None] = deploy_plan,
    notifier: Callable[..., None] = notify_remote_owner,
    create_sheet: bool = True,
    sheet_writer: Callable[..., str] | None = None,
    standby_dir: Path | str = DEFAULT_STANDBY_DIR,
) -> PublishResult:
    """standby 승격(없으면 OCR) → Docs readback → 배포 → owner test."""
    year = int(year)
    month = int(month)
    path = manager.plan_path(year, month)
    had_original = path.exists()
    before_text = path.read_text(encoding="utf-8") if had_original else ""
    backup_path = manager.create_backup(year, month)

    try:
        standby_path = Path(standby_dir) / f"{year:04d}_{month:02d}.json"
        if standby_path.exists():
            after_plan = json.loads(standby_path.read_text(encoding="utf-8"))
            manager.validate(year, month, after_plan)
            path.parent.mkdir(parents=True, exist_ok=True)
            temporary = path.with_suffix(".json.tmp")
            temporary.write_text(manager._serialize(after_plan), encoding="utf-8")
            temporary.replace(path)
        else:
            generated = generator(year, month)
            if generated is None:
                raise RuntimeError("standby가 없고 asset 재파싱도 실패했습니다.")
        after_plan = manager.load(year, month)
        manager.validate(year, month, after_plan)
    except Exception:
        if backup_path is not None:
            shutil.copy2(backup_path, path)
        elif not had_original and path.exists():
            path.unlink()
        raise

    after_text = path.read_text(encoding="utf-8")
    diff = "".join(
        difflib.unified_diff(
            before_text.splitlines(keepends=True),
            after_text.splitlines(keepends=True),
            fromfile=f"{path.name} (before)",
            tofile=f"{path.name} (standby approved)",
        )
    )
    if create_sheet:
        url = (sheet_writer or upsert_quiet_time_tab)(after_plan, year, month)
        print(f"📄 Quiet Time 적용 시트: {url}")
    deployer(manager, year, month, host, remote_project)
    if send_test:
        notifier(host, remote_project, year, month)
    return PublishResult(
        path=path,
        backup_path=backup_path,
        diff=diff,
        changed=before_text != after_text,
        test_sent=send_test,
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python main.py plan",
        description="📅 월별 말씀 JSON 조회·수정·검증·배포",
    )
    commands = parser.add_subparsers(dest="plan_command")

    commands.add_parser("list", help="보유한 월별 plan 목록")

    show = commands.add_parser("show", help="월 전체 또는 특정 날짜 조회")
    show.add_argument("year", type=int)
    show.add_argument("month", type=int)
    show.add_argument("--day", type=int)

    validate = commands.add_parser("validate", help="월별 plan 검증")
    validate.add_argument("year", type=int)
    validate.add_argument("month", type=int)

    edit = commands.add_parser("edit", help="특정 날짜 필드 수정")
    edit.add_argument("year", type=int)
    edit.add_argument("month", type=int)
    edit.add_argument("day", type=int)
    edit.add_argument("--yes", action="store_true", help="diff 확인 질문을 생략하고 저장")
    for field, label in FIELD_LABELS.items():
        edit.add_argument(f"--{field}", help=f"{label} 값 (빈 문자열로 공란 지정 가능)")

    preview = commands.add_parser("preview", help="Telegram 발송 없이 요약 미리보기")
    preview.add_argument("year", type=int)
    preview.add_argument("month", type=int)
    preview.add_argument("day", type=int)
    preview.add_argument("--lang", choices=("ALL", "KO", "EN", "MN"), default="ALL")

    import_images = commands.add_parser(
        "import-images",
        help="임의 이름의 BR/QT 이미지를 검사하고 표준 이름으로 assets에 가져오기",
    )
    import_images.add_argument("year", type=int)
    import_images.add_argument("month", type=int)
    import_images.add_argument("--br", help="BR 이미지 경로")
    import_images.add_argument("--qt", help="QT 이미지 경로")
    import_images.add_argument(
        "--replace",
        action="store_true",
        help="같은 연월·종류의 기존 asset 교체",
    )

    stage_image = commands.add_parser("stage-image", help="caption 이미지 저장 후 standby JSON 생성")
    stage_image.add_argument("year", type=int)
    stage_image.add_argument("month", type=int)
    stage_image.add_argument("kind", choices=("BR", "QT"))
    stage_image.add_argument("image")

    classify = commands.add_parser("classify", help="이미지가 BR인지 QT인지 판별해 출력")
    classify.add_argument("image")

    reparse = commands.add_parser("reparse", help="backup 후 이미지/OCR로 월 plan 재생성")
    reparse.add_argument("year", type=int)
    reparse.add_argument("month", type=int)
    reparse.add_argument("--yes", action="store_true", help="확인 질문 생략")

    deploy = commands.add_parser("deploy", help="검증 후 운영 mh_bot에 반영")
    deploy.add_argument("year", type=int)
    deploy.add_argument("month", type=int)
    deploy.add_argument("--host", default="mh_bot@100.103.20.9")
    deploy.add_argument(
        "--remote-project",
        default="/home/mh_bot/projects/Bible_notice_telegram_bot",
    )
    deploy.add_argument("--yes", action="store_true", help="확인 질문 생략")

    publish = commands.add_parser(
        "publish",
        help="asset 재파싱 → 검증 → QT Docs 탭 → mh_bot 배포 → owner Telegram test",
    )
    publish.add_argument("year", type=int)
    publish.add_argument("month", type=int)
    publish.add_argument("--host", default="mh_bot@100.103.20.9")
    publish.add_argument(
        "--remote-project",
        default="/home/mh_bot/projects/Bible_notice_telegram_bot",
    )
    publish.add_argument("--no-test", action="store_true", help="Telegram test만 생략")
    publish.add_argument("--no-sheet", action="store_true", help="긴급 시 Google Docs 단계만 생략")
    publish.add_argument("--yes", action="store_true", help="확인 질문 생략")

    sheet = commands.add_parser("sheet", help="검증된 plan으로 기존 문서의 월별 QT 탭 갱신")
    sheet.add_argument("year", type=int)
    sheet.add_argument("month", type=int)
    notify = commands.add_parser("notify", help="owner 개인방에 publish test 1건 발송")
    notify.add_argument("year", type=int)
    notify.add_argument("month", type=int)
    notify.add_argument("--day", type=int)
    return parser


def _confirm(prompt: str) -> bool:
    return input(f"{prompt} [y/N]: ").strip().lower() in {"y", "yes"}


def _interactive_edit(manager: PlanManager, year: int, month: int) -> None:
    day = int(input("수정할 날짜: ").strip())
    plan = manager.load(year, month)
    row = plan[str(day)]
    print(manager.render(year, month, day))
    updates = {}
    for field, index in FIELD_INDEX.items():
        label = FIELD_LABELS[field]
        value = input(f"{label} [{row[index]}] (Enter=유지, '-'=공란): ")
        if value == "":
            continue
        updates[field] = "" if value == "-" else value
    if not updates:
        print("변경 없음")
        return

    proposed = copy.deepcopy(plan)
    for field, value in updates.items():
        proposed[str(day)][FIELD_INDEX[field]] = value.strip()
    manager.validate(year, month, proposed)
    old_text = manager._serialize(plan)
    new_text = manager._serialize(proposed)
    print(
        "".join(
            difflib.unified_diff(
                old_text.splitlines(keepends=True),
                new_text.splitlines(keepends=True),
                fromfile="before",
                tofile="after",
            )
        )
    )
    if _confirm("backup 후 저장할까요?"):
        result = manager.save(year, month, proposed)
        print(f"✅ 저장: {result.path}")
        print(f"🛟 backup: {result.backup_path}")


def interactive(manager: PlanManager) -> int:
    now = datetime.now(ZoneInfo("Asia/Seoul"))
    year = int(input(f"연도 [{now.year}]: ").strip() or now.year)
    month = int(input(f"월 [{now.month}]: ").strip() or now.month)

    while True:
        print(
            "\n=== 📅 말씀 plan 관리자 ===\n"
            f"대상: {year}년 {month:02d}월\n"
            "1. 월 전체 보기\n"
            "2. 날짜 수정\n"
            "3. 검증\n"
            "4. 발송 없는 미리보기\n"
            "5. asset 재파싱 → QT Docs 탭 → 운영 반영 → Telegram test\n"
            "6. 이미지 가져오기 (파일명 자동 정리)\n"
            "7. OCR 재생성만\n"
            f"8. HWPX parsing toggle [현재 {'ON' if is_hwpx_parsing_enabled() else 'OFF'}]\n"
            "9. 운영 서버 반영만\n"
            "10. 월 변경\n"
            "0. 종료"
        )
        choice = input("선택: ").strip()
        try:
            if choice == "1":
                print(manager.render(year, month))
            elif choice == "2":
                _interactive_edit(manager, year, month)
            elif choice == "3":
                manager.validate(year, month)
                print("✅ 검증 통과")
            elif choice == "4":
                day = int(input("미리볼 날짜: ").strip())
                print(preview_day(manager, year, month, day, "ALL"))
            elif choice == "5":
                if _confirm("asset을 재파싱해 JSON 교체·QT Docs 탭·운영 배포·owner test할까요?"):
                    result = publish_plan(
                        manager,
                        year,
                        month,
                        "mh_bot@100.103.20.9",
                        "/home/mh_bot/projects/Bible_notice_telegram_bot",
                    )
                    print(result.diff or "내용 변경 없음")
                    print(f"✅ publish 완료 (backup: {result.backup_path})")
            elif choice == "6":
                br_path = input("BR 이미지 경로 (없으면 Enter): ").strip() or None
                qt_path = input("QT 이미지 경로 (없으면 Enter): ").strip() or None
                replace = _confirm("같은 달의 기존 이미지를 교체해도 될까요?")
                imported = import_plan_images(
                    year,
                    month,
                    br_path=br_path,
                    qt_path=qt_path,
                    replace=replace,
                )
                for kind, path in imported.items():
                    print(f"✅ {kind}: {path}")
                print("ℹ️ 검토 후 5번 publish를 실행하면 JSON 생성·배포·test가 진행됩니다.")
            elif choice == "7":
                if _confirm("현재 파일을 backup하고 OCR로 다시 생성할까요?"):
                    backup = manager.create_backup(year, month)
                    generated = generate_monthly_plan(year, month)
                    if generated is None:
                        raise RuntimeError("OCR 재생성 실패")
                    manager.validate(year, month)
                    print(f"✅ 재생성·검증 완료 (backup: {backup})")
            elif choice == "8":
                enabled = not is_hwpx_parsing_enabled()
                set_hwpx_parsing_enabled(enabled)
                print(f"⚙️ HWPX parsing: {'ON' if enabled else 'OFF'}")
            elif choice == "9":
                if _confirm("검증 후 운영 mh_bot에 반영할까요?"):
                    deploy_plan(
                        manager,
                        year,
                        month,
                        "mh_bot@100.103.20.9",
                        "/home/mh_bot/projects/Bible_notice_telegram_bot",
                    )
            elif choice == "10":
                year = int(input("연도: ").strip())
                month = int(input("월: ").strip())
            elif choice == "0":
                return 0
            else:
                print("지원하지 않는 선택입니다.")
        except (FileNotFoundError, ValueError, subprocess.CalledProcessError) as error:
            print(f"❌ {error}")


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    manager = PlanManager()

    if args.plan_command is None:
        if sys.stdin.isatty():
            return interactive(manager)
        parser.print_help()
        return 0

    try:
        if args.plan_command == "list":
            months = manager.list_months()
            print("\n".join(f"{year:04d}_{month:02d}" for year, month in months))
        elif args.plan_command == "show":
            print(manager.render(args.year, args.month, args.day))
        elif args.plan_command == "validate":
            manager.validate(args.year, args.month)
            print(f"✅ {args.year}_{args.month:02d}.json 검증 통과")
        elif args.plan_command == "edit":
            updates = {
                field: getattr(args, field)
                for field in FIELD_INDEX
                if getattr(args, field) is not None
            }
            before = manager.load(args.year, args.month)
            proposed = copy.deepcopy(before)
            day_key = str(args.day)
            if day_key not in proposed:
                raise ValueError(f"{args.day}일 데이터가 없습니다.")
            for field, value in updates.items():
                proposed[day_key][FIELD_INDEX[field]] = value.strip()
            manager.validate(args.year, args.month, proposed)
            old_text = manager._serialize(before)
            new_text = manager._serialize(proposed)
            diff = "".join(
                difflib.unified_diff(
                    old_text.splitlines(keepends=True),
                    new_text.splitlines(keepends=True),
                    fromfile="before",
                    tofile="after",
                )
            )
            print(diff or "변경 없음")
            should_save = args.yes or (sys.stdin.isatty() and _confirm("backup 후 저장할까요?"))
            if diff and should_save:
                result = manager.save(args.year, args.month, proposed)
                print(f"✅ 저장: {result.path}")
                print(f"🛟 backup: {result.backup_path}")
            elif diff:
                print("ℹ️ 저장하지 않았습니다. 저장하려면 --yes를 추가하세요.")
        elif args.plan_command == "preview":
            print(preview_day(manager, args.year, args.month, args.day, args.lang))
        elif args.plan_command == "import-images":
            imported = import_plan_images(
                args.year,
                args.month,
                br_path=args.br,
                qt_path=args.qt,
                replace=args.replace,
            )
            for kind, path in imported.items():
                print(f"✅ {kind}: {path}")
            print(
                f"다음 단계: python main.py plan publish "
                f"{args.year} {args.month}"
            )
        elif args.plan_command == "stage-image":
            path = stage_plan_image(args.year, args.month, args.kind, args.image)
            if path:
                print(f"✅ standby 생성: {path.name}\n검토 후 plan publish로 반영하세요.")
            else:
                waiting = "QT" if args.kind == "BR" else "BR"
                print(f"⏳ {args.kind} 저장 완료 · {waiting} 이미지 대기 중")
        elif args.plan_command == "classify":
            from tools.plan_parser import classify_plan_image

            kind = classify_plan_image(args.image)
            if not kind:
                raise SystemExit("판별 실패")
            print(kind)
        elif args.plan_command == "reparse":
            if args.yes or _confirm("현재 파일을 backup하고 OCR로 다시 생성할까요?"):
                backup = manager.create_backup(args.year, args.month)
                generate_monthly_plan(args.year, args.month)
                manager.validate(args.year, args.month)
                print(f"✅ 재생성·검증 완료 (backup: {backup})")
        elif args.plan_command == "deploy":
            if args.yes or _confirm("운영 mh_bot에 반영할까요?"):
                deploy_plan(
                    manager,
                    args.year,
                    args.month,
                    args.host,
                    args.remote_project,
                )
        elif args.plan_command == "publish":
            if args.yes or _confirm(
                "asset 재파싱 → 검증 → QT Docs 탭 → mh_bot 배포 → owner Telegram test를 실행할까요?"
            ):
                result = publish_plan(
                    manager,
                    args.year,
                    args.month,
                    args.host,
                    args.remote_project,
                    send_test=not args.no_test,
                    create_sheet=not args.no_sheet,
                )
                print(result.diff or "내용 변경 없음")
                print(f"✅ publish 완료: {result.path}")
                print(f"🛟 backup: {result.backup_path}")
                print(f"📨 Telegram test: {'완료' if result.test_sent else '생략'}")
        elif args.plan_command == "sheet":
            plan = manager.validate(args.year, args.month)
            print(upsert_quiet_time_tab(plan, args.year, args.month))
        elif args.plan_command == "notify":
            send_publish_test(manager, args.year, args.month, args.day)
        return 0
    except (
        FileNotFoundError,
        ValueError,
        RuntimeError,
        json.JSONDecodeError,
        subprocess.CalledProcessError,
    ) as error:
        print(f"❌ {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
