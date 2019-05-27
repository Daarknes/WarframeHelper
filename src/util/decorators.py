import inspect
import os
import time


def _func_info(func):
    path = os.path.relpath(inspect.getsourcefile(func))
    path, _ = os.path.splitext(path)
    return "{}.{}() ".format(path, func.__name__)

def print_info(*args, format_str=""):
    # decorator was used directly (@print_info)
    if len(args) == 1 and callable(args[0]):
        def wrapper(*fargs, **fkwargs):
            print("calling '{}' with arguments {}, {}. ".format(_func_info(args[0]), fargs, fkwargs) + format_str.format(*fargs, *fkwargs))
            return args[0](*fargs, **fkwargs)

        return wrapper
    # decorator was used with arguments (@print_info(format_str="..."))
    elif not args:
        def decorator(func):
            def wrapper(*fargs, **fkwargs):
                print("calling '{}' with arguments {}, {}. ".format(_func_info(func), fargs, fkwargs) + format_str.format(*fargs, *fkwargs))
                return func(*fargs, **fkwargs)

            return wrapper
        return decorator
    else:
        raise TypeError("{}() takes 0 positional arguments but {} was given".format(print_info.__name__, len(args)))


def printcaller(start=0, recursions=None):
    def decorator(func):
        def inner(*args, **kwargs):
            import traceback
            import sys
            print ("caller traceback for", _func_info(func))
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
            print("benchmark for", _func_info(func), ": {0:.3f} ms".format(duration))
        return res

    return timePrinter

def benchmarkName(name):
    return lambda func: benchmark(func, name=name)
