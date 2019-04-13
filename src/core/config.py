import os
import re
from builtins import isinstance
import traceback
import sys


# TODO: rewrite this

section_str = """#===============================================================================
# {}
#===============================================================================
"""
_block_sym = r'"""'
block_pattern = re.compile(r'(.*?) *= *' + _block_sym + r'((?:.*?\n?)*)' + _block_sym)
pattern = re.compile(r"(\w+) *= *([^=\n]+)")

class FunctionBlock():
    def __init__(self, body, *params):
        self._body = body
        self._params = params
        self._fname = None
        
        code = "def func(" + ", ".join(params) + "):\n"
        for line in body.split("\n"):
            code += "  " + line + "\n"
        exec(code)
        self._func = eval("func")

    def __call__(self, *params):
        try:
            return self._func(*params)
        except:
            print("Traceback (most recent call last):", file=sys.stderr)
            # print caller info
            traceback.print_stack(sys._getframe(1))
            
            exc_type, exc_obj, exc_tb = sys.exc_info()
            tb = exc_tb
            while tb is not None:
                exc_tb = tb
                tb = tb.tb_next
            
            if self._fname is not None:
                print("  Traceback for function '{}':".format(self._fname), file=sys.stderr)
            
            lines = self._body.split("\n")
            lineno = exc_tb.tb_lineno - 2
            num_digits = len(str(len(lines)))
            
            for i, line in enumerate(lines):
                line = str(i).rjust(num_digits, " ") + " " + line
                if i == lineno:
                    line = "    -> " + line
                else:
                    line = "       " + line
                print(line, file=sys.stderr)

            print(*traceback.format_exception_only(exc_type, exc_obj), file=sys.stderr)
            sys.exit(1)

    def __str__(self):
        return _block_sym + self._body + _block_sym


class Config():
    def __init__(self):
        self._sections = []
        self._defaults = {}
        self._entries = {}
        self._func_locals = {}
    
    def addSection(self, name):
        section = _ConfigSection(name)
        self._sections.append(section)
        return section
    
    def __getitem__(self, key):
        return self._entries[key]
    
    def build(self):
        self._defaults.clear()
        for section in self._sections:
            for entry in section.entries:
                self._defaults[entry.key] = entry.value
 
    def loadAndUpdate(self, path):
        self._entries.clear()
        
        # when the config does not exist, fill self._entries with the default values and save it
        if not os.path.exists(path):
            for key, value in self._defaults.items():
                self._entries[key] = value
                # add FunctionBlocks to the globals dict to make all "functions" accessible
                if isinstance(value, FunctionBlock):
                    globals()[key] = value

            self._save(path)
            return

        with open(path, "r") as f:
            raw_data = f.read()
        needsSave = False

        while True:
            res = re.search(block_pattern, raw_data)
            if res is None:
                break
            
            key = res.group(1)
            raw_data = raw_data[:res.span()[0]] + raw_data[res.span()[1]+1:]
            
            # not an allowed key
            if key not in self._defaults:
                needsSave = True
                continue

            value = res.group(2)
            self._entries[key] = FunctionBlock(value, *self._defaults[key]._params)
            self._entries[key]._fname = key
            # add FunctionBlocks to the globals dict to make all "functions" accessible
            globals()[key] = self._entries[key]
        
        for key, value in re.findall(pattern, raw_data):
            # not an allowed key
            if key not in self._defaults:
                needsSave = True
                continue
            
            vType = type(self._defaults[key])
            if vType == bool:
                value = value == "True"
            else:
                value = vType(value)
            self._entries[key] = value
        
        # check if all default keys exist in the loaded config
        for key, value in self._defaults.items():
            if key not in self._entries:
                self._entries[key] = value
                needsSave = True
        
        if needsSave:
            self._save(path)
    
    def _save(self, path):
        raw_data = ""
        for section in self._sections:
            raw_data += section_str.format(section.name)

            for entry in sorted(section.entries, key=lambda entry: entry.key):
                raw_data += "# " + entry.comment + "\n"
                raw_data += entry.key + " = " + str(self._entries[entry.key]) + "\n\n"
                
        with open(path, "w") as f:
            f.write(raw_data)
    
    def __repr__(self):
        return repr(self._entries)

class _ConfigSection():
    def __init__(self, name):
        self.name = name
        self.entries = []

    def addEntry(self, key, value, comment):
        if isinstance(value, FunctionBlock):
            value._fname = key
            comment += " (PARAMS: " + ", ".join(value._params) + ")"
        else:
            comment += " (DEFAULT: " + str(value) + ")"
        self.entries.append(_ConfigEntry(key, value, comment))

class _ConfigEntry():
    def __init__(self, key, value, comment):
        self.key = key
        self.value = value
        self.comment = comment
    
    def __str__(self):
        return (self.key, self.value, self.comment)
