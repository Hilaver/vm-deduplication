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


# 根据img的描述文件重定位到每一个分段去重后的meta文件和base文件
# img_descr中的frag_descr有一个字段fragment_file_info_path，这个path指向一个json文件，json中保存了该分段的MD5文件路径、
# 分段的块数、最后一块的信息，以及一个frag_cluster_map的路径，这个frag_cluster_map也是一个json，保存了聚类后每个类去重
# 时的相关信息，是一个分段名为键、值为{分段块数、去重后的meta offset、meta path、base path、最后一块信息}的json，根据
# 此信息完成重构

# 镜像描述文件
class ImgDescriptor:
    def __init__(self, img_unique_nb, img_type, img_size, img_name, img_path, disk_type, fragment_nums,
                 boot_sector_offset):
        self.img_unique_nb, self.img_type, self.img_size, self.img_name, self.img_path, self.disk_type, \
        self.fragment_nums, self.boot_sector_offset = img_unique_nb, img_type, img_size, img_name, img_path, \
                                                      disk_type, fragment_nums, boot_sector_offset


# 镜像分段描述文件
class FragmentDescriptor:
    def __init__(self, fragment_unique_nb, fragment_infile_nb, fragment_offset, fragment_size, boot_signature,
                 fragment_type, fragment_simhash, fragment_name, fragment_path, src_path_name, fragment_file_info_path):
        self.fragment_unique_nb, self.fragment_infile_nb, self.fragment_offset, self.fragment_size, \
        self.boot_signature, self.fragment_type, self.fragment_simhash, self.fragment_name, self.fragment_path, \
        self.src_path_name, self.fragment_file_info_path = fragment_unique_nb, fragment_infile_nb, fragment_offset, \
                                                           fragment_size, boot_signature, fragment_type, \
                                                           fragment_simhash, fragment_name, fragment_path, \
                                                           src_path_name, fragment_file_info_path

    # print
    def check(self):
        print(
            "fragment_unique_nb\t{}\nfragment_infile_nb\t{}\nfragment_offset\t{}\nfragment_size\t{}\nboot_signature\t{}\nfragment_type\t{}\nfragment_name\t{}\nfragment_path\t{}\nsrc_path_name\t{}\nfragment_file_info_path\t{}".format(
                self.fragment_unique_nb, self.fragment_infile_nb, self.fragment_offset,
                self.fragment_size, self.boot_signature, self.fragment_type,
                self.fragment_name, self.fragment_path, self.src_path_name,
                self.fragment_file_info_path))
        simhash_str1, simhash_str2 = struct.unpack('>QQ', self.fragment_simhash)
        print("fragment_simhash\t{}{}\n".format(hex(simhash_str1)[2:].zfill(16), hex(simhash_str2)[2:].zfill(16)))

    # check simhash
    def check_simhash(self):
        simhash_str1, simhash_str2 = struct.unpack('>QQ', self.fragment_simhash)
        print("fragment_simhash\t{}{}\n".format(hex(simhash_str1)[2:].zfill(16), hex(simhash_str2)[2:].zfill(16)))

    # 是否包含文件系统
    def is_fs(self):
        return self.fragment_type != 0 and self.fragment_type != 1 \
               and self.fragment_type != 6 and self.fragment_type != 8


# 从镜像描述文件中获取所有分段
def get_img_and_frags_info_from_file(img_descr_file):
    ret = []
    with open(img_descr_file, "rb") as f:
        data = f.read(4 * 2 + 8 + 256 * 2 + 4 * 3)
        img_unique_nb, img_type, img_size, img_name, img_path, disk_type, fragment_nums, boot_sector_offset = \
            struct.unpack(
                "<IiQ256s256siII", data)
        # print(img_unique_nb, img_type, img_size, img_name.decode().strip('\0'), img_path.decode().strip('\0'),
        #       disk_type,
        #       fragment_nums, boot_sector_offset)
        img_descr = ImgDescriptor(img_unique_nb, img_type, img_size, img_name.decode().strip('\0'),
                                  img_path.decode().strip('\0'),
                                  disk_type,
                                  fragment_nums, boot_sector_offset)
        print(img_descr.img_name)
        for i in range(fragment_nums):
            data = f.read((4 * 2 + 8 * 2 + 4 * 2 + 16 + 256 * 4))
            fragment_unique_nb, fragment_infile_nb, fragment_offset, fragment_size, boot_signature, fragment_type, \
            fragment_simhash, fragment_name, fragment_path, src_path_name, fragment_file_info_path = struct.unpack(
                "<IIQQII16s256s256s256s256s", data)
            ret.append(FragmentDescriptor(fragment_unique_nb, fragment_infile_nb, fragment_offset, fragment_size,
                                          boot_signature, fragment_type,
                                          fragment_simhash, fragment_name.decode().strip('\0'),
                                          fragment_path.decode().strip('\0'),
                                          src_path_name.decode().strip('\0'),
                                          fragment_file_info_path.decode().strip('\0')))
    return img_descr, ret


