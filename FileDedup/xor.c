//
// Created by 56556 on 2018/11/12.
//

#include <stdio.h>
#define MAX_PATH_LEN	255


int main(int argc, char *argv[]){

    char str1[MAX_PATH_LEN] = {0};
    char str2[MAX_PATH_LEN] = {0};

    sprintf(str1, "%s", argv[1]);
    sprintf(str2, "%s", argv[2]);

    char ret[MAX_PATH_LEN]={0};
    int diff_cnt=0;

    for (int i = 0; i < 128; ++i) {
        if (str1[i]!=str2[i]){
            diff_cnt++;
            ret[i]='1';
        }else{
            ret[i]='0';
        }
    }

    printf("xor return: %s\n",ret);
    printf("diff_cnt: %d\n",diff_cnt);


    return 0;
}