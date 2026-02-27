#!/bin/bash
# Run script for PramanaGST local development
echo "Starting PramanaGST local server..."
uvicorn backend.api.main:app --reload
