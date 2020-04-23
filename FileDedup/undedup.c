//
// Created by 56556 on 2018/10/25.
//

#include <stdio.h>
#include <stdlib.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <unistd.h>
#include <getopt.h>
#include <fcntl.h>
#include <errno.h>
#include "dedup.h"

/* block length */
static unsigned int g_block_size = BLOCK_SIZE;

//print buffer in byte
void printBuffer(void *buffer, long long size) {
    char *p = (char *) buffer;
    long long pos = 0;
    while (pos < size) {
//        fprintf(fp,"%+02X ", *(p++));
        printf("%+02X ", *(p++));
        if (++pos % 16 == 0) { /*fprintf(fp,"\n");*/ printf("\n"); }
    }
}

void show_pkg_header(dedup_package_header dedup_pkg_hdr) {
    printf("block_size = %d/n", dedup_pkg_hdr.block_size);
    printf("block_num = %d/n", dedup_pkg_hdr.block_num);
    printf("blockid_size = %d/n", dedup_pkg_hdr.blockid_size);
    printf("magic_num = 0x%x/n", dedup_pkg_hdr.magic_num);
    printf("file_num = %d/n", dedup_pkg_hdr.file_num);
    printf("metadata_offset = %lld/n", dedup_pkg_hdr.metadata_offset);
}

int prepare_target_file(char *pathname, char *basepath, int mode) {
    char fullpath[MAX_PATH_LEN] = {0};
    char path[MAX_PATH_LEN] = {0};
    char *p = NULL;
    int pos = 0, fd;
    if(basepath[strlen(basepath)-1]=='/'){
        sprintf(fullpath, "%s%s", basepath, pathname);
    }
    else{
        sprintf(fullpath, "%s/%s", basepath, pathname);
    }

    p = fullpath;
    while (*p)
    {
        path[pos++] = *p;
        if (*p == '/'){
            if (access(path,0)!=0){
                mkdir(path, 0755);
            }
        }
        p++;
    }
    fd = open(fullpath, O_WRONLY | O_CREAT, mode);
    return fd;
}

int undedup_regfile(int fd, dedup_entry_header dedup_entry_hdr, char *dest_dir, int debug) {
    char pathname[MAX_PATH_LEN] = {0};
    block_id_t *metadata = NULL;
    unsigned int block_num = 0;
    char *buf = NULL;
    char *last_block_buf = NULL;
    long long offset, i;
    int fd_dest, ret = 0;
    metadata = (block_id_t *) malloc(BLOCK_ID_SIZE * dedup_entry_hdr.block_num);
    if (NULL == metadata)
        return errno;
    buf = (char *) malloc(g_block_size);
    last_block_buf = (char *) malloc(g_block_size);
    if (NULL == buf || NULL == last_block_buf) {
        ret = errno;
        goto _UNDEDUP_REGFILE_EXIT;
    }
    read(fd, pathname, dedup_entry_hdr.path_len);
    read(fd, metadata, BLOCK_ID_SIZE * dedup_entry_hdr.block_num);
    read(fd, last_block_buf, dedup_entry_hdr.last_block_size);
    fd_dest = prepare_target_file(pathname, dest_dir, dedup_entry_hdr.mode);
    if (fd_dest == -1) {
        printf("prepare_target_file failed\n");
        ret = errno;
        goto _UNDEDUP_REGFILE_EXIT;
    }
    if (debug)
        printf("%s/%s/n", dest_dir, pathname);
    /* write regular block */
    block_num = dedup_entry_hdr.block_num;
    for (i = 0; i < block_num; ++i) {
        offset = DEDUP_PKGHDR_SIZE + metadata[i] * g_block_size;
        lseek(fd, offset, SEEK_SET);
        read(fd, buf, g_block_size);
        write(fd_dest, buf, g_block_size);
    }
    /* write last block */
    write(fd_dest, last_block_buf, dedup_entry_hdr.last_block_size);
    close(fd_dest);
    _UNDEDUP_REGFILE_EXIT:
    if (metadata) free(metadata);
    if (buf) free(buf);
    if (last_block_buf) free(last_block_buf);
    return ret;
}

int undedup_package(char *src_file, char *dest_dir, int debug) {
    int fd, i, ret = 0;
    dedup_package_header dedup_pkg_hdr;
    dedup_entry_header dedup_entry_hdr;
    unsigned long long offset;
    if (-1 == (fd = open(src_file, O_RDONLY))) {
        printf("open src_file failed\n");
        perror("open source file");
        return errno;
    }
    if (read(fd, &dedup_pkg_hdr, DEDUP_PKGHDR_SIZE) != DEDUP_PKGHDR_SIZE) {
        printf("read dedup_package_header failed\n");
        perror("read dedup_package_header");
        ret = errno;
        goto _UNDEDUP_PKG_EXIT;
    }
    if (debug)
        show_pkg_header(dedup_pkg_hdr);
    offset = dedup_pkg_hdr.metadata_offset;
    for (i = 0; i < dedup_pkg_hdr.file_num; ++i) {
        if (lseek(fd, offset, SEEK_SET) == -1) {
            ret = errno;
            break;
        }

        if (read(fd, &dedup_entry_hdr, DEDUP_ENTRYHDR_SIZE) != DEDUP_ENTRYHDR_SIZE) {
            ret = errno;
            break;
        }
        ret = undedup_regfile(fd, dedup_entry_hdr, dest_dir, debug);
        if (ret != 0)
            break;
        offset += DEDUP_ENTRYHDR_SIZE;
        offset += dedup_entry_hdr.path_len;
        offset += dedup_entry_hdr.block_num * dedup_entry_hdr.entry_size;
        offset += dedup_entry_hdr.last_block_size;
    }
    _UNDEDUP_PKG_EXIT:
    close(fd);
    return ret;
}


int main(int argc, char *argv[]) {

    //opt format
    char *opt_format = "zb:d";
    int opt;
    int ret = -1;
    int is_decompress = 0;
    int is_debug = 0;
    //tmp file path
    char *tmp_file = "./.tmp.bz";

    while ((opt = getopt(argc, argv, opt_format)) != -1) {
        switch (opt) {
            case 'z': {
                is_decompress = 1;
                break;
            }

            case 'd': {
                is_debug = 1;
                break;
            }
            default:
                break;
        }
    }


    //dest file fullpath
    char dest_path[MAX_PATH_LEN] = {0};
    //src file fullpath
    char src_fullpath[MAX_PATH_LEN] = {0};

    int cur_ind = optind;
    sprintf(dest_path, "%s", argv[cur_ind]);
    sprintf(src_fullpath, "%s", argv[cur_ind + 1]);


    printf("dest_path: %s\n", dest_path);
    printf("src_fullpath: %s\n", src_fullpath);

    printf("is_decompress: %s\n", is_decompress == 1 ? "true" : "false");
    printf("is_debug: %s\n", is_debug == 1 ? "true" : "false");


    if (is_decompress) {
        //decompress and undedup
//        ret = zlib_decompress_file(src_fullpath, tmp_file);
//        if (ret == 0) {
//            ret=undedup_package(src_fullpath, dest_path, is_debug);
//            remove(tmp_file);
//        }
    }
    else{
        //only undedup
        ret=undedup_package(src_fullpath, dest_path, is_debug);
    }

    return ret;

}
