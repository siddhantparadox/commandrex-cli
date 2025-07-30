"""
Main entry point for CommandRex CLI.

This module provides the command-line interface for CommandRex,
handling command-line arguments and launching the application.
"""

import asyncio
import importlib.metadata
import os
import sys
from typing import Optional, List, Dict, Any

import typer
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

# Import from our own modules
from commandrex.config import api_manager, settings
from commandrex.executor import platform_utils, shell_manager, command_parser
from commandrex.translator import openai_client, prompt_builder
from commandrex.utils import logging, security

# Create Typer app
app = typer.Typer(
    name="commandrex",
    help="A natural language interface for terminal commands",
    add_completion=False,
)

# Set up console for rich output
console = Console()


def get_version() -> str:
    """Get the installed version of CommandRex."""
    try:
        return importlib.metadata.version("commandrex")
    except importlib.metadata.PackageNotFoundError:
        return "0.1.0"  # Default during development


@app.callback(invoke_without_command=True)
def callback(
    ctx: typer.Context,
    version: Optional[bool] = typer.Option(
        None, "--version", "-v", help="Show the application version and exit."
    ),
    reset_api_key: bool = typer.Option(
        False, "--reset-api-key", help="Reset the stored OpenAI API key."
    )
) -> None:
    """CommandRex CLI."""
    # Only process these options if no command was invoked
    if ctx.invoked_subcommand is None:
        if version:
            console.print(f"[bold green]CommandRex CLI Version:[/] {get_version()}")
            raise typer.Exit()
        
        if reset_api_key:
            # Delete the existing API key
            if api_manager.delete_api_key():
                console.print("[bold green]API key deleted successfully.[/]")
            else:
                console.print("[bold red]Failed to delete API key.[/]")
                raise typer.Exit(1)
            
            # Ask if the user wants to set a new API key now
            set_new_key = typer.confirm("Do you want to set a new API key now?", default=True)
            
            if set_new_key:
                # Prompt for new API key
                console.print(
                    Panel(
                        "Please enter your OpenAI API key.\n"
                        "Your API key will be stored securely in your system's keyring.\n"
                        "You can find your API key at: [link]https://platform.openai.com/api-keys[/link]",
                        title="Set New API Key",
                        border_style="green",
                    )
                )
                
                # Get API key from user
                api_key = typer.prompt("Enter your OpenAI API key", hide_input=True)
                
                if not api_manager.is_api_key_valid(api_key):
                    console.print("[bold red]Invalid API key format.[/]")
                    console.print("You will be prompted to enter an API key the next time you run CommandRex.")
                    raise typer.Exit(1)
                
                if api_manager.save_api_key(api_key):
                    console.print("[bold green]New API key saved successfully![/]")
                else:
                    console.print("[bold red]Failed to save new API key.[/]")
                    console.print("You will be prompted to enter an API key the next time you run CommandRex.")
                    raise typer.Exit(1)
            else:
                console.print("You will be prompted to enter an API key the next time you run CommandRex.")
            
            raise typer.Exit()
        
        # If no options were provided, show help
        if not version and not reset_api_key:
            console.print(ctx.get_help())
            raise typer.Exit()


