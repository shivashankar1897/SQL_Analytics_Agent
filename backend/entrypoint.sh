#!/bin/sh
# Author: Suresh D R | AI Product Developer & Technology Mentor
# Runs FastAPI in the background and Streamlit in the foreground,
# both inside the same container.

uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --workers 1 &

export BACKEND_URL=http://localhost:8000
streamlit run streamlit_app.py --server.port=8501 --server.address=0.0.0.0
