import numpy as np
from matplotlib import ticker
from matplotlib.ticker import MultipleLocator
from sklearn import datasets
from datetime import datetime
import random
import matplotlib.pyplot as plt


def qcow2_mem_usage():
    print("QCOW2: memory usage")
    # deduputil
    cnt = 0
    deduputil_max = 0
    deduputil_avg = 0
    ax = plt.subplot2grid((1, 1), (0, 0))
    ax.spines['right'].set_visible(False)
    ax.spines['top'].set_visible(False)
    with open("qcow2_deduputil.log", "r") as f:
        y_arr_deduputil = []
        for line in f:
            line = line.rstrip('\n')
            words = line.split(" ")
            tmp = int(words[7]) / 1024
            y_arr_deduputil.append(tmp)
            y_arr_deduputil.append(tmp)
            deduputil_max = max(tmp, deduputil_max)
            deduputil_avg += tmp
            deduputil_avg += tmp
            cnt += 2
    deduputil_avg /= cnt
    x_arr_deduputil = range(0, cnt)
    tmp_pos = 0.0
    x_arr_tmp = []
    for i in range(0, cnt):
        x_arr_tmp.append(tmp_pos)
        tmp_pos += 0.0000625
    ax.plot(x_arr_tmp, y_arr_deduputil, label='deduputil')
    # plt.plot(x_arr_deduputil, y_arr_deduputil, label='deduputil')
    print("deduputil", cnt)
    print("deduputil_max", deduputil_max)
    print("deduputil_avg", deduputil_avg)

    # simdedup
    cnt = 0
    y_arr_simdedup = []
    simdedup_max = 0
    simdedup_avg = 0
    with open("qcow2_simdedup_prehandle.log", "r") as f:
        for line in f:
            line = line.rstrip('\n')
            words = line.split(" ")
            tmp = int(words[7]) / 1024
            y_arr_simdedup.append(tmp)
            simdedup_max = max(tmp, simdedup_max)
            simdedup_avg += tmp
            cnt += 1
    with open("qcow2_simdedup_dedup.log", "r") as f:
        for line in f:
            line = line.rstrip('\n')
            words = line.split(" ")
            tmp = int(words[7]) / 1024
            y_arr_simdedup.append(tmp)
            simdedup_max = max(tmp, simdedup_max)
            simdedup_avg += tmp
            cnt += 1
    simdedup_avg /= cnt
    x_arr_simdedup = range(0, cnt)
    tmp_pos = 0.0
    x_arr_tmp = []
    for i in range(0, cnt):
        x_arr_tmp.append(tmp_pos)
        tmp_pos += 0.0000625
    ax.plot(x_arr_tmp, y_arr_simdedup, label='simdedup')
    # plt.plot(x_arr_simdedup, y_arr_simdedup, label='simdedup')
    print("simdedup", cnt)
    print("simdedup_max", simdedup_max)
    print("simdedup_avg", simdedup_avg)
    # opendedup
    cnt = 0
    opendedup_max = 0
    opendedup_avg = 0
    with open("qcow2_opendedup.log", "r") as f:
        y_arr_opendedup = []
        for line in f:
            line = line.rstrip('\n')
            words = line.split(" ")
            # print(words)
            tmp = int(words[7]) / 1024
            y_arr_opendedup.append(tmp)
            y_arr_opendedup.append(tmp)
            y_arr_opendedup.append(tmp)
            opendedup_max = max(tmp, simdedup_max)
            opendedup_avg += tmp
            opendedup_avg += tmp
            opendedup_avg += tmp
            cnt += 3
        x_arr_opendedup = range(0, cnt)
    opendedup_avg /= cnt
    x_arr_tmp = []
    tmp_pos = 0.0
    x_arr_tmp = []
    for i in range(0, cnt):
        x_arr_tmp.append(tmp_pos)
        tmp_pos += 0.0000625
    ax.plot(x_arr_tmp, y_arr_opendedup, label='opendedup')
    # plt.plot(x_arr_opendedup, y_arr_opendedup, label='opendedup')
    print("opendedup", cnt)
    print("opendedup_max", opendedup_max)
    print("opendedup_avg", opendedup_avg)
    # lessfs
    # cnt = 0
    # with open("qcow2_lessfs.log", "r") as f:
    #     y_arr_lessfs = []
    #     for line in f:
    #         line = line.rstrip('\n')
    #         words = line.split(" ")
    #         # print(words)
    #         y_arr_lessfs.append(int(words[7]))
    #         cnt += 1
    #     x_arr_lessfs = range(0, cnt)
    # plt.plot(x_arr_lessfs, y_arr_lessfs, label='opendedup')
    # ax = plt.subplots()
    for i in range(0, 6000, 1000):
        ax.axhline(i, color='#8B8B7A', linewidth=1, linestyle="--")
    plt.ylim(0, 5500)
    plt.xlabel('deduplication progress rate')
    plt.ylabel('memory(MB)')
    plt.legend(loc='center right')
    plt.show()


