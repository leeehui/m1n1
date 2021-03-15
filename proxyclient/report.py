import os, sys
import re
import xlwt
import argparse, pathlib

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

    def get_info(self, file_name):
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
                    res = re.match("\[C\d\]\[ELF_\w*\]Success", line)
                    if res:
                        #print(line)
                        # findall int including core num with idx[0]
                        sub_info = []
                        core_cycle_inst = re.findall(r"\d+", lines[idx - 1])
                        if core_cycle_inst:
                            core_num = core_cycle_inst[0]
                            cycle = core_cycle_inst[1]
                            instruction = core_cycle_inst[2]
                            ipc_str = re.findall("ipc = \d+\.\d*", lines[idx - 1])
                            ipc = ipc_str[0].split("ipc = ")[1]
                            sub_info.append(core_num)
                            sub_info.append(ipc)
                            sub_info.append(cycle)
                            sub_info.append(instruction)
                        pmcs = re.findall(r"\b\d+\b", lines[idx - 2])
                        for pmc in pmcs:
                            sub_info.append(pmc)

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
                print(files)
                for idx, file_name in enumerate(files):
                    if file_name.endswith('.log'):
                        file_path = os.path.join(root, file_name)
                        print(file_path)
                        row_to_written = idx + row_delta
                        info, elf_names, events = self.get_info(file_path)
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
        wb.save(report_name)
        if error_cnt:
            print("total error_cnt: %d, please check report xls" % error_cnt)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='log parser')
    parser.add_argument('payload', type=pathlib.Path)
    args = parser.parse_args()
    lr = LogReporter()
    lr.do_report(args.payload)