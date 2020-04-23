from collections import Counter
from sklearn.cluster import KMeans
from sklearn.cluster import DBSCAN
from sklearn.cluster import AffinityPropagation
from sklearn.cluster import MeanShift
from sklearn.cluster import AgglomerativeClustering
from sklearn.cluster import Birch
from sklearn.cluster import SpectralBiclustering
from sklearn.cluster import SpectralClustering
from sklearn.cluster import SpectralCoclustering
from sklearn.cluster import FeatureAgglomeration
from sklearn.cluster import OPTICS
from sklearn.mixture import GaussianMixture
from sklearn.metrics import calinski_harabaz_score
from sklearn import metrics
from sklearn.metrics.cluster import adjusted_rand_score
from sklearn.metrics import adjusted_mutual_info_score
import numpy as np
import random
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

# (500MB*1024*1024/(16+4))*8 [16B:md5 4B:block_id] 单位：sector
# 即：100GB
CLUSTER_SPLIT_SIZE = 209715200

# FRAG_INFO_PATH = "/data/frag_info/"
# FRAG_INFO_PATH = "/data/frag_info_tmp/"
FRAG_INFO_PATH = "/data/frag_info_qcow2/"
# FRAG_INFO_PATH = "/data/frag_info_test_kmeans/"
# FRAG_INFO_PATH = sys.argv[1]

g_unique_blk_num = 0


# for test


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
        print("fragment_simhash\t{}{}".format(hex(simhash_str1)[2:].zfill(16), hex(simhash_str2)[2:].zfill(16)))

    # get frag simhash
    def get_simhash_str(self):
        simhash_str1, simhash_str2 = struct.unpack('>QQ', self.fragment_simhash)
        return "{}{}".format(hex(simhash_str1)[2:].zfill(16), hex(simhash_str2)[2:].zfill(16))

    # 是否包含文件系统
    def is_fs(self):
        return self.fragment_type != 0 and self.fragment_type != 1 \
               and self.fragment_type != 6 and self.fragment_type != 8


# 存储所有的镜像分段
g_all_frag_descrs = []

# 存储所有的类 每一个类包含N个镜像分段
g_all_frag_clusters = {"fs_cluster": {}, "non_fs_cluster": {}}


