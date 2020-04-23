from sklearn.cluster import DBSCAN
from hashlib import md5
# import tarfile
import struct
import shutil
import ctypes
import json
import time
import sys
import os

MOUNT_PATH = "/mnt/"
DEDUP_DEST = "/data/datastore/dedup_store/"
SECTOR_SIZE = 512
BLOCK_SIZE = 4096

# (500MB*1024*1024/(16+4))*8 [16B:md5 4B:block_id] 单位：sector
# 即：100GB
CLUSTER_SPLIT_SIZE = 209715200

# FRAG_INFO_PATH = "/data/frag_info/"
FRAG_INFO_PATH = sys.argv[1]

g_unique_blk_num = 0


# for test
# 按照文件进行去重的结构
# |--img
#     |--frag_1
#         |--frag_offset
#         |--frag_size
#         |--frag_..
#         |--frag_file_info_json【这里保存了分段中的所有文件信息：小文件的md5，大文件定长分块的md5】
#             |--【去重的时候：
#                 每个类有一个cluster_file_htable，存储了文件md5-->文件去重后的信息
#                 frag_cluster_map里面保存了分段名-->cluster_file_htable的映射
#                 小文件直接复制到去重目录，文件名为md5.file，根据md5可查到
#                 大文件根据md5可查到cluster_file_htable中保存的定长分块的meta信息以及base文件路径，注意最后一块是追加到meta文件的
#                 重构时：根据img_descr找到每个分段的名称，然后从frag_cluster_map找到该分段对应的所在类的cluster_file_htable(json)，然后：
#                 文件系统分段：从分段的file_info_json里面获取每个文件的md5，根据这个md5从cluster_file_htable找，如果是小文件，直接从dest_path拷贝，如果是大文件，找到meta文件和base文件，读取对应的分块完成重构
#                 非文件系统分段：如果分段大小小于BLOCK_SIZE，则处理过程同小文件的处理，若分段大小大于BLOCK_SIZE，处理过程同大文件】
#     |--frag_2
#     |--frag_..



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
        return self.fragment_file_info_path != "NULL"


# 存储所有的镜像分段
g_all_frag_descrs = []

# 存储所有的类 每一个类包含N个镜像分段
# g_all_frag_clusters = {"fs_cluster": [], "non_fs_cluster": []}
g_all_frag_clusters = {"fs_cluster": {}, "non_fs_cluster": {}}


# 从镜像描述文件中获取所有分段
def get_frags_info_from_file(img_descr_file):
    ret = []
    with open(img_descr_file, "rb") as f:
        data = f.read(4 * 2 + 8 + 256 * 2 + 4 * 3)
        img_unique_nb, img_type, img_size, img_name, img_path, disk_type, fragment_nums, boot_sector_offset = struct.unpack(
            "<IiQ256s256siII", data)
        # print(img_unique_nb, img_type, img_size, img_name.decode().strip('\0'), img_path.decode().strip('\0'),
        #       disk_type,
        #       fragment_nums, boot_sector_offset)
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
    return ret


# 执行cmd
def exec_cmd(cmd):
    return (os.popen(cmd).readlines())


# 获取文件系统中所有文件的信息【读取json】
def get_fs_frag_file_info(frag_descr):
    file_htable = None
    with open(frag_descr.fragment_file_info_path, 'r') as f:
        file_htable = json.load(fp=f)
    return file_htable


# convert to binary string
def convert_bin(s):
    ret = []
    for c in s:
        ret.append(1 if c == '1' else -1)
    return ret


# 计算hamming distance
def calc_Hamming_dist(simhash_bytes1, simhash_bytes2):
    ret = 0
    if len(simhash_bytes1) != len(simhash_bytes2):
        return -1
    for i in range(len(simhash_bytes1)):
        for b in (bin(simhash_bytes1[i] ^ simhash_bytes2[i])[2:]):
            ret += 1 if b == '1' else 0
    return ret


# 获取所有的分段
for root, dirs, files in os.walk(FRAG_INFO_PATH, topdown=False):
    for file in files:
        if os.path.splitext(file)[1] == ".descr":
            g_all_frag_descrs += (get_frags_info_from_file(os.path.join(root, file)))


# for i in range(len(sys.argv)):
#     if i > 0:
#         g_all_frag_descrs += (get_frags_info_from_file(sys.argv[i]))


