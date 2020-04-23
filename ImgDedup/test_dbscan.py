import numpy as np
# import matplotlib.pyplot as plt
from sklearn import datasets

# X1, y1 = datasets.make_circles(n_samples=500, factor=.6,
#                                noise=.04)
# X2, y2 = datasets.make_blobs(n_samples=100, n_features=2, centers=[[1.2, 1.2]], cluster_std=[[.1]],
#                              random_state=9)
#
# X = np.concatenate((X1, X2))
#
# plt.scatter(X[:, 0], X[:, 1], marker='o')
# plt.show()


# from sklearn.cluster import KMeans
#
# y_pred = KMeans(n_clusters=3, random_state=9).fit_predict(X)
# plt.scatter(X[:, 0], X[:, 1], c=y_pred)
# plt.show()

from sklearn.cluster import DBSCAN


def calc_Hamming_dist(s1_bin, s2_bin):
    ret = 0
    if len(s1_bin) != len(s2_bin):
        return -1
    for i in range(len(s1_bin)):
        ret += (1 if s1_bin[i] != s2_bin[i] else 0)
    return ret


def convert_bin(s):
    ret = []
    for c in s:
        ret.append(1 if c == '1' else -1)
    return ret


def read_file(filename):
    x = []
    with open(filename, 'r+') as f:
        for line in f:
            x.append(line.strip('\n'))
    return np.asarray(x)


# X = read_file("F:\\image_block_info\\tmp\\simhash_data.txt")
X = read_file("/zcy/simhash_data.txt")

disX = [[0 for i in range(len(X))] for j in range(len(X))]
for i in range(len(X)):
    for j in range(len(X)):
        str1 = convert_bin(format(int(X[i], 16), '#0130b')[2:])
        str2 = convert_bin(format(int(X[j], 16), '#0130b')[2:])
        disX[i][j] = calc_Hamming_dist(str1, str2)

# print((disX))
from sklearn.metrics.pairwise import pairwise_distances

y_pred = DBSCAN(eps=20, min_samples=5, metric="precomputed").fit_predict(disX)

print(y_pred)
# y_pred = DBSCAN(eps=0.1, min_samples=10).fit_predict(X)
# plt.scatter(X[:, 0], X[:, 1], c=y_pred)
# plt.show()


