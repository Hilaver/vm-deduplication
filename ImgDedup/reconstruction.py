from hashlib import md5
# import tarfile
import struct
import shutil
import ctypes
import json
import time
import sys
import os

DEDUP_DEST = "/data/datastore/dedup_store/"
SECTOR_SIZE = 512

# 注意这个需要跟ImgSplit2的参数一致
BLOCK_SIZE = 4096

# rebuild_img_descr = "/data/frag_info/centos_6.5_x64_min_with_testfile_2.raw.descr"
rebuild_img_descr = sys.argv[1]
rebuild_dest_path = "/data/rebuild/"
# rebuild_dest_path = sys.argv[2]