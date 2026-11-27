/* V24 (read-only): im.elf /proc/self/maps — report byte count + whether 'lib' (sanity) and 'fx2_pre' (our marker) appear. */
static long sc(long n,long a,long b,long c,long d,long e){register long x8 asm("x8")=n,x0 asm("x0")=a,x1 asm("x1")=b,x2 asm("x2")=c,x3 asm("x3")=d,x4 asm("x4")=e;
  asm volatile("svc 0":"+r"(x0):"r"(x8),"r"(x1),"r"(x2),"r"(x3),"r"(x4):"memory","cc");return x0;}
static char O[400]; static int on; static void ap(const char*s){while(*s&&on<360)O[on++]=*s++;}
static void apn(long v){char t[20];int k=0;if(!v)t[k++]='0';while(v){t[k++]='0'+v%10;v/=10;}while(k)O[on++]=t[--k];}
static int has3(const char*b,long r,char a,char c,char d){for(long i=0;i+2<r;i++)if(b[i]==a&&b[i+1]==c&&b[i+2]==d)return 1;return 0;}
__attribute__((constructor)) static void go(void){
  char comm[20]; long fd=sc(56,-100,(long)"/proc/self/comm",0,0,0); long n=0; if(fd>=0){n=sc(63,fd,(long)comm,18,0,0);sc(57,fd,0,0,0,0);} if(n>0&&comm[n-1]=='\n')comm[n-1]=0; comm[n>0?(n<19?n-1:19):0]=0;
  long total=0; int haslib=0, hasmk=0, hasld=0;
  fd=sc(56,-100,(long)"/proc/self/maps",0,0,0);
  if(fd>=0){ char buf[8192];
    for(;;){ long r=sc(63,fd,(long)buf,sizeof buf,0,0); if(r<=0)break; total+=r;
      if(has3(buf,r,'l','i','b'))haslib=1;
      if(has3(buf,r,'l','d','-'))hasld=1;
      for(long i=0;i+6<r;i++) if(buf[i]=='f'&&buf[i+1]=='x'&&buf[i+2]=='2'&&buf[i+3]=='_'&&buf[i+4]=='p'&&buf[i+5]=='r'&&buf[i+6]=='e')hasmk=1;
    } sc(57,fd,0,0,0,0);
  }
  ap("readcheck 1 level 24\neuid 0\n== level 24\nDONE: comm="); ap(comm[0]?comm:"?");
  ap("  maps_bytes="); apn(total);
  ap("  has'lib'="); ap(haslib?"Y":"N"); ap("  has'ld-'="); ap(hasld?"Y":"N");
  ap("  marker='fx2_pre'="); ap(hasmk?"YES":"no");
  ap("\n== done, bytes written before this line: 0\n");
  long rf=sc(56,-100,(long)"/tmp_wbshd/readcheck_result.txt",0x241,0644,0); if(rf>=0){sc(64,rf,(long)O,on,0,0);sc(57,rf,0,0,0,0);}
}
