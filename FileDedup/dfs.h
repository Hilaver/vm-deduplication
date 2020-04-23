//
// Created by 56556 on 2018/12/21.
//

#pragma pack(1)

#ifndef FILEDEDUP_DFS_H
#define FILEDEDUP_DFS_H


#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <dirent.h>
#include <unistd.h>
#include <getopt.h>
#include <fcntl.h>
#include <dirent.h>
#include <errno.h>
#include <sys/time.h>
#include "md5.h"
#include "hash.h"
#include "hashtable.h"
#include "dedup.h"

//#define MAX_PATH_LEN    255
#define MAX_DIRC_NUM    4096

//typedef struct _file_info {
//    char file_name[MAX_PATH_LEN];
//    uint64_t file_sz;
//    uint32_t file_cnt;
//} FileInfo, *pFileInfo;



void show_md5(unsigned char md5_checksum[16]);

int is_block_zero(void *buffer, unsigned int size);

int fixed_size_md5(char *file, unsigned int block_size, hashtable *htable);

bool ExecuteCMD(const char *cmd, char *result);

void dfs_directory(const char *path, hashtable *htable, int print_sz, int print_md5);

//void auto_filter_dfs(FragmentType fs_type, int is_boot, const char *mount_path, hashtable *htable);

void Usage_dfs();


#endif //FILEDEDUP_DFS_H
