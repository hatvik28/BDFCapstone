#!/usr/bin/env python
from spotbugs1.app import app as flask_app
import os
import sys

# Add the current directory to the Python path
sys.path.insert(0, os.path.abspath('.'))

# Import directly from app directory

if __name__ == "__main__":
    print("Starting Server...")
    flask_app.run(debug=True)
