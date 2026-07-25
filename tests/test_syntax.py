import os
import tempfile
import unittest

import app.main as shell
from app.declare import SHELL_VARIABLES


class CommandSyntaxTests(unittest.TestCase):
    def test_prompt_is_roger(self):
        self.assertEqual(shell.PROMPT, "roger $ ")

    def test_unterminated_quote_is_reported(self):
        parts, error = shell.tokenize_command("echo 'hello")

        self.assertIsNone(parts)
        self.assertEqual(error, "unterminated quote")

    def test_pipe_cannot_start_a_command(self):
        self.assertEqual(
            shell.validate_command_syntax(["|", "wc"]),
            "syntax error near unexpected token `|`",
        )

    def test_pipe_cannot_end_a_command(self):
        self.assertEqual(
            shell.validate_command_syntax(["echo", "hello", "|"]),
            "syntax error near unexpected token `newline`",
        )

    def test_redirection_requires_a_filename(self):
        self.assertEqual(
            shell.validate_command_syntax(["echo", "hello", ">"]),
            "syntax error near unexpected token `newline`",
        )

    def test_redirection_cannot_be_followed_by_an_operator(self):
        self.assertEqual(
            shell.validate_command_syntax(["echo", "hello", ">", ">", "output.txt"]),
            "syntax error near unexpected token `>`",
        )

    def test_valid_pipeline_and_redirection_are_accepted(self):
        self.assertIsNone(
            shell.validate_command_syntax(["echo", "hello", "|", "wc", ">", "count.txt"])
        )


class EnvironmentBuiltinTests(unittest.TestCase):
    def setUp(self):
        self.original_environment = os.environ.copy()
        self.original_variables = SHELL_VARIABLES.copy()
        self.original_exports = shell.EXPORTED_VARIABLES.copy()
        self.original_directory = os.getcwd()
        self.original_previous_directory = shell.PREVIOUS_DIRECTORY

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self.original_environment)
        SHELL_VARIABLES.clear()
        SHELL_VARIABLES.update(self.original_variables)
        shell.EXPORTED_VARIABLES.clear()
        shell.EXPORTED_VARIABLES.update(self.original_exports)
        os.chdir(self.original_directory)
        shell.PREVIOUS_DIRECTORY = self.original_previous_directory

    def test_export_makes_a_variable_available_to_external_commands(self):
        self.assertEqual(shell.handle_export(["ROGER_TEST=value"]), 0)
        self.assertEqual(SHELL_VARIABLES["ROGER_TEST"], "value")
        self.assertEqual(os.environ["ROGER_TEST"], "value")

    def test_unset_removes_a_variable_from_both_scopes(self):
        shell.handle_export(["ROGER_TEST=value"])
        self.assertEqual(shell.handle_unset(["ROGER_TEST"]), 0)
        self.assertNotIn("ROGER_TEST", SHELL_VARIABLES)
        self.assertNotIn("ROGER_TEST", os.environ)

    def test_status_expansion_supports_dollar_question_mark(self):
        shell.LAST_EXIT_STATUS = 127
        self.assertEqual(shell.expand_raw_command("echo $? ${?}"), "echo 127 127")

    def test_cd_without_an_argument_uses_home_and_cd_dash_returns(self):
        with tempfile.TemporaryDirectory() as home_directory:
            os.environ["HOME"] = home_directory
            self.assertEqual(shell.handle_cd([]), 0)
            self.assertEqual(os.path.realpath(os.getcwd()), os.path.realpath(home_directory))
            self.assertEqual(shell.handle_cd(["-"]), 0)
            self.assertEqual(os.path.realpath(os.getcwd()), os.path.realpath(self.original_directory))


if __name__ == "__main__":
    unittest.main()
