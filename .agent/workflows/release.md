---
description: Build, publish, and release instaharvest_v2 package
---

// turbo-all

## Release Workflow

1. Run full test suite:
```bash
python -m pytest tests/ --override-ini="addopts=" -q --no-header
```

2. Build the package:
```bash
python -m build
```

3. Check package:
```bash
twine check dist/*
```

4. Upload to PyPI (requires confirmation):
```bash
twine upload dist/*
```
