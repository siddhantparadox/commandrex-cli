# CommandRex 🦖

A natural language interface for terminal commands.

## Description

CommandRex allows you to interact with your terminal using natural language. Simply tell CommandRex what you want to do, and it will translate your request into the appropriate terminal command. It's like having an AI assistant for your command line!

## Features

- **Natural Language Command Translation**: Convert plain English to precise terminal commands
- **Command Explanations**: Get detailed explanations of what commands do and how they work
- **Safety Analysis**: Automatic detection of potentially dangerous commands with warnings
- **Cross-Platform Support**: Works on Windows, macOS, and Linux
- **Interactive Mode**: Real-time command translation and execution
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

### Using Poetry

```bash
git clone https://github.com/siddhantparadox/commandrex-cli.git
cd commandrex-cli
poetry install
```

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

This launches CommandRex in interactive mode, where you can type natural language requests and get immediate command translations.

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

### Help Command

Get help information about CommandRex and its commands:

```bash
commandrex --help
```

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
# 1. Type your request and press Enter
# 2. See the translation and explanation
# 3. Choose whether to execute it
# 4. Type 'exit' or press Ctrl+C to quit
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

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

MIT