def check_api_key() -> bool:
    """
    Check if the OpenAI API key is available.
    
    Returns:
        bool: True if the API key is available, False otherwise.
    """
    api_key = api_manager.get_api_key()
    if not api_key:
        console.print(
            Panel(
                "[bold]Welcome to CommandRex![/] 🦖\n\n"
                "To get started, you'll need to set up your OpenAI API key.\n"
                "This will allow CommandRex to translate your natural language into terminal commands.",
                title="Welcome",
                border_style="green",
            )
        )
        
        # Ask if the user wants to set up the API key now
        setup_now = typer.confirm("Would you like to set up your API key now?", default=True)
        if setup_now:
            # Prompt for API key
            console.print(
                Panel(
                    "Please enter your OpenAI API key.\n"
                    "Your API key will be stored securely in your system's keyring.\n"
                    "You can find your API key at: [link]https://platform.openai.com/api-keys[/link]",
                    title="Set API Key",
                    border_style="green",
                )
            )
            
            # Get API key from user
            new_api_key = typer.prompt("Enter your OpenAI API key", hide_input=True)
            
            if not api_manager.is_api_key_valid(new_api_key):
                console.print("[bold red]Invalid API key format.[/]")
                return False
            
            if api_manager.save_api_key(new_api_key):
                console.print("[bold green]API key saved successfully![/]")
                return True
            else:
                console.print("[bold red]Failed to save API key.[/]")
                return False
        else:
            console.print(
                Panel(
                    "CommandRex requires an API key to function properly.\n\n"
                    "Your API key is stored securely in your system's keyring and is only used to communicate with OpenAI's API.\n"
                    "This allows CommandRex to translate your natural language into powerful terminal commands, saving you time and effort.\n\n"
                    "Would you like to set up your API key now and unlock the full potential of CommandRex?",
                    title="API Key Required",
                    border_style="yellow",
                )
            )
            
            # Ask again if the user wants to set up the API key
            setup_now_retry = typer.confirm("Set up your API key now?", default=True)
            if setup_now_retry:
                # Prompt for API key
                console.print(
                    Panel(
                        "Please enter your OpenAI API key.\n"
                        "Your API key will be stored securely in your system's keyring.\n"
                        "You can find your API key at: [link]https://platform.openai.com/api-keys[/link]",
                        title="Set API Key",
                        border_style="green",
                    )
                )
                
                # Get API key from user
                new_api_key = typer.prompt("Enter your OpenAI API key", hide_input=True)
                
                if not api_manager.is_api_key_valid(new_api_key):
                    console.print("[bold red]Invalid API key format.[/]")
                    return False
                
                if api_manager.save_api_key(new_api_key):
                    console.print("[bold green]API key saved successfully![/]")
                    return True
                else:
                    console.print("[bold red]Failed to save API key.[/]")
                    return False
            else:
                console.print("[yellow]CommandRex requires an API key to function. Exiting...[/]")
                return False
    
    if not api_manager.is_api_key_valid(api_key):
        console.print(
            Panel(
                "[bold red]Invalid API Key[/]\n\n"
                "The provided OpenAI API key appears to be invalid.",
                title="Invalid API Key",
                border_style="red",
            )
        )
        
        # Ask if the user wants to reset the API key
        reset_key = typer.confirm("Would you like to reset your API key now?", default=True)
        if reset_key:
            # Delete the existing API key
            if api_manager.delete_api_key():
                console.print("[bold green]Invalid API key deleted.[/]")
            
            # Prompt for new API key
            console.print(
                Panel(
                    "Please enter your OpenAI API key.\n"
                    "Your API key will be stored securely in your system's keyring.\n"
                    "You can find your API key at: [link]https://platform.openai.com/api-keys[/link]",
                    title="Set New API Key",
                    border_style="green",
                )
            )
            
            # Get API key from user
            new_api_key = typer.prompt("Enter your OpenAI API key", hide_input=True)
            
            if not api_manager.is_api_key_valid(new_api_key):
                console.print("[bold red]Invalid API key format.[/]")
                return False
            
            if api_manager.save_api_key(new_api_key):
                console.print("[bold green]New API key saved successfully![/]")
                return True
            else:
                console.print("[bold red]Failed to save new API key.[/]")
                return False
        else:
            console.print("Please check your API key and try again.")
            return False
    
    return True



