# Code Review Prompt

## Purpose
Use this prompt template when asking an agent to review code for quality,
security, and correctness.

## Template

```
Please review the following {{language}} code.

Focus on:
1. Correctness – does the code do what it's supposed to do?
2. Security – are there any vulnerabilities or unsafe patterns?
3. Performance – are there obvious inefficiencies?
4. Readability – is the code easy to understand and maintain?

Return your feedback as a structured list of issues, each with:
- Severity: High | Medium | Low
- Location: file/line (if applicable)
- Description: what the issue is
- Suggestion: how to fix it

Code:
```{{language}}
{{code}}
```
```

## Variables
- `{{language}}` – programming language (e.g., Python, TypeScript)
- `{{code}}` – the code to review
