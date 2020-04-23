#
# 用于计算镜像段的simhash
#
#

import os
import sys
import json
# import hashlib
import time
import numpy as np
from hashlib import md5

SECTOR_SIZE = 512
BLOCK_SIZE = 4096

# 确定挂载路径和镜像段名称
if len(sys.argv) < 3:
    MOUNT_PATH = "/mnt/"
    FRAG_NAME = str(int(time.time())) + "_tmp"
else:
    MOUNT_PATH = sys.argv[1]
    FRAG_NAME = sys.argv[2]

# class NameSizeNum:
#     def __init__(self, na, sz, cnt):
#         self.name = na
#         self.size = sz
#         self.num = cnt


htable = dict()
inode_set = set()


# def get_file_md5(file_path):
#     md5 = None
#     if os.path.isfile(file_path):
#         f = open(file_path, 'rb')
#         md5_obj = hashlib.md5()
#         md5_obj.update(f.read())
#         hash_code = md5_obj.hexdigest()
#         f.close()
#         md5 = str(hash_code).lower()
#     return md5

# 获取文件定长分块md5 和 文件摘要 【分块计算MD5 并将所有分块的md5拼接为一个字符串 并将该字符串的md5作为文件摘要】
def file_digest(file_path):
    # 文件中包含的完整数据块数量
    file_blk_cnt = 0
    # 最后一个数据块的大小
    last_blk_sz = 0
    # last_blk_buf = None
    blk_md5_arr = []
    md5_total_str = ""
    f_digest = None
    # md5_ctx = hashlib.md5()
    if os.path.isfile(file_path):
        with open(file_path, 'rb') as f:
            while True:
                f.seek(file_blk_cnt * BLOCK_SIZE)
                buf = f.read(BLOCK_SIZE)
                if len(buf) != BLOCK_SIZE:
                    last_blk_sz = len(buf)
                    # last_blk_buf = buf
                    blk_md5 = md5(buf).hexdigest()
                    # blk_md5_arr.append(blk_md5)
                    md5_total_str += blk_md5
                    # md5_ctx.update(blk_md5.encode())
                    break
                file_blk_cnt += 1
                blk_md5 = md5(buf).hexdigest()
                blk_md5_arr.append(blk_md5)
                md5_total_str += blk_md5
            f_digest = md5(md5_total_str.encode()).hexdigest()
        # f_sz = os.path.getsize(file_path)
        # if f_sz < BLOCK_SIZE:
        #     last_blk_sz = f_sz
        #     with open(file_path, 'rb') as f:
        #         f_digest = md5(f.read()).hexdigest()
        # else:
        #     with open(file_path, 'rb') as f:
        #         while True:
        #             f.seek(file_blk_cnt * BLOCK_SIZE)
        #             buf = f.read(BLOCK_SIZE)
        #             if len(buf) != BLOCK_SIZE:
        #                 last_blk_sz = len(buf)
        #                 # last_blk_buf = buf
        #                 blk_md5 = md5(buf).hexdigest()
        #                 # blk_md5_arr.append(blk_md5)
        #                 md5_total_str += blk_md5
        #                 # md5_ctx.update(blk_md5.encode())
        #                 break
        #             file_blk_cnt += 1
        #             blk_md5 = md5(buf).hexdigest()
        #             blk_md5_arr.append(blk_md5)
        #             md5_total_str += blk_md5
        #         f_digest = md5(md5_total_str.encode()).hexdigest()

    # file_digest = md5_ctx.hexdigest()
    # return (file_digest, {"blk_num": file_blk_cnt, "last_blk_sz": last_blk_sz, "blk_md5": blk_md5_arr})
    return (f_digest, {"blk_num": file_blk_cnt, "last_blk_sz": last_blk_sz, "blk_md5": blk_md5_arr})


def exec_cmd(cmd):
    return (os.popen(cmd).readlines())


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


def get_weight(file_sz, file_num):
    # return round(file_sz * file_num / 1024, 2)
    return file_sz * file_num
    # return file_num


simhash_ret = np.array([0] * 128)

# linux_filter = ["bin", "lib", "lib64", "sbin", "usr", "home"]
# windows_filter = ["Windows"]

