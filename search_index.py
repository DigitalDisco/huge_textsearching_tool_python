#!/usr/bin/env python3

from argparse import ArgumentParser, Namespace
from pathlib import Path
from mmap import mmap

from util import DiskIntArray, DiskBytesArray


################################################################################
## Search in text using index

def search_suffix_array(textfile:Path, indexfile:Path, args:Namespace):
    """
    Search for the search string `args.search_string` in the given text.
    Print at most `args.num_matches` number of matches.
    """
    with DiskBytesArray(textfile) as text:
        with DiskIntArray(indexfile) as index:
            search_key : bytes = args.search_string.encode()
            start : int = binary_search_first(search_key, index, text)
            list = []
            for i in range(start,len(index)):         
                if i-start >= args.num_matches:  
                    break
                word_index=index[i]
                word_end = word_index+len(search_key)
                if text[word_index:word_end] == search_key:
                    print_keyword_in_context(text,word_index,word_end, args)





def print_keyword_in_context(text:mmap, start:int, end:int, args:Namespace):
    """
    Print one match (between positions [start...end-1]),
    together with `args.context` bytes of context before and after.
    """
    context_start = max(0, start-args.context)
    context_end = min(len(text), end+args.context)

    prefix = text[context_start : start      ].decode(errors='ignore')
    found  = text[        start : end        ].decode(errors='ignore')
    suffix = text[          end : context_end].decode(errors='ignore')

    found = found.replace('\n', ' ').replace('\r', '')
    if args.trim_lines:
        _, _, prefix = prefix.rpartition('\n')
        suffix, _, _ = suffix.partition('\n')
    else:
        prefix = prefix.replace('\n', ' ').replace('\r', '')
        suffix = suffix.replace('\n', ' ').replace('\r', '')

    print(f"{start:8d}:  {prefix:>{args.context}s}|{found}|{suffix:<{args.context}s}")


def binary_search_first(search_key:bytes, index:memoryview, text:mmap) -> int:
    
    """
    Binary search for the search key in the suffix array,
    return the *first* occurrence of the search key.
    """
    high = len(index)-1
    low = 0
    mid = (low+high)//2
    
    while high-low>1:
        mid = (low+high)//2
        ptr = index[mid]
        ptr_key= text[ptr:ptr+len(search_key)]
        if search_key > ptr_key:
            low = mid+1
        else:
            high = mid
        
    if search_key == text[index[low]:index[low] + len(search_key)]:
        return low

    elif search_key == text[index[high]:index[high] + len(search_key)]:
        return high
    else:
        return -1

###############################################################################
## Main function

def main(args:Namespace):
    indexfile : Path = args.textfile.with_suffix(args.suffix)
    search_suffix_array(args.textfile, indexfile, args)


CONTEXT = 40
NUM_MATCHES = 20
INDEX_SUFFIX = '.ix'

parser = ArgumentParser(description='Search tool for text files')
parser.add_argument('--suffix', default=INDEX_SUFFIX,
    help=f'suffix of index file (default: {INDEX_SUFFIX})')
parser.add_argument('--num-matches', '-n', type=int, default=NUM_MATCHES,
    help=f'number of matches to show (default: {NUM_MATCHES} matches)')
parser.add_argument('--context', '-c', type=int, default=CONTEXT,
    help=f'context to show to the left and right (default: {CONTEXT} bytes)')
parser.add_argument('--trim-lines', '-t', action='store_true',
    help='trim each search result to the matching line')
parser.add_argument('textfile', type=Path,
    help='text file (utf-8 encoded)')
parser.add_argument('search_string',
    help='string to search for')


if __name__ == '__main__':
    main(parser.parse_args())

