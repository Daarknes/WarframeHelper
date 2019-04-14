class ProgressBar():
    def __init__(self, width, max_val, fill_char="#"):
        self._width = width
        self._max_val = max_val
        self._fill_char = fill_char
        self._value = 0
        print("|" + width * "-" + "| 0%", end="\r")

    def update(self):
        self._value += 1
        progress = int(self._value / self._max_val * self._width)
        perc = int(100 * self._value / self._max_val)

        bar_str = progress * self._fill_char +  (self._width-progress) * "-"
        
        print("|{}| {}%".format(bar_str, perc), end="\r")
        # Print New Line on Complete
        if self._value == self._max_val:
            print()
        elif self._value > self._max_val:
            raise Exception("can't update progress bar over the max_value")