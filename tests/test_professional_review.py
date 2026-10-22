import copy
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools import guardian_professional_review as r


class ProfessionalReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.corpus = r._json(r.ROOT / 'core/qualification-cases-v1.json')

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        # macOS may expose the OS temp root through /var -> /private/var.
        # Canonicalize only this trusted fixture root, never candidate paths.
        self.root = Path(self.temp.name).resolve()
        (self.root / 'answer.txt').write_bytes(b'candidate output, not verified')
        self.sha = hashlib.sha256((self.root / 'answer.txt').read_bytes()).hexdigest()
        self.manifest = {'schema_version': 1, 'submissions': [{
            'case_id': 'A00:professional:1', 'author_id': 'candidate',
            'revision': 'fixture', 'model': 'fixture-no-model-executed',
            'artifacts': [{'path': 'answer.txt', 'sha256': self.sha}]}]}

    def export(self, artifacts=False):
        out = self.root / 'bundle'
        r.export(self.corpus, out, self.manifest if artifacts else None, self.root)
        review = r._json(out / 'review-template.json')
        return out, review

    def test_preview_103_no_oracle_or_future_private_fields(self):
        corpus = copy.deepcopy(self.corpus)
        for case in corpus['cases']:
            case['private_answer'] = 'SECRET_SENTINEL'
            case['oracle']['acceptance'] = 'SECRET_SENTINEL'
        rows = r.preview(corpus)
        self.assertEqual(len(rows), 103)
        encoded = json.dumps(rows)
        self.assertNotIn('SECRET_SENTINEL', encoded)
        self.assertNotIn('"oracle"', encoded)

    def test_template_unknown_never_qualified(self):
        out, review = self.export()
        report = r.ingest(self.corpus, out, review)
        self.assertEqual(report['qualified_cases'], 0)
        self.assertFalse(report['private_holdout_validated'])
        self.assertFalse(report['reviewer_identity_authenticated'])
        self.assertEqual(len(report['rows']), 103)
        self.assertTrue(all(row['criteria']['unknown'] > 0 for row in report['rows']))

    def test_forged_human_approval_unknown_field_rejected(self):
        out, review = self.export()
        review['human_approved'] = True
        with self.assertRaises(ValueError):
            r.ingest(self.corpus, out, review)

    def test_external_review_and_ai_never_certify(self):
        out, review = self.export(artifacts=True)
        first = review['reviews'][0]['criteria'][0]
        first.update(verdict='supported', evidence_sha256=[self.sha], rationale='Read bytes only; no runtime observed')
        for kind in ('AI_ADVISORY', 'EXTERNAL_REVIEW_UNAUTHENTICATED'):
            review['review_kind'] = kind
            report = r.ingest(self.corpus, out, review)
            self.assertEqual(report['qualified_cases'], 0)
            self.assertEqual(report['rows'][0]['criteria']['supported'], 1)
            self.assertEqual(report['rows'][0]['review_class'], kind)
        review['review_kind'] = 'AUTHENTICATED_SME'
        with self.assertRaises(ValueError):
            r.ingest(self.corpus, out, review)

    def test_conclusions_require_evidence_for_exact_case(self):
        out, review = self.export()
        review['reviews'][0]['criteria'][0]['verdict'] = 'supported'
        with self.assertRaises(ValueError):
            r.ingest(self.corpus, out, review)

    def test_missing_criteria_rejected(self):
        out, review = self.export()
        review['reviews'][0]['criteria'].pop()
        with self.assertRaises(ValueError):
            r.ingest(self.corpus, out, review)

    def test_unknown_case_and_duplicate_case_rejected(self):
        for cid in ('unknown', 'S08:typed:1', 'A00:professional:2'):
            out, review = self.export()
            review['reviews'][0]['case_id'] = cid
            with self.assertRaises(ValueError):
                r.ingest(self.corpus, out, review)
            # each subsequent export requires a new directory
            import shutil
            shutil.rmtree(out)

    def test_manifest_unknown_case_and_duplicate_path(self):
        for mutation in ('unknown', 'duplicate'):
            manifest = copy.deepcopy(self.manifest)
            if mutation == 'unknown':
                manifest['submissions'][0]['case_id'] = 'unknown'
            else:
                manifest['submissions'][0]['artifacts'].append(copy.deepcopy(manifest['submissions'][0]['artifacts'][0]))
            with self.assertRaises(ValueError):
                r.validate_manifest(self.corpus, manifest, self.root)

    def test_input_and_exported_artifact_drift(self):
        out, review = self.export(artifacts=True)
        (self.root / 'answer.txt').write_text('changed')
        with self.assertRaises(ValueError):
            r.validate_manifest(self.corpus, self.manifest, self.root)
        (out / 'artifacts' / (self.sha + '.bin')).write_text('changed')
        with self.assertRaises(ValueError):
            r.ingest(self.corpus, out, review)

    def test_output_exists_never_overwritten(self):
        out, _ = self.export()
        before = (out / 'index.json').read_bytes()
        with self.assertRaises(FileExistsError):
            r.export(self.corpus, out)
        self.assertEqual((out / 'index.json').read_bytes(), before)

    def test_invalid_paths(self):
        for path in ('../answer.txt', '/answer.txt', 'C:/answer.txt', 'a\\b', './answer.txt', 'a//b', 'NUL.txt', 'folder./x', 'a /x'):
            manifest = copy.deepcopy(self.manifest)
            manifest['submissions'][0]['artifacts'][0]['path'] = path
            with self.assertRaises(ValueError):
                r.validate_manifest(self.corpus, manifest, self.root)

    def test_reparse_component_rejected_without_link_privilege(self):
        original = Path.lstat
        target = self.root / 'answer.txt'
        def fake_lstat(path):
            result = original(path)
            if path == target:
                class Attr:
                    st_mode = result.st_mode
                    st_file_attributes = 0x400
                return Attr()
            return result
        with patch.object(Path, 'lstat', fake_lstat):
            with self.assertRaisesRegex(ValueError, 'reparse'):
                r._read(target)

    def test_duplicate_json_and_nonfinite_rejected(self):
        path = self.root / 'bad.json'
        for text in ('{"a":1,"a":2}', '{"a":NaN}', '[]garbage'):
            path.write_text(text)
            with self.assertRaises(ValueError):
                r._json(path)

    def test_bounded_file(self):
        with patch.object(r, 'MAX_BYTES', 1):
            with self.assertRaises(ValueError):
                r._read(self.root / 'answer.txt')

    def test_bundle_binding_and_rubric_drift(self):
        out, review = self.export()
        review['bundle_sha256'] = '0' * 64
        with self.assertRaises(ValueError):
            r.ingest(self.corpus, out, review)
        index = r._json(out / 'index.json')
        index['cases'][0]['criteria'][0]['requirement'] = 'tampered'
        (out / 'index.json').write_text(json.dumps(index))
        review['bundle_sha256'] = r.q.digest(index)
        with self.assertRaises(ValueError):
            r.ingest(self.corpus, out, review)

    def test_criterion_duplicates_and_cross_case_evidence(self):
        out, review = self.export(artifacts=True)
        item = review['reviews'][1]
        item['criteria'][0].update(verdict='supported', evidence_sha256=[self.sha])
        with self.assertRaises(ValueError):
            r.ingest(self.corpus, out, review)
        item['criteria'][0].update(verdict='unknown', evidence_sha256=[])
        item['criteria'][1]['id'] = item['criteria'][0]['id']
        with self.assertRaises(ValueError):
            r.ingest(self.corpus, out, review)

    def test_identical_bytes_different_paths_deduplicate_blobs(self):
        (self.root / 'other.txt').write_bytes((self.root / 'answer.txt').read_bytes())
        self.manifest['submissions'][0]['artifacts'].append({'path': 'other.txt', 'sha256': self.sha})
        out, review = self.export(artifacts=True)
        self.assertEqual(len(list((out / 'artifacts').iterdir())), 1)
        self.assertEqual(r.ingest(self.corpus, out, review)['qualified_cases'], 0)

    def test_boolean_schema_version_rejected(self):
        out, review = self.export()
        review['schema_version'] = True
        with self.assertRaises(ValueError):
            r.ingest(self.corpus, out, review)

    def test_blind_bundle_omits_author_model_and_original_path(self):
        out, _ = self.export(artifacts=True)
        index = (out / 'index.json').read_text(encoding='utf-8')
        self.assertNotIn('"author_id"', index)
        self.assertNotIn('"model"', index)
        self.assertNotIn('answer.txt', index)
        self.assertEqual((out / 'artifacts' / (self.sha + '.bin')).read_bytes(), (self.root / 'answer.txt').read_bytes())


if __name__ == '__main__':
    unittest.main()
