# Simple Test Suite for VastPy CLI

This directory contains a focused test suite for the VastPy CLI parameter handling functionality.

## Test Files

- `test_simple.py` - Comprehensive tests covering all essential functionality
- `run_tests.py` - Simple test runner script

## Running Tests

```bash
python3 tests/run_tests.py
```

## Test Coverage

The simplified test suite covers all essential functionality with just 3 tests:

1. **Parameter Classification** - Verifies parameters are correctly assigned to query/body based on HTTP method
2. **CLI Integration** - Tests complete flow from CLI arguments to HTTP requests  
3. **Backward Compatibility** - Ensures legacy usage patterns still work

## Key Test Scenarios

- Explicit-only parameters: `vastpy-cli get users --qparam page=1 --qparam limit=10`
- Mixed parameters with file input: `vastpy-cli post users --qparam notify=true --file-input data.json`
- Legacy usage: `vastpy-cli post users name=John email=john@example.com`
- Parameter merging: `x=3 --dparam x=7` → `x=[3,7]`

## HTTP Method Behavior

- **GET/DELETE**: All parameters → query string
- **POST/PATCH/PUT**: Query params → URL, Data params → body  
- **File input**: Takes precedence over other body data