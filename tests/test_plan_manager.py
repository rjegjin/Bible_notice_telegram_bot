import json
import tempfile
import unittest
from unittest.mock import MagicMock, patch
from pathlib import Path

from PIL import Image

from tools.plan_manager import PlanManager, import_plan_images, publish_plan, stage_plan_image
from tools.quiet_time_docs import HEADERS, month_rows, upsert_quiet_time_tab, verify_tab


def valid_july_plan():
    return {
        str(day): ["마 1", "창 1", "시 1", f"잠 {day}", "요 1:1-2"]
        for day in range(1, 32)
    }


class PlanManagerTests(unittest.TestCase):
    @patch("tools.plan_manager.generate_monthly_plan", return_value={"1": ["마 1", "창 1", "시 1", "잠 1", "요 1:1-2"]})
    def test_stage_waits_for_both_images_then_writes_standby(self, generate):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            assets = root / "assets"
            standby = root / "standby"
            br = root / "br.jpg"
            qt = root / "qt.jpg"
            Image.new("RGB", (20, 20), "white").save(br)
            Image.new("RGB", (20, 20), "white").save(qt)

            first = stage_plan_image(2026, 10, "BR", br, assets_dir=assets, standby_dir=standby)
            second = stage_plan_image(2026, 10, "QT", qt, assets_dir=assets, standby_dir=standby)

        self.assertIsNone(first)
        self.assertEqual(second, standby / "2026_10.json")
        generate.assert_called_once_with(2026, 10, output_dir=standby)
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.plans_dir = Path(self.temp_dir.name)
        self.plan_path = self.plans_dir / "2026_07.json"
        self.original = valid_july_plan()
        self.plan_path.write_text(
            json.dumps(self.original, ensure_ascii=False, indent=4) + "\n",
            encoding="utf-8",
        )
        self.manager = PlanManager(self.plans_dir)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_update_validates_backs_up_and_atomically_saves(self):
        result = self.manager.update_day(
            2026,
            7,
            15,
            {"qt": "요 5:1-18"},
        )

        saved = json.loads(self.plan_path.read_text(encoding="utf-8"))
        backup = json.loads(result.backup_path.read_text(encoding="utf-8"))
        self.assertEqual(saved["15"][4], "요 5:1-18")
        self.assertEqual(backup, self.original)
        self.assertIn('-        "요 1:1-2"', result.diff)
        self.assertIn('+        "요 5:1-18"', result.diff)

    def test_invalid_update_preserves_original_without_backup(self):
        with self.assertRaisesRegex(ValueError, "성경 DB 범위 밖"):
            self.manager.update_day(
                2026,
                7,
                3,
                {"qt": "욥 1:35-51"},
            )

        saved = json.loads(self.plan_path.read_text(encoding="utf-8"))
        self.assertEqual(saved, self.original)
        self.assertFalse((self.plans_dir / "backups").exists())

    def test_unknown_field_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "지원하지 않는 필드"):
            self.manager.update_day(2026, 7, 1, {"memo": "잘못된 필드"})

    def test_list_months_reads_only_plan_file_names(self):
        (self.plans_dir / "notes.json").write_text("{}", encoding="utf-8")
        (self.plans_dir / "2026_08.json").write_text("{}", encoding="utf-8")

        self.assertEqual(
            self.manager.list_months(),
            [(2026, 7), (2026, 8)],
        )

    def test_publish_reparses_deploys_and_notifies_owner(self):
        deployed = []
        notified = []

        def generator(year, month):
            plan = valid_july_plan()
            plan["6"][0] = "마 21-24"
            self.plan_path.write_text(
                json.dumps(plan, ensure_ascii=False, indent=4) + "\n",
                encoding="utf-8",
            )
            return plan

        result = publish_plan(
            self.manager,
            2026,
            7,
            host="example",
            remote_project="/remote/project",
            send_test=True,
            generator=generator,
            deployer=lambda *args: deployed.append(args),
            notifier=lambda *args: notified.append(args),
            sheet_writer=lambda *args: None,
        )

        self.assertTrue(result.changed)
        self.assertTrue(result.backup_path.exists())
        self.assertIn("마 21-24", result.diff)
        self.assertEqual(len(deployed), 1)
        self.assertEqual(len(notified), 1)

    def test_publish_promotes_validated_standby_without_reocr(self):
        standby_dir = self.plans_dir / "standby"
        standby_dir.mkdir()
        standby = valid_july_plan()
        standby["6"][0] = "마 21-24"
        (standby_dir / "2026_07.json").write_text(
            json.dumps(standby, ensure_ascii=False, indent=4) + "\n",
            encoding="utf-8",
        )

        publish_plan(
            self.manager,
            2026,
            7,
            "example",
            "/remote/project",
            generator=lambda *_: self.fail("standby가 있으면 재OCR하면 안 됨"),
            standby_dir=standby_dir,
            sheet_writer=lambda *_: None,
            deployer=lambda *_: None,
            notifier=lambda *_: None,
        )

        self.assertEqual(json.loads(self.plan_path.read_text(encoding="utf-8")), standby)

    def test_docs_failure_stops_deploy_and_notification(self):
        with patch('tools.plan_manager.upsert_quiet_time_tab', create=True,
                   side_effect=RuntimeError('Docs readback failed')):
            with self.assertRaisesRegex(RuntimeError, 'Docs readback failed'):
                publish_plan(
                    self.manager, 2026, 7, 'example', '/remote/project',
                    generator=lambda *args: self.original,
                    deployer=lambda *args: self.fail('must not deploy'),
                    notifier=lambda *args: self.fail('must not notify'),
                )

    def test_sheet_runs_before_deploy_and_can_be_skipped(self):
        for enabled in (True, False):
            events = []
            publish_plan(self.manager, 2026, 7, 'example', '/remote/project',
                         generator=lambda *args: self.original,
                         create_sheet=enabled,
                         sheet_writer=lambda *args: events.append('sheet'),
                         deployer=lambda *args: events.append('deploy'),
                         notifier=lambda *args: events.append('notify'))
            self.assertEqual(events, ['sheet', 'deploy', 'notify'] if enabled else ['deploy', 'notify'])

    def test_publish_restores_backup_when_generated_plan_is_invalid(self):
        def invalid_generator(year, month):
            plan = valid_july_plan()
            plan["3"][4] = "욥 1:35-51"
            self.plan_path.write_text(
                json.dumps(plan, ensure_ascii=False, indent=4) + "\n",
                encoding="utf-8",
            )
            return plan

        with self.assertRaisesRegex(ValueError, "성경 DB 범위 밖"):
            publish_plan(
                self.manager,
                2026,
                7,
                host="example",
                remote_project="/remote/project",
                send_test=False,
                generator=invalid_generator,
                deployer=lambda *args: self.fail("invalid plan must not deploy"),
                notifier=lambda *args: self.fail("invalid plan must not notify"),
            )

        restored = json.loads(self.plan_path.read_text(encoding="utf-8"))
        self.assertEqual(restored, self.original)


