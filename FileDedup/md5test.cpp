//
// Created by 56556 on 2018/12/28.
//

#include <stdio.h>
#include <string.h>
#include <stdint.h>
#include <sys/stat.h>
#include "md5.h"

//print md5
void show_md5(unsigned char md5_checksum[16]) {
    int i;
    for (i = 0; i < 16; i++) {
        printf("%02x", md5_checksum[i]);
    }
    printf("\n");
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

bool Md5Sum(const char *file_path, unsigned char *result) {

    struct stat statbuf = {0};

    if (-1 == stat(file_path, &statbuf)) {
        return false;
    }
    if (S_IFREG & statbuf.st_mode) {
        char cmd[1024] = {0}, buf_ps[1024] = {0}, md5_string[32 + 1] = {0};
        sprintf(cmd, "md5sum %s", file_path);
        FILE *ptr;
        if ((ptr = popen(cmd, "r")) != NULL) {
            while (fgets(buf_ps, 1024, ptr) != NULL) {
                memcpy(md5_string, buf_ps, 32);
                memset(buf_ps, 0, sizeof(buf_ps));
                break;
            }
            pclose(ptr);
            return CheckMd5String((unsigned char *) md5_string) && Md5String2Bin(md5_string, result);
        } else {
            return false;
        }
    } else {
        return false;
    }
}

int main(int argc, char *argv[]) {


    unsigned char md5_digest[16] = {0};


    Md5Sum(argv[1], md5_digest);

    show_md5(md5_digest);



//    printf("%s: ", argv[1]);
//
//
//    DefaultMd5(argv[1], md5_digest);
//
////    if (md5_file(argv[1],md5_digest)!=0){
////        printf("error\n");
////    }
//
//    printf("%s\n",md5_digest);

    return 0;
}