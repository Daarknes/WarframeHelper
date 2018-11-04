import inspect
import os
import time


def _funcInfo(func):
    fileName = os.path.relpath(inspect.getsourcefile(func))
    return "\"{}\" ({})".format(func.__name__, fileName)

def printcaller(start=0, recursions=None):
    def decorator(func):
        def inner(*args, **kwargs):
            import traceback
            import sys
            print ("caller traceback for", _funcInfo(func))
            traceback.print_stack(sys._getframe(1 + start), limit=recursions)
            return func(*args, **kwargs)

        return inner

    return decorator

def benchmark(func, name=""):
    def timePrinter(*args, **kwargs):
        start = time.clock()
        res = func(*args, **kwargs)
        duration = (time.clock() - start) * 1000.0
        if name:
            print("benchmark for", name, ": {0:.3f} ms".format(duration))
        else:
            print("benchmark for", _funcInfo(func), ": {0:.3f} ms".format(duration))
        return res

    return timePrinter

def benchmarkName(name):
    return lambda func: benchmark(func, name=name)
