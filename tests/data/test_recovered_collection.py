"""Read-only acceptance checks for the 2026-09-28 rebuilt private collection.

The public sample and the historical private curation have their own tests.
Set TOEFL_RECOVERY_TEST_ROOT to validate an isolated install before publication.
No files, source materials, sessions, or expected hashes are rewritten here.
"""
from __future__ import annotations

from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import re
import unittest
from urllib.parse import unquote, urlsplit
import wave

from backend.engine import grade, media_sequence
from backend.presentation import content_digest, validate_question

REPOSITORY = Path(__file__).resolve().parents[2]
VERSION = '2026-09-28-source-reconstruction-v1'
EXPECTED_EXAMS = {
    *(f'experience-{n}' for n in range(1, 4)),
    *(f'pack-{n}' for n in range(1, 7)),
    'student-1', 'student-2', 'teacher-1', 'teacher-2', 'paid-1', 'paid-2',
    *(f'essentials-{n}' for n in range(1, 4)),
}
SAMPLE_PROFILE = {'id': 'ets-practice-test-1', 'version': 3, 'profile': 'runtime-only'}
HASH = re.compile(r'^[0-9a-f]{64}$')
SUBJECTIVE = {'email', 'academic_discussion', 'picture_writing', 'listen_repeat', 'interview', 'read_aloud'}
# These two supplied editions print named posts without portraits. This narrow
# exception was checked on Paid 1 PDF pages 20–21 and Paid 2 pages 25–26;
# borrowing the Pack screenshots' faces would misrepresent their source layout.
TEXT_ONLY_DISCUSSIONS = {
    'paid-1-w-academic_discussion': ('mat-41197f393dad', 20, ['Dr. Gupta', 'Kelly', 'Andrew']),
    'paid-2-w-academic_discussion': ('mat-7a22d4e00f33', 25, ['Dr. Diaz', 'Claire', 'Andrew']),
}


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8'))


def items(exam):
    for section in exam['sections']:
        for module in section['modules']:
            for question in module['questions']:
                yield section, module, question


def units(question):
    return len(question['blanks']) if question['type'] == 'cloze' else 1


def conflicted(item):
    return (item.get('answerConflict', {}).get('status') == 'needs-review'
            or item.get('auditStatus') == 'answer-conflict')


def available(question):
    # A deliberately untimed paper-transcript study can remain answerable while
    # its unmatched recording keeps the strict listening scope unavailable.
    return (question.get('sourcePromptAvailable', True)
            and (not question.get('referenceOnly') or question.get('sourcePromptAvailable') is True))


