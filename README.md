# CommandRex 🦖

A natural language interface for terminal commands.

## Description

CommandRex allows you to interact with your terminal using natural language. Simply tell CommandRex what you want to do, and it will translate your request into the appropriate terminal command. It's like having an AI assistant for your command line!

## Features

- **Natural Language Command Translation**: Convert plain English to precise terminal commands
- **Command Explanations**: Get detailed explanations of what commands do and how they work
- **Safety Analysis**: Automatic detection of potentially dangerous commands with warnings
- **Cross-Platform Support**: Works on Windows, macOS, and Linux
- **Interactive Mode**: Real-time command translation and execution with ASCII art welcome screen
- **Educational Breakdowns**: Learn terminal commands through component-by-component explanations
- **Secure API Key Management**: Your OpenAI API key is stored securely in your system's keyring

## Requirements

- Python 3.10 or higher
- OpenAI API key (get one at [https://platform.openai.com/api-keys](https://platform.openai.com/api-keys))
- Internet connection for API communication

## Installation

### From PyPI (Recommended)

```bash
pip install commandrex
```

### From Source

```bash
git clone https://github.com/siddhantparadox/commandrex-cli.git
cd commandrex-cli
pip install -e .
```

### Using Poetry (for Development)

**Prerequisites:** Poetry must be installed first. Install Poetry using one of these methods:

**Linux/macOS/WSL:**
```bash
curl -sSL https://install.python-poetry.org | python3 -
```

**Windows (PowerShell):**
```powershell
(Invoke-WebRequest -Uri https://install.python-poetry.org -UseBasicParsing).Content | py -
```

**Alternative (using pipx):**
```bash
pipx install poetry
```

**Then install CommandRex:**
```bash
git clone https://github.com/siddhantparadox/commandrex-cli.git
cd commandrex-cli
poetry install
```

> **Note:** Poetry is a build and dependency management tool, not a runtime dependency. It should be installed separately on your system before using `poetry install`.

## Usage

CommandRex can be invoked using either `commandrex` or `python -m commandrex` followed by a command (run, translate, explain) and options.

For example:
- `commandrex run` - Start interactive mode
- `commandrex translate "query"` - Translate a natural language query
- `commandrex explain "command"` - Explain a shell command

### Interactive Mode

Start the interactive terminal interface:

```bash
commandrex run
```

This launches CommandRex in interactive mode with a welcome screen displaying "COMMAND REX" in green ASCII art. You can type natural language requests and get immediate command translations.

**Options:**
- `--debug` or `-d`: Enable debug mode with detailed system information
- `--api-key YOUR_KEY`: Use a specific OpenAI API key for this session
- `--model MODEL_NAME`: Specify an OpenAI model (default: gpt-4o-mini)
- `--translate "query"` or `-t "query"`: Directly translate a query without entering interactive mode

**Example:**
```bash
commandrex run --model gpt-4o --debug
```

### Command Translation

Translate natural language to a shell command:

```bash
commandrex translate "list all files in the current directory including hidden ones"
```

**Options:**
- `--execute` or `-e`: Execute the translated command after showing it
- `--api-key YOUR_KEY`: Use a specific OpenAI API key for this translation
- `--model MODEL_NAME`: Specify an OpenAI model (default: gpt-4o-mini)

**Examples:**
```bash
commandrex translate "find all PDF files modified in the last week"
commandrex translate "create a backup of my Documents folder" --execute
```

### Command Explanation

Get a detailed explanation of a shell command:

```bash
commandrex explain "grep -r 'TODO' --include='*.py' ."
```

This will provide:
- A general explanation of what the command does
- Breakdown of each component
- Safety assessment
- Related commands and examples

**Options:**
- `--api-key YOUR_KEY`: Use a specific OpenAI API key for this explanation
- `--model MODEL_NAME`: Specify an OpenAI model (default: gpt-4o-mini)

### Help System

CommandRex features a comprehensive help system with beautiful formatting:

**Main Help:**
```bash
commandrex --help
```
Shows a beautifully formatted overview with:
- Available commands in a table
- Global options in a styled box
- Usage examples with syntax highlighting
- Troubleshooting section with common solutions

**Command-Specific Help:**
```bash
commandrex run --help        # Interactive mode help
commandrex translate --help  # Translation command help
commandrex explain --help    # Explanation command help
```
Each command provides detailed information about its options and usage patterns.

### Global Options

These options work with any command:

- `--version` or `-v`: Show the application version
- `--reset-api-key`: Reset the stored OpenAI API key

**Examples:**
```bash
commandrex --version
commandrex --reset-api-key
```

### First-Time Setup

When you first run CommandRex, it will:

1. Ask for your OpenAI API key (get one at https://platform.openai.com/api-keys)
2. Store this key securely in your system's keyring
3. Detect your shell environment and operating system

The API key setup only happens once; the key is stored securely for future use.

### Example Workflow

**Basic Translation:**
```bash
# Translate a natural language query to a command
commandrex translate "find large files in my Downloads folder"
```

**Translation with Execution:**
```bash
# Translate and execute a command
commandrex translate "create a directory structure for my new project" --execute
```

**Interactive Mode:**
```bash
# Start interactive mode
commandrex run

# In interactive mode:
# 1. Welcome screen displays "COMMAND REX" in green ASCII art
# 2. Type your request and press Enter
# 3. See the translation and explanation
# 4. Choose whether to execute it
# 5. Type 'exit' or press Ctrl+C to quit
```

### Troubleshooting

**API Key Issues:**
```bash
# Reset your API key
commandrex --reset-api-key
```

**Command Accuracy:**
If a translated command doesn't match your intent:
1. Try being more specific in your request
2. Use the interactive mode to refine your query
3. Try a different model with `--model gpt-4o` for potentially better results

**Shell Detection:**
```bash
# Run in debug mode to see detected shell information
commandrex run --debug
```

## Examples

Here are some examples of natural language queries you can use with CommandRex:

- "Show me all running processes"
- "Find all text files containing the word 'important'"
- "Create a backup of my documents folder"
- "Show disk usage for the current directory"
- "Kill the process running on port 3000"
- "Extract the contents of archive.zip to the folder 'extracted'"
- "Show me the last 50 lines of the error log"

## How It Works

CommandRex uses OpenAI's language models to translate your natural language requests into terminal commands. It provides context about your operating system, shell environment, and common command patterns to generate accurate and safe commands.

The application:
1. Analyzes your request
2. Generates an appropriate command
3. Explains what the command does
4. Checks for potential safety issues
5. Executes the command if requested

## Security

CommandRex takes security seriously:

- Your API key is stored securely in your system's keyring
- Commands are analyzed for potential security risks before execution
- Potentially dangerous commands are clearly marked with warnings
- You always have the final say on whether to execute a command
- No data is stored or shared beyond what's needed for API communication

## Testing

CommandRex has a comprehensive test suite with 522 tests achieving 86.89% code coverage. The project follows Test-Driven Development (TDD) practices to ensure code quality and reliability.

### Running Tests

**Run all tests:**
```bash
# Using pytest directly
pytest

# With coverage report
pytest --cov=commandrex --cov-report=term-missing

# Using the test runner script
python run_tests.py
```

**Run specific test categories:**
```bash
# Unit tests only
pytest tests/unit/

# Integration tests only
pytest tests/integration/

# End-to-end tests only
pytest tests/e2e/

# Run tests in parallel (faster)
pytest -n auto
```

**Run specific test files:**
```bash
# Test a specific module
pytest tests/unit/test_security.py

# Test with verbose output
pytest tests/unit/test_api_manager.py -v

# Run a specific test
pytest tests/unit/test_security.py::TestCommandSafetyAnalyzer::test_analyze_command_dangerous_rm_rf
```

### Test Structure

The test suite is organized into three main categories:

```
tests/
├── conftest.py              # Shared test fixtures and configuration
├── unit/                    # Unit tests (488 tests)
│   ├── test_api_manager.py  # API key management tests
│   ├── test_security.py     # Security and safety analysis tests
│   ├── test_main.py         # CLI interface tests
│   ├── test_openai_client.py # OpenAI API integration tests
│   └── ...
├── integration/             # Integration tests (9 tests)
│   └── test_basic_workflow.py # Cross-component workflow tests
└── e2e/                     # End-to-end tests (25 tests)
    └── test_cli_commands.py # Complete CLI command testing
```

### Test Coverage

Current test coverage by module:
- **API Manager**: 100% coverage
- **Security Module**: 99% coverage
- **Settings Module**: 99% coverage
- **Shell Manager**: 100% coverage
- **OpenAI Client**: 100% coverage
- **Prompt Builder**: 100% coverage
- **Logging Utils**: 100% coverage
- **Command Parser**: 91% coverage
- **Platform Utils**: 78% coverage
- **Main CLI**: 68% coverage

### Development Testing

**Prerequisites for testing:**
```bash
# Install development dependencies
pip install -e ".[dev]"

# Or using Poetry
poetry install
```

**Test configuration:**
- Minimum coverage threshold: 80%
- Test timeout: 300 seconds
- Parallel execution supported
- Cross-platform testing (Windows, macOS, Linux)

**Continuous Integration:**
Tests run automatically on:
- Pull requests
- Pushes to main branch
- Multiple Python versions (3.10, 3.11, 3.12)
- Multiple operating systems

**Writing Tests:**
See [`TDD_WORKFLOW.md`](TDD_WORKFLOW.md) for detailed guidelines on:
- Test-driven development practices
- Writing effective unit tests
- Mocking strategies for external dependencies
- Integration testing patterns
- End-to-end testing approaches

**Test Utilities:**
- **Fixtures**: Shared test data and mock objects in `conftest.py`
- **Mocking**: Comprehensive mocking of OpenAI API, file system, and system calls
- **Async Testing**: Full support for testing async/await code patterns
- **CLI Testing**: Specialized testing for Typer-based CLI commands

## Code Quality and Pre-commit Hooks

CommandRex uses pre-commit hooks to maintain code quality and consistency. The project includes automated formatting, linting, and various file checks.

### Setting up Pre-commit

**Install development dependencies:**
```bash
# Using pip
pip install -e ".[dev]"

# Or using Poetry
poetry install --with dev
```

**Install pre-commit hooks:**
```bash
pre-commit install
```

### Pre-commit Hooks

The following hooks run automatically on every commit:

- **Ruff v0.12.4**: Extremely fast Python linting and formatting (with unsafe fixes enabled)
- **Trailing whitespace**: Removes trailing whitespace
- **End of file fixer**: Ensures files end with a newline
- **Merge conflict checker**: Detects merge conflict markers
- **YAML syntax checker**: Validates YAML files
- **TOML syntax checker**: Validates TOML files
- **Large file checker**: Prevents committing large files (max 1MB)

**Note**: This project uses Ruff exclusively for both linting and formatting, eliminating the need for separate Black and isort tools. Ruff provides equivalent functionality with superior performance.

All Python-related hooks are optimized to run only on Python files (`.py`, `.pyi`) for better performance.

### Manual Hook Execution

**Run all hooks on all files:**
```bash
pre-commit run --all-files
```

**Run specific hooks:**
```bash
# Run only ruff linting
pre-commit run ruff-check --all-files

# Run only ruff formatting
pre-commit run ruff-format --all-files

# Run only trailing whitespace fixer
pre-commit run trailing-whitespace --all-files

# Run only YAML checker
pre-commit run check-yaml --all-files

# Run only TOML checker
pre-commit run check-toml --all-files
```

**Update hook versions:**
```bash
pre-commit autoupdate
```

### Editor Integration with Ruff Server

For the best development experience, configure your editor to use the native Ruff language server instead of the older ruff-lsp. The native server offers superior performance and is built directly into Ruff.

**VS Code Setup:**
Add this to your VS Code settings (`.vscode/settings.json` or user settings):
```json
{
    "ruff.nativeServer": "on",
    "ruff.fixAll": true,
    "ruff.organizeImports": true,
    "ruff.showSyntaxErrors": true
}
```

**Neovim Setup (0.11+):**
```lua
vim.lsp.config('ruff', {
  init_options = {
    settings = {
      fixAll = true,
      organizeImports = true,
      showSyntaxErrors = true
    }
  }
})
vim.lsp.enable('ruff')
```

**Neovim Setup (0.10 with nvim-lspconfig):**
```lua
require('lspconfig').ruff.setup({
  init_options = {
    settings = {
      fixAll = true,
      organizeImports = true,
      showSyntaxErrors = true
    }
  }
})
```

**Other Editors:**
Most editors support the Language Server Protocol. Configure your editor to use:
- **Command**: `ruff server`
- **File types**: Python (`.py`, `.pyi`)

**Benefits of Native Ruff Server:**
- **Superior Performance**: Native Rust implementation is significantly faster than ruff-lsp
- **Built-in**: No separate installation required
- **Modern Architecture**: Lock-free data model with continuous event loop
- **Better Integration**: More reliable LSP implementation with real-time diagnostics

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

**Development Setup:**
1. Fork the repository
2. Clone your fork: `git clone https://github.com/YOUR_USERNAME/commandrex-cli.git`
3. Install development dependencies: `pip install -e ".[dev]"`
4. Install pre-commit hooks: `pre-commit install`
5. Run tests to ensure everything works: `pytest`
6. Make your changes following TDD practices
7. Ensure tests pass and coverage remains above 80%
8. Submit a pull request

**Code Quality Requirements:**
- All commits must pass pre-commit hooks (ruff, trailing whitespace, etc.)
- All new code must have corresponding tests
- Maintain or improve test coverage
- Follow existing test patterns and conventions
- Include both unit and integration tests where appropriate

**CI/CD Integration:**
Pre-commit hooks should also be integrated into your CI/CD pipeline to ensure code quality standards are maintained across all contributions. Consider adding a workflow step that runs `pre-commit run --all-files` in your GitHub Actions or other CI systems.

## License

MIT
