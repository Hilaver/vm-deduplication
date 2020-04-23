from sklearn.cluster import KMeans
from hashlib import md5
# import tarfile
import struct
import shutil
import ctypes
import json
import time
import sys
import os

DEDUP_DEST = "/data/datastore/dedup_kmeans/"
IMG_PATH = "/data/images/"
IMG_FINGER_PATH = "/data/imgs_fingerset/"
SECTOR_SIZE = 512
BLOCK_SIZE = 4096

# 所有镜像名
g_imgs = []


# 读取文件的MD5集合
def read_file(filename):
    x = []
    with open(filename, 'r+') as f:
        for line in f:
            x.append(line.strip('\n'))
    return x


# 定长分块计算文件MD5
def file_chunk_md5(file_path):
    md5_set = []
    with open(file_path, 'rb') as f:
        file_blk_cnt = 0
        # print(md5(f.read()).hexdigest())
        while True:
            f.seek(file_blk_cnt * BLOCK_SIZE)
            buf = f.read(BLOCK_SIZE)
            if len(buf) != BLOCK_SIZE:
                last_blk_sz = len(buf)
                # last_blk_buf = buf
                blk_md5 = md5(buf).hexdigest()
                # print(last_blk_sz, blk_md5)
                md5_set.append(blk_md5)
                break
            file_blk_cnt += 1
            blk_md5 = md5(buf).hexdigest()
            md5_set.append(blk_md5)
            # print(BLOCK_SIZE, blk_md5)
    return md5_set


# 文件定长分块去重
def file_fsp(src_file,base_file,meta_file):
    fd_base = open(base_file, 'wb+')
    fd_meta = open(meta_file, 'wb+')
    md5_set = set()
    md5_array=[]
    infile_unique_blk=0
    with open(src_file, 'rb') as f:
        file_blk_cnt = 0
        # print(md5(f.read()).hexdigest())
        while True:
            f.seek(file_blk_cnt * BLOCK_SIZE)
            buf = f.read(BLOCK_SIZE)
            if len(buf) != BLOCK_SIZE:
                last_blk_sz = len(buf)
                # last_blk_buf = buf
                blk_md5 = md5(buf).hexdigest()
                # print(last_blk_sz, blk_md5)
                md5_array.append(blk_md5)
                if(blk_md5 not in md5_set):
                    md5_set.add(blk_md5)
                    infile_unique_blk += 1
                    fd_base.write(buf)
                fd_meta.write(struct.pack('<I', infile_unique_blk))
                break
            else:
                file_blk_cnt += 1
                blk_md5 = md5(buf).hexdigest()
                md5_array.append(blk_md5)
                if(blk_md5 not in md5_set):
                    md5_set.add(blk_md5)
                    infile_unique_blk+=1
                    fd_base.write(buf)
                fd_meta.write(struct.pack('<I', infile_unique_blk))
            # print(BLOCK_SIZE, blk_md5)
    return md5_array


# 保存镜像MD5集合 -> img_name.digest
def save_file_digest(digest_set, dest_path):
    with open(dest_path, 'w+') as f:
        for digest in digest_set:
            f.write(digest + "\n")
    return


# 计算两个镜像指纹集合的相似度
def get_similarity(digest_set_file_1, digest_set_file_2):
    digest_set_1 = set(read_file(digest_set_file_1))
    digest_set_2 = set(read_file(digest_set_file_2))
    return 2.0 * float(len(digest_set_1.intersection(digest_set_2))) / (
                float(len(digest_set_1)) + float(len(digest_set_2)))


# 获取所有的镜像文件  定长分块计算MD5
for root, dirs, files in os.walk(IMG_PATH, topdown=False):
    for file in files:
        g_imgs.append(file)
        save_file_digest(file_chunk_md5(IMG_PATH+file),IMG_FINGER_PATH+file+".digest")
        # save_file_digest(file_fsp(IMG_PATH+file,DEDUP_DEST+file+".base",DEDUP_DEST+file+".meta"),IMG_FINGER_PATH+file+".digest")

# save_file_digest(file_fsp("/zcy/deduputil-1.4.1.tar.gz",DEDUP_DEST+"deduputil-1.4.1.tar.gz"+".base",DEDUP_DEST+"deduputil-1.4.1.tar.gz"+".meta"),IMG_FINGER_PATH+"deduputil-1.4.1.tar.gz"+".digest")

# 镜像个数
g_imgs_num = len(g_imgs)

# 所有镜像之间的相似度
g_similarity = [[0.0 for j in range(g_imgs_num)] for i in range(g_imgs_num)]

# 计算相似度
for i in range(g_imgs_num):
    for j in range(g_imgs_num):
        if(i==j):
            g_similarity[i][j]=1.0
        else:
            g_similarity[i][j] = get_similarity(IMG_FINGER_PATH + g_imgs[i] + ".digest",
                                            IMG_FINGER_PATH + g_imgs[j] + ".digest")

print(g_similarity)

# K-means 大概17个分组
y_pred=KMeans(n_clusters=17, random_state=9).fit_predict(g_similarity)

print(g_imgs)
print(y_pred)

# 分类结果
g_clusters={}

for i in range(len(y_pred)):
    if y_pred[i] not in g_clusters:
        g_clusters[y_pred[i]]=[g_imgs[i]]
    else:
        g_clusters[y_pred[i]].append(g_imgs[i])

print(g_clusters)

# 保存到json
with open(DEDUP_DEST+"clustering_ret.json", 'w+') as outfile:
    json.dump(g_clusters, outfile, ensure_ascii=False)
    outfile.write('\n')


# 分类去重
for key,val in g_clusters.items():
    # 类的数据块文件和元数据文件
    clu_base_file=DEDUP_DEST+"cluster_"+str(key)+".base"
    clu_meta_file=DEDUP_DEST+"cluster_"+str(key)+".meta"
    fd_clu_base=open(clu_base_file,"wb+")
    fd_clu_meta=open(clu_meta_file,"wb+")
    # 类的分块指纹set
    clu_finger_set=set()
    # 类的唯一块编号
    clu_unique_blk=0
    for img in val:
        md5_arr=read_file(IMG_FINGER_PATH+img+".digest")
        infile_blk_cnt=0
        fd_img=open(IMG_PATH+img,"rb")
        for md5 in md5_arr:
            if md5 not in clu_finger_set:
                fd_img.seek(infile_blk_cnt*BLOCK_SIZE)
                fd_clu_base.write(fd_img.read(BLOCK_SIZE))
                clu_finger_set.add(md5)
                clu_unique_blk += 1
            fd_clu_meta.write(struct.pack('<I', clu_unique_blk))
            infile_blk_cnt+=1
        fd_img.close()
    fd_clu_meta.close()
    fd_clu_base.close()

