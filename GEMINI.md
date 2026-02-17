# Gemini Integration

**Python Environment:** Always use root `unified_venv` at `/home/rjegj/projects/unified_venv`.

Uses **Google Gemini 2.0 Flash** to parse Bible reading plans from images.

## Workflow
1. Input: Images in assets/ folder.
2. Process: tools/gemini_parser.py sends to Gemini API.
3. Output: JSON plan in plans/ folder.

**Git Automation:** Automatically perform `git add .`, `git commit`, and `git push` upon task completion.