@app.command()
def translate(
    query: List[str] = typer.Argument(
        None, help="Natural language query to translate into a command."
    ),
    execute: bool = typer.Option(
        False, "--execute", "-e", help="Execute the translated command."
    ),
    api_key: Optional[str] = typer.Option(
        None, "--api-key", help="OpenAI API key (overrides stored key)."
    ),
    model: str = typer.Option(
        "gpt-4o-mini", "--model", "-m", help="OpenAI model to use."
    ),
) -> None:
    """
    Translate natural language to a shell command.
    
    Provide your query as arguments, and CommandRex will translate it
    into the appropriate shell command for your system.
    """
    # Join query parts into a single string
    if not query:
        console.print("[bold red]Error:[/] No query provided.")
        console.print("Usage: [bold]commandrex translate \"your query here\"[/]")
        raise typer.Exit(1)
    
    query_text = " ".join(query)
    
    # Use provided API key or get from keyring
    if api_key:
        if not api_manager.is_api_key_valid(api_key):
            console.print("[bold red]Invalid API key format.[/]")
            raise typer.Exit(1)
    else:
        if not check_api_key():
            raise typer.Exit(1)
        api_key = api_manager.get_api_key()
    
    # Create OpenAI client
    client = openai_client.OpenAIClient(api_key=api_key, model=model)
    
    # Create prompt builder
    pb = prompt_builder.PromptBuilder()
    
    # Get system context
    system_context = pb.build_system_context()
    
    # Show thinking animation
    with console.status("[bold green]Thinking...[/]", spinner="dots"):
        try:
            # Run in event loop
            result = asyncio.run(
                client.translate_to_command(query_text, system_context)
            )
        except Exception as e:
            console.print(f"[bold red]Error:[/] {str(e)}")
            raise typer.Exit(1)
    
    # Display the result
    command = result.command
    explanation = result.explanation
    is_dangerous = result.is_dangerous
    
    # Create a panel with the command and explanation
    command_text = Text(command, style="bold white on blue")
    panel_content = f"{command_text}\n\n[bold]Explanation:[/]\n{explanation}"
    
    if is_dangerous:
        panel_title = "⚠️  Command (Potentially Dangerous)"
        panel_style = "red"
    else:
        panel_title = "🦖 Command"
        panel_style = "green"
    
    console.print(
        Panel(
            panel_content,
            title=panel_title,
            border_style=panel_style,
        )
    )
    
    # Show safety assessment if the command is dangerous
    if is_dangerous:
        safety_concerns = result.safety_assessment.get("concerns", [])
        if safety_concerns:
            console.print("\n[bold red]Safety Concerns:[/]")
            for concern in safety_concerns:
                console.print(f"  • {concern}")
    
    # Show command components
    components = result.components
    if components:
        console.print("\n[bold]Command Components:[/]")
        for component in components:
            console.print(f"  • [bold]{component['part']}[/]: {component['description']}")
    
    # Show alternatives if available
    alternatives = getattr(result, 'alternatives', [])
    if alternatives:
        console.print("\n[bold]Alternative Commands:[/]")
        for alt in alternatives:
            console.print(f"  • {alt}")
    
    # Execute the command if requested
    if execute:
        if is_dangerous:
            execute_anyway = typer.confirm(
                "This command is potentially dangerous. Execute anyway?",
                default=False,
            )
            if not execute_anyway:
                console.print("[yellow]Command execution cancelled.[/]")
                return
        
        console.print("\n[bold]Executing command:[/]")
        
        # Create shell manager
        shell_mgr = shell_manager.ShellManager()
        
        # Execute the command
        try:
            # Define callbacks for real-time output
            def stdout_callback(line: str) -> None:
                console.print(line, end="")
            
            def stderr_callback(line: str) -> None:
                console.print(f"[red]{line}[/]", end="")
            
            # Run in event loop
            result, _ = asyncio.run(
                shell_mgr.execute_command_safely(
                    command,
                    stdout_callback=stdout_callback,
                    stderr_callback=stderr_callback,
                    validate=False,  # Skip validation since we've already checked
                )
            )
            
            # Show execution result
            if result.success:
                console.print("\n[bold green]Command executed successfully.[/]")
            else:
                console.print(f"\n[bold red]Command failed with exit code {result.return_code}.[/]")
        
        except Exception as e:
            console.print(f"\n[bold red]Error executing command:[/] {str(e)}")


