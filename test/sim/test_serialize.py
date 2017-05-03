import os
import sys
import unittest

parent_directory = os.path.abspath(os.path.join(sys.path[0], os.pardir))
sys.path.insert(0, parent_directory)

import stengel.sim.serialize as serialize


class SerializerTestClass(serialize.DictSerialize):
    unpassed_attributes = ["c"]

    def __init__(self, a, b):
        self.a = a
        self.b = b
        self.c = a * 3


class SerializerTestSuperClass(serialize.DictSerialize):
    attribute_objects = ["f"]

    def __init__(self, e, f=None):
        self.e = e
        self.f = f

    @staticmethod
    def _from_dict_f(dict_):
        return SerializerTestClass.from_dict(dict_)


class TestSerialization(unittest.TestCase):
    def test_to_dict(self):
        obj = SerializerTestClass(2, 3)
        self.assertEqual(obj.as_dict(), {"a": 2, "b": 3, "c": 6})

    def test_from_dict(self):
        obj = SerializerTestClass.from_dict({"a": 2, "b": 3, "c": 5})
        self.assertEqual(obj.__dict__, SerializerTestClass(2, 3).__dict__)

    def test_to_dict_with_recursion(self):
        sub_obj = SerializerTestClass(4, 5)
        obj = SerializerTestSuperClass(7, sub_obj)
        self.assertEqual(obj.as_dict(), {"e": 7, "f": {"a": 4, "b": 5, "c": 12}})

    def test_from_dict_with_recursion(self):
        dict_obj = SerializerTestSuperClass.from_dict({"e": 7, "f": {"a": 4, "b": 5}})
        direct_obj = SerializerTestSuperClass(7, SerializerTestClass(4, 5))
        # We can't directly compare the dict as easily here (since the sub-objects won't
        # match), but we can go piecemeal...
        self.assertEqual(dict_obj.e, direct_obj.e)
        self.assertEqual(dict_obj.f.__dict__, direct_obj.f.__dict__)

    def test_to_dict_with_missing_recursion(self):
        obj = SerializerTestSuperClass(11)
        self.assertEqual(obj.as_dict(), {"e": 11})

    def test_from_dict_with_missing_recursion(self):
        obj = SerializerTestSuperClass(17)
        self.assertEqual(obj.as_dict(), {"e": 17, })
