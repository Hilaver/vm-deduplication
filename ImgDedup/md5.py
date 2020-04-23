from hashlib import md5
import sys


if len(sys.argv) < 2:
    exit(-1)

with open(sys.argv[1], 'rb') as f:
    print(md5(f.read()).hexdigest())