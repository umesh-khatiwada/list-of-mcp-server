uv run server.py —server_type=sse

python server.py --server_type=sse

python3 -m venv myenv

source myenv/bin/activate

uvicorn server:app --reload --host 0.0.0.0 --port 8000
