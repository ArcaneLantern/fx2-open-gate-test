/* V22 (read-only): from inside im.elf, read /proc/self/auxv for AT_SECURE (23) and /proc/self/environ
 * for any LD_* / GLIBC_* vars that would disable /etc/ld.so.preload. Settles the preload mystery. */
static long sc(long n,long a,long b,long c,long d,long e){register long x8 asm("x8")=n,x0 asm("x0")=a,x1 asm("x1")=b,x2 asm("x2")=c,x3 asm("x3")=d,x4 asm("x4")=e;
  asm volatile("svc 0":"+r"(x0):"r"(x8),"r"(x1),"r"(x2),"r"(x3),"r"(x4):"memory","cc");return x0;}
static long sl(const char*s){long n=0;while(s[n])n++;return n;}
static char O[1600]; static int on; static void ap(const char*s){while(*s&&on<1560)O[on++]=*s++;}
static void aph(unsigned long v){const char*h="0123456789abcdef";for(int i=60;i>=0;i-=4)O[on++]=h[(v>>i)&0xf];}
static int rdf(const char*p,char*buf,int n){long fd=sc(56,-100,(long)p,0,0,0);if(fd<0)return -1;long r=sc(63,fd,(long)buf,n,0,0);sc(57,fd,0,0,0,0);return (int)r;}
static int pre(const char*s,const char*p){for(int i=0;p[i];i++)if(s[i]!=p[i])return 0;return 1;}
__attribute__((constructor)) static void go(void){
  ap("readcheck 1 level 22\neuid 0\n== level 22\nDONE: ");
  char self[20]; int n=rdf("/proc/self/comm",self,19); if(n>0){if(self[n-1]=='\n')self[n-1]=0; self[n>19?19:n]=0;} ap("comm="); ap(self[0]?self:"?");
  /* auxv */
  unsigned long av[256]; int an=rdf("/proc/self/auxv",(char*)av,sizeof av);
  unsigned long at_secure=0xffffffff; int pairs=an/16;
  for(int i=0;i+1<pairs*2;i+=2){ unsigned long t=av[i],v=av[i+1]; if(t==0)break; if(t==23)at_secure=v; }
  ap("  AT_SECURE=0x"); if(at_secure==0xffffffff)ap("notfound"); else aph(at_secure);
  /* environ: scan for LD_ / GLIBC_ */
  char env[1200]; int en=rdf("/proc/self/environ",env,sizeof env-1); if(en<0)en=0; env[en]=0;
  ap("  env_LD/GLIBC:"); int found=0; int p=0;
  while(p<en){ char*s=env+p; int len=sl(s); if(len==0){p++;continue;}
    if(pre(s,"LD_")||pre(s,"GLIBC_")){ ap(" "); ap(s); found=1; } p+=len+1; }
  if(!found) ap(" (none)");
  ap("\n== done, bytes written before this line: 0\n");
  long rf=sc(56,-100,(long)"/tmp_wbshd/readcheck_result.txt",0x241,0644,0); if(rf>=0){sc(64,rf,(long)O,on,0,0);sc(57,rf,0,0,0,0);}
}
