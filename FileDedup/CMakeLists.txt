cmake_minimum_required(VERSION 3.12)
project(FileDedup)

set(CMAKE_CXX_STANDARD 11)

set(INC_DIR E:\\cygwin64\\usr\\include)
#set(LINK_DIR /cygdrive/F/410project/VMware/VMware-vix-disklib-6.0.0-2498720.x86_64/lib64)

include_directories(${INC_DIR})
#link_directories(${LINK_DIR})
#link_libraries(libvixDiskLib)


#add_executable(FileDedup dedup.h dedup.c undedup.c hash.h hash.c hashtable.h hashtable.c libz.h libz.c test.c md5.h md5.c xor.c partitions.c blkid.h img_split.cpp)
#add_executable(ImgSplit img_split.cpp img_split.h log.c util.h util.cpp)
add_executable(ImgSplit2 img_split_new.cpp img_split_new.h log.c util.h util.cpp)
#add_executable(Md5 md5.c md5.h md5test.cpp)
#add_executable(Test md5.c md5.h hash.h hash.c hashtable.h hashtable.c libz.h test.c)
#add_executable(Dfs md5.c md5.h hash.h hash.c hashtable.h hashtable.c libz.h dfs.cpp dfs.h)
