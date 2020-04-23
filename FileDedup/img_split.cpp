//
// Created by 56556 on 2018/12/10.
//
#pragma pack(1)

#include <math.h>
#include "img_split.h"


static unsigned int g_htab_backet_nr = BACKET_SIZE;

static long long int simhash_arr[MD5_LEN * 8] = {0};

static FragmentDescriptor g_fragments_arr[MAX_FRAG_NUM];

//print fragment info
void CheckFragDescr(pFragmentDescriptor p_frag_descr) {
    printf(
            "\n\nfragment_unique_nb\t%u,"
            "\nfragment_infile_nb\t%u,"
            "\nfragment_offset\t%llu,"
            "\nfragment_size\t%llu,"
            "\nboot_signature\t%u,"
            "\nfragment_type\t%u,"
            "\nfragment_name\t%s,"
            "\nfragment_path\t%s,"
            "\nsrc_path_name\t%s,"
            "\nfragment_file_info_path\t%s,\n", p_frag_descr->fragment_unique_nb, p_frag_descr->fragment_infile_nb,
            p_frag_descr->fragment_offset, p_frag_descr->fragment_size, p_frag_descr->boot_signature,
            p_frag_descr->fragment_type,
            p_frag_descr->fragment_name, p_frag_descr->fragment_path, p_frag_descr->src_path_name,
            p_frag_descr->fragment_file_info_path);
    printf("fragment_simhash\t");
    show_simhash(p_frag_descr->fragment_simhash);

//    uint8_t simhash[16] = {0};
//    GetFragSimhash(p_frag_descr, simhash);

}

//print img info
void CheckImgDescr(pImgDescriptor p_img_descr) {
    printf(
            "\n\nimg_unique_nb\t%u,\nimg_type\t%d,\nimg_size\t%lu,\nimg_name\t%s,\nimg_path\t%s,\ndisk_type\t%d,\nfragment_nums\t%u,\nboot_sector_offset\t%u\n\n",
            p_img_descr->img_unique_nb, p_img_descr->img_type, p_img_descr->img_size, p_img_descr->img_name,
            p_img_descr->img_path,
            p_img_descr->disk_type, p_img_descr->fragment_nums, p_img_descr->boot_sector_offset);
    //printf fragment info
    for (int i = 0; i < p_img_descr->fragment_nums; i++) {
        CheckFragDescr(&(p_img_descr->fragments[i]));
    }
}

//获取分段的类型
FragmentType GetFragmentType(uint8_t system_signature) {
    FragmentType ret = empty;
    switch (system_signature) {
        case 0X00: {
            ret = empty;
            break;
        }
        case 0X07: {
            ret = ntfs;
            break;
        }
        case 0X0B:
        case 0X0C: {
            ret = fat32;
        }
        case 0X06: {
            ret = fat16;
            break;
        }
        case 0X83: {
            ret = linux_normal;
            break;
        }
        case 0X82: {
            ret = linux_swap;
            break;
        }
        case 0X8E: {
            ret = lvm;
            break;
        }
        default: {
            ret = empty;
            break;
        }
    }
    return ret;
}

//获取镜像文件类型 【后缀】
ImgType GetImgType(const char *type_str) {

    ImgType img_type;
    if (strcmp(type_str, "vmdk") == 0) {
        img_type = vmdk;
    } else if (strcmp(type_str, "raw") == 0) {
        img_type = raw;
    } else if (strcmp(type_str, "qcow2") == 0) {
        img_type = qcow2;
    } else if (strcmp(type_str, "vhd") == 0) {
        img_type = vhd;
    } else if (strcmp(type_str, "vdi") == 0) {
        img_type = vdi;
    } else {
        img_type = other;
    }
    return img_type;
}

//是否是虚拟机镜像文件
bool CheckImgFile(char *file_name) {
    string fn = string(file_name);
    unsigned long dot_pos = 0, last_slash_pos = 0;
    dot_pos = fn.rfind('.');
    return !(GetImgType(fn.substr(dot_pos + 1, fn.size()).c_str()) == other);
}

//获取镜像磁盘类型【MBR|GPT|PV|UNKNOWN】
DiskType GetDiskType(const char *file_name) {

    //open file
    int fd = open(file_name, O_RDONLY);
    if (fd == -1) {
        printf("open file error\n");
        return unknown;
    }
    //第一个扇区的偏移
    unsigned long dot_pos = 0;
    string fn = string(file_name);
    dot_pos = fn.rfind('.');
    ImgType img_type = GetImgType(fn.substr(dot_pos + 1, fn.size()).c_str());
    uint64_t first_sector_offset = (img_type == vdi ? 0X200000 : 0X00);
    //read the first sector
    DiskType ret;
    bool is_55AA = false, is_gpt = false, is_pv = false;
    unsigned int rwsize = 0;
    void *sector_buf;
    sector_buf = malloc(SECTOR_SIZE);
    lseek(fd, first_sector_offset, SEEK_SET);
    if ((rwsize = read(fd, sector_buf, SECTOR_SIZE)) != SECTOR_SIZE) {
        printf("read regular file error\n");
        return unknown;
    }
    //第一个扇区结尾是否是 0X55AA 如果是55AA 可能为MBR或者GPT 再读第二扇区 判断是否是GPT分区表
    unsigned char *ptr_buf = (unsigned char *) sector_buf;
    if (((*(ptr_buf + SECTOR_SIZE - 2)) == 0X55) && ((*(ptr_buf + SECTOR_SIZE - 1)) == 0XAA)) {
        is_55AA = true;
    }
    //继续读下一个扇区
    lseek(fd, first_sector_offset + SECTOR_SIZE, SEEK_SET);
    if ((rwsize = read(fd, sector_buf, SECTOR_SIZE)) != SECTOR_SIZE) {
        printf("read regular file error\n");
        return unknown;
    }
    close(fd);
    uint64_t *ptr = (uint64_t *) sector_buf;
    //  EFI PART
    if ((*ptr) == 0X5452415020494645) {
        is_gpt = true;
    }
        //  LABELONE
    else if ((*ptr) == 0X454E4F4C4542414C) {
        is_pv = true;
    }
    //return
    if (is_55AA) {
        if (is_gpt)
            ret = gpt;
        else
            ret = mbr;
    } else {
        if (is_pv)
            ret = pv;
        else
            ret = unknown;
    }
    return ret;
}

