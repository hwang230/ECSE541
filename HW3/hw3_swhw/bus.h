#include "bus_if.h"

class bus : public sc_module, public bus_master_if, public bus_minion_if
{
  public:
    // declaration of bus_master_if functions
    bus(sc_module_name name);
    virtual void Request(unsigned int mst_id, unsigned int addr, unsigned int op, 
    unsigned int len); 
    virtual bool WaitForAcknowledge(unsigned int mst_id); 
    virtual void ReadData(unsigned int &data); 
    virtual void WriteData(unsigned int data); 
    // declaration of bus_minion_if functions
    virtual void Listen(unsigned int &req_addr, unsigned int &req_op, unsigned int 
    &req_len); 
    virtual void Acknowledge();  
    virtual void SendReadData(unsigned int data); 
    virtual void ReceiveWriteData(unsigned int &data); 


  private:
    // internal state for master-slave communication
    unsigned int r_mst_id;
    unsigned int r_addr;
    unsigned int r_op;
    unsigned int r_len;
    unsigned int write_data;
    unsigned int read_data;
    bool req_pending = false; // to inform that req is sent but not yet treated
    bool ack_pending = false; // to inform that ack is sent but not yet treated
    sc_event req_event; // to inform that req is valid
    sc_event ack_event; // to inform that ack is valid
    bool read_pending = false; // to wait until data is here 
    sc_event read_event; // to inform master that data is ready
    bool write_pending = false; // to stop minion from processing before data arrives
    sc_event write_event; // to inform that data is in the shared var
    sc_event read_receive_event; // to ensure master has consumed before minion fetches new word
};