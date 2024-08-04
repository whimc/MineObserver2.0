# WHIMC-Photographer Client

**This can currently only be ran on Windows machines!**

The client will run `photographer.py`. This script is responsible for taking screenshots whenever the server requests.
It connects to the server running `WHIMC-Photographer` via a WebSocket to communicate.
The server will req

## Setup

```powershell
python -m venv venv
./venv/Scripts/activate
pip install -r requirements.txt
```

## Configure
```
python photographer.py --host <minecraft server ip> --port <port from plugin config> --api-version <1 | 2>
```