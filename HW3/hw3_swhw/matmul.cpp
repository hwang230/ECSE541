#include "matmul.h"

extern unsigned int inputA, inputB, inputC;
extern unsigned int matSize, loops;

double sw_cycle_time = 6.67;
extern double hw_cycle_time; // comes from defined value in hw.cpp

// constructor
matmul::matmul(sc_module_name name): sc_module(name){
    SC_THREAD(do_MATMUL);
}


void matmul::do_MATMUL(){

    int n, i, j; // k is taken care of now by hw
    unsigned int r_addr, r_addrA, r_addrB, r_addrC;
    unsigned int status;

    for (n=0; n<loops; n++) // Total Cycles: 8186006, Execs: 1, Iters: 1000
    {
        // initialize loop
        for(i=0; i<matSize; i++){ // Total Cycles: 579000, Execs: 1000, Iters: 5
            for(j=0; j<matSize; j++){ // Total Cycles: 520000, Execs: 5000, Iters: 5

                // addrC[n][i][j] = 0;
                r_addr = inputC  + i*matSize +j; // single cell for address

                busMaster->Request(0, r_addr, 1, 1);
                busMaster->WriteData(0); // write zero to r_addr for initialization
                busMaster->WaitForAcknowledge(0);
            }
        }

        // config matSize for hw loop
        busMaster->Request(0, 20, 1, 1);
        busMaster->WriteData(matSize);
        busMaster->WaitForAcknowledge(0);

        // calculation loop
        for(i=0; i<matSize; i++){ // Total Cycles: 7579000, Execs: 1000, Iters: 5
            for(j=0; j<matSize; j++){ // Total Cycles: 7520000, Execs: 5000, Iters: 5
                    
                // 'j' loop cycles = 7,520,000
                // 'k' loop cycles = 7,225,000
                // Overhead = (7,520,000 - 7,225,000) = 295,000 cycles
                // Cycles/iteration = 295,000/5,000 executions = 59 cycles
                // wait(59 * sw_cycle_time, SC_NS);

                // addrC[n][i][j] += addrA[n][i][k] * addrB[n][k][j];
                r_addrC = inputC + i*matSize +j;
                r_addrA = inputA + i*matSize;
                r_addrB = inputB + j;

                // config C address
                busMaster->Request(0, 8, 1, 1);
                busMaster->WriteData(r_addrC);
                busMaster->WaitForAcknowledge(0);

                // config A address
                busMaster->Request(0, 12, 1, 1);
                busMaster->WriteData(r_addrA);
                busMaster->WaitForAcknowledge(0);

                // config B address
                busMaster->Request(0, 16, 1, 1);
                busMaster->WriteData(r_addrB);
                busMaster->WaitForAcknowledge(0);

                // hw computations:
                busMaster->Request(0, 0, 1, 1);
                busMaster->WriteData(1);
                busMaster->WaitForAcknowledge(0);

                status = 0; // ensure status = 0 (busy)
                while(status == 0){

                    busMaster->Request(0, 4, 0, 1); // request a status read
                    busMaster->WaitForAcknowledge(0);
                    busMaster->ReadData(status); // status = 1 means hw is done
                    wait(hw_cycle_time, SC_NS);
                }

            }
        }

    }
    sc_stop();
}