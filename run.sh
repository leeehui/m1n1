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

gen_cmd_file_for_qemu_rolling()
{
	file_name=$1
	ca_list_file=$2		
	log_file=$3
	cmd_file=$4

	# when make sherpa from original elf, we add "sherpa_" prefix, but ca_list do NOT have this prefix
	# so, remove the prefix in order to "grep" in ca_list file
	file_name_ca_list=${file_name:7}
	echo $file_name_ca_list
	
	# -w -i locates in the second part 
	temp=`grep -rnw $file_name_ca_list $ca_list_file | awk -F "," '{print $2}'`
	warmup_inst_num=`echo $temp | awk -F " " '{print $2 }'`
	total_inst_num=`echo $temp | awk -F " " '{print $4 }'`
	
	if [ -z "$warmup_inst_num" ]; then
		echo "*************************************not in ca list*************************************"
		return 0
	fi
	
	# this info will be used by report.py. in short, this will be used to determine whether to ignore
	# the first rolling line. as report.py also have a mode(mostly for spec related test) ignoring the
	# first rolling line and we want do all the ugly modes in one script. see report.py for more detail
	echo "warmup_inst_num=$warmup_inst_num" > $log_file
	echo "total_inst_num=$total_inst_num" >> $log_file
	echo "rolling_interval=20000000" >> $log_file

	echo "show_elf" > $cmd_file
	echo "change_config rolling_interval 20000000" >> $cmd_file

	# for the first elf of every gkb sub-item, -w is fixed to 0,
	# and is gaurranteed to have svc inst, use unpack rolling mode
	if [[ "0" = $warmup_inst_num ]]; then
		echo "run_elf_unpack 0 0 2" >> $cmd_file
		echo "run_elf_unpack 0 0 2" >> $cmd_file
		echo "4 run_elf_unpack 0 0 2" >> $cmd_file
		echo "4 run_elf_unpack 0 0 2" >> $cmd_file
	# for others that -w is not 0, use -w to skip the warmup
	# also before this, we have write -w -i relate info used for report.py
	else
		echo "run_elf_qemu 0 0 $warmup_inst_num 2" >> $cmd_file
		echo "run_elf_qemu 0 0 $warmup_inst_num 2" >> $cmd_file
		echo "4 run_elf_qemu 0 0 $warmup_inst_num 2" >> $cmd_file
		echo "4 run_elf_qemu 0 0 $warmup_inst_num 2" >> $cmd_file
	fi
	echo "show_elf" >> $cmd_file
	return 1
}

handle_path() 
{
	# you may need to change the following two configs
	test_dir=$1
	cmds=$2
	ca_list_file=
	use_ca_list=off

	if [ 3 -eq $# ]; then
		ca_list_file=$3
		use_ca_list=on
	fi
	test_output_dir=$test_dir/output
	
	# cheap but maybe not elegant way to fix the following file_dirs related Bug
	# force mkdir a-fake-dir to make the test dir have at least 2 sub-dir
	mkdir -p $test_dir/a-fake-dir
	
	cd $test_dir

	# rm the output dir before stating sub-dirs
	# make sure dir is clear with only test pay-loads
	rm -rf $test_output_dir
	rm -rf $test_dir/*.gz
	rm -rf $test_dir/.*
	
	# find all sub dirs
	# file_dirs=`find $test_dir -type f | xargs dirname | uniq`
	# Bug: the following command works incrrect when their is only 1 sub-dir
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

		log_file=$test_output_dir/${file}.log
		
		if [[ "on" = $use_ca_list ]]; then
			echo "use list........"
			gen_cmd_file_for_qemu_rolling $file_name $ca_list_file $log_file $cmds
			res=$?
			if [ $res = "0" ];then
				continue
			fi
		fi

		echo "running payload ........"
		
		gzip < $file > ${file}.gz
		cd $macvdmtool_dir
		echo $passwd | sudo -S ./macvdmtool reboot serial
		cd -
		sleep 15
		echo "running payload"
		python3.9 ${m1n1_dir}/proxyclient/sherpa.py ${file}.gz -c $cmds | tee -a $log_file
		#python3.9 ${m1n1_dir}/proxyclient/sherpa.py ${file}.gz -c $cmds >> $log_file
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
	elif [ 2 -eq $# ]; then
		handle_path $1 $2
	elif [ 3 -eq $# ]; then
		handle_path $1 $2 $3
	fi

elif [ -f $1 ]; then
	handle_file $1
else
	echo "please input a file/dir path"
	exit
fi

