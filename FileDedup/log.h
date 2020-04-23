/************************************************************************\
 *  Copyright (C), 2017-2020, Capsheaf Tech. Co., Ltd.
 *
 *  FileName: log.h
 *  Author: zhouji
 *  Version: V1.0
 *  Date: 2017/07/06
 *  Description:    日志模块，用于记录系统各种级别的日志。相关日志级别定义、
 *                  接口函数定义
 * 
 *  Function List:
 *      1.log_init(): 初始化日志模块
 *      2.log_close(): 关闭日志模块
 *      3.log_write(): 宏接口，用于提供给用户来记录日志的接口
 *      4.my_log_write(): 真正用于记录日志的接口
 *
 *  History:
 *      <author>   <time>  <version>  <desc>        
 *       zhouji   17/07/06    1.0     构建这个模块
\************************************************************************/

#ifndef _LOG_H_
#define _LOG_H_

//#include "core.h"

/* 日志级别 */
#define LOG_EMERG       0       /* 日志级别：紧急 */
#define LOG_ERR         1       /* 日志级别：错误 */
#define LOG_WARN        2       /* 日志级别：警告 */
#define LOG_INFO        3       /* 日志级别：信息 */
#define LOG_DEBUG1      4       /* 日志级别：调试级别1，少量的重要调试日志 */
#define LOG_DEBUG2      5       /* 日志级别：调试级别1，重要调试日志 */
#define LOG_DEBUG3      6       /* 日志级别：调试级别1，较详细调试日志 */
#define LOG_DEBUG4      7       /* 日志级别：调试级别1，大量的较详细调试日志 */
#define LOG_DEBUG5      8       /* 日志级别：调试级别1，大量的详细调试日志 */

#define MAX_SHELL_STR_LEN 1024
#define MAX_TEXT_LEN 1024
#define MAX_PATH_LEN 256

/*
 *  Function:   log_write()
 *  Description:记录日志接口
 *  Params:     level, unsigned short, 日志级别
 *              fmt, const char *, 格式化字符串
 *              arg, ..., 可变参数
 *  Return:     void
 */
#define log_write(level, fmt, arg...) my_log_write(\
        __FILE__, __FUNCTION__, __LINE__, level, fmt, ##arg)    

/*
 *  Function:   log_init()
 *  Description:初始化日志模块
 *  Params:     prefix, char *, 日志文件存放的路径，最后一个字符必须为"/"
 *  Return:     int, 是否成功; -1，失败; 0, 成功
 */
int log_init(char *prefix);

/*
 *  Function:   log_close()
 *  Description:关闭日志模块
 *  Params:     void
 *  Return:     void
 */
void  log_close(void);

/*
 *  Function:   log_write()
 *  Description:真正用于记录日志的接口，根据日志级别存储日志，当传入的日志级别
 *              大于当前设置的日志级别时，该日志将不会被记录。当前的日志级别由
 *              宏DEBUG定义
 *  Params:     file, const char *, 调用者所属文件的文件名
 *              function, const char *, 调用函数
 *              line, unsigned long long, 调用者在文件的行号
 *              level, unsigned short, 日志级别
 *              fmt, const char *, 格式化字符串
 *              arg, ..., 可变参数
 *  Return:     void
 */
void  my_log_write(const char *file, const char *function, 
                   unsigned long long line, unsigned short level, const char *fmt, ...);

#endif