//获取挂载后的分区的类型(是否是OS分区)
MountedType GetMountedType(const char *mount_path, FragmentType frag_type) {
    char cmd_result[1024] = {0};
    bool exec_ret = false;
    char cmd[1024] = {0};

    memset(cmd, 0, sizeof(cmd));
    sprintf(cmd, "sudo ls  %s", mount_path);
    memset(cmd_result, 0, sizeof(cmd_result));
    exec_ret = ExecuteCMD(cmd, cmd_result);
    if (exec_ret) {
        if (frag_type == ntfs) {
            const char *os_dir[8] = {"PerfLogs", "Program Files", "Program Files (x86)", "ProgramData", "Windows",
                                     "Users", "pagefile.sys", "Recovery"};
            int os_dir_cnt = 0;
            for (int i = 0; i < 8; ++i) {
                if (strstr(cmd_result, os_dir[i])) {
                    os_dir_cnt++;
                }
            }
            if (os_dir_cnt > 4) {
//                printf("windows_os\n");
                return windows_os;
            } else {
//                printf("windows_else\n");
                return windows_else;
            }
        } else if (frag_type == linux_normal) {
            const char *os_dir[13] = {"bin", "boot", "dev", "etc", "home", "lib", "lib64", "proc", "root", "sbin",
                                      "sys",
                                      "usr", "var"};
            int os_dir_cnt = 0;
            for (int i = 0; i < 13; ++i) {
                if (strstr(cmd_result, os_dir[i])) {
                    os_dir_cnt++;
                }
            }
            if (os_dir_cnt > 5) {
//                printf("linux_os\n");
                return linux_os;
            } else {
//                printf("linux_else\n");
                return linux_else;
            }
        } else {
            return unknown_mount_type;
        }
    } else {
        log_write(LOG_ERR, "ExecuteCMD(%s) error", cmd);
        return unknown_mount_type;
    }
}


int AccumulateMd5ByFixedChunk(void *key, void *data) {
    printf("in ht:%s\n", (char *) key);
    pBlockInfo pbi = (pBlockInfo) data;
    printf("cnt: %d\n", pbi->block_cnt);
    unsigned char *p_c = (unsigned char *) key;
    for (int i = 0; i < MD5_LEN * 2; i++) {
        for (int j = 0; j < 4; j++) {
            simhash_arr[i * 4 + 4 - j - 1] += ((0x01 << j) & (*p_c) ? (pbi->block_cnt) : -((pbi->block_cnt)));
        }
        p_c++;
    }
}

int AccumulateMd5(void *key, void *data) {
//    printf("%s\n", (char *) key);
//    return 0;
//    show_md5((unsigned char *) key);
    pFileInfo pfi = (pFileInfo) data;
//    printf("%s\n%lu\n%u\n", pfi->file_name, pfi->file_sz, pfi->file_cnt);
    unsigned char *p_c = (unsigned char *) key;
//    long long int hash_tmp[MD5_LEN * 8] = {0};
    for (int i = 0; i < MD5_LEN * 2; i++) {
        for (int j = 0; j < 4; j++) {
            simhash_arr[i * 4 + 4 - j - 1] += ((0x01 << j) & (*p_c) ? (pfi->file_cnt) * (pfi->file_sz) : -(
                    (pfi->file_cnt) * (pfi->file_sz)));
//            hash_tmp[i * 8 + 8 - j - 1] = ((1 << j) & (*p_c) ? (pfi->file_cnt) * (pfi->file_sz) : -(
//                (pfi->file_cnt) * (pfi->file_sz)));
//            simhash_arr[i * 8 + 8 - j - 1] += hash_tmp[i * 8 + 8 - j - 1];
//            simhash_arr[i * 8 + 8 - j - 1] += ((0x01 << j) & (*p_c) ? (pfi->file_cnt) * (pfi->file_sz) : -(
//                (pfi->file_cnt) * (pfi->file_sz)));
        }
        p_c++;
    }
//    printf("hash:[");
//    for (int i = 0; i < MD5_LEN * 8; ++i) {
//        printf("%2d ", hash_tmp[i]);
//    }
//    printf("]\n");
//    printf("simhash[");
//    for (int i = 0; i < MD5_LEN * 8; ++i) {
//        printf("%2d ", simhash_arr[i]);
//    }
//    printf("]\n");
//    for (int k = 0; k < MD5_LEN * 8; ++k) {
//        printf("%d ", simhash_arr[k]);
//    }
//    printf("\n");
//
//    getchar();
    return 0;
}

int GetFragSimhashByFixedChunk(pFragmentDescriptor p_frag_descr, uint8_t simhash[MD5_LEN], uint32_t chunk_size) {
    log_write(LOG_INFO, "Start GetFragSimhashByFixedChunk");
    char cmd_result[1024] = {0};
    char simhash_str[MD5_LEN * 2 + 1] = {0};
    bool exec_ret = false;
    char cmd[1024] = {0};
    memset(cmd, 0, sizeof(cmd));
    sprintf(cmd, "python3 \"/data/script/ImgDedup/get_frag_simhash_new.py\" \"%s\" \"%s%s\" %llu %llu %u",
            p_frag_descr->src_path_name, p_frag_descr->fragment_path,
            p_frag_descr->fragment_name, p_frag_descr->fragment_offset, p_frag_descr->fragment_size, chunk_size);
    log_write(LOG_INFO, "GetFragSimhashByFixedChunk: ExecuteCMD(%s) ", cmd);
    memset(cmd_result, 0, sizeof(cmd_result));
    exec_ret = ExecuteCMD(cmd, cmd_result);
    if (exec_ret) {
        strncpy(simhash_str, cmd_result, strlen(cmd_result) - 1);
        Md5String2Bin(simhash_str, simhash);
        log_write(LOG_INFO, "GetFragSimhashByFixedChunk Success");
        return 0;
    } else {
        log_write(LOG_ERR, "ExecuteCMD(%s) error", cmd);
        return -1;
    }
    return 0;
}

int CalcSimhashByPy(pFragmentDescriptor p_frag_descr, const char *mount_path, uint8_t simhash[MD5_LEN]) {
    log_write(LOG_INFO, "Start CalcSimhashByPy");
    char cmd_result[1024] = {0};
    char simhash_str[MD5_LEN * 2 + 1] = {0};
    bool exec_ret = false;
    char cmd[1024] = {0};
    memset(cmd, 0, sizeof(cmd));
    sprintf(cmd, "python3 \"/data/script/ImgDedup/get_frag_simhash.py\" \"%s\" \"%s%s\"", MOUNT_PATH,
            p_frag_descr->fragment_path,
            p_frag_descr->fragment_name);
    log_write(LOG_INFO, "CalcSimhashByPy: ExecuteCMD(%s) ", cmd);
    memset(cmd_result, 0, sizeof(cmd_result));
    exec_ret = ExecuteCMD(cmd, cmd_result);
    if (exec_ret) {
        strncpy(simhash_str, cmd_result, strlen(cmd_result) - 1);
        Md5String2Bin(simhash_str, simhash);
        log_write(LOG_INFO, "CalcSimhashByPy Success");
        return 0;
    } else {
        log_write(LOG_ERR, "ExecuteCMD(%s) error", cmd);
        return -1;
    }
}

