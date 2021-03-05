#!/bin/bash

passwd=tgb*963.1
m1n1_dir=/Users/abc/Projects/AsahiLinux/m1n1-upstream/m1n1
macvdmtool_dir=/Users/abc/Projects/AsahiLinux/macvdmtool
cmds=/Users/abc/Projects/AsahiLinux/m1n1/test
test_dir=/Users/abc/Projects/AsahiLinux/m1n1-ftp/auto

# find sub-dirs
file_dirs=`ls ${test_dir}/* | grep  ":" | awk -F ":" '{print $1}'`
for dir in $file_dirs
do
	echo $dir
	# find pure name without .bin suffix 
	file_names=`ls ${dir}/* | awk -F "/" -F ":" '{print $NF}' | awk -F "." '{print $1}'`
	for name in $file_names
	do
		echo ${name}
		gzip < ${name}.bin > ${name}.gz
		cd $macvdmtool_dir
		echo $passwd | sudo -S ./macvdmtool reboot serial
		cd -
		sleep 4
		python3.9 ${m1n1_dir}/proxyclient/chainload.py ../../m1n1-ftp/m1n1.macho
		python3.9 ${m1n1_dir}/proxyclient/sherpa.py ${name}.gz -c $cmds
		rm ${name}.gz
	done
done


#for a in {1..5}
#do
#	cd $macvdmtool_dir
#	echo $passwd | sudo -S ./macvdmtool reboot serial
#	cd -
#	sleep 4
#	python3.9 proxyclient/chainload.py ../../m1n1-ftp/m1n1.macho
#	python3.9 proxyclient/sherpa.py ../../m1n1-ftp/sherpa.gz -c $cmds
#done

#cd $macvdmtool_dir
#echo $passwd | sudo -S ./macvdmtool reboot serial
#cd -
#sleep 4
#python3.9 proxyclient/chainload.py ../../m1n1-ftp/m1n1.macho
#python3.9 proxyclient/sherpa.py ../../m1n1-ftp/sherpa_rolling5.gz

