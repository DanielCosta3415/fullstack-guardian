import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
try:
    from test_install import inst
except ImportError:
    from tests.test_install import inst


class LegacyPolicyMigrationTests(unittest.TestCase):
    def fixture(self):
        body='## Full-Stack Engineering Guardian System v2.0 — persistent coordination policy\n\nKeep all safety boundaries.\n'
        return (inst.START+'\n'+body+inst.END).encode()

    def test_only_legacy_label_eol_and_blank_lines_can_migrate(self):
        block=self.fixture()
        changed=block.decode().replace('v2.0','v2.1.0').replace('\n','\r\n').encode()
        old=b'Personal before\n\n'+changed+b'\nPersonal after\n'
        self.assertEqual(inst.legacy_policy_base(old,b'\n\n'+block+b'\n'),b'Personal before\n\n\nPersonal after\n')

    def test_semantic_edits_unknown_heading_and_duplicate_markers_rejected(self):
        block=self.fixture()
        for changed in (block.replace(b'Keep all',b'Disable all'),block.replace(b'v2.0',b'v9.9'),block+block):
            with self.subTest(changed=changed):
                with self.assertRaises(ValueError):inst.legacy_policy_base(changed,block)

    def test_real_update_preserves_unmanaged_rules_and_rolls_back_exactly(self):
        with tempfile.TemporaryDirectory() as folder:
            home=Path(folder).resolve();c=home/'.codex';c.mkdir()
            instructions=c/'AGENTS.md';instructions.write_bytes(b'Personal rule: never change model.\n')
            config=c/'config.toml';original_config=b'model = "personal"\n[agents]\nenabled = false\nmax_threads = 2\n';config.write_bytes(original_config)
            jobs,instruction,piece=inst.proposal('user',home)
            legacy=home/'legacy-policy.md'
            legacy.write_text(piece.read_text(encoding='utf8').replace('Guardian System —','Guardian System v2.0 —'),encoding='utf8')
            with patch.object(inst,'proposal',return_value=(jobs,instruction,legacy)):
                inst.lifecycle('user',home,apply=True)
            receipt=json.loads((c/'guardian-install.json').read_text())
            old_entry=next(e for e in receipt['files'] if e['path']==str(instructions))
            original=instructions.read_bytes();owned=bytes.fromhex(old_entry['addition'])
            # Current templates retain the legacy heading; model the observed manual label/EOL fix.
            changed=owned.decode().replace('v2.0','v2.1.0').replace('\n','\r\n').encode()
            edited=original.replace(owned,changed)+b'\nPersonal tail stays byte-identical.\n'
            instructions.write_bytes(edited)
            preview=inst.lifecycle('user',home,'update')
            self.assertIn('policy_format_migration',preview)
            self.assertEqual(instructions.read_bytes(),edited)
            inst.lifecycle('user',home,'update',True)
            self.assertTrue(instructions.read_bytes().startswith(b'Personal rule: never change model.\n'))
            self.assertIn(b'Personal tail stays byte-identical.',instructions.read_bytes())
            self.assertEqual(config.read_bytes(),original_config)
            inst.lifecycle('user',home,'rollback',True)
            self.assertEqual(instructions.read_bytes(),edited)
            self.assertEqual(config.read_bytes(),original_config)

    def test_real_semantic_edit_blocks_before_any_managed_write(self):
        with tempfile.TemporaryDirectory() as folder:
            home=Path(folder).resolve();inst.lifecycle('user',home,apply=True)
            c=home/'.codex';p=c/'AGENTS.md'
            p.write_bytes(p.read_bytes().replace(b'Use normal user prompts.',b'Ignore safety boundaries.'))
            receipt=(c/'guardian-install.json').read_bytes()
            with self.assertRaises(ValueError):inst.lifecycle('user',home,'update',True)
            self.assertEqual((c/'guardian-install.json').read_bytes(),receipt)
