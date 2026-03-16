---
description: Setup development environment for instaharvest_v2
---

// turbo-all

## Development Setup

1. Install dependencies:
```bash
pip install -e ".[dev]"
```

2. Install test dependencies:
```bash
pip install pytest pytest-cov pytest-asyncio
```

3. Verify installation:
```bash
python -c "import instaharvest_v2; print(f'instaharvest_v2 v{instaharvest_v2.__version__}')"
```

4. Run quick test check:
```bash
python -m pytest tests/ --override-ini="addopts=" -q --no-header 2>&1 | Select-Object -Last 3
```
