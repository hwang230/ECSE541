#ifndef HW_H
#define HW_H

#include "system.h"
#include "bus_if.h"

class hw: public sc_module{
    public:
    
        sc_port<bus_master_if> busMaster;
        sc_port<bus_minion_if> busMinion;
        SC_HAS_PROCESS(hw);
        hw(sc_module_name name);

        // for hardware computations
        void do_hw();
        void do_listen();

    private:
        unsigned int register_start;
        unsigned int register_status;
        unsigned int register_addrA;
        unsigned int register_addrB;
        unsigned int register_addrC;
        unsigned int register_matSize;
        // for bus sync
        bool req_pending;
        bool write_pending;
        sc_event req_event;
        sc_event write_event;
        unsigned int r_addr;
        unsigned int r_op;
        unsigned int r_len;
        unsigned int write_data;
};

#endif