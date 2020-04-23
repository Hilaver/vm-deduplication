# from datasketch import MinHash
from hashlib import sha1
from hashlib import sha512
from hashlib import md5
# import matplotlib.pyplot as plt
import random, copy, struct
import numpy as np
import os
import sys
import time

NUM_PERM = (1 << 8) - 1
BLOCK_SIZE = 1 << 12

IS_SAMPLING = False
SAMPLING_INTERVAL = 10

# BLOCK_FILE_PATH = "F:\\image_block_info\\"
# IMAGE_FILE_PATH = "F:\\images\\"
BLOCK_FILE_PATH = "/zcy/image_block_info/"
IMAGE_FILE_PATH = "/data/images/"

# for test zone

# exit(0)
# test end


# The size of a hash value in number of bytes
hashvalue_byte_size = len(bytes(np.int64(42).data))

# http://en.wikipedia.org/wiki/Mersenne_prime
_mersenne_prime = (1 << 61) - 1
_max_hash = (1 << 31) - 1
_hash_range = (1 << 31)


class MinHash(object):
    '''MinHash is a probabilistic data structure for computing
    `Jaccard similarity`_ between sets.

    Args:
        num_perm (int, optional): Number of random permutation functions.
            It will be ignored if `hashvalues` is not None.
        seed (int, optional): The random seed controls the set of random
            permutation functions generated for this MinHash.
        hashobj (optional): The hash function used by this MinHash.
            It must implements
            the `digest()` method similar to hashlib_ hash functions, such
            as `hashlib.sha1`.
        hashvalues (`numpy.array` or `list`, optional): The hash values is
            the internal state of the MinHash. It can be specified for faster
            initialization using the existing state from another MinHash.
        permutations (optional): The permutation function parameters. This argument
            can be specified for faster initialization using the existing
            state from another MinHash.

    Note:
        To save memory usage, consider using :class:`datasketch.LeanMinHash`.

    Note:
        Since version 1.1.1, MinHash will only support serialization using
        `pickle`_. ``serialize`` and ``deserialize`` methods are removed,
        and are supported in :class:`datasketch.LeanMinHash` instead.
        MinHash serialized before version 1.1.1 cannot be deserialized properly
        in newer versions (`need to migrate? <https://github.com/ekzhu/datasketch/issues/18>`_).

    Note:
        Since version 1.1.3, MinHash uses Numpy's random number generator
        instead of Python's built-in random package. This change makes the
        hash values consistent across different Python versions.
        The side-effect is that now MinHash created before version 1.1.3 won't
        work (i.e., ``jaccard``, ``merge`` and ``union``)
        with those created after.

    .. _`Jaccard similarity`: https://en.wikipedia.org/wiki/Jaccard_index
    .. _hashlib: https://docs.python.org/3.5/library/hashlib.html
    .. _`pickle`: https://docs.python.org/3/library/pickle.html
    '''

    def __init__(self, num_perm=128, seed=1, hashobj=sha1,
                 hashvalues=None, permutations=None):
        if hashvalues is not None:
            num_perm = len(hashvalues)
        if num_perm > _hash_range:
            # Because 1) we don't want the size to be too large, and
            # 2) we are using 4 bytes to store the size value
            raise ValueError("Cannot have more than %d number of\
                    permutation functions" % _hash_range)
        self.seed = seed
        self.hashobj = hashobj
        # Initialize hash values
        if hashvalues is not None:
            self.hashvalues = self._parse_hashvalues(hashvalues)
        else:
            self.hashvalues = self._init_hashvalues(num_perm)
        # Initalize permutation function parameters
        if permutations is not None:
            self.permutations = permutations
        else:
            generator = np.random.RandomState(self.seed)
            # Create parameters for a random bijective permutation function
            # that maps a 32-bit hash value to another 32-bit hash value.
            # http://en.wikipedia.org/wiki/Universal_hashing
            self.permutations = np.array([(generator.randint(1, _mersenne_prime, dtype=np.uint64),
                                           generator.randint(0, _mersenne_prime, dtype=np.uint64))
                                          for _ in range(num_perm)], dtype=np.uint64).T
        if len(self) != len(self.permutations[0]):
            raise ValueError("Numbers of hash values and permutations mismatch")

    def _init_hashvalues(self, num_perm):
        return np.ones(num_perm, dtype=np.uint64) * _max_hash

    def _parse_hashvalues(self, hashvalues):
        return np.array(hashvalues, dtype=np.uint64)

    def update(self, b):
        '''Update this MinHash with a new value.

        Args:
            b (bytes): The value of type `bytes`.

        Example:
            To update with a new string value:

            .. code-block:: python

                minhash.update("new value".encode('utf-8'))
        '''
        hv = struct.unpack('<I', self.hashobj(b).digest()[:4])[0]
        # hv = int(b[:8], 16)
        a, b = self.permutations
        phv = np.bitwise_and((a * hv + b) % _mersenne_prime, np.uint64(_max_hash))
        self.hashvalues = np.minimum(phv, self.hashvalues)

    def jaccard(self, other):
        '''Estimate the `Jaccard similarity`_ (resemblance) between the sets
        represented by this MinHash and the other.

        Args:
            other (datasketch.MinHash): The other MinHash.

        Returns:
            float: The Jaccard similarity, which is between 0.0 and 1.0.
        '''
        if other.seed != self.seed:
            raise ValueError("Cannot compute Jaccard given MinHash with\
                    different seeds")
        if len(self) != len(other):
            raise ValueError("Cannot compute Jaccard given MinHash with\
                    different numbers of permutation functions")
        return np.float(np.count_nonzero(self.hashvalues == other.hashvalues)) / \
               np.float(len(self))

    def count(self):
        '''Estimate the cardinality count based on the technique described in
        `this paper <http://ieeexplore.ieee.org/stamp/stamp.jsp?arnumber=365694>`_.

        Returns:
            int: The estimated cardinality of the set represented by this MinHash.
        '''
        k = len(self)
        return np.float(k) / np.sum(self.hashvalues / np.float(_max_hash)) - 1.0

    def merge(self, other):
        '''Merge the other MinHash with this one, making this one the union
        of both.

        Args:
            other (datasketch.MinHash): The other MinHash.
        '''
        if other.seed != self.seed:
            raise ValueError("Cannot merge MinHash with\
                    different seeds")
        if len(self) != len(other):
            raise ValueError("Cannot merge MinHash with\
                    different numbers of permutation functions")
        self.hashvalues = np.minimum(other.hashvalues, self.hashvalues)

    def digest(self):
        '''Export the hash values, which is the internal state of the
        MinHash.

        Returns:
            numpy.array: The hash values which is a Numpy array.
        '''
        return copy.copy(self.hashvalues)

    def is_empty(self):
        '''
        Returns:
            bool: If the current MinHash is empty - at the state of just
                initialized.
        '''
        if np.any(self.hashvalues != _max_hash):
            return False
        return True

    def clear(self):
        '''
        Clear the current state of the MinHash.
        All hash values are reset.
        '''
        self.hashvalues = self._init_hashvalues(len(self))

    def copy(self):
        '''
        :returns: datasketch.MinHash -- A copy of this MinHash by exporting its state.
        '''
        return MinHash(seed=self.seed, hashvalues=self.digest(),
                       permutations=self.permutations)

    def __len__(self):
        '''
        :returns: int -- The number of hash values.
        '''
        return len(self.hashvalues)

    def __eq__(self, other):
        '''
        :returns: bool -- If their seeds and hash values are both equal then two are equivalent.
        '''
        return self.seed == other.seed and \
               np.array_equal(self.hashvalues, other.hashvalues)

    @classmethod
    def union(cls, *mhs):
        '''Create a MinHash which is the union of the MinHash objects passed as arguments.

        Args:
            *mhs: The MinHash objects to be united. The argument list length is variable,
                but must be at least 2.

        Returns:
            datasketch.MinHash: A new union MinHash.
        '''
        if len(mhs) < 2:
            raise ValueError("Cannot union less than 2 MinHash")
        num_perm = len(mhs[0])
        seed = mhs[0].seed
        if any((seed != m.seed or num_perm != len(m)) for m in mhs):
            raise ValueError("The unioning MinHash must have the\
                    same seed and number of permutation functions")
        hashvalues = np.minimum.reduce([m.hashvalues for m in mhs])
        permutations = mhs[0].permutations
        return cls(num_perm=num_perm, seed=seed, hashvalues=hashvalues,
                   permutations=permutations)


