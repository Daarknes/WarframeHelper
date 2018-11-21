class ProgressBar():
    def __init__(self, width, max_val, fill_char="#"):
        self._width = width
        self._max_val = max_val
        self._fill_char = fill_char
        print("[" + width * "-" + "]", end="\r")

    def update(self, value):
        progress = int(value / self._max_val * self._width)
        perc = int(100 * value / self._max_val)

        bar_str = progress * self._fill_char +  (self._width-progress) * "-"
        
        print("\r|{}| {}%".format(bar_str, perc), end="\r")
        # Print New Line on Complete
        if value >= self._max_val:
            print()