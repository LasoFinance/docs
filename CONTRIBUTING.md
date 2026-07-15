# Contribute to the documentation

Thank you for your interest in improving the Laso Finance documentation. This guide will help you get started.

## How this repo works

This repository is the public home for the Laso Finance documentation. It is a mirror: the docs are maintained upstream and synced here automatically. When you open a pull request against this repo and it is merged, your changes are automatically synced back upstream and published. You do not need to do anything special. Just edit the docs and open a PR.

## How to contribute

### Option 1: Edit directly on GitHub

1. Navigate to the page you want to edit
2. Click the edit (pencil) button
3. Make your changes and open a pull request

### Option 2: Local development

1. Fork and clone this repository
2. Install the Mintlify CLI: `npm i -g mint`
3. Create a branch for your changes
4. Make your changes
5. Run `mint dev` from the repository root
6. Preview your changes at `http://localhost:3000`
7. Commit and open a pull request

Before opening a PR, run `mint dev` and make sure it reports no parsing errors or broken links. The docs build fails on issues that `mint dev` surfaces, so treat them as blocking.

For more details on local development, see the [development guide](development.mdx).

## Writing guidelines

- **Use active voice**: "Run the command", not "The command should be run"
- **Address the reader directly**: use "you" instead of "the user"
- **Keep sentences concise**: aim for one idea per sentence
- **Lead with the goal**: start instructions with what the reader wants to accomplish
- **Use consistent terminology**: don't alternate between synonyms for the same concept
- **Include examples**: show, don't just tell

## What not to edit

A few files in this repo are generated or managed upstream and will be overwritten on the next sync:

- `llms.txt`, `llms-full.txt`, `skill.md` are generated. Open an issue instead of editing them directly.
- `api-reference/openapi.json` is the API source of truth. Corrections are welcome, but structural changes are best raised as an issue first.