# 挂载分区
def mount_partition(frag_descr, loop_dev, mount_path):
    cmd = "sudo losetup {} {} -o {}".format(loop_dev, frag_descr.src_path_name,
                                            int(frag_descr.fragment_offset) * SECTOR_SIZE)
    ret = exec_cmd(cmd)
    if len(ret) != 0:
        return False
    # ntfs
    if frag_descr.fragment_type == 2:
        cmd = "sudo mount -o ro -t ntfs-3g {} {}".format(loop_dev, mount_path)
    elif frag_descr.fragment_type == 5:
        cmd = "sudo mount -o ro {} {}".format(loop_dev, mount_path)
    else:
        cmd = "sudo mount -o ro {} {}".format(loop_dev, mount_path)
    ret = exec_cmd(cmd)
    if len(ret) != 0:
        return False
    return True


# 卸载分区
def umount_partition(frag_descr, loop_dev, mount_path):
    ret = exec_cmd("umount -f {}".format(mount_path))
    if len(ret) == 0:
        ret = exec_cmd("losetup -d {}".format(loop_dev))
        return True if len(ret) == 0 else False
    else:
        return False


# linux copy
def os_copy(src, dest):
    cmd = "cp -f \"{}\" \"{}\"".format(src, dest)
    ret = exec_cmd(cmd)
    return True if len(ret) == 0 else False


# 判断数据块是否为0
def is_zero_blk(blk_buf):
    pass


# 复制src文件中指定数据到dest
def bytes_copy2file(fd_src, fd_dest, start_offset, cp_size):
    fd_src.seek(start_offset)
    fd_dest.write(fd_src.read(cp_size))


# 获取类中所有分段的大小
def get_cluster_total_sz(cluster_list):
    ret = 0
    for frag in cluster_list:
        ret += frag.fragment_size
    return ret


# 将大小超过限制的类分裂
def split_cluster(cluster_list, split_sz):
    size_cnt = 0
    tmp = []
    ret = []
    for frag in cluster_list:
        if size_cnt + frag.fragment_size > split_sz:
            if len(tmp) != 0:
                ret.append(tmp)
            tmp = [frag]
            size_cnt = frag.fragment_size
        else:
            tmp.append(frag)
            size_cnt += frag.fragment_size
    if len(tmp) != 0:
        ret.append(tmp)
    return ret


# for debug
def check_all_clusters():
    print("----> FS-clusters")
    for (k, v) in g_all_frag_clusters["fs_cluster"].items():
        print("cluster[{}]".format(k))
        for frag in v:
            print(frag.fragment_name)
            frag.check_simhash()
    print("----> Non-FS-clusters")
    for (k, v) in g_all_frag_clusters["non_fs_cluster"].items():
        print("cluster[{}]".format(k))
        for frag in v:
            print(frag.fragment_name)
            frag.check_simhash()


# 文件块级去重 追加到basefile metafile
def file_dedup_fsp(f_src, fd_base, fd_meta, blk_md5_ht):
    # src_sz = os.path.getsize(f_src)
    meta_offset = fd_meta.tell()
    # 文件中包含的完整数据块数量
    file_blk_cnt = 0
    # 最后一个数据块的大小
    last_blk_sz = 0
    last_blk_buf = None
    global g_unique_blk_num
    with open(f_src, 'rb') as fd_src:
        while True:
            fd_src.seek(file_blk_cnt * BLOCK_SIZE)
            buf = fd_src.read(BLOCK_SIZE)
            if len(buf) != BLOCK_SIZE:
                last_blk_sz = len(buf)
                last_blk_buf = buf
                break
            file_blk_cnt += 1
            md5_digest = md5(buf).hexdigest()
            if md5_digest in blk_md5_ht:
                fd_meta.write(struct.pack('<I', blk_md5_ht[md5_digest]))
            else:
                blk_md5_ht[md5_digest] = g_unique_blk_num
                fd_meta.write(struct.pack('<I', g_unique_blk_num))
                g_unique_blk_num += 1
                fd_base.write(buf)
    if last_blk_sz != 0:
        fd_meta.write(last_blk_buf)
    return (file_blk_cnt, last_blk_sz, meta_offset)


