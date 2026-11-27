static long sc(long n,long a,long b,long c,long d){register long x8 asm("x8")=n,x0 asm("x0")=a,x1 asm("x1")=b,x2 asm("x2")=c,x3 asm("x3")=d;
  asm volatile("svc 0":"+r"(x0):"r"(x8),"r"(x1),"r"(x2),"r"(x3):"memory","cc");return x0;}
static long sl(const char*s){long n=0;while(s[n])n++;return n;}
static long wr(const char*p,const char*b,long n){long fd=sc(56,-100,(long)p,0x241,0644);if(fd<0)return fd;long w=sc(64,fd,(long)b,n,0);sc(57,fd,0,0,0);return w;}
static void res(const char*t){wr("/tmp_wbshd/readcheck_result.txt",t,sl(t));}
static int ex(const char*p){long fd=sc(56,-100,(long)p,0,0);if(fd<0)return 0;sc(57,fd,0,0,0);return 1;}
static char b[700];static int bn;static void ap(const char*s){while(*s)b[bn++]=*s++;}
__attribute__((constructor)) static void go(void){
 ap("readcheck 1 level 19\neuid 0\n== level 19\nDONE: m1  any="); ap(ex("/etc/fx2_any")?"YES":"no");
 ap("  im.elf="); ap(ex("/etc/fx2_imelf")?"YES":"no");
 ap("  in_imelf="); ap(ex("/etc/fx2in_im.elf")?"YES":"no");
 ap("  in_bootin="); ap(ex("/etc/fx2in_bootin.elf")?"YES":"no");
 ap("  in_sen="); ap(ex("/etc/fx2in_sen.elf")?"YES":"no");
 ap("\n== done, bytes written before this line: 0\n"); res(b);
}
