#!/bin/sh

# env
# . /root/admin-openrc.sh

#nova_instance_inc_dir="/data/vmdks/"
nova_instance_inc_dir="/data/vms/"
nova_instance_base_dir="/opt/stack/data/nova/instances/_base/"
frag_info_path="/data/frag_info_qcow2/"
dedup_shell_file="/data/script/qcow2_dedup.sh"
echo "#!/bin/sh" > $dedup_shell_file
echo "#pre handle" >> $dedup_shell_file
# get all shutoff|suspended instances
for item in $(ls $nova_instance_inc_dir)
do
echo "dedup instance[$nova_instance_inc_dir$item]"
echo "ImgSplit2  -o -x $nova_instance_inc_dir$item -d $frag_info_path -b 4096" >> $dedup_shell_file
done
# get all unused backing files
# for base_img in $(ls "$nova_instance_base_dir")
# do
# ret=$(sudo lsof $nova_instance_base_dir$base_img)
# if [ ! -n "$ret" ]; then
#   echo "dedup backing file[$nova_instance_base_dir$base_img]"
# echo "ImgSplit2  -o -x $nova_instance_base_dir$base_img -d /data/frag_info/ -b 4096" >> /data/nova_dedup.sh
# else
#   echo "backing file in use[$nova_instance_base_dir$base_img]"
# fi
# done


echo "#dedup" >> $dedup_shell_file
echo "time python3 /data/script/ImgDedup/simhash_dedup_new.py &" >> $dedup_shell_file
# sudo /data/nova_dedup.sh &
