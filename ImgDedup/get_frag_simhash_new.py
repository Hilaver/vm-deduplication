# python3 get_frag_simhash_new.py 原始镜像文件  frag_info路径+镜像段名称  该镜像段起始偏移  该镜像段大小  定长分块大小
import os
import queue
import math
import threading
import sys
import json
# import hashlib
import time
import struct
import numpy as np
from hashlib import md5
from collections import Counter

SECTOR_SIZE = 512
BLOCK_SIZE = 4096
BLANK_BLOCK_MD5_DICT = {512: "bf619eac0cdf3f68d496ea9344137e8b",
                        1024: "0f343b0931126a20f133d67c2b018a3b",
                        4096: "620f0b67a91f7f74151bc5be745b7110",
                        8192: "0829f71740aab1ab98b33eae21dee122",
                        1048576: "b6d81b360a5672d80c27430f39153e2c"
                        }
# 保存分段的信息
# frag_block_info
#     |--block_num[注意这里不包含最后一个块，最后一个块的MD5没有写到MD5.file]
#     |--blank_block_num
#     |--has_last_block
#     |--last_block_offset
#     |--last_block_size
# frag_block_md5_file
FRAG_INFO_JSON = {
    "frag_block_info": {"block_num": 0, "blank_block_num": 0,
                        "has_last_block": 0, "last_block_offset": -1, "last_block_size": 0},
    "frag_block_md5_file": ""}

# 获取命令行参数
if len(sys.argv) < 6:
    # pass
    print("0")
    exit(-1)

# 原始镜像路径
img_path = sys.argv[1]
# img_path = "/data/images/centos_6.5_x64_min_with_origin_os_2.raw"
# img_path = "F:\\data\\centos_6.5_x64_min_with_origin_os_2.raw"
# frag_info+镜像段名称
frag_name = sys.argv[2]
# frag_name = "/data/frag_info/centos_6.5_x64_min_with_origin_os_2.raw.part_5"
# frag_name = "F:\\data\\centos_6.5_x64_min_with_origin_os_2.raw.part_5"
# 镜像段的偏移【sector】
frag_offset = int(sys.argv[3])
# frag_offset = int(5533696)
# 镜像段大小【sector】
frag_size = int(sys.argv[4])
# frag_size = int(2854912)
# 定长分块粒度【byte】
BLOCK_SIZE = int(sys.argv[5])
# BLOCK_SIZE = int(4096)

FRAG_INFO_JSON["frag_block_md5_file"] = frag_name + ".md5.file"


# tools function
def convert_bin(s):
    ret = []
    for c in s:
        ret.append(1 if c == '1' else -1)
    return ret


def to_bin(arr):
    ret = []
    for i in arr:
        ret.append(1 if i > 0 else 0)
    return ret


def is_zero_blk(blk_buf, blk_size):
    for byte in blk_size:
        if byte != 0:
            return False
    return True


def test():
    print(BLANK_BLOCK_MD5_DICT[512])
    pass


# md5队列
md5_que = queue.Queue(maxsize=-1)
# finish flag
md5_calc_finish_flag = False


