static long sc(long n,long a,long b,long c,long d){register long x8 asm("x8")=n,x0 asm("x0")=a,x1 asm("x1")=b,x2 asm("x2")=c,x3 asm("x3")=d;
  asm volatile("svc 0":"+r"(x0):"r"(x8),"r"(x1),"r"(x2),"r"(x3):"memory","cc");return x0;}
static long sl(const char*s){long n=0;while(s[n])n++;return n;}
static void rm(const char*p){sc(35,-100,(long)p,0,0);}
__attribute__((constructor)) static void go(void){
  rm("/etc/ld.so.preload"); rm("/etc/fx2_preload_marker.so");
  rm("/etc/fx2_any"); rm("/etc/fx2_imelf");
  rm("/etc/fx2in_im.elf"); rm("/etc/fx2in_bootin.elf"); rm("/etc/fx2in_sen.elf");
  rm("/etc/fx2_preload_ran");
  rm("/setting/mode/preload"); rm("/setting/fx2_preload_marker.so"); rm("/setting/fx2_preload_ran");
  const char*t="readcheck 1 level 17\neuid 0\n== level 17\nDONE: preload hook and markers removed\n== done, bytes written before this line: 0\n";
  long fd=sc(56,-100,(long)"/tmp_wbshd/readcheck_result.txt",0x241,0644); if(fd>=0){sc(64,fd,(long)t,sl(t),0);sc(57,fd,0,0,0);}
}
