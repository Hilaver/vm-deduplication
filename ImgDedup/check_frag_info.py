import struct
import sys
import os

FRAG_INFO_PATH = "/data/frag_info/"


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

    # 是否包含文件系统
    def is_fs(self):
        return self.fragment_file_info_path != "NULL"


# 存储所有的镜像分段
g_all_frag_descrs = []


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

# 如果无命令行参数，从 FRAG_INFO_PATH 中检索所有后缀名为 .descr的镜像描述文件并解析
if len(sys.argv) == 1:
    # 获取所有的分段
    for root, dirs, files in os.walk(FRAG_INFO_PATH, topdown=False):
        for file in files:
            if os.path.splitext(file)[1] == ".descr":
                g_all_frag_descrs += (get_frags_info_from_file(os.path.join(root, file)))

# 如果有一个命令行参数，且该参数是一个目录，检索该目录中的所有镜像描述文件并解析
elif len(sys.argv) == 2:
    if os.path.isdir(sys.argv[1]):
        # 获取所有的分段
        for root, dirs, files in os.walk(sys.argv[1], topdown=False):
            for file in files:
                if os.path.splitext(file)[1] == ".descr":
                    g_all_frag_descrs += (get_frags_info_from_file(os.path.join(root, file)))
    else:
        if os.path.splitext(sys.argv[1])[1] == ".descr":
            g_all_frag_descrs += (get_frags_info_from_file(sys.argv[1]))

# 如果命令行参数为镜像描述文件的绝对路径
else:
    for i in range(len(sys.argv)):
        if i == 0:
            continue
        g_all_frag_descrs += (get_frags_info_from_file(sys.argv[i]))

for frag in g_all_frag_descrs:
    frag.check()