# 下面是os walk遍历的
# def os_walk(root):
#     for root, dirs, files in os.walk(root, topdown=False):
#         for name in files:
#             dir = os.path.join(root, name)
#             # 如果是软链接
#             if os.path.islink(dir):
#                 # 获取源
#                 real_path = os.path.realpath(dir)
#                 if real_path[0:len(MOUNT_PATH)] != MOUNT_PATH:
#                     real_path = MOUNT_PATH.rstrip('/') + real_path
#                 # 如果源不存在
#                 if os.path.exists(real_path) == False:
#                     if "None" in htable:
#                         htable["None"]["real_dir"].append(real_path)
#                         htable["None"]["num"] += 1
#                         htable["None"]["s_link"].append({"src": real_path, "dest": dir})
#                     else:
#                         htable["None"] = {
#                             "inode": [],
#                             "real_dir": [real_path],
#                             "s_link": [{"src": real_path, "dest": dir}],
#                             "h_link": [],
#                             "size": 0,
#                             "num": 1
#                         }
#                     continue
#                 # 计算源 md5
#                 md5_digest = get_file_md5(real_path)
#                 stat_buf = os.stat(real_path)
#                 if md5_digest is None:
#                     if "None" in htable:
#                         htable["None"]["inode"].append(stat_buf.st_ino)
#                         htable["None"]["real_dir"].append(real_path)
#                         htable["None"]["num"] += 1
#                     else:
#                         htable["None"] = {
#                             "inode": [stat_buf.st_ino],
#                             "real_dir": [real_path],
#                             "s_link": [{"src": real_path, "dest": dir}],
#                             "h_link": [],
#                             "size": stat_buf.st_size,
#                             "num": 1
#                         }
#                     continue
#                 # 如果源 已经在htable 增加一条软链接
#                 if md5_digest in htable:
#                     htable[md5_digest]["s_link"].append({"src": real_path, "dest": dir})
#                 # 否则 增加一条 htable
#                 else:
#                     htable[md5_digest] = {
#                         "inode": [stat_buf.st_ino],
#                         "real_dir": [real_path],
#                         "s_link": [{"src": real_path, "dest": dir}],
#                         "h_link": [],
#                         "size": stat_buf.st_size,
#                         "num": 1
#                     }
#             # 如果不是软链接
#             else:
#                 # 计算md5
#                 md5_digest = get_file_md5(dir)
#                 stat_buf = os.stat(dir)
#                 if md5_digest is None:
#                     if "None" in htable:
#                         htable["None"]["inode"].append(stat_buf.st_ino)
#                         htable["None"]["real_dir"].append(dir)
#                         htable["None"]["num"] += 1
#                     else:
#                         htable["None"] = {
#                             "inode": [stat_buf.st_ino],
#                             "real_dir": [dir],
#                             "s_link": [],
#                             "h_link": [],
#                             "size": stat_buf.st_size,
#                             "num": 1
#                         }
#                     continue
#                 # 如果该md5已存在
#                 if md5_digest in htable:
#                     # inode是否重复 判断是否是硬链接
#                     # 如果inode已存在 增加一条硬链接
#                     if stat_buf.st_ino in htable[md5_digest]["inode"]:
#                         htable[md5_digest]["h_link"].append(dir)
#                     # 否则 是两个内容相同的文件
#                     else:
#                         htable[md5_digest]["inode"].append(stat_buf.st_ino)
#                         htable[md5_digest]["real_dir"].append(dir)
#                         htable[md5_digest]["num"] += 1
#                 # 该dm5不存在 增加一条htable
#                 else:
#                     htable[md5_digest] = {
#                         "inode": [stat_buf.st_ino],
#                         "real_dir": [dir],
#                         "s_link": [],
#                         "h_link": [],
#                         "size": stat_buf.st_size,
#                         "num": 1
#                     }
#
#
# os_walk(MOUNT_PATH)

