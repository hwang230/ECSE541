#ifndef SAD_H
#define SAD_H

#include "systemc.h"
#include "simple_mem_if.h"
#include "system.h" // for the variables needed in do_SAD()

class sad: public sc_module{
public:
    // interface with memory
    sc_port<simple_mem_if> memIf;

    SC_HAS_PROCESS(sad);

    // constructor
    sad(sc_module_name name);

    // perform SAD operations
    void do_SAD();
};

#endif