class QuietTimeDocsTests(unittest.TestCase):
    def tab(self):
        rows = month_rows(valid_july_plan(), 2026, 7)
        content = []
        index = 1
        def paragraph(text):
            nonlocal index
            start = index
            index += len(text) + 1
            return {'startIndex': start, 'endIndex': index, 'paragraph': {
                'elements': [{'textRun': {'content': text + '\n'}}]}}
        for page, page_rows in enumerate((rows[:15], rows[15:])):
            title = '2026년 7월 Quiet Time 적용 시트'
            content.append(paragraph(title if page == 0 else f'{title} (16일 ~ 31일)'))
            start = index
            index += 1
            table_rows = []
            for values in [HEADERS] + [r[0] for r in page_rows]:
                cells = []
                for ci, value in enumerate(values):
                    index += 1
                    cells.append({'content': [paragraph('내 적용 기록' if ci == 5 and value == '' else value)]})
                table_rows.append({'tableCells': cells})
            content.append({'startIndex': start, 'endIndex': index, 'table': {
                'rows': len(table_rows), 'columns': 7, 'tableRows': table_rows}})
            if len(content) == 2:
                content.append({'startIndex': index, 'endIndex': index + 1,
                                'sectionBreak': {'sectionStyle': {'sectionType': 'NEXT_PAGE'}}})
                index += 1
        content.append(paragraph(''))
        return {'tabProperties': {'title': '7월', 'tabId': 'target'},
                'documentTab': {'body': {'content': content}}}

    def test_existing_tab_targeting_preserves_application_and_checks_readback(self):
        tab = self.tab()
        other = {'tabProperties': {'title': '8월', 'tabId': 'other'}, 'documentTab': {'body': {'content': []}}}
        service = MagicMock()
        api = service.documents.return_value
        api.get.return_value.execute.side_effect = [
            {'revisionId': revision, 'tabs': [other, tab]} for revision in ('r1', 'r2', 'r2')]
        api.batchUpdate.return_value.execute.side_effect = [
            {'writeControl': {'requiredRevisionId': revision}} for revision in ('r2', 'r3')]
        url = upsert_quiet_time_tab(valid_july_plan(), 2026, 7, service=service)
        self.assertTrue(url.endswith('tab=target'))
        self.assertEqual(api.batchUpdate.call_count, 1)
        bodies = [c.kwargs['body'] for c in api.batchUpdate.call_args_list]
        self.assertEqual([b['writeControl']['requiredRevisionId'] for b in bodies], ['r1'])
        for body in bodies:
            for request in body['requests']:
                self.assertNotIn('addDocumentTab', request)
                self.assertIn('target', json.dumps(request))
        note_ranges = [(cell['content'][0]['startIndex'], cell['content'][0]['endIndex'])
                       for e in tab['documentTab']['body']['content'] if 'table' in e
                       for r in e['table']['tableRows'][1:] for cell in r['tableCells'][3:]]
        for req in bodies[0]['requests']:
            if 'deleteContentRange' in req:
                rng = req['deleteContentRange']['range']
                self.assertFalse(any(rng['startIndex'] < end and rng['endIndex'] > start
                                     for start, end in note_ranges))
        tab['documentTab']['body']['content'][1]['table']['tableRows'][1]['tableCells'][2]['content'][0]['paragraph']['elements'][0]['textRun']['content'] = '잘못된 본문\n'
        with self.assertRaisesRegex(RuntimeError, '본문 불일치'):
            verify_tab(tab, month_rows(valid_july_plan(), 2026, 7), 2026, 7)

    def test_validation_precedes_api_and_revision_conflict_stops_writes(self):
        service = MagicMock()
        with self.assertRaises(ValueError):
            upsert_quiet_time_tab({}, 2026, 7, service=service)
        service.documents.assert_not_called()
        api = service.documents.return_value
        tab = self.tab()
        api.get.return_value.execute.side_effect = [
            {'revisionId': 'r1', 'tabs': [tab]}, {'revisionId': 'collaborator', 'tabs': [tab]}]
        api.batchUpdate.return_value.execute.return_value = {'writeControl': {'requiredRevisionId': 'r2'}}
        with self.assertRaisesRegex(RuntimeError, '다른 편집자'):
            upsert_quiet_time_tab(valid_july_plan(), 2026, 7, service=service)
        self.assertEqual(api.batchUpdate.call_count, 1)

    def test_missing_month_creates_one_tab_with_two_tables_and_scoped_requests(self):
        service = MagicMock()
        api = service.documents.return_value
        tab = self.tab()
        blank = {'tabProperties': tab['tabProperties'], 'documentTab': {'body': {'content': []}}}
        api.get.return_value.execute.side_effect = [
            {'revisionId': 'r0', 'tabs': []}, {'revisionId': 'r1', 'tabs': [blank]},
            *[{'revisionId': f'r{i}', 'tabs': [tab]} for i in (2, 3, 4)]]
        api.batchUpdate.return_value.execute.side_effect = [
            {'writeControl': {'requiredRevisionId': f'r{i}'}} for i in (1, 2, 3, 4)]
        upsert_quiet_time_tab(valid_july_plan(), 2026, 7, service=service)
        bodies = [c.kwargs['body'] for c in api.batchUpdate.call_args_list]
        self.assertEqual(bodies[0]['requests'], [{'addDocumentTab': {'tabProperties': {'title': '7월'}}}])
        structure = bodies[1]['requests']
        self.assertEqual([r['insertTable']['rows'] for r in structure if 'insertTable' in r], [17, 16])
        self.assertEqual([r['insertSectionBreak']['sectionType'] for r in structure if 'insertSectionBreak' in r], ['NEXT_PAGE'])
        for body in bodies[1:]:
            for request in body['requests']:
                self.assertIn('target', json.dumps(request))

    def test_month_lengths_and_holiday_priority(self):
        for year, month, days in [(2026, 2, 28), (2028, 2, 29), (2026, 9, 30), (2026, 10, 31)]:
            plan = {str(d): ['마 1', '창 1', '시 1', '잠 1', '요 1:1-2'] for d in range(1, days + 1)}
            rows = month_rows(plan, year, month)
            self.assertEqual(len(rows), days)
            self.assertEqual(rows[-1][0][0], f'{month}/{days}')
            if month == 10:
                self.assertEqual(rows[2][1], {'red': 1})  # Saturday, National Foundation Day.
                self.assertEqual(rows[4][1], {'red': 1})  # Substitute holiday.
                self.assertEqual(rows[9][1], {'blue': 1})


