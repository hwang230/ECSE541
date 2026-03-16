#include "systemc.h"
#include <fstream>
#include <string>

#include "system.h"
#include "memory.h"

using namespace std;


unsigned int input1Addr, input2Addr, outputAddr;
unsigned int inputA, inputB, inputC;
unsigned int size, loops;
int sc_main(int argc, char* argv[]) {
    // initialize values for input and output addresses
    input1Addr = INPUT1_ADDR;
    input2Addr = INPUT2_ADDR;
    outputAddr = SAD_OUTPUT_ADDR;

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

    /* start of functional SAD implementation */
    memory *myMem;
    //sad *soSad;

    if (argc == 1){
        cout << "Usage: ./sad <memfile>" << endl;
        return 1;
    } else{
        myMem = new memory("myMem", string(argv[1]));
    }

    //soSad = new sad("soSad");
    //soSad->memIf(*myMem);

    cout << "Initial memory state:" << endl;
    myMem->memoryPrint(outputAddr, outputAddr+NUM_BLOCKS);

    /* end of functional SAD implementation */

    /* run the simulation */
    sc_time startTime = sc_time_stamp();
    sc_start();
    sc_time stopTime = sc_time_stamp();

    cout << "Simulated for " << (stopTime - startTime) << endl;

    // print the output values after they are modified
    cout << "Final memory state:" << endl;
    myMem->memoryPrint(outputAddr, outputAddr+NUM_BLOCKS);

    return 0;
} // main