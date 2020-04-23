INCLUDEDIR = /usr/include/
#INCLUDEDIR = E:\cygwin64\usr\include
LIBDIR = /usr/local/lib
#LIBDIR = E:\cygwin64\lib
LIBS = -lpthread -pthread -lm -lz

all: Xor ImgSplit2 Md5

clean:
	$(RM) -f Xor
	$(RM) -f ImgSplit2
	$(RM) -f Md5

Xor: xor.c
	$(CXX) -o $@  -I$(INCLUDEDIR)  -L$(LIBS) $? -g
ImgSplit2: img_split_new.cpp log.c log.h util.cpp util.h
	$(CXX) -o $@  -I$(INCLUDEDIR)  -L$(LIBS) $? -g
Md5: md5.c md5.h md5test.cpp
	$(CXX) -o $@  -I$(INCLUDEDIR)  -L$(LIBS) $? -g
