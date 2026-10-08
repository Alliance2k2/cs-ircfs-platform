# Contributing to CS-IRCFS

Thank you for helping improve CS-IRCFS. Every change reaches `main` through a pull request that a maintainer reviews and approves. Nobody pushes directly to `main`.

## Set up

1. **Fork** the repository on GitHub (top-right **Fork** button), then clone your fork:

   ```powershell
   git clone https://github.com/<your-username>/cs-ircfs-platform.git
   cd cs-ircfs-platform
   git remote add upstream https://github.com/Alliance2k2/cs-ircfs-platform.git
   ```

2. Install and run with sample data (Python 3.11 or later):

   ```powershell
   python -m pip install -r backend/requirements.txt
   copy .env.example .env
   .\start-local.ps1 -Demo
   ```

   Open http://127.0.0.1:8000. Evaluation mode uses a separate SQLite database with invented data, so no PostgreSQL is needed to start.

## Make a change

1. Update your copy and create a branch for one change:

   ```powershell
   git checkout main
   git pull upstream main
   git checkout -b fix/short-description
   ```

2. Make the change, then run the tests:

   ```powershell
   cd backend
   python -m pytest -q -p no:cacheprovider
   ```

   Tests run on an in-memory database and make no network calls. Add or update tests for any behaviour you change.

3. Commit with a clear message and push to your fork:

   ```powershell
   git add <files>
   git commit -m "Explain what the change does and why"
   git push origin fix/short-description
   ```

4. On GitHub, open a **pull request** from your branch into `main`. Describe what changed, why, and how you tested it. A maintainer reviews it and either approves and merges it, or asks for changes.

## Rules

- **Never commit secrets or data.** `.env`, `infrastructure/stack.env` and `*.db` files are ignored by Git; keep it that way. Share credentials privately, never in a commit, issue or pull request.
- **No real citizen data** in code, tests, screenshots or issues. Use invented names and phone numbers.
- **Database changes** go through a new Alembic migration in `backend/migrations/versions/`, with an upgrade and a downgrade. Never edit an existing migration.
- **Kinyarwanda text** on phone screens and in the interface should be checked by a native speaker; mention it in the pull request when you add or change any.
- **Keep the style of the surrounding code**: small functions, clear names, and comments that explain why rather than what.
- One topic per pull request keeps reviews quick.

## Reporting problems

Open an issue describing what happened, what you expected, and the steps to reproduce it. For a security problem, do not open a public issue: contact the maintainers privately.

## License

By contributing, you agree that your contributions are released under the [MIT License](LICENSE).
