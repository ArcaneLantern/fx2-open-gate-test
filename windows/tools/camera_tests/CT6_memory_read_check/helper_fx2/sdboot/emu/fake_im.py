"""EMULATION ONLY: a process that stands in for the camera application in the test sandbox (emu_fx2boot.py).

It names itself im.elf, maps a copy of the camera's libmpr.so the way the dynamic loader maps a library's text (private, read + execute, from
file offset 0), prints the mapping's address, and sleeps. The loader's "outside" encoder step must find it by name, find the mapping in
/proc/<pid>/maps, and read and write the bytes through /proc/<pid>/mem: the real kernel does the rest, as on the camera.

  python3 fake_im.py <libmpr.so> [name]
"""
import ctypes
import mmap
import os
import sys
import time

path = sys.argv[1]
name = (sys.argv[2] if len(sys.argv) > 2 else "im.elf").encode()
libc = ctypes.CDLL(None, use_errno=True)
libc.prctl(15, ctypes.c_char_p(name), 0, 0, 0)                     # PR_SET_NAME
fd = os.open(path, os.O_RDONLY)
size = os.fstat(fd).st_size
libc.mmap.restype = ctypes.c_void_p
libc.mmap.argtypes = [ctypes.c_void_p, ctypes.c_size_t, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_long]
addr = libc.mmap(None, size, mmap.PROT_READ | mmap.PROT_EXEC, mmap.MAP_PRIVATE, fd, 0)
if addr in (None, ctypes.c_void_p(-1).value):
    raise SystemExit("mmap failed")
print("%d %x %d" % (os.getpid(), addr, size), flush=True)
while True:
    time.sleep(3600)
