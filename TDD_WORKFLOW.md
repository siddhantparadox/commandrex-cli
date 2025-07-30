# Test-Driven Development (TDD) Workflow for CommandRex CLI

This document outlines the comprehensive TDD workflow implemented for CommandRex CLI, providing guidelines for maintaining and extending the test suite.

## 🎯 TDD Philosophy

CommandRex CLI follows the **RED-GREEN-REFACTOR** cycle:

1. **RED**: Write a failing test that describes the desired functionality
2. **GREEN**: Write the minimal code to make the test pass
3. **REFACTOR**: Improve the code while keeping tests green

## 📊 Current Test Coverage

### Overall Statistics
- **Total Coverage**: 86.36% (Target: 80% ✅)
- **Total Tests**: 497 tests
- **Test Categories**:
  - Unit Tests: 488 tests
  - Integration Tests: 9 tests
  - End-to-End Tests: 50+ tests

### Module Coverage Breakdown
```
commandrex/config/api_manager.py      100% (58 tests)
commandrex/executor/shell_manager.py  100% (33 tests)
commandrex/translator/openai_client.py 100% (22 tests)
commandrex/translator/prompt_builder.py 100% (57 tests)
commandrex/utils/logging.py           100% (43 tests)
commandrex/config/settings.py         99% (42 tests)
commandrex/utils/security.py          99% (60 tests)
commandrex/executor/command_parser.py 91% (75 tests)
commandrex/executor/platform_utils.py 78% (78 tests)
commandrex/main.py                     64% (35 tests)
```

## 🏗️ Test Structure

### Directory Organization
```
tests/
├── conftest.py              # Shared fixtures and utilities
├── unit/                    # Unit tests for individual modules
│   ├── test_api_manager.py
│   ├── test_command_parser.py
│   ├── test_logging.py
│   ├── test_main.py
│   ├── test_openai_client.py
│   ├── test_platform_utils.py
│   ├── test_prompt_builder.py
│   ├── test_security.py
│   ├── test_settings.py
│   └── test_shell_manager.py
├── integration/             # Integration tests for workflows
│   └── test_basic_workflow.py
└── e2e/                     # End-to-end CLI tests
    └── test_cli_commands.py
```

### Test Categories

#### 1. Unit Tests
- **Purpose**: Test individual functions and classes in isolation
- **Scope**: Single module or class
- **Mocking**: Heavy use of mocks for external dependencies
- **Examples**: API key validation, command parsing, security analysis

#### 2. Integration Tests
- **Purpose**: Test interactions between multiple components
- **Scope**: Cross-module workflows
- **Mocking**: Minimal, focuses on real interactions
- **Examples**: API key + security integration, command parsing + platform detection

#### 3. End-to-End Tests
- **Purpose**: Test complete CLI workflows from user perspective
- **Scope**: Full application behavior
- **Mocking**: External services only (OpenAI API, system calls)
- **Examples**: Complete translate/explain/run command workflows

## 🔧 Testing Tools and Configuration

### Core Testing Stack
- **pytest**: Test framework and runner
- **pytest-cov**: Coverage reporting
- **pytest-mock**: Enhanced mocking capabilities
- **pytest-asyncio**: Async test support
- **pytest-xdist**: Parallel test execution
- **pytest-timeout**: Test timeout management

### Configuration (`pyproject.toml`)
```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
addopts = [
    "--cov=commandrex",
    "--cov-report=term-missing",
    "--cov-report=html",
    "--cov-report=xml",
    "--cov-fail-under=80",
    "--strict-markers",
    "--disable-warnings",
    "-v"
]
markers = [
    "slow: marks tests as slow",
    "integration: marks tests as integration tests",
    "e2e: marks tests as end-to-end tests",
    "unit: marks tests as unit tests"
]
```

## 🧪 Testing Patterns and Best Practices

