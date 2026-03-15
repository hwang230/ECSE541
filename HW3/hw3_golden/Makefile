SYSTEMC = ../../../systemc-2.3.2
CC=g++
CFLAGS=-g3 -std=c++14
IFLAGS=-isystem $(SYSTEMC)/src
LFLAGS=-lsystemc -lm -L$(SYSTEMC)/lib-macosx64
DEPS=system.h memory.h simple_mem_if.h matmul.h bus_if.h bus.h
OBJS=system.o memory.o matmul.o bus.o

%.o: %.cpp $(DEPS)
	$(CC) -c -o $@ $< $(CFLAGS) $(IFLAGS)

sad: $(OBJS)
	$(CC) -o $@ $^ $(CFLAGS) $(LFLAGS)

.PHONY: clean

clean:
	rm -f $(OBJS) sad
