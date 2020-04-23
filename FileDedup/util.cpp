//
// Created by 56556 on 2018/12/28.
//

#include "util.h"


//print simhash
void show_simhash(uint8_t simhash[MD5_LEN]) {
    int i;
    for (i = 0; i < MD5_LEN; i++) {
        printf("%02x", simhash[i]);
    }
    printf("\n");
}

//print md5
void show_md5(unsigned char md5_checksum[MD5_LEN]) {
    int i;
    for (i = 0; i < MD5_LEN; i++) {
        printf("%02x", md5_checksum[i]);
    }
    printf("\n");
}

void md5_2_str(unsigned char *md5_checksum) {
    static char *hex = "0123456789abcdef";
    char md5_str[33] = {0};
    int i, j = 0;

    for (i = 0; i < 16; i++) {
        md5_str[j++] = hex[(0xf0 & md5_checksum[i]) >> 4];
        md5_str[j++] = hex[0x0f & md5_checksum[i]];
    }
    md5_str[j] = '\0';
    memcpy(md5_checksum, md5_str, 33);
}

void simhash_2_bin(long long int *simhash_arr, uint8_t simhash[MD5_LEN]) {
    unsigned char *p_c = (unsigned char *) simhash;
    for (int i = 0; i < MD5_LEN; i++) {
        for (int j = 0; j < 8; j++) {
            (*p_c) |= ((simhash_arr[i * 8 + j]) << (8 - 1 - j));
        }
        p_c++;
    }
}

bool Md5String2Bin(const char *md5_string, unsigned char *md5_digest) {
    if (strlen(md5_string) != 32) {
        return false;
    }
    for (int i = 0; i < 32; i += 2) {
        unsigned char ch1 = (unsigned char) md5_string[i], ch2 = (unsigned char) md5_string[i + 1];
        ch1 = ((ch1 < 'a' ? ch1 - '0' : ch1 - 'a' + 10) & (unsigned char) 0x0f);
        ch2 = ((ch2 < 'a' ? ch2 - '0' : ch2 - 'a' + 10) & (unsigned char) 0x0f);
        md5_digest[i >> 1] = (((ch1 & (0x0f)) << 4) | (ch2 & (0x0f))) & (0xff);
    }
//    getchar();
    return true;
}

bool CheckMd5String(unsigned char *md5str) {
    for (int i = 0; i < 32; i++) {
        if ((!(md5str[i] >= '0' && md5str[i] <= '9')) && (!(md5str[i] >= 'a' && md5str[i] <= 'f'))) {
            return false;
        }
    }
    return true;
}

void format_cmd(char *cmd) {
    size_t str_len = strlen(cmd);
    char format_cmd_str[1024] = {0};
    int ch_cnt = 0;
    for (int i = 0; i < str_len; i++) {
        if (cmd[i] == '$') {
            format_cmd_str[ch_cnt++] = '\\', format_cmd_str[ch_cnt++] = '$';
        } else {
            format_cmd_str[ch_cnt++] = cmd[i];
        }
    }
    strcpy(cmd, format_cmd_str);
}

bool Md5Digest(const char *file_path, unsigned char *result) {

    struct stat statbuf = {0};

    if (-1 == stat(file_path, &statbuf)) {
        return false;
    }
    if (S_IFREG & statbuf.st_mode) {
        char cmd[1024] = {0}, buf_ps[1024] = {0}, md5_string[32 + 1] = {0};
        sprintf(cmd, "md5sum \"%s\"", file_path);
        format_cmd(cmd);
        FILE *ptr;
        if ((ptr = popen(cmd, "r")) != NULL) {
            while (fgets(buf_ps, 33, ptr) != NULL) {
                memcpy(md5_string, buf_ps, 32);
//                memset(buf_ps, 0, sizeof(buf_ps));
                break;
            }
            pclose(ptr);
            //for debug
//            printf("md5 str: %s\n", md5_string);
//            bool ret = CheckMd5String((unsigned char *) md5_string) && Md5String2Bin(md5_string, result);
            bool ret = CheckMd5String((unsigned char *) md5_string);
            ret ? memcpy(result, md5_string, strlen(md5_string)) : result = NULL;
//            show_md5(result);
            return ret;
        } else {
            return false;
        }
    } else {
        return false;
    }
}


//int to string
string Int2String(int n) {
    char ret[MAX_NAME_LEN];
    sprintf(ret, "%d", n);
    return string(ret);
}

bool ExecuteCMD(const char *cmd, char *result) {

    char buf_ps[1024] = {0};
    FILE *ptr;
    if ((ptr = popen(cmd, "r")) != NULL) {
        while (fgets(buf_ps, 1024, ptr) != NULL) {
            strcat(result, buf_ps);
            memset(buf_ps, 0, sizeof(buf_ps));
        }
        pclose(ptr);
        return true;
    }
    return false;
}

//判断数据块是否是零块
int is_block_zero(void *buffer, unsigned int size) {
    unsigned char *ptr;
    unsigned int pos = 0;
    ptr = (unsigned char *) buffer;
    for (; pos < size; pos++) {
        if (*ptr != 0) {
            return 0;
        }
        ptr++;
    }
    return 1;
}