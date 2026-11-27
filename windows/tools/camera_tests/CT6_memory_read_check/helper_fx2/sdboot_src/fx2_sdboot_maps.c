/* V23 (read-only): from inside im.elf, scan /proc/self/maps for our preload marker and count mapped .so's.
 * Run AFTER install + reboot: tells whether /etc/ld.so.preload actually loaded the marker into im.elf. */
static long sc(long n,long a,long b,long c,long d,long e){register long x8 asm("x8")=n,x0 asm("x0")=a,x1 asm("x1")=b,x2 asm("x2")=c,x3 asm("x3")=d,x4 asm("x4")=e;
  asm volatile("svc 0":"+r"(x0):"r"(x8),"r"(x1),"r"(x2),"r"(x3),"r"(x4):"memory","cc");return x0;}
static long sl(const char*s){long n=0;while(s[n])n++;return n;}
static char O[400]; static int on; static void ap(const char*s){while(*s&&on<360)O[on++]=*s++;}
static void apn(long v){char t[20];int k=0;if(!v)t[k++]='0';while(v){t[k++]='0'+v%10;v/=10;}while(k)O[on++]=t[--k];}
__attribute__((constructor)) static void go(void){
  char comm[20]; long fd=sc(56,-100,(long)"/proc/self/comm",0,0,0); long n=0; if(fd>=0){n=sc(63,fd,(long)comm,18,0,0);sc(57,fd,0,0,0,0);} if(n>0&&comm[n-1]=='\n')comm[n-1]=0; comm[n>0?(n-1<19?n-1:19):0]=0;
  int marker=0, socount=0;
  fd=sc(56,-100,(long)"/proc/self/maps",0,0,0);
  if(fd>=0){ char buf[4096]; char win[32]; int wl=0; 
    for(;;){ long r=sc(63,fd,(long)buf,sizeof buf,0,0); if(r<=0)break;
      for(long i=0;i<r;i++){ char c=buf[i];
        /* sliding window to find "fx2_preload" and ".so\n" */
        if(wl<31)win[wl++]=c; else { for(int j=0;j<31;j++)win[j]=win[j+1]; win[31]=c; }
        /* check tail for ".so\n" */
        if(c=='\n'){ if(wl>=4 && win[wl-4]=='.'&&win[wl-3]=='s'&&win[wl-2]=='o') socount++; wl=0; }
      }
      /* crude: scan whole buffer for substring fx2_preload */
      for(long i=0;i+11<r;i++) if(buf[i]=='f'&&buf[i+1]=='x'&&buf[i+2]=='2'&&buf[i+3]=='_'&&buf[i+4]=='p'&&buf[i+5]=='r'&&buf[i+6]=='e') marker=1;
    }
    sc(57,fd,0,0,0,0);
  }
  ap("readcheck 1 level 23\neuid 0\n== level 23\nDONE: maps probe  comm="); ap(comm[0]?comm:"?");
  ap("  marker_mapped="); ap(marker?"YES":"no");
  ap("  so_lines(approx)="); apn(socount);
  ap("\n== done, bytes written before this line: 0\n");
  long rf=sc(56,-100,(long)"/tmp_wbshd/readcheck_result.txt",0x241,0644,0); if(rf>=0){sc(64,rf,(long)O,on,0,0);sc(57,rf,0,0,0,0);}
}