# 文件块级去重 追加到basefile metafile
def file_dedup_fsp_comm(fd_src, src_start_offset, src_sz, fd_base, fd_meta, blk_md5_ht, is_reg_file):
    # src_sz = os.path.getsize(f_src)
    meta_offset = fd_meta.tell()
    # 文件中包含的完整数据块数量
    file_blk_cnt = 0
    # 最后一个数据块的大小
    last_blk_sz = 0
    last_blk_buf = None
    global g_unique_blk_num
    # 如果是常规文件
    if is_reg_file == True:
        # with open(f_src, 'rb') as fd_src:
        while True:
            fd_src.seek(file_blk_cnt * BLOCK_SIZE)
            buf = fd_src.read(BLOCK_SIZE)
            if len(buf) != BLOCK_SIZE:
                last_blk_sz = len(buf)
                last_blk_buf = buf
                break
            file_blk_cnt += 1
            md5_digest = md5(buf).hexdigest()
            if md5_digest in blk_md5_ht:
                fd_meta.write(struct.pack('<I', blk_md5_ht[md5_digest]))
            else:
                blk_md5_ht[md5_digest] = g_unique_blk_num
                fd_meta.write(struct.pack('<I', g_unique_blk_num))
                g_unique_blk_num += 1
                fd_base.write(buf)
    # 如果是不含FS的分段
    else:
        # is_first_zero_blk=True
        while True:
            read_offset = file_blk_cnt * BLOCK_SIZE
            read_sz = BLOCK_SIZE if src_sz - read_offset > BLOCK_SIZE else src_sz - read_offset
            read_offset += src_start_offset
            fd_src.seek(read_offset)
            buf = fd_src.read(read_sz)
            if read_sz != BLOCK_SIZE:
                last_blk_sz = len(buf)
                last_blk_buf = buf
                break
            file_blk_cnt += 1
            md5_digest = md5(buf).hexdigest()
            if md5_digest in blk_md5_ht:
                fd_meta.write(struct.pack('<I', blk_md5_ht[md5_digest]))
            else:
                blk_md5_ht[md5_digest] = g_unique_blk_num
                fd_meta.write(struct.pack('<I', g_unique_blk_num))
                g_unique_blk_num += 1
                fd_base.write(buf)
    if last_blk_sz != 0:
        fd_meta.write(last_blk_buf)
    return (file_blk_cnt, last_blk_sz, meta_offset)


# 文件块级去重 追加到basefile metafile
def file_dedup_fsp_comm2(fd_src, src_start_offset, src_sz, fd_base, fd_meta, blk_md5_ht, is_reg_file, reg_file_info):
    # src_sz = os.path.getsize(f_src)
    meta_offset = fd_meta.tell()
    # 文件中包含的完整数据块数量
    file_blk_cnt = 0
    # 最后一个数据块的大小
    last_blk_sz = 0
    last_blk_buf = None
    global g_unique_blk_num
    # 如果是常规文件
    if is_reg_file == True:
        # with open(f_src, 'rb') as fd_src:
        for i in range(int(reg_file_info["blk_num"])):
            md5_digest = reg_file_info["blk_md5"][i]
            if md5_digest in blk_md5_ht:
                fd_meta.write(struct.pack('<I', blk_md5_ht[md5_digest]))
            else:
                fd_src.seek(i * BLOCK_SIZE)
                buf = fd_src.read(BLOCK_SIZE)
                blk_md5_ht[md5_digest] = g_unique_blk_num
                fd_meta.write(struct.pack('<I', g_unique_blk_num))
                g_unique_blk_num += 1
                fd_base.write(buf)
        last_blk_sz = int(reg_file_info["last_blk_sz"])
        if last_blk_sz != 0:
            fd_src.seek(int(reg_file_info["blk_num"]) * BLOCK_SIZE)
            last_blk_buf = fd_src.read(last_blk_sz)
        # while True:
        #     fd_src.seek(file_blk_cnt * BLOCK_SIZE)
        #     buf = fd_src.read(BLOCK_SIZE)
        #     if len(buf) != BLOCK_SIZE:
        #         last_blk_sz = len(buf)
        #         last_blk_buf = buf
        #         break
        #     file_blk_cnt += 1
        #     md5_digest = md5(buf).hexdigest()
        #     if md5_digest in blk_md5_ht:
        #         fd_meta.write(struct.pack('<I', blk_md5_ht[md5_digest]))
        #     else:
        #         blk_md5_ht[md5_digest] = g_unique_blk_num
        #         fd_meta.write(struct.pack('<I', g_unique_blk_num))
        #         g_unique_blk_num += 1
        #         fd_base.write(buf)
    # 如果是不含FS的分段
    else:
        # is_first_zero_blk=True
        while True:
            read_offset = file_blk_cnt * BLOCK_SIZE
            read_sz = BLOCK_SIZE if src_sz - read_offset > BLOCK_SIZE else src_sz - read_offset
            read_offset += src_start_offset
            fd_src.seek(read_offset)
            buf = fd_src.read(read_sz)
            if read_sz != BLOCK_SIZE:
                last_blk_sz = len(buf)
                last_blk_buf = buf
                break
            file_blk_cnt += 1
            md5_digest = md5(buf).hexdigest()
            if md5_digest in blk_md5_ht:
                fd_meta.write(struct.pack('<I', blk_md5_ht[md5_digest]))
            else:
                blk_md5_ht[md5_digest] = g_unique_blk_num
                fd_meta.write(struct.pack('<I', g_unique_blk_num))
                g_unique_blk_num += 1
                fd_base.write(buf)
    if last_blk_sz != 0:
        fd_meta.write(last_blk_buf)
    return (file_blk_cnt, last_blk_sz, meta_offset)