//获取分段的simhash
int GetFragSimhash(pFragmentDescriptor p_frag_descr, uint8_t *simhash) {
    log_write(LOG_INFO, "Start GetFragSimhash");
    FragmentType frag_type = (FragmentType) p_frag_descr->fragment_type;
    if (frag_type != linux_normal && frag_type != ntfs) {
        return 0;
    }

    char loop_path[MAX_PATH_LEN] = {0};

    char cmd_result[1024] = {0};
    bool exec_ret = false;
    char cmd[1024] = {0};

    memset(cmd, 0, sizeof(cmd));
    sprintf(cmd, "%s", "losetup -f");
    memset(cmd_result, 0, sizeof(cmd_result));
    exec_ret = ExecuteCMD(cmd, cmd_result);
    if (exec_ret) {
        strncpy(loop_path, cmd_result, strlen(cmd_result) - 1);
    } else {
        log_write(LOG_ERR, "ExecuteCMD(%s) error", cmd);
        return -1;
    }
//    return -1;

    bool losetup_ret = false, can_mount = false, mount_ret = false;

    //losetup
    memset(cmd, 0, sizeof(cmd));
    sprintf(cmd, "sudo losetup %s %s -o %lu", loop_path, p_frag_descr->src_path_name,
            uint64_t(p_frag_descr->fragment_offset) * 512);
    log_write(LOG_INFO, "CMD:[%s]", cmd);
    memset(cmd_result, 0, sizeof(cmd_result));
    exec_ret = ExecuteCMD(cmd, cmd_result);
    if (exec_ret) {
        //if losetup success
        losetup_ret = true;

        //mount
        switch (frag_type) {
            case linux_normal: {
                log_write(LOG_INFO, "frag_type: linux_normal[%s]", p_frag_descr->fragment_name);
                memset(cmd, 0, sizeof(cmd));
                sprintf(cmd, "sudo mount -o ro %s %s", loop_path, MOUNT_PATH);
                log_write(LOG_INFO, "CMD:[%s]", cmd);
                memset(cmd_result, 0, sizeof(cmd_result));
                exec_ret = ExecuteCMD(cmd, cmd_result);
                if (exec_ret) {
                    mount_ret = true;
                } else {
                    log_write(LOG_ERR, "ExecuteCMD(%s) error", cmd);
                }
                break;
            }
            case ntfs: {
                log_write(LOG_INFO, "frag_type: ntfs[%s]", p_frag_descr->fragment_name);
                memset(cmd, 0, sizeof(cmd));
                sprintf(cmd, "sudo mount -t ntfs-3g -o ro %s %s", loop_path, MOUNT_PATH);
                log_write(LOG_INFO, "CMD:[%s]", cmd);
                memset(cmd_result, 0, sizeof(cmd_result));
                exec_ret = ExecuteCMD(cmd, cmd_result);
                if (exec_ret) {
                    mount_ret = true;
                } else {
                    log_write(LOG_ERR, "ExecuteCMD(%s) error", cmd);
                }
                break;
            }
            default: {

                break;
            }
        }


        //if mounted
        if (mount_ret) {

            log_write(LOG_INFO, "Mount Success");

            CalcSimhashByPy(p_frag_descr, MOUNT_PATH, simhash);
//            GetFragSimhashByFixedChunk(p_frag_descr, simhash, 4096);
//            show_simhash(simhash);
            memcpy(p_frag_descr->fragment_simhash, simhash, MD5_LEN);
            char file_info_json_fullpath[256] = {0};
            sprintf(file_info_json_fullpath, "%s%s.json", p_frag_descr->fragment_path, p_frag_descr->fragment_name);
            strcpy(p_frag_descr->fragment_file_info_path, file_info_json_fullpath);

            //umount
            memset(cmd, 0, sizeof(cmd));
            sprintf(cmd, "sudo umount -f %s", MOUNT_PATH);
            log_write(LOG_INFO, "CMD:[%s]", cmd);
            memset(cmd_result, 0, sizeof(cmd_result));
            exec_ret = ExecuteCMD(cmd, cmd_result);
        } else {
            //mount failed
            //try
            //umount
            memset(cmd, 0, sizeof(cmd));
            sprintf(cmd, "sudo umount -f %s", MOUNT_PATH);
            log_write(LOG_ERR, "CMD:[%s]", cmd);
            memset(cmd_result, 0, sizeof(cmd_result));
            exec_ret = ExecuteCMD(cmd, cmd_result);
        }


    } else {
        log_write(LOG_ERR, "losetup failed:", cmd);
    }


    //losetup delete
    if (losetup_ret) {
        memset(cmd, 0, sizeof(cmd));
        sprintf(cmd, "sudo losetup -d %s", loop_path);
        memset(cmd_result, 0, sizeof(cmd_result));
        exec_ret = ExecuteCMD(cmd, cmd_result);
    } else {
        //try
        memset(cmd, 0, sizeof(cmd));
        sprintf(cmd, "sudo losetup -d %s", loop_path);
        memset(cmd_result, 0, sizeof(cmd_result));
        exec_ret = ExecuteCMD(cmd, cmd_result);
    }



//    memset(cmd_result, 0, sizeof(cmd_result));
//    exec_ret = ExecuteCMD(cmd, cmd_result);
//    if (exec_ret) {
//
//
//    } else {
//        log_write(LOG_ERR, "ExecuteCMD(%s) error", cmd);
//        return -1;
//    }

    return 0;
}

//write fragment
bool WriteFragment2File(FragmentDescriptor *p_frag_descr) {
    bool ret = false;
    if (access(p_frag_descr->fragment_path, 0) != 0) {
        //存储分段的目录不存在
        if (mkdir(p_frag_descr->fragment_path, 0766) != 0) {
            printf("mkdir error:%d\n", errno);
            return false;
        }
    }
    int fd_src = open(p_frag_descr->src_path_name, O_RDONLY);
    if (fd_src == -1) {
        printf("open src error:%d\n", errno);
        return false;
    }
    int fd_dest = open(
            (string(p_frag_descr->fragment_path) + string(p_frag_descr->fragment_name)).c_str(), O_CREAT |
                                                                                                 O_RDWR |
                                                                                                 O_TRUNC);
    if (fd_dest == -1) {
        printf("open dest error:%d\n", errno);
        return false;
    }
    lseek(fd_src, p_frag_descr->fragment_offset * SECTOR_SIZE, SEEK_SET);
    uint32_t rwsize = 0;
    void *read_buf;
    read_buf = malloc(BLK_MIN_SIZE);
    uint32_t read_blks = 0;
    while ((read_blks + 1) * 8 < p_frag_descr->fragment_size) {
        rwsize = read(fd_src, read_buf, BLK_MIN_SIZE);
        write(fd_dest, read_buf, rwsize);
        read_blks++;
    }
    uint32_t remain_sectors = p_frag_descr->fragment_size - read_blks * 8;
    read_buf = realloc(read_buf, SECTOR_SIZE);
    while (remain_sectors--) {
        rwsize = read(fd_src, read_buf, SECTOR_SIZE);
        write(fd_dest, read_buf, rwsize);
    }
    close(fd_dest);
    close(fd_src);
    return true;

}

