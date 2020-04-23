import redis
import os
import sys
import struct
import json
import time
import numpy as np
from hashlib import md5

if len(sys.argv) < 3:
    # pass
    print("parameters error")
    print("para1: origin files path, para2: dedup dest path")
    exit(-1)

origin_path = sys.argv[1]
dedup_path = sys.argv[2]

dedup_unique_file = "redis_dedup_unique_block.file"
dedup_last_block_file = "redis_dedup_last_block.file"

BLOCK_SIZE = 4096
g_unique_num = 0
g_dedup_files = []

FILE_INFO_JSON = {
    "file_path": "",
    "file_size": 0,
    "file_meta_path": "",
    "file_block_num": 0,
    "last_block_size": 0,
    "last_block_offset": 0
}


def get_files_in_dir(path):
    ret = []
    for root, dirs, files in os.walk(path, topdown=False):
        for name in files:
            ret.append(os.path.join(root, name))
    return ret


r = redis.Redis(host='192.168.59.141', port=6379,
                decode_responses=True)  # host是redis主机，需要redis服务端和客户端都启动 redis默认端口是6379
r.flushall()
if os.path.isdir(origin_path):
    print("origin path is {}".format(origin_path))
    g_dedup_files = get_files_in_dir(origin_path)
else:
    print("origin file is {}".format(origin_path))
    g_dedup_files.append(origin_path)

# 唯一块
fd_base = open(dedup_path + "/" + dedup_unique_file, "wb+")
# last block
fd_last = open(dedup_path + "/" + dedup_last_block_file, "wb+")

for file in g_dedup_files:
    file_blk_cnt = 0  # 总块数
    chunk_size = BLOCK_SIZE
    file_size = os.path.getsize(file)
    FILE_INFO_JSON["file_path"] = file
    FILE_INFO_JSON["file_size"] = file_size
    print(file)
    file_meta_path = dedup_path + "/" + md5(file.encode()).hexdigest() + ".meta"
    fd_file_meta = open(file_meta_path, "wb+")
    FILE_INFO_JSON["file_meta_path"] = file_meta_path
    fd_file_meta_arr=[]
    with open(file, "rb") as fd_origin_file:
        while True:
            buf_offset = file_blk_cnt * chunk_size
            # if reach the end offset
            if buf_offset >= file_size:
                break
            fd_origin_file.seek(buf_offset)
            # 如果该分段不足BLOCK_SIZE,读取实际长度
            if file_size - buf_offset < chunk_size:
                buf_size = file_size - buf_offset
            else:
                buf_size = chunk_size
            # read buf
            buf = fd_origin_file.read(buf_size)
            # handle the last block
            if buf_size != chunk_size:
                last_blk_sz = len(buf)
                FILE_INFO_JSON["last_block_size"] = last_blk_sz
                FILE_INFO_JSON["last_block_offset"] = fd_last.tell()
                fd_last.write(buf)
                # file_blk_cnt += 1
                # print(last_blk_sz, blk_md5)
                break
            blk_md5 = md5(buf).hexdigest()
            if r.exists(blk_md5):
                # print("redis exist")
                fd_file_meta_arr.append(int(r[blk_md5]))
                # fd_file_meta.write(struct.pack('<I', int(r[blk_md5])))
            else:
                # print("redis not exist")
                r.set(blk_md5, g_unique_num)
                fd_file_meta_arr.append(int(g_unique_num))
                # fd_file_meta.write(struct.pack('<I', int(g_unique_num)))
                fd_base.write(buf)
                g_unique_num += 1
            file_blk_cnt += 1
            # time.sleep(1)
        for blk_num in fd_file_meta_arr:
            fd_file_meta.write(struct.pack('<I', int(blk_num)))
        FILE_INFO_JSON["file_block_num"] = file_blk_cnt
    fd_file_meta.close()
    with open(dedup_path + "/" + md5(file.encode()).hexdigest() + ".json", 'w+') as outfile:
        json.dump(FILE_INFO_JSON, outfile, ensure_ascii=False)
        outfile.write('\n')

fd_base.close()
fd_last.close()
