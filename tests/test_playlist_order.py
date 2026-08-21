import unittest

from core.playlist_order import build_reordered_ids


class PlaylistOrderTests(unittest.TestCase):
    def test_single_item_moves_to_top_middle_and_bottom(self):
        original = ["a", "b", "c", "d"]
        self.assertEqual(build_reordered_ids(original, ["c"], 0), ["c", "a", "b", "d"])
        self.assertEqual(build_reordered_ids(original, ["a"], 3), ["b", "c", "a", "d"])
        self.assertEqual(build_reordered_ids(original, ["a"], 4), ["b", "c", "d", "a"])

    def test_non_contiguous_multi_selection_moves_as_one_stable_block(self):
        original = ["a", "b", "c", "d", "e"]
        self.assertEqual(
            build_reordered_ids(original, ["d", "b"], 5),
            ["a", "c", "e", "b", "d"],
        )
        self.assertEqual(
            build_reordered_ids(original, ["b", "d"], 0),
            ["b", "d", "a", "c", "e"],
        )

    def test_invalid_or_duplicate_ids_are_rejected(self):
        with self.assertRaises(ValueError):
            build_reordered_ids(["a", "b"], [""], 1)
        with self.assertRaises(ValueError):
            build_reordered_ids(["a", "a"], ["a"], 1)
        with self.assertRaises(ValueError):
            build_reordered_ids(["a", "b"], ["c"], 1)


if __name__ == "__main__":
    unittest.main()
