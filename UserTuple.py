"""A more or less complete user-defined wrapper around tuple objects.
Adopted version of the standard library's UserList."""

#XXX tuple instances (in Python 2.2) contain also:
# __class__, __delattr__, __getattribute__, __hash__, __new__,
# __reduce__, __setattr__, __str__

class UserTuple:
    def __init__(self, inittuple=None):
        self.data = ()
        if inittuple is not None:
            # XXX should this accept an arbitrary sequence?
            if type(inittuple) == type(self.data):
                self.data = inittuple
            elif isinstance(inittuple, UserTuple):
                # this results in
                #   self.data is inittuple.data
                # but that's ok for tuples because they are
                # immutable. (Builtin tuples behave the same.)
                self.data = inittuple.data[:]
            else:
                # same applies here
                self.data = tuple(inittuple)
    def __repr__(self): return repr(self.data)
    def __lt__(self, other): return self.data <  self.__cast(other)
    def __le__(self, other): return self.data <= self.__cast(other)
    def __eq__(self, other): return self.data == self.__cast(other)
    def __ne__(self, other): return self.data != self.__cast(other)
    def __gt__(self, other): return self.data >  self.__cast(other)
    def __ge__(self, other): return self.data >= self.__cast(other)
    def __cast(self, other):
        if isinstance(other, UserTuple): return other.data
        else: return other
    def __cmp__(self, other):
        return cmp(self.data, self.__cast(other))
    def __contains__(self, item): return item in self.data
    def __len__(self): return len(self.data)
    def __getitem__(self, i): return self.data[i]
    def __getslice__(self, i, j):
        i = max(i, 0); j = max(j, 0)
        return self.__class__(self.data[i:j])
    def __add__(self, other):
        if isinstance(other, UserTuple):
            return self.__class__(self.data + other.data)
        elif isinstance(other, type(self.data)):
            return self.__class__(self.data + other)
        else:
            return self.__class__(self.data + tuple(other))
    # dir( () ) contains no __radd__ (at least in Python 2.2)
    def __mul__(self, n):
        return self.__class__(self.data*n)
    __rmul__ = __mul__