# for debug
# tmp_fs = []
# tmp_non_fs = []
# for frag in g_all_frag_descrs:
#     if frag.is_fs():
#         tmp_fs.append(frag)
#     else:
#         tmp_non_fs.append(frag)
#
#
# g_all_frag_clusters["fs_cluster"].append(tmp_fs)
# g_all_frag_clusters["non_fs_cluster"].append(tmp_non_fs)

# 聚类 DBSCAN

# 所有包含文件系统的分段
g_all_fs_frag_descrs = []
# 所有不含文件系统的分段
g_all_non_fs_frag_descrs = []

for frag in g_all_frag_descrs:
    if frag.is_fs():
        g_all_fs_frag_descrs.append(frag)
    else:
        g_all_non_fs_frag_descrs.append(frag)

# 含FS的段的数量
fs_frag_num = len(g_all_fs_frag_descrs)
# 不含FS的段数量
non_fs_frag_num = len(g_all_non_fs_frag_descrs)

# 处理含FS的分段
# hamming distance square matrix
disX = [[0 for i in range(fs_frag_num)] for j in range(fs_frag_num)]
for i in range(fs_frag_num):
    for j in range(fs_frag_num):
        disX[i][j] = calc_Hamming_dist(g_all_fs_frag_descrs[i].fragment_simhash,
                                       g_all_fs_frag_descrs[j].fragment_simhash)
# DBSCAN 海明距离小于20 每个类中至少包含2个点
clustering = DBSCAN(eps=20, min_samples=2, metric="precomputed").fit_predict(disX)

# 将同类的分段保存
for i in range(len(clustering)):
    if clustering[i] in g_all_frag_clusters["fs_cluster"]:
        g_all_frag_clusters["fs_cluster"][clustering[i]].append(g_all_fs_frag_descrs[i])
    else:
        g_all_frag_clusters["fs_cluster"][clustering[i]] = [g_all_fs_frag_descrs[i]]

# 处理不含FS的分段
for i in range(non_fs_frag_num):
    frag_t = g_all_non_fs_frag_descrs[i].fragment_type
    if frag_t in g_all_frag_clusters["non_fs_cluster"]:
        g_all_frag_clusters["non_fs_cluster"][frag_t].append(g_all_non_fs_frag_descrs[i])
    else:
        g_all_frag_clusters["non_fs_cluster"][frag_t] = [g_all_non_fs_frag_descrs[i]]

# check_all_clusters()


# 大类分裂

max_fs_cluster_num = clustering.max()
max_non_fs_cluster_num = 9

#   待删除的超大小限制的类名
del_fs_cluster_array = []
del_non_fs_cluster_array = []

#   分裂出的新类
new_fs_cluster_array = []
new_non_fs_cluster_array = []

