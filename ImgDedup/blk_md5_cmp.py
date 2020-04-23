from hashlib import md5
from collections import Counter
import sys

if len(sys.argv) < 3:
    exit(-1)

BLOCK_SIZE = 4096

md5_arr = []

with open(sys.argv[1], 'rb') as fd_1:
    file_blk_cnt = 0
    # print(md5(f.read()).hexdigest())
    with open(sys.argv[2], "rb") as fd_2:

        while True:
            # fd_1.seek(file_blk_cnt * BLOCK_SIZE)
            # fd_2.seek(file_blk_cnt * BLOCK_SIZE)
            buf_1 = fd_1.read(BLOCK_SIZE)
            buf_2 = fd_2.read(BLOCK_SIZE)
            if len(buf_1) != BLOCK_SIZE or len(buf_2) != BLOCK_SIZE:
                last_blk_sz = min(int(len(buf_1)), int(len(buf_2)))
                print("last block size is {}".format(last_blk_sz))
                # last_blk_buf = buf
                blk_md5_1 = md5(buf_1).hexdigest()
                blk_md5_2 = md5(buf_2).hexdigest()
                # md5_arr.append(blk_md5)
                print(last_blk_sz, blk_md5_1)
                print(last_blk_sz, blk_md5_2)
                break
            blk_md5_1 = md5(buf_1).hexdigest()
            blk_md5_2 = md5(buf_2).hexdigest()
            # md5_arr.append(blk_md5)
            if blk_md5_2 == blk_md5_1:
                pass
            else:
                print("block num {}, md5_1[{}] md5_2[{}]".format(file_blk_cnt, blk_md5_1, blk_md5_2))
            file_blk_cnt += 1
            # print(BLOCK_SIZE, blk_md5)