class ImportPlanImagesTests(unittest.TestCase):
    def test_imports_arbitrary_names_using_canonical_asset_names(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "phone-upload.jpg"
            Image.new("RGB", (10, 10), "white").save(source)

            imported = import_plan_images(
                2026,
                8,
                br_path=source,
                assets_dir=root / "assets",
            )

            self.assertEqual(
                imported["BR"].name,
                "2026년_08월_BR_passage.jpg",
            )
            self.assertTrue(imported["BR"].exists())

    def test_existing_asset_requires_explicit_replace(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            assets = root / "assets"
            assets.mkdir()
            existing = assets / "2026년_08월_QT_passage.png"
            replacement = root / "new-qt.jpg"
            Image.new("RGB", (10, 10), "white").save(existing)
            Image.new("RGB", (10, 10), "black").save(replacement)

            with self.assertRaisesRegex(FileExistsError, "--replace"):
                import_plan_images(
                    2026,
                    8,
                    qt_path=replacement,
                    assets_dir=assets,
                )

            imported = import_plan_images(
                2026,
                8,
                qt_path=replacement,
                assets_dir=assets,
                replace=True,
            )
            self.assertFalse(existing.exists())
            self.assertTrue(imported["QT"].exists())


if __name__ == "__main__":
    unittest.main()