# 根据定长分块的md5加权计算镜像段的simhash
# 此处需保存定长分块的md5值
# 不需去重
def fixed_chunk_simhash(src_img_path: str, fragment_offset: int, fragment_size: int, chunk_size: int, N: float, K: int):
    # print("debug:", src_img_path, fragment_offset, fragment_size, chunk_size)
    frag_offset = fragment_offset * SECTOR_SIZE
    frag_size = fragment_size * SECTOR_SIZE
    frag_end_offset = frag_offset + frag_size
    md5_dict = {}
    file_blk_cnt = 0  # 总块数
    blank_blk_cnt = 0  # 空白块数量
    small_blk_cnt = 0  # 不足BLOCK_SIZE的块数
    simhash_ret = np.array([0] * 128)
    unique_blk_num = 0  # 唯一块的编号
    # md5_meta_file = open(FRAG_INFO_JSON["frag_block_md5_file"], "wb+")
    with open(src_img_path, 'rb') as f:
        # print(md5(f.read()).hexdigest())
        # buf_offset = file_blk_cnt * chunk_size + frag_offset
        # f.seek(buf_offset)
        while True:
            buf_offset = file_blk_cnt * chunk_size + frag_offset
            # if reach the end offset
            if buf_offset >= frag_end_offset:
                break
            f.seek(buf_offset)
            # 如果该分段不足BLOCK_SIZE,读取实际长度
            if frag_end_offset - buf_offset < chunk_size:
                buf_size = frag_end_offset - buf_offset
                small_blk_cnt += 1
            else:
                buf_size = chunk_size
            # read buf
            buf = f.read(buf_size)
            # handle the last block
            if buf_size != chunk_size:
                last_blk_sz = len(buf)
                # last_blk_buf = buf
                # blk_md5 = md5(buf).hexdigest()
                # pass
                # print("LAST", last_blk_sz)
                FRAG_INFO_JSON["frag_block_info"]["has_last_block"] = 1
                FRAG_INFO_JSON["frag_block_info"]["last_block_offset"] = buf_offset
                FRAG_INFO_JSON["frag_block_info"]["last_block_size"] = last_blk_sz
                # file_blk_cnt += 1
                # print(last_blk_sz, blk_md5)
                break
            md5_ret = md5(buf)
            blk_md5 = md5_ret.hexdigest()
            # save md5

            # md5_meta_file.write(struct.pack(">Q", int(blk_md5[:16], 16)))
            # md5_meta_file.write(struct.pack(">Q", int(blk_md5[16:], 16)))
            md5_que.put(blk_md5[:16])
            md5_que.put(blk_md5[16:])
            # print(int(blk_md5[16:], 16))
            # md5_meta_file.write(int.to_bytes(16, int(blk_md5, 16)))
            if blk_md5 != BLANK_BLOCK_MD5_DICT[chunk_size]:
                # simhash_ret += np.array(convert_bin(format(int(blk_md5, 16), '#0130b')[2:]))
                if blk_md5 in md5_dict:
                    md5_dict[blk_md5] += 1
                else:
                    md5_dict[blk_md5] = 1
            else:
                blank_blk_cnt += 1
            file_blk_cnt += 1
            # print(BLOCK_SIZE, blk_md5)
            # time.sleep(2)
        # print("BLOCK CNT:", file_blk_cnt)
        # print("BLANK BLOCK CNT:", blank_blk_cnt)
        # print("SMALL BLOCK CNT:", small_blk_cnt)
        FRAG_INFO_JSON["frag_block_info"]["block_num"] = file_blk_cnt
        FRAG_INFO_JSON["frag_block_info"]["blank_block_num"] = blank_blk_cnt
    # md5_meta_file.write(md5_meta_buf)
    md5_calc_finish_flag = True
    # md5_meta_file.close()
    # print("--> WATCH ME:")
    # print(Counter(md5_arr))

    # calculate simhash
    # with open(frag_name+'.txt', 'w+') as outfile:
    #     json.dump(md5_dict, outfile, ensure_ascii=False)
    #     outfile.write('\n')
    # md5_dict=Counter(md5_dict)

    # 加权求和
    # 判定是否分段只有零块
    # if len(md5_dict) == 0:
    #     md5_dict[BLANK_BLOCK_MD5_DICT[chunk_size]] = 1

    # origin
    for (k, v) in md5_dict.items():
        # if v == 1:
        # simhash_ret += (np.array(convert_bin(format(int(k, 16), '#0130b')[2:])))
        # simhash_ret += (np.array(convert_bin(format(int(k, 16), '#0130b')[2:])) * (int(v ** N) + int(K)))
        simhash_ret += (np.array(convert_bin(format(int(k, 16), '#0130b')[2:])) * int(11 + math.log(v, 2)))
        # simhash_ret += (np.array(convert_bin(format(int(k, 16), '#0130b')[2:])) * int(v ** 0.7))
        # simhash_ret += (np.array(convert_bin(format(int(k, 16), '#0130b')[2:])) * int(v))
        # simhash_ret += (np.array(convert_bin(format(int(k, 16), '#0130b')[2:])))

    # qcow2改进
    # md5_dict = Counter(md5_dict)
    # max_value = max(md5_dict.values())
    # # print(max_value)
    # md5_dict = md5_dict.most_common(len(md5_dict))
    # for (k, v) in md5_dict:
    #     if v == max_value:
    #         continue
    #     simhash_ret += (np.array(convert_bin(format(int(k, 16), '#0130b')[2:])))

    sim_str = ""
    for i in to_bin(simhash_ret):
        sim_str += str(i)
    print((hex(int(sim_str, 2))[2:]).zfill(32))
    # print(FRAG_INFO_JSON)
    fd_md5_meta_file = open(FRAG_INFO_JSON["frag_block_md5_file"], "wb+")
    while True:
        if md5_calc_finish_flag == True and md5_que.empty() == True:
            break
        fd_md5_meta_file.write(struct.pack(">Q", int(md5_que.get(), 16)))
    fd_md5_meta_file.close()
    # threading.Thread(target=save_md5_thread, args=()).start()
    # print(FRAG_INFO_JSON)
    # print("")


# start

# md5计算结果需要保存

# threading.Thread(target=fixed_chunk_simhash, args=(img_path, frag_offset, frag_size, BLOCK_SIZE)).start()
# for i in range(1, 10, 2):
#     print("N:", i / 10)
#     for j in range(1, 10, 2):
#         print("K:", j)
    # fixed_chunk_simhash(img_path, int(frag_offset), int(frag_size), int(BLOCK_SIZE), i / 10, 5)
fixed_chunk_simhash(img_path, int(frag_offset), int(frag_size), int(BLOCK_SIZE), 0.5, 3)
# print((hex(int("0", 2))[2:]).zfill(32))
# exit(0)

with open(frag_name + '.new.json', 'w+') as outfile:
    json.dump(FRAG_INFO_JSON, outfile, ensure_ascii=False)
    outfile.write('\n')

# end
