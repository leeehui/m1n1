#!/bin/bash
export M1N1DEVICE=/dev/cu.debug-console
passwd=tgb*963.1
root_dir=/Users/abc/Projects/AsahiLinux
m1n1_dir=$root_dir/m1n1
macvdmtool_dir=$root_dir/macvdmtool

handle_file() 
{
	file=$1
	gzip < $file > ${file}.gz
	cd $macvdmtool_dir
	echo $passwd | sudo -S ./macvdmtool reboot serial
	cd -
	sleep 8
	echo "running payload"
	python3.9 ${m1n1_dir}/proxyclient/sherpa.py ${file}.gz
	rm -rf ${file}.gz
}
handle_path() 
{
	# you may need to change the following two configs
	test_dir=$1
	cmds=$2
	test_output_dir=$test_dir/output
	
	cd $test_dir

	# rm the output dir before stating sub-dirs
	# make sure dir is clear with only test pay-loads
	rm -rf $test_output_dir
	rm -rf $test_dir/*.gz
	rm -rf $test_dir/.*
	
	# find all sub dirs
	# file_dirs=`find $test_dir -type f | xargs dirname | uniq`
	file_dirs=`ls -R ./* | grep  ":" | awk -F ":" '{print $1}'`
	
	# mk output dir in case file_dirs is null which will cause error when redirecting log file
	echo "making dir: $test_output_dir"
	mkdir -p $test_output_dir
	
	for dir in $file_dirs
	do
		echo "making dir: $test_output_dir/$dir"
		mkdir -p $test_output_dir/$dir
		rm -rf $test_dir/$dir/*.gz
		rm -rf $test_dir/$dir/.*
	done
	
	# we are in $test_dir now
	file_names=`find ./ -type f`
	for file in $file_names
	do
		echo $file
		file_dir=`echo $file | xargs dirname`
		echo $file_dir
		file_name=`echo $file | xargs basename`
		echo $file_name
		
		gzip < $file > ${file}.gz
		cd $macvdmtool_dir
		echo $passwd | sudo -S ./macvdmtool reboot serial
		cd -
		sleep 15
		echo "running payload"
		#python3.9 ${m1n1_dir}/proxyclient/sherpa.py ${file}.gz -c $cmds | tee $test_output_dir/${file}.log
		python3.9 ${m1n1_dir}/proxyclient/sherpa.py ${file}.gz -c $cmds > $test_output_dir/${file}.log
		rm -rf ${file}.gz
	done
	echo "reporting..."
	python3.9  ${m1n1_dir}/proxyclient/report.py $test_output_dir 
}

help()
{
	echo "./run.sh <your test bin file/root dir> [corresponding sherpa cmd if you input a root dir]"
}

if [ 0 -eq $# ]; then
	help
	exit
fi

if [ -d $1 ]; then
	test_dir=$1	
	if [ 1 -eq $# ]; then
		echo "please input cmds file that sherpa will automatically run"
		exit
	else
		handle_path $1 $2
	fi

elif [ -f $1 ]; then
	handle_file $1
else
	echo "please input a file/dir path"
	exit
fi

