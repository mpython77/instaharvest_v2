---
description: Run all tests with coverage measurement
---

// turbo-all

## Test Coverage Workflow

1. Run all unit tests with coverage report:
```bash
python -m pytest tests/ --cov=instaharvest_v2 --cov-report=term-missing:skip-covered --override-ini="addopts=" -q --no-header
```

2. Generate HTML coverage report:
```bash
python -m pytest tests/ --cov=instaharvest_v2 --cov-report=html:htmlcov --override-ini="addopts=" -q --no-header
```

3. Show coverage summary only:
```bash
python -m pytest tests/ --cov=instaharvest_v2 --override-ini="addopts=" -q --no-header 2>&1 | Select-Object -Last 5
```

4. Run specific test file:
```bash
python -m pytest tests/<test_file>.py --override-ini="addopts=" -q --tb=short
```

5. Run tests matching pattern:
```bash
python -m pytest tests/ -k "<pattern>" --override-ini="addopts=" -q --tb=short
```
