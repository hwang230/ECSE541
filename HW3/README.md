How to build and run all three models:
1. Ensure the folder for each model is placed in the same directory. 
2. Ensure the systemC library (version 2.3.2) is placed in one directory above the folder for each model. 
    - If the systemC folder name does not match systemc-2.3.2, then the file name must be explicitly changed in each Makefile. 
    - Or simply change the Systemc folder name to systemc-2.3.2
3. cd into directory Assignment2
4. Ensure run.sh has permission to execute. If not then run, "chmod +x run.sh" in terminal. 
5. Run "./run.sh" in command line to compile and run the three models. 

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
