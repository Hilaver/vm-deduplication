//
// Created by 56556 on 2018/12/21.
//

#pragma pack(1)

#ifndef FILEDEDUP_IMG_SPLIT_H
#define FILEDEDUP_IMG_SPLIT_H


#include <stdlib.h>
#include <string>
#include <sys/types.h>
#include <dirent.h>
#include <unistd.h>
#include <getopt.h>
#include <fcntl.h>
#include <dirent.h>
#include <errno.h>
#include <sys/time.h>

#include "log.h"
#include "md5.h"
#include "hash.h"
#include "hashtable.h"
//#include "dedup.h"
#include "util.h"

using namespace std;

//#define MAX_PATH_LEN    256
#define MAX_FRAG_NUM    4096
#define MAX_DIRC_NUM    4096

#define MBR_LEN 446
#define SECTOR_SIZE 512
#define BLK_MIN_SIZE 4096

#define VDI_HEADER_LEN 0X1000

#define LogPathPre "/zcy/";

#define MOUNT_PATH "/mnt/"

static uint32_t global_fragment_nb = 0;
static uint32_t global_img_nb;

//DPT表项
typedef struct _part_tab_entry {
    uint8_t boot_signature; //引导标志
    uint8_t start_head; //CHS寻址方式，起始磁头
    uint8_t start_sector;   //起始扇区，本字节低六位
    uint8_t start_cylinder; //起始磁道(柱面)，start_sector高二位和本字节
    uint8_t system_signature;   //分区类型标志
    uint8_t end_head;   //终止磁头
    uint8_t end_sector; //终止扇区
    uint8_t end_cylinder;   //终止磁道
    uint32_t start_sector_nb;   //LBA寻址，起始扇区号
    uint32_t total_sectors_num; //该分区扇区总数
} PartTabEntry, *pPartTabEntry;

//MBR扇区
typedef struct _mbr_sector {
    uint8_t mbr_loader[MBR_LEN];
    PartTabEntry part_tab_entrys[4];
    uint8_t end_signature[2];
} MbrSector, *pMbrSector;

//typedef struct _file_info {
////    char file_name[MAX_PATH_LEN];
//    uint64_t file_sz;
//    uint32_t file_cnt;
//} FileInfo, pFileInfo;

//镜像类型
typedef enum _img_type {
    raw, vmdk, qcow2, vhd, vdi, other
} ImgType;

//磁盘类型
typedef enum _disk_type {
    mbr, gpt, pv, unknown
} DiskType;

typedef enum _mounted_type {
    linux_os, linux_else, windows_os, windows_else, unknown_mount_type
} MountedType;

typedef enum _fragment_type {
    img_header, // 【0】文件头
    boot_interval,  // 【1】 0扇区到第一分区的间隙
    ntfs,   // 【2】 07h
    fat32,  // 【3】 0Bh 0Ch
    fat16,  // 【4】 06h
    linux_normal,  // 【5】 83h
    linux_swap, // 【6】 82h
    lvm, // 【7】 8Eh
    empty,   // 【8】 未分配空间
    other_type
} FragmentType;

typedef struct _fragment_descriptor {

    uint32_t fragment_unique_nb;    //片段唯一编号
    uint32_t fragment_infile_nb;    //片段在文件内的编号

    uint64_t fragment_offset;   //该片段在原文件的偏移 单位：扇区
    uint64_t fragment_size; //该片段size 单位：扇区

    uint32_t boot_signature;    //启动标志 【是否为系统分区】
    uint32_t fragment_type; //该片段的类型 【fs_type|boot_interval|img_header|empty|other】
    uint8_t fragment_simhash[MD5_LEN];    //分段的simhash值
    char fragment_name[MAX_NAME_LEN];   //片段name
    char fragment_path[MAX_PATH_LEN];   //片段路径
    char src_path_name[MAX_NAME_LEN];   //原文件绝对路径
    char fragment_file_info_path[MAX_NAME_LEN];   //文件系统中所有文件的信息.json【key为文件md5】
} FragmentDescriptor, *pFragmentDescriptor;


typedef struct _img_descriptor {

    uint32_t img_unique_nb; //镜像文件唯一编号

    ImgType img_type;  //文件后缀类型
    uint64_t img_size;  //文件size[Byte]
    char img_name[MAX_NAME_LEN];    //文件名
    char img_path[MAX_PATH_LEN];    //文件路径

    DiskType disk_type; //磁盘镜像的分区类型【MBR|GPT|PV|UNKNOWN】
    uint32_t fragment_nums;  //镜像文件分段个数
    uint32_t boot_sector_offset;    //磁盘引导分区在文件中的偏移 【可用来判定镜像文件是否包含文件头，如vdi】

    FragmentDescriptor fragments[0];   //分割后的片段
} ImgDescriptor, *pImgDescriptor;


typedef struct _file_info {
    char file_name[MAX_PATH_LEN];
    uint64_t file_sz;
    uint32_t file_cnt;
} FileInfo, *pFileInfo;

typedef struct _block_info {
    uint64_t block_id;
    uint32_t block_cnt;
} BlockInfo, *pBlockInfo;

void dfs_directory(const char *path, hashtable *htable, int calc_md5, int print_sz, int print_md5, int print_filename);

void auto_filter_dfs(FragmentType fs_type, int is_os, const char *mount_path, hashtable *htable);

//void show_simhash(uint8_t simhash[MD5_LEN]);

void CheckFragDescr(pFragmentDescriptor p_frag_descr);

void CheckImgDescr(pImgDescriptor p_img_descr);

FragmentType GetFragmentType(uint8_t system_signature);

ImgType GetImgType(const char *type_str);

DiskType GetDiskType(const char *file_name);

MountedType GetMountedType(const char *mount_path, FragmentType frag_type);

bool WriteFragment2File(FragmentDescriptor *p_frag_descr);

int ParseImgFile(char *file_name, pImgDescriptor p_img_descriptor, const char *dest_path, int only_descr);

int ReadImgDescr(const char *file, pImgDescriptor p_img_descr);

int MergeFragments(pImgDescriptor p_img_descr, const char *dest_file_path);

int AccumulateMd5ByFixedChunk(void *key, void *data);

int AccumulateMd5(void *key, void *data);

int GetFragSimhash(pFragmentDescriptor p_frag_descr, uint8_t simhash[MD5_LEN]);

int CalcSimhashByPy(pFragmentDescriptor p_frag_descr, const char *mount_path, uint8_t simhash[MD5_LEN]);

int GetFragSimhashByFixedChunk(pFragmentDescriptor p_frag_descr, uint8_t simhash[MD5_LEN], uint32_t chunk_size);

void dfs_directory(const char *path, hashtable *htable, int calc_md5, int print_sz, int print_md5, int print_filename);

void Usage();


#endif //FILEDEDUP_IMG_SPLIT_H



