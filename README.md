# SCOP Workspace

SCOP reviews a public GitHub pull request locally. It shows a summary with links and exact source excerpts for each claim.

## Quick start on Linux or Windows with WSL

1. On Windows, open PowerShell and run `wsl --install -d Ubuntu` if WSL is not installed. Restart if prompted, then launch **Ubuntu**. Run the commands below in Ubuntu (Bash). On Linux, use your regular terminal.
2. Install Git and Python 3.12 in that Linux environment. On Ubuntu 24.04, run `sudo apt update && sudo apt install git python3.12`.
3. Clone and launch from the repository root.

   ```sh
   git clone https://github.com/sovereis/SCOP.git
   cd SCOP
   python3.12 -B -m server.scop_web
   ```

4. Keep the terminal open and visit **http://127.0.0.1:8765** in your browser. On WSL, that can be your Windows browser. Try `https://github.com/pallets/flask/pull/5808` and tick the read-only GitHub consent box before generating a summary.

Workflow completion means SCOP ran its required steps and matched the cited excerpts. Review each claim in context before deciding whether to accept it or request rework.

## Optional local recording

An unrecorded review works immediately. To enable recording and human evaluation, stop SCOP with Ctrl+C and restart it with a dedicated private directory outside every Git checkout. On WSL, use its Linux filesystem (for example, a path under your WSL home).

```sh
mkdir -m 700 "$HOME/scop-measurements"
python3.12 -B -m server.scop_web --store-dir "$HOME/scop-measurements"
```

Recording and feedback each require explicit consent in the browser. Leave unknown durations blank.

## Troubleshooting

- **Wrong shell or missing Python:** in Windows Terminal, select Ubuntu or run `wsl -d Ubuntu`, then check `python3.12 --version` and `cd` to the checkout.
- **Local origin denied:** open the exact address printed by SCOP, including `127.0.0.1` and the port. If your Windows browser cannot reach WSL, verify the server is still running and check WSL localhost forwarding. Keep the listener on loopback.
- **Recording disabled:** restart with `--store-dir` or continue without recording.
- **Invalid URL:** use the PR's main page, with a positive PR number and no extra path, query, or fragment.
- **GitHub unavailable:** check connectivity from Linux or WSL, confirm the PR is public, and retry after rate limits reset if applicable. Missing patch evidence can also block a review.

See the [web architecture and developer tests](server/WEB.md).

## Public landing on Vercel

Deploy only the `landing` root directory using its [Vercel setup guide](landing/README.md#deploy-to-vercel-after-approval). The production signup API requires configured Supabase storage and server-only environment variables. Git-triggered deployments are disabled in the configuration. The Workspace continues to run locally through the commands above.