### 1. Test Organization Pattern
```python
class TestModuleName:
    """Test cases for ModuleName functionality."""
    
    def setup_method(self):
        """Set up test fixtures before each test."""
        pass
    
    def teardown_method(self):
        """Clean up after each test."""
        pass
    
    def test_specific_functionality(self):
        """Test specific functionality with descriptive name."""
        # Arrange
        # Act
        # Assert
        pass
```

### 2. Mocking Strategies

#### External API Mocking
```python
@patch('commandrex.translator.openai_client.OpenAI')
def test_openai_integration(self, mock_openai):
    """Test OpenAI API integration with proper mocking."""
    mock_client = Mock()
    mock_openai.return_value = mock_client
    
    # Configure mock response
    mock_response = Mock()
    mock_response.choices[0].message.content = '{"command": "ls -la"}'
    mock_client.chat.completions.create.return_value = mock_response
    
    # Test the functionality
    client = OpenAIClient("test-key")
    result = client.translate_to_command("list files")
    
    assert result.command == "ls -la"
```

#### System Call Mocking
```python
@patch('subprocess.run')
def test_shell_execution(self, mock_run):
    """Test shell command execution with mocked subprocess."""
    mock_run.return_value = Mock(
        returncode=0,
        stdout="file1.txt\nfile2.txt",
        stderr=""
    )
    
    manager = ShellManager()
    result = manager.execute_command("ls")
    
    assert result.success is True
    assert "file1.txt" in result.stdout
```

### 3. Fixture Usage

#### Shared Fixtures (`conftest.py`)
```python
@pytest.fixture
def mock_api_key():
    """Provide a valid test API key."""
    return "sk-test123456789012345678901234567890123456789012"

@pytest.fixture
def mock_openai_client():
    """Provide a mocked OpenAI client."""
    with patch('commandrex.translator.openai_client.OpenAI') as mock:
        yield mock

@pytest.fixture
def temp_config_dir():
    """Provide a temporary configuration directory."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)
```

### 4. Parameterized Testing
```python
@pytest.mark.parametrize("command,expected_danger", [
    ("ls -la", False),
    ("rm -rf /", True),
    ("sudo rm file", True),
    ("echo hello", False),
])
def test_command_danger_detection(self, command, expected_danger):
    """Test danger detection for various commands."""
    analyzer = CommandSafetyAnalyzer()
    result = analyzer.analyze_command(command)
    assert result.is_dangerous == expected_danger
```

## 🚀 Running Tests

### Basic Test Execution
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=commandrex

# Run specific test file
pytest tests/unit/test_api_manager.py

# Run specific test class
pytest tests/unit/test_api_manager.py::TestGetApiKey

# Run specific test method
pytest tests/unit/test_api_manager.py::TestGetApiKey::test_get_api_key_from_keyring
```

### Advanced Test Execution
```bash
# Run tests in parallel
pytest -n auto

# Run only fast tests (exclude slow markers)
pytest -m "not slow"

# Run integration tests only
pytest -m integration

# Run with verbose output
pytest -v

# Run with debugging on first failure
pytest --pdb

# Generate HTML coverage report
pytest --cov=commandrex --cov-report=html
```

### CI/CD Integration
Tests run automatically on:
- Every push to main branch
- Every pull request
- Scheduled daily runs

## 📝 Writing New Tests

### 1. Before Writing Code (TDD Approach)
```python
def test_new_feature_should_work():
    """Test that new feature works as expected."""
    # This test should FAIL initially (RED)
    result = new_feature("input")
    assert result == "expected_output"
```

### 2. Implement Minimal Code
```python
def new_feature(input_data):
    """Implement minimal code to make test pass."""
    # GREEN: Make the test pass with minimal implementation
    return "expected_output"
```

### 3. Refactor and Add Edge Cases
```python
def test_new_feature_edge_cases():
    """Test edge cases for new feature."""
    # Add comprehensive test cases
    assert new_feature("") == ""
    assert new_feature(None) is None
    with pytest.raises(ValueError):
        new_feature("invalid_input")
