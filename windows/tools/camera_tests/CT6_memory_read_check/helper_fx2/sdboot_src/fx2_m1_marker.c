static long sc(long n,long a,long b,long c,long d){register long x8 asm("x8")=n,x0 asm("x0")=a,x1 asm("x1")=b,x2 asm("x2")=c,x3 asm("x3")=d;
  asm volatile("svc 0":"+r"(x0):"r"(x8),"r"(x1),"r"(x2),"r"(x3):"memory","cc");return x0;}
static void touch(const char*p){long fd=sc(56,-100,(long)p,0x241,0644);if(fd>=0){sc(64,fd,(long)"ok\n",3,0);sc(57,fd,0,0,0);}}
__attribute__((constructor)) static void m1(void){
  touch("/etc/fx2_any");                      /* proof it loaded into some process */
  char comm[20]; for(int i=0;i<20;i++)comm[i]=0;
  long fd=sc(56,-100,(long)"/proc/self/comm",0,0); if(fd<0)return;
  long n=sc(63,fd,(long)comm,18,0); sc(57,fd,0,0,0);        /* read */
  if(n<=0)return; if(comm[n-1]=='\n')comm[n-1]=0;
  /* build /etc/fx2in_<comm> */
  char path[48]; const char*pre="/etc/fx2in_"; int k=0; for(;pre[k];k++)path[k]=pre[k];
  for(int i=0;comm[i]&&k<46;i++){char c=comm[i]; path[k++]=(c=='/'?'_':c);} path[k]=0;
  touch(path);
  /* specific: comm == "im.elf" */
  const char*t="im.elf"; int same=1; for(int i=0;i<6;i++) if(comm[i]!=t[i]){same=0;break;}
  if(same&&comm[6]==0) touch("/etc/fx2_imelf");
}
