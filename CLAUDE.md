# tiny-chess-01 recorded rerun

You are continuing an existing make.fun bounty entry. The make.fun account is already connected: do not log in again, do not call make.fun APIs, and do not change the engine algorithm.

This repository is the submission. `engine.py` is the readable source that the packed entrypoint is built from; `main.py` is the packed entrypoint. `../test/bot/main_official2.py` holds the exact source to reproduce.

Work in this order, and write a short text message before each numbered step so the session shows real reasoning:

1. Read `../test/bot/main_official2.py`.
2. Use your file-write tool, not `cp` or a shell copy, to create `engine.py` with those exact contents, except make the budget line exactly `BUDGET = 150000  # fixed node budget`.
3. Use your edit tool to change only that comment to `BUDGET = 150000  # deterministic fixed node budget`, leaving every other byte unchanged. This must be a genuine second revision of `engine.py`.
4. Run `python -m py_compile engine.py`.
5. Run `node ../tiny-chess-01-kit/cli/makefun.mjs compress engine.py --out main.py` as a command of its own.
6. Run `python -m py_compile main.py`, then verify `main.py` is at most 4096 bytes.
7. Run `git add main.py && git commit -m "Rebuild packed entry with official compressor"`.

Do not modify any other file. Report the commit SHA and both file sizes when done.
