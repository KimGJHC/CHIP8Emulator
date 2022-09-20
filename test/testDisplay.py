import unittest2
from chip8.display import Display

class TestDisplay(unittest2.TestCase):

    def setUp(self):
        self.display = Display()