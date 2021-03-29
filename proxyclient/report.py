import os, sys
import re
import xlwt
import argparse, pathlib
import shutil

class LogReporter:
    def __init__(self):
        self.rename_row_start = 0 #if a sheet names "sheet-rename-xxx", this means we renamed a sheername longer than 31 characters
        self.header_row_start = self.rename_row_start + 1
        self.data_row_start = self.header_row_start + 1
        self.sherpa_counter_num = 6
        self.header = [["Core", "Ipc", "Cycle", "Inst", "Elfnum", "PMC2", "PMC3", "PMC4", "PMC5", "PMC6", "PMC7"],
                       ["Core", "Ipc", "Cycle", "Inst", "Elfnum", "PMC2", "PMC3", "PMC4", "PMC5", "PMC6", "PMC7"]]

    def is_valid_log(self, lines):
        cnt = 0
        for line in lines:
            res = re.search("\[shell info\]start shell main proc,the elf file start addr is", line)
            if res:
                cnt = cnt + 1
        # 8 core booted into kernel
        if cnt == 8:
            print("startup OK.")
            return True
        else:
            print("startup Error. cnt: %d" % cnt)
            return False

    def get_elf_info(self, lines):
        elf_names = []
        for idx, line in enumerate(lines): 
            res = re.match("elf_index    name    addr    size    run_status    run_count    run_total", line)
            if res:
                elf_names.append(lines[idx + 1].split()[1])
            res = re.match("===========================End=============================", line)
            if res:
                break
        #print(elf_names)
        return elf_names 

    def get_event_info(self, lines):
        events = []
        for idx, line in enumerate(lines): 
            res = re.match("enable counter \d+ ,event is 0x\w+", line)
            if res:
                #print(line)
                events.append(lines[idx].split("event is ")[1].split()[0])
                if len(events) == self.sherpa_counter_num:
                    break
        #print(events)
        return events

    def get_ipc_pmc_info(self, line_ipc, line_pmc):
        # findall int including core num with idx[0]
        sub_info = []
        core_cycle_inst = re.findall(r"\d+", line_ipc)
        if core_cycle_inst:
            core_num = core_cycle_inst[0]
            cycle = core_cycle_inst[1]
            instruction = core_cycle_inst[2]
            ipc_str = re.findall("ipc = \d+\.\d*", line_ipc)
            ipc = ipc_str[0].split("ipc = ")[1]
            sub_info.append(core_num)
            sub_info.append(ipc)
            sub_info.append(cycle)
            sub_info.append(instruction)

        # Note: first item is elfnum, we just did not extract that
        pmcs = re.findall(r"\b\d+\b", line_pmc)
        for pmc in pmcs:
            sub_info.append(pmc)

        return sub_info

    # currently this temporarily for calculating ipc throuth rolling, depends on 
    # rolling_valid_lines, this is calculated before
    def get_rolling_info(self, lines, start_idx, rolling_valid_lines, is_skip_first_rolling):
        info = []
        rolling_cycle = []
        rolling_inst = []
        all_cycle = 0
        all_inst = 0
        idx = start_idx
        core_num = 0
        is_core_num_set = 0

        # first we fall back to extract all rolling lines
        while re.match("\[C\d\]\[ROLLING\]", lines[idx]):
            res = re.findall(r"\d+", lines[idx])
            if not is_core_num_set:
                core_num = res[0]
                is_core_num_set = 1
            # Note: this match relys on specific sherpa output!
            # see [C\d][ROLLING]... for details
            rolling_inst.append(res[-3])
            rolling_cycle.append(res[-4])

            idx -= 1
        # do NOT forget reverse the result!
        rolling_cycle = rolling_cycle[::-1]
        rolling_inst = rolling_inst[::-1]
        #print(rolling_valid_lines)
        #print(rolling_cycle)
        #print(rolling_inst)
        # first is always warmup, just skip
        if is_skip_first_rolling == True:
            start = 1
        else:
            start = 0
        cnt = 0
        for i in range(start, len(rolling_cycle)):
            if cnt >= rolling_valid_lines: # count only the rolling num dir name "tell" us 
                break
            all_cycle += int(rolling_cycle[i])
            all_inst += int(rolling_inst[i])
            cnt += 1

        #print("all_cycle %d" % all_cycle)
        #print("all_inst %d" % all_inst)
        if all_cycle:
            ipc = float(all_inst) / float(all_cycle)
        else:
            ipc = sys.maxsize

        info.append(core_num)
        info.append(str(ipc))
        info.append(str(all_cycle))
        info.append(str(all_inst))
        # elf_num forced to 0
        info.append("0")
        for i in range(self.sherpa_counter_num): 
            info.append("0")
        
        return info

    def get_info(self, file_name, rolling_valid_lines, is_skip_first_rolling):
        info = []
        elf_names = []
        events = []
        with open(file_name, 'r', encoding='unicode_escape') as file_content:
            lines = file_content.readlines()
            if self.is_valid_log(lines):
                elf_names = self.get_elf_info(lines)
                events = self.get_event_info(lines)
                # get counter related info
                for idx, line in enumerate(lines):
                    if re.match("\[C\d\]\[ELF_\w*\]Success", line):
                        #print(line)
                        start_idx = idx - 1
                        if re.match("\[C\d\]\[SVCROLLING\]", lines[idx - 1]):
                            start_idx -= 1

                        if re.match("\[C\d\]\[ROLLING\]", lines[idx - 1]):
                            sub_info = self.get_rolling_info(lines, start_idx, rolling_valid_lines, is_skip_first_rolling) 
                        else:
                            sub_info = self.get_ipc_pmc_info(lines[start_idx], lines[start_idx - 1]) 
                        info.append(sub_info)
                    else:
                        # no valid info
                        pass
                    
            else:
                pass
        return (info, elf_names, events)

    def get_info_big_core(self, info):
        info_big_core = []
        for idx in range(len(info)):
            if int(info[idx][0]) >= 4:
                info_big_core.append(info[idx])
                # we only need the first big core item
                break
        return info_big_core
    
    # find rolling_valid_lines in dir name
    # only for special binary dirs
    def get_valid_rolling_num(self, root):
        dir_name = root.split("/")[-1]
        splited_dir_name = dir_name.split("_inst") 
        #print(dir_name)
        #print(splited_dir_name)
        rolling_valid_lines = 0
        if len(splited_dir_name) >= 2: # if dir name contains "_inst"
            aux_data = re.findall(r"\d+", splited_dir_name[1]) # just extract all int nums
            if (len(aux_data) >= 2): # as naming is consistent for this kind of binary, 
                inst = aux_data[0]   # we are sure 0 is for effective inst
                warmup = aux_data[1] # we are sure 1 is for warmup    inst
                rolling_valid_lines = int(int(inst) / int(warmup))
                #print("rolling_valid_lines %d" % rolling_valid_lines)
        return rolling_valid_lines
    
    def get_valid_rolling_num_from_log(self, log_file):
        rolling_valid_lines = 0
        with open(log_file, 'r', encoding='unicode_escape') as file_content:
            line_warmup = file_content.readline()
            if re.match("warmup_inst_num=", line_warmup):
                warmup_inst = int(re.findall(r"\d+", line_warmup)[0])
                line_total_inst = file_content.readline()
                total_inst = int(re.findall(r"\d+", line_total_inst)[0])
                line_rolling_interval = file_content.readline()
                rolling_interval = int(re.findall(r"\d+", line_rolling_interval)[0])

                # as for warmup_inst = 0, we have change cmd file in run.sh, just do report 
                if rolling_interval != 0:
                    rolling_valid_lines = (total_inst - warmup_inst) / rolling_interval

        return rolling_valid_lines

    def fill_sheet_header(self, ws):
        header = self.header
        init_col = 1
        for idx in range(len(header)):
            if idx >= 1:
                init_col += len(header[idx-1]) + 1
            for sub_idx, name in enumerate(header[idx]):
                ws.write(self.header_row_start, init_col + sub_idx, name)

    def fill_sheet_line(self, ws, row, col, info, elf_names, events):
        for idx in range(len(info)):
            for sub_idx, sub_item in enumerate(info[idx]):
                #print(sub_idx)
                if sub_idx == 4:
                    sub_item = sub_item + " : " + elf_names[int(sub_item)]
                if sub_idx >= 5:
                    sub_item = events[sub_idx - 5] + " : " + sub_item
                ws.write(row + idx, col + sub_idx + 1, sub_item)

    def do_report(self, dir_to_report):
        #rootdir = sys.argv[1]()
        #rootdir = "/Users/abc/Projects/AsahiLinux/m1n1-ftp/auto/output"
        rerun_dir = str(dir_to_report) + "/Rerun" 
        os.system("rm -rf %s/*.xls " % str(dir_to_report))
        os.system("rm -rf %s/.* " % str(dir_to_report))
        os.system("rm -rf %s " % rerun_dir)
        os.system("mkdir %s " % rerun_dir)
        rootdir = str(dir_to_report)
        report_name = os.path.join(rootdir, "report.xls")
        wb = xlwt.Workbook()
        ws_error_startup = wb.add_sheet("Error_startup")
        #ws_error_cmd_timeout = wb.add_sheet("Error_cmd_timeout")
        error_cnt = 0
        sheet_rename_cnt = 0
        #dirs = os.listdir("/Users/abc/Projects/AsahiLinux/m1n1-ftp/auto/output")
        for root, subdirs, files in os.walk(rootdir):
            if files:
                # build a new sheet
                rela_file_path = root.split(rootdir)
                rela_file_portions = rela_file_path[1].split("/")
                sheet_name="RES"
                for p in rela_file_portions:
                    if p:
                        sheet_name = sheet_name + "-" + p 
                #print(sheet_name)
                try:
                    ws = wb.add_sheet(sheet_name)
                except:
                    sheet_renamed = "sheet-rename-" + str(sheet_rename_cnt)
                    sheet_rename_cnt += 1
                    ws = wb.add_sheet(sheet_renamed)
                    ws.write(self.rename_row_start, 0, sheet_name)

                self.fill_sheet_header(ws)
                row_delta = self.data_row_start
                row_delta_big_core = self.data_row_start
                col_start_big_core = len(self.header[0]) + 1

                rolling_valid_lines = self.get_valid_rolling_num(root)

                print(files)
                for idx, file_name in enumerate(files):
                    if file_name.endswith('.log'):
                        file_path = os.path.join(root, file_name)

                        print(file_path)

                        row_to_written = idx + row_delta

                        rolling_valid_lines_from_log = self.get_valid_rolling_num_from_log(file_path)
                        if rolling_valid_lines_from_log:
                            print("rolling_valid_lines_from_log: %d" % rolling_valid_lines_from_log)
                            info, elf_names, events = self.get_info(file_path, rolling_valid_lines_from_log, is_skip_first_rolling = False)
                        else:
                            info, elf_names, events = self.get_info(file_path, rolling_valid_lines, is_skip_first_rolling = True)
                        if info:
                            # report to specific sheet only if there is valic info
                            ws.write(row_to_written, 0, file_name)
                            # if this info is about big core
                            #print(info)
                            #print(elf_names)
                            #print(events)
                            self.fill_sheet_line(ws, row_to_written, 0, info, elf_names, events) 
                            row_delta = row_delta + len(info) + 1

                            info_big_core = self.get_info_big_core(info)
                            if info_big_core:
                                ws.write(row_delta_big_core, col_start_big_core, file_name)
                                self.fill_sheet_line(ws, row_delta_big_core, col_start_big_core, info_big_core, elf_names, events)
                                row_delta_big_core += 1 #only have one item
                        else:
                            ws_error_startup.write(error_cnt, 0, file_path)
                            error_cnt = error_cnt + 1
                            rerun_file_name = file_path.replace("output/", "")
                            rerun_file_name = rerun_file_name.replace(".log", "")
                            rerun_file_dest = root.replace("output","output/Rerun")
                            os.system("mkdir -p %s"% rerun_file_dest)
                            #print(root)
                            print(rerun_file_name)
                            print(root)
                            print(rerun_file_dest)
                            shutil.copy(rerun_file_name, rerun_file_dest)
                            
        wb.save(report_name)
        if error_cnt:
            print("total error_cnt: %d, please check report xls" % error_cnt)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='log parser')
    parser.add_argument('payload', type=pathlib.Path)
    args = parser.parse_args()
    lr = LogReporter()
    lr.do_report(args.payload)