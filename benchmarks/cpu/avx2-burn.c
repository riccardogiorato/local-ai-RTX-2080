// avx2-burn: N threads of independent 256-bit FMA chains (AVX2+FMA), the instruction mix that heats a
// Coffee Lake core hardest. Usage: avx2-burn THREADS SECONDS. Prints total GFLOP/s.
#include <immintrin.h>
#include <pthread.h>
#include <stdio.h>
#include <stdlib.h>
#include <time.h>
static double secs; static volatile int stop;
static double now(void){ struct timespec t; clock_gettime(CLOCK_MONOTONIC,&t); return t.tv_sec+t.tv_nsec*1e-9; }
static void *work(void *arg){
  __m256 a[12]; __m256 m=_mm256_set1_ps(0.9999999f), c=_mm256_set1_ps(1e-7f);
  for(int i=0;i<12;i++) a[i]=_mm256_set1_ps(1.0f+i);
  unsigned long long it=0;
  while(!stop){ for(int k=0;k<1000;k++) for(int i=0;i<12;i++) a[i]=_mm256_fmadd_ps(a[i],m,c); it++; }
  float s=0; float o[8]; for(int i=0;i<12;i++){ _mm256_storeu_ps(o,a[i]); s+=o[0]; }
  *(double*)arg = (double)it*1000*12*8*2 + (s==12345.f);   // flops (keep result live)
  return NULL;
}
int main(int argc,char**argv){
  int n=argc>1?atoi(argv[1]):6; secs=argc>2?atof(argv[2]):60;
  pthread_t th[64]; double fl[64]={0}; double t0=now();
  for(int i=0;i<n;i++) pthread_create(&th[i],0,work,&fl[i]);
  while(now()-t0<secs){ struct timespec s={0,100000000}; nanosleep(&s,0); }
  stop=1; double tot=0; for(int i=0;i<n;i++){ pthread_join(th[i],0); tot+=fl[i]; }
  printf("avx2-burn: %d threads, %.0f s, %.1f GFLOP/s\n", n, now()-t0, tot/(now()-t0)/1e9);
  return 0;
}
