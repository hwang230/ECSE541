#ifndef MEMORY_H
#define MEMORY_H

#include "systemc.h"
#include "system.h"
#include "simple_mem_if.h"
#include <iostream>
#include <fstream>
#include <string>

#define MEM_SIZE MEMORY_SIZE

class memory: public sc_module, public simple_mem_if { 
public: 
    // constructor 
    memory(sc_module_name name, std::string memfile); 
  
    // declaration of simple_mem_if functions 
    virtual bool Read(unsigned int addr, unsigned int& data); 
    virtual bool Write(unsigned int addr, unsigned int data); 
    
    // helper function
    void memoryPrint(unsigned int start, unsigned int end);
  
private: 
    // array used for storing data 
    unsigned int mem[MEM_SIZE]; 
    // helper function
    void memoryInit(std::string memfile);
    bool isMemoryValid(unsigned int addr);
};

#endif