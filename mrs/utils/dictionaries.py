""" Slightly adapted from:
https://realpython.com/inheritance-composition-python/#mixing-features-with-mixin-classes
"""
import uuid


class AsDictMixin:

    def to_dict(self):
        return {
            prop: self._represent(value)
            for prop, value in self.__dict__.items()
            if not self.is_internal(prop)
        }

    @classmethod
    def _represent(cls, value):
        if isinstance(value, object):
            if hasattr(value, 'to_dict'):
                return value.to_dict()
            elif isinstance(value, uuid.UUID):
                return str(value)
            else:
                return value
        else:
            return value

    @staticmethod
    def is_internal(prop):
        return prop.startswith('_')

    @classmethod
    def from_dict(cls, info_dict):
        attrs = dict()
        for key, value in info_dict.items():
            attrs[key] = AsDictMixin._get_value(key, value)

        return cls(**attrs)

    @staticmethod
    def _get_value(key, value):
        if isinstance(key, object):
            if hasattr(key, 'from_dict'):
                return key.from_dict()
            else:
                return value
        else:
            return value
