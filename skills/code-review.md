# Code Review Skill

## Description
Performs a thorough code review on a given diff or file, checking for:
- Correctness and logic errors
- Security vulnerabilities
- Performance issues
- Code style and maintainability

## Usage
Provide the code or diff to review, and this skill will return structured feedback.

## Input
- `code` (string): The code or diff to review
- `language` (optional, string): The programming language (e.g., `python`, `javascript`)

## Output
A structured review with:
- **Summary**: Overall assessment
- **Issues**: List of problems found (severity: high / medium / low)
- **Suggestions**: Recommended improvements

## Example Prompt
> Review the following Python code for correctness, security, and style:
> ```python
> <code here>
> ```