```

### Test Naming Conventions
- Use descriptive names: `test_api_key_validation_with_invalid_format`
- Follow pattern: `test_[what]_[condition]_[expected_result]`
- Group related tests in classes: `TestApiKeyValidation`

### Test Documentation
```python
def test_complex_functionality(self):
    """
    Test complex functionality with multiple scenarios.
    
    This test verifies that:
    1. Input validation works correctly
    2. Processing handles edge cases
    3. Output format matches expectations
    4. Error conditions are handled gracefully
    """
    # Test implementation
```

## 🔍 Debugging Tests

### Common Issues and Solutions

#### 1. Mock Not Working
```python
# Problem: Mock not being applied
@patch('module.function')  # Wrong module path

# Solution: Use correct import path
@patch('commandrex.config.api_manager.keyring.get_password')
```

#### 2. Async Test Issues
```python
# Problem: Async function not awaited
def test_async_function():
    result = async_function()  # Missing await

# Solution: Use pytest-asyncio
@pytest.mark.asyncio
async def test_async_function():
    result = await async_function()
```

#### 3. File Permission Errors (Windows)
```python
# Problem: File locked by test
def test_file_operations():
    with open("test.log", "w") as f:
        f.write("test")
    # File still locked

# Solution: Proper cleanup
def test_file_operations():
    try:
        with open("test.log", "w") as f:
            f.write("test")
    finally:
        # Ensure file is closed and cleaned up
        if os.path.exists("test.log"):
            os.remove("test.log")
```

### Debugging Commands
```bash
# Run single test with debugging
pytest tests/unit/test_api_manager.py::test_specific -v -s

# Show print statements
pytest -s

# Drop into debugger on failure
pytest --pdb

# Show local variables on failure
pytest --tb=long

# Run with coverage and show missing lines
pytest --cov=commandrex --cov-report=term-missing
```

## 📈 Maintaining Test Quality

### Code Coverage Goals
- **Minimum**: 80% overall coverage
- **Target**: 90%+ for critical modules
- **New Code**: 100% coverage required

### Test Quality Metrics
1. **Test Isolation**: Each test should be independent
2. **Fast Execution**: Unit tests < 1s, integration tests < 10s
3. **Reliable**: Tests should not be flaky
4. **Maintainable**: Clear, readable test code
5. **Comprehensive**: Cover happy path, edge cases, and error conditions

### Regular Maintenance Tasks
- **Weekly**: Review test coverage reports
- **Monthly**: Update test dependencies
- **Quarterly**: Refactor slow or flaky tests
- **Per Release**: Add integration tests for new features

## 🔄 Continuous Improvement

### Adding New Test Categories
1. **Performance Tests**: For benchmarking critical paths
2. **Security Tests**: For vulnerability scanning
3. **Compatibility Tests**: For different Python versions
4. **Load Tests**: For stress testing CLI operations

### Test Automation Enhancements
- **Mutation Testing**: Verify test quality with mutmut
- **Property-Based Testing**: Use hypothesis for edge case discovery
- **Visual Testing**: Screenshot comparison for CLI output
- **Contract Testing**: API contract validation

## 📚 Resources and References

### Documentation
- [pytest Documentation](https://docs.pytest.org/)
- [pytest-cov Documentation](https://pytest-cov.readthedocs.io/)
- [unittest.mock Documentation](https://docs.python.org/3/library/unittest.mock.html)

### Best Practices
- [Testing Best Practices](https://docs.python-guide.org/writing/tests/)
- [TDD Guidelines](https://testdriven.io/test-driven-development/)
- [Mock Object Patterns](https://martinfowler.com/articles/mocksArentStubs.html)

### CommandRex-Specific Guidelines
- Always mock external APIs (OpenAI, keyring)
- Use temporary directories for file operations
- Test cross-platform compatibility where applicable
- Maintain high coverage for security-critical code
- Document complex test scenarios

---

This TDD workflow ensures CommandRex CLI maintains high quality, reliability, and maintainability through comprehensive testing practices.