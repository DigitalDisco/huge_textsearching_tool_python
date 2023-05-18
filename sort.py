#!/usr/bin/env python3

import sys
import random
from time import time
from pathlib import Path
from argparse import ArgumentParser, Namespace
from typing import List, Callable, Any, MutableSequence, Union
from contextlib import redirect_stdout, redirect_stderr
from io import StringIO
from traceback import print_tb

from util import ProgressBar, ComparableWithCounter, DiskIntArray, DiskIntArrayBuilder

# Type aliases
SortableSequence = Union[memoryview, MutableSequence[Any]]
SortKey = Callable[[Any], Any]
PivotSelector = Callable[[SortableSequence, int, int, SortKey], int]


###############################################################################
## Insertion sort

def insertion_sort(array:SortableSequence, key:SortKey):
    """
    In-place insertion sort using a sort key.
    """
    for i in ProgressBar(range(0, len(array)), desc="Insertion sort"):

        j = i-1 #inner loop which starts at index of outer loop - 1, iterates list to the left
        while key(array[j]) > key(array[j+1]) and j>=0: #checks if left neighbor is bigger than the current element and swaps them if so, keeps swapping until right place for current element is found, stops at 0 to avoid going into negative values
            array[j], array[j+1] = array[j+1], array[j] #takes a element at i, puts it in the list, and checks if any previous element in the list is greater or less than the newly checked element
            j -= 1 #goes further to the left after swap


###############################################################################
## Quicksort

def quicksort(array:SortableSequence, key:SortKey, pivotselector:PivotSelector, cutoff:int=0):
    """
    In-place quicksort using a sort key.
    """
    #Step 1 choose pivot
    #Step 2 split around pivot
    #Step 3 repeat until base case (single element)
    with ProgressBar(total=len(array), desc="Quicksorting") as logger:
        
        quicksort_subarray(array, 0, len(array), key, pivotselector, cutoff, logger)
        logger.update(len(array) - logger.n)

############################################### pivotselector ger INDEX på pivoten 
def quicksort_subarray(array:SortableSequence, lo:int, hi:int, key:SortKey,
                       pivotselector:PivotSelector, cutoff:int, logger):
    """
    Quicksorts the subarray array[lo:hi] in place.
    """
    logger.update(lo - logger.n)
    # Base case
    size = hi - lo
    if size == 0:
        return
    if cutoff >= size:
        builtin_timsort(array, lo, hi, key)
    else:
        pivot = partition(array, lo, hi, key, pivotselector)   # Partition the subarray; update pivot with its new position
        quicksort_subarray(array, lo, pivot, key, pivotselector,cutoff, logger)                # Sort left partition
        quicksort_subarray(array, pivot+1, hi,key, pivotselector,cutoff, logger)       



def builtin_timsort(array:SortableSequence, lo:int, hi:int, key:SortKey):
    """
    Call Python's built-in sort on the subarray array[lo:hi].
    """
    sorted_array : List[int] = sorted(array[lo:hi], key=key)
    for i, val in enumerate(sorted_array, lo):
        array[i] = val


def partition(array:SortableSequence, lo:int, hi:int,
              key:SortKey, pivotselector:PivotSelector) -> int:
    """
    Partition the subarray sa[lo:hi]. Returns the final index of the pivot.
    """
    def swap(i, j):
        array[i], array[j] = array[j], array[i]
    pivot = pivotselector(array,lo,hi,key)
    swap(lo,pivot)
    pivot = lo
    lo+=1
    hi-=1
    pivot_value = array[pivot]
    while True:
        while lo <= hi and key(array[lo]) < key(pivot_value): #key!= array
            lo+=1
        while lo <= hi and key(array[hi]) > key(pivot_value):
            hi-=1
        if lo > hi:
            break
        swap(lo,hi)
        lo+=1;hi-=1
    swap(pivot,hi)
    return hi


def take_first_pivot(array:SortableSequence, lo:int, hi:int, key:SortKey) -> int:
    """
    Returns the first index in the subsequence [lo...hi-1] (i.e., lo).
    """
    return lo


def random_pivot(array:SortableSequence, lo:int, hi:int, key:SortKey) -> int:
    """
    Returns a random index in the subsequence [lo...hi-1].
    """
    return random.randrange(lo, hi)