//parse img file and save the descriptor
int ParseImgFile(char *file_name, pImgDescriptor p_img_descriptor, const char *dest_path, int only_descr) {

    //last used sector
    uint64_t last_sector = 0;


    //open file
    int fd = open(file_name, O_RDONLY);
    if (fd == -1) {
        printf("open file error\n");
        return errno;
    }
    //malloc MBR
    pMbrSector p_mbr_sector = (pMbrSector) malloc(sizeof(MbrSector));
    if (p_mbr_sector == NULL) {
        printf("malloc mbr_sector error\n");
        return errno;
    }

    //get img size
    struct stat statbuf = {0};
    if (-1 == fstat(fd, &statbuf)) {
        printf("fstat regular file\n");
        return errno;
    }
    //img info
    //  get unique nb
    p_img_descriptor->img_unique_nb = global_img_nb++;
    //  get size
    p_img_descriptor->img_size = statbuf.st_size;
    //  get name and path
    string fn = string(file_name);
    unsigned long dot_pos = 0, last_slash_pos = 0;
    dot_pos = fn.rfind('.');
    last_slash_pos = fn.rfind('/');
    strcpy(p_img_descriptor->img_name, fn.substr(last_slash_pos + 1, fn.size()).c_str());
    strcpy(p_img_descriptor->img_path, fn.substr(0, last_slash_pos + 1).c_str());
    //  get img type
    p_img_descriptor->img_type = GetImgType(fn.substr(dot_pos + 1, fn.size()).c_str());
    //  get disk type
    p_img_descriptor->disk_type = GetDiskType(file_name);
    // get first data sector
//    p_img_descriptor->boot_sector_offset = (p_img_descriptor->img_type == vdi ? VDI_HEADER_LEN : 0X00);
    p_img_descriptor->boot_sector_offset = 0X00;

    uint32_t fragment_infile_nb = 0;

    //fragment destination path
    // default
//    string frag_dest_path = string(p_img_descriptor->img_path) + string(p_img_descriptor->img_name) + string("-split/");
    //else
    string frag_dest_path = string(dest_path);

    //处理文件头
    if (p_img_descriptor->img_type == vdi) {
        //文件头分割
        FragmentDescriptor frag_descr;
        memset(&frag_descr, 0, sizeof(FragmentDescriptor));
        frag_descr.boot_signature = 0X00;
        frag_descr.fragment_unique_nb = global_fragment_nb++;
        frag_descr.fragment_infile_nb = fragment_infile_nb;
        strcpy(frag_descr.fragment_name,
               strcat(p_img_descriptor->img_name, (string(".part_") + Int2String(fragment_infile_nb)).c_str()));
        frag_descr.fragment_offset = p_img_descriptor->boot_sector_offset + 0;
        frag_descr.fragment_size = VDI_HEADER_LEN;
        frag_descr.fragment_type = img_header;
        memset(frag_descr.fragment_simhash, 0, sizeof(frag_descr.fragment_simhash));
        strcpy(frag_descr.fragment_path, frag_dest_path.c_str());
        strcpy(frag_descr.src_path_name, file_name);
        strcpy(frag_descr.fragment_file_info_path, "NULL");
        fragment_infile_nb++;
        last_sector += (frag_descr.fragment_size);
//        CheckFragDescr(frag_descr);
        //add to img_descr
        p_img_descriptor = (ImgDescriptor *) realloc(p_img_descriptor, sizeof(ImgDescriptor) +
                                                                       sizeof(FragmentDescriptor) * fragment_infile_nb);
        p_img_descriptor->fragments[fragment_infile_nb - 1] = frag_descr;
        g_fragments_arr[global_fragment_nb] = frag_descr;

        printf("handle file header finish\n");
    }


    //如果整个磁盘是pv
    if (p_img_descriptor->disk_type == pv) {
        //new fragment
        printf("whole disk is pv\n");
        FragmentDescriptor frag_descr;
        memset(&frag_descr, 0, sizeof(FragmentDescriptor));
        frag_descr.boot_signature = 0X00;
        frag_descr.fragment_unique_nb = global_fragment_nb++;
        frag_descr.fragment_infile_nb = fragment_infile_nb;
        strcpy(frag_descr.fragment_name,
               (string(p_img_descriptor->img_name) +
                string(".part_") + Int2String(fragment_infile_nb)).c_str());
        frag_descr.fragment_offset = p_img_descriptor->boot_sector_offset + 0;
        frag_descr.fragment_size = (p_img_descriptor->img_size - p_img_descriptor->boot_sector_offset) / 512;
        frag_descr.fragment_type = lvm;
        //这里simhash先置零
        memset(frag_descr.fragment_simhash, 0, sizeof(frag_descr.fragment_simhash));
        strcpy(frag_descr.fragment_path, frag_dest_path.c_str());
        strcpy(frag_descr.src_path_name, file_name);
        strcpy(frag_descr.fragment_file_info_path, "NULL");
        fragment_infile_nb++;
        last_sector += (frag_descr.fragment_size);

        //add to img_descr
        p_img_descriptor = (ImgDescriptor *) realloc(p_img_descriptor, sizeof(ImgDescriptor) +
                                                                       sizeof(FragmentDescriptor) * fragment_infile_nb);
        p_img_descriptor->fragments[fragment_infile_nb - 1] = frag_descr;
        g_fragments_arr[global_fragment_nb] = frag_descr;
    } else {
        //如果磁盘不是pv
        //read the first sector
        unsigned int rwsize = 0;
        void *sector_buf;
        sector_buf = malloc(SECTOR_SIZE);
        if ((rwsize = read(fd, sector_buf, SECTOR_SIZE)) != SECTOR_SIZE) {
            printf("read regular file error\n");
            return errno;
        }
        //parse mbr sector
        p_mbr_sector = (pMbrSector) sector_buf;
        for (int i = 0; i < 4; i++) {
            if (p_mbr_sector->part_tab_entrys[i].start_sector_nb == 0) {
                printf("partition end\n");
                break;
            }
            //第一个分区
            if (i == 0 && p_img_descriptor->disk_type != pv) {
                //  0扇区到第一个分区之间需分割
                FragmentDescriptor frag_descr;
                memset(&frag_descr, 0, sizeof(FragmentDescriptor));
//                frag_descr.boot_signature = p_mbr_sector->part_tab_entrys[i].boot_signature;
                frag_descr.boot_signature = 0X00;
                frag_descr.fragment_unique_nb = global_fragment_nb++;
                frag_descr.fragment_infile_nb = fragment_infile_nb;
                strcpy(frag_descr.fragment_name,
                       (string(p_img_descriptor->img_name) +
                        string(".part_") + Int2String(fragment_infile_nb)).c_str());
                frag_descr.fragment_size = 0X7FFFFFFF;
                for (int j = 0; j < 4; j++) {
                    if (p_mbr_sector->part_tab_entrys[j].start_sector_nb == 0) { break; }
                    frag_descr.fragment_size = min(frag_descr.fragment_size,
                                                   uint64_t(p_mbr_sector->part_tab_entrys[j].start_sector_nb));
                }
                frag_descr.fragment_offset = p_img_descriptor->boot_sector_offset + 0;
//                frag_descr.fragment_size = p_mbr_sector->part_tab_entrys[i].start_sector_nb;
                frag_descr.fragment_type = boot_interval;
                //这里simhash先置零
                memset(frag_descr.fragment_simhash, 0, sizeof(frag_descr.fragment_simhash));
                strcpy(frag_descr.fragment_path, frag_dest_path.c_str());
                strcpy(frag_descr.src_path_name, file_name);
                strcpy(frag_descr.fragment_file_info_path, "NULL");
                fragment_infile_nb++;
                last_sector += (frag_descr.fragment_size);
//                CheckFragDescr(frag_descr);
//                WriteFragment2File(&frag_descr);
                //add to img_descr
                p_img_descriptor = (ImgDescriptor *) realloc(p_img_descriptor, sizeof(ImgDescriptor) +
                                                                               sizeof(FragmentDescriptor) *
                                                                               fragment_infile_nb);
                p_img_descriptor->fragments[fragment_infile_nb - 1] = frag_descr;
                g_fragments_arr[global_fragment_nb] = frag_descr;
//                CheckFragDescr(p_img_descriptor->fragments[0]);
            }

            //如果不是扩展分区
            if (p_mbr_sector->part_tab_entrys[i].system_signature != 0X05 &&
                p_mbr_sector->part_tab_entrys[i].system_signature != 0X0F) {
                FragmentDescriptor frag_descr;
                memset(&frag_descr, 0, sizeof(FragmentDescriptor));
                frag_descr.boot_signature = p_mbr_sector->part_tab_entrys[i].boot_signature;
                frag_descr.fragment_unique_nb = global_fragment_nb++;
                frag_descr.fragment_infile_nb = fragment_infile_nb;
                strcpy(frag_descr.fragment_name,
                       (string(p_img_descriptor->img_name) +
                        string(".part_") + Int2String(fragment_infile_nb)).c_str());
                frag_descr.fragment_offset =
                        p_img_descriptor->boot_sector_offset + p_mbr_sector->part_tab_entrys[i].start_sector_nb;
                frag_descr.fragment_size = p_mbr_sector->part_tab_entrys[i].total_sectors_num;
                frag_descr.fragment_type = GetFragmentType(p_mbr_sector->part_tab_entrys[i].system_signature);
                memset(frag_descr.fragment_simhash, 0, sizeof(frag_descr.fragment_simhash));
                strcpy(frag_descr.fragment_path, frag_dest_path.c_str());
                strcpy(frag_descr.src_path_name, file_name);
                strcpy(frag_descr.fragment_file_info_path, "NULL");
                fragment_infile_nb++;
                last_sector += (frag_descr.fragment_size);
//                CheckFragDescr(frag_descr);
                //add to img_descr
                p_img_descriptor = (ImgDescriptor *) realloc(p_img_descriptor, sizeof(ImgDescriptor) +
                                                                               sizeof(FragmentDescriptor) *
                                                                               fragment_infile_nb);
                //calc simhash
                uint8_t simhash[MD5_LEN] = {0};
                GetFragSimhash(&frag_descr, simhash);
//                show_simhash(simhash);
//                GetFragSimhashByFixedChunk(&frag_descr, simhash);
                p_img_descriptor->fragments[fragment_infile_nb - 1] = frag_descr;
                g_fragments_arr[global_fragment_nb] = frag_descr;
//                CheckFragDescr(p_img_descriptor->fragments[fragment_infile_nb - 1]);
            }

            //extend partition
            if (i == 3) {
                bool is_extend_end = false;
                //parse EBR
                printf("find extend partition\n");
                pMbrSector p_ebr_sector = (pMbrSector) malloc(sizeof(MbrSector));
                uint64_t ebr_sector_offset = (p_mbr_sector->part_tab_entrys[i].start_sector_nb) * SECTOR_SIZE +
                                             p_img_descriptor->boot_sector_offset;
                while (!is_extend_end) {
                    //move to extend partition
                    lseek(fd, ebr_sector_offset, SEEK_SET);
                    //read ebr sector
                    if ((rwsize = read(fd, sector_buf, SECTOR_SIZE)) != SECTOR_SIZE) {
                        printf("read regular file error\n");
                        return errno;
                    }
                    p_ebr_sector = (pMbrSector) sector_buf;

                    //这里应该将EBR与逻辑分区分开

                    //ebr间隙
                    FragmentDescriptor frag_descr;
                    memset(&frag_descr, 0, sizeof(FragmentDescriptor));
                    frag_descr.boot_signature = 0X00;
                    frag_descr.fragment_unique_nb = global_fragment_nb++;
                    frag_descr.fragment_infile_nb = fragment_infile_nb;
                    strcpy(frag_descr.fragment_name,
                           (string(p_img_descriptor->img_name) +
                            string(".part_") + Int2String(fragment_infile_nb)).c_str());
                    frag_descr.fragment_offset = p_img_descriptor->boot_sector_offset + ebr_sector_offset / 512;
                    frag_descr.fragment_size = p_ebr_sector->part_tab_entrys[0].start_sector_nb;
                    frag_descr.fragment_type = boot_interval;
                    memset(frag_descr.fragment_simhash, 0, sizeof(frag_descr.fragment_simhash));
                    strcpy(frag_descr.fragment_path, frag_dest_path.c_str());
                    strcpy(frag_descr.src_path_name, file_name);
                    strcpy(frag_descr.fragment_file_info_path, "NULL");
                    fragment_infile_nb++;
                    last_sector += (frag_descr.fragment_size);
//                    CheckFragDescr(frag_descr);
                    //add to img_descr
                    p_img_descriptor = (ImgDescriptor *) realloc(p_img_descriptor, sizeof(ImgDescriptor) +
                                                                                   sizeof(FragmentDescriptor) *
                                                                                   fragment_infile_nb);
                    p_img_descriptor->fragments[fragment_infile_nb - 1] = frag_descr;
                    g_fragments_arr[global_fragment_nb] = frag_descr;
//                    CheckFragDescr(p_img_descriptor->fragments[fragment_infile_nb - 1]);

                    //逻辑分区
                    FragmentDescriptor frag_descr2;
                    memset(&frag_descr2, 0, sizeof(FragmentDescriptor));
                    frag_descr2.boot_signature = p_ebr_sector->part_tab_entrys[0].boot_signature;
                    frag_descr2.fragment_unique_nb = global_fragment_nb++;
                    frag_descr2.fragment_infile_nb = fragment_infile_nb;
                    strcpy(frag_descr2.fragment_name,
                           (string(p_img_descriptor->img_name) +
                            string(".part_") + Int2String(fragment_infile_nb)).c_str());
                    frag_descr2.fragment_offset = p_img_descriptor->boot_sector_offset + ebr_sector_offset / 512 +
                                                  p_ebr_sector->part_tab_entrys[0].start_sector_nb;
                    frag_descr2.fragment_size = p_ebr_sector->part_tab_entrys[0].total_sectors_num;
                    frag_descr2.fragment_type = GetFragmentType(p_ebr_sector->part_tab_entrys[0].system_signature);
                    memset(frag_descr.fragment_simhash, 0, sizeof(frag_descr.fragment_simhash));
                    strcpy(frag_descr2.fragment_path, frag_dest_path.c_str());
                    strcpy(frag_descr2.src_path_name, file_name);
                    strcpy(frag_descr2.fragment_file_info_path, "NULL");
                    fragment_infile_nb++;
                    last_sector += (frag_descr2.fragment_size);
//                    CheckFragDescr(frag_descr);
                    //add to img_descr
                    p_img_descriptor = (ImgDescriptor *) realloc(p_img_descriptor, sizeof(ImgDescriptor) +
                                                                                   sizeof(FragmentDescriptor) *
                                                                                   fragment_infile_nb);
                    //calc simhash
                    uint8_t simhash[MD5_LEN] = {0};
                    GetFragSimhash(&frag_descr2, simhash);
//                    show_simhash(simhash);
//                    GetFragSimhashByFixedChunk(&frag_descr, simhash);
                    p_img_descriptor->fragments[fragment_infile_nb - 1] = frag_descr2;
                    g_fragments_arr[global_fragment_nb] = frag_descr2;


                    /*

                    FragmentDescriptor frag_descr;
                    frag_descr.boot_signature = p_ebr_sector->part_tab_entrys[0].boot_signature;
                    frag_descr.fragment_unique_nb = global_fragment_nb++;
                    frag_descr.fragment_infile_nb = fragment_infile_nb;
                    strcpy(frag_descr.fragment_name,
                           (string(p_img_descriptor->img_name) +
                            string(".part_") + Int2String(fragment_infile_nb)).c_str());
                    frag_descr.fragment_offset = p_img_descriptor->boot_sector_offset + ebr_sector_offset / 512;
                    frag_descr.fragment_size = ((p_ebr_sector->part_tab_entrys[1].start_sector_nb) == 0 ?
                                                p_ebr_sector->part_tab_entrys[0].total_sectors_num +
                                                p_ebr_sector->part_tab_entrys[0].start_sector_nb
                                                                                                        : p_ebr_sector->part_tab_entrys[1].start_sector_nb);
                    frag_descr.fragment_type = GetFragmentType(p_ebr_sector->part_tab_entrys[0].system_signature);
                    strcpy(frag_descr.fragment_path, frag_dest_path.c_str());
                    strcpy(frag_descr.src_path_name, file_name);
                    fragment_infile_nb++;
                    last_sector += (frag_descr.fragment_size);
//                    CheckFragDescr(frag_descr);
                    //add to img_descr
                    p_img_descriptor = (ImgDescriptor *) realloc(p_img_descriptor, sizeof(ImgDescriptor) +
                                                                                   sizeof(FragmentDescriptor) *
                                                                                   fragment_infile_nb);
                    p_img_descriptor->fragments[fragment_infile_nb - 1] = frag_descr;
//                    CheckFragDescr(p_img_descriptor->fragments[fragment_infile_nb - 1]);

                     */

                    //next extend partition
                    if ((p_ebr_sector->part_tab_entrys[1].start_sector_nb) == 0) {
                        is_extend_end = true;
                    } else {
                        ebr_sector_offset += ((p_ebr_sector->part_tab_entrys[1].start_sector_nb) * SECTOR_SIZE);
                    }
                }
            }
        }
        //all partitions searched
        //check if reached the end of file
        if (last_sector * SECTOR_SIZE < p_img_descriptor->img_size) {
            //new empty fragment
            printf("find unused sectors\n");
            FragmentDescriptor frag_descr;
            memset(&frag_descr, 0, sizeof(FragmentDescriptor));
            frag_descr.boot_signature = 0X00;
            frag_descr.fragment_unique_nb = global_fragment_nb++;
            frag_descr.fragment_infile_nb = fragment_infile_nb;
            strcpy(frag_descr.fragment_name,
                   (string(p_img_descriptor->img_name) +
                    string(".part_") + Int2String(fragment_infile_nb)).c_str());
            frag_descr.fragment_offset = last_sector;
            frag_descr.fragment_size = p_img_descriptor->img_size / SECTOR_SIZE - last_sector;
            frag_descr.fragment_type = empty;
            memset(frag_descr.fragment_simhash, 0, sizeof(frag_descr.fragment_simhash));
            strcpy(frag_descr.fragment_path, frag_dest_path.c_str());
            strcpy(frag_descr.src_path_name, file_name);
            strcpy(frag_descr.fragment_file_info_path, "NULL");
            fragment_infile_nb++;
            last_sector += (frag_descr.fragment_size);
//            CheckFragDescr(frag_descr);
            //add to img_descr
            p_img_descriptor = (ImgDescriptor *) realloc(p_img_descriptor, sizeof(ImgDescriptor) +
                                                                           sizeof(FragmentDescriptor) *
                                                                           fragment_infile_nb);
            p_img_descriptor->fragments[fragment_infile_nb - 1] = frag_descr;
            g_fragments_arr[global_fragment_nb] = frag_descr;
//            CheckFragDescr(p_img_descriptor->fragments[fragment_infile_nb - 1]);
        }

    }

    //总分段个数
    p_img_descriptor->fragment_nums = fragment_infile_nb;

    //for debug
//    printf("fragment_infile_nb is %d\n", fragment_infile_nb);

    CheckImgDescr(p_img_descriptor);

    if (only_descr == 0) {
        char op;
        printf("continue?(y/n)");
        scanf("%c", &op);
        if (op == 'n') {

            //pass

        } else if (op == 'y') {

            //
            //split img
            for (int i = 0; i < fragment_infile_nb; i++) {
                printf("saving fragment[%d] ...\n", i);
                WriteFragment2File(&(p_img_descriptor->fragments[i]));
                printf("save fragment[%d] finish\n", i);
            }

        } else {
            //
        }
    }


//    const char *img_descr_path = (string(p_img_descriptor->img_path) + string(p_img_descriptor->img_name) +
//                                  string("-split")).c_str();
    if (access(frag_dest_path.c_str(), 0) != 0) {
        //存储分段的目录不存在
        if (mkdir(frag_dest_path.c_str(), 0766) != 0) {
            printf("mkdir error:%d\n", errno);
            return false;
        }
    }
    //save the img descriptor
    string file_img_descr = frag_dest_path + string(p_img_descriptor->img_name) + string(".descr");
    int fd_img_descr = open(file_img_descr.c_str(), O_CREAT | O_RDWR | O_TRUNC);
    if (fd_img_descr == -1) {
        printf("open file error: %d\n", errno);
        return -1;
    }
    void *ptr_write_buf = (void *) p_img_descriptor;
    if (write(fd_img_descr, ptr_write_buf, sizeof(ImgDescriptor) + sizeof(FragmentDescriptor) * fragment_infile_nb) ==
        -1) {
        printf("write file error:%d\n", errno);
        return -1;
    }
    chmod(file_img_descr.c_str(), 0644);
    printf("\n\nsave img descriptor finish\n");
    close(fd_img_descr);
    close(fd);

    //for debug
//    printf("\n\nfor debug\n");
//    for (int k = 0; k < global_fragment_nb; ++k) {
//        CheckFragDescr(&(g_fragments_arr[k]));
//    }

}

