#!/usr/bin/env python3

import sys
from argparse import ArgumentParser, Namespace
from pathlib import Path
from mmap import mmap
from functools import cmp_to_key

from util import ProgressBar, DiskBytesArray, DiskIntArray, DiskIntArrayBuilder
from sort import SortKey, insertion_sort, quicksort, median_of_three, random_pivot, take_first_pivot


###############################################################################
## Build the index

def build_suffix_array(textfile:Path, indexfile:Path, args:Namespace):
    """
    Find word start positions, and then sort them lexicographically.
    """
    collect_corpus_positions(textfile, indexfile)
    sort_suffix_array(textfile, indexfile, args.cutoff)
    test_sortedness(textfile, indexfile)


def collect_corpus_positions(textfile:Path, indexfile:Path):
    """
    Find all postitions in the `textfile` where a word starts,
    and add them to the `indexfile`.
    """
    
    with DiskBytesArray(textfile) as text:
        with DiskIntArrayBuilder(indexfile) as index:

            previous = ' '
            for i,char in enumerate(ProgressBar(text,desc='collecting_pos')):                        #keep count of the file position i   +  iterate over all bytes
                                                                #       !!!!!OBS!!!!!!     i is not the actual file position, just an int that follows at the "correct" position
                                                                #and isn't affected by text.read()

                                                                #text.read() automatically advances the file position(which byte we are looking at, starting at 0) by one.
                                                                #This is why we need to reset to the "correct" position i+1 at the end of each for loop, keep
                                                                #track of i, etc...
                if char.isalnum() and not previous.isalnum():
                    index.append(i)   
                previous = char
                """if bytes.isalpha(text.read(1)):                 #if current byte is alphanumerical   
                                                    
                    if i==0:                                    #small exception for the first byte, which doesn't have a byte before it to check
                        index.append(i)

                    text.seek(-2,1)                             #move to file position before position i ( https://docs.python.org/3/library/mmap.html to check how text.seek and other text.blablabla work)
                    if bytes.isalpha(text.read(1)) == False:   #check if byte before isn't alphanumerical (if it isn't, it means that  byte i is the beginning of a word, sinsce there are no letters before it)
                        index.append(i)
                text.seek(i+1)"""                                  #move to the "actual" next byte


###############################################################################
## Sorting

def sort_suffix_array(textfile:Path, indexfile:Path, cutoff:int):
    """
    Sorts the index file alphabetically according to positions in the text file.
    """
    with DiskBytesArray(textfile) as text:
        with DiskIntArray(indexfile) as suffixarray:
            quicksort(suffixarray, take_prefix(text), median_of_three)
            insertion_sort(suffixarray, exact_compare(text))

# 100 works fine for both CPython and PyPy
COMPARE_BUFFER_SIZE = 100


def take_prefix(text:mmap) -> SortKey:
    """
    Creates a sort key that returns {COMPARE_BUFFER_SIZE} bytes.
    """
    def key(pos:int) -> bytes:
        return text[pos:pos+COMPARE_BUFFER_SIZE]
    return key


def exact_compare(text:mmap) -> SortKey:
    """
    Creates a sort key that compares text positions exactly
    (much slower than `take_prefix`).
    """
    def key(pos1:int, pos2:int) -> int:
        if pos1 == pos2: return 0
        while True:
            bytes1 = text[pos1:pos1+COMPARE_BUFFER_SIZE]
            bytes2 = text[pos2:pos2+COMPARE_BUFFER_SIZE]
            if bytes1 != bytes2:
                return -1 if bytes1 < bytes2 else 1
            pos1 += COMPARE_BUFFER_SIZE
            pos2 += COMPARE_BUFFER_SIZE
    return cmp_to_key(key)


###############################################################################
## Testing

def test_sortedness(textfile:Path, indexfile:Path):
    """
    Tests that the index file is a correct suffix array for the text file.
    """
    errs = 0
    with DiskBytesArray(textfile) as text:
        with DiskIntArray(indexfile) as index:
            key = exact_compare(text)
            left = 0
            leftKey = key(left)
            for i, right in enumerate(ProgressBar(index[1:], desc="Testing sortedness"), 1):
                rightKey = key(right)
                if not leftKey < rightKey:
                    lstr = text[left : left+20]
                    rstr = text[right : right+20]
                    if errs < 10: 
                        print(f"# Error in position {i}:  {lstr}  >=  {rstr}", file=sys.stderr)
                    errs += 1
                left = right
                leftKey = rightKey
    if errs:
        sys.exit(f"{errs} ordering errors!")


###############################################################################
## Main function

def main(args:Namespace):
    indexfile : Path = args.textfile.with_suffix(args.suffix)
    build_suffix_array(args.textfile, indexfile, args)


SORTING_CUTOFF = 10_000
INDEX_SUFFIX = '.ix'

parser = ArgumentParser(description='Search tool for text files')
parser.add_argument('--suffix', default=INDEX_SUFFIX,
    help=f'suffix of index file (default: {INDEX_SUFFIX})')
parser.add_argument('--cutoff', type=int, default=SORTING_CUTOFF,
    help=f"cutoff when to resort to Python's built-in sort (default: {SORTING_CUTOFF:_d})")
parser.add_argument('textfile', type=Path,
    help='text file (utf-8 encoded)')


if __name__ == '__main__':
    main(parser.parse_args())

