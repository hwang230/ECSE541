#include "bus.h"

double cycle_time = 6.67; // in ns
bus::bus(sc_module_name name): sc_module(name){
}
// bus master functions
void bus::Request(unsigned int mst_id, unsigned int addr, unsigned int op, 
unsigned int len){
    // set shared variables values and trigger minions
    // Should wait at least two clock cycles
    wait(2*cycle_time, SC_NS);
    r_mst_id = mst_id;
    r_addr = addr;
    r_op = op;
    r_len = len;
    req_pending = true;
    req_event.notify();
}

bool bus::WaitForAcknowledge(unsigned int mst_id){
    // stay waiting until ack signal is sent and that request ID match
    while (!ack_pending || mst_id != r_mst_id){
        wait(ack_event);
    }
    ack_pending = false;
    return true;
}

void bus::ReadData(unsigned int &data){
    // the value is stored in read_data - shared var by master and minion
    // it then gets stored in the variable requested
    while (!read_pending){
        wait(read_event);
    }
    // requires two cycles
    wait(2*cycle_time, SC_NS);
    data = read_data;
    read_pending = false;
    read_receive_event.notify();
    return;
}

void bus::WriteData(unsigned int data){
    // put the data to be written to in shared var write_data
    // so minion can also have access to it
    // requires one cycle
    wait(cycle_time, SC_NS);
    write_data = data;
    write_pending = true;
    write_event.notify();
    return;
}

// bus minion functions
void bus::Listen(unsigned int &req_addr, unsigned int &req_op, unsigned int 
&req_len){
    // minion should standby until request is sent by master
    while (!req_pending) wait(req_event);
    // then use these stored variables to perform the operation 
    // requested by master
    req_pending = false;
    req_addr = r_addr;
    req_op = r_op;
    req_len = r_len;
    return;
}

void bus::Acknowledge(){
    // require one cycle
    wait(cycle_time, SC_NS);
    ack_pending = true; // set ack_pending to true so it does not wait in loop
    ack_event.notify(); // similar to mutex - inform the ack_event to get out
    return;
}

void bus::SendReadData(unsigned int data){   
    // this data represents the data from memory location
    // we store it in read_data so it can be accessed by master bus as well
    while (read_pending) wait(read_receive_event);
    read_data = data;
    read_pending = true;
    read_event.notify();
    return;
}

void bus::ReceiveWriteData(unsigned int &data){
    while (!write_pending) wait(write_event);
    data = write_data;
    write_pending = false;
    return;
}