//parse imgs
int ParseImgFiles(char *imgs_path, const char *dest_path, int only_descr) {
    struct stat statbuf = {0};
    if (-1 == stat(imgs_path, &statbuf)) {
        printf("open %s error\n", imgs_path);
        return -1;
    }
    if (S_IFDIR & statbuf.st_mode) {
        //目录
        DIR *dp;
        struct dirent *dirp;
        if ((dp = opendir(imgs_path)) == NULL) {
            printf("can't open %s\n", imgs_path);
            return -1;
        }
        while ((dirp = readdir(dp)) != NULL) {
            if (CheckImgFile(dirp->d_name)) {
                char filepath[MAX_PATH_LEN] = {0};
                char destpath[MAX_PATH_LEN] = {0};
                if (imgs_path[strlen(imgs_path) - 1] == '/') {
                    sprintf(filepath, "%s%s", imgs_path, dirp->d_name);
                } else {
                    sprintf(filepath, "%s/%s", imgs_path, dirp->d_name);
                }
                pImgDescriptor p_img_descriptor;
                if ((p_img_descriptor = (pImgDescriptor) malloc(sizeof(ImgDescriptor))) == NULL) {
                    printf("malloc img_descriptor_error\n");
                    return -1;
                }
                if (dest_path[strlen(dest_path) - 1] == '/') {
                    sprintf(destpath, "%s", dest_path);
                } else {
                    sprintf(destpath, "%s/", dest_path);
                }
                ParseImgFile(filepath, p_img_descriptor, destpath, only_descr);
//                printf("%s\n", dirp->d_name);
            }
        }
        closedir(dp);
    } else if (S_IFREG & statbuf.st_mode) {
        printf("%s\n", imgs_path);
    } else {

    }
    return 0;
}

