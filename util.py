
import sys
import time
from pathlib import Path
from mmap import mmap
from typing import BinaryIO, Any, Iterator, Iterable
from types import TracebackType


###############################################################################
## External array of bytes

class DiskBytesArray:
    """
    A class for treating a binary file as a (fixed-size) array of bytes.
    """
    _file : BinaryIO
    _mmap : mmap

    def __init__(self, path:Path):
        self._file = open(path, 'r+b')
        self._mmap = mmap(self._file.fileno(), 0)

    def __enter__(self) -> mmap:
        return self._mmap

    def __exit__(self, exc_type:BaseException, exc_val:BaseException, exc_tb:TracebackType):
        self._mmap.close()
        self._file.close()


###############################################################################
## External array of integers

class DiskIntArray:
    """
    A class for treating a binary file as a (fixed-size) array of 4-byte unsigned integers.
    """
    # The typecodes for unsigned integers: B (1-byte), H (2-byte), I (4-byte), Q (8-byte)
    typecode = 'I'  # Capital typecode means unsigned integer
    elemsize =  4   # We use 4-byte integers

    _file : BinaryIO
    _view : memoryview

    def __init__(self, path:Path):
        self._file = open(path, 'r+b')
        self._view = memoryview(mmap(self._file.fileno(), 0)).cast(self.typecode)

    def __enter__(self) -> memoryview:
        return self._view

    def __exit__(self, exc_type:BaseException, exc_val:BaseException, exc_tb:TracebackType):
        self._view.release()
        self._file.close()


class DiskIntArrayBuilder:
    """
    A class for building a DiskIntArray by appending integers to the end of the file.
    """
    _file : BinaryIO

    def __init__(self, path:Path):
        self._file = open(path, 'w+b')

    def __enter__(self) -> 'DiskIntArrayBuilder':
        return self

    def __exit__(self, exc_type:BaseException, exc_val:BaseException, exc_tb:TracebackType):
        self._file.close()

    def append(self, value:int):
        self._file.write(value.to_bytes(DiskIntArray.elemsize, byteorder=sys.byteorder))


###############################################################################
## Logging

class ProgressBar:
    """
    A simple progress bar, inspired by the `tqdm` module.
    For "real" programs, you should install `tqdm` instead.
    """
    visible : bool = True  # class-variable to turn on/off all progress bars

    iter : Iterator
    desc : str
    start : float
    total : int
    n : int
    interval : int
    barwidth : int
    unit : int
    unit_suffix : str

    def __init__(self, iterable:Iterable=(), desc:str="Logging", total:int=0, barwidth:int=20, unit=1000):
        self.start = time.time()
        self.iter = iter(iterable)
        self.desc = desc
        self.total = total
        if not self.total:
            self.total = len(iterable)  # type: ignore
        self.barwidth = barwidth
        self.n = 0
        self.interval = max(1, min(self.total//200, 100))
        assert unit in (1, 1000, 1_000_000), "Can only handle unit == 1 or 1000 or 1_000_000"
        self.unit = unit
        self.unit_suffix = (
            ' ' if unit == 1 else
            'k' if unit == 1000 else
            'M' if unit == 1_000_000 else
            '#'
        )
        self._print_infoline()

    def __iter__(self):
        return self

    def __next__(self):
        try:
            el = next(self.iter)
        except StopIteration:
            self._print_infoline()
            self._close_infoline()
            raise
        self.n += 1
        if self.n % self.interval == 0:
            self._print_infoline()
        return el

    def __enter__(self):
        return self

    def __exit__(self, exc_type:BaseException, exc_val:BaseException, exc_tb:TracebackType):
        self._print_infoline()
        self._close_infoline()
        pass

    def update(self, add):
        self.n += add
        if self.n % self.interval == 0:
            self._print_infoline()

    def _print_infoline(self):
        if ProgressBar.visible:
            if self.total == 0:
                percent = 0
            else:
                percent = self.n / self.total
            hashes = round(percent * self.barwidth)
            pbar = '[' + '=' * hashes + '·' * (self.barwidth-hashes) + ']'
            elapsed = time.time() - self.start
            print(f"{self.desc:20s} {percent:4.0%} {pbar} {self.n/self.unit:6.0f}{self.unit_suffix} "
                f"of {self.total/self.unit:.0f}{self.unit_suffix}  | {elapsed:6.1f} s",
                file=sys.stderr, end='\r', flush=True)

    def _close_infoline(self):
        if ProgressBar.visible:
            print(file=sys.stderr)


###############################################################################
## Debugging

class ComparableWithCounter:
    """
    A wrapper class for comparing that tracks how many times we call a comparator.
    Note: This makes the comparator 5-10 times slower, so it should only be
    used for debugging!
    """
    val : Any
    instantiations : int = 0
    comparisons : int = 0

    def __init__(self, n:Any):
        self.val = n
        ComparableWithCounter.instantiations += 1
    def __lt__(self, other:'ComparableWithCounter') -> bool:
        ComparableWithCounter.comparisons += 1
        return self.val < other.val
    def __le__(self, other:'ComparableWithCounter') -> bool:
        ComparableWithCounter.comparisons += 1
        return self.val <= other.val
    def __gt__(self, other:'ComparableWithCounter') -> bool:
        ComparableWithCounter.comparisons += 1
        return self.val > other.val
    def __ge__(self, other:'ComparableWithCounter') -> bool:
        ComparableWithCounter.comparisons += 1
        return self.val >= other.val
    def __eq__(self, other:object) -> bool:
        ComparableWithCounter.comparisons += 1
        return isinstance(other, ComparableWithCounter) and self.val == other.val
    def __ne__(self, other:object) -> bool:
        return not (self == other)
    def __str__(self):
        return str(self.val)
    def __repr__(self):
        return repr(self.val)


def print_suffix_array(textfile:Path, indexfile:Path, num:int=5):
    """
    Print a (portion of a) suffix array, used for debugging.
    """
    with DiskBytesArray(textfile) as text:
        with DiskIntArray(indexfile) as index:
            def print_line(i:int, ptr:int):
                s = text[ptr:ptr+20].decode(errors='replace').replace('\n', ' ')
                print(f"{i:8d}. {ptr:8d}: {s}")

            size = len(index)
            print("-" * 40)
            for i in range(num): 
                print_line(i, index[i])
            print("     ...")
            for i in range(size//2, size//2 + num): 
                print_line(i, index[i])
            print("     ...")
            for i in range(size - num, size): 
                print_line(i, index[i])
            print("-" * 40)

