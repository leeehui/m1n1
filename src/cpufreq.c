/* SPDX-License-Identifier: MIT */

#include "string.h"
#include "types.h"
#include "utils.h"


#define NUM_BASES			3
 #define NUM_CLUSTERS			2
 //#define PMGR_BASE			2

 #define CLUSTER_ECPU			0
 #define CLUSTER_PCPU			1

 #define DFLT_STATE			2
 #define SETVOLT_MIN_STATE		6
 #define DRAMCFG_SLOW			0
 #define DRAMCFG_FAST			1
 #define FAST_FREQ_INVALID		(-1u)

 #define CLUSTER_VCTRL			0x20000
 #define   CLUSTER_VCTRL_SETVOLT		BIT(29)
 #define CLUSTER_PSTATE			0x20020
 #define   CLUSTER_PSTATE_LOCKCTRL	BIT(42)
 #define   CLUSTER_PSTATE_BUSY		BIT(31)
 #define   CLUSTER_PSTATE_SET		BIT(25)
 #define   CLUSTER_PSTATE_DISABLE	BIT(22)
 #define   CLUSTER_PSTATE_TGT0_MASK	15
 #define   CLUSTER_PSTATE_TGT_MASK	0xF00F
 #define   CLUSTER_PSTATE_TGT1_SHIFT	12
 #define CLUSTER_CPUTVM			0x20048
 #define   CLUSTER_CPUTVM_ENABLE		BIT(0)
 #define CLUSTER_PSCTRL			0x200f8
 #define   CLUSTER_PSCTRL_ENABLE		BIT(40)
 #define CLUSTER_DVMR			0x206b8
 #define   CLUSTER_DVMR_ENABLE		BIT(63)
 #define   CLUSTER_DVMR_ENABLE_PCPU	(BIT(32) | BIT(31))

 #define CLUSTER_LIMIT2			0x40240
 #define CLUSTER_LIMIT3			0x40250
 #define CLUSTER_CTRL			0x440f8
 #define   CLUSTER_CTRL_ENABLE		BIT(0)
 #define CLUSTER_LIMIT1			0x48400
 #define   CLUSTER_LIMIT_ENABLE		BIT(63)

 #define CLUSTER_PSINFO1_SET		0x70210
 #define CLUSTER_PSINFO2_SET		0x70218
 #define CLUSTER_PSINFO1_GET(i)		(0x70000 + 0x20 * (i))
 #define CLUSTER_PSINFO2_GET(i)		(0x70008 + 0x20 * (i))

 #define PMGR_CPUGATING(cl)		(0x1c080 + 8 * (cl))
 #define   PMGR_CPUGATING_ENABLE		BIT(31)
 #define PMGR_CPUTVM0			0x48000
 #define PMGR_CPUTVM1			0x48c00
 #define PMGR_CPUTVM2			0x48800
 #define PMGR_CPUTVM3			0x48400
 #define   PMGR_CPUTVM_ENABLE		BIT(0)

 #define MCC_NUM_LANES			8
 #define MCC_DRAMCFG0(ln)		(0xdc4 + 0x40000 * (ln))
 #define MCC_DRAMCFG1(ln)		(0xdbc + 0x40000 * (ln))

 #define PMGR_BASE 0x23b700000
 #define PMGR_CLUSTER1_BASE 0x210e00000
 #define PMGR_CLUSTER2_BASE 0x211e00000
 #define MCC_BASE 0x200200000

 #define writeq(val,addr) write64(addr,val)
 #define readq(addr) read64(addr)
 #define writel(val,addr) write32(addr,val)
 #define readl(addr) read32(addr)

static u64 cluster_bases[NUM_CLUSTERS] = { PMGR_CLUSTER1_BASE, PMGR_CLUSTER2_BASE};
static u32 pcpu_dramcfg[2][MCC_NUM_LANES][2];

static inline void rmwq(u64 clr, u64 set, u64 base)
 	{ write64(base, (read64(base) & ~clr) | set); }
static inline void rmwl(u32 clr, u32 set, u64 base)
 	{ write32(base, (read32(base) & ~clr) | set); }

static int apple_m1_cpufreq_wait_idle(int cluster)
 {
 	u64 base = cluster_bases[cluster];
 	unsigned max = 1000;
 	u32 state;

 	while(max --) {
 		state = readq(base + CLUSTER_PSTATE);
 		if(!(state & CLUSTER_PSTATE_BUSY))
 			return 0;

 		udelay(50);
 	}

 	printf("timed out waiting for pstate idle on cluster %d.\n", cluster);
 	return -1;
 }