def median_of_three(array:SortableSequence, lo:int, hi:int, key:SortKey) -> int:
    lowkey = key(array[lo])
    highkey = key(array[hi-1])
    mediankey = key((array[(hi-1 + lo)//2]))
    #print(key(lo), key(hi), key((lo+hi)/2))
    
    if lowkey >= highkey and lowkey <= mediankey or lowkey <= highkey and lowkey >= mediankey:
        return  lo
    if mediankey >= highkey and mediankey <= lowkey or mediankey <= highkey and mediankey >= lowkey:
        return (lo+hi-1)//2
    if highkey >= lowkey and highkey <= mediankey or highkey <= lowkey and highkey >= mediankey:
        return hi-1
    """
    Returns the index of the median of the first, mid and last element
    in the subsequence [lo...hi-1].
    """



###############################################################################
## Testing

def check_sorted_array(array:SortableSequence, key:SortKey):
    """
    Tests that an array is sorted according to the given sort key.
    """
    leftKey = key(array[0])
    for i, rightVal in enumerate(ProgressBar(array[1:], desc="Checking array"), 1):
        rightKey = key(rightVal)
        assert leftKey < rightKey, f"Ordering error in position {i}: {leftKey} >= {rightKey}"
        leftKey = rightKey


def check_array_contents(array:SortableSequence, expected:SortableSequence):
    """
    Tests that an array is equal to what is expected.
    """
    assert len(array) == len(expected), \
        f"Wrong size of array: should be {len(expected)}, but was {len(array)}"
    for i, (val, correct) in enumerate(zip(array, expected)):
        assert val == correct, f"Wrong value in position {i}: should be {correct}, but was {val}"


def test_sorting_algorithm(sort, key:SortKey, array_path:Path, max_size:int=20):
    """
    Tests that a sorting algorithm works on arrays of all sizes up to `max_size`.
    """
    input_list = expected = result = None  # this is to keep the type checker satisfied
    try:
        for size in ProgressBar(range(1, max_size+1), "Testing different sizes", unit=1):
            for randomness in [0.0, 0.25, 1.0]:
                # Run each test 10 times to increase the chance of failure.
                for i in range(10):
                    ProgressBar.visible = False  # Disable output from inner progress bars
                    create_partially_shuffled_array(size, randomness, array_path)
                    with DiskIntArray(array_path) as numbers:
                        input_list = list(numbers)
                        expected = list(sorted(input_list))
                        try:
                            sort(numbers)
                            check_sorted_array(numbers, key)
                            check_array_contents(numbers, expected)
                        except Exception as e:
                            ProgressBar.visible = True
                            result = list(numbers)
                            raise # Will be caught higher-up
                    ProgressBar.visible = True

    except Exception as e:
        print("\n\nA test failed!", file=sys.stderr)
        print(file=sys.stderr)
        print("Traceback (most recent call last):", file=sys.stderr)
        print_tb(e.__traceback__)
        print(file=sys.stderr)
        print(f"Input array: {input_list}", file=sys.stderr)
        if expected != result:
            print(f"Expected result: {expected}", file=sys.stderr)
            print(f"Actual result: {result}", file=sys.stderr)
        print(f"{type(e).__name__}: {e}", file=sys.stderr)
        sys.exit(1)


###############################################################################
## Creating random arrays

def create_partially_shuffled_array(size:int, randomness:float, path:Path):
    """
    Creates a DiskIntArray of the integers [0..size-1] in random order.
    randomness controls how random the final list will be
    (0 means that it is sorted, and 1 means that it totally random).
    Uses the Fisher-Yates shuffle algorithm, but decides randomly when to swap elements.
    """
    assert 0.0 <= randomness <= 1.0
    with DiskIntArrayBuilder(path) as numbers:
        for i in ProgressBar(range(size), desc="Creating array"):
            numbers.append(i)
    with DiskIntArray(path) as numbers:
        for index in ProgressBar(range(size), desc="Shuffling array"):
            if random.random() < randomness:
                other = random.randrange(index, size)
                numbers[index], numbers[other] = numbers[other], numbers[index]


###############################################################################
## Main function

def main(args:Namespace):
    if args.recursion_limit:
        sys.setrecursionlimit(args.recursion_limit)

    ComparableWithCounter.comparisons = 0
    sortkey = ComparableWithCounter
    if args.algorithm.startswith('i'):
        def sort(numbers):
            insertion_sort(numbers, sortkey)
    elif args.algorithm.startswith('q'):
        pivot = (
            take_first_pivot if args.pivot == "take-first"      else
            random_pivot     if args.pivot == "random"          else
            median_of_three  if args.pivot == "median-of-three" else
            NotImplemented
        )
        def sort(numbers):
            quicksort(numbers, sortkey, pivot, cutoff=args.cutoff)
    else:
        raise ValueError(f"Unknown algorithm: {args.algorithm}")

    if args.test:
        if args.num >= 500:
            args.num = 20
        test_sorting_algorithm(sort, sortkey, args.array_path, max_size=args.num)
        return

    create_partially_shuffled_array(args.num, args.randomness, args.array_path)
    with DiskIntArray(args.array_path) as numbers:
        start_time = time()
        sort(numbers)
        elapsed_time = time() - start_time
        instantiations = ComparableWithCounter.instantiations
        comparisons = ComparableWithCounter.comparisons
        check_sorted_array(numbers, sortkey)

    print(f"""
Sorting time:{elapsed_time:12_.3f} secs
Key calls:  {instantiations:13_d} calls
Comparisons:{comparisons:13_d} cmps
Comp. speed:{comparisons/elapsed_time:13_.0f} cmps/sec
""", file=sys.stderr)


default_array_path = Path('testarray.ix')

parser = ArgumentParser(description='Testing different sorting implementations')
parser.add_argument('--test', action='store_true',
    help='run exhaustive tests on small arrays')
parser.add_argument('--num', '-n', type=int, default=1000,
    help='sort the numbers 0...N-1 (default: 1000, or 20 if you run the exhaustive --test)')
parser.add_argument('--randomness', '-r', type=float, default=1.0,
    help='randomness in shuffling the numbers (default: 1.0)')
parser.add_argument('--pivot', '-p', default='take-first', 
    choices=['take-first', 'random', 'median-of-three'],
    help='[only for quicksort] pivot selector (default: take-first)')
parser.add_argument('--cutoff', '-c', type=int, default=0,
    help='[only for quicksort] cutoff to built-in Timsort (default: 0)')
parser.add_argument('--recursion-limit', '-R', type=int,
    help=f"set the recursion limit in Python (default: {sys.getrecursionlimit()})")
parser.add_argument('--array-path', type=Path, default=default_array_path,
    help=f"the path to the external array file (default: {default_array_path})")
parser.add_argument('algorithm', choices=['insertsort', 'quicksort'],
    help='sorting algorithm to test')

if __name__ == '__main__':
    main(parser.parse_args())

