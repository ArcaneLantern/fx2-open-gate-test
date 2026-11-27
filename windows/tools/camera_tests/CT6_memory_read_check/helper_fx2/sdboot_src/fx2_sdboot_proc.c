/* V21 (read-only, LOCAL 2026-11-27): live /proc probe of im.elf, per maccer_acer's suggestion.
 * Finds a running process named "im.elf" and dumps its mount namespace, root, and capabilities,
 * vs our own process, to settle why /etc/ld.so.preload skips it. Reads only; writes only the result. */
static long sc(long n,long a,long b,long c,long d,long e){register long x8 asm("x8")=n,x0 asm("x0")=a,x1 asm("x1")=b,x2 asm("x2")=c,x3 asm("x3")=d,x4 asm("x4")=e;
  asm volatile("svc 0":"+r"(x0):"r"(x8),"r"(x1),"r"(x2),"r"(x3),"r"(x4):"memory","cc");return x0;}
static long sl(const char*s){long n=0;while(s[n])n++;return n;}
static int eq(const char*a,const char*b){int i=0;for(;a[i]&&b[i];i++)if(a[i]!=b[i])return 0;return a[i]==b[i];}
static char O[1600]; static int on;
static void ap(const char*s){while(*s&&on<1560)O[on++]=*s++;}
static void apn(long v){char t[24];int k=0;if(v==0)t[k++]='0';while(v){t[k++]='0'+v%10;v/=10;}while(k)O[on++]=t[--k];}
static int rdlink(const char*p,char*buf,int n){long r=sc(78,-100,(long)p,(long)buf,n,0);if(r<0){buf[0]=0;return 0;}buf[r]=0;return (int)r;}
static int rdfile(const char*p,char*buf,int n){long fd=sc(56,-100,(long)p,0,0,0);if(fd<0)return 0;long r=sc(63,fd,(long)buf,n-1,0,0);sc(57,fd,0,0,0,0);if(r<0)r=0;buf[r]=0;return (int)r;}
/* copy a "Key:" line from status into O */
static void line(const char*st,const char*key){int kl=sl(key);const char*p=st;
  while(*p){const char*s=p;int i=0;for(;key[i]&&p[i];i++)if(p[i]!=key[i])break;
    if(i==kl){ap(" ");while(*p&&*p!='\n'){O[on++]=*p++;}return;} while(*p&&*p!='\n')p++; if(*p)p++; }
}
static char path[64]; static void mkpath(const char*pid,const char*suf){int k=0;const char*a="/proc/";while(a[k]){path[k]=a[k];k++;}int j=0;while(pid[j]){path[k++]=pid[j++];}int m=0;while(suf[m]){path[k++]=suf[m++];}path[k]=0;}
__attribute__((constructor)) static void go(void){
  char selfmnt[64],selfroot[128],comm[20],st[2048],lnk[128];
  rdlink("/proc/self/ns/mnt",selfmnt,sizeof selfmnt);
  rdlink("/proc/self/root",selfroot,sizeof selfroot);
  rdfile("/proc/self/comm",comm,sizeof comm); for(int i=0;i<20;i++)if(comm[i]=='\n')comm[i]=0;
  ap("readcheck 1 level 21\neuid 0\n== level 21\nDONE: live probe. self comm="); ap(comm);
  ap(" self_mnt="); ap(selfmnt); ap(" self_root="); ap(selfroot); ap("\n");
  long fd=sc(56,-100,(long)"/proc",0,0,0); int found=0,total=0;
  if(fd>=0){ char buf[1024];
    for(;;){ long n=sc(61,fd,(long)buf,sizeof buf,0,0); if(n<=0)break; long p=0;
      while(p<n){ unsigned short rl=*(unsigned short*)(buf+p+16); char*nm=buf+p+19;
        if(nm[0]>='0'&&nm[0]<='9'){ total++; mkpath(nm,"/comm"); char c2[20]; rdfile(path,c2,sizeof c2); for(int i=0;i<20;i++)if(c2[i]=='\n')c2[i]=0;
          if(eq(c2,"im.elf")){ found=1;
            ap("IM.ELF FOUND pid="); ap(nm);
            mkpath(nm,"/ns/mnt"); rdlink(path,lnk,sizeof lnk); ap(" mnt="); ap(lnk); ap(lnk[0]&&eq(lnk,selfmnt)?"(SAME ns)":"(DIFFERENT ns)");
            mkpath(nm,"/root"); rdlink(path,lnk,sizeof lnk); ap(" root="); ap(lnk);
            mkpath(nm,"/status"); rdfile(path,st,sizeof st);
            line(st,"Uid:"); line(st,"CapEff:"); line(st,"CapInh:"); line(st,"CapBnd:"); line(st,"NoNewPrivs:"); line(st,"Seccomp:");
            ap("\n");
          } }
        p+=rl; } }
    sc(57,fd,0,0,0,0);
  }
  if(!found){ ap("IM.ELF NOT RUNNING (not in /proc). total pids="); apn(total); ap("\n"); }
  ap("== done, bytes written before this line: 0\n");
  long rf=sc(56,-100,(long)"/tmp_wbshd/readcheck_result.txt",0x241,0644,0); if(rf>=0){sc(64,rf,(long)O,on,0,0);sc(57,rf,0,0,0,0);}
}
