#!/bin/bash
# Debug launcher for Mac - captures errors

cd "$(dirname "$0")"

echo "=== Debug Launch ===" > debug_output.log
echo "Date: $(date)" >> debug_output.log
echo "Python: $(which python3)" >> debug_output.log
echo "PWD: $(pwd)" >> debug_output.log
echo "" >> debug_output.log

# Run the app and capture output
echo "Launching app..." >> debug_output.log

if [ -d "dist/ImageProcessorPro.app" ]; then
    # Try to run the binary directly to see errors
    ./dist/ImageProcessorPro.app/Contents/MacOS/ImageProcessorPro 2>&1 | tee -a debug_output.log
else
    echo "App not found!" >> debug_output.log
fi

echo "" >> debug_output.log
echo "=== End Debug ===" >> debug_output.log

# Show the log
cat debug_output.log