//read img descriptor
int ReadImgDescr(const char *file, pImgDescriptor p_img_descr) {
    int fd = open(file, O_RDONLY);
    if (fd == -1) {
        printf("open file error: %d\n", errno);
        return errno;
    }
    void *read_buf = (void *) (p_img_descr);
    uint32_t rwsize;
    uint32_t img_descr_size = sizeof(ImgDescriptor);
    if (!(rwsize = read(fd, read_buf, img_descr_size))) {
        printf("read regular file error: %d\n", errno);
        return errno;
    }

    //realloc
    img_descr_size = sizeof(ImgDescriptor) + sizeof(FragmentDescriptor) * p_img_descr->fragment_nums;
    p_img_descr = (pImgDescriptor) realloc(p_img_descr, img_descr_size);
    lseek(fd, 0, SEEK_SET);
    if (!(rwsize = read(fd, read_buf, img_descr_size))) {
        printf("read regular file error: %d\n", errno);
        return errno;
    }
    close(fd);

    return 0;
}

//merge fragments
int MergeFragments(pImgDescriptor p_img_descr, const char *dest_file_path) {
    //if restore to original path
    string dest_file = string(p_img_descr->img_path) + string(p_img_descr->img_name);
    //else
//    string dest_file = string(dest_file_path) + string(p_img_descr->img_name);

    int fd_dest = open(dest_file.c_str(), O_CREAT | O_RDWR | O_TRUNC);

    if (fd_dest == -1) {
        printf("open dest file error: %d\n", fd_dest);
    }

    int fd_frag;
    for (int i = 0; i < p_img_descr->fragment_nums; i++) {
        //append fragment to dest file
        string frag_file =
                string(p_img_descr->fragments[i].fragment_path) + string(p_img_descr->fragments[i].fragment_name);
        if ((fd_frag = open(frag_file.c_str(), O_RDONLY)) == -1) {
            printf("open fragment file error: %d\n", errno);
            close(fd_dest);
            return -1;
        }
        uint32_t rwsize = 0;
        void *read_buf;
        read_buf = malloc(BLK_MIN_SIZE);
        uint32_t read_blks = 0;
        while ((read_blks + 1) * 8 < p_img_descr->fragments[i].fragment_size) {
            rwsize = read(fd_frag, read_buf, BLK_MIN_SIZE);
            write(fd_dest, read_buf, rwsize);
            read_blks++;
        }
        uint32_t remain_sectors = p_img_descr->fragments[i].fragment_size - read_blks * 8;
        read_buf = realloc(read_buf, SECTOR_SIZE);
        while (remain_sectors--) {
            rwsize = read(fd_frag, read_buf, SECTOR_SIZE);
            write(fd_dest, read_buf, rwsize);
        }
        close(fd_frag);
    }

    close(fd_dest);
    return 0;
}

