from datetime import datetime
import sys


class _Logger:
    def __init__(self, stream, mng, time_format_str="[{}] "):
        self.stream = stream
        self.mng = mng
        self.time_format_str = time_format_str
    
    def write(self, text):
        if not text:
            return

        if isinstance(text, bytes):
            text = text.decode("utf-8")

        try:
            self.stream.write(text)
        except Exception as e:
            text += "\n" + str(e)

        time = datetime.now().strftime("%H:%M:%S")
        time = self.time_format_str.format(time)

        if self.mng.escflag:
            out = time
            self.mng.escflag = False
        else:
            out = ""
        
        if text.endswith("\n"):
            self.mng.escflag = True
            text = text[:-1]
        
        out += ("\n" + time).join(text.split("\n"))
        if self.mng.escflag:
            out += "\n"

        self.mng.log.write(out)
        self.mng.log.flush()
    
    def flush(self):
        self.mng.log.flush()

class _LoggerMng:
    def __init__(self, path):
        self.escflag = True
        self.log = open(path, "w")

        sys.stdout = _Logger(sys.stdout, self)
        sys.stderr = _Logger(sys.stderr, self, time_format_str=">>{} ")
    
    def __del__(self):
        self.log.close()

def init(path):
    _ = _LoggerMng(path)