# 从镜像描述文件中获取所有分段
def get_frags_info_from_file(img_descr_file):
    ret = []
    with open(img_descr_file, "rb") as f:
        data = f.read(4 * 2 + 8 + 256 * 2 + 4 * 3)
        img_unique_nb, img_type, img_size, img_name, img_path, disk_type, fragment_nums, boot_sector_offset = \
            struct.unpack(
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
    with open(frag_descr.fragment_file_info_path, 'r') as f:
        file_htable = json.load(fp=f)
    return file_htable


# convert to binary string
def convert_bin(s):
    ret = []
    for c in s:
        ret.append(1 if c == '1' else 0)
    return ret


# 计算hamming distance
def calc_hamming_dist(simhash_bytes1, simhash_bytes2):
    ret = 0
    if len(simhash_bytes1) != len(simhash_bytes2):
        return -1
    for i in range(len(simhash_bytes1)):
        for b in (bin(simhash_bytes1[i] ^ simhash_bytes2[i])[2:]):
            ret += 1 if b == '1' else 0
    return int(ret)


def calc_arr_hamming_dist(arr1, arr2):
    # print(arr1)
    # print(arr2)
    ret = 0
    for i in range(len(arr1)):
        if arr1[i] != arr2[i]:
            ret += 1
    return ret


# 获取所有的分段
for root, dirs, files in os.walk(FRAG_INFO_PATH, topdown=False):
    for file in files:
        if os.path.splitext(file)[1] == ".descr":
            g_all_frag_descrs += (get_frags_info_from_file(os.path.join(root, file)))


# for i in range(len(sys.argv)):
#     if i > 0:
#         g_all_frag_descrs += (get_frags_info_from_file(sys.argv[i]))


# linux copy
def os_copy(src, dest):
    cmd = "cp -f \"{}\" \"{}\"".format(src, dest)
    ret = exec_cmd(cmd)
    return True if len(ret) == 0 else False


# 判断数据块是否为0
def is_zero_blk(blk_buf):
    pass


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
            # frag.check_simhash()
    print("----> Non-FS-clusters")
    for (k, v) in g_all_frag_clusters["non_fs_cluster"].items():
        print("cluster[{}]".format(k))
        for frag in v:
            print(frag.fragment_name)
            # frag.check_simhash()


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
        # print(frag.fragment_name)
    else:
        g_all_non_fs_frag_descrs.append(frag)
        # print(frag.fragment_name)

# 打乱
# random.shuffle(g_all_fs_frag_descrs)

# real_label = [0] * 13
# for i in range(5):
#     real_label.append(1)
# for i in range(2):
#     real_label.append(2)
# for i in range(10):
#     real_label.append(3)
# for i in range(8):
#     real_label.append(4)
# for i in range(5):
#     real_label.append(0)
# for i in range(7):
#     real_label.append(6)
# for i in range(17):
#     real_label.append(7)
# for i in range(9):
#     real_label.append(8)
# for i in range(3):
#     real_label.append(9)
# for i in range(5):
#     real_label.append(10)
# for i in range(4):
#     real_label.append(11)
# for i in range(1):
#     real_label.append(12)

#
# for item in g_all_fs_frag_descrs:
#     print(item.fragment_name)
# exit(0)

# 含FS的段的数量
# g_all_fs_frag_descrs *= 4
fs_frag_num = len(g_all_fs_frag_descrs)
# 不含FS的段数量
non_fs_frag_num = len(g_all_non_fs_frag_descrs)

# print("g_all_fs_frag_descrs",g_all_fs_frag_descrs)
# print("g_all_non_fs_frag_descrs",g_all_non_fs_frag_descrs)
#
# exit(0)

# 处理含FS的分段
# hamming distance square matrix
disX = [[0 for i in range(fs_frag_num)] for j in range(fs_frag_num)]
_disX = [[0 for i in range(fs_frag_num)] for j in range(fs_frag_num)]
for i in range(fs_frag_num):
    for j in range(fs_frag_num):
        disX[i][j] = calc_hamming_dist(g_all_fs_frag_descrs[i].fragment_simhash,
                                       g_all_fs_frag_descrs[j].fragment_simhash)
        _disX[i][j] = -disX[i][j]

# print(disX)

# simhash 矩阵
simhash_arr = list()
for i in range(len(g_all_fs_frag_descrs)):
    # print(g_all_fs_frag_descrs[i].get_simhash_str())
    # simhash_arr.append(np.array(convert_bin(format(int(g_all_fs_frag_descrs[i].get_simhash_str(), 16), '#0130b')[2:])))
    simhash_arr.append((convert_bin(format(int(g_all_fs_frag_descrs[i].get_simhash_str(), 16), '#0130b')[2:])))


def compactness_separation_score(x, labels):
    print("num of samples:", len(x))
    print("num of clusters:", len(Counter(labels)))

    def trans(arr):
        ret = [0] * 128
        for i in range(len(arr)):
            ret[i] = 1 if arr[i] == 1 else -1
        return ret

    def get_cluster_center(xdata):
        # ret = np.array(xdata[0])
        ret = np.array([0] * 128)
        for i in xdata:
            ret += np.array(trans(i))
        for i in range(len(ret)):
            ret[i] = 0 if ret[i] <= 0 else 1
        return ret

    def cluster_dist(c1, c2):
        ret = 0
        for p1 in c1:
            for p2 in c2:
                ret += calc_arr_hamming_dist(p1, p2)
        return ret / (len(c1) * len(c2))

    x_map = {}
    for i in range(len(x)):
        if labels[i] in x_map:
            x_map[labels[i]].append(x[i])
        else:
            x_map[labels[i]] = []
            x_map[labels[i]].append(x[i])

    center_map = {}
    for label, sim_arr in x_map.items():
        cluster_center = get_cluster_center(sim_arr)
        center_map[label] = cluster_center

    inner_dist_map = {}
    inner_avg = 0.0
    for label, sim_arr in x_map.items():
        inner_dist_sum = 0
        for sim in sim_arr:
            inner_dist_sum += calc_arr_hamming_dist(sim, center_map[label])
        inner_dist_map[label] = inner_dist_sum / len(sim_arr)
        inner_avg += inner_dist_map[label]
    inner_avg /= len(inner_dist_map)
    # print(inner_dist_map)
    print("inner avg:", inner_avg)

    unique_labels = x_map.keys()
    outer_avg = 0.0
    for label1 in unique_labels:
        for label2 in unique_labels:
            if label1 != label2:
                outer_avg += cluster_dist(x_map[label1], x_map[label2])
                # print("--->",label1, label2, cluster_dist(x_map[label1], x_map[label2]))
    outer_avg /= (len(unique_labels) ** 2)
    print("outer avg", outer_avg)

    if inner_avg == 0.0:
        print("outter/inner:inf")
    else:
        print("outter/inner:", outer_avg / inner_avg)


def check_clustering(frags_arr, labels):
    print(labels)
    dic = {}
    for i in range(len(frags_arr)):
        if labels[i] in dic:
            dic[labels[i]].append(frags_arr[i].fragment_name)
        else:
            dic[labels[i]] = [frags_arr[i].fragment_name]
    for (k, v) in dic.items():
        print("cluster:", k)
        print("num:", len(v))
        print(v)
    # print(frags_arr[i].fragment_name, labels[i])


# for test
# print("KMeans")
# clustering4 = KMeans(n_clusters=2).fit_predict(disX)
# check_clustering(g_all_fs_frag_descrs, clustering4)
# # print("ARI:", adjusted_rand_score(real_label, clustering4))
# score = metrics.calinski_harabasz_score(simhash_arr, clustering4)
# print("CH:", score)
# # print("AMI:", adjusted_mutual_info_score(real_label, clustering4))
# compactness_separation_score(simhash_arr, clustering4)
# exit(0)


# print("DBSCAN")
# # 还行,聚类效果一般，但是去重率会比较高
# clustering = DBSCAN(eps=21, min_samples=1, metric=lambda a, b: calc_arr_hamming_dist(a, b)).fit(simhash_arr)
# check_clustering(g_all_fs_frag_descrs, clustering.labels_)
# print("ARI:", adjusted_rand_score(real_label, clustering.labels_))
# score = metrics.calinski_harabasz_score(simhash_arr, clustering.labels_)
# print("CH:", score)
# print("AMI:", adjusted_mutual_info_score(real_label, clustering.labels_))
# compactness_separation_score(simhash_arr, clustering.labels_)

# print("AffinityPropagation")
# for i in range(10, 300, 2):
#     print("i:", i)
clustering2 = AffinityPropagation(preference=i * (-1), affinity="precomputed").fit(
        _disX)  # affinity必须是precomputed或者欧式距离 无复制镜像的情况下preference=-50 有复制时-170
# check_clustering(g_all_fs_frag_descrs, clustering2.labels_)
# print(len(real_label))
# print(len(clustering2.labels_))
# exit(0)
# print("ARI:", adjusted_rand_score(real_label, clustering2.labels_))
# score = metrics.calinski_harabasz_score(simhash_arr, clustering2.labels_)
# print("CH:", score)
# print("AMI:", adjusted_mutual_info_score(real_label, clustering2.labels_))
# compactness_separation_score(simhash_arr, clustering2.labels_)

# exit(0)

# print("MeanShift")
# clustering3 = MeanShift(bandwidth=66).fit(disX)  # bandwidth=70 划分比较细 100时很粗略
# check_clustering(g_all_fs_frag_descrs, clustering3.labels_)
# print("ARI:", adjusted_rand_score(real_label, clustering3))
# score = metrics.calinski_harabasz_score(simhash_arr, clustering3)
# print("CH:", score)
# print("AMI:", adjusted_mutual_info_score(real_label, clustering3))
# compactness_separation_score(simhash_arr, clustering3)


# exit(0)
#
# print("AgglomerativeClustering 不行[需要n_clusters]")
# clustering4 = AgglomerativeClustering(n).fit_predict(_disX)
# check_clustering(g_all_fs_frag_descrs, clustering4)
#
# # exit(0)
#
# print("KMeans 凑合 需要初始化簇数")
# clustering5 = KMeans(n_clusters=12).fit_predict(disX)
# check_clustering(g_all_fs_frag_descrs, clustering5)
#
# print("Birch 凑合 需要初始化簇数")
# clustering6 = Birch(n_clusters=12).fit_predict(disX)
# check_clustering(g_all_fs_frag_descrs, clustering6)
#
# print("SpectralClustering 需要初始化簇数")
# clustering7 = SpectralClustering().fit_predict(disX)
# check_clustering(g_all_fs_frag_descrs, clustering7)


# exit(0)

# 将同类的分段保存
clustering = clustering2.labels_
for i in range(len(clustering)):
    if clustering[i] in g_all_frag_clusters["fs_cluster"]:
        g_all_frag_clusters["fs_cluster"][clustering[i]].append(g_all_fs_frag_descrs[i])
    else:
        g_all_frag_clusters["fs_cluster"][clustering[i]] = [g_all_fs_frag_descrs[i]]

# 处理不含FS的分段
frag_t = 100
g_all_frag_clusters["non_fs_cluster"][frag_t] = []
for i in range(non_fs_frag_num):
    # frag_t = g_all_non_fs_frag_descrs[i].fragment_type
    g_all_frag_clusters["non_fs_cluster"][frag_t].append(g_all_non_fs_frag_descrs[i])
    # if frag_t in g_all_frag_clusters["non_fs_cluster"]:
    #     g_all_frag_clusters["non_fs_cluster"][frag_t].append(g_all_non_fs_frag_descrs[i])
    # else:
    #     g_all_frag_clusters["non_fs_cluster"][frag_t] = [g_all_non_fs_frag_descrs[i]]

check_all_clusters()


# exit(0)


# here
def merge_split():
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
        elif get_cluster_total_sz(cluster) > CLUSTER_SPLIT_SIZE // 2:
            new_fs_cluster_array += split_cluster(cluster, CLUSTER_SPLIT_SIZE // 2)
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
    return
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

    print("\n\nAFTER MERGE & SPLIT")
    check_all_clusters()


# merge_split()
# print("\n\nAFTER MERGE & SPLIT")
# check_all_clusters()
# exit(0)

# for frag in g_all_fs_frag_descrs:
#     print(frag.fragment_name)
# print(clustering)
#

# 分段名-->类.json的映射
frag_cluster_map = {}


# 获取分段的定长分块的MD5
def get_frag_fixed_chunk_md5_from_file(frag_descr):
    frag_md5_arr_tmp = []
    with open(frag_descr.fragment_file_info_path, "r") as f:
        frag_blk_info_tmp = json.load(fp=f)
    md5_file_path = frag_blk_info_tmp["frag_block_md5_file"]
    frag_block_num = frag_blk_info_tmp["frag_block_info"]["block_num"]
    blk_cnt = 0
    with open(md5_file_path, "rb") as f:
        while blk_cnt < frag_block_num:
            # f.seek(blk_cnt * 16)
            data = f.read(16)
            md5_str1, md5_str2 = struct.unpack('>QQ', data)
            frag_md5_arr_tmp.append(str(hex(md5_str1)[2:].zfill(16)) + str(hex(md5_str2)[2:].zfill(16)))
            # print((md5))
            blk_cnt += 1
    return frag_md5_arr_tmp, frag_blk_info_tmp["frag_block_info"]


# 镜像段到去重文件的映射
# |镜像段名称：
#       |--blk_num[不包含最后一个small_blk]
#       |--meta_file_path
#       |--meta_offset
#       |--base_file_path
#       |--has_last_blk
#       |--last_blk_file_path[存储所有分段的最后一个small block]
#       |--last_blk_offset【最后一个小分块在last_blk_file_path中的偏移】
#       |--last_blk_size

# for debug
# for (clu_name, cluster) in g_all_frag_clusters["fs_cluster"].items():
#     print("-->now handle cluster {}".format(clu_name))
#     # 类中所有分块的MD5-->唯一块号
#     cluster_blk_md5_htable = {}
#     # 每个类独占一个去重目录
#     timestamp = str(int(round(time.time() * 1000)))
#     cluster_dedup_path = DEDUP_DEST + timestamp
#     # cmd = "sudo mkdir {}".format(cluster_dedup_path)
#     # ret = exec_cmd(cmd)
#     # if len(ret) != 0:
#     #     print("mkdir error")
#     #     break
#     # continue
#     # 创建该类的基础数据块文件和元数据文件
#     # base_file_path = cluster_dedup_path + "/" + "base.file"
#     # meta_file_path = cluster_dedup_path + "/" + "meta.file"
#     # last_blk_file_path = cluster_dedup_path + "/" + "last_blk.file"
#     # fd_base = open(base_file_path, 'ab+')
#     # fd_meta = open(meta_file_path, 'ab+')
#     # fd_last_blk = open(last_blk_file_path, 'ab+')
#     # print("create meta base lst_blk file")
#     # blk num置零
#     g_unique_blk_num = 0
#     # frag_cluster_map的保存路径
#     cluster_json_path = cluster_dedup_path + '.json'
#     for frag in cluster:
#         print("now dedup frag[{}] in cluster[{}]".format(frag.fragment_name, clu_name))
#         # 获取分段的所有分块的md5和最后一块的信息
#         (frag_md5_arr, frag_blk_info) = get_frag_fixed_chunk_md5_from_file(frag)
#         # src
#         fd_src = open(frag.src_path_name, "rb")
#         # 分段中的每个块
#         blk_num_without_last = int(frag_blk_info["block_num"])
#         print("frag fragment_offset is {}".format(frag.fragment_offset))
#         # msg = input()
#         # debug cmp block md5
#         for i in range(blk_num_without_last):
#             blk_md5 = frag_md5_arr[i]
#             src_blk_offset = i * BLOCK_SIZE + frag.fragment_offset * SECTOR_SIZE
#
#             fd_src.seek(src_blk_offset)
#             buf = fd_src.read(BLOCK_SIZE)
#             src_blk_md5 = md5(buf).hexdigest()
#             if blk_md5 == src_blk_md5:
#                 print("blk {} same".format(i))
#             else:
#                 print("blk {} diff: {} {}".format(i, blk_md5, src_blk_md5))
#         fd_src.close()
#
# exit(0)

# 每一个类单独去重 【含FS的类】
for (clu_name, cluster) in g_all_frag_clusters["fs_cluster"].items():
    print("-->now handle cluster {}".format(clu_name))
    # 类中所有分块的MD5-->唯一块号
    cluster_blk_md5_htable = {}
    # 每个类独占一个去重目录
    timestamp = str(int(round(time.time() * 1000)))
    cluster_dedup_path = DEDUP_DEST + timestamp
    cmd = "sudo mkdir {}".format(cluster_dedup_path)
    ret = exec_cmd(cmd)
    if len(ret) != 0:
        print("mkdir error")
        break
    # continue
    # 创建该类的基础数据块文件和元数据文件
    base_file_path = cluster_dedup_path + "/" + "base.file"
    meta_file_path = cluster_dedup_path + "/" + "meta.file"
    last_blk_file_path = cluster_dedup_path + "/" + "last_blk.file"
    fd_base = open(base_file_path, 'ab+')
    fd_meta = open(meta_file_path, 'ab+')
    fd_last_blk = open(last_blk_file_path, 'ab+')
    print("create meta base lst_blk file")
    # blk num置零
    g_unique_blk_num = 0
    # frag_cluster_map的保存路径
    cluster_json_path = cluster_dedup_path + '.json'
    for frag in cluster:
        print("now dedup frag[{}] in cluster[{}]".format(frag.fragment_name, clu_name))
        # 获取分段的所有分块的md5和最后一块的信息
        (frag_md5_arr, frag_blk_info) = get_frag_fixed_chunk_md5_from_file(frag)
        # src
        fd_src = open(frag.src_path_name, "rb")
        # 分段中的每个块
        blk_num_without_last = int(frag_blk_info["block_num"])
        # 保存frag_name-->去重文件的映射
        frag_cluster_map[frag.fragment_name] = {"blk_num": blk_num_without_last, "meta_file_path": meta_file_path,
                                                "meta_offset": fd_meta.tell(), "base_file_path": base_file_path,
                                                "has_last_blk": frag_blk_info["has_last_block"]}
        for i in range(blk_num_without_last):
            blk_md5 = frag_md5_arr[i]
            # 如果md5已存在，则追加唯一块号到meta
            if blk_md5 in cluster_blk_md5_htable:
                fd_meta.write(struct.pack('<I', cluster_blk_md5_htable[blk_md5]))
                # print("block[{}]: find dedup blk, write meta".format(i))
                # time.sleep(0.5)
            else:
                src_blk_offset = i * BLOCK_SIZE + frag.fragment_offset * SECTOR_SIZE
                fd_src.seek(src_blk_offset)
                buf = fd_src.read(BLOCK_SIZE)
                cluster_blk_md5_htable[blk_md5] = g_unique_blk_num
                fd_meta.write(struct.pack('<I', g_unique_blk_num))
                g_unique_blk_num += 1
                fd_base.write(buf)
                # print("block[{}]: find uinique blk, write meta and base".format(i))
                # time.sleep(0.5)
        # 处理最后一个分块 追加到last_blk_file_path
        if frag_blk_info["has_last_block"] == 1:
            print("has lst blk, write lst")
            frag_cluster_map[frag.fragment_name]["last_blk_file_path"] = last_blk_file_path
            frag_cluster_map[frag.fragment_name]["last_blk_offset"] = fd_last_blk.tell()
            last_block_offset_in_src = int(frag_blk_info["last_block_offset"])
            last_block_sz = int(frag_blk_info["last_block_size"])
            frag_cluster_map[frag.fragment_name]["last_blk_size"] = last_block_sz
            fd_src.seek(last_block_offset_in_src)
            fd_last_blk.write(fd_src.read(last_block_sz))
        # 一个镜像段处理完成
        fd_src.close()
        # 保存frag_cluster_map的路径到fragment_file_info中，用于重构时从img->frag_name->frag_cluster_map->meta/base
        frag_info_json = {"frag_block_info": frag_blk_info,
                          "frag_block_md5_file": FRAG_INFO_PATH + frag.fragment_name + ".md5.file",
                          "dedup_map_json": cluster_json_path}
        with open(frag.fragment_file_info_path, 'w+') as outfile:
            json.dump(frag_info_json, outfile, ensure_ascii=False)
            outfile.write('\n')

    # 类中的所有镜像段处理完成
    # 保存frag_cluster_map
    with open(cluster_json_path, 'w+') as outfile:
        json.dump(frag_cluster_map, outfile, ensure_ascii=False)
        outfile.write('\n')
    fd_meta.close()
    fd_base.close()
    fd_last_blk.close()

# 每一个类单独去重 【不含FS的类】
for (clu_name, cluster) in g_all_frag_clusters["non_fs_cluster"].items():
    print("-->now handle cluster {}".format(clu_name))
    # 类中所有分块的MD5-->唯一块号
    cluster_blk_md5_htable = {}
    # 每个类独占一个去重目录
    timestamp = str(int(round(time.time() * 1000)))
    cluster_dedup_path = DEDUP_DEST + timestamp
    cmd = "sudo mkdir {}".format(cluster_dedup_path)
    ret = exec_cmd(cmd)
    if len(ret) != 0:
        print("mkdir error")
        break
    # continue
    # 创建该类的基础数据块文件和元数据文件
    base_file_path = cluster_dedup_path + "/" + "base.file"
    meta_file_path = cluster_dedup_path + "/" + "meta.file"
    last_blk_file_path = cluster_dedup_path + "/" + "last_blk.file"
    fd_base = open(base_file_path, 'ab+')
    fd_meta = open(meta_file_path, 'ab+')
    fd_last_blk = open(last_blk_file_path, 'ab+')
    print("create meta base lst_blk file")
    # blk num置零
    g_unique_blk_num = 0
    # frag_cluster_map的保存路径
    cluster_json_path = cluster_dedup_path + '.json'
    for frag in cluster:
        print("now dedup frag[{}] in cluster[{}]".format(frag.fragment_name, clu_name))
        # 获取分段的所有分块的md5和最后一块的信息
        (frag_md5_arr, frag_blk_info) = get_frag_fixed_chunk_md5_from_file(frag)
        # src
        fd_src = open(frag.src_path_name, "rb")
        # 分段中的每个块
        blk_num_without_last = int(frag_blk_info["block_num"])
        # 保存frag_name-->去重文件的映射
        frag_cluster_map[frag.fragment_name] = {"blk_num": blk_num_without_last, "meta_file_path": meta_file_path,
                                                "meta_offset": fd_meta.tell(), "base_file_path": base_file_path,
                                                "has_last_blk": frag_blk_info["has_last_block"]}
        for i in range(blk_num_without_last):
            blk_md5 = frag_md5_arr[i]
            # 如果md5已存在，则追加唯一块号到meta
            if blk_md5 in cluster_blk_md5_htable:
                fd_meta.write(struct.pack('<I', cluster_blk_md5_htable[blk_md5]))
                # print("block[{}]: find dedup blk, write meta".format(i))
                # time.sleep(0.5)
            else:
                src_blk_offset = i * BLOCK_SIZE + frag.fragment_offset * SECTOR_SIZE
                fd_src.seek(src_blk_offset)
                buf = fd_src.read(BLOCK_SIZE)
                cluster_blk_md5_htable[blk_md5] = g_unique_blk_num
                fd_meta.write(struct.pack('<I', g_unique_blk_num))
                g_unique_blk_num += 1
                fd_base.write(buf)
                # print("block[{}]: find uinique blk, write meta and base".format(i))
                # time.sleep(0.5)
        # 处理最后一个分块 追加到last_blk_file_path
        if frag_blk_info["has_last_block"] == 1:
            print("has lst blk, write lst")
            frag_cluster_map[frag.fragment_name]["last_blk_file_path"] = last_blk_file_path
            frag_cluster_map[frag.fragment_name]["last_blk_offset"] = fd_last_blk.tell()
            last_block_offset_in_src = int(frag_blk_info["last_block_offset"])
            last_block_sz = int(frag_blk_info["last_block_size"])
            frag_cluster_map[frag.fragment_name]["last_blk_size"] = last_block_sz
            fd_src.seek(last_block_offset_in_src)
            fd_last_blk.write(fd_src.read(last_block_sz))
        # 一个镜像段处理完成
        fd_src.close()
        # 保存frag_cluster_map的路径到fragment_file_info中，用于重构时从img->frag_name->frag_cluster_map->meta/base
        frag_info_json = {"frag_block_info": frag_blk_info,
                          "frag_block_md5_file": FRAG_INFO_PATH + frag.fragment_name + ".md5.file",
                          "dedup_map_json": cluster_json_path}
        with open(frag.fragment_file_info_path, 'w+') as outfile:
            json.dump(frag_info_json, outfile, ensure_ascii=False)
            outfile.write('\n')
    # 类中的所有镜像段处理完成
    # 保存frag_cluster_map
    with open(cluster_json_path, 'w+') as outfile:
        json.dump(frag_cluster_map, outfile, ensure_ascii=False)
        outfile.write('\n')
    fd_meta.close()
    fd_base.close()
    fd_last_blk.close()

print("dedup finish")
exit(0)