// fs dfs
void dfs_directory(const char *path, hashtable *htable, int calc_md5, int print_sz, int print_md5, int print_filename) {

    char buf_ps[1024] = {0};
    FILE *ptr;
    char cmd[MAX_PATH_LEN] = {0};
    sprintf(cmd, "du -ha \"%s\" | awk -v FS='\\t' '{print $2}'", path);
//    printf("%s\n", cmd);
    if ((ptr = popen(cmd, "r")) != NULL) {
        struct stat statbuf = {0};
        char file_name[MAX_PATH_LEN] = {0};
        while (fgets(buf_ps, 1024, ptr) != NULL) {
            memset(file_name, 0, sizeof(file_name));
            memset(&statbuf, 0, sizeof(struct stat));
            strcpy(file_name, buf_ps);
            file_name[strlen(file_name) - 1] = 0;
            if (-1 == stat(file_name, &statbuf)) {
                continue;
            }
            if (S_IFREG & statbuf.st_mode) {
                if (print_filename) {
                    printf("%s\n", file_name);
                }
                if (print_sz) {
                    printf("%lu\n", statbuf.st_size);
                }
                if (calc_md5) {
                    unsigned char md5[MD5_LEN * 2 + 1];
                    //这里可能不需要完全通过计算文件md5去判断是否重复 待修改
                    //改不动了 先这样吧
//                    bool ret = Md5Digest(file_name, md5);
                    int ret = md5_file(file_name, md5);
                    md5_2_str(md5);
//                    printf("before insert: %s\n", md5);
//                    show_md5(md5);
                    pFileInfo p_file_info = (FileInfo *) hash_value((void *) md5, htable);
                    if (p_file_info == NULL) {
                        p_file_info = (pFileInfo) malloc(sizeof(FileInfo));
                        p_file_info->file_cnt = 1;
                        p_file_info->file_sz = statbuf.st_size;
                        strcpy(p_file_info->file_name, file_name);
//                        void *key = malloc(MD5_LEN);
//                        memcpy(key, md5, MD5_LEN);
                        hash_insert((void *) strdup((char *) md5), (void *) p_file_info, htable);
                    } else {
                        (p_file_info->file_cnt)++;
                    }
                    if (print_md5) {
                        if (ret) {
                            show_md5(md5);
                        } else {
                            printf("md5\n");
                        }
                    }
                }
            }
            memset(buf_ps, 0, sizeof(buf_ps));
        }
        pclose(ptr);
    }
}

