//
// Created by 56556 on 2018/10/25.
//

#include <stdio.h>
#include <stdlib.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <dirent.h>
#include <unistd.h>
#include <getopt.h>
#include <fcntl.h>
#include <dirent.h>
#include <errno.h>
#include <sys/time.h>
#include "dedup.h"

/* unique block number in package */
static unsigned int g_unique_block_nr = 0;
/* regular file number in package */
static unsigned int g_regular_file_nr = 0;
/* block length */
static unsigned int g_block_size = BLOCK_SIZE;
/* hashtable backet number */
static unsigned int g_htab_backet_nr = BACKET_SIZE;

//calc run time
struct timeval time_start, time_end;
double run_time = 0.0;

void show_md5(unsigned char md5_checksum[16]) {
    int i;
    for (i = 0; i < 16; i++) {
        printf("%02x", md5_checksum[i]);
    }
    printf("\n");
}

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
    printf("block_size = %d\n", dedup_pkg_hdr.block_size);
    printf("block_num = %d\n", dedup_pkg_hdr.block_num);
    printf("blockid_size = %d\n", dedup_pkg_hdr.blockid_size);
    printf("magic_num = 0x%x\n", dedup_pkg_hdr.magic_num);
    printf("file_num = %d\n", dedup_pkg_hdr.file_num);
    printf("metadata_offset = %lld\n", dedup_pkg_hdr.metadata_offset);
}

int dedup_regfile(char *fullpath, int prepos, int fd_bdata, int fd_mdata, hashtable *htable, int debug) {
    int fd;
    unsigned long long cnt = 0;
    unsigned long long block_total_num=0;
    unsigned long long block_unique_num=0;
    unsigned char *buf = NULL;
    unsigned int rwsize, pos;
    unsigned char md5_checksum[16 + 1] = {0};
    unsigned int *metadata = NULL;
    unsigned int block_num = 0;
    struct stat statbuf;
    dedup_entry_header dedup_entry_hdr;
    if (-1 == (fd = open(fullpath, O_RDONLY))) {
        perror("open regulae file");
        return errno;
    }
    if (-1 == fstat(fd, &statbuf)) {
        perror("fstat regular file");
        goto _DEDUP_REGFILE_EXIT;
    }
    block_num = statbuf.st_size / g_block_size;
    block_total_num=block_num;
    metadata = (unsigned int *) malloc(BLOCK_ID_SIZE * block_num);
    if (metadata == NULL) {
        perror("malloc metadata for regfile");
        goto _DEDUP_REGFILE_EXIT;
    }
    buf = (unsigned char *) malloc(g_block_size);
    if (buf == NULL) {
        perror("malloc buf for regfile");
        goto _DEDUP_REGFILE_EXIT;
    }
    pos = 0;
    while (rwsize = read(fd, buf, g_block_size)) {
        /* if the last block */
        if (rwsize != g_block_size)
            break;
        /* calculate md5 */
        md5(buf, rwsize, md5_checksum);
//        show_md5(md5_checksum);
        /* check hashtable with hashkey */
        unsigned int *bindex = (block_id_t *) hash_value((void *) md5_checksum, htable);
        if (bindex == NULL) {

            //cnt block_unique_num
            block_unique_num++;

            bindex = (unsigned int *) malloc(BLOCK_ID_SIZE);
            if (NULL == bindex) {
                perror("malloc in dedup_regfile");
                break;
            }
            /* insert hash entry and write unique block into bdata*/
            *bindex = g_unique_block_nr;
            hash_insert((void *) strdup((char *) md5_checksum), (void *) bindex, htable);
            //唯一数据块写入 fd_bdata
            write(fd_bdata, buf, rwsize);
            g_unique_block_nr++;
        }
        //for test
        cnt++;
        if (cnt > 100000) {
            cnt = 0;
            //record time
            gettimeofday(&time_end, NULL);
            //calc run time
            printf("RUN TIME(s): %lf\n",
                   (time_end.tv_sec - time_start.tv_sec) + (double) (time_end.tv_usec - time_start.tv_usec) / 1000000);

        }
        metadata[pos] = *bindex;
        memset(buf, 0, g_block_size);
        memset(md5_checksum, 0, 16 + 1);
        pos++;
    }

    printf("\n\n\nmd5 dedup finish, next write metadata\n\n");
    printf("block_total_num is %llu\nblock_unique_num is %llu\ndup_rate is %lf\n\n",block_total_num,block_unique_num,(double)(block_total_num-block_unique_num)/block_total_num);
    //record time
    gettimeofday(&time_end, NULL);
    //calc run time
    printf("RUN TIME(s): %lf\n\n",
           (time_end.tv_sec - time_start.tv_sec) + (double) (time_end.tv_usec - time_start.tv_usec) / 1000000);



    /* write metadata into mdata */
    printf("start write metadata...\n");

    dedup_entry_hdr.path_len = strlen(fullpath) - prepos;
    dedup_entry_hdr.block_num = block_num;
    dedup_entry_hdr.entry_size = BLOCK_ID_SIZE;
    dedup_entry_hdr.last_block_size = rwsize;
    dedup_entry_hdr.mode = statbuf.st_mode;
    write(fd_mdata, &dedup_entry_hdr, sizeof(dedup_entry_header));
    write(fd_mdata, fullpath + prepos, dedup_entry_hdr.path_len);
    write(fd_mdata, metadata, BLOCK_ID_SIZE * block_num);
    write(fd_mdata, buf, rwsize);
    g_regular_file_nr++;
    _DEDUP_REGFILE_EXIT:
    close(fd);
    if (metadata) free(metadata);
    if (buf) free(buf);

    printf("\nwrite metadata finish, end\n\n");
    //record time
    gettimeofday(&time_end, NULL);
    //calc run time
    printf("RUN TIME(s): %lf\n\n",
           (time_end.tv_sec - time_start.tv_sec) + (double) (time_end.tv_usec - time_start.tv_usec) / 1000000);


    return 0;
}