def get_file_size(filepath):
    # filepath = np.unicode(filepath, 'utf8')
    fsize = os.path.getsize(filepath)
    return fsize


def read_file(filename):
    x = []
    with open(filename, 'r+') as f:
        for line in f:
            x.append(line.strip('\n'))
    return np.asarray(x)


def write_file(data_set, filename):
    with open(filename, 'w') as f:
        for item in data_set:
            f.write(str(item) + "\n")


def is_zero_block(buffer):
    for c in buffer:
        if c != 0x00:
            return False
    return True


def convert_bin(s):
    ret = []
    for c in s:
        ret.append(1 if c == '1' else -1)
    return ret


def to_bin(arr):
    ret = []
    for i in arr:
        ret.append(1 if i > 0 else 0)
    return ret


# print(np.array(convert_bin("100011111001110")).dot(3))
#
# exit(0)

g_is_minhash_calc = True

# file_name_arr=[]
file_name_arr = ["ubuntu_14_x64_thick_20-flat.vmdk"]
# file_name_arr = ["ubuntu_14_x64_thick_10-flat.vmdk", "ubuntu_16_x64_thick_10-flat.vmdk", "ubuntu_16_x64_thick_20-flat.vmdk"]
# file_name_arr = ["ubuntu_14_x64_thick_10-flat.vmdk", "ubuntu_16_x64_thick_10-flat.vmdk",
#                  "ubuntu_16_x64_thick_20-flat.vmdk",
#                  "windows_2008_R2_x64_thick_10-flat.vmdk", "windows_2012_R2_x64_thick_10-flat.vmdk",
#                  "windows_2012_x64_thick_10-flat.vmdk"]

