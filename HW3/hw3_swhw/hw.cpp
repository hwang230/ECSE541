#include "hw.h"

double hw_cycle_time = 6.67; // 150MHz

hw::hw(sc_module_name name) : sc_module(name){

    register_start = 0;
    register_status = 0;
    req_pending = false;
    write_pending = false;
    SC_THREAD(do_hw);
    SC_THREAD(do_listen);
}

void hw::do_hw(){

    while(true){ // keep hardware awake

        while(register_start == 0){ // wait for sw activation
            wait(hw_cycle_time, SC_NS);
        }

        // hw start
        register_status = 0; // this means busy
        unsigned int result;
        unsigned int dataA, dataB, dataC;

        // hw does the "k" loop
        for(unsigned int k = 0; k < register_matSize; k++){

            unsigned int r_addrA = register_addrA + k;
            unsigned int r_addrB = register_addrB + (k * register_matSize);
            
            // retrieve value at A
            busMaster->Request(1, r_addrA, 0, 1);
            busMaster->WaitForAcknowledge(1);
            busMaster->ReadData(dataA);

            // retrieve value stored at B
            busMaster->Request(1, r_addrB, 0, 1);
            busMaster->WaitForAcknowledge(1);
            busMaster->ReadData(dataB);

            // retrieve initial value stored at C
            busMaster->Request(1, register_addrC, 0, 1);
            busMaster->WaitForAcknowledge(1);
            busMaster->ReadData(dataC);

            // compute result
            result = dataC + dataA * dataB;
            // write result to C
            busMaster->Request(1, register_addrC, 1, 1);
            busMaster->WriteData(result);
            busMaster->WaitForAcknowledge(1);
        }

        register_start = 0; // reset start
        register_status = 1; // done work so sw can continue loop

    }

}

void hw::do_listen(){
    while(true){

        unsigned int req_addr, req_op, req_len;

        busMinion->Listen(req_addr, req_op, req_len); // sw command
        if (req_addr >= 1024) continue; // for hw only

        if(req_op == 0){ // read
            unsigned int data = 0;
            if(req_addr == 4){
                data = register_status; // give status to sw
            }
            busMinion->SendReadData(data);
            busMinion->Acknowledge();
        }
        else if(req_op == 1){ // write
            unsigned int data = 0;
            busMinion->ReceiveWriteData(data);

            // address decoding to write to
            if(req_addr == 0){
                register_start = data;

            }
            else if(req_addr == 8){
                register_addrC = data;
            }
            else if(req_addr == 12){
                register_addrA = data;
            }
            else if(req_addr == 16){
                register_addrB = data;
            }
            else if(req_addr == 20){
                register_matSize = data;
            }

            busMinion->Acknowledge();
        }
    }
}