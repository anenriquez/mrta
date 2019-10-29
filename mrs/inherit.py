# based on https://stackoverflow.com/questions/4295678/understanding-the-difference-between-getattr-and-getattribute

_marker = object()

class Parent(object):

    def __init__(self, x, y, z):
        self.x = x
        self.y = y
        self.z = z

class Child(Parent):

    _inherited = ['x', 'y', 'z']

    def __init__(self, parent):
        self._parent = parent
        self.a = "not got from dad"

    def __getattr__(self, name):
        print("Name: ", name)
        if name in self._inherited:
            # Get it from papa:
            try:
                return getattr(self._parent, name)
            except AttributeError:
                raise
                # if default is _marker:
                #     raise
                # return default

        if name not in self.__dict__:
            raise AttributeError(name)
        return self.__dict__[name]


if __name__ == '__main__':
    A = Parent('gotten', 'from', 'dad')
    B = Child(A)
    B.y
    # B.h
    # print("a, b and c is", B.x, B.y, B.z)
    #
    # print("But x is", B.a)
    #
    # A.x = "updated!"
    # print("And the child also gets", B.x)

