//
// Created by 56556 on 2018/12/28.
//

#ifndef FILEDEDUP_UTIL_H
#define FILEDEDUP_UTIL_H

#include <stdio.h>
#include <string.h>
#include <stdint.h>
#include <iostream>
#include <sys/stat.h>

#define MAX_NAME_LEN    256

#define BACKET_SIZE     10485760

#define MD5_LEN 16

using namespace std;

void show_simhash(uint8_t simhash[MD5_LEN]);

void show_md5(unsigned char md5_checksum[MD5_LEN]);

string Int2String(int n);

void format_cmd(char *cmd);

bool ExecuteCMD(const char *cmd, char *result);

void md5_2_str(unsigned char *md5_checksum);

void simhash_2_bin(long long int *simhash_arr, uint8_t simhash[MD5_LEN]);

bool Md5String2Bin(const char *md5_string, unsigned char *md5_digest);

bool CheckMd5String(unsigned char *md5str);

bool Md5Digest(const char *file_path, unsigned char *result);

int is_block_zero(void *buffer, unsigned int size);


#endif //FILEDEDUP_UTIL_H
