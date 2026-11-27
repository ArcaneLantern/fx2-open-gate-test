/* FX2 /etc/ld.so.preload NO-OP TEST payload (LOCAL, 2026-11-27). Global preload: ld.so loads this into every
 * dynamically-linked process. Constructor writes /etc/fx2_preload_ran (proof it loaded) and returns. Only syscalls,
 * cannot crash a process; if unloadable, stock glibc prints "...ignored." and the process runs normally. */
static long sc4(long n,long a,long b,long c,long d){register long x8 asm("x8")=n,x0 asm("x0")=a,x1 asm("x1")=b,x2 asm("x2")=c,x3 asm("x3")=d;
  asm volatile("svc 0":"+r"(x0):"r"(x8),"r"(x1),"r"(x2),"r"(x3):"memory","cc");return x0;}
__attribute__((constructor)) static void mark(void){
  long fd=sc4(56,-100,(long)"/etc/fx2_preload_ran",0x241,0644); if(fd<0)return;
  sc4(64,fd,(long)"ok\n",3,0); sc4(57,fd,0,0,0);
}