@app.command()
def explain(
    command: List[str] = typer.Argument(
        None, help="Command to explain."
    ),
    api_key: Optional[str] = typer.Option(
        None, "--api-key", help="OpenAI API key (overrides stored key)."
    ),
    model: str = typer.Option(
        "gpt-4o-mini", "--model", "-m", help="OpenAI model to use."
    ),
) -> None:
    """
    Explain a shell command.
    
    Provide a command, and CommandRex will explain what it does
    and break down its components.
    """
    # Join command parts into a single string
    if not command:
        console.print("[bold red]Error:[/] No command provided.")
        console.print("Usage: [bold]commandrex explain \"ls -la\"[/]")
        raise typer.Exit(1)
    
    command_text = " ".join(command)
    
    # Use provided API key or get from keyring
    if api_key:
        if not api_manager.is_api_key_valid(api_key):
            console.print("[bold red]Invalid API key format.[/]")
            raise typer.Exit(1)
    else:
        if not check_api_key():
            raise typer.Exit(1)
        api_key = api_manager.get_api_key()
    
    # Create OpenAI client
    client = openai_client.OpenAIClient(api_key=api_key, model=model)
    
    # Show thinking animation
    with console.status("[bold green]Analyzing command...[/]", spinner="dots"):
        try:
            # Run in event loop
            result = asyncio.run(
                client.explain_command(command_text)
            )
        except Exception as e:
            console.print(f"[bold red]Error:[/] {str(e)}")
            raise typer.Exit(1)
    
    # Display the result
    explanation = result.get("explanation", "No explanation available.")
    components = result.get("components", [])
    examples = result.get("examples", [])
    related_commands = result.get("related_commands", [])
    
    # Create a panel with the command and explanation
    command_text_display = Text(command_text, style="bold white on blue")
    panel_content = f"{command_text_display}\n\n[bold]Explanation:[/]\n{explanation}"
    
    console.print(
        Panel(
            panel_content,
            title="🦖 Command Explanation",
            border_style="green",
        )
    )
    
    # Show command components
    if components:
        console.print("\n[bold]Command Components:[/]")
        for component in components:
            console.print(f"  • [bold]{component['part']}[/]: {component['description']}")
    
    # Show examples
    if examples:
        console.print("\n[bold]Examples:[/]")
        for example in examples:
            console.print(f"  • {example}")
    
    # Show related commands
    if related_commands:
        console.print("\n[bold]Related Commands:[/]")
        for cmd in related_commands:
            console.print(f"  • {cmd}")
    
    # Show safety assessment
    safety_analyzer = security.CommandSafetyAnalyzer()
    safety_result = safety_analyzer.analyze_command(command_text)
    
    if not safety_result["is_safe"]:
        console.print("\n[bold red]Safety Concerns:[/]")
        for concern in safety_result["concerns"]:
            console.print(f"  • {concern}")
        
        if safety_result["recommendations"]:
            console.print("\n[bold yellow]Recommendations:[/]")
            for rec in safety_result["recommendations"]:
                console.print(f"  • {rec}")


