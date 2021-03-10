#!/bin/bash
export M1N1DEVICE=/dev/cu.debug-console
passwd=tgb*963.1
root_dir=/Users/abc/Projects/AsahiLinux
m1n1_dir=$root_dir/m1n1-upstream/m1n1
macvdmtool_dir=$root_dir/macvdmtool

# you may need to change the following two configs
test_dir=$root_dir/m1n1-ftp/auto
#test_dir=$root_dir/m1n1-ftp/test-dir

cmds=$m1n1_dir/cmds
#cmds=$m1n1_dir/cmds-hwp-off
test_output_dir=$test_dir/output

echo "ready to run $1 times"

cd $test_dir

# rm the output dir before stating sub-dirs
rm -rf $test_output_dir

#file_dirs=`find $test_dir -type f | xargs dirname | uniq`
file_dirs=`ls ./* | grep  ":" | awk -F ":" '{print $1}'`

# mk output dir in case file_dirs is null which will cause error when redirecting log file
echo "making dir: $test_output_dir"
mkdir -p $test_output_dir

for dir in $file_dirs
do
	echo "making dir: $test_output_dir/$dir"
	mkdir -p $test_output_dir/$dir
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
	sleep 4
	echo "running payload"
	#python3.9 ${m1n1_dir}/proxyclient/sherpa.py ${file}.gz -c $cmds 
	python3.9 ${m1n1_dir}/proxyclient/sherpa.py ${file}.gz -c $cmds > $test_output_dir/${file}.log
	#python3.9 ${m1n1_dir}/proxyclient/sherpa.py ${file}.gz
	rm -rf ${file}.gz
done

echo "reporting..."
python3.9  ${m1n1_dir}/proxyclient/report.py $test_output_dir 
