import os, sys
import re
import xlwt
import argparse, pathlib

def is_valid_log(lines):
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

def get_elf_info(lines):
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

def get_event_info(lines, sherpa_counter_num):
    events = []
    for idx, line in enumerate(lines): 
        res = re.match("enable counter \d+ ,event is 0x\w+", line)
        if res:
            #print(line)
            events.append(lines[idx].split("event is ")[1].split()[0])
            if len(events) == sherpa_counter_num:
                break
    #print(events)
    return events

def get_info(file_name, sherpa_counter_num):
    info = []
    elf_names = []
    events = []
    with open(file_name, 'r', encoding='unicode_escape') as file_content:
        lines = file_content.readlines()
        if is_valid_log(lines):
            elf_names = get_elf_info(lines)
            events = get_event_info(lines, sherpa_counter_num)
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

def fill_sheet_header(ws):
    header = ["Core", "Ipc", "Cycle", "Inst", "Elfnum", "PMC2", "PMC3", "PMC4", "PMC5", "PMC6", "PMC7",]
    for idx, name in enumerate(header):
        ws.write(0, idx + 1, name)

def fill_sheet_line(ws, row, info, elf_names, events):
    for idx in range(len(info)):
        for sub_idx, sub_item in enumerate(info[idx]):
            #print(sub_idx)
            if sub_idx == 4:
                sub_item = sub_item + " : " + elf_names[int(sub_item)]
            if sub_idx >= 5:
                sub_item = events[sub_idx - 5] + " : " + sub_item
            ws.write(row + idx, sub_idx + 1, sub_item)

def do_report(dir_to_report):

    sherpa_counter_num = 6
    #rootdir = sys.argv[1]()
    #rootdir = "/Users/abc/Projects/AsahiLinux/m1n1-ftp/auto/output"
    rootdir = str(dir_to_report)
    report_name = os.path.join(rootdir, "report.xls")
    wb = xlwt.Workbook()
    ws_error_startup = wb.add_sheet("Error_startup")
    #ws_error_cmd_timeout = wb.add_sheet("Error_cmd_timeout")
    error_cnt = 0
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
            ws = wb.add_sheet(sheet_name)
            fill_sheet_header(ws)
            row_delta = 0
            print(files)
            for idx, file_name in enumerate(files):
                if file_name.endswith('.log'):
                    file_path = os.path.join(root, file_name)
                    print(file_path)
                    row_to_written = idx + row_delta + 1
                    ws.write(row_to_written, 0, file_name)
                    info, elf_names, events = get_info(file_path, sherpa_counter_num)
                    if info:
                        #print(info)
                        #print(elf_names)
                        #print(events)
                        fill_sheet_line(ws, row_to_written, info, elf_names, events) 
                        row_delta = row_delta + len(info)
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
    do_report(args.payload)