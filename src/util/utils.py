import operator


def batch_iter(lst, size):
    """
    Generator that iterates over `lst` yielding batches of size (at most) `size`
    """
    for i in range(0, len(lst), size):
        yield lst[i : i+size]


def levenshtein_distance(s, t, costs=(1, 1, 1)):
    """ 
        iterative_levenshtein(s, t) -> ldist (int)
        ldist is the Levenshtein distance between the strings s and t.
        
        costs: a tuple or a list with three integers (d, i, s) where
                d defines the costs for a deletion
                i defines the costs for an insertion and
                s defines the costs for a substitution
    """
    rows = len(s)+1
    cols = len(t)+1
    deletes, inserts, substitutes = costs
    
    # For all i and j, dist[i,j] will contain the Levenshtein distance between the first i characters of s and the first j characters of t
    dist = [[0 for _ in range(cols)] for _ in range(rows)]
    # source prefixes can be transformed into empty strings 
    # by deletions:
    for row in range(1, rows):
        dist[row][0] = row * deletes
    # target prefixes can be created from an empty source string
    # by inserting the characters
    for col in range(1, cols):
        dist[0][col] = col * inserts
        
    for col in range(1, cols):
        for row in range(1, rows):
            if s[row-1] == t[col-1]:
                cost = 0
            else:
                cost = substitutes
            dist[row][col] = min(dist[row-1][col] + deletes,
                                 dist[row][col-1] + inserts,
                                 dist[row-1][col-1] + cost) # substitution    
 
    return dist[rows-1][cols-1]


def _op(value1, value2, func):
    if isinstance(value1, NoneFloat):
        value1 = value1._value
    elif isinstance(value2, NoneFloat):
        value2 = value2._value
    
    if value1 is None or value2 is None:
        return NoneFloat()
    else:
        return NoneFloat(func(value1, value2))

class NoneFloat:
    def __init__(self, value=None):
        self._value = value
    
    @property
    def value(self):
        return self._value
        
    def __neg__(self):
        return NoneFloat(-self._value) if self._value is not None else NoneFloat()
        
    def __add__(self, other):
        return _op(self, other, operator.add)
    
    def __radd__(self, other):
        return _op(other, self, operator.add)

    def __sub__(self, other):
        return _op(self, other, operator.sub)
        
    def __rsub__(self, other):
        return _op(other, self, operator.sub)
    
    def __truediv__(self, other):
        return _op(self, other, operator.truediv)
    
    def __rtruediv__(self, other):
        return _op(other, self, operator.truediv)
    
    def __div__(self, other):
        return _op(self, other, operator.floordiv)
    
    def __rdiv__(self, other):
        return _op(other, self, operator.floordiv)
    
    def __round__(self, decimals):
        return NoneFloat() if self._value is None else NoneFloat(self._value.__round__(decimals))
    
    def __str__(self):
        return str(self._value)
    
    def __repr__(self):
        return "NoneFloat({})".format(self._value)
    
    def __format__(self, params):
        return str(None) if self._value is None else self._value.__format__(params)
