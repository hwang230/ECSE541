#include "bus.h"

double bus_cycle_time = 6.67;

bus::bus(sc_module_name name): sc_module(name){
    bus_busy = false;
    req_pending = false;
    ack_pending = false;
    read_pending = false;
    write_pending = false;
}
// bus master functions
void bus::Request(unsigned int mst_id, unsigned int addr, unsigned int op, 
unsigned int len){

    while(bus_busy){
        wait(bus_free_event);
    }
    bus_busy = true;
    // 2 cycles for request
    wait(2 * bus_cycle_time, SC_NS);

    // set shared variables values and trigger minions
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

    if(r_op == 1){ // read keeps bus busy, write clears
        bus_busy = false;
        bus_free_event.notify();
    }
    return true;
}

void bus::ReadData(unsigned int &data){
    // the value is stored in read_data - shared var by master and minion
    // it then gets stored in the variable requested
    while (!read_pending){
        wait(read_event);
    }
    // 2 cycles for read data
    wait(2 * bus_cycle_time, SC_NS);

    data = read_data;
    read_pending = false;
    read_receive_event.notify();

    bus_busy = false;
    bus_free_event.notify();

    return;
}

void bus::WriteData(unsigned int data){
    // 1 cycle for write
    wait(1 * bus_cycle_time, SC_NS);
    // put the data to be written to in shared var write_data
    // so minion can also have access to it
    write_data = data;
    write_pending = true;
    write_event.notify();

    return;
}

// bus minion functions
void bus::Listen(unsigned int &req_addr, unsigned int &req_op, unsigned int 
&req_len){

    if(req_pending){ // request pending for other minion
        wait(ack_event);
    }

    // minion should standby until request is sent by master
    while (!req_pending) wait(req_event);
    // then use these stored variables to perform the operation 
    // requested by master
    req_addr = r_addr;
    req_op = r_op;
    req_len = r_len;
    return;
}

void bus::Acknowledge(){
    // 1 cycle for acknoledge
    wait(1 * bus_cycle_time, SC_NS);

    req_pending = false; // only the target minion will set this to false
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
