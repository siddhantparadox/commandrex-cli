#!/usr/bin/env python3
"""
Test script for the enhanced PromptBuilder class.

This script creates an instance of the PromptBuilder class and
generates a translation prompt for a sample request.
"""

import json
import sys
from commandrex.translator.prompt_builder import PromptBuilder
from commandrex.executor import platform_utils

def main():
    """Test the PromptBuilder class."""
    # Create a PromptBuilder instance
    prompt_builder = PromptBuilder()
    
    # First, test shell detection
    print("=== Shell Detection Test ===")
    shell_info = platform_utils.detect_shell()
    if shell_info:
        shell_name, shell_version, capabilities = shell_info
        print(f"Detected Shell: {shell_name}")
        print(f"Shell Version: {shell_version}")
        print("\nShell Capabilities:")
        for capability, value in capabilities.items():
            print(f"- {capability}: {value}")
    else:
        print("Shell detection failed")
    
    # Test command adaptation
    print("\n=== Command Adaptation Test ===")
    unix_command = "ls -la | grep 'txt'"
    adapted_command = platform_utils.adapt_command_for_shell(unix_command)
    print(f"Original command: {unix_command}")
    print(f"Adapted command: {adapted_command}")
    
    # Sample request
    request = "find large files in my downloads folder"
    
    # Generate a translation prompt
    messages = prompt_builder.build_translation_prompt(request)
    
    # Print the messages
    print("\n=== Translation Prompt ===")
    for i, message in enumerate(messages):
        print(f"\n--- Message {i+1} ({message['role']}) ---")
        print(message['content'][:500] + "..." if len(message['content']) > 500 else message['content'])
    
    # Test explanation prompt
    command = "find ~/Downloads -type f -size +10M -exec ls -lh {} \\; | sort -rh"
    explanation_messages = prompt_builder.build_explanation_prompt(command)
    
    print("\n\n=== Explanation Prompt ===")
    for i, message in enumerate(explanation_messages):
        print(f"\n--- Message {i+1} ({message['role']}) ---")
        print(message['content'][:500] + "..." if len(message['content']) > 500 else message['content'])
    
    # Test safety assessment prompt
    safety_messages = prompt_builder.build_safety_assessment_prompt(command)
    
    print("\n\n=== Safety Assessment Prompt ===")
    for i, message in enumerate(safety_messages):
        print(f"\n--- Message {i+1} ({message['role']}) ---")
        print(message['content'][:500] + "..." if len(message['content']) > 500 else message['content'])
    
    # Test shell-specific examples
    if shell_info:
        print("\n\n=== Shell-Specific Examples ===")
        shell_examples = prompt_builder._get_shell_specific_examples(shell_name)
        print(shell_examples)

if __name__ == "__main__":
    main()
