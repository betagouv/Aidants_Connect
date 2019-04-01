from selenium import webdriver
import unittest
import time

class NewVisitorConnection(unittest.TestCase):

    def setUp(self):
        self.browser = webdriver.Firefox()

    def tearDown(self):
        self.browser.quit()

    def test_page_loads(self):
        self.browser.get('http://localhost:8000')
        hello_world = self.browser.find_element_by_id("hello_world").text
        self.assertEqual(hello_world, "Hello, World")