#   含FS
for (clu_name, cluster) in g_all_frag_clusters["fs_cluster"].items():
    # 如果类中只有一个分段
    if len(cluster) == 1:
        continue
    elif get_cluster_total_sz(cluster) > CLUSTER_SPLIT_SIZE:
        new_fs_cluster_array += split_cluster(cluster, CLUSTER_SPLIT_SIZE)
        # g_all_frag_clusters["fs_cluster"].pop(clu_name)
        del_fs_cluster_array.append(clu_name)
    else:
        pass

#   不含FS
for (clu_name, cluster) in g_all_frag_clusters["non_fs_cluster"].items():
    # 如果类中只有一个分段
    if len(cluster) == 1:
        continue
    elif get_cluster_total_sz(cluster) > CLUSTER_SPLIT_SIZE:
        new_non_fs_cluster_array += split_cluster(cluster, CLUSTER_SPLIT_SIZE)
        # g_all_frag_clusters["fs_cluster"].pop(clu_name)
        del_non_fs_cluster_array.append(clu_name)
    else:
        pass

#   删除超大小的类
for k in del_fs_cluster_array:
    g_all_frag_clusters["fs_cluster"].pop(k)

for k in del_non_fs_cluster_array:
    g_all_frag_clusters["non_fs_cluster"].pop(k)
#   增加新的分割后的类
for new_fs_cluster in new_fs_cluster_array:
    max_fs_cluster_num += 1
    g_all_frag_clusters["fs_cluster"][max_fs_cluster_num] = new_fs_cluster
for new_non_fs_cluster in new_non_fs_cluster_array:
    max_non_fs_cluster_num += 1
    g_all_frag_clusters["non_fs_cluster"][max_non_fs_cluster_num] = new_non_fs_cluster

###############################################################################################
# 小类的合并

#   cluster.sz < CLUSTER_SPLIT_SIZE/2 的类
small_sz_fs_cluster = []
small_sz_non_fs_cluster = []
#   待删除的小类
del_samll_fs_cluster_array = []
del_samll_non_fs_cluster_array = []
#   新增的合并类
new_merged_fs_cluster_array = []
new_merged_non_fs_cluster_array = []
#   含FS
for (clu_name, cluster) in g_all_frag_clusters["fs_cluster"].items():
    clu_sz = get_cluster_total_sz(cluster)
    if clu_sz <= CLUSTER_SPLIT_SIZE // 2:
        small_sz_fs_cluster.append((clu_name, clu_sz))
#   不含FS
for (clu_name, cluster) in g_all_frag_clusters["non_fs_cluster"].items():
    clu_sz = get_cluster_total_sz(cluster)
    if clu_sz <= CLUSTER_SPLIT_SIZE // 2:
        small_sz_non_fs_cluster.append((clu_name, clu_sz))

if len(small_sz_fs_cluster) > 1:
    small_sz_fs_cluster = sorted(small_sz_fs_cluster, key=lambda item: item[1])
    new_clu_sz = 0
    tmp_frag_arr = []
    for (clu_name, clu_sz) in small_sz_fs_cluster:
        if new_clu_sz + clu_sz > CLUSTER_SPLIT_SIZE:
            new_merged_fs_cluster_array.append(tmp_frag_arr)
            tmp_frag_arr = g_all_frag_clusters["fs_cluster"][clu_name]
            new_clu_sz = clu_sz
        else:
            tmp_frag_arr += g_all_frag_clusters["fs_cluster"][clu_name]
            new_clu_sz += clu_sz
    if len(tmp_frag_arr) != 0:
        new_merged_fs_cluster_array.append(tmp_frag_arr)
    for (clu_name, clu_sz) in small_sz_fs_cluster:
        g_all_frag_clusters["fs_cluster"].pop(clu_name)
    for cluster in new_merged_fs_cluster_array:
        max_fs_cluster_num += 1
        g_all_frag_clusters["fs_cluster"][max_fs_cluster_num] = cluster

