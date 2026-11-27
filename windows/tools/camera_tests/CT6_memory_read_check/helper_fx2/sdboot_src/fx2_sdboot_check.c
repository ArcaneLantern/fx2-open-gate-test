/* LOCAL (2026-11-27) FX2 /etc/ld.so.preload CHECK (V18, read-only). Delivered by the kit's guarded Jiritsu path. Writes the rw
 * /etc partition (nflasha10). /etc/ld.so.preload is the STANDARD glibc global preload (no debug mode needed), read by
 * ld-2.25.so for every process. Recovery: UNINSTALL (V17), delete /etc/ld.so.preload over USB service mode, or a fw update. */
static long sc(long n,long a,long b,long c,long d){register long x8 asm("x8")=n,x0 asm("x0")=a,x1 asm("x1")=b,x2 asm("x2")=c,x3 asm("x3")=d;
  asm volatile("svc 0":"+r"(x0):"r"(x8),"r"(x1),"r"(x2),"r"(x3):"memory","cc");return x0;}
static long slen(const char*s){long n=0;while(s[n])n++;return n;}
static long wr(const char*p,const char*b,long n){long fd=sc(56,-100,(long)p,0x241,0644);if(fd<0)return fd;long w=sc(64,fd,(long)b,n,0);sc(57,fd,0,0,0);return w;}
static void result(const char*t){wr("/tmp_wbshd/readcheck_result.txt",t,slen(t));}
static int exists(const char*p){long fd=sc(56,-100,(long)p,0,0);if(fd<0)return 0;sc(57,fd,0,0,0);return 1;}
__attribute__((constructor)) static void go(void){
  if(exists("/etc/fx2_preload_ran"))
    result("readcheck 1 level 18\neuid 0\n== level 18\nDONE: marker present -- /etc/ld.so.preload FIRED\n== done, bytes written before this line: 0\n");
  else
    result("readcheck 1 level 18\neuid 0\n== level 18\n!! marker absent: the /etc/ld.so.preload did NOT fire\n== done, bytes written before this line: 0\n");
}
