# Testing Guide for CommandRex

This document provides comprehensive information about testing CommandRex, including how to run tests, write new tests, and understand the testing architecture.

## Quick Start

### Install Test Dependencies

```bash
# Using Poetry (recommended)
poetry install --extras test

# Using pip
pip install -e .[test]

# Install development dependencies
pip install -e .[dev]
```

The `test` extras also install tools like `black` and `ruff` used in CI.

### Run Tests

```bash
# Run all tests
python run_tests.py --all

# Run unit tests only
python run_tests.py --unit

# Run integration tests only
python run_tests.py --integration

# Run with coverage
python run_tests.py --all --coverage

# Run specific test file
python run_tests.py --test tests/unit/test_security.py

# Run with verbose output
python run_tests.py --all --verbose
```

### Using pytest directly

```bash
# Run all tests
pytest tests/

# Run unit tests with coverage
pytest tests/unit --cov=commandrex --cov-report=term-missing

# Run integration tests
pytest tests/integration -m integration

# Run specific test
pytest tests/unit/test_security.py::TestCommandSafetyAnalyzer::test_analyze_command_safe
```

## Test Architecture

### Directory Structure

```
tests/
├── __init__.py
├── conftest.py                    # Shared fixtures (284 lines)
├── unit/                          # Unit tests (488+ tests)
│   ├── __init__.py
│   ├── test_security.py          # Security module tests (99% coverage)
│   ├── test_api_manager.py       # API manager tests (100% coverage)
│   ├── test_command_parser.py    # Command parser tests (91% coverage)
│   ├── test_platform_utils.py    # Platform utilities tests (78% coverage)
│   ├── test_shell_manager.py     # Shell manager tests (100% coverage)
│   ├── test_openai_client.py     # OpenAI client tests (100% coverage)
│   ├── test_settings.py          # Settings tests (99% coverage)
│   ├── test_prompt_builder.py    # Prompt builder tests (100% coverage)
│   ├── test_main.py              # Main CLI tests (68% coverage)
│   └── test_logging.py           # Logging tests (100% coverage)
├── integration/                   # Integration tests (9 tests)
│   ├── __init__.py
│   └── test_basic_workflow.py    # Basic workflow tests
└── e2e/                          # End-to-end tests (25 tests)
    ├── __init__.py
    └── test_cli_commands.py       # CLI command tests (666 lines)
```

### Test Categories

Tests are organized into three main categories:

1. **Unit Tests** (`tests/unit/`): Test individual functions and classes in isolation
2. **Integration Tests** (`tests/integration/`): Test interaction between components
3. **End-to-End Tests** (`tests/e2e/`): Test complete user workflows and CLI commands

### Test Markers

Tests use pytest markers for categorization:

- `@pytest.mark.unit`: Unit tests
- `@pytest.mark.integration`: Integration tests
- `@pytest.mark.e2e`: End-to-end tests
- `@pytest.mark.slow`: Slow-running tests
- `@pytest.mark.network`: Tests requiring network access

## Writing Tests

### Test Naming Convention

- Test files: `test_<module_name>.py`
- Test classes: `Test<ClassName>`
- Test methods: `test_<function_name>_<scenario>_<expected_result>()`

Example:
```python
def test_parse_command_with_quotes_returns_parsed_parts():
    """Test that commands with quotes are parsed correctly."""
    pass
```

### Using Fixtures

The project provides many shared fixtures in `conftest.py`:

```python
def test_api_key_validation(valid_api_key, invalid_api_key):
    """Test API key validation with different key formats."""
    assert api_manager.is_api_key_valid(valid_api_key) is True
    assert api_manager.is_api_key_valid(invalid_api_key) is False
```

### Mocking External Dependencies

Always mock external dependencies:

```python
@patch('keyring.get_password')
def test_get_api_key_from_keyring(mock_get_password, valid_api_key):
    """Test retrieving API key from keyring."""
    mock_get_password.return_value = valid_api_key
    
    result = api_manager.get_api_key()
    assert result == valid_api_key
```

### Testing Async Code