if len(small_sz_non_fs_cluster) > 1:
    small_sz_non_fs_cluster = sorted(small_sz_non_fs_cluster, key=lambda item: item[1])
    new_clu_sz = 0
    tmp_frag_arr = []
    for (clu_name, clu_sz) in small_sz_non_fs_cluster:
        if new_clu_sz + clu_sz > CLUSTER_SPLIT_SIZE:
            new_merged_non_fs_cluster_array.append(tmp_frag_arr)
            tmp_frag_arr = g_all_frag_clusters["non_fs_cluster"][clu_name]
            new_clu_sz = clu_sz
        else:
            tmp_frag_arr += g_all_frag_clusters["non_fs_cluster"][clu_name]
            new_clu_sz += clu_sz
    if len(tmp_frag_arr) != 0:
        new_merged_non_fs_cluster_array.append(tmp_frag_arr)
    for (clu_name, clu_sz) in small_sz_non_fs_cluster:
        g_all_frag_clusters["non_fs_cluster"].pop(clu_name)
    for cluster in new_merged_non_fs_cluster_array:
        max_non_fs_cluster_num += 1
        g_all_frag_clusters["non_fs_cluster"][max_non_fs_cluster_num] = cluster

##################################################################################################

# print("\n\nAFTER MERGE & SPLIT")
# check_all_clusters()


# exit(0)
#
# for frag in g_all_fs_frag_descrs:
#     print(frag.fragment_name)
# print(clustering)
#

# 分段名-->类.json的映射
frag_cluster_map = {}

# 每一个类单独去重 【含FS的类】
for (clu_name, cluster) in g_all_frag_clusters["fs_cluster"].items():
    # 类中所有文件
    cluster_file_htable = {}
    # 类中所有数据块【定长】
    cluster_blk_htable = {}
    # 处理每一个类中的所有分段【文件级去重+块级去重】
    # 每个类独占一个去重目录
    timestamp = str(int(round(time.time() * 1000)))
    cluster_dedup_path = DEDUP_DEST + timestamp
    cmd = "sudo mkdir {}".format(cluster_dedup_path)
    ret = exec_cmd(cmd)
    if len(ret) != 0:
        print("mkdir error")
        break
    # 创建该类的基础数据块文件和元数据文件
    base_file_path = cluster_dedup_path + "/" + "base.file"
    meta_file_path = cluster_dedup_path + "/" + "meta.file"
    fd_base = open(base_file_path, 'ab+')
    fd_meta = open(meta_file_path, 'ab+')
    # blk num置零
    g_unique_blk_num = 0
    cluster_json_path = cluster_dedup_path + '.json'
    # for debug
    # tar = tarfile.open(cluster_dedup_path + "/" + timestamp + ".tar.gz", "x:gz")
    # debug end
    for frag in cluster:
        # 获取该分段文件系统中的所有文件信息
        files_htable = get_fs_frag_file_info(frag)
        # 添加一条分段名到类json的映射
        frag_cluster_map[frag.fragment_name] = cluster_json_path
        # 挂载该分区
        next_loop = exec_cmd("losetup -f")
        next_loop = next_loop[0].strip('\n')
        ret = mount_partition(frag, next_loop, MOUNT_PATH)
        if ret == False:
            print("mount partition error")
            break
        # 遍历所有文件并去重
        for (k, v) in files_htable.items():
            # do not handle special files, e.g. socket fifo
            if k == "None":
                continue
            # 如果所属类中 该文件第一次出现: add into cluster_file_htable
            if k not in cluster_file_htable:
                if v["size"] < BLOCK_SIZE:
                    # 对于小于BLOCK_SIZE的文件 只进行文件级去重
                    dest_file = cluster_dedup_path + "/" + k + ".file"
                    # dest_file = cluster_dedup_path + v["real_dir"][0]
                    # copy
                    # tar.add(v["real_dir"][0])
                    shutil.copyfile(v["real_dir"][0], dest_file, follow_symlinks=True)
                    # os_copy(v["real_dir"][0], dest_file)
                    # print("copy file {} finish".format(v["real_dir"][0]))
                    # and record
                    cluster_file_htable[k] = {"is_dedup": 0, "file_size": v["size"], "dest_path": dest_file,
                                              "block_num": 0, "last_blk_size": v["size"], "meta_path": "None",
                                              "meta_offset": -1}
                else:
                    # 如果文件大于BLOCK_SIZE
                    # (block_num, last_blk_sz, meta_offset) = file_dedup_fsp(v["real_dir"][0], fd_base, fd_meta,
                    #                                                        cluster_blk_htable)
                    fd_src = open(v["real_dir"][0], 'rb')
                    # (block_num, last_blk_sz, meta_offset) = file_dedup_fsp_comm(fd_src, 0, v["size"], fd_base, fd_meta,
                    #                                                             cluster_blk_htable, True)
                    (block_num, last_blk_sz, meta_offset) = file_dedup_fsp_comm2(fd_src, 0, v["size"], fd_base, fd_meta,
                                                                                 cluster_blk_htable, True, v["f_info"])
                    cluster_file_htable[k] = {"is_dedup": 1, "file_size": v["size"], "dest_path": base_file_path,
                                              "block_num": block_num, "last_blk_size": last_blk_sz,
                                              "meta_path": meta_file_path, "meta_offset": meta_offset}
                    fd_src.close()
        # 卸载分区
        umount_partition(frag, next_loop, MOUNT_PATH)
    # save cluster file htable
    with open(cluster_json_path, 'w+') as outfile:
        json.dump(cluster_file_htable, outfile, ensure_ascii=False)
        outfile.write('\n')
    # tar.close()

    # file close
    fd_base.close()
    fd_meta.close()