def walk(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk(child)


def source_ids(value):
    return {record[key] for record in walk(value)
            for key in ('materialId', 'sourceMaterialId', 'referenceMaterialId')
            if isinstance(record.get(key), str)}


def asset_urls(value):
    return {record['url'] for record in walk(value)
            if isinstance(record.get('url'), str) and record['url'].startswith('/assets/')}


class RecoveredCollectionIntegrity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        requested = os.environ.get('TOEFL_RECOVERY_TEST_ROOT')
        cls.root = Path(requested).expanduser().resolve() if requested else REPOSITORY
        catalog_path = cls.root / 'generated/catalog.json'
        if not catalog_path.is_file():
            if requested:
                raise AssertionError(f'Explicit recovery test root has no catalog: {cls.root}')
            raise unittest.SkipTest('No reconstructed private collection is installed')
        cls.catalog = read_json(catalog_path)
        rows = cls.catalog.get('exams', []) + cls.catalog.get('supplementalExams', [])
        # A partial/corrupt reconstruction must fail rather than masquerade as a
        # public checkout. Proof files are a second detection signal.
        detected = any(row.get('recoveryReview') for row in rows)
        detected = detected or any((cls.root / 'generated/recovery/2026-09-28').glob('*.json'))
        if not detected:
            if requested:
                raise AssertionError('Explicit recovery test root contains no reconstructed snapshot')
            raise unittest.SkipTest('No reconstructed private collection is installed')
        cls.rows = rows
        cls.exams = {row['id']: read_json(cls.root / 'generated/exams' / f"{row['id']}.json")
                     for row in rows}
        cls.materials = {m['id']: m for m in cls.catalog['materials']}
        cls.questions = {q['id']: q for exam in cls.exams.values() for _, _, q in items(exam)}
        cls.hash_cache = {}
        cls.proofs = {}
        for eid, exam in cls.exams.items():
            if eid != 'student-1':
                relative = exam.get('recoveryReview', {}).get('proof')
                if not isinstance(relative, str):
                    raise AssertionError(f'{eid}: reconstruction proof is missing')
                target = (cls.root / relative).resolve()
                if not target.is_relative_to(cls.root) or not target.is_file():
                    raise AssertionError(f'{eid}: invalid reconstruction proof path')
                cls.proofs[eid] = read_json(target)

    def digest(self, path):
        path = Path(path).resolve()
        self.assertTrue(path.is_relative_to(self.root), f'Path escapes snapshot: {path}')
        self.assertTrue(path.is_file(), f'Missing file: {path}')
        if path not in self.hash_cache:
            result = hashlib.sha256()
            with path.open('rb') as handle:
                for chunk in iter(lambda: handle.read(1024 * 1024), b''):
                    result.update(chunk)
            self.hash_cache[path] = result.hexdigest()
        return self.hash_cache[path]

    def local_url(self, url):
        parsed = urlsplit(url)
        self.assertFalse(parsed.scheme or parsed.netloc, url)
        decoded = unquote(parsed.path)
        if decoded.startswith('/materials/'):
            base, relative = self.root / 'data', decoded.removeprefix('/materials/')
        else:
            self.assertTrue(decoded.startswith('/assets/'), url)
            base, relative = self.root / 'generated/assets', decoded.removeprefix('/assets/')
        target = (base / relative).resolve()
        self.assertTrue(target.is_relative_to(base.resolve()), url)
        return target

    def assert_source_media(self, value):
        for media in value if isinstance(value, list) else [value]:
            self.assertIsInstance(media, dict)
            source = self.materials[media.get('materialId') or media.get('sourceMaterialId')]
            self.assertIn(source['kind'], {'audio', 'video'})
            self.assertEqual(media['sourceSha256'], source['sha256'])
            self.assertNotEqual(media.get('scope'), 'section')
            self.assertNotIn('/_analysis/', media['url'])
            target = self.local_url(media['url'])
            self.assertTrue(target.is_file())
            spans = media.get('sourceIntervals') or ([media] if 'startSeconds' in media else [])
            for span in spans:
                self.assertGreaterEqual(span['startSeconds'], 0)
                self.assertLess(span['startSeconds'], span['endSeconds'])
                self.assertLessEqual(span['endSeconds'], source['durationSeconds'] + .25)
            if target.suffix.lower() == '.wav':
                with wave.open(str(target), 'rb') as wav:
                    seconds = wav.getnframes() / wav.getframerate()
                self.assertAlmostEqual(seconds, media['durationSeconds'], delta=.03)

    def test_all_eighteen_archives_and_all_source_files_are_present(self):
        ids = [row['id'] for row in self.rows]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(set(ids), EXPECTED_EXAMS)
        self.assertEqual(set(self.exams), EXPECTED_EXAMS)
        self.assertEqual(len(self.questions), 1514)
        self.assertEqual(sum(units(q) for q in self.questions.values()), 1811)
        self.assertEqual(len(self.materials), len(self.catalog['materials']))
        self.assertEqual(len(self.materials), 393)
        paths = [m['path'] for m in self.materials.values()]
        self.assertEqual(len(paths), len(set(paths)))
        actual = {p.relative_to(self.root / 'data').as_posix()
                  for p in (self.root / 'data').rglob('*')
                  if p.is_file() and p.relative_to(self.root / 'data').parts[0] != 'user-packs'
                  and not any(part.startswith('.') for part in p.relative_to(self.root / 'data').parts)}
        self.assertEqual(actual, set(paths), 'Catalog must inventory every non-hidden original file')
        self.assertEqual(sum(len(list(items(e))) for e in self.exams.values()), len(self.questions),
                         'Question IDs must be unique across source occurrences')

    def test_original_file_bytes_hashes_urls_and_pdf_page_bounds(self):
        for mid, material in self.materials.items():
            with self.subTest(material=mid):
                path = self.local_url(material['url'])
                self.assertEqual(path, (self.root / 'data' / material['path']).resolve())
                self.assertRegex(material['sha256'], HASH)
                self.assertEqual(path.stat().st_size, material['bytes'])
                self.assertEqual(self.digest(path), material['sha256'])
        for qid, q in self.questions.items():
            with self.subTest(question=qid):
                source = q['source']
                material = self.materials[source['materialId']]
                self.assertEqual(self.local_url(source['url']), self.local_url(material['url']))
                if material['kind'] == 'pdf':
                    self.assertIs(type(source['page']), int)
                    self.assertTrue(1 <= source['page'] <= material['pages'])
                else:
                    # The preserved public sample intentionally practices the
                    # supplied audio edition of interview question 1.
                    self.assertEqual(qid, 'student-1-s-interview-1-audio')
                    self.assertEqual(q['type'], 'interview')
                    self.assertEqual(q['audio']['materialId'], material['id'])
                    self.assertTrue(q['sourceVariant']['paperPrompt'])
                for field in ('sha256', 'sourceSha256'):
                    if field in source:
                        self.assertEqual(source[field], material['sha256'])
                self.assertIs(type(q['number']), int)
                self.assertGreater(q['number'], 0)

    def test_immutable_proofs_bind_every_native_screen_asset_and_source(self):
        for eid, exam in self.exams.items():
            with self.subTest(exam=eid):
                inputs = exam['verificationInputs']
                self.assertEqual(inputs['sourceHashStatus'], 'passed')
                self.assertEqual(inputs['missingFiles'], [])
                self.assertEqual(inputs['changedSourceMaterialIds'], [])
                self.assertTrue(inputs['curationSha256ByPath'])
                for relative, expected in inputs['curationSha256ByPath'].items():
                    self.assertRegex(expected, HASH)
                    self.assertEqual(self.digest(self.root / relative), expected, relative)
                native = {q['id']: content_digest(q) for _, _, q in items(exam)}
                self.assertEqual(inputs['structuredContentSha256ByQuestionId'], native)
                required_assets = asset_urls(exam['sections'])
                self.assertEqual(set(inputs['assetSha256ByUrl']), required_assets)
                for url, expected in inputs['assetSha256ByUrl'].items():
                    self.assertEqual(self.digest(self.local_url(url)), expected, url)
                if eid == 'student-1':
                    self.assertEqual(exam['bundledExample'], SAMPLE_PROFILE)
                    original = read_json(REPOSITORY / 'examples/ets-practice-test-1/exam.json')
                    self.assertEqual(exam['sections'], original['sections'])
                    continue
                marker = exam['recoveryReview']
                self.assertEqual(marker['version'], VERSION)
                self.assertTrue(marker['allOriginalItemsInventoried'])
                self.assertFalse(marker['officialScoring'])
                proof = self.proofs[eid]
                self.assertEqual(proof['schemaVersion'], 1)
                self.assertEqual(proof['examId'], eid)
                self.assertEqual(proof['rebuildVersion'], VERSION)
                self.assertFalse(proof['publisherCertified'])
                self.assertTrue(proof['method'])
                self.assertEqual(proof['nativeContentSha256ByQuestionId'], native)
                self.assertEqual(proof['runtimeAssetSha256ByUrl'], inputs['assetSha256ByUrl'])
                sources = proof['sourceSha256ById']
                self.assertEqual(set(sources), set(exam['sourceMaterialIds']))
                self.assertFalse(source_ids(exam['sections']) - set(sources),
                                 f'{eid}: referenced originals absent from immutable proof')
                for mid, expected in sources.items():
                    self.assertEqual(expected, self.materials[mid]['sha256'])
                self.assertTrue(proof['reviewReports'], 'Empty review gates are not valid provenance')
                review_text = json.dumps(proof['reviewReports'])
                for qid in native:
                    self.assertTrue(json.dumps(qid) in review_text or
                                    json.dumps(qid.removesuffix('-audio')) in review_text,
                                    f'{qid}: no corresponding per-item review evidence')
                digest = inputs['curationSha256ByPath'][marker['proof']]
                self.assertEqual(Path(marker['proof']).name, f'{eid}-{digest[:12]}.json')

    def test_native_presentations_and_original_media_are_usable(self):
        for eid, exam in self.exams.items():
            for section in exam['sections']:
                for module in section['modules']:
                    if module.get('directionsAudio'):
                        with self.subTest(exam=eid, module=module['id']):
                            self.assert_source_media(module['directionsAudio'])
            for section, module, q in items(exam):
                with self.subTest(question=q['id']):
                    self.assertEqual(validate_question(q, strict=True), [])
                    for asset in q.get('assets', []):
                        self.assertEqual(asset['role'], 'essentialVisual')
                        self.assertTrue(asset['highResolution'])
                        self.assertTrue(self.local_url(asset['url']).is_file())
                    for asset in q.get('sourceEvidenceAssets', []):
                        self.assertTrue(asset['reviewOnly'])
                        self.assertTrue(self.local_url(asset['url']).is_file())
                    for field in ('audio', 'cueAudio', 'directionsAudio', 'mediaSequence'):
                        if not q.get(field):
                            continue
                        self.assert_source_media(q[field])
                    if section['id'] in {'listening', 'speaking'} and q['type'] != 'read_aloud':
                        if exam.get('scopedEligibility', {}).get(section['id']):
                            self.assertIs(q.get('audio', {}).get('verified'), True)
                            self.assertIs(q['audio'].get('containsResponseWait'), False)
                        if q.get('transcript') and q.get('audio', {}).get('verified') and not q.get('referenceOnly'):
                            self.assertNotEqual(q['prompt'].strip(), q['transcript'].strip())
                            self.assertFalse(any(b.get('text', '').strip() == q['transcript'].strip()
                                                 for b in q['stemBlocks']))
                    if q['type'] == 'academic_discussion':
                        dialogues = [b for b in q['stemBlocks'] if b['type'] == 'dialogue']
                        self.assertEqual(len(dialogues), 1)
                        self.assertEqual(len(dialogues[0]['turns']), 3)
                        turns = dialogues[0]['turns']
                        if q['id'] in TEXT_ONLY_DISCUSSIONS:
                            mid, page, speakers = TEXT_ONLY_DISCUSSIONS[q['id']]
                            self.assertEqual((q['source']['materialId'], q['source']['page']), (mid, page))
                            self.assertEqual([t['speaker'] for t in turns], speakers)
                            self.assertEqual(q['assets'], [])
                            self.assertTrue(all('avatarAssetIndex' not in t for t in turns))
                            self.assertTrue(all(len(t['text']) > 100 for t in turns))
                        else:
                            self.assertEqual([t.get('avatarAssetIndex') for t in turns], [0, 1, 2])
                            self.assertEqual(len(q['assets']), 3)

    def test_reference_answers_grade_and_source_conflicts_do_not(self):
        for qid, q in self.questions.items():
            with self.subTest(question=qid):
                if q['type'] in SUBJECTIVE:
                    self.assertIsNone(grade(q, 'sample response'))
                    continue
                if conflicted(q):
                    self.assertIsNone(grade(q, q.get('sourceReferenceAnswer') or q.get('answer')))
                    self.assertTrue(q.get('warnings') or q.get('answerConflict', {}).get('reason'))
                    self.assertIsNone(q.get('answer'), 'An unresolved key must not be presented as correct')
                    self.assertFalse(q.get('acceptedAnswers'))
                    conflict = q.get('answerConflict', {})
                    self.assertTrue(q.get('sourceReferenceAnswer') or conflict.get('provided')
                                    or conflict.get('sourceAnswer') or conflict.get('sourceReferenceAnswer'))
                    continue
                if q['type'] == 'cloze':
                    ids = [b['id'] for b in q['blanks']]
                    self.assertEqual(Counter(re.findall(r'\{\{([^{}]+)\}\}', q['passageTemplate'])), Counter(ids))
                    answers = {}
                    for blank in q['blanks']:
                        if conflicted(blank):
                            self.assertIsNone(blank.get('answer'))
                            self.assertFalse(blank.get('fullWord') or blank.get('acceptedAnswers'))
                            conflict = blank.get('answerConflict', {})
                            self.assertTrue(blank.get('sourceReferenceAnswer') or conflict.get('provided')
                                            or conflict.get('sourceAnswer') or conflict.get('sourceReferenceAnswer'))
                            continue
                        if blank.get('autoScorable') is False:
                            self.fail(f'{qid}/{blank["id"]}: disabled grading has no documented source conflict')
                        self.assertIsInstance(blank.get('answer'), str)
                        missing = blank.get('missingLetters') or blank['answer']
                        self.assertEqual(len(missing), blank['length'])
                        if blank.get('fullWord'):
                            self.assertEqual((blank.get('prefix', '') + missing + blank.get('suffix', '')).casefold(),
                                             blank['fullWord'].casefold())
                        answers[blank['id']] = missing
                    expected = {'correct': len(answers), 'total': len(answers)} if answers else None
                    self.assertEqual(grade(q, answers), expected)
                    if answers:
                        self.assertEqual(grade(q, {}), {'correct': 0, 'total': len(answers)})
                elif q['type'] == 'choice':
                    ids = [c['id'] for c in q['choices']]
                    self.assertEqual(len(ids), len(set(ids)))
                    self.assertIn(q['answer'], ids)
                    self.assertEqual(grade(q, q['answer']), {'correct': 1, 'total': 1})
                    for other in set(ids) - {q['answer']}:
                        self.assertEqual(grade(q, other), {'correct': 0, 'total': 1})
                elif q['type'] == 'build_sentence':
                    order = q['expectedTokenOrder']
                    self.assertIsInstance(order, list)
                    self.assertEqual(len(order), sum('fixed' not in s for s in q['slots']))
                    self.assertEqual(len(order), len(set(order)))
                    self.assertTrue(all(type(i) is int and 0 <= i < len(q['tokens']) for i in order))
                    self.assertEqual(grade(q, {'tokenOrder': order}), {'correct': 1, 'total': 1})
                    self.assertEqual(grade(q, {'tokenOrder': []}), {'correct': 0, 'total': 1})

    def test_experience_two_conversation_directions_belong_to_question_eleven(self):
        # A missing OCR question once shifted the 11–12 conversation directions
        # onto response question 1. Bind the actual original files explicitly.
        response = self.questions['experience-2-l1-1']
        conversation = self.questions['experience-2-l1-11']
        self.assertEqual(response['taskType'], 'listen_response')
        self.assertFalse(response.get('directionsAudio'))
        self.assertEqual([m['materialId'] for m in media_sequence(response)], ['mat-e45f89013d19'])
        self.assertEqual(conversation['taskType'], 'conversation')
        self.assertEqual([m['materialId'] for m in media_sequence(conversation)],
                         ['mat-0a07d4a5bcb2', 'mat-8a09d9d1cab0'])
        self.assertEqual(media_sequence(conversation)[0]['kind'], 'directions')
        for q in (response, conversation):
            self.assertEqual(q['source']['materialId'], 'mat-f272755f6d06')

    def test_catalog_and_exam_counts_describe_the_actual_snapshot(self):
        totals = Counter()
        content_units = {}
        summary_by_id = {row['id']: row for row in self.rows}
        for eid, exam in self.exams.items():
            questions = [q for _, _, q in items(exam)]
            count = sum(map(units, questions))
            scorable = sum((grade(q, {}) or {}).get('total', 0) for q in questions if available(q))
            objective = sum(units(q) for q in questions if q['type'] not in SUBJECTIVE and available(q))
            with self.subTest(exam=eid):
                self.assertEqual(exam['questionCount'], count)
                self.assertEqual(exam['screenCount'], len(questions))
                self.assertEqual(exam['autoScorableCount'], scorable)
                self.assertEqual(exam['unscoredCount'], objective - scorable)
                self.assertEqual(exam['autoScoringComplete'], objective == scorable)
                for key in ('questionCount', 'screenCount', 'autoScorableCount', 'unscoredCount', 'strictEligible'):
                    self.assertEqual(summary_by_id[eid][key], exam[key])
                if exam.get('interactiveQuestionCount') is not None:
                    self.assertEqual(exam['interactiveQuestionCount'], sum(units(q) for q in questions if available(q)))
                for section in exam['sections']:
                    summary = next(s for s in summary_by_id[eid]['sections'] if s['id'] == section['id'])
                    self.assertEqual(summary['questionCount'], sum(units(q) for m in section['modules'] for q in m['questions']))
            totals['questionCount'] += count
            totals['supplementalQuestionCount' if exam.get('supplemental') else 'ibtQuestionCount'] += count
            totals['supplementalExamCount' if exam.get('supplemental') else 'ibtExamCount'] += 1
            if not exam.get('supplemental') and not exam.get('resourcesOnly'):
                totals['interactiveExamCount'] += 1
            totals['strictExamCount'] += bool(exam['strictEligible'])
            for q in questions:
                self.assertRegex(q['contentId'], r'^qcontent-[0-9a-f]{20}$')
                if q['contentId'] in content_units:
                    self.assertEqual(content_units[q['contentId']], units(q))
                content_units[q['contentId']] = units(q)
        totals['uniqueQuestionCount'] = sum(content_units.values())
        for key, expected in totals.items():
            self.assertEqual(self.catalog['stats'][key], expected, key)
        stats = self.catalog['stats']
        self.assertEqual(stats['materialFileCount'], len(self.materials))
        self.assertEqual(stats['fileCount'], len(self.materials) + len(self.catalog.get('excludedSystemFiles', [])))
        self.assertEqual(stats['totalBytes'], sum(m['bytes'] for m in self.materials.values()))
        for kind in ('pdf', 'audio', 'video'):
            self.assertEqual(stats[kind + 'Count'], sum(m['kind'] == kind for m in self.materials.values()))

    def test_missing_original_tasks_are_explicit_and_never_filled_with_guesses(self):
        paid = self.exams['paid-2']
        build = next(m for s in paid['sections'] for m in s['modules'] if m['id'] == 'writing-build')
        self.assertEqual([q['number'] for q in build['questions']], list(range(1, 7)))
        self.assertEqual(build['expectedItemCount'], 10)
        excluded = paid['excludedTasks']
        self.assertEqual([(x['section'], x['taskType'], x['number']) for x in excluded],
                         [('writing', 'build_sentence', n) for n in range(7, 11)])
        self.assertFalse(paid['strictEligible'], 'An incomplete writing section cannot be a full strict mock')
        self.assertFalse(paid['scopedEligibility']['writing'])
        for item in excluded:
            self.assertTrue(item['reason'])
            self.assertIn(item['source']['materialId'], self.materials)
            self.assertTrue(self.local_url(item['source']['url']).is_file())
        essentials = self.exams['essentials-2']
        excluded = [x for s in essentials['sections'] for x in s.get('excludedTasks', [])]
        self.assertEqual([x['originalNumber'] for x in excluded], [14, 17])
        self.assertEqual(essentials['expectedSourceQuestionCount'], essentials['questionCount'] + len(excluded))
        for item in excluded:
            self.assertIs(item['sourcePromptAvailable'], False)
            self.assertEqual(item['status'], 'reference-only-source-prompt-missing')
            self.assertTrue(item['reason'])
            self.assertTrue(self.local_url(item['source']['url']).is_file())
        for eid in ('essentials-1', 'essentials-2', 'essentials-3'):
            exam = self.exams[eid]
            self.assertIs(exam['supplemental'], True)
            self.assertEqual(exam['timingPolicy'], 'untimed')
            self.assertIs(exam['strictEligible'], False)

    def test_paid_one_webinar_correction_preserves_both_source_editions(self):
        exam = self.exams['paid-1']
        if exam.get('recoveryReview', {}).get('amendedAt') != '2026-10-04':
            self.skipTest('Optional October 4 source correction is not installed')
        question = self.questions['paid-1-r1-24']
        matching = self.questions['pack-1-reading-m1-24']
        self.assertEqual(question['choices'], matching['choices'])
        self.assertEqual(question['stemBlocks'], matching['stemBlocks'])
        self.assertEqual(question['answer'], 'D')
        self.assertEqual(question['sourceReferenceAnswer'], 'B')
        self.assertEqual(question['editionReferenceAnswer'], 'B')
        self.assertEqual(question['resolutionEvidence']['originalOptionD'],
                         'They will have a chance to talk to others during the')
        self.assertEqual(question['choices'][3]['text'],
                         'They will have a chance to talk to others during the webinar.')
        self.assertEqual(question['canonicalQuestionId'], matching['id'])
        self.assertEqual(question['contentId'], matching['contentId'])
        self.assertTrue(question['sourceVariant']['notice'])
        self.assertEqual(question['source']['materialId'], 'mat-41197f393dad')
        self.assertEqual(question['resolutionEvidence']['matchingSource']['materialId'], 'mat-e028047bd7f0')
        self.assertEqual(grade(question, 'D'), {'correct': 1, 'total': 1})
        self.assertEqual(grade(question, 'B'), {'correct': 0, 'total': 1})
        proof = self.proofs['paid-1']
        amendment = proof['reviewReports']['amendment-2026-10-04']
        previous = proof['revision']['previousProof']
        self.assertEqual(self.digest(self.root / previous), proof['revision']['previousProofSha256'])
        self.assertEqual(amendment['before']['choices'][3]['text'],
                         question['resolutionEvidence']['originalOptionD'])
        self.assertIsNone(amendment['before']['answer'])
        self.assertEqual(content_digest(amendment['after']), content_digest(question))
        self.assertEqual(read_json(self.root / previous)['nativeContentSha256ByQuestionId'][question['id']],
                         content_digest(amendment['before']))


if __name__ == '__main__':
    unittest.main()
