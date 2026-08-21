import unittest

from core.midi_text import decode_midi_text


class MidiTextDecodeTests(unittest.TestCase):
    @staticmethod
    def latin1_wrapper(text: str, encoding: str) -> str:
        return text.encode(encoding).decode("latin1")

    def test_ascii_is_unchanged(self):
        self.assertEqual(decode_midi_text("Piano Track"), "Piano Track")

    def test_utf8_chinese_track_name(self):
        source = "主旋律（钢琴）"
        self.assertEqual(decode_midi_text(self.latin1_wrapper(source, "utf-8")), source)

    def test_gb18030_chinese_track_name(self):
        source = "左手伴奏"
        self.assertEqual(decode_midi_text(self.latin1_wrapper(source, "gb18030")), source)

    def test_big5_chinese_track_name(self):
        source = "鋼琴主旋律"
        self.assertEqual(decode_midi_text(self.latin1_wrapper(source, "big5")), source)


if __name__ == "__main__":
    unittest.main()
