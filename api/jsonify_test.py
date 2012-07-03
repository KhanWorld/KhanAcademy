""" Unit tests for jsonify functionality """

import unittest
from jsonify import camel_casify, JSONModelEncoder, JSONModelEncoderCamelCased

class JsonifyTest(unittest.TestCase):
    def setUp(self):
        pass

    def test_camel_casing(self):
        self.assertEqual("", camel_casify(""))
        self.assertEqual("foo", camel_casify("foo"))
        self.assertEqual("fooBar", camel_casify("foo_bar"))
        self.assertEqual("fooBarJoeRalph", camel_casify("foo_bar_joe_ralph"))
        self.assertEqual("hypens-confuse-me", camel_casify("hypens-confuse-me"))
        self.assertEqual("trailingDoesntMatter_", camel_casify("trailing_doesnt_matter_"))

    o = {
        "one_two": ["buckle", "shoe"],
        "three_four": {"knock": "door"},
        "fivesix": "pickup sticks",
    }
    def test_normal_encoder(self):
        self.assertEqual(
                '{"one_two": ["buckle", "shoe"], "three_four": {"knock": "door"}, "fivesix": "pickup sticks"}',
                JSONModelEncoder().encode(self.o))

    def test_camel_casing_encoder(self):
        self.assertEqual(
                '{"oneTwo": ["buckle", "shoe"], "threeFour": {"knock": "door"}, "fivesix": "pickup sticks"}',
                JSONModelEncoderCamelCased().encode(self.o))

if __name__ == '__main__':
    unittest.main()
