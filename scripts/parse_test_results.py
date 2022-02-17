#!/usr/bin/env python3

import re
import sys
from typing import Counter
import numpy as np
from collections import Counter

def parse_line(line):
    re_passed = re.search('\d* passed', line)
    re_failed = re.search('\d* failed', line)
    re_error = re.search('\d* errors', line)
    re_seconds = re.search('in \d*', line)
    
    passed = 0 if re_passed is None else int(re_passed.group().split()[0])
    failed = 0 if re_failed is None else int(re_failed.group().split()[0])
    errors = 0 if re_error is None else int(re_error.group().split()[0])
    seconds = 0 if re_seconds is None else int(re_seconds.group().split()[-1])
    
    return passed,failed,errors,seconds

def parse_lines(lines):
    fails_list, passed_list, errors_list, seconds_list = [],[],[],[]
    
    for line in lines:
        passed,failed,errors,seconds = parse_line(line)
        passed_list.append(passed)
        fails_list.append(failed)
        errors_list.append(errors)
        seconds_list.append(seconds)
        
    return passed_list, fails_list, errors_list, seconds_list


def print_stats(x, msg):
    print('='*10)
    print(msg)
    print(f'Mean: {np.mean(x):.2f} ± {np.std(x):.2f}')
    print(f'Min-Max: [{np.min(x)},{np.max(x)}]')
    print('Frequencies', Counter(x))
    print('='*10)
    

if '__main__' == __name__:
    filename = sys.argv[1]
    with open(filename) as fi:
        p,f,e,s = parse_lines([line.strip() for line in fi])
        print_stats(p, 'Number of passed tests')
        print_stats(f, 'Number of failed tests')
        print_stats(e, 'Number of error tests')
        print_stats(s, 'Number of seconds')        
