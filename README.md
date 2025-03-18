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

### Interactive Mode

Start the interactive terminal interface:

```bash
python -m commandrex run
```

This launches CommandRex in interactive mode, where you can type natural language requests and see them translated into terminal commands.

For more detailed information:

```bash
python -m commandrex run --debug
```

### Translate a Command

Translate a natural language query to a shell command:

```bash
python -m commandrex translate "list all files in the current directory including hidden ones"
```

Add the `--execute` flag to automatically execute the translated command:

```bash
python -m commandrex translate "create a new directory called projects" --execute
```

### Explain a Command

Get a detailed explanation of a shell command:

```bash
python -m commandrex explain "grep -r 'TODO' --include='*.py' ."
```

This will provide:
- A general explanation of what the command does
- Breakdown of each component
- Safety assessment
- Related commands and examples

### API Key Management

Reset your stored API key:

```bash
python -m commandrex --reset-api-key
```

### Other Options

View version information:

```bash
python -m commandrex --version
```

Use a different OpenAI model:

```bash
python -m commandrex run --model gpt-4o
```

Enable debug mode:

```bash
python -m commandrex run --debug
```

See help:

```bash
python -m commandrex run --help
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