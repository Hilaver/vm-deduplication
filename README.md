# 虚拟机镜像去重Demo

Author：Nero

__Simdedup-对虚拟机磁盘镜像进行重复数据删除的性能优化__

Simdedup是一个基于相似性实现局部去重的重复数据删除demo

FileDedup为预处理代码，C编写，用于解析镜像文件结构

ImgDedup用于聚类去重，python编写

代码比较粗糙，仅供参考
