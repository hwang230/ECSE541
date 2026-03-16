#ifndef MATMUL_H
#define MATMUL_H

#include "systemc.h"
#include "bus_if.h"
#include "system.h"

class matmul: public sc_module{
public:
    // interface with minion as bus master
    sc_port<bus_master_if> busMaster;
    
    SC_HAS_PROCESS(matmul);

    // constructor
    matmul(sc_module_name name);

    // perform matmul operations
    void do_MATMUL();

};

#endif