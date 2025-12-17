# Red Team Agent - Quick Local Run

## Super Quick Start (30 seconds)

```bash
# 1. Go to redteam agent directory
cd redteam-agent

# 2. Install dependencies
pip install -r requirements.txt

# 3. Set API key
export DEEPSEEK_API_KEY=your-key-here

# 4. Run the agent
python run.py
```

---

## What Happens

The agent will:
1. Connect to DeepSeek API (or OpenAI)
2. Initialize the red team agent
3. Execute: "List the files in the current directory?"
4. Show results in both normal and streaming modes
5. Display the final output

---

## Configuration (Optional)

Create `.env` file in `redteam-agent/` directory:

```bash
# Copy from root
cp ../.env.example .env

# Edit with your settings
CAI_MODEL=deepseek-chat
DEEPSEEK_API_KEY=sk-your-key
REDTEAM_AGENT_MAX_TOKENS=1000
```

---

## Common Issues

### "No API key set"
```bash
export DEEPSEEK_API_KEY=your-key
# or use .env file (see above)
```

### "Module not found"
```bash
pip install -r requirements.txt
```

### "Connection refused"
```bash
# Check API key is valid
# Check internet connection
# Check base URL: DEEPSEEK_BASE_URL=https://api.deepseek.ai/v1/
```

---

## Running Modes

### Normal (Non-Streaming)
```bash
python run.py
```
Waits for complete response.

### Streaming
Already included in `run.py` - shows real-time events.

### Custom Prompt
Edit `redtem_agent.py`:
```python
async def main():
    result = await Runner.run(ctf_agent, "Your custom prompt here")
    print(result.final_output)
```

---

## File Structure

```
redteam-agent/
├── run.py              ← Simple runner script
├── redtem_agent.py     ← Main agent code
├── config.py           ← Configuration
├── requirements.txt    ← Dependencies
├── Dockerfile          ← For Docker
├── README.md           ← Full documentation
└── .env               ← Your secrets (not in git)
```

---

## Docker (Optional)

### Build
```bash
cd redteam-agent
docker build -t redteam-agent -f Dockerfile.local .
```

### Run
```bash
docker run -e DEEPSEEK_API_KEY=your-key redteam-agent
```

---

## Next Steps

1. ✅ Run: `python run.py`
2. ✅ Check output
3. ✅ Modify prompts in `redtem_agent.py`
4. ✅ Add custom tools as needed
5. ✅ Read [README.md](README.md) for full guide

---

## Support

- **Issues?** Check [README.md](README.md) troubleshooting section
- **Want Docker?** See docker instructions above
- **Integration?** Check main [README.md](../README.md)
