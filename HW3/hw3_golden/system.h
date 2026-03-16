#ifndef SYSTEM_H
#define SYSTEM_H

#include <systemc.h>

#define NUM_BLOCKS 64
#define BLOCK_SIZE 64
#define INPUT1_ADDR 0
#define INPUT2_ADDR 16384
#define SAD_OUTPUT_ADDR 32768
#define MEMORY_SIZE (1 << (10+6))

// new variable for HW3
#define addrC
#define addrA
#define addrB
#define SIZE 6
#define LOOPS 1000

#endif