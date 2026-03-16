#include "systemc.h"
#include <fstream>
#include <string>

#include "system.h"
#include "memory.h"
#include "matmul.h"
using namespace std;


unsigned int input1Addr, input2Addr, outputAddr;
unsigned int inputA, inputB, inputC;
unsigned int matSize, loops;

int sc_main(int argc, char* argv[]) {
    // initialize values for input and output addresses
    input1Addr = INPUT1_ADDR;
    input2Addr = INPUT2_ADDR;
    outputAddr = SAD_OUTPUT_ADDR;
    inputA = addrA;
    inputB = addrB;
    inputC = addrC;
    matSize = SIZE;
    loops = LOOPS;

    // next, check usage
    if (argc != 2 && argc != 4 && argc !=5) {
        cerr << "Usage: " << argv[0] << " <filename> [intput1Addr input2Addr [outputAddr]]" << endl;
        return 0;
    } // if

    // set custom addresses
    if (argc >= 4) {
        input1Addr = stoi(argv[2]);
        input2Addr = stoi(argv[3]);

        if (argc > 4)
            outputAddr = stoi(argv[4]);
    } // if

    // check addresses against memory size
    if (input1Addr + NUM_BLOCKS*BLOCK_SIZE > MEMORY_SIZE) {
        cerr << "*** ERROR in main: input1Addr invalid" << endl;
        return 0;
    } // if

    if (input2Addr + NUM_BLOCKS*BLOCK_SIZE > MEMORY_SIZE) {
        cerr << "*** ERROR in main: input2Addr invalid" << endl;
        return 0;
    } // if

    if (outputAddr + NUM_BLOCKS > MEMORY_SIZE) {
        cerr << "*** ERROR in main: outputAddr invalid" << endl;
        return 0;
    }

    /* start of functional MATMUL implementation */
    memory *myMem;
    matmul *myMatmul;
    bus *myBus;

    if (argc == 1){
        cout << "Usage: ./sad <memfile>" << endl;
        return 1;
    } else{
        myMem = new memory("myMem", string(argv[1]));
    }
    myMatmul = new matmul("myMatmul");
    myBus = new bus("myBus");

    // connect the modules together
    myMatmul->busMaster(*myBus);
    myMem->bus_port(*myBus);

    cout << "Initial memory state:" << endl;
    cout << "Matrix A state:" << endl;
    myMem->memoryPrint(inputA, inputA + matSize*matSize);
    cout << "Matrix B state:" << endl;
    myMem->memoryPrint(inputB, inputB + matSize*matSize);
    cout << "Matrix C state:" << endl;
    myMem->memoryPrint(inputC, inputC + matSize*matSize);

    /* end of functional MATMUL implementation */

    /* run the simulation */
    sc_time startTime = sc_time_stamp();
    sc_start();
    sc_time stopTime = sc_time_stamp();

    cout << "Simulated for " << (stopTime - startTime) << endl;

    // print the output values after they are modified
    cout << "Final memory state:" << endl;
    myMem->memoryPrint(inputC, inputC + matSize*matSize);

    return 0;
} // main