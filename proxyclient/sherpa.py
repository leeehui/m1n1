#!/usr/bin/python
import argparse, pathlib
import time

parser = argparse.ArgumentParser(description='(Linux) kernel loader for m1n1')
parser.add_argument('payload', type=pathlib.Path)
parser.add_argument('-c', '--cmds', type=pathlib.Path)
args = parser.parse_args()

from setup import *

print(args.payload)
print(args.cmds)
#payload = open(sys.argv[1], "rb").read()
payload = args.payload.read_bytes()

compressed_size = len(payload)
compressed_addr = 0x910000000

print("Loading %d bytes to 0x%x..0x%x..." % (compressed_size, compressed_addr, compressed_addr + compressed_size))

iface.writemem(compressed_addr, payload, True)

kernel_size = 200 * 1024 * 1024
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

print("Uncompressing...")
iface.dev.timeout = 40

kernel_size = p.gzdec(compressed_addr, compressed_size, kernel_base, kernel_size)
print(kernel_size)

if kernel_size < 0:
    raise Exception("Decompression error!")

print("Decompress OK...")

p.dc_cvau(kernel_base, kernel_size)
p.ic_ivau(kernel_base, kernel_size)

print("Ready to kick other cpus to kernel")
#print("smp_start_secondaries...")
#p.smp_start_secondaries()
# see def test_smp_ipi(): for more detailed info
for i in range(1, 8):
    print("core %d jumping to kernel..." % i)
    p.smp_call(i, kernel_base)
    time.sleep(0.5) #seems sherpa do NOT support simultaneously smp boot, so must sleep!

time.sleep(2)
print("Ready to boot")
daif = u.mrs(DAIF)
daif |= 0x3c0
u.msr(DAIF, daif)
print("DAIF: %x" % daif)

p.kboot_boot(kernel_base)
time.sleep(1)

iface.ttymode(cmds=args.cmds)