def vmdk_mem_usage():
    print("VMDK: memory usage")
    # deduputil
    cnt = 0
    deduputil_max = 0
    deduputil_avg = 0
    ax = plt.subplot2grid((1, 1), (0, 0))
    ax.spines['right'].set_visible(False)
    ax.spines['top'].set_visible(False)

    with open("vmdk_deduputil.log", "r") as f:
        y_arr_deduputil = []
        for line in f:
            line = line.rstrip('\n')
            words = line.split(" ")
            tmp = int(words[7]) / 1024
            y_arr_deduputil.append(tmp)
            y_arr_deduputil.append(tmp)
            deduputil_max = max(deduputil_max, tmp)
            deduputil_avg += tmp
            deduputil_avg += tmp
            cnt += 2
    deduputil_avg /= cnt
    x_arr_deduputil = range(0, cnt)
    # plt.plot(x_arr_deduputil, y_arr_deduputil, label='deduputil')
    tmp_pos = 0.0
    x_arr_tmp = []
    for i in range(0, cnt):
        x_arr_tmp.append(tmp_pos)
        tmp_pos += 0.00023
    ax.plot(x_arr_tmp, y_arr_deduputil, label='deduputil')

    print("deduputil", cnt)
    print("deduputil_max", deduputil_max)
    print("deduputil_avg", deduputil_avg)

    # simdedup
    cnt = 0
    y_arr_simdedup = []
    simdedup_max = 0
    simdedup_avg = 0
    with open("vmdk_simdedup_prehandle.log", "r") as f:
        for line in f:
            line = line.rstrip('\n')
            words = line.split(" ")
            tmp = int(words[7]) / 1024
            y_arr_simdedup.append(tmp)
            y_arr_simdedup.append(tmp)
            simdedup_max = max(simdedup_max, tmp)
            simdedup_avg += tmp
            simdedup_avg += tmp
            cnt += 2
    with open("vmdk_simdedup_dedup.log", "r") as f:
        for line in f:
            line = line.rstrip('\n')
            words = line.split(" ")
            tmp = int(words[7]) / 1024
            y_arr_simdedup.append(tmp)
            y_arr_simdedup.append(tmp)
            simdedup_max = max(simdedup_max, tmp)
            simdedup_avg += tmp
            simdedup_avg += tmp
            cnt += 2
    x_arr_simdedup = range(0, cnt)
    simdedup_avg /= cnt
    # plt.plot(x_arr_simdedup, y_arr_simdedup, label='simdedup')
    tmp_pos = 0.0
    x_arr_tmp = []
    for i in range(0, cnt):
        x_arr_tmp.append(tmp_pos)
        tmp_pos += 0.00023
    ax.plot(x_arr_tmp, y_arr_simdedup, label='simdedup')
    print("simdedup", cnt)
    print("simdedup_max", simdedup_max)
    print("simdedup_avg", simdedup_avg)

    # opendedup
    cnt = 0
    opendedup_max = 0
    opendedup_avg = 0
    with open("vmdk_opendedup.log", "r") as f:
        y_arr_opendedup = []
        for line in f:
            line = line.rstrip('\n')
            words = line.split(" ")
            # print(words)
            tmp = int(words[7]) / 1024
            y_arr_opendedup.append(tmp)
            opendedup_max = max(tmp, opendedup_max)
            opendedup_avg += tmp
            cnt += 1
    opendedup_avg /= cnt
    x_arr_opendedup = range(0, cnt)
    # plt.plot(x_arr_opendedup, y_arr_opendedup, label='opendedup')
    tmp_pos = 0.0
    x_arr_tmp = []
    for i in range(0, cnt):
        x_arr_tmp.append(tmp_pos)
        tmp_pos += 0.00023
    ax.plot(x_arr_tmp, y_arr_opendedup, label='opendedup')

    print("opendedup", cnt)
    print("opendedup_max", opendedup_max)
    print("opendedup_avg", opendedup_avg)
    # lessfs
    # cnt = 0
    # with open("qcow2_lessfs.log", "r") as f:
    #     y_arr_lessfs = []
    #     for line in f:
    #         line = line.rstrip('\n')
    #         words = line.split(" ")
    #         # print(words)
    #         y_arr_lessfs.append(int(words[7]))
    #         cnt += 1
    #     x_arr_lessfs = range(0, cnt)
    # plt.plot(x_arr_lessfs, y_arr_lessfs, label='opendedup')
    for i in range(0, 4500, 500):
        ax.axhline(i, color='#8B8B7A', linewidth=1, linestyle="--")
    plt.ylim(0, 4200)
    plt.xlabel('deduplication progress rate')
    plt.ylabel('memory(MB)')
    plt.legend()
    plt.show()


