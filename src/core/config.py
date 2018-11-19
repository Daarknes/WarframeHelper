import os


section_str = """#===============================================================================
# {}
#===============================================================================
"""

class Config():
    def __init__(self):
        self._sections = []
        self._defaults = {}
        self._entries = {}
    
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
        
        if not os.path.exists(path):
            for key, value in self._defaults.items():
                self._entries[key] = value
            self._save(path)
            return

        with open(path, "r") as f:
            raw_data = f.read()

        needsSave = False
         
        for line in raw_data.split("\n"):
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            key, value = line.split("=")
            key = key.strip()
            if key not in self._defaults:
                needsSave = True
                continue
            
            value = value.strip()
            vType = type(self._defaults[key])
            if vType == bool:
                value = value == "True"
            else:
                value = vType(value)

            self._entries[key] = value
        
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

class _ConfigSection():
    def __init__(self, name):
        self.name = name
        self.entries = []

    def addEntry(self, key, value, comment):
        self.entries.append(_ConfigEntry(key, value, comment))

class _ConfigEntry():
    def __init__(self, key, value, comment):
        self.key = key
        self.value = value
        self.comment = comment
    
    def __str__(self):
        return (self.key, self.value, self.comment)
