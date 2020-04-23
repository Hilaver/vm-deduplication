//
// Created by 56556 on 2018/12/18.
//

#pragma pack(1)

#include "dfs.h"


/* hashtable backet number */
static unsigned int g_htab_backet_nr = BACKET_SIZE;
//static unsigned int g_unique_block_nr = 0;
//static unsigned int g_unique_file_nr = 0;
//calc run time
struct timeval time_start, time_end;
double run_time = 0.0;

//print md5
void show_md5(unsigned char md5_checksum[16]) {
    int i;
    for (i = 0; i < 16; i++) {
        printf("%02x", md5_checksum[i]);
    }
    printf("\n");
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


//分块计算文件MD5
//int fixed_size_md5(char *file, unsigned int block_size, hashtable *htable) {
//
//    int fd;
//    unsigned int rwsize, pos = 0;
//    unsigned char md5_checksum[16 + 1] = {0};
//    unsigned char *buf = NULL;
//    unsigned long long block_total_num = 0;
//    unsigned long long block_unique_num = 0;
//    buf = (unsigned char *) malloc(block_size);
//
////    long long int simhash_arr[128] = {0};
//
//
//    if (-1 == (fd = open(file, O_RDONLY))) {
//        perror("open regulae file");
//        return errno;
//    }
//    struct stat statbuf;
//    if (-1 == fstat(fd, &statbuf)) {
//        perror("fstat regular file");
//        return errno;
//    }
//    block_total_num = statbuf.st_size / block_size;
//    //record time
////    gettimeofday(&time_end, NULL);
//
//
//    printf("block size:%u\n", block_size);
//
//    while (rwsize = read(fd, buf, block_size)) {
//        /* if the last block */
////        if (rwsize != block_size)
////            break;
//
//        /* calculate md5 */
//
//
//
//
//
//        if (is_block_zero((void *) buf, rwsize)) {
////            printf("above is zero block\n");
////            getchar();
//        } else {
////            md5(buf, rwsize, md5_checksum);
////            show_md5(md5_checksum);
//        }
//
//
////        unsigned int *bindex = (block_id_t *) hash_value((void *) md5_checksum, htable);
////
////        if (bindex == NULL) {
////            //cnt block_unique_num
////            block_unique_num++;
////            bindex = (unsigned int *) malloc(BLOCK_ID_SIZE);
////            if (NULL == bindex) {
////                perror("malloc in dedup_regfile");
////                break;
////            }
////            /* insert hash entry and write unique block into bdata*/
////            *bindex = g_unique_block_nr;
////            hash_insert((void *) strdup((char *) md5_checksum), (void *) bindex, htable);
////
////            show_md5(md5_checksum);
////            g_unique_block_nr++;
////        } else {
////        }
//    }
//
////    printf("block_total_num is %llu\nblock_unique_num is %llu\ndup_rate is %lf\n\n", block_total_num, block_unique_num,
////           (double) (block_total_num - block_unique_num) / block_total_num);
//
//    return 0;
//
//}


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


void test_du() {
    char buf_ps[1024] = {0};
    FILE *ptr;
    const char *cmd = "du -ha \"/mnt/\" | awk -v FS='\\t' '{print $2}'";
    printf("%s\n", cmd);
    if ((ptr = popen(cmd, "r")) != NULL) {
        struct stat statbuf = {0};
        char file_name[MAX_PATH_LEN] = {0};
        while (fgets(buf_ps, 1024, ptr) != NULL) {
            memset(file_name, 0, sizeof(file_name));
            strcpy(file_name, buf_ps);
            file_name[strlen(file_name) - 1] = 0;
            if (-1 == stat(file_name, &statbuf)) {
                printf("fucku\n");
                continue;
            }
            if (S_IFREG & statbuf.st_mode) {
                printf("%s\n", file_name);
            }
            memset(buf_ps, 0, sizeof(buf_ps));
        }
        pclose(ptr);
    }
}


// fs dfs
void dfs_directory(const char *path, hashtable *htable, int print_sz, int print_md5) {

//    char filepath[MAX_PATH_LEN] = {0};
//    if (path[strlen(path) - 1] == '/' && strlen(path) != 1) {
//        strncpy(filepath, path, strlen(path) - 1);
//    } else {
//        strcpy(filepath, path);
//    }
//


    char buf_ps[1024] = {0};
    FILE *ptr;
    char cmd[MAX_PATH_LEN]={0};
    sprintf(cmd,"du -ha \"%s\" | awk -v FS='\\t' '{print $2}'",path);
    printf("%s\n", cmd);
    if ((ptr = popen(cmd, "r")) != NULL) {
        struct stat statbuf = {0};
        char file_name[MAX_PATH_LEN] = {0};
        while (fgets(buf_ps, 1024, ptr) != NULL) {
            memset(file_name, 0, sizeof(file_name));
            strcpy(file_name, buf_ps);
            file_name[strlen(file_name) - 1] = 0;
            if (-1 == stat(file_name, &statbuf)) {
                printf("fucku\n");
                continue;
            }
            if (S_IFREG & statbuf.st_mode) {
                printf("%s\n", file_name);
                if (print_sz) {
                    printf("%lu\n", statbuf.st_size);
                }
                if (print_md5) {
                    unsigned char md5[16];
                    //这里可能不需要完全通过计算文件md5去判断是否重复 待修改
                    if (md5_file(file_name, md5) == 0) {
                        show_md5(md5);
//                        pFileInfo p_file_info = (FileInfo *) hash_value((void *) md5, htable);
//                        if (p_file_info == NULL) {
//                            p_file_info = (pFileInfo) malloc(sizeof(FileInfo));
//                            p_file_info->file_cnt = 1;
//                            p_file_info->file_sz = statbuf.st_size;
//                            strcpy(p_file_info->file_name, file_name);
//                            hash_insert((void *) strdup((char *) md5), (void *) p_file_info, htable);
//                        } else {
//                            printf("find dup file\n");
//                            getchar();
//                            (p_file_info->file_cnt)++;
//                        }
                    } else {
                        printf("md5\n");
                    }
                }
            }
            memset(buf_ps, 0, sizeof(buf_ps));
        }
        pclose(ptr);
    }

//    struct stat statbuf = {0};
//    if (-1 == stat(filepath, &statbuf)) {
//        printf("%s\n", filepath);
//        if (print_sz) { printf("0\n"); }
//        if (print_md5) { printf("md5\n"); }
////        printf("fstat regular file\n");
//        return;
//    }
//
//    if (S_IFREG & statbuf.st_mode) {
//        //常规文件
//        printf("%s\n", filepath);
//
//        if (print_sz) {
//            printf("%lu\n", statbuf.st_size);
//        }
//        if (print_md5) {
//            unsigned char md5[16];
//            //这里可能不需要完全通过计算文件md5去判断是否重复 待修改
//            if (md5_file(filepath, md5) == 0) {
//                show_md5(md5);
//                pFileInfo p_file_info = (FileInfo *) hash_value((void *) md5, htable);
//                if (p_file_info == NULL) {
//                    p_file_info = (pFileInfo) malloc(sizeof(FileInfo));
//                    p_file_info->file_cnt = 1;
//                    p_file_info->file_sz = statbuf.st_size;
//                    strcpy(p_file_info->file_name, filepath);
//                    hash_insert((void *) strdup((char *) md5), (void *) p_file_info, htable);
//                } else {
//                    printf("find dup file\n");
//                    getchar();
//                    (p_file_info->file_cnt)++;
//                }
//
//
//            } else {
//                printf("md5\n");
//            }
//        }
//
//
//    } else if (S_IFDIR & statbuf.st_mode) {
//        //目录
        DIR *dp;
//        struct dirent *dirp;
//        if ((dp = opendir(filepath)) == NULL) {
////            printf("can't open %s\n", filepath);
//            return;
//        }
//        while ((dirp = readdir(dp)) != NULL) {
//            char file[MAX_PATH_LEN];
//            if (strcmp(filepath, "/") == 0) {
//                sprintf(file, "%s%s", filepath, dirp->d_name);
//            } else {
//                sprintf(file, "%s/%s", filepath, dirp->d_name);
//            }
//            if (strcmp(".", dirp->d_name) != 0 && strcmp("..", dirp->d_name) != 0) {
//                dfs_directory(file, htable, print_sz, print_md5);
//            }
////            dfs_directory(file);
////            printf("%s\n", dirp->d_name);
//        }
//        closedir(dp);
//    } else {
//        printf("%s\n", filepath);
//        if (print_sz) { printf("0\n"); }
//        if (print_md5) { printf("md5\n"); }
////        printf("unknown type\n");
////        getchar();
//        return;
//    }

}

//void auto_filter_dfs(FragmentType fs_type, int is_boot, const char *mount_path, hashtable *htable) {
//
//    uint32_t path_cnt = 0;
//
//    switch (fs_type) {
//        case linux_normal: {
//
//            if (is_boot) {
//                char paths[MAX_PATH_LEN][MAX_DIRC_NUM] = {{"/bin"},
//                                                          {"/lib"},
//                                                          {"/lib64"},
//                                                          {"/root"},
//                                                          {"/sbin"},
//                                                          {"/usr"},
//                                                          {"/home"}};
//                path_cnt = 7;
//                for (int i = 0; i < path_cnt; i++) {
//                    char dfs_path[MAX_PATH_LEN] = {0};
//                    sprintf(dfs_path, "%s%s", mount_path, paths[i]);
//                    printf("dfs_path: %s\n", dfs_path);
////                    dfs_directory(dfs_path, htable, 0, 0);
//                }
//            } else {
//
//            }
//
//            //先不做处理
////            dfs_directory(mount_path, htable, 0, 0);
//
//            break;
//        }
//        case ntfs: {
//
//            if (is_boot) {
//                char paths[MAX_PATH_LEN][MAX_DIRC_NUM] = {{"/Windows"}};
//                path_cnt = 1;
//                for (int i = 0; i < path_cnt; i++) {
//                    char dfs_path[MAX_PATH_LEN] = {0};
//                    sprintf(dfs_path, "%s%s", mount_path, paths[i]);
//                    printf("dfs_path: %s\n", dfs_path);
////                    dfs_directory(dfs_path, htable, 0, 0);
//                }
//
//            } else {
//
//            }
//
//            break;
//        }
//        default: {
//            break;
//        }
//    }
//}

void Usage_dfs() {
    printf("\n\n");
    printf("    /**\n"
           "     *  Usage:\n"
           "     *\n"
           "     *      -p [path]: deep first search in Path\n"
           "     *      -s: print file Size\n"
           "     *      -m: print file Md5\n"
           "     *      -a: set an auto filter\n"
           "     *      -h: help\n"
           "     *\n"
           "     * */");
    printf("\n\n");
}



void test_default_md5(){


    char cmd[MAX_PATH_LEN]="md5sum /data/images/centos_6.5_x64_min_1.raw";




}

int main(int argc, char *argv[]) {



    int opt;
    //opt format
    char *opt_format = "p:smah";
    int is_reg_dfs = 0, is_print_size = 0, is_print_md5 = 0;
    int is_auto_filter = 0;
    int is_debug = 0;

    char src_path[MAX_PATH_LEN];
//    char src_header[MAX_PATH_LEN];
//    char split_path[MAX_PATH_LEN];

    while ((opt = getopt(argc, argv, opt_format)) != -1) {
        switch (opt) {
            case 'p': {
                is_reg_dfs = 1;
                strcpy(src_path, optarg);
                break;
            }
            case 's': {
                is_print_size = 1;
                break;
            }
            case 'm': {
                is_print_md5 = 1;
                break;
            }
            case 'h': {
                //print usage
                Usage_dfs();
                break;
            }
            case 'a': {
                is_auto_filter = 1;
                break;
            }
            default:
                break;
        }

    }


    hashtable *htable = NULL;
    htable = create_hashtable(g_htab_backet_nr);

    if (is_auto_filter) {

    }


    if (is_reg_dfs) {
        dfs_directory(src_path, htable, is_print_size, is_print_md5);
    }

    hash_free(htable);

    return 0;
}
