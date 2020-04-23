#!/bin/sh
#get pid
#python3_pid = $(ps aux|grep get_frag_simhash_new.py | grep -v grep | awk  '{print $2}')
log_file="/data/log/mem_watch_opendedup.log"
#pname="lessfs /etc/lessfs.cfg"
pname="jsvc"
#ppid=124947
#date > $log_file

while [ true ]
do
	pid=`ps aux|grep $pname|grep Sl| grep -v grep | awk  '{print $2}'`
	if [ "$pid" ];then
		#get mem resource
		while [ "$pid" ]
		do
			pidstat -p $pid -r|sed -n '4p' >> $log_file
			sleep 2s
			echo $pid
#			pid=`ps aux|grep $pname| grep -v grep | awk  '{print $2}'`
		done
	else
		sleep 1s
	fi

done