# 每一个类单独去重 【不含FS的类】
for (clu_name, cluster) in g_all_frag_clusters["non_fs_cluster"].items():
    # 类中所有文件
    cluster_file_htable = {}
    # 类中所有数据块【定长】
    cluster_blk_htable = {}
    # 处理每一个类中的所有分段【文件级去重+块级去重】
    # 每个类独占一个去重目录
    timestamp = str(int(round(time.time() * 1000)))
    cluster_dedup_path = DEDUP_DEST + timestamp
    cmd = "sudo mkdir {}".format(cluster_dedup_path)
    ret = exec_cmd(cmd)
    if len(ret) != 0:
        print("mkdir error")
        break
    # 创建该类的基础数据块文件和元数据文件
    base_file_path = cluster_dedup_path + "/" + "base.file"
    meta_file_path = cluster_dedup_path + "/" + "meta.file"
    fd_base = open(base_file_path, 'ab+')
    fd_meta = open(meta_file_path, 'ab+')
    # blk num置零
    g_unique_blk_num = 0
    cluster_json_path = cluster_dedup_path + '.json'
    for frag in cluster:
        # 添加一条分段名到类json的映射
        frag_cluster_map[frag.fragment_name] = cluster_json_path
        if frag.fragment_size < BLOCK_SIZE:
            fd_src = open(frag.src_path_name, 'rb')
            f_dest = cluster_dedup_path + "/" + frag.fragment_name
            fd_dest = open(f_dest, 'wb+')
            bytes_copy2file(fd_src, fd_dest, frag.fragment_offset * SECTOR_SIZE, frag.fragment_size)
            cluster_file_htable[frag.fragment_name] = {"is_dedup": 0, "file_size": frag.fragment_size,
                                                       "dest_path": f_dest,
                                                       "block_num": 0, "last_blk_size": frag.fragment_size,
                                                       "meta_path": "None",
                                                       "meta_offset": -1}
            fd_src.close()
            fd_dest.close()
        else:
            fd_src = open(frag.src_path_name, 'rb')
            (block_num, last_blk_sz, meta_offset) = file_dedup_fsp_comm2(fd_src, frag.fragment_offset * SECTOR_SIZE,
                                                                         frag.fragment_size, fd_base, fd_meta,
                                                                         cluster_blk_htable, False, {})
            cluster_file_htable[frag.fragment_name] = {"is_dedup": 1, "file_size": frag.fragment_size,
                                                       "dest_path": base_file_path,
                                                       "block_num": block_num, "last_blk_size": last_blk_sz,
                                                       "meta_path": meta_file_path, "meta_offset": meta_offset}

            fd_src.close()
    # save cluster file htable
    with open(cluster_json_path, 'w+') as outfile:
        json.dump(cluster_file_htable, outfile, ensure_ascii=False)
        outfile.write('\n')

    # file close
    fd_base.close()
    fd_meta.close()
# save frag to cluster map
with open(DEDUP_DEST + "/" + "frag_cluster.map.json", 'w+') as outfile:
    json.dump(frag_cluster_map, outfile, ensure_ascii=False)
    outfile.write('\n')

# for frag in g_all_frag_descrs:
#     if frag.is_fs():
#         frag.check()
