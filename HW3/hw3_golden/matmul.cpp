#include "matmul.h"

// constructor
matmul::matmul(sc_module_name name): sc_module(name){
    SC_THREAD(do_MATMUL);
}

void matmul::do_MATMUL(){
    
}