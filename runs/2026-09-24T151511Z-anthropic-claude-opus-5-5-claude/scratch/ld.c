#include <stdint.h>
#include <string.h>
#include <stdlib.h>
#define MAXC 400
static int W,H,S,NC;
static char B0[MAXC];
static int dirs[4];
static int att,def;
static int keys[16],nkeys;
static uint64_t Z[MAXC][3],ZT,ZK[MAXC];
typedef struct {uint64_t k; signed char wd; signed char ld; short bm;} TE; // wd: min depth attacker win known (127 none); ld: max depth loss known (-1 none)
#define TTB 23
static TE *TT;
static long nodes; static long nlimit=0; static int aborted=0;
enum{EMP=0,BLK=1,WHT=2,EDGE=3,OUT=4};
static uint64_t rnd(){static uint64_t x=88172645463325252ULL;x^=x<<13;x^=x>>7;x^=x<<17;return x;}
static int mark[MAXC],mk=0;
static int stk[MAXC];
static int grp(char*b,int p,int*g,int*libs){ // returns size; libs count (OUT counts as many)
  if(mk>1000000000){memset(mark,0,sizeof(mark));mk=0;}
  mk++; int n=0,sp=0,c=b[p],nl=0; stk[sp++]=p;mark[p]=mk;
  static int lm[MAXC];static int lmk=0; if(lmk>1000000000){memset(lm,0,sizeof(lm));lmk=0;} lmk++;
  while(sp){int q=stk[--sp]; if(g)g[n]=q; n++;
    for(int d=0;d<4;d++){int r=q+dirs[d];
      if(b[r]==c&&mark[r]!=mk){mark[r]=mk;stk[sp++]=r;}
      else if(b[r]==EMP&&lm[r]!=lmk){lm[r]=lmk;nl++;}
      else if(b[r]==OUT)nl+=100;}}
  *libs=nl;return n;}
static uint64_t hsh(char*b){uint64_t h=0;for(int i=0;i<NC;i++)if(b[i]==1||b[i]==2)h^=Z[i][(int)b[i]];return h;}
// play: returns 0 illegal, else 1; sets *nko
static int play(char*b,int p,int c,int ko,int*nko){
  if(b[p]!=EMP||p==ko)return 0;
  int o=3-c,g[MAXC],capn=0,capp=-1,l;
  b[p]=c;
  for(int d=0;d<4;d++){int r=p+dirs[d]; if(b[r]==o){int n=grp(b,r,g,&l); if(l==0){for(int i=0;i<n;i++)b[g[i]]=EMP; capn+=n; capp=r;}}}
  int n=grp(b,p,g,&l);
  if(l==0){b[p]=EMP;return 0;}
  *nko=-1;
  if(capn==1&&n==1&&l==1)*nko=capp;
  return 1;}
// Benson for def; returns 1 if all keys alive
static int benson(char*b){
  static int cid[MAXC],rid[MAXC];int nch=0,nr=0;
  static int chalive[MAXC];static int ropen[MAXC];
  for(int i=0;i<NC;i++){cid[i]=-1;rid[i]=-1;}
  int g[MAXC],l;
  for(int i=0;i<NC;i++)if(b[i]==def&&cid[i]<0){int n=grp(b,i,g,&l);for(int k=0;k<n;k++)cid[g[k]]=nch;chalive[nch]=1;nch++;}
  static int rcells[MAXC][MAXC/4+1];static int rn[MAXC];
  for(int i=0;i<NC;i++)if(b[i]!=def&&b[i]!=EDGE&&rid[i]<0){
    int sp=0;stk[sp++]=i;rid[i]=nr;ropen[nr]=0;rn[nr]=0;
    while(sp){int q=stk[--sp]; if(b[q]==OUT)ropen[nr]=1; if(rn[nr]<MAXC/4)rcells[nr][rn[nr]++]=q; else ropen[nr]=1;
      for(int d=0;d<4;d++){int r=q+dirs[d]; if(b[r]!=def&&b[r]!=EDGE&&rid[r]<0){rid[r]=nr;stk[sp++]=r;}}}
    nr++;}
  // region alive flags
  static int ralive[MAXC];
  for(int r=0;r<nr;r++)ralive[r]=!ropen[r];
  int changed=1;
  while(changed){changed=0;
    for(int c=0;c<nch;c++)if(chalive[c]){
      int v=0;
      for(int r=0;r<nr&&v<2;r++)if(ralive[r]){
        int adj=0,healthy=1;
        for(int k=0;k<rn[r];k++){int q=rcells[r][k];int a=0;
          for(int d=0;d<4;d++){int x=q+dirs[d];if(b[x]==def&&cid[x]==c)a=1;}
          if(a)adj=1; if(b[q]==EMP&&!a)healthy=0;}
        if(adj&&healthy)v++;}
      if(v<2){chalive[c]=0;changed=1;}}
    for(int r=0;r<nr;r++)if(ralive[r]){
      for(int k=0;k<rn[r];k++){int q=rcells[r][k];
        for(int d=0;d<4;d++){int x=q+dirs[d];if(b[x]==def&&!chalive[cid[x]]){ralive[r]=0;changed=1;goto nx;}}}
      nx:;}
  }
  for(int i=0;i<nkeys;i++)if(!chalive[cid[keys[i]]])return 0;
  return 1;}
