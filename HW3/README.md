How to build and run all three models:
1. Ensure the folder for each model is placed in the same directory under HW3. 
2. Ensure the systemC library (version 2.3.2) is placed at the same directory as ECSE541.
    - If the systemC folder name does not match systemc-2.3.2, then the file name must be explicitly changed in each Makefile. 
    - Or simply change the Systemc folder name to systemc-2.3.2
3. cd into directory Assignment2
4. Ensure run.sh has permission to execute. If not then run, "chmod +x run.sh" in terminal. 
5. Run "./run.sh" in command line to compile and run the three models. 
6. To run custom inputs, simply enter the arguments in order after "./run.sh"
    - Example: ./run.sh 1000 1200 1400 2 1 
    - The five arguments represent respectively addrC addrA addrC SIZE LOOPS
    - The memory file is preset in run.sh as only 1 memfile is provided

Note: 

Average Result Noted in three runs:
- Untimed:
    -> Simulated for ns.
    -> Wall-clock time: 
- Approximate-timed:
    -> Simulated for ns. 
    -> Wall-clock time: 
- Mixed cycle accurate and approximate-timed:
    -> Simulated for ns. 
    -> Wall-clock time: 
