"""
Unit tests for commandrex.config.api_manager module.

Tests API key management functionality including keyring storage,
environment variable fallback, and validation.
"""

import os
import pytest
from unittest.mock import patch, Mock

import keyring
from keyring.errors import PasswordDeleteError

from commandrex.config import api_manager


class TestGetApiKey:
    """Test cases for get_api_key function."""

    def test_get_api_key_from_keyring(self, mock_keyring, valid_api_key):
        """Test retrieving API key from keyring."""
        mock_keyring['get'].return_value = valid_api_key
        
        result = api_manager.get_api_key()
        
        assert result == valid_api_key
        mock_keyring['get'].assert_called_once_with(
            api_manager.SERVICE_NAME, 
            api_manager.API_KEY_NAME
        )

    def test_get_api_key_from_environment(self, mock_keyring, valid_api_key):
        """Test retrieving API key from environment variable when keyring is empty."""
        mock_keyring['get'].return_value = None
        
        with patch.dict(os.environ, {api_manager.ENV_VAR_NAME: valid_api_key}):
            result = api_manager.get_api_key()
        
        assert result == valid_api_key
        mock_keyring['get'].assert_called_once()

    def test_get_api_key_none_when_not_found(self, mock_keyring):
        """Test that None is returned when API key is not found anywhere."""
        mock_keyring['get'].return_value = None
        
        with patch.dict(os.environ, {}, clear=True):
            result = api_manager.get_api_key()
        
        assert result is None

    def test_get_api_key_prefers_keyring_over_env(self, mock_keyring, valid_api_key):
        """Test that keyring is preferred over environment variable."""
        keyring_key = "sk-keyring" + "a" * 42
        env_key = "sk-env" + "b" * 46
        
        mock_keyring['get'].return_value = keyring_key
        
        with patch.dict(os.environ, {api_manager.ENV_VAR_NAME: env_key}):
            result = api_manager.get_api_key()
        
        assert result == keyring_key
        assert result != env_key

    @patch('commandrex.config.api_manager.logger')
    def test_get_api_key_logs_env_usage(self, mock_logger, mock_keyring, valid_api_key):
        """Test that using environment variable is logged."""
        mock_keyring['get'].return_value = None
        
        with patch.dict(os.environ, {api_manager.ENV_VAR_NAME: valid_api_key}):
            api_manager.get_api_key()
        
        mock_logger.info.assert_called_once()
        assert api_manager.ENV_VAR_NAME in mock_logger.info.call_args[0][0]


class TestSaveApiKey:
    """Test cases for save_api_key function."""

    def test_save_api_key_success(self, mock_keyring, valid_api_key):
        """Test successful API key saving."""
        mock_keyring['set'].return_value = None
        
        result = api_manager.save_api_key(valid_api_key)
        
        assert result is True
        mock_keyring['set'].assert_called_once_with(
            api_manager.SERVICE_NAME,
            api_manager.API_KEY_NAME,
            valid_api_key
        )

    def test_save_api_key_empty_string(self, mock_keyring):
        """Test saving empty API key fails."""
        result = api_manager.save_api_key("")
        
        assert result is False
        mock_keyring['set'].assert_not_called()

    def test_save_api_key_whitespace_only(self, mock_keyring):
        """Test saving whitespace-only API key fails."""
        result = api_manager.save_api_key("   \t\n  ")
        
        assert result is False
        mock_keyring['set'].assert_not_called()

    def test_save_api_key_none(self, mock_keyring):
        """Test saving None API key fails."""
        result = api_manager.save_api_key(None)
        
        assert result is False
        mock_keyring['set'].assert_not_called()

    def test_save_api_key_keyring_exception(self, mock_keyring, valid_api_key):
        """Test handling keyring exceptions during save."""
        mock_keyring['set'].side_effect = Exception("Keyring error")
        
        result = api_manager.save_api_key(valid_api_key)
        
        assert result is False

    @patch('commandrex.config.api_manager.logger')
    def test_save_api_key_logs_success(self, mock_logger, mock_keyring, valid_api_key):
        """Test that successful save is logged."""
        mock_keyring['set'].return_value = None
        
        api_manager.save_api_key(valid_api_key)
        
        mock_logger.info.assert_called_once_with("API key saved successfully")

    @patch('commandrex.config.api_manager.logger')
    def test_save_api_key_logs_error(self, mock_logger, mock_keyring, valid_api_key):
        """Test that save errors are logged."""
        error_msg = "Keyring access denied"
        mock_keyring['set'].side_effect = Exception(error_msg)
        
        api_manager.save_api_key(valid_api_key)
        
        mock_logger.error.assert_called_once()
        assert error_msg in mock_logger.error.call_args[0][0]

    @patch('commandrex.config.api_manager.logger')
    def test_save_api_key_logs_empty_key_error(self, mock_logger, mock_keyring):
        """Test that empty key error is logged."""
        api_manager.save_api_key("")
        
        mock_logger.error.assert_called_once_with("Cannot save empty API key")


