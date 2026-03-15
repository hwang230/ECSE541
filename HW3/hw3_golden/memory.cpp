#include "memory.h"


// execute function takes care of handshake with master
void memory::execute(){
    // should continuously receive request
    while (true){ 
        unsigned int req_addr, req_op, req_len;
        bus_port->Listen(req_addr, req_op, req_len);
        // assume 0 for read and 1 for write
        if (req_op == 0){
            // read case
            unsigned int data; // what happens on burst transfer?
            for (int i = 0; i < req_len; i++){
                memory::Read(req_addr + i, data);
                bus_port->SendReadData(data);
            }
            bus_port->Acknowledge();

        } else if (req_op == 1){
            // write case
            unsigned int data;
            for (int i = 0; i < req_len; i++){
                bus_port->ReceiveWriteData(data);
                memory::Write(req_addr + i, data);
            }
            bus_port->Acknowledge();
        }
    }
    return;
}

// constructor implementation
memory::memory(sc_module_name name, std::string memfile): sc_module(name){
    // initialize memory using helper function
    memoryInit(memfile);
}

// read function
bool memory::Read(unsigned int addr, unsigned int& data){
    if (isMemoryValid(addr)){
        // case where it is valid
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