static unsigned saved_set_volt = 0;
 int apple_m1_cpufreq_set_target(int cluster, unsigned int index)
 {
 	unsigned set_volt;
 	int res;
 	u64 base = cluster_bases[cluster];

 	res = apple_m1_cpufreq_wait_idle(cluster);
 	if(res < 0)
 		return res;

 	set_volt = (index >= SETVOLT_MIN_STATE);
 	if(set_volt != saved_set_volt)
 		rmwq(0, CLUSTER_VCTRL_SETVOLT, base + CLUSTER_VCTRL);
 	else
 		set_volt = 0;

 	rmwq(CLUSTER_PSTATE_TGT_MASK,
 		CLUSTER_PSTATE_SET | (index << CLUSTER_PSTATE_TGT1_SHIFT) | index,
 		base + CLUSTER_PSTATE);
 	writeq(readq(base + CLUSTER_PSINFO1_GET(index)), base + CLUSTER_PSINFO1_SET);
 	writeq(readq(base + CLUSTER_PSINFO2_GET(index)), base + CLUSTER_PSINFO2_SET);

 	if(set_volt != saved_set_volt)
 		rmwq(0, CLUSTER_VCTRL_SETVOLT, base + CLUSTER_VCTRL);
 	else
 		rmwq(CLUSTER_VCTRL_SETVOLT, 0, base + CLUSTER_VCTRL);
 	saved_set_volt = set_volt;

    if(cluster == CLUSTER_PCPU ) {
 		/* tolerance for roundoff  */
 		//cfg = (hcc->freqs[index].frequency > (hc->pcpu_fast_freq * 1000 + 1000)) ? DRAMCFG_FAST : DRAMCFG_SLOW;
        unsigned cfg =  DRAMCFG_FAST;
        unsigned ln;
 		u64 mcc = MCC_BASE;

 		for(ln=0; ln<MCC_NUM_LANES; ln++) {
 			writel(pcpu_dramcfg[cfg][ln][0], mcc + MCC_DRAMCFG0(ln));
 			writel(pcpu_dramcfg[cfg][ln][1], mcc + MCC_DRAMCFG1(ln));
 		}
 	}

 	res = apple_m1_cpufreq_wait_idle(cluster);
 	if(res < 0)
 		return res;

 	return 0;
 }

static void apple_m1_cpufreq_hwsetup_cluster(int cluster)
 {
 	u64 base = cluster_bases[cluster];
 	u64 pmgr = PMGR_BASE;
 	unsigned ps;

 	rmwq(0, CLUSTER_DVMR_ENABLE | (cluster ? CLUSTER_DVMR_ENABLE_PCPU : 0),
 	     base + CLUSTER_DVMR);

 	rmwq(0, CLUSTER_LIMIT_ENABLE, base + CLUSTER_LIMIT1);
 	rmwq(CLUSTER_LIMIT_ENABLE, 0, base + CLUSTER_LIMIT2);
 	rmwq(0, CLUSTER_LIMIT_ENABLE, base + CLUSTER_LIMIT3);

 	rmwq(0, CLUSTER_PSTATE_LOCKCTRL, base + CLUSTER_PSTATE);

 	rmwl(0, PMGR_CPUGATING_ENABLE, pmgr + PMGR_CPUGATING(cluster));

 	writeq(CLUSTER_CTRL_ENABLE, base + CLUSTER_CTRL);

 	ps = readq(base + CLUSTER_PSTATE) & CLUSTER_PSTATE_TGT0_MASK;
 	rmwq(0, CLUSTER_PSCTRL_ENABLE, base + CLUSTER_PSCTRL);
 	writeq(readq(base + CLUSTER_PSINFO1_GET(ps)), base + CLUSTER_PSINFO1_SET);
 	writeq(readq(base + CLUSTER_PSINFO2_GET(ps)), base + CLUSTER_PSINFO2_SET);
 }

void apple_m1_cpufreq_hwsetup(void)
 {
 	u64 *base = cluster_bases;
 	u64 pmgr = PMGR_BASE;
    u64 mcc = MCC_BASE;
 	unsigned ln;

    pcpu_dramcfg[DRAMCFG_FAST][0][0] = 0x33010000;
    pcpu_dramcfg[DRAMCFG_FAST][0][1] = 0x40535555;
 	for(ln=0; ln<MCC_NUM_LANES; ln++) {
 		pcpu_dramcfg[DRAMCFG_SLOW][ln][0] = readl(mcc + MCC_DRAMCFG0(ln));
 		pcpu_dramcfg[DRAMCFG_SLOW][ln][1] = readl(mcc + MCC_DRAMCFG1(ln));
 		if(!ln)
 			continue;
 		pcpu_dramcfg[DRAMCFG_FAST][ln][0] = pcpu_dramcfg[DRAMCFG_FAST][0][0];
 		pcpu_dramcfg[DRAMCFG_FAST][ln][1] = pcpu_dramcfg[DRAMCFG_FAST][0][1];
 	}

 	rmwq(CLUSTER_PSTATE_DISABLE, 0, base[0] + CLUSTER_PSTATE);
 	rmwq(CLUSTER_PSTATE_DISABLE, 0, base[1] + CLUSTER_PSTATE);

 	rmwq(0, CLUSTER_CPUTVM_ENABLE, base[0] + CLUSTER_CPUTVM);
 	rmwq(0, CLUSTER_CPUTVM_ENABLE, base[1] + CLUSTER_CPUTVM);
 	rmwl(0, PMGR_CPUTVM_ENABLE, pmgr + PMGR_CPUTVM0);
 	rmwl(0, PMGR_CPUTVM_ENABLE, pmgr + PMGR_CPUTVM1);
 	rmwl(0, PMGR_CPUTVM_ENABLE, pmgr + PMGR_CPUTVM2);
 	rmwl(0, PMGR_CPUTVM_ENABLE, pmgr + PMGR_CPUTVM3);

 	apple_m1_cpufreq_hwsetup_cluster(0);
 	apple_m1_cpufreq_hwsetup_cluster(1);
 }