static int status(char*b){for(int i=0;i<nkeys;i++)if(b[keys[i]]!=def)return 1; if(benson(b))return -1; return 0;}
static int movelist[MAXC],nmv;
static int hist[MAXC];
// attacker wins?  tm to move; depth remaining
static int search(char*b,int tm,int ko,int depth,uint64_t h){
  nodes++; if(nlimit&&nodes>nlimit){aborted=1;return 0;}
  int st=status(b); if(st)return st==1;
  if(depth<=0)return 0;
  uint64_t key=h^(tm==att?ZT:0)^(ko>=0?ZK[ko]:0);
  TE*e=&TT[key&((1<<TTB)-1)];
  if(e->k==key){ if(e->wd<=depth)return 1; if(e->ld>=depth)return 0;}
  int isatt=(tm==att),res=!isatt;
  char nb[MAXC];
  // defender pass option first? try moves first
  int bm=(e->k==key)?e->bm:-1; int best=-1;
  int ord[MAXC],no=0; if(bm>=0)ord[no++]=bm;
  for(int m=0;m<nmv;m++)if(movelist[m]!=bm)ord[no++]=movelist[m];
  for(int i=(bm>=0);i<no;i++){int j=i;while(j>(bm>=0)&&hist[ord[j]]>hist[ord[j-1]]){int t=ord[j];ord[j]=ord[j-1];ord[j-1]=t;j--;}}
  for(int m=0;m<no;m++){int p=ord[m]; if(b[p]!=EMP)continue;
    if(!isatt){int own=1;for(int d=0;d<4;d++){int r=p+dirs[d];if(b[r]!=def&&b[r]!=EDGE)own=0;} if(own)continue;}
    memcpy(nb,b,NC);int nko;
    if(!play(nb,p,tm,ko,&nko))continue;
    int w=search(nb,3-tm,nko,depth-1,hsh(nb));
    if(isatt&&w){res=1;best=p;hist[p]+=depth;goto done;}
    if(!isatt&&!w){res=0;best=p;hist[p]+=depth;goto done;}
  }
  if(!isatt){ // pass
    int w=search(b,att,-1,depth-1,h);
    if(!w)res=0; else res=1;
  }
  done:
  if(aborted)return 0;
  if(e->k!=key){e->k=key;e->wd=127;e->ld=-1;e->bm=-1;}
  if(best>=0)e->bm=best;
  if(res){if(depth<e->wd)e->wd=depth;} else {if(depth>e->ld)e->ld=depth;}
  return res;}
// API
int ld_init(const char*grid,int w,int h,int attacker,const int*kp,int nk,const int*moves,int nm){
  W=w;H=h;S=w;NC=w*h;dirs[0]=1;dirs[1]=-1;dirs[2]=S;dirs[3]=-S;
  for(int i=0;i<NC;i++){char ch=grid[i];B0[i]=ch=='.'?EMP:ch=='X'?BLK:ch=='O'?WHT:ch=='#'?EDGE:OUT;}
  att=attacker;def=3-att;nkeys=nk;for(int i=0;i<nk;i++)keys[i]=kp[i];
  nmv=nm;for(int i=0;i<nm;i++)movelist[i]=moves[i];
  static int inited=0;
  if(!inited){for(int i=0;i<MAXC;i++){Z[i][1]=rnd();Z[i][2]=rnd();ZK[i]=rnd();}ZT=rnd();TT=calloc(1<<TTB,sizeof(TE));inited=1;}
  memset(TT,0,sizeof(TE)*(1<<TTB));
  memset(hist,0,sizeof(hist));
  nodes=0;return 0;}
// query: board string, tm, ko, depth -> attacker wins
int ld_query(const char*grid,int tm,int ko,int depth){
  char b[MAXC];for(int i=0;i<NC;i++){char ch=grid[i];b[i]=ch=='.'?EMP:ch=='X'?BLK:ch=='O'?WHT:ch=='#'?EDGE:OUT;}
  aborted=0; long n0=nodes; nodes=0; int r=search(b,tm,ko,depth,hsh(b)); nodes+=n0; if(aborted){memset(TT,0,sizeof(TE)*(1<<TTB));return -1;} return r;}
void ld_limit(long l){nlimit=l;}
int ld_status(const char*grid){char b[MAXC];for(int i=0;i<NC;i++){char ch=grid[i];b[i]=ch=='.'?EMP:ch=='X'?BLK:ch=='O'?WHT:ch=='#'?EDGE:OUT;} return status(b);}
long ld_nodes(){return nodes;}
