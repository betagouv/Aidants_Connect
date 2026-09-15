from django.test import TestCase, override_settings


class SearchEngineIndexingTests(TestCase):
    @override_settings(ALLOW_SEARCH_ENGINE_INDEXING=False)
    def test_robots_txt_allows_crawl_when_indexing_disabled(self):
        response = self.client.get("/robots.txt")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/plain")
        self.assertIn("Allow: /", response.content.decode())
        self.assertNotIn("Disallow:", response.content.decode())

    @override_settings(ALLOW_SEARCH_ENGINE_INDEXING=True)
    def test_robots_txt_allows_all_when_indexing_enabled(self):
        response = self.client.get("/robots.txt")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content.decode(), "User-agent: *\nAllow: /\n")

    @override_settings(ALLOW_SEARCH_ENGINE_INDEXING=False)
    def test_x_robots_tag_header_when_indexing_disabled(self):
        response = self.client.get("/")
        self.assertEqual(response["X-Robots-Tag"], "noindex, nofollow")
        self.assertContains(
            response, 'name="robots" content="noindex, nofollow"', html=False
        )

    @override_settings(ALLOW_SEARCH_ENGINE_INDEXING=True)
    def test_no_x_robots_tag_header_when_indexing_enabled(self):
        response = self.client.get("/")
        self.assertNotIn("X-Robots-Tag", response)
        self.assertNotContains(
            response, 'name="robots" content="noindex, nofollow"', html=False
        )
