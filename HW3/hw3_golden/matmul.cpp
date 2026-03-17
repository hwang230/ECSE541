#include "matmul.h"

extern unsigned int inputA, inputB, inputC;
extern unsigned int matSize, loops;

// constructor
matmul::matmul(sc_module_name name): sc_module(name){
    SC_THREAD(do_MATMUL);
}


void matmul::do_MATMUL(){
    int n;  int i,j,k;
    unsigned int r_addr;
    unsigned int r_addrA, r_addrB, r_addrC;
    unsigned int dataA, dataB, dataC;
    unsigned int result;
    for (n=0; n<loops; n++) // Total Cycles: 8186006, Execs: 1, Iters: 1000
    {
        for(i=0; i<matSize; i++){ // Total Cycles: 579000, Execs: 1000, Iters: 5
            for(j=0; j<matSize; j++){ // Total Cycles: 520000, Execs: 5000, Iters: 5
                // replace this with bus functions
                //addrC[n][i][j] = 0;
                r_addr = inputC  + i*matSize +j;
                busMaster->Request(0, r_addr, 1, 1);
                busMaster->WriteData(0);
                busMaster->WaitForAcknowledge(0);
            }
        }
        for(i=0; i<matSize; i++){ // Total Cycles: 7579000, Execs: 1000, Iters: 5
            for(j=0; j<matSize; j++){ // Total Cycles: 7520000, Execs: 5000, Iters: 5
                for(k=0; k<matSize; k++){ // Total Cycles: 7225000, Execs: 25000, Iters: 5
                    // replace this with bus functions
                    //addrC[n][i][j] += addrA[n][i][k] * addrB[n][k][j];
                    // addresses calculation
                    r_addrC = inputC  + i*matSize + j;
                    r_addrA = inputA  + i*matSize + k;
                    r_addrB = inputB  + k*matSize + j;

                    // retrieve value at A
                    busMaster->Request(0, r_addrA, 0, 1);
                    busMaster->WaitForAcknowledge(0);
                    busMaster->ReadData(dataA);

                    // retrieve value stored at B
                    busMaster->Request(0, r_addrB, 0, 1);
                    busMaster->WaitForAcknowledge(0);
                    busMaster->ReadData(dataB);

                    // retrieve initial value stored at C
                    busMaster->Request(0, r_addrC, 0, 1);
                    busMaster->WaitForAcknowledge(0);
                    busMaster->ReadData(dataC);
                    
                    result = dataC + dataA * dataB;
                    busMaster->Request(0, r_addrC, 1, 1);
                    busMaster->WriteData(result);
                    busMaster->WaitForAcknowledge(0);
                }
            }
        }
    }
}