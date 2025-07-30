"""
Basic integration tests for CommandRex workflow.

Tests the integration between different modules in common workflows.
"""

import pytest
from unittest.mock import patch, Mock, AsyncMock

from commandrex.config import api_manager
from commandrex.utils.security import CommandSafetyAnalyzer
from commandrex.executor.command_parser import CommandParser


@pytest.mark.integration
class TestBasicWorkflow:
    """Test basic CommandRex workflows."""

    def test_api_key_and_security_integration(self, valid_api_key, mock_keyring):
        """Test integration between API key management and security."""
        # Setup API key
        mock_keyring['get'].return_value = valid_api_key
        mock_keyring['set'].return_value = None
        
        # Save and retrieve API key
        assert api_manager.save_api_key(valid_api_key) is True
        retrieved_key = api_manager.get_api_key()
        assert retrieved_key == valid_api_key
        
        # Validate API key format
        assert api_manager.is_api_key_valid(retrieved_key) is True
        
        # Test security analysis with valid setup
        analyzer = CommandSafetyAnalyzer()
        result = analyzer.analyze_command("ls -la")
        assert result["is_safe"] is True

    def test_command_parsing_and_security_integration(self):
        """Test integration between command parsing and security analysis."""
        parser = CommandParser()
        analyzer = CommandSafetyAnalyzer()
        
        # Test safe command
        safe_command = "ls -la"
        cmd, args = parser.parse_command(safe_command)
        assert cmd == "ls"
        
        validation = parser.validate_command(safe_command)
        assert validation["is_valid"] is True
        assert validation["is_dangerous"] is False
        
        security_result = analyzer.analyze_command(safe_command)
        assert security_result["is_safe"] is True
        
        # Test dangerous command
        dangerous_command = "rm -rf /"
        cmd, args = parser.parse_command(dangerous_command)
        assert cmd == "rm"
        
        validation = parser.validate_command(dangerous_command)
        assert validation["is_dangerous"] is True
        
        security_result = analyzer.analyze_command(dangerous_command)
        assert security_result["is_safe"] is False

    def test_command_enhancement_and_validation_integration(self):
        """Test integration between command enhancement and validation."""
        parser = CommandParser()
        
        with patch('commandrex.executor.platform_utils.get_platform_info') as mock_info:
            mock_info.return_value = {
                "os_name": "windows",
                "shell_name": "cmd"
            }
            
            # Original Unix command
            original_command = "ls -la"
            
            # Enhance for Windows
            enhanced_command = parser.enhance_command(original_command)
            assert enhanced_command == "dir -la"
            
            # Validate both commands
            original_validation = parser.validate_command(original_command)
            enhanced_validation = parser.validate_command(enhanced_command)
            
            # Both should be valid (though enhanced might have different parsing)
            assert original_validation["is_valid"] is True
            assert enhanced_validation["is_valid"] is True


@pytest.mark.integration
@pytest.mark.slow
class TestErrorHandlingIntegration:
    """Test error handling across integrated components."""

    def test_keyring_failure_handling(self, valid_api_key):
        """Test handling of keyring failures across the system."""
        with patch('keyring.get_password', side_effect=Exception("Keyring error")):
            # Should handle keyring errors gracefully
            with pytest.raises(Exception):
                api_manager.get_api_key()

    def test_invalid_api_key_workflow(self, invalid_api_key, mock_keyring):
        """Test workflow with invalid API key."""
        mock_keyring['get'].return_value = invalid_api_key
        
        # Get invalid key
        retrieved_key = api_manager.get_api_key()
        assert retrieved_key == invalid_api_key
        
        # Validation should fail
        assert api_manager.is_api_key_valid(retrieved_key) is False
        
        # Security analysis should still work
        analyzer = CommandSafetyAnalyzer()
        result = analyzer.analyze_command("ls -la")
        assert result["is_safe"] is True

    def test_malformed_command_handling(self):
        """Test handling of malformed commands across components."""
        parser = CommandParser()
        analyzer = CommandSafetyAnalyzer()
        
        malformed_command = 'rm "unclosed quote'
        
        # Parser should handle gracefully
        cmd, args = parser.parse_command(malformed_command)
        assert cmd == "rm"
        
        # Validation should flag as problematic
        validation = parser.validate_command(malformed_command)
        # May be valid but dangerous, or invalid due to parsing issues
        
        # Security analysis should handle gracefully
        security_result = analyzer.analyze_command(malformed_command)
        assert security_result["is_safe"] is False  # Should be flagged as unsafe


@pytest.mark.integration
class TestConfigurationIntegration:
    """Test configuration-related integrations."""

    def test_api_key_environment_fallback_integration(self, valid_api_key, mock_keyring):
        """Test API key environment fallback in integrated workflow."""
        # No key in keyring
        mock_keyring['get'].return_value = None
        
        with patch.dict('os.environ', {'OPENAI_API_KEY': valid_api_key}):
            # Should get key from environment
            retrieved_key = api_manager.get_api_key()
            assert retrieved_key == valid_api_key
            
            # Should validate correctly
            assert api_manager.is_api_key_valid(retrieved_key) is True
            
            # System should work normally
            analyzer = CommandSafetyAnalyzer()
            result = analyzer.analyze_command("ls -la")
            assert result["is_safe"] is True


@pytest.mark.integration
class TestCrossComponentDataFlow:
    """Test data flow between components."""

    def test_command_analysis_data_flow(self):
        """Test data flow from parsing through security analysis."""
        parser = CommandParser()
        analyzer = CommandSafetyAnalyzer()
        
        test_command = "sudo rm -rf /tmp/test"
        
        # Step 1: Parse command
        cmd, args = parser.parse_command(test_command)
        assert cmd == "sudo"
        assert "rm" in args
        
        # Step 2: Validate command
        validation = parser.validate_command(test_command)
        assert validation["is_dangerous"] is True
        assert validation["needs_confirmation"] is True
        
        # Step 3: Security analysis
        security_result = analyzer.analyze_command(test_command)
        assert security_result["is_safe"] is False
        assert security_result["risk_level"] == "high"
        
        # Step 4: Extract components
        components = parser.extract_command_components(test_command)
        assert len(components) >= 3
        assert any(comp["part"] == "sudo" for comp in components)
        
        # Data should be consistent across components
        assert validation["is_dangerous"] == (not security_result["is_safe"])

    def test_platform_specific_integration(self):
        """Test platform-specific behavior integration."""
        parser = CommandParser()
        
        # Test Windows-specific integration
        with patch('commandrex.executor.platform_utils.get_platform_info') as mock_info:
            mock_info.return_value = {
                "os_name": "windows",
                "shell_name": "powershell"
            }
            
            # Command enhancement
            enhanced = parser.enhance_command("grep pattern file.txt")
            assert "Select-String" in enhanced
            
            # Validation should work with enhanced command
            validation = parser.validate_command(enhanced)
            assert validation["is_valid"] is True
            
            # Components extraction should work
            components = parser.extract_command_components(enhanced)
            assert len(components) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])