int dedup_dir(char *fullpath, int prepos, int fd_bdata, int fd_mdata, hashtable *htable, int debug) {
    DIR *dp;
    struct dirent *dirp;
    struct stat statbuf;
    char subpath[MAX_PATH_LEN] = {0};
    if (NULL == (dp = opendir(fullpath))) {
        return errno;
    }
    while ((dirp = readdir(dp)) != NULL) {
        if (strcmp(dirp->d_name, ".") == 0 || strcmp(dirp->d_name, "..") == 0)
            continue;
        sprintf(subpath, "%s/%s", fullpath, dirp->d_name);
        if (0 == lstat(subpath, &statbuf)) {
            if (debug)
                printf("%s\n", subpath);
            if (S_ISREG(statbuf.st_mode))
                dedup_regfile(subpath, prepos, fd_bdata, fd_mdata, htable, debug);
            else if (S_ISDIR(statbuf.st_mode))
                dedup_dir(subpath, prepos, fd_bdata, fd_mdata, htable, debug);
        }
    }
    closedir(dp);
    return 0;
}

int dedup_package(int path_nr, char **src_paths, char *dest_file, int debug) {
    int fd, fd_bdata, fd_mdata, ret = 0;
    struct stat statbuf;
    hashtable *htable = NULL;
    dedup_package_header dedup_pkg_hdr;
    char **paths = src_paths;
    int i, rwsize, prepos;
    char buf[1024 * 1024] = {0};
    if (-1 == (fd = open(dest_file, O_WRONLY | O_CREAT, 0755))) {
        perror("open dest file");
        ret = errno;
        goto _DEDUP_PKG_EXIT;
    }
    htable = create_hashtable(g_htab_backet_nr);
    if (NULL == htable) {
        perror("create_hashtable");
        ret = errno;
        goto _DEDUP_PKG_EXIT;
    }
    fd_bdata = open("./.bdata", O_RDWR | O_CREAT, 0777);
    fd_mdata = open("./.mdata", O_RDWR | O_CREAT, 0777);
    if (-1 == fd_bdata || -1 == fd_mdata) {
        perror("open bdata or mdata");
        ret = errno;
        goto _DEDUP_PKG_EXIT;
    }
    g_unique_block_nr = 0;
    g_regular_file_nr = 0;
    for (i = 0; i < path_nr; i++) {
        if (lstat(paths[i], &statbuf) < 0) {
            perror("lstat source path");
            ret = errno;
            goto _DEDUP_PKG_EXIT;
        }
        if (S_ISREG(statbuf.st_mode) || S_ISDIR(statbuf.st_mode)) {
            if (debug)
                printf("%s\n", paths[i]);
            /* get filename position in pathname */
            prepos = strlen(paths[i]) - 1;
            if (strcmp(paths[i], "/") != 0 && *(paths[i] + prepos) == '/') {
                *(paths[i] + prepos--) = 0;
            }
            while (*(paths[i] + prepos) != '/' && prepos >= 0) prepos--;
            prepos++;
            if (S_ISREG(statbuf.st_mode))
                dedup_regfile(paths[i], prepos, fd_bdata, fd_mdata, htable, debug);
            else
                dedup_dir(paths[i], prepos, fd_bdata, fd_mdata, htable, debug);
        } else {
            if (debug)
                printf("%s is not regular file or directory.\n", paths[i]);
        }
    }
    /* fill up dedup package header */
    dedup_pkg_hdr.block_size = g_block_size;
    dedup_pkg_hdr.block_num = g_unique_block_nr;
    dedup_pkg_hdr.blockid_size = BLOCK_ID_SIZE;
    dedup_pkg_hdr.magic_num = DEDUP_MAGIC_NUM;
    dedup_pkg_hdr.file_num = g_regular_file_nr;
    dedup_pkg_hdr.metadata_offset = DEDUP_PKGHDR_SIZE + g_block_size * g_unique_block_nr;
    write(fd, &dedup_pkg_hdr, DEDUP_PKGHDR_SIZE);
    /* fill up dedup package unique blocks*/
    lseek(fd_bdata, 0, SEEK_SET);
    while (rwsize = read(fd_bdata, buf, 1024 * 1024)) {
        write(fd, buf, rwsize);
        memset(buf, 0, 1024 * 1024);
    }
    /* fill up dedup package metadata */
    lseek(fd_mdata, 0, SEEK_SET);
    while (rwsize = read(fd_mdata, buf, 1024 * 1024)) {
        write(fd, buf, rwsize);
        memset(buf, 0, 1024 * 1024);
    }
    if (debug)
        show_pkg_header(dedup_pkg_hdr);
    _DEDUP_PKG_EXIT:
    close(fd);
    close(fd_bdata);
    close(fd_mdata);
    unlink("./.bdata");
    unlink("./.mdata");
    hash_free(htable);

    return ret;
}

