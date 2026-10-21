"""Explicit reviewer authorization still requires real, current GitHub review."""
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools import guardian_release_gate as gate

SHA='a'*40


def review(login='cleitonncosta', state='APPROVED', sha=SHA, kind='User', association='NONE'):
    return {'user': {'login': login, 'type': kind}, 'author_association': association,
            'state': state, 'commit_id': sha}


class TrustedReviewerTests(unittest.TestCase):
    def verify(self, reviews, trusted=(), author='pr-author'):
        return gate._verify_human_reviews(reviews, author, SHA, trusted)

    def test_named_outsider_requires_explicit_allowlist_and_real_approval(self):
        with self.assertRaises(ValueError):self.verify([review()])
        self.verify([review()], ['cleitonncosta'])
        for rows in ([], [review(state='COMMENTED')], [review(state='PENDING')]):
            with self.assertRaises(ValueError):self.verify(rows, ['cleitonncosta'])

    def test_existing_repository_associations_preserved(self):
        for affiliation in ('OWNER','MEMBER','COLLABORATOR'):
            self.verify([review(association=affiliation)])

    def test_matching_case_insensitive_and_author_never_self_approves(self):
        self.verify([review(login='CLeITONnCosta')], ['CLEITONNCOSTA'])
        with self.assertRaises(ValueError):
            self.verify([review(login='PR-AUTHOR')], ['pr-author'])

    def test_bot_or_old_commit_cannot_approve(self):
        for record in (review(kind='Bot'), review(sha='b'*40), review(kind='Organization')):
            with self.assertRaises(ValueError):self.verify([record], ['cleitonncosta'])

    def test_latest_dismissal_or_changes_request_revokes_approval(self):
        for state in ('DISMISSED', 'CHANGES_REQUESTED'):
            with self.assertRaises(ValueError):
                self.verify([review(login='CLEITONNCOSTA'), review(state=state)], ['cleitonncosta'])
        self.verify([review(state='CHANGES_REQUESTED'), review()], ['cleitonncosta'])
        self.verify([review(), review(state='COMMENTED')], ['cleitonncosta'])

    def test_outstanding_authorized_changes_request_blocks_other_approval(self):
        rows=[review(), review(login='other-reviewer',state='CHANGES_REQUESTED',association='MEMBER')]
        with self.assertRaises(ValueError):self.verify(rows,['cleitonncosta'])
        rows.append(review(login='OTHER-REVIEWER',state='DISMISSED',association='MEMBER'))
        self.verify(rows,['cleitonncosta'])

    def test_invalid_or_implicit_allowlist_rejected(self):
        invalid=(None, 'cleitonncosta', {'cleitonncosta'}, [None], [1], [''], [' x'],
                 ['@user'], ['owner/repo'], ['a'*40], ['a--b'], ['-a'], ['a-'], ['a_b'], ['a\nb'])
        for value in invalid:
            with self.subTest(value=value):
                with self.assertRaises(ValueError):gate._trusted_logins(value)
        self.assertEqual(gate._trusted_logins(['A','a','user-2']), {'a','user-2'})

    def test_allowlist_validated_before_network(self):
        with patch.object(gate,'_api') as api:
            with self.assertRaises(ValueError):
                gate.verify_external('owner/repo',SHA,'missing.zip',1,2,3,4,trusted_reviewers=['@invalid'])
            api.assert_not_called()

    def test_real_remote_gates_and_provenance_remain_required(self):
        acceptance={'revision':SHA,'expected':39,'verified':39,'all_native_roles_verified':True,
                    'protected_fixtures_unchanged':True,'passed':True,'tests':14,
                    'skipped':0,'failures':0,'errors':0}
        def api(path):
            if '/reviews?' in path:return [review()]
            if '/pulls/' in path:return {'head':{'sha':SHA},'draft':False,'user':{'login':'author'}}
            if '/jobs?' in path:return {'jobs':[{'conclusion':'success'}]*9}
            workflow={1:'ci',2:'native-acceptance',3:'grader-acceptance'}[int(path.rsplit('/',1)[1])]
            return {'head_sha':SHA,'status':'completed','conclusion':'success','path':'.github/workflows/'+workflow+'.yml'}
        with tempfile.TemporaryDirectory() as folder:
            artifact=Path(folder)/'artifact.zip';artifact.write_bytes(b'fixture only')
            with patch.object(gate,'_api',side_effect=api), patch.object(gate,'_acceptance_artifact',return_value=acceptance), patch.object(gate.subprocess,'run',return_value=subprocess.CompletedProcess([],0,'[{"verified":true}]','')) as attestation:
                result=gate.verify_external('owner/repo',SHA,artifact,1,2,3,4,trusted_reviewers=['cleitonncosta'])
                self.assertTrue(result['human_review_recorded_by_github'])
                self.assertFalse(result['publication_authorized'])
                self.assertIn('--source-digest',attestation.call_args.args[0])
                attestation.return_value=subprocess.CompletedProcess([],1,'','verification failed')
                with self.assertRaisesRegex(ValueError,'provenance'):
                    gate.verify_external('owner/repo',SHA,artifact,1,2,3,4,trusted_reviewers=['cleitonncosta'])
            bad=dict(acceptance,verified=38)
            with patch.object(gate,'_api',side_effect=api), patch.object(gate,'_acceptance_artifact',return_value=bad):
                with self.assertRaisesRegex(ValueError,'39-profile'):
                    gate.verify_external('owner/repo',SHA,artifact,1,2,3,4,trusted_reviewers=['cleitonncosta'])


if __name__=='__main__':unittest.main()