For async functions, use `pytest-asyncio`:

```python
@pytest.mark.asyncio
async def test_async_function():
    """Test async function."""
    result = await some_async_function()
    assert result is not None
```

## Available Fixtures

### API Key Fixtures
- `valid_api_key`: Valid OpenAI API key format
- `invalid_api_key`: Invalid API key format
- `mock_keyring`: Mocked keyring operations

### OpenAI API Fixtures
- `mock_openai_response`: Mock API response
- `mock_dangerous_command_response`: Mock dangerous command response
- `mock_openai_client`: Mocked OpenAI client

### Platform Fixtures
- `mock_windows_platform`: Mock Windows platform detection
- `mock_unix_platform`: Mock Unix platform detection
- `mock_shell_detection`: Mock shell detection

### Command Execution Fixtures
- `mock_successful_command_result`: Mock successful command result
- `mock_failed_command_result`: Mock failed command result
- `mock_shell_manager`: Mocked shell manager

### Test Data Fixtures
- `sample_commands`: Sample commands for testing
- `sample_system_info`: Sample system information
- `temp_dir`: Temporary directory
- `temp_config_file`: Temporary configuration file

## Test Configuration

### pytest Configuration

The `pyproject.toml` file contains pytest configuration:

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = "test_*.py"
python_classes = "Test*"
python_functions = "test_*"
addopts = [
    "--strict-markers",
    "--strict-config",
    "--verbose",
    "--cov=commandrex",
    "--cov-report=term-missing",
    "--cov-report=html:htmlcov",
    "--cov-report=xml",
    "--cov-fail-under=80",
]
markers = [
    "unit: Unit tests",
    "integration: Integration tests",
    "e2e: End-to-end tests",
    "slow: Slow running tests",
    "network: Tests that require network access",
]
asyncio_mode = "auto"
timeout = 300
```

### Coverage Configuration

Coverage is configured to:
- Require 80% minimum coverage
- Generate HTML reports in `htmlcov/`
- Generate XML reports for CI/CD
- Show missing lines in terminal output

## Continuous Integration

### GitHub Actions

The project uses GitHub Actions for CI/CD with the following jobs:

1. **Test Matrix**: Tests across Python 3.10, 3.11, 3.12 on Ubuntu, Windows, macOS
2. **Security Scan**: Runs bandit security analysis
3. **Type Check**: Runs mypy type checking
4. **Coverage**: Generates and uploads coverage reports

### Running CI Locally

You can simulate CI locally:

```bash
# Install dependencies
python run_tests.py --install

# Run linting
python run_tests.py --lint

# Run all tests with coverage
python run_tests.py --all --coverage

# Format code
python run_tests.py --format
```

## Test Development Guidelines

### 1. Test-Driven Development (TDD)

Follow the RED-GREEN-REFACTOR cycle:

1. **RED**: Write a failing test
2. **GREEN**: Write minimal code to make it pass
3. **REFACTOR**: Improve code while keeping tests passing

### 2. Test Independence

- Each test should be independent
- Use fixtures for setup/teardown
- Don't rely on test execution order

### 3. Descriptive Test Names

```python
# Good
def test_parse_command_with_quotes_returns_correct_args():
    pass

# Bad
def test_parse():
    pass
```

### 4. Test One Thing

Each test should verify one specific behavior:

```python
# Good - tests one specific scenario
def test_is_dangerous_flags_rm_rf_as_dangerous():
    parser = CommandParser()
    is_dangerous, reasons = parser.is_dangerous("rm -rf /")
    assert is_dangerous is True
    assert len(reasons) > 0

# Bad - tests multiple things
def test_command_validation():
    # Tests parsing, validation, and danger detection
    pass
```

### 5. Use Parametrized Tests

For testing multiple similar scenarios:

```python
@pytest.mark.parametrize("command,expected_dangerous", [
    ("ls -la", False),
    ("rm -rf /", True),
    ("sudo rm file", True),
])
def test_danger_detection(command, expected_dangerous):
    parser = CommandParser()
    is_dangerous, _ = parser.is_dangerous(command)
    assert is_dangerous == expected_dangerous
