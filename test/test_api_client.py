import os
import tempfile
import unittest
from src.api.api_client import LalalAIClient


def _fake_response(status_code=200, json_data=None, text=None):
    class FakeResp:
        def __init__(self, status_code, json_data, text=None):
            self.status_code = status_code
            self._json = json_data or {}
            self.text = text or str(self._json)

        def json(self):
            return self._json

    return FakeResp(status_code, json_data, text)


class TestLalalAIClient(unittest.TestCase):
    def test_headers_and_base_url(self):
        client = LalalAIClient("pk_test_key")
        self.assertIn('X-License-Key', client.session.headers)
        self.assertEqual(client.session.headers['X-License-Key'], 'pk_test_key')
        self.assertTrue(client.BASE_URL.endswith('/api/v1/'))

    def test_list_voice_packs_parsing(self):
        client = LalalAIClient("pk_test_key")

        def fake_post(url, json=None, timeout=None):
            return _fake_response(200, {'packs': [{'pack_id': 'ALEX_KAYE', 'ready_to_use': True}]})

        client.session.post = fake_post
        packs = client.list_voice_packs()
        self.assertIsInstance(packs, dict)
        self.assertIn('packs', packs)
        self.assertEqual(len(packs['packs']), 1)

    def test_check_job_status_v1_and_legacy(self):
        client = LalalAIClient("pk_test_key")

        # v1-style response
        v1_payload = {
            'result': {
                'task-1': {
                    'status': 'success',
                    'result': {
                        'tracks': [
                            {'label': 'stem_track', 'url': 'https://example.com/stem.mp3'},
                            {'label': 'back_track', 'url': 'https://example.com/back.mp3'}
                        ],
                        'duration': 3.2
                    }
                }
            }
        }

        client.session.post = lambda url, json=None, timeout=None: _fake_response(200, v1_payload)
        status, result = client.check_job_status('task-1')
        self.assertEqual(status, 'completed')
        self.assertEqual(result.get('stem_track'), 'https://example.com/stem.mp3')

        # legacy-style response
        legacy_payload = {
            'result': {
                'abc123': {
                    'task': {'state': 'success'},
                    'split': {'stem_track': 'https://example.com/legacy_stem.mp3', 'duration': 4.0}
                }
            }
        }

        client.session.post = lambda url, json=None, timeout=None: _fake_response(200, legacy_payload)
        status2, result2 = client.check_job_status('abc123')
        self.assertEqual(status2, 'completed')
        self.assertEqual(result2.get('stem_track'), 'https://example.com/legacy_stem.mp3')

    def test_upload_file_parsing(self):
        client = LalalAIClient("pk_test_key")
        # create a small temp file
        fd, path = tempfile.mkstemp()
        os.close(fd)
        with open(path, 'wb') as f:
            f.write(b"test")

        # fake upload response
        client.session.post = lambda url, data=None, headers=None, timeout=None: _fake_response(200, {'id': 'src-123', 'status': 'success'})
        file_id = client.upload_file(path)
        self.assertEqual(file_id, 'src-123')

        os.remove(path)

    def test_process_voice_cleanup_maps_voice_to_vocals(self):
        client = LalalAIClient("pk_test_key")
        captured = {}

        def fake_post(url, json=None, timeout=None, **kwargs):
            captured['url'] = url
            captured['json'] = json
            return _fake_response(200, {'task_id': 'task-123'})

        client.session.post = fake_post
        task_id = client.process_voice_cleanup("src-1", stem='voice', noise_cancelling=2)
        # client should use the dedicated voice_clean endpoint for background-voice cleanup
        self.assertTrue(captured['url'].endswith('/split/voice_clean/'))
        # voice_clean expects literal 'voice' when the user requested 'voice'
        self.assertEqual(captured['json']['presets']['stem'], 'voice')
        # local noise_cancelling (0..2) should map to API-level (1..3): 2 -> 3
        self.assertEqual(captured['json']['presets']['noise_cancelling_level'], 3)
        self.assertEqual(task_id, 'task-123')

    def test_noise_cancelling_mapping_local_to_api(self):
        client = LalalAIClient("pk_test_key")
        captured = {}

        def fake_post(url, json=None, timeout=None, **kwargs):
            captured['json'] = json
            return _fake_response(200, {'task_id': 'task-xyz'})

        client.session.post = fake_post

        client.process_voice_cleanup("src-1", stem='voice', noise_cancelling=0)
        self.assertEqual(captured['json']['presets']['noise_cancelling_level'], 1)

        client.process_voice_cleanup("src-1", stem='voice', noise_cancelling=1)
        self.assertEqual(captured['json']['presets']['noise_cancelling_level'], 2)

        client.process_voice_cleanup("src-1", stem='voice', noise_cancelling=2)
        self.assertEqual(captured['json']['presets']['noise_cancelling_level'], 3)


if __name__ == '__main__':
    unittest.main()
