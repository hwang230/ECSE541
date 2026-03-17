#!/bin/bash
# For each file, perform "make" then call "/usr/bin/time -l -h -p ./sad mem_init.txt"

# list of directories
# DIRS=("hw3_golden" "hw3_approximate_timed" "hw3_mixed")
DIRS=("hw3_golden")
INPUT_FILE="mem_init.txt"

echo "Starting Simulation ..."
echo "----------------------------------------"

for dir in "${DIRS[@]}"; do
    if [ -d "$dir" ]; then
        echo "ENTERING: $dir"
        cd "$dir" || exit

        # compile he model
        echo ">>> Compiling..."
        make clean > /dev/null
        make > /dev/null

        # check if make succeeded
        if [ $? -eq 0 ]; then
            echo ">>> Running Simulation ($dir)..."
            echo "----------------------------------------"
            
            # run the model 
            /usr/bin/time -l -h -p ./matmul "$INPUT_FILE" "$@" 
            
            echo "----------------------------------------"
            echo "----------------------------------------"
        else
            echo ">>> ERROR: Compilation failed in $dir"
        fi

        # clean up after running
        make clean > /dev/null 

        # return to parent directory
        cd ..
        echo ""
    else
        echo ">>> WARNING: Directory '$dir' not found. Skipping."
        echo ""
    fi
done

echo "Simulation Complete."