```

## Debugging Tests

### Running Tests in Debug Mode

```bash
# Run with pdb on failure
pytest tests/unit/test_security.py --pdb

# Run with verbose output
pytest tests/unit/test_security.py -v -s

# Run specific test with output
pytest tests/unit/test_security.py::TestCommandSafetyAnalyzer::test_analyze_command_safe -v -s
```

### Using Print Statements

```python
def test_something():
    result = some_function()
    print(f"Debug: result = {result}")  # Will show with -s flag
    assert result is not None
```

### IDE Integration

Most IDEs support pytest integration:

- **VS Code**: Use Python Test Explorer
- **PyCharm**: Built-in pytest runner
- **Vim/Neovim**: Use vim-test plugin

## Performance Testing

### Timeout Configuration

Tests have a 300-second timeout configured in `pyproject.toml`. For longer tests:

```python
@pytest.mark.timeout(600)  # 10 minutes
def test_long_running_operation():
    pass
```

### Marking Slow Tests

```python
@pytest.mark.slow
def test_expensive_operation():
    pass
```

Run without slow tests:
```bash
pytest tests/ -m "not slow"
```

## Security Testing

### Testing Security Features

Security tests focus on:
- Command safety analysis
- API key validation
- Input sanitization
- Error handling

### Example Security Test

```python
def test_command_injection_prevention():
    """Test that command injection attempts are detected."""
    dangerous_commands = [
        "ls; rm -rf /",
        "cat file | sh",
        "echo `rm file`"
    ]
    
    analyzer = CommandSafetyAnalyzer()
    for cmd in dangerous_commands:
        result = analyzer.analyze_command(cmd)
        assert result["is_safe"] is False
```

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure CommandRex is installed in development mode
   ```bash
   pip install -e .
   ```

2. **Fixture Not Found**: Check that fixtures are defined in `conftest.py`

3. **Mock Not Working**: Ensure you're patching the right import path

4. **Async Test Failures**: Make sure to use `@pytest.mark.asyncio`

### Getting Help

- Check existing tests for examples
- Review fixture definitions in `conftest.py`
- Run tests with `-v` for verbose output
- Use `--pdb` to debug failing tests

## Contributing Tests

When contributing new tests:

1. Follow the existing patterns and conventions
2. Add appropriate fixtures if needed
3. Update this documentation if adding new test categories
4. Ensure tests pass on all platforms
5. Maintain or improve code coverage

## Test Statistics

Current test coverage and statistics:

- **Total Tests**: 522 tests across all categories
- **Overall Coverage**: 86.89% (exceeds 80% target)
- **Unit Tests**: 488+ tests with high coverage per module
- **Integration Tests**: 9 tests covering cross-component workflows
- **End-to-End Tests**: 25 tests covering complete CLI workflows
- **Test Success Rate**: 100% (all tests passing)

### Coverage by Module

| Module | Coverage | Test Count | Status |
|--------|----------|------------|--------|
| Security | 99% | 50+ tests | ✅ Excellent |
| API Manager | 100% | 40+ tests | ✅ Complete |
| Command Parser | 91% | 60+ tests | ✅ Very Good |
| Platform Utils | 78% | 30+ tests | ✅ Good |
| Shell Manager | 100% | 45+ tests | ✅ Complete |
| OpenAI Client | 100% | 35+ tests | ✅ Complete |
| Settings | 99% | 40+ tests | ✅ Excellent |
| Prompt Builder | 100% | 25+ tests | ✅ Complete |
| Main CLI | 68% | 30+ tests | ⚠️ Acceptable |
| Logging | 100% | 15+ tests | ✅ Complete |

## Future Enhancements

Planned testing improvements:

1. **Performance Tests**: Benchmark critical operations
2. **Mutation Testing**: Verify test quality with mutation testing
3. **Property-Based Testing**: Use Hypothesis for property-based tests
4. **Visual Regression Testing**: For CLI output formatting
5. **Load Testing**: Test with high command volumes