class TestDeleteApiKey:
    """Test cases for delete_api_key function."""

    def test_delete_api_key_success(self, mock_keyring):
        """Test successful API key deletion."""
        mock_keyring['delete'].return_value = None
        
        result = api_manager.delete_api_key()
        
        assert result is True
        mock_keyring['delete'].assert_called_once_with(
            api_manager.SERVICE_NAME,
            api_manager.API_KEY_NAME
        )

    def test_delete_api_key_not_found(self, mock_keyring):
        """Test deleting non-existent API key."""
        mock_keyring['delete'].side_effect = PasswordDeleteError("Password not found")
        
        result = api_manager.delete_api_key()
        
        assert result is True  # Should still return True as it's not an error

    def test_delete_api_key_other_exception(self, mock_keyring):
        """Test handling other exceptions during deletion."""
        mock_keyring['delete'].side_effect = Exception("Keyring error")
        
        result = api_manager.delete_api_key()
        
        assert result is False

    @patch('commandrex.config.api_manager.logger')
    def test_delete_api_key_logs_success(self, mock_logger, mock_keyring):
        """Test that successful deletion is logged."""
        mock_keyring['delete'].return_value = None
        
        api_manager.delete_api_key()
        
        mock_logger.info.assert_called_once_with("API key deleted successfully")

    @patch('commandrex.config.api_manager.logger')
    def test_delete_api_key_logs_not_found(self, mock_logger, mock_keyring):
        """Test that 'not found' case is logged."""
        mock_keyring['delete'].side_effect = PasswordDeleteError("Not found")
        
        api_manager.delete_api_key()
        
        mock_logger.info.assert_called_once_with("No API key found to delete")

    @patch('commandrex.config.api_manager.logger')
    def test_delete_api_key_logs_error(self, mock_logger, mock_keyring):
        """Test that deletion errors are logged."""
        error_msg = "Access denied"
        mock_keyring['delete'].side_effect = Exception(error_msg)
        
        api_manager.delete_api_key()
        
        mock_logger.error.assert_called_once()
        assert error_msg in mock_logger.error.call_args[0][0]


class TestIsApiKeyValid:
    """Test cases for is_api_key_valid function."""

    def test_is_api_key_valid_correct_format(self, valid_api_key):
        """Test validation of correctly formatted API key."""
        result = api_manager.is_api_key_valid(valid_api_key)
        assert result is True

    def test_is_api_key_valid_minimum_length(self):
        """Test validation of minimum length API key."""
        # 40 characters after "sk-" prefix
        min_key = "sk-" + "a" * 40
        result = api_manager.is_api_key_valid(min_key)
        assert result is True

    def test_is_api_key_valid_too_short(self):
        """Test validation of too short API key."""
        short_key = "sk-" + "a" * 39  # One character too short
        result = api_manager.is_api_key_valid(short_key)
        assert result is False

    def test_is_api_key_valid_wrong_prefix(self):
        """Test validation of API key with wrong prefix."""
        wrong_prefix = "pk-" + "a" * 48
        result = api_manager.is_api_key_valid(wrong_prefix)
        assert result is False

    def test_is_api_key_valid_no_prefix(self):
        """Test validation of API key without prefix."""
        no_prefix = "a" * 51
        result = api_manager.is_api_key_valid(no_prefix)
        assert result is False

    def test_is_api_key_valid_empty_string(self):
        """Test validation of empty string."""
        result = api_manager.is_api_key_valid("")
        assert result is False

    def test_is_api_key_valid_none(self):
        """Test validation of None value."""
        result = api_manager.is_api_key_valid(None)
        assert result is False

    def test_is_api_key_valid_non_string(self):
        """Test validation of non-string value."""
        result = api_manager.is_api_key_valid(12345)
        assert result is False

    def test_is_api_key_valid_whitespace(self):
        """Test validation of whitespace string."""
        result = api_manager.is_api_key_valid("   ")
        assert result is False

    @pytest.mark.parametrize("key_length", [40, 48, 51, 60])
    def test_is_api_key_valid_various_lengths(self, key_length):
        """Test validation of API keys with various valid lengths."""
        api_key = "sk-" + "a" * key_length
        result = api_manager.is_api_key_valid(api_key)
        assert result is True

    @pytest.mark.parametrize("invalid_key", [
        "sk-",  # Just prefix
        "sk-a",  # Too short
        "sk-" + "a" * 39,  # One char too short
        "SK-" + "a" * 48,  # Wrong case prefix
        "sk_" + "a" * 48,  # Wrong separator
        "sk-" + "a" * 48 + " ",  # Trailing space
        " sk-" + "a" * 48,  # Leading space
    ])
    def test_is_api_key_valid_invalid_formats(self, invalid_key):
        """Test validation of various invalid API key formats."""
        result = api_manager.is_api_key_valid(invalid_key)
        assert result is False


