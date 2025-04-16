import unittest
from unittest.mock import patch, MagicMock
from app.services.LLMModel import LLMModel


class TestUpdateSolution(unittest.TestCase):

    def setUp(self):
        # Initialize LLMModel with a mock API key
        self.llm_model = LLMModel(api_key="mock_api_key")

    @patch('openai.ChatCompletion.create')
    def test_successful_update(self, mock_openai):
        # Mock the API response
        mock_response = MagicMock()
        mock_response.choices = [{
            'message': {
                'content': 'FULL_FILE:\n```java\n// Updated full file\n```\nSNIPPET:\n```java\n// Updated snippet\n```'
            }
        }]
        mock_openai.return_value = mock_response

        # Call update_solution
        result = self.llm_model.update_solution(
            bug_type="NullPointerException",
            description="Null pointer dereference",
            original_code="public class Test {}",
            current_solution="public class Test { void method() {} }",
            user_feedback="Improve the solution"
        )

        # Assertions
        self.assertIn('full_file', result)
        self.assertIn('snippet', result)
        self.assertEqual(result['full_file'], '// Updated full file')
        self.assertEqual(result['snippet'], '// Updated snippet')

    @patch('openai.ChatCompletion.create')
    def test_invalid_feedback(self, mock_openai):
        # Mock the API response
        mock_response = MagicMock()
        mock_response.choices = [{
            'message': {
                'content': 'FULL_FILE:\n```java\n// Updated full file\n```\nSNIPPET:\n```java\n// Updated snippet\n```'
            }
        }]
        mock_openai.return_value = mock_response

        # Call update_solution with empty feedback
        with self.assertRaises(Exception) as context:
            self.llm_model.update_solution(
                bug_type="NullPointerException",
                description="Null pointer dereference",
                original_code="public class Test {}",
                current_solution="public class Test { void method() {} }",
                user_feedback=""
            )

        self.assertTrue('User feedback is required' in str(context.exception))

    @patch('openai.ChatCompletion.create')
    def test_response_parsing(self, mock_openai):
        # Mock the API response with unexpected format
        mock_response = MagicMock()
        mock_response.choices = [{
            'message': {
                'content': 'Unexpected format'
            }
        }]
        mock_openai.return_value = mock_response

        # Call update_solution and expect an exception due to parsing failure
        with self.assertRaises(Exception) as context:
            self.llm_model.update_solution(
                bug_type="NullPointerException",
                description="Null pointer dereference",
                original_code="public class Test {}",
                current_solution="public class Test { void method() {} }",
                user_feedback="Improve the solution"
            )

        self.assertTrue(
            'Could not extract code from LLM response' in str(context.exception))


if __name__ == '__main__':
    unittest.main()