@app.command()
def run(
    query: List[str] = typer.Argument(
        None, help="Natural language query to translate and potentially execute."
    ),
    yes: bool = typer.Option(
        False, "--yes", "-y", help="Skip confirmation prompts and execute commands automatically."
    ),
    debug: bool = typer.Option(
        False, "--debug", "-d", help="Enable debug mode."
    ),
    api_key: Optional[str] = typer.Option(
        None, "--api-key", help="OpenAI API key (overrides stored key)."
    ),
    model: str = typer.Option(
        "gpt-4o-mini", "--model", "-m", help="OpenAI model to use."
    ),
    translate_arg: Optional[str] = typer.Option(
        None, "--translate", "-t", help="Directly translate a natural language query without interactive mode."
    ),
) -> None:
    """
    Start the CommandRex terminal interface.
    
    This launches the interactive terminal UI for CommandRex.
    """
    # Set up signal handlers for clean exit
    import signal
    
    def signal_handler(sig, frame):
        console.print("\n[bold]Exiting CommandRex. Goodbye! 👋[/]")
        sys.exit(0)
    
    # Register the signal handler for SIGINT (Ctrl+C)
    signal.signal(signal.SIGINT, signal_handler)
    
    # Detect if we're running in Git Bash
    shell_info = platform_utils.detect_shell()
    running_in_git_bash = shell_info and shell_info[0] == "bash" and platform_utils.is_windows()
    
    # Handle direct query arguments
    if query:
        query_text = " ".join(query)
        console.print(f"[bold]Translating:[/] {query_text}")
        
        # Debug shell detection
        if debug:
            shell_info = platform_utils.detect_shell()
            console.print(f"\n[bold]Debug - Shell Detection:[/]")
            if shell_info:
                console.print(f"  • Detected shell: {shell_info[0]}")
                console.print(f"  • Shell version: {shell_info[1]}")
                console.print(f"  • Running on Windows: {platform_utils.is_windows()}")
                console.print(f"  • Git Bash detection: {platform_utils.is_windows() and shell_info[0] == 'bash'}")
            else:
                console.print("  • No shell detected")
        
        process_translation(query_text, api_key, model, yes_flag=yes)
        return
    
    # If a direct translation was provided, process it without interactive mode
    if translate_arg:
        console.print(f"[bold]Translating:[/] {translate_arg}")
        
        # Debug shell detection
        if debug:
            shell_info = platform_utils.detect_shell()
            console.print(f"\n[bold]Debug - Shell Detection:[/]")
            if shell_info:
                console.print(f"  • Detected shell: {shell_info[0]}")
                console.print(f"  • Shell version: {shell_info[1]}")
                console.print(f"  • Running on Windows: {platform_utils.is_windows()}")
                console.print(f"  • Git Bash detection: {platform_utils.is_windows() and shell_info[0] == 'bash'}")
            else:
                console.print("  • No shell detected")
        
        process_translation(translate_arg, api_key, model, yes_flag=yes)
        return
    
    # Set debug mode in settings
    settings.settings.set("advanced", "debug_mode", debug)
    
    # Use provided API key or get from keyring
    if api_key:
        if not api_manager.is_api_key_valid(api_key):
            console.print("[bold red]Invalid API key format.[/]")
            raise typer.Exit(1)
    else:
        if not check_api_key():
            raise typer.Exit(1)
    
    # Show welcome message
    console.print(
        Panel(
            "[bold]Welcome to CommandRex![/]\n\n"
            "Use the interactive CLI mode to translate natural language to commands.\n"
            "You can also use the [bold]translate[/] or [bold]explain[/] commands directly.",
            title="🦖 CommandRex",
            border_style="green",
        )
    )
    
    # Only show detailed information in debug mode
    if debug:
        # Display platform information
        platform_info = platform_utils.get_platform_info()
        console.print("\n[bold]System Information:[/]")
        console.print(f"  • OS: {platform_info.get('os_name', 'Unknown')}")
        console.print(f"  • Shell: {platform_info.get('shell_name', 'Unknown')} {platform_info.get('shell_version', '')}")
        console.print(f"  • Python: {platform_info.get('python_version', 'Unknown')}")
        
        console.print("\n[bold]Debug mode:[/] [green]Enabled[/]")
        console.print("[bold]Model:[/] " + model)
        console.print("\nPress CTRL+C to exit")
    
    try:
        # Placeholder for our actual application
        if debug:
            console.print("\n[bold green]🦖 CommandRex is ready![/]")
            console.print("Type your natural language request (or 'exit' to quit):")
        else:
            console.print("\n[bold green]Type your natural language request (or 'exit' to quit):[/]")
        
        # Special instructions for Git Bash users
        if running_in_git_bash:
            console.print("\n[bold yellow]Git Bash detected![/]")
            console.print("Interactive mode may not work properly in Git Bash.")
            console.print("For best results, use the --translate (-t) option:")
            console.print("[bold]python -m commandrex run --translate \"your request here\"[/]")
            console.print("Or use CMD or PowerShell instead.")
            console.print("Press Ctrl+C to exit at any time.")
            
        # Inform user about non-interactive mode option
        console.print("\n[bold]Tip:[/] You can use non-interactive mode with:")
        console.print("[bold]python -m commandrex run -t \"your request here\"[/]")
        
        while True:
            try:
                # Print prompt and flush to ensure it's displayed
                sys.stdout.write("> ")
                sys.stdout.flush()
                
                # Read a line from stdin
                user_input = sys.stdin.readline().strip()
                
                if user_input.lower() in ["exit", "quit"]:
                    break
                
                if not user_input.strip():
                    continue
                
                # Process the translation
                process_translation(user_input, api_key, model, yes_flag=False)
            except KeyboardInterrupt:
                # This will be handled by our signal handler
                pass
            except Exception as e:
                console.print(f"\n[bold red]Error reading input:[/] {str(e)}")
                console.print("Try using the --translate option instead:")
                console.print("[bold]python -m commandrex run -t \"your request here\"[/]")
    
    except Exception as e:
        console.print(f"\n[bold red]Unexpected error:[/] {str(e)}")
        sys.exit(1)