class TestApiManagerConstants:
    """Test cases for module constants."""

    def test_service_name_constant(self):
        """Test that SERVICE_NAME constant is set correctly."""
        assert api_manager.SERVICE_NAME == "commandrex"

    def test_api_key_name_constant(self):
        """Test that API_KEY_NAME constant is set correctly."""
        assert api_manager.API_KEY_NAME == "openai_api_key"

    def test_env_var_name_constant(self):
        """Test that ENV_VAR_NAME constant is set correctly."""
        assert api_manager.ENV_VAR_NAME == "OPENAI_API_KEY"


class TestApiManagerIntegration:
    """Integration tests for API manager functionality."""

    def test_full_api_key_lifecycle(self, mock_keyring, valid_api_key):
        """Test complete API key lifecycle: save, get, delete."""
        # Initially no key
        mock_keyring['get'].return_value = None
        assert api_manager.get_api_key() is None
        
        # Save key
        mock_keyring['set'].return_value = None
        assert api_manager.save_api_key(valid_api_key) is True
        
        # Get saved key
        mock_keyring['get'].return_value = valid_api_key
        assert api_manager.get_api_key() == valid_api_key
        
        # Delete key
        mock_keyring['delete'].return_value = None
        assert api_manager.delete_api_key() is True
        
        # Verify key is gone
        mock_keyring['get'].return_value = None
        assert api_manager.get_api_key() is None

    def test_environment_fallback_behavior(self, mock_keyring, valid_api_key):
        """Test that environment variable works as fallback."""
        # No key in keyring
        mock_keyring['get'].return_value = None
        
        # No key in environment
        with patch.dict(os.environ, {}, clear=True):
            assert api_manager.get_api_key() is None
        
        # Key in environment
        with patch.dict(os.environ, {api_manager.ENV_VAR_NAME: valid_api_key}):
            assert api_manager.get_api_key() == valid_api_key

    def test_validation_integration(self, mock_keyring):
        """Test that validation works with save/get operations."""
        invalid_key = "invalid-key"
        
        # Should not save invalid key
        assert api_manager.save_api_key(invalid_key) is True  # save doesn't validate
        
        # But validation should catch it
        assert api_manager.is_api_key_valid(invalid_key) is False

    @patch('commandrex.config.api_manager.logger')
    def test_error_logging_integration(self, mock_logger, mock_keyring, valid_api_key):
        """Test that errors are properly logged across operations."""
        # Test save error logging
        mock_keyring['set'].side_effect = Exception("Save error")
        api_manager.save_api_key(valid_api_key)
        assert mock_logger.error.called
        
        # Reset mock
        mock_logger.reset_mock()
        
        # Test delete error logging
        mock_keyring['delete'].side_effect = Exception("Delete error")
        api_manager.delete_api_key()
        assert mock_logger.error.called


@pytest.mark.unit
class TestApiManagerEdgeCases:
    """Test edge cases and error conditions."""

    def test_keyring_import_error(self, valid_api_key):
        """Test behavior when keyring module has issues."""
        with patch('keyring.get_password', side_effect=ImportError("No keyring backend")):
            # Should handle gracefully
            with pytest.raises(ImportError):
                api_manager.get_api_key()

    def test_concurrent_access(self, mock_keyring, valid_api_key):
        """Test concurrent access to keyring operations."""
        # This is a basic test - real concurrent testing would need threading
        mock_keyring['get'].return_value = valid_api_key
        mock_keyring['set'].return_value = None
        
        # Simulate rapid successive calls
        results = []
        for _ in range(10):
            results.append(api_manager.get_api_key())
            api_manager.save_api_key(valid_api_key)
        
        # All should succeed
        assert all(result == valid_api_key for result in results)

    def test_unicode_api_key(self, mock_keyring):
        """Test handling of unicode characters in API key."""
        unicode_key = "sk-" + "ñ" * 48
        
        result = api_manager.is_api_key_valid(unicode_key)
        # Should handle unicode gracefully
        assert isinstance(result, bool)

    def test_very_long_api_key(self, mock_keyring):
        """Test handling of extremely long API key."""
        long_key = "sk-" + "a" * 1000
        
        # Should still validate based on prefix and minimum length
        assert api_manager.is_api_key_valid(long_key) is True
        
        # Should be able to save/retrieve
        mock_keyring['set'].return_value = None
        mock_keyring['get'].return_value = long_key
        
        assert api_manager.save_api_key(long_key) is True
        assert api_manager.get_api_key() == long_key