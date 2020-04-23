import sys
str1 = sys.argv[1]
str2 = sys.argv[2]

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



str1 = convert_bin(format(int(str1, 16), '#0130b')[2:])
str2 = convert_bin(format(int(str2, 16), '#0130b')[2:])

print(calc_Hamming_dist(str1, str2))

exit(0)