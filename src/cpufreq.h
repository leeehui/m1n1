/* SPDX-License-Identifier: MIT */
#ifndef __CPUFREQ_H__
#define __CPUFREQ_H__

int apple_m1_cpufreq_set_target(int cluster, unsigned int index);
void apple_m1_cpufreq_hwsetup(void);

#endif
