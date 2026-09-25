# Laso Finance Documentation

Public documentation for [Laso Finance](https://laso.finance), the payment API for AI agents: order prepaid cards and gift cards, and send money to USD/EUR/GBP debit cards or US bank accounts, paying with USDC on Base or Solana over the [x402 protocol](https://laso.finance/SKILL.md).

- Docs site: [docs.laso.finance](https://docs.laso.finance)
- Agent skill: [laso.finance/SKILL.md](https://laso.finance/SKILL.md)
- OpenAPI spec: [laso.finance/openapi.json](https://laso.finance/openapi.json)
- LLM index: [laso.finance/llms.txt](https://laso.finance/llms.txt)

## Install the agent skill

Give your coding agent the Laso Finance skill so it can spend USDC on your behalf:

```bash
npx skills add LasoFinance/docs
```

Or install it manually:

```bash
mkdir -p ~/.claude/skills/laso-finance
curl -sS https://laso.finance/SKILL.md -o ~/.claude/skills/laso-finance/SKILL.md
```

The skill source lives in [`skills/laso-finance/SKILL.md`](skills/laso-finance/SKILL.md). It is generated from [`skill.md`](skill.md) at the repo root, which is the file served at `https://laso.finance/SKILL.md`; the two are always byte-identical, so either copy can be verified against the digest published at [`/.well-known/docs-version.json`](https://laso.finance/.well-known/docs-version.json).

## Contributing

This repository is a mirror of the upstream docs source; merged PRs sync back upstream automatically. See [CONTRIBUTING.md](CONTRIBUTING.md).

To preview locally:

```bash
npm i -g mint
mint dev
```

View your local preview at `http://localhost:3000`.
