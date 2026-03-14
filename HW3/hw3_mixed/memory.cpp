#include "memory.h"


// rtl operation 
// this goes on every clk cycle
void MEMORY_RTL::rtl(){
    Ack.write(SC_LOGIC_0);
    if (Ren.read() == SC_LOGIC_1){
        // assert Ack signal when Ren asserted 
        DataOut.write(mem[Addr.read()]);
        Ack.write(SC_LOGIC_1);
    } else if (Wen.read() == SC_LOGIC_1){
        // assert Ack signal when Wen asserted
        mem[Addr.read()] = DataIn.read();
        Ack.write(SC_LOGIC_1);
    } 
}

// constructor implementation
memory::memory(sc_module_name name, std::string memfile): sc_module(name){
    //initialize memory using helper function
    memory_rtl = new MEMORY_RTL("memory_rtl", const_cast<char*>(memfile.c_str()));

    // map the signals to ports
    memory_rtl->Clk(s_clk);
    memory_rtl->Ren(s_ren);
    memory_rtl->Wen(s_wen);
    memory_rtl->Addr(s_addr);
    memory_rtl->DataIn(s_datain);
    memory_rtl->DataOut(s_dataout);
    memory_rtl->Ack(s_ack);
    
    // start memory and clock
    SC_THREAD(oscillator);
    memoryInit(memfile);
}

// clock definition 
void memory::oscillator(){
    while(true){
        s_clk.write(SC_LOGIC_0);
        wait(5, SC_NS);
        s_clk.write(SC_LOGIC_1);
        wait(5, SC_NS);
    }
}

// read function
bool memory::Read(unsigned int addr, unsigned int& data){
    if (isMemoryValid(addr)){
        // case where it is valid
        s_addr.write(addr);
        s_ren.write(SC_LOGIC_1); 
        // wait until ack gets rising edge
        wait(s_ack.posedge_event());
        // deassert signals and store data 
        data = s_dataout.read();
        s_ren.write(SC_LOGIC_0); // reset ren signal
        // wait until ack deasserts by rtl
        wait(s_ack.negedge_event());
        return true;
    } 
    // handle invalid memory outside
    return false;
}

// write function
bool memory::Write(unsigned int addr, unsigned int data){
    if (isMemoryValid(addr)){
        // case where it is valid
        s_addr.write(addr);
        s_wen.write(SC_LOGIC_1);
        s_datain.write(data);
        // wait until ack rising edge
        wait(s_ack.posedge_event());
        // deasserts signals and write data
        s_wen.write(SC_LOGIC_0); // reset wen signal
        // wait until ack deasserts by rtl
        wait(s_ack.negedge_event());
        return true;
    }
    // handle invalid memory outside
    return false;
}

// print memory
void memory::memoryPrint(unsigned int start, unsigned int end) {
    // ensure end is valid
    if (end >= MEM_SIZE) {
        end = MEM_SIZE-1;
        cerr << "*** ERROR in memoryPrint: end > MEMORY_SIZE-1" << endl; 
    }

    // print the requested values
    for (unsigned int i=start; i<end; i++) {
        cout << memory_rtl->mem[i] << " ";
    }

    cout << endl;
} // memoryPrint


// intiailize memory
void memory::memoryInit(std::string memfile) {
    // open the memory initialization file
    ifstream memfileStream(memfile);

    std::string entry = "";
    int i = 0;

    // iterate until we run out of memory or the file ends
    for (; i<MEM_SIZE; i++) {
        // get a token, delimited by a space
        if (getline(memfileStream, entry, ' ')) {
            // turn the token into an int and save it
            memory_rtl->mem[i] = std::stoi(entry);
        }
        else {
            // leave the loop when the file ends
            break;
        }
    } // for

    // if the init file isn't big enough to initialize all memory locations,
    // fill the rest with zeroes
    for (; i<MEM_SIZE; i++)
        memory_rtl->mem[i] = 0;

} // memoryInit

// check if addr valid
bool memory::isMemoryValid(unsigned int addr){
    return addr < MEM_SIZE;
}