# 获取分段的定长分块的MD5
def get_frag_info_from_json(frag_descr):
    with open(frag_descr.fragment_file_info_path, "r") as f:
        frag_blk_info_tmp = json.load(fp=f)
    return frag_blk_info_tmp


# 获取分段的去重map
def get_frag_cluster_map(frag_cluster_map_json_path):
    with open(frag_cluster_map_json_path, "r") as f:
        frag_cluster_map = json.load(fp=f)
    return frag_cluster_map


# 读取分段的meta到array
def get_frag_meta(frag_blk_num, meta_offset, frag_meta_file_path):
    frag_meta_arr = []
    with open(frag_meta_file_path, "rb") as fd_meta:
        fd_meta.seek(int(meta_offset))
        for i in range(int(frag_blk_num)):
            blk_num = (struct.unpack("<I", fd_meta.read(4)))
            frag_meta_arr += blk_num
    return frag_meta_arr


# 重构分段
def rebuild_frag(frag_descr, fd_dest):
    print("rebuild frag:[{}]".format(frag_descr.fragment_name))
    # 获取分段的块信息
    frag_info = get_frag_info_from_json(frag_descr)
    # print(frag_info)
    # exit(0)
    # 获取分段与去重文件的映射关系
    frag_cluster_map = get_frag_cluster_map(frag_info["dedup_map_json"])
    # print(frag_cluster_map)
    frag_dedup_info = frag_cluster_map[frag_descr.fragment_name]
    print(frag_dedup_info)
    # fd_meta = open(frag_dedup_info["meta_file_path"], "rb")
    fd_base = open(frag_dedup_info["base_file_path"], "rb")
    frag_blk_num = frag_dedup_info["blk_num"]
    # 从整个类的meta文件中提取该分段的meta
    blk_meta_arr = get_frag_meta(frag_blk_num, frag_dedup_info["meta_offset"], frag_dedup_info["meta_file_path"])
    # print(blk_meta_arr)
    # 将每个分块写回fd_dest
    fd_dest.seek(frag_descr.fragment_offset * SECTOR_SIZE)
    for blk_num in blk_meta_arr:
        fd_base.seek(blk_num * BLOCK_SIZE)
        buf = fd_base.read(BLOCK_SIZE)
        fd_dest.write(buf)
    fd_base.close()
    # 处理最后一个块
    if frag_dedup_info["has_last_blk"] == 1:
        print("has last block")
        # print(frag_dedup_info)
        last_block_file_path = frag_dedup_info["last_blk_file_path"]
        last_block_offset_in_dedupfile = frag_dedup_info["last_blk_offset"]
        last_block_offset_in_src = int(frag_dedup_info["blk_num"]) * BLOCK_SIZE
        last_block_sz = frag_dedup_info["last_blk_size"]
        # 读取最后一块
        fd_lst = open(last_block_file_path, "rb")
        fd_lst.seek(last_block_offset_in_dedupfile)
        buf = fd_lst.read(last_block_sz)
        # 写回目标文件
        fd_dest.seek(last_block_offset_in_src)
        fd_dest.write(buf)
        # print("last_block_offset_in_src", last_block_offset_in_src, "last_block_sz", last_block_sz)
        fd_lst.close()
    # msg = input()


# 重构镜像
def rebuild_img(img_descr_file, dest_path):
    # pass
    img_descr, frag_arr = get_img_and_frags_info_from_file(img_descr_file)
    rebuild_frag_arr = []
    # rebuild dest file name
    dest_file_path = dest_path + img_descr.img_name + ".rebuild"
    print("rebuild img: {} to {}".format(img_descr_file, dest_file_path))
    # print(dest_file_path)
    fd_dest = open(dest_file_path, 'wb+')
    for frag in frag_arr:
        rebuild_frag_arr.append(frag)
        # frag.check()
        # 这里可以起多个线程，每个线程重构一个分段
        rebuild_frag(frag, fd_dest)
    fd_dest.close()
    print("rebuild finish")


rebuild_img(rebuild_img_descr, rebuild_dest_path)
