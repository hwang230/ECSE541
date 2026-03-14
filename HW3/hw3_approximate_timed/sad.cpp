#include "sad.h"


// constructor 
sad::sad(sc_module_name name): sc_module(name){
    SC_THREAD(do_SAD);
} // sadModule::sadModule

// sad function definition
void sad::do_SAD(){
    int i, v;
    unsigned int block;
    unsigned int sad;
    unsigned int first_data, second_data;
    // timing calculation
    int total_wait_time;
    int per_block_time; 
    // worst-case inner loop contains 14 wait statements
    // 2 were excluded as wait already defined inside Read()
    per_block_time = 12*BLOCK_SIZE; 
    // 6 for the number of wait statements excluding those in inner loops
    // should be 7 but Write() already accounted for 1 wait statement
    total_wait_time = (2 + NUM_BLOCKS*(per_block_time + 6))*10;
    wait(total_wait_time, SC_NS);
    // do the work of the algorithm
    for (block=0; block<NUM_BLOCKS; block++) 
    {
        sad = 0;
        for (i=0; i<BLOCK_SIZE; i++) 
        {
            memIf->Read(INPUT1_ADDR+(block*BLOCK_SIZE)+i, first_data);
            memIf->Read(INPUT2_ADDR+(block*BLOCK_SIZE)+i, second_data);
            v = first_data - second_data;
            // v needs to be positive
            if (v < 0) v = -v;
            sad += v;
        }
        memIf->Write(SAD_OUTPUT_ADDR+block, sad);
    }
}