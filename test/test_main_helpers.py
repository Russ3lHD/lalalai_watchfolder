import unittest

from main import map_stem_for_ui


class TestMainHelpers(unittest.TestCase):
    def test_map_stem_for_ui_maps_vocals_to_voice(self):
        self.assertEqual(map_stem_for_ui('vocals'), 'voice')
        self.assertEqual(map_stem_for_ui('voice'), 'voice')
        self.assertEqual(map_stem_for_ui('drum'), 'drum')


if __name__ == '__main__':
    unittest.main()