# 获取所有镜像
# for file in os.listdir(IMAGE_FILE_PATH):
#     file_name_arr.append(file)

digest_set_arr = []
minhash_arr = []
block_num_arr = []
unique_block_num_arr = []

# for test
# for i in range(len(file_name_arr)):
#     minhash_arr.append(MinHash(num_perm=NUM_PERM))
# for i in range(len(file_name_arr)):
#     digest_set = read_file(BLOCK_FILE_PATH + file_name_arr[i] + ".digest")
#     g_start_time = time.clock()
#     for digest in digest_set:
#         minhash_arr[i].update(digest.encode('utf8'))
#     g_end_time = time.clock()
#     print("calc minhash time[{}]:{}".format(file_name_arr[i],g_end_time - g_start_time))
#
# exit(0)

# if minhash has been calculated
for file_name in file_name_arr:
    file_minhash = read_file(BLOCK_FILE_PATH + file_name + ".vector")
    minhash_arr.append(file_minhash)

# if minhash set len != NUM_PERM, re calc
for minhash in minhash_arr:
    if len(minhash) != NUM_PERM:
        g_is_minhash_calc = False
        break

print("BLOCK_SIZE: {}".format(BLOCK_SIZE))
print("NUM_PERM: {}".format(NUM_PERM))
print("SAMPLING_INTERVAL: {}".format(SAMPLING_INTERVAL) if IS_SAMPLING else "NO SAMPLING")

if g_is_minhash_calc == True:
    for i in range(len(minhash_arr)):
        minhash_arr[i] = MinHash(num_perm=NUM_PERM, hashvalues=minhash_arr[i])


