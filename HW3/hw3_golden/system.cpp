#include "systemc.h"
#include <fstream>
#include <string>

#include "system.h"
#include "memory.h"
#include "matmul.h"
using namespace std;


unsigned int inputA, inputB, inputC;
unsigned int matSize, loops;

int sc_main(int argc, char* argv[]) {
    // initialize values for input and output addresses
    inputA = addrA;
    inputB = addrB;
    inputC = addrC;
    matSize = SIZE;
    loops = LOOPS;

    // next, check usage
    if (argc != 2 && argc != 6 && argc !=7) {
        cerr << "Usage: " << argv[0] << " <filename> [[[addrC addrA addrB] size] loops]" << endl;
        return 0;
    } // if

    // set custom addresses
    if (argc >= 6) {
        inputC = stoi(argv[2]);
        inputA = stoi(argv[3]);
        inputB = stoi(argv[4]);
        matSize = stoi(argv[5]);
        if (argc > 6)
            loops = stoi(argv[6]);
    } // if

    // check addresses against memory size
    if (inputC + matSize*matSize > MEMORY_SIZE) {
        cerr << "*** ERROR in main: inputC invalid" << endl;
        return 0;
    } // if

    if (inputA + matSize*matSize > MEMORY_SIZE) {
        cerr << "*** ERROR in main: inputA invalid" << endl;
        return 0;
    } // if

    if (inputB + matSize*matSize > MEMORY_SIZE) {
        cerr << "*** ERROR in main: inputB invalid" << endl;
        return 0;
    }

    /* start of functional MATMUL implementation */
    memory *myMem;
    matmul *myMatmul;
    bus *myBus;

    // this command should be ran with more than 2 args
    if (argc == 1){
        cout << "Usage: ./matmul <memfile>" << endl;
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
    cout << "Final memory state for Matrix C:" << endl;
    myMem->memoryPrint(inputC, inputC + matSize*matSize);

    return 0;
} // main