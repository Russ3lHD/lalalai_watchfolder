import unittest
import tempfile
from pathlib import Path
from src.core.folder_watcher import AudioFileHandler


class TestFolderWatcher(unittest.TestCase):
    def test_is_supported_audio_file_ignores_processed_suffixes(self):
        tmp = tempfile.TemporaryDirectory()
        base = Path(tmp.name)
        files = [
            "song.wav",
            "song_clean.wav",
            "song_clean_clean.wav",
            "song_converted.wav",
            "track.mp3",
            "note.txt",
        ]

        for f in files:
            p = base / f
            p.write_bytes(b"test")

        handler = AudioFileHandler(lambda x: None, {'wav', 'mp3'})

        self.assertTrue(handler._is_supported_audio_file(str(base / 'song.wav')))
        self.assertFalse(handler._is_supported_audio_file(str(base / 'song_clean.wav')))
        self.assertFalse(handler._is_supported_audio_file(str(base / 'song_clean_clean.wav')))
        self.assertFalse(handler._is_supported_audio_file(str(base / 'song_converted.wav')))
        self.assertTrue(handler._is_supported_audio_file(str(base / 'track.mp3')))
        self.assertFalse(handler._is_supported_audio_file(str(base / 'note.txt')))

        tmp.cleanup()
