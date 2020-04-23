import redis
import os
import sys
import struct
import json
import numpy as np
from hashlib import md5

BLOCK_SIZE = 4096

if len(sys.argv) < 2:
    # pass
    print("parameters error")
    print("para: file info path")
    exit(-1)


def get_file_name_from_path(path):
    return path.split("/")[-1]


def read_json_from_file(json_path):
    with open(json_path, "r") as f:
        ret = json.load(fp=f)
    return ret


file_info_path = str(sys.argv[1])

rebuild_file_info = read_json_from_file(file_info_path)

print(rebuild_file_info)

rebuild_path = "/data/rebuild/"
redis_meta_path = "/data/redis_dedup/"
dedup_unique_file = "redis_dedup_unique_block.file"
dedup_last_block_file = "redis_dedup_last_block.file"

file_meta_path = rebuild_file_info["file_meta_path"]
fd_meta = open(rebuild_file_info["file_meta_path"], "rb")
fd_base = open(redis_meta_path + dedup_unique_file, "rb")
rebuild_file_path = rebuild_path + get_file_name_from_path(rebuild_file_info["file_path"]) + ".rebuild"
fd_rebuild = open(rebuild_file_path, "wb+")
rebuild_file_blk_num = rebuild_file_info["file_block_num"]
rebuild_file_meta_arr = []
for i in range(int(rebuild_file_blk_num)):
    blk_num = (struct.unpack("<I", fd_meta.read(4)))
    rebuild_file_meta_arr += blk_num
for blk_num in rebuild_file_meta_arr:
    fd_base.seek(blk_num * BLOCK_SIZE)
    buf = fd_base.read(BLOCK_SIZE)
    fd_rebuild.write(buf)
if int(rebuild_file_info["last_block_size"]) != 0:
    fd_last = open(redis_meta_path + dedup_last_block_file, "rb")
    fd_last.seek(int(rebuild_file_info["last_block_offset"]))
    buf = fd_last.read(int(rebuild_file_info["last_block_size"]))
    fd_rebuild.write(buf)
    fd_last.close()
fd_base.close()
fd_meta.close()
fd_rebuild.close()