def avg_max_mem_usage():
    print("QCOW2 && VMDK: max and avg memory")
    name_list = ['qcow2 images', 'vmdk images']
    num_list_simdedup_avg = [282.38818491831074, 96.13047239219114]
    num_list_simdedup_max = [846.62109375, 421.73828125]
    num_list_deduputil_avg = [3994.259720281189, 2689.6942346003957]
    num_list_deduputil_max = [4923.69140625, 3778.40234375]
    num_list_opendedup_avg = [4389.5308780101905, 3564.892591294176]
    num_list_opendedup_max = [4900.70703125, 4038.15234375]
    x = list(range(len(num_list_simdedup_avg)))
    total_width, n = 0.8, 6
    width = total_width / n

    plt.bar(x, num_list_simdedup_avg, width=width, label='simdedup avg', fc='#CD661D')
    for i in range(len(x)):
        x[i] = x[i] + width
    plt.bar(x, num_list_simdedup_max, width=width, label='simdedup max', fc='#FFA500')
    for i in range(len(x)):
        x[i] = x[i] + width
    plt.bar(x, num_list_deduputil_avg, width=width, label='deduputil avg', tick_label=name_list, fc='#00008B')
    for i in range(len(x)):
        x[i] = x[i] + width
    plt.bar(x, num_list_deduputil_max, width=width, label='deduputil max', tick_label=name_list, fc='#104E8B')
    for i in range(len(x)):
        x[i] = x[i] + width
    plt.bar(x, num_list_opendedup_avg, width=width, label='opendedup avg', fc='#698B22')
    for i in range(len(x)):
        x[i] = x[i] + width
    plt.bar(x, num_list_opendedup_max, width=width, label='opendedup max', fc='#008B00')
    plt.xlabel('samples')
    plt.ylabel('memory usage(MB)')
    plt.ylim(0, 6000)
    # plt.legend()
    plt.legend(loc='upper center', ncol=3, fancybox=True, shadow=True)
    plt.show()


def time_usage():
    print("QCOW2 && VMDK: dedup time")
    name_list = ['qcow2 images', 'vmdk images']
    num_list_simdedup_avg = [417, 174]
    num_list_deduputil_avg = [754, 207]
    num_list_opendedup_avg = [431, 317]

    up_height = 20
    x_resz = 0.03

    plt.text(0 - x_resz, 417 + up_height, "417")
    plt.text(0.1966666666 - x_resz, 754 + up_height, "754")
    plt.text(0.3933333333 - x_resz, 431 + up_height, "431")
    plt.text(0.7 - x_resz, 174 + up_height, "174")
    plt.text(0.8966666 - x_resz, 207 + up_height, "207")
    plt.text(1.09333333 - x_resz, 317 + up_height, "317")

    x = [0, 0.7]
    # x = list(range(len(num_list_simdedup_avg)))
    total_width, n = 0.5, 3
    width = total_width / n
    print(x)
    plt.bar(x, num_list_simdedup_avg, width=width, label='simdedup')
    for i in range(len(x)):
        x[i] = x[i] + width + 0.03
    print(x)
    plt.bar(x, num_list_deduputil_avg, width=width, label='deduputil', tick_label=name_list)
    for i in range(len(x)):
        x[i] = x[i] + width + 0.03
    print(x)
    plt.bar(x, num_list_opendedup_avg, width=width, label='opendedup')

    plt.xlabel('samples')
    plt.ylabel('time usage(min)')
    plt.ylim(0, 850)
    plt.legend()
    # plt.legend(loc='upper center', ncol=3, fancybox=True, shadow=True)
    plt.show()


def data_increase():
    x_arr = []
    y_arr = []
    for i in range(2010, 2026):
        x_arr.append(i)
        y_arr.append((1.3 ** (i - 2010)) * 175 / (1.3 ** 15))
    print(x_arr)
    print(y_arr)
    plt.plot(x_arr, y_arr)
    # plt.xlabel('dedup_process')
    plt.ylabel('data(ZB)')
    plt.legend()
    plt.show()


# avg_max_mem_usage()
qcow2_mem_usage()
vmdk_mem_usage()
# time_usage()

# data_increase()
