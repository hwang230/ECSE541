#ifndef MEMORY_H
#define MEMORY_H

#include "systemc.h"
#include "system.h"
#include "simple_mem_if.h"
#include <iostream>
#include <fstream>
#include <string>

#define MEM_SIZE MEMORY_SIZE

class MEMORY_RTL: public sc_module {
public:
    sc_in<sc_logic> Clk;
    sc_in<sc_logic> Ren, Wen;
    sc_in<int> Addr;
    sc_in<int> DataIn;
    sc_out<int> DataOut;
    sc_out<sc_logic> Ack;

    unsigned int mem[MEM_SIZE];

    SC_HAS_PROCESS(MEMORY_RTL);

    MEMORY_RTL(sc_module_name name, char* memInitFilename) : sc_module(name) {
        SC_METHOD(rtl);
        sensitive << Clk.pos();
    }

    void rtl();
};

class memory: public sc_module, public simple_mem_if { 
public: 
    // constructor 
    memory(sc_module_name name, std::string memfile); 
    // declaration of simple_mem_if functions 
    virtual bool Read(unsigned int addr, unsigned int& data); 
    virtual bool Write(unsigned int addr, unsigned int data); 
    SC_HAS_PROCESS(memory);
    // helper function
    void memoryPrint(unsigned int start, unsigned int end);
  
private: 
    // array used for storing data 
    unsigned int mem[MEM_SIZE]; 
    // helper function
    void memoryInit(std::string memfile);
    bool isMemoryValid(unsigned int addr);

    // for mixed cycle accurate and approximate timed
    sc_signal<sc_logic> s_clk;
    sc_signal<sc_logic> s_ren, s_wen;
    sc_signal<int> s_addr;
    sc_signal<int> s_datain;
    sc_signal<int> s_dataout;
    sc_signal<sc_logic> s_ack;
    
    MEMORY_RTL *memory_rtl;
    void oscillator();
};



#endif