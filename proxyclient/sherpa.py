#!/usr/bin/python
import argparse, pathlib
import time

parser = argparse.ArgumentParser(description='(Linux) kernel loader for m1n1')
parser.add_argument('payload', type=pathlib.Path)
parser.add_argument('-c', '--cmds', type=pathlib.Path)
args = parser.parse_args()

core_num = 8

from setup import *

print(args.payload)
print(args.cmds)
#payload = open(sys.argv[1], "rb").read()
payload = args.payload.read_bytes()

compressed_size = len(payload)
compressed_addr = 0x910000000

print("Loading %d bytes to 0x%x..0x%x..." % (compressed_size, compressed_addr, compressed_addr + compressed_size))

iface.writemem(compressed_addr, payload, True)

kernel_size = 1000 * 1024 * 1024
kernel_base = 0x880000000

print("Kernel_base: 0x%x" % kernel_base)

assert not (kernel_base & 0xffff)

print("smp_start_secondaries...")
p.smp_start_secondaries()

#ap_trampoline_code_addr = 0x890000000
#c = asm.ARMAsm("""
#        msr DAIFClr, 7
#        ldr x1, =0x880000000
#        blr x1
#""", ap_trampoline_code_addr)
#
#iface.writemem(ap_trampoline_code_addr, c.data)
#p.dc_cvau(ap_trampoline_code_addr, len(c.data))
#p.ic_ivau(ap_trampoline_code_addr, len(c.data))
#
#print("Enable IRQs on secondaries")
#for i in range(1, 8):
#    ret = p.smp_call_sync(i, code)
#    #print("0x%x"%ret)

print("Uncompressing...", flush=True)
iface.dev.timeout = 40

kernel_size = p.gzdec(compressed_addr, compressed_size, kernel_base, kernel_size)
print(kernel_size)

if kernel_size < 0:
    raise Exception("Decompression error!", flush=True)

print("Decompress OK...", flush=True)

p.dc_cvau(kernel_base, kernel_size)
p.ic_ivau(kernel_base, kernel_size)

print("Ready to kick other cpus to kernel", flush=True)
#print("smp_start_secondaries...")
#p.smp_start_secondaries()
# see def test_smp_ipi(): for more detailed info
for i in range(1, core_num):
    print("core %d jumping to kernel..." % i, flush=True)
    p.smp_call(i, kernel_base)
    iface.wait_one_cmd(silent = True)
    #time.sleep(1) #seems sherpa do NOT support simultaneously smp boot, so must sleep!

print("trying to speedup big cores", flush=True)
p.smp_set_freq(1, 15)

print("Ready to boot", flush=True)
daif = u.mrs(DAIF)
daif |= 0x3c0
u.msr(DAIF, daif)
print("DAIF: %x" % daif, flush=True)

p.kboot_boot(kernel_base)

# wait 8 core bringup
for i in range(core_num):
    # fixme: b'[shell info]start shell main proc,the elf file start addr is'  does NOT work!
    iface.wait_run_elf_cmd(b'shell info]start shell main proc,the elf file start addr is')
    print("booted core num: %d" % (i+1), flush=True)

iface.ttymode(cmds=args.cmds)