def process_translation(query: str, api_key: Optional[str], model: str, yes_flag: bool = False) -> None:
    """
    Process a natural language query and translate it to a command.
    
    Args:
        query (str): The natural language query
        api_key (Optional[str]): The OpenAI API key (or None to use stored key)
        model (str): The model to use
        yes_flag (bool): Whether to skip confirmation prompts
    """
    # Process the input
    console.print("[bold green]Translating...[/]")
    
    # Create OpenAI client
    client = openai_client.OpenAIClient(api_key=api_key or api_manager.get_api_key(), model=model)
    
    # Create prompt builder
    pb = prompt_builder.PromptBuilder()
    
    # Get system context
    system_context = pb.build_system_context()
    
    # Translate the command
    try:
        # Run in event loop
        result = asyncio.run(
            client.translate_to_command(query, system_context)
        )
        
        # Display the result
        command = result.command
        explanation = result.explanation
        is_dangerous = result.is_dangerous
        
        # Create a panel with the command and explanation
        command_text = Text(command, style="bold white on blue")
        panel_content = f"{command_text}\n\n[bold]Explanation:[/]\n{explanation}"
        
        if is_dangerous:
            panel_title = "⚠️  Command (Potentially Dangerous)"
            panel_style = "red"
        else:
            panel_title = "🦖 Command"
            panel_style = "green"
        
        console.print(
            Panel(
                panel_content,
                title=panel_title,
                border_style=panel_style,
            )
        )
        
        # Show safety assessment if the command is dangerous
        if is_dangerous:
            safety_concerns = result.safety_assessment.get("concerns", [])
            if safety_concerns:
                console.print("\n[bold red]Safety Concerns:[/]")
                for concern in safety_concerns:
                    console.print(f"  • {concern}")
        
        # Show command components
        components = result.components
        if components:
            console.print("\n[bold]Command Components:[/]")
            for component in components:
                console.print(f"  • [bold]{component['part']}[/]: {component['description']}")
        
        # Show alternatives if available
        alternatives = getattr(result, 'alternatives', [])
        if alternatives:
            console.print("\n[bold]Alternative Commands:[/]")
            for alt in alternatives:
                console.print(f"  • {alt}")
        
        # Ask if the user wants to execute the command (unless --yes flag is used)
        if yes_flag:
            execute = True
        else:
            execute = typer.confirm("Execute this command?", default=False)
        
        if execute:
            console.print("\n[bold]Executing command:[/]")
            
            # Create shell manager
            shell_mgr = shell_manager.ShellManager()
            
            # Execute the command
            try:
                # Define callbacks for real-time output
                def stdout_callback(line: str) -> None:
                    console.print(line, end="")
                
                def stderr_callback(line: str) -> None:
                    console.print(f"[red]{line}[/]", end="")
                
                # Run in event loop
                result, _ = asyncio.run(
                    shell_mgr.execute_command_safely(
                        command,
                        stdout_callback=stdout_callback,
                        stderr_callback=stderr_callback,
                        validate=False,  # Skip validation since we've already checked
                    )
                )
                
                # Show execution result
                if result.success:
                    console.print("\n[bold green]Command executed successfully.[/]")
                else:
                    console.print(f"\n[bold red]Command failed with exit code {result.return_code}.[/]")
            
            except Exception as e:
                console.print(f"\n[bold red]Error executing command:[/] {str(e)}")
    
    except Exception as e:
        console.print(f"[bold red]Error during translation:[/] {str(e)}")


if __name__ == "__main__":
    app()
