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