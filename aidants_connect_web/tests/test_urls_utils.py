from unittest import TestCase

from aidants_connect_common.utils.urls import join_url_parts


class TestUtils(TestCase):
    def test_join_url_parts(self):
        base = "https://example.org"
        self.assertEqual(base, join_url_parts(base))
        self.assertEqual(f"{base}/", join_url_parts(f"{base}/"))
        self.assertEqual(f"{base}/path", join_url_parts(base, "path"))
        self.assertEqual(f"{base}/path", join_url_parts(f"{base}/", "path"))
        self.assertEqual(f"{base}/path", join_url_parts(f"{base}/", "/path"))
        self.assertEqual(f"{base}/path/", join_url_parts(base, "/path/"))
        self.assertEqual(f"{base}/path/", join_url_parts(base, "path/"))
        self.assertEqual(f"{base}/path/", join_url_parts(f"{base}/", "/path/"))
        self.assertEqual(
            f"{base}/path/path2", join_url_parts(f"{base}/", "/path/", "path2")
        )
        self.assertEqual(
            f"{base}/path/path2/", join_url_parts(f"{base}/", "/path/", "path2/")
        )
        self.assertEqual(
            f"{base}/path/path2/", join_url_parts(f"{base}/", "/path/", "/path2/")
        )