# 下面是Linux du遍历的 更快一些
for line in exec_cmd("du -ha \"" + MOUNT_PATH + "\" | awk -v FS='\\t' '{print $2}'"):
    dir = line.strip('\n')
    # 如果是软链接
    if os.path.islink(dir):
        # 获取源
        real_path = os.path.realpath(dir)
        if real_path[0:len(MOUNT_PATH)] != MOUNT_PATH:
            real_path = MOUNT_PATH.rstrip('/') + real_path
        # 如果源不存在
        if os.path.exists(real_path) == False:
            if "None" in htable:
                htable["None"]["real_dir"].append(real_path)
                htable["None"]["s_link"].append({"src": real_path, "dest": dir})
            else:
                htable["None"] = {
                    "inode": [],
                    "real_dir": [real_path],
                    "s_link": [{"src": real_path, "dest": dir}],
                    "h_link": [],
                    "size": 0,
                    "num": 1,
                    "f_info": {
                        "blk_num": 0,
                        "last_blk_sz": 0,
                        "blk_md5": []
                    }
                }
            continue
        # 如果源是目录
        if os.path.isdir(real_path):
            if "None" in htable:
                htable["None"]["s_link"].append({"src": real_path, "dest": dir})
            else:
                htable["None"] = {
                    "inode": [],
                    "real_dir": [],
                    "s_link": [{"src": real_path, "dest": dir}],
                    "h_link": [],
                    "size": 0,
                    "num": 0,
                    "f_info": {
                        "blk_num": 0,
                        "last_blk_sz": 0,
                        "blk_md5": []
                    }
                }
            continue
        # 计算源 md5
        # md5_digest = get_file_md5(real_path)
        (md5_digest, file_info) = file_digest(real_path)
        stat_buf = os.stat(real_path)
        if md5_digest is None:
            if "None" in htable:
                htable["None"]["inode"].append(stat_buf.st_ino)
                htable["None"]["real_dir"].append(real_path)
                htable["None"]["num"] += 1
            else:
                htable["None"] = {
                    "inode": [stat_buf.st_ino],
                    "real_dir": [real_path],
                    "s_link": [{"src": real_path, "dest": dir}],
                    "h_link": [],
                    "size": stat_buf.st_size,
                    "num": 1,
                    "f_info": {
                        "blk_num": 0,
                        "last_blk_sz": 0,
                        "blk_md5": []
                    }
                }
            continue
        # 如果源 已经在htable 增加一条软链接
        if md5_digest in htable:
            htable[md5_digest]["s_link"].append({"src": real_path, "dest": dir})
        # 否则 增加一条 htable
        else:
            htable[md5_digest] = {
                "inode": [stat_buf.st_ino],
                "real_dir": [real_path],
                "s_link": [{"src": real_path, "dest": dir}],
                "h_link": [],
                "size": stat_buf.st_size,
                "num": 1,
                "f_info": file_info
            }
    # 如果是常规文件
    elif os.path.isfile(dir):
        # md5_digest = get_file_md5(dir)
        (md5_digest, file_info) = file_digest(dir)
        stat_buf = os.stat(dir)
        if md5_digest is None:
            if "None" in htable:
                htable["None"]["inode"].append(stat_buf.st_ino)
                htable["None"]["real_dir"].append(dir)
                htable["None"]["num"] += 1
            else:
                htable["None"] = {
                    "inode": [stat_buf.st_ino],
                    "real_dir": [dir],
                    "s_link": [],
                    "h_link": [],
                    "size": stat_buf.st_size,
                    "num": 1,
                    "f_info": {
                        "blk_num": 0,
                        "last_blk_sz": 0,
                        "blk_md5": []
                    }
                }
            continue
        # 如果该md5已存在
        if md5_digest in htable:
            # inode是否重复 判断是否是硬链接
            # 如果inode已存在 增加一条硬链接
            if stat_buf.st_ino in htable[md5_digest]["inode"]:
                htable[md5_digest]["h_link"].append(dir)
            # 否则 是两个内容相同的文件
            else:
                htable[md5_digest]["inode"].append(stat_buf.st_ino)
                htable[md5_digest]["real_dir"].append(dir)
                htable[md5_digest]["num"] += 1
        # 该dm5不存在 增加一条htable
        else:
            htable[md5_digest] = {
                "inode": [stat_buf.st_ino],
                "real_dir": [dir],
                "s_link": [],
                "h_link": [],
                "size": stat_buf.st_size,
                "num": 1,
                "f_info": file_info
            }
    # 如果是目录
    elif os.path.isdir(dir):
        pass

    # 特殊文件 如socket
    else:
        # 计算md5
        # md5_digest = get_file_md5(dir)
        (md5_digest, file_info) = file_digest(dir)
        stat_buf = os.stat(dir)
        if md5_digest is None:
            if "None" in htable:
                htable["None"]["inode"].append(stat_buf.st_ino)
                htable["None"]["real_dir"].append(dir)
                htable["None"]["num"] += 1
            else:
                htable["None"] = {
                    "inode": [stat_buf.st_ino],
                    "real_dir": [dir],
                    "s_link": [],
                    "h_link": [],
                    "size": stat_buf.st_size,
                    "num": 1,
                    "f_info": {
                        "blk_num": 0,
                        "last_blk_sz": 0,
                        "blk_md5": []
                    }
                }
            continue
        # 如果该md5已存在
        if md5_digest in htable:
            # inode是否重复 判断是否是硬链接
            # 如果inode已存在 增加一条硬链接
            if stat_buf.st_ino in htable[md5_digest]["inode"]:
                htable[md5_digest]["h_link"].append(dir)
            # 否则 是两个内容相同的文件
            else:
                htable[md5_digest]["inode"].append(stat_buf.st_ino)
                htable[md5_digest]["real_dir"].append(dir)
                htable[md5_digest]["num"] += 1
        # 该dm5不存在 增加一条htable
        else:
            htable[md5_digest] = {
                "inode": [stat_buf.st_ino],
                "real_dir": [dir],
                "s_link": [],
                "h_link": [],
                "size": stat_buf.st_size,
                "num": 1,
                "f_info": file_info
            }
        ############################################################
        # if (md5_digest not in htable):
        #     # htable[md5_digest] = NameSizeNum(dir, os.path.getsize(dir), 1)
        #     htable[md5_digest] = {"dir": [dir], "size": os.path.getsize(dir), "num": 1}
        # else:
        #     htable[md5_digest]["num"] += 1
        #     htable[md5_digest]["dir"].append(dir)

# print(htable)

for (k, v) in htable.items():
    if k != "None":
        simhash_ret += (np.array(convert_bin(format(int(k, 16), '#0130b')[2:])) * (get_weight(v["size"], v["num"])))

sim_str = ""
for i in to_bin(simhash_ret):
    sim_str += str(i)
print((hex(int(sim_str, 2))[2:]).zfill(32))

with open(FRAG_NAME + '.json', 'w+') as outfile:
    json.dump(htable, outfile, ensure_ascii=False)
    outfile.write('\n')
