from hashlib import md5
from collections import Counter
import sys

# import matplotlib.pyplot as plt
BLANK_BLOCK_MD5_1KB = "620f0b67a91f7f74151bc5be745b7110"
BLANK_BLOCK_MD5_1MB = "b6d81b360a5672d80c27430f39153e2c"
BLANK_BLOCK_MD5_4KB = "620f0b67a91f7f74151bc5be745b7110"
# if len(sys.argv) < 2:
#     exit(-1)


BLOCK_SIZE = 4096


def get_chunk_md5(filename):
    md5_arr = []
    with open(filename, 'rb') as f:
        file_blk_cnt = 0
        # print(md5(f.read()).hexdigest())
        while True:
            offset_tmp = file_blk_cnt * BLOCK_SIZE
            f.seek(offset_tmp)
            buf = f.read(BLOCK_SIZE)
            if len(buf) != BLOCK_SIZE:
                last_blk_sz = len(buf)
                if last_blk_sz == 0:
                    break
                # last_blk_buf = buf
                blk_md5 = md5(buf).hexdigest()
                md5_arr.append(blk_md5)
                print("last", last_blk_sz, blk_md5)
                break
            file_blk_cnt += 1
            blk_md5 = md5(buf).hexdigest()
            # md5_arr.append(blk_md5)
            if blk_md5 != BLANK_BLOCK_MD5_4KB:
                md5_arr.append(blk_md5)
            if blk_md5 == "4ce03cf381c94f2b03bfb7cadd0021bf":
            # if blk_md5 == "bd2a85559944833ebb9a29c4c468a742":
                print(offset_tmp)
            # print(BLOCK_SIZE, blk_md5)
    return md5_arr


# centos65_1 = "/data/vms/centos6.5.basicserver.001.qcow2"
centos65_1 = "/data/vms/ubuntu14.basicserver.002.qcow2"
centos65_2 = "/data/vms/centos6.5.basicserver.002.qcow2"

centos65_1_md5_arr = get_chunk_md5(centos65_1)
# centos65_2_md5_arr = get_chunk_md5(centos65_2)

centos65_1_md5_set = set(centos65_1_md5_arr)


# centos65_2_md5_set = set(centos65_2_md5_arr)

centos65_1_dict = Counter(centos65_1_md5_arr)
# centos65_2_dict = Counter(centos65_2_md5_arr)

centos65_1_dict_most = centos65_1_dict.most_common(20)
# centos65_2_dict_most = centos65_2_dict.most_common(20)

# centos65_1_dict_T = dict(zip(centos65_1_dict.values(), centos65_1_dict.keys()))
# centos65_2_dict_T = dict(zip(centos65_2_dict.values(), centos65_2_dict.keys()))

print("centos65_1_dict_most", centos65_1_dict_most)
# print("centos65_2_dict_most", centos65_2_dict_most)

exit(0)

print("centos65_1_dict.values()", Counter(centos65_1_dict.values()))
print("centos65_2_dict.values()", Counter(centos65_2_dict.values()))

centos65_1_unique_md5_arr = []
centos65_2_unique_md5_arr = []
for (k, v) in centos65_1_dict.items():
    if v == 1:
        centos65_1_unique_md5_arr.append(k)
for (k, v) in centos65_2_dict.items():
    if v == 1:
        centos65_2_unique_md5_arr.append(k)

centos65_1_unique_md5_set = set(centos65_1_unique_md5_arr)
centos65_2_unique_md5_set = set(centos65_2_unique_md5_arr)

print("1 & 2:", len(centos65_1_md5_set & centos65_2_md5_set))
print("1 & 2(unique):", len(centos65_1_unique_md5_set & centos65_2_unique_md5_set))

print("&&:", len((centos65_1_md5_set & centos65_2_md5_set) & (centos65_1_unique_md5_set & centos65_2_unique_md5_set)))

# print(centos65_1_dict_T)
# print(centos65_2_dict_T)

exit(0)

centos7_1 = "/data/tmp/centos7.everything.001.vmdk"
win2012r2_1 = "/data/tmp/windowsserver.2012r2.001.vmdk"
centos7_2 = "/data/tmp/centos7.everything.002.vmdk"
win2012r2_2 = "/data/tmp/windowsserver.2012r2.002.vmdk"

test_file_1 = "/data/tmp/testfiles.001.vmdk"
test_file_2 = "/data/tmp/testfiles.002.vmdk"
test_file_3 = "/data/tmp/testfiles.003.vmdk"
test_file_4 = "/data/tmp/testfiles.004.vmdk"
test_file_5 = "/data/tmp/testfiles.005.vmdk"

test_file_1_md5_arr = get_chunk_md5(test_file_1)
test_file_2_md5_arr = get_chunk_md5(test_file_2)
test_file_3_md5_arr = get_chunk_md5(test_file_3)
test_file_4_md5_arr = get_chunk_md5(test_file_4)
test_file_5_md5_arr = get_chunk_md5(test_file_5)
# centos7_1_md5_arr = get_chunk_md5(centos7_1)
# centos7_2_md5_arr = get_chunk_md5(centos7_2)
# win2012r2_1_md5_arr = get_chunk_md5(win2012r2_1)
# win2012r2_2_md5_arr = get_chunk_md5(win2012r2_2)

test_file_1_md5_set = set(test_file_1_md5_arr)
test_file_2_md5_set = set(test_file_2_md5_arr)
test_file_3_md5_set = set(test_file_3_md5_arr)
test_file_4_md5_set = set(test_file_4_md5_arr)
test_file_5_md5_set = set(test_file_5_md5_arr)
# centos7_1_md5_set = set(centos7_1_md5_arr)
# centos7_2_md5_set = set(centos7_2_md5_arr)
# win2012r2_1_md5_set = set(win2012r2_1_md5_arr)
# win2012r2_2_md5_set = set(win2012r2_2_md5_arr)

# test_file_total_blk = len(test_file_1_md5_arr) * 5
# print("test files total blk num:", test_file_total_blk)
print("test file 1 unique:", len(test_file_1_md5_set))
print("test file 2 unique:", len(test_file_2_md5_set))
print("test file 3 unique:", len(test_file_3_md5_set))
print("test file 4 unique:", len(test_file_4_md5_set))
print("test file 5 unique:", len(test_file_5_md5_set))
print("test file dedup blk num:", len(
    test_file_1_md5_set | test_file_2_md5_set | test_file_3_md5_set | test_file_4_md5_set | test_file_5_md5_set))

exit(0)
