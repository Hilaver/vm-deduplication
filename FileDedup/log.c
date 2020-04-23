/************************************************************************\
 *  Copyright (C), 2017-2020, Capsheaf Tech. Co., Ltd.
 *
 *  FileName: log.c
 *  Author: zhouji
 *  Version: V1.0
 *  Date: 2017/07/06
 *  Description:    日志模块的实现
 * 
 *  Function List:
 *      1.log_init(): 初始化日志模块
 *      2.log_close(): 关闭日志模块
 *      3.log_archive(): 日志归档，当单个日志文件长度超过LOG_SIZE_LIMIT时，
 *              先将当前日志文件更名为"原文件名.bak"，然后将创建新的同名日
 *              志文件用于记录后续日志
 *      4.my_log_write(): 真正用于记录日志的接口
 *
 *  History:
 *      <author>   <time>  <version>  <desc>        
 *       zhouji   17/07/06    1.0     构建这个模块
\************************************************************************/
#include <sys/stat.h>
#include <unistd.h>
#include <stdarg.h>
#include <pthread.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include "log.h"

#define LOG_FILE_PATH       "log/"                  /* 日志文件上级目录名 */
#define LOG_FILE_NAME       "dedup.log"    /* 日志文件名 */

#define LOG_SIZE_LIMIT      1024*1024*200           /* 日志文件最大大小，单位MB */
#define DEBUG               LOG_DEBUG5              /* 默认日志级别 */

/* 日志级别描述字符串，与log.h中的日志级别宏对应 */
static const char *log_level_str[] = {
    "EMERG",
    "ERROR",
    "WARN",
    "INFO",
    "DEBUG1",
    "DEBUG2",
    "DEBUG3",
    "DEBUG4",
    "DEBUG5"
};


static FILE *s_log_fp;          /* 日志文件文件描述符 */
static pthread_mutex_t s_log_mutex;        /* 日志文件写互斥锁 */
static char *s_log_full_path;   /* 日志文件全路径 */

/* 动态日志输出级别，可更改该值来调整日志输出的详细级别 */
static unsigned short            s_log_level;


int log_init(char *prefix)
{
    unsigned long long nlen, plen;

    pthread_mutex_init(&s_log_mutex, NULL);

    if (prefix) {
        plen = strlen(prefix);
    } else {
#ifdef LOG_PREFIX
        prefix = LOG_PREFIX;
        plen = strlen(prefix);
#else
        plen = 0;
#endif
    }

    char logFileName[255]={0};
    //add time to prefix
//    time_t t=time(NULL);
//    char dateBuf[255]={0};
//    strftime(dateBuf, 255, "%Y-%m-%d_", localtime(&t));
//    if (strlen(dateBuf)!=0){
//        strcpy(logFileName,dateBuf);
//    }
    //end
    strcat(logFileName,LOG_FILE_NAME);
    plen += strlen(LOG_FILE_PATH);
    nlen = strlen(logFileName);
    s_log_full_path = (char *)malloc(plen + nlen + 1);
    if (s_log_full_path == NULL) {
        perror("[ERROR] could not malloc file path");
        return -1;
    }

    if (plen) strcpy(s_log_full_path, prefix);

    strcat(s_log_full_path, LOG_FILE_PATH);

    if (access(s_log_full_path, F_OK) == -1) {
        if (mkdir(s_log_full_path, S_IRWXU | S_IRWXG | S_IXOTH) == -1) {
            perror("[ERROR] could not create log path");
            return -1;
        }
    }

    strcat(s_log_full_path, logFileName);

    s_log_fp = NULL;
    if ((s_log_fp = fopen(s_log_full_path, "a")) == NULL) {
        perror("[ERROR] could not open log file");
        return -1;
    }

    setvbuf(s_log_fp, NULL, _IOLBF, 0);

#if defined(DEBUG)
    s_log_level = DEBUG;
#else
    s_log_level = LOG_INFO;
#endif

    return 0;
}

void log_close(void)
{
    if (s_log_fp)
        fclose(s_log_fp);

    s_log_fp = NULL;
}

static int log_archive(void)
{
    char    shell_str[MAX_SHELL_STR_LEN];
    char    backup_name[MAX_PATH_LEN];
    int   ret;

    log_close();

    snprintf(backup_name, MAX_PATH_LEN, "%s.bak", s_log_full_path);
    if (access(backup_name, F_OK) == 0) {
        snprintf(shell_str, MAX_SHELL_STR_LEN, "/bin/rm -rf %s", backup_name);
        ret = system(shell_str);
        if (ret != 0) {
            perror("[ERROR] could not rm log backup file");
            return -1;
        }
    }

    snprintf(shell_str, MAX_SHELL_STR_LEN, "/bin/mv %s %s", s_log_full_path, backup_name);
    ret = system(shell_str);
    if (ret != 0) {
        perror("[ERROR] could not mv log file");
        return -1;
    }

    if ((s_log_fp = fopen(s_log_full_path, "a")) == NULL) {
        perror("[ERROR] could not open log file");
        return -1;
    }

    setvbuf(s_log_fp, NULL, _IOLBF, 0);

    return 0;
}

void my_log_write(const char *file, const char *function,
                  unsigned long long line, unsigned short level, const char *fmt, ...)
{
    va_list ap;
    char msg[MAX_TEXT_LEN];
    char log_msg[MAX_TEXT_LEN];
    char *st;
    time_t t;
    struct stat s;

    if (level > s_log_level || s_log_fp == NULL)
        return ;

    va_start(ap, fmt);
    vsnprintf(msg, MAX_TEXT_LEN, fmt, ap);
    va_end(ap);

    pthread_mutex_lock(&s_log_mutex);

    if (time(&t) == (time_t)-1) {
        perror("[ERROR] could not get time");
        return ;
    }

    /* 当当前日志文件总大小大于LOG_SIZE_LIMIT时，将对日志文件进行归档 */
    memset(&s, 0, sizeof(s));
    stat(s_log_full_path, &s);
    if (s.st_size > LOG_SIZE_LIMIT) {
        if (log_archive() != 0)
            goto unlock;
    }

    st = ctime(&t);
    st[strlen(st) - 1] = 0;
    snprintf(log_msg, MAX_TEXT_LEN, "%s [%s] [%s %s() %llu] [PID: %llu] \t%s",
            st, log_level_str[level], file, function, line, pthread_self(), msg);

//    printf("%s\n", log_msg);
    fprintf(s_log_fp, "%s\n", log_msg);

unlock:
    pthread_mutex_unlock(&s_log_mutex);
}