//dfs with filter
void auto_filter_dfs(FragmentType fs_type, int is_os, const char *mount_path, hashtable *htable) {

    uint32_t path_cnt = 0;

    switch (fs_type) {
        case linux_normal: {
            if (is_os) {
                char paths[MAX_PATH_LEN][MAX_DIRC_NUM] = {{"bin"},
                                                          {"lib"},
                                                          {"lib64"},
//                                                          {"root"},
                                                          {"sbin"},
                                                          {"usr"},
                                                          {"home"}};
                path_cnt = 5;
                for (int i = 0; i < path_cnt; i++) {
                    char dfs_path[MAX_PATH_LEN] = {0};
                    sprintf(dfs_path, "%s%s", mount_path, paths[i]);
                    dfs_directory(dfs_path, htable, 1, 0, 0, 0);
                }
            } else {
                dfs_directory(mount_path, htable, 1, 0, 0, 0);
            }

            //先不做处理
//            dfs_directory(mount_path, htable, 1, 0, 0, 0);

            break;
        }
        case ntfs: {
            if (is_os) {
                char paths[MAX_PATH_LEN][MAX_DIRC_NUM] = {{"Windows"}};
                path_cnt = 1;
                for (int i = 0; i < path_cnt; i++) {
                    char dfs_path[MAX_PATH_LEN] = {0};
                    sprintf(dfs_path, "%s%s", mount_path, paths[i]);
                    dfs_directory(dfs_path, htable, 1, 0, 0, 0);
                }

            } else {
                dfs_directory(mount_path, htable, 1, 0, 0, 0);
            }

            break;
        }
        default: {
            break;
        }
    }
}

void Usage() {
    printf("\n\n");
    printf("    /**\n"
           "     *  Usage:\n"
           "     *\n"
           "     *      -x [img_file]: split regular img(according to disk partitions)\n"
           "     *      -s [img_file_path]: split regular imgs in path(according to disk partitions)\n"
           "     *      -o: only generate img descriptor file\n"
           "     *      -r [img_descr]: read img descriptor file\n"
           "     *      -m [img_descr]: merge img fragments\n"
           "     *      -d:[destination path]: path to store fragments and img descriptor\n"
           "     *      -h: help\n"
           "     *\n"
           "     * */");
    printf("\n\n");
}


void test() {
//    hashtable *htable = NULL;
//    htable = create_hashtable(BACKET_SIZE);



    return;
}

int main(int argc, char *argv[]) {


    if (argc < 2) {
        Usage();
        return -1;
    }

    //log init
    char pre[] = LogPathPre;
    if (log_init(pre) != 0) {
        printf("log_init error\n");
        return -1;
    }

//    ParseImgFiles("/data/images", "/data/frag_info", 1);

//    test();
//
//    return -1;


    int opt;
    //opt format
    char *opt_format = "x:s:or:d:hm:";
    int is_reg_split = 0, is_only_header = 0, is_read_header = 0;
    int is_multi_split = 0;
    int is_merge = 0;
    int is_debug = 0;

    char src_img[MAX_PATH_LEN];
    char src_header[MAX_PATH_LEN];
    char split_path[MAX_PATH_LEN];
    char imgs_path[MAX_PATH_LEN];

    while ((opt = getopt(argc, argv, opt_format)) != -1) {
        switch (opt) {
            case 'x': {
                is_reg_split = 1;
                strcpy(src_img, optarg);
                break;
            }
            case 's': {
                is_multi_split = 1;
                strcpy(imgs_path, optarg);
                break;
            }
            case 'o': {
                is_only_header = 1;
                break;
            }
            case 'r': {
                is_read_header = 1;
                strcpy(src_header, optarg);
                break;
            }
            case 'h': {
                //print usage
                Usage();
                break;
            }
            case 'd': {
//                is_debug = 1;
                strcpy(split_path, optarg);
                break;
            }
            case 'm': {
                is_merge = 1;
                strcpy(src_header, optarg);
                break;
            }
            default:
                break;
        }

    }

    if (is_reg_split) {
        //malloc img_descriptor
        pImgDescriptor p_img_descriptor;
        if ((p_img_descriptor = (pImgDescriptor) malloc(sizeof(ImgDescriptor))) == NULL) {
            printf("malloc img_descriptor_error\n");
            return errno;
        }
        ParseImgFile(src_img, p_img_descriptor, split_path, is_only_header);
    } else if (is_multi_split) {
        ParseImgFiles(imgs_path, split_path, is_only_header);
    } else if (is_read_header) {
        pImgDescriptor p_img_descr = (ImgDescriptor *) malloc(sizeof(FragmentDescriptor));
        if (ReadImgDescr(src_header, p_img_descr) == 0) {
            CheckImgDescr(p_img_descr);
        } else {
            printf("ReadImgDescr failed\n");
        }
    } else if (is_merge) {
        pImgDescriptor p_img_descr = (ImgDescriptor *) malloc(sizeof(FragmentDescriptor));
        if (ReadImgDescr(src_header, p_img_descr) == 0) {
            CheckImgDescr(p_img_descr);
            if (MergeFragments(p_img_descr, "/tmp") == 0) {
                printf("MergeFragments finish\n");
            } else {
                printf("MergeFragments error\n");
            }
        } else {
            printf("ReadImgDescr failed\n");
        }
    }


    return 0;
}
