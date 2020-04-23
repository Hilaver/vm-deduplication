#!/bin/sh
#get pid
#python3_pid = $(ps aux|grep get_frag_simhash_new.py | grep -v grep | awk  '{print $2}')
log_file="/data/log/mem_watch_simhash.log"
pname="get_frag_simhash_new.py"
#pname="systemd"

date > $log_file

while [ true ]
do
	pid=`ps aux|grep $pname| grep -v grep | awk  '{print $2}'`
	if [ "$pid" ];then
		#get mem resource
		while [ "$pid" ]
		do
			pidstat -p $pid -r|sed -n '4p' >> $log_file
			sleep 2s
			pid=`ps aux|grep $pname| grep -v grep | awk  '{print $2}'`
		done
	else
		sleep 1s
	fi

done
