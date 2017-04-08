from __future__ import (absolute_import, division,
                        print_function, unicode_literals)

import copy


class DictSerialize(object):
    """Mixin for objects that will serialize themselves as dicts.

    This mixin will serialize the instance variables (and only the instance variables) of
    the object, and will also serialize sub-objects recursively.

    Instance variables:
        object_type: Type of the object, including module.
    Class variables:
        attribute_objects: A list of strings, each of which is an attribute that itself
            is an object that should be serialized as a dictionary.
        unpassed_attributes: A list of strings, each of which is an attribute that is
            included in the serialization, but which should not be passed as an argument
            to the object's constructor.
    """

    attribute_objects = []
    unpassed_attributes = ["event_type"]

    def __init__(self):
        pass

    def as_dict(self):
        """Convert an object to a dictionary representation."""
        object_dict = copy.deepcopy(self.__dict__)
        # Convert the attribute objects to dictionaries recursively.
        for k in object_dict.keys():
            if k in self.attribute_objects:
                object_dict[k] = object_dict[k].as_dict()
        return object_dict

    @classmethod
    def from_dict(cls, dict_):
        """Instantiate an object from a dictionary representation of itself."""
        dict_ = copy.deepcopy(dict_)
        for attribute in dict_.keys():
            # Convert the attribute objects from dictionaries back to objects. For each
            # attribute object, the parent object should have a corresponding class method
            # called _from_dict_[name_of_attribute_object] that's a wrapper around
            # [class_of_attribute_object].from_dict().
            if attribute in cls.attribute_objects and dict_[attribute]:
                dict_[attribute] = getattr(cls, "_from_dict_" + attribute)(dict_[attribute])
            elif attribute in cls.unpassed_attributes:
                del dict_[attribute]
        return cls(**dict_)
