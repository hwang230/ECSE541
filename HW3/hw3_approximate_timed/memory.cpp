#include "memory.h"

// constructor implementation
memory::memory(sc_module_name name, std::string memfile): sc_module(name){
    // initialize memory using helper function
    memoryInit(memfile);

}

// read function
bool memory::Read(unsigned int addr, unsigned int& data){
    if (isMemoryValid(addr)){
        // case where it is valid
        wait(10, SC_NS);
        data = mem[addr];
        return true;
    } 
    // handle invalid memory outside
    return false;
}

// write function
bool memory::Write(unsigned int addr, unsigned int data){
    if (isMemoryValid(addr)){
        // case where it is valid
        wait(10, SC_NS);
        mem[addr] = data;
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
        cout << mem[i] << " ";
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
            mem[i] = std::stoi(entry);
        }
        else {
            // leave the loop when the file ends
            break;
        }
    } // for

    // if the init file isn't big enough to initialize all memory locations,
    // fill the rest with zeroes
    for (; i<MEM_SIZE; i++)
        mem[i] = 0;

} // memoryInit

// check if addr valid
bool memory::isMemoryValid(unsigned int addr){
    return addr < MEM_SIZE;
}