int main(int argc, char *argv[]) {

    //example
    // ./FileDedup -z /destpath/destfile.ded /srcpath/srcfile

    //record start time
    gettimeofday(&time_start, NULL);

    if (remove("runtime.txt") != 0) {
        printf("delete runtime.rd failed\n");
    }

    FILE *fp;

    int opt;
    int ret = -1;
    //opt format
    char *opt_format = "zb:d";
    int is_compress = 0;
    int is_debug = 0;

    //tmp file path
    char *tmp_file = "./.tmp.ded";

    //dest file fullpath
    char dest_fullpath[MAX_PATH_LEN] = {0};
    //src file paths
    char **src_paths;
    int src_path_nr;

    while ((opt = getopt(argc, argv, opt_format)) != -1) {
        switch (opt) {
            case 'z': {
                is_compress = 1;
                break;
            }
            case 'b': {
                g_block_size = atoi(optarg);
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
    int cur_ind = optind;
    sprintf(dest_fullpath, "%s", argv[cur_ind]);
    printf("dest_fullpath: %s\n", dest_fullpath);
    src_paths = argv + optind + 1;
    src_path_nr = argc - optind - 1;
    printf("src_path_nr: %d\n", src_path_nr);

    for (int i = 0; i < src_path_nr; i++) {
        printf("src_paths[%d]: %s\n", i, src_paths[i]);
    }

    printf("is_compress: %s\n", is_compress == 1 ? "true" : "false");
    printf("is_debug: %s\n", is_debug == 1 ? "true" : "false");
    printf("block_size(B): %u\n", g_block_size);

    if (is_compress) {
        //dedup and compress
        if ((ret = dedup_package(src_path_nr, src_paths, tmp_file, is_debug)) == 0) {
            //compress
            ret = zlib_compress_file(tmp_file, argv[optind]);
            remove(tmp_file);
        }

    } else {
        //only dedup
        ret = dedup_package(src_path_nr, src_paths, dest_fullpath, is_debug);
    }

    //record end time
    gettimeofday(&time_end, NULL);
    //calc run time
    double runtime = (time_end.tv_sec - time_start.tv_sec) + (double) (time_end.tv_usec - time_start.tv_usec) / 1000000;
    printf("RUN TIME(s): %lf\n", runtime);


    if ((fp = fopen("runtime.txt", "w+")) != NULL) {
        fprintf(fp, "%lf\n", runtime);
        fclose(fp);
    }


    return ret;
}