else:
    digest_set_arr.clear()
    minhash_arr.clear()
    g_start_time = time.clock()
    # for each file
    for file_name in file_name_arr:
        # full path of file
        full_file_path = IMAGE_FILE_PATH + file_name
        # start to calc block digest with fixed size
        start_time = time.clock()
        block_digest, file_ptr = "", np.int64(0)
        minhash = MinHash(num_perm=NUM_PERM)
        file_size = get_file_size(full_file_path)
        digest_set = set()
        digest_dict = dict()
        has_zero_block = False
        # 如果抽样
        block_cnt = 0
        unique_block_cnt = 0
        # calc digest with fixed size
        with open(full_file_path.encode('utf8'), 'rb') as f:
            while file_ptr < file_size:
                if file_size - file_ptr < BLOCK_SIZE:
                    break
                f.seek(file_ptr)
                block_cnt += 1
                # block_digest = md5(f.read(BLOCK_SIZE)).hexdigest()
                buf = f.read(BLOCK_SIZE)
                is_zero_block(buf)
                # if is_zero_block(buf) != True:
                #     block_digest = sha512(buf).hexdigest()
                #     if block_digest not in digest_dict:
                #         digest_dict[block_digest] = 1
                #     else:
                #         digest_dict[block_digest] += 1
                # else:
                #     if has_zero_block == False:
                #         block_digest = sha512(buf).hexdigest()
                #         digest_dict[block_digest] = 1
                #         has_zero_block = True
                #     else:
                #         pass

                # print((str(bin(int(block_digest,16))))[2:])
                # print(block_digest)
                # block_digest = sha1(f.read(BLOCK_SIZE)).hexdigest()
                # if block_digest not in digest_set:
                #     digest_set.add(block_digest)
                #     # 如果抽样
                #     if IS_SAMPLING:
                #         if unique_block_cnt % SAMPLING_INTERVAL == 0:
                #             minhash.update(block_digest.encode('utf8'))
                #     # 不抽样
                #     else:
                #         minhash.update(block_digest.encode('utf8'))
                #     unique_block_cnt += 1
                #     # minhash.update(block_digest)
                # else:
                #     pass
                file_ptr += BLOCK_SIZE
        # save block num info
        exit(-1)
        ret = np.array([0] * 512)
        for (k, v) in digest_dict.items():
            ret += (np.array(convert_bin(k[2:])).dot(v))
        print(to_bin(ret))
        exit(-1)
        block_num_arr.append(block_cnt)
        unique_block_num_arr.append(unique_block_cnt)
        # calc digest end
        end_time = time.clock()
        print(file_name, "calc digest and minhash time:", end_time - start_time)
        # save info
        digest_set_arr.append(digest_set)
        minhash_arr.append(minhash)

    g_end_time = time.clock()
    print("Time of part-1[calc digest and minhash]:", g_end_time - g_start_time)
    # exit(0)
    # save info to file
    g_start_time = time.clock()
    for file_cnt in range(len(file_name_arr)):
        write_file(digest_set_arr[file_cnt], BLOCK_FILE_PATH + file_name_arr[file_cnt] + ".digest")
        write_file(minhash_arr[file_cnt].hashvalues, BLOCK_FILE_PATH + file_name_arr[file_cnt] + ".vector")
    g_end_time = time.clock()
    print("save digest and minhash time:", g_end_time - g_start_time)

# calc Actual Jaccard
digest_set_arr.clear()
# minhash_arr.clear()
# g_start_time = time.clock()
for file_name in file_name_arr:
    g_start_time = time.clock()
    digest_set = set(read_file(BLOCK_FILE_PATH + file_name + ".digest"))
    digest_set_arr.append(digest_set)
    g_end_time = time.clock()
    print("read digest of file[{}]:{}".format(file_name, g_end_time - g_start_time))
for i in range(len(file_name_arr)):
    for j in range(i):
        g_start_time = time.clock()
        actual_jaccard = float(
            len(digest_set_arr[i].intersection(digest_set_arr[j]))) / float(
            len(digest_set_arr[i].union(digest_set_arr[j])))
        print("Actual Jaccard for [" + file_name_arr[i] + "," + file_name_arr[j] + "]:", actual_jaccard)
        g_end_time = time.clock()
        print("Actual Jaccard time:", g_end_time - g_start_time)

# calc Estimated Jaccard
g_start_time = time.clock()
for i in range(len(file_name_arr)):
    for j in range(i):
        print("Estimated Jaccard for [" + file_name_arr[i] + "," + file_name_arr[j] + "]:",
              minhash_arr[i].jaccard(minhash_arr[j]))
g_end_time = time.clock()
print("Estimated Jaccard time:", g_end_time - g_start_time)

# block dedup info
if len(block_num_arr) != 0:
    for i in range(len(file_name_arr)):
        print(
            "[{}]:[block num is {}, unique block num is {}, dup_rate is {}]".format(file_name_arr[i], block_num_arr[i],
                                                                                    unique_block_num_arr[i], float(
                    block_num_arr[i] - unique_block_num_arr[i]) / float(block_num_arr[i])))

# exit(0)
