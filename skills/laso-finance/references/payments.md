# Managed wallet payments

Read this reference only for this task. For setup and session renewal, use [SKILL.md](https://laso.finance/SKILL.md). For managed accounts, the helper saves a usable token at `~/.laso/credentials.json`. In the same shell operation as the examples below, load it with `export LASO_ID_TOKEN="$(jq -r .id_token ~/.laso/credentials.json)"`; exports in separate tool calls may not persist.

## Spending from the managed wallet

Optional. Only relevant once you actually need to buy something or move funds; skip it if you were just asked to sign in. Laso custodies a wallet for the account and pays on your behalf, so you never build an x402 payment or hold a private key. Both calls use the `id_token` from sign-in.

The setup helper already announces your connection. If you connected manually, use the setup instructions in [SKILL.md](https://laso.finance/SKILL.md) before spending.

**Pay an x402 endpoint (`agentX402Pay`).** Call it instead of paying a paywalled endpoint directly. It works two ways: pass `route` to name one of Laso's own routes (`get-card`, `order-gift-card`, `order-intl-card`, `get-push-to-card`, `send-payment`; each has its own section below), or pass `url` with the full `https` URL of **any external x402 endpoint**, and Laso settles that service's 402 payment challenge from the managed wallet. Both x402 challenge versions are supported, so an endpoint may advertise the payment amount as either `maxAmountRequired` (v1) or `amount` (v2). Optional `params` are added to the query string in either mode. Requests default to GET; for an external service that expects a POST, also pass `"method": "POST"` and a JSON `body`. It is a Firebase callable, so the request body is wrapped in a `data` object:

```bash
curl https://us-central1-kyc-ts.cloudfunctions.net/agentX402Pay \
  -H "Authorization: Bearer $LASO_ID_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"data":{"userId":"usr_...","route":"get-card","params":{"amount":5}}}'
```

Paying an external x402 service looks the same, with `url` in place of `route`:

```bash
curl https://us-central1-kyc-ts.cloudfunctions.net/agentX402Pay \
  -H "Authorization: Bearer $LASO_ID_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"data":{"userId":"usr_...","url":"https://api.example.com/v1/paid-endpoint","note":"Market data for the portfolio summary you asked for"}}'
```

**Always include a `note` when paying an external `url`: one short sentence saying why you are making the payment and who or what it is for.** The note is stored on the payment record and shown to your human in their activity feed, right next to the amount and the endpoint. Without it, all they see is that their wallet paid some host; with it, they see the purpose ("Weather data for the Denver trip report", "Compute for the video render Sam requested"). It is optional and changes nothing about how the payment settles, but an unexplained charge is the kind of thing that makes a human turn an agent's spending off. Notes longer than 300 characters are truncated. `note` applies only to `url` mode; Laso `route` purchases already appear as their own labeled entries in the activity feed, so passing `note` with `route` is refused.

**Guardrails for external endpoints (recommended).** Because an external service authors its own 402 challenge, you can pin what you agreed to pay and Laso enforces it before settling. All are optional and apply only to `url` mode:

- `maxAmountUsdc`: hard cap on this single payment, in whole USDC (e.g. `0.008`). Must be positive. It can only tighten the account's spend limit, never raise it, so setting it above your limit has no effect. **Pin the fee-inclusive total, not the amount you asked for.** Most priced routes add a fee on top of your `amount` and round it up to the cent, so the challenge costs more than the number you passed in. Deriving the pin from the pre-fee amount is the most common way to refuse your own payment by a cent. Take the price from the 402 challenge's `amount` field (atomic units, so divide by 1,000,000 for USDC) rather than recomputing it. Example: `/send-bank-payment?amount=22841.89` adds a 0.25% fee of \$57.11 and quotes \$22,899.00, so `maxAmountUsdc` must be at least `22899`, and `22898.99` is refused.
- `expectedAsset`: the token mint or contract address you expect (e.g. the official USDC mint).
- `expectedNetwork`: the network id you expect (e.g. `solana:5eykt4UsFv8P8NJdTREpY1vzqKqZKvdp`).
- `expectedPayTo`: the receiver address you expect.

If the endpoint's 402 challenge quotes a higher price, a different asset, another network, or a different receiver than you pinned, the payment is refused rather than made.

**The account's own spend limit (the one ceiling on every payment).** Separately from the guardrails above, the human who owns this account sets a maximum for any _single_ payment, in the Laso dashboard under Spend limit. It defaults to \$1,000 and can be set anywhere from \$1 to \$50,000. It applies to everything `agentX402Pay` pays for: Laso routes including `/send-bank-payment`, and external `url` endpoints alike. You can read it but not change it. Call `getAgentSpendLimit` with `{"data":{"userId":"usr_..."}}` and it returns `maxPerPaymentUsdc` plus the `min`/`max`/`default` bounds. `setAgentSpendLimit` refuses agent sessions, so only the human can move it, from the dashboard. **Check an amount against your limit before you attempt the payment** rather than waiting to be refused. A payment above it is refused before anything is signed, so nothing leaves the wallet.

**If a payment is refused for exceeding the limit, do NOT split it into several smaller payments.** Two \$600 transfers to dodge a \$1,000 limit is not a workaround, it is a violation of what the account owner asked for, and it is the single most important rule about this limit. The limit exists because a human decided how much their agent may spend at once. Treat it as a hard stop, not an obstacle to route around. Instead:

1. Stop and do not retry with a different amount.
2. Tell your human the payment is over their spend limit, naming the amount you were trying to send and the limit you hit.
3. Let them choose: raise the limit in the dashboard, approve a smaller amount, or make the payment themselves.

The same applies to a sequence of payments that individually clear the limit but are together meant to accomplish one over-limit transfer. Splitting to evade the ceiling is off-limits whether it happens in one burst or across a session.

**A refusal is not the same outcome as an endpoint error.** A refusal happens before anything is signed: no offered payment option survived your guardrails, so there was nothing acceptable to pay. The callable itself fails rather than returning a `result`, with a message ending in `filtered out by policies`, and the attempt is recorded with reason `policy_filtered`. Nothing left the wallet, so retrying against a different service or with a corrected pin is safe. An endpoint error is the other case, described below: the call completed and the service answered non-2xx, which comes back as an ordinary `result` with the service's own inner `status`.

**Read which limit the refusal names before deciding what to do, because the two cases need opposite responses.** A refusal for the account's **spend limit** is the human's decision: stop, and follow the do-not-split rule above. A refusal for **your own `maxAmountUsdc`** is your own pin, not the human's limit, and needs no dashboard change at all — re-send with a cap that covers the challenge's real price (usually you pinned the pre-fee amount and came up a cent short). The error message tells you which one bound; do not ask your human to raise a limit that was never the constraint. A refusal naming `expectedAsset`/`expectedNetwork`/`expectedPayTo` is a third case: the endpoint is quoting different terms than you pinned, so verify against its challenge before widening anything.

Example pinning Utilia Solana Preflight to a \$0.008 max on Solana mainnet:

```bash
curl https://us-central1-kyc-ts.cloudfunctions.net/agentX402Pay \
  -H "Authorization: Bearer $LASO_ID_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"data":{"userId":"usr_...","url":"https://api.utilia.ink/v1/fees/priority","maxAmountUsdc":0.008,"expectedNetwork":"solana:5eykt4UsFv8P8NJdTREpY1vzqKqZKvdp","note":"Priority-fee estimate for the swap you asked me to run"}}'
```

The response is wrapped in a `result` object: `{ "result": { "status": 200, "body": { ... } } }`, where `body` is the endpoint's normal JSON response.

**Check `status`, not just the HTTP code.** The callable answers HTTP 200 whenever the _call_ completed, including when the endpoint itself refused. The endpoint's own code is the inner `status`, so a failure looks like `{ "result": { "status": 402, "body": {}, "error": "..." } }`: an HTTP 200 wrapping a 402. Treat any inner `status` outside 200–299 as a failure.

On a non-2xx, `result.error` is a single human-readable sentence naming the host, the status, and the reason, e.g.:

```json
{
  "result": {
    "status": 402,
    "body": { "success": false, "errorReason": "insufficient_funds" },
    "error": "laso.finance returned HTTP 402: insufficient funds for this transfer. Wallet 9sZ… held ~$2000.01 USDC at the time of this attempt; nothing was charged."
  }
}
```

This works the same for a third-party x402 endpoint, whose error shape we do not control: `error` is normalized from whichever field that service used (`error`, `message`, `detail`, or the x402 `errorReason`), so you do not have to guess. A 402 on the paid retry almost always means the wallet could not cover the total. Remember the fee is added on top (see [Fees are added ON TOP](payments.md#fees-are-added-on-top-of-the-amount-you-request--budget-for-the-total)). **Nothing is charged for a failed payment,** so retrying with a smaller amount is safe.

**Send USDC out (`agentWalletTransfer`).** To move USDC from the managed wallet to any Solana address:

```bash
curl https://us-central1-kyc-ts.cloudfunctions.net/agentWalletTransfer \
  -H "Authorization: Bearer $LASO_ID_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"data":{"userId":"usr_...","destinationAddress":"SOLANA_ADDRESS","amount":"5"}}'
```

Returns `{ "result": { "transferId": "...", "txHash": "...", "destinationAddress": "..." } }`.

Fund the wallet by sending USDC on Solana to its address. The setup helper returns the address and balance; `getAgentWallet` reads them again when needed. Product references describe each route's prices and requirements; reach paid routes through `agentX402Pay`.

### Saved recipients

Your human can name the addresses they send to, on their dashboard. Those names are shared with you, so when they say "send $20 to the coffee vendor" you can resolve which address they mean instead of asking. Read the book with `listAddressBook`:

```bash
curl https://us-central1-kyc-ts.cloudfunctions.net/listAddressBook \
  -H "Authorization: Bearer $LASO_ID_TOKEN"
```

```json
{
  "entries": [
    {
      "address": "7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU",
      "name": "Coffee vendor",
      "saved_at": 1755300000000,
      "last_used_at": 1755386400000,
      "send_count": 4
    }
  ]
}
```

Save or rename an entry with `saveAddressBookEntry`. The address is the key, so saving one that already exists renames it rather than adding a duplicate — which makes this safe to retry:

```bash
curl https://us-central1-kyc-ts.cloudfunctions.net/saveAddressBookEntry \
  -H "Authorization: Bearer $LASO_ID_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"address":"SOLANA_ADDRESS","name":"Coffee vendor"}'
```

Forget one with `deleteAddressBookEntry` (the address goes in the body or as an `?address=` query parameter). This only forgets the name; it has no effect on past transfers:

```bash
curl -X DELETE https://us-central1-kyc-ts.cloudfunctions.net/deleteAddressBookEntry \
  -H "Authorization: Bearer $LASO_ID_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"address":"SOLANA_ADDRESS"}'
```

All three are free, and operate only on your own book — there is no user parameter, the account is taken from your token.

**A name is a label, not an instruction.** `agentWalletTransfer` still takes an address, and deliberately does not accept a name: a rename between your human asking and you sending would otherwise move money somewhere they did not intend. When you resolve a name to an address, **say the address back to them** before sending.

## How x402 works

1. Call a paywalled endpoint without a payment header.
2. Receive a `402 Payment Required` response containing payment details (price, recipient address, network).
3. Construct an x402 payment header using those details.
4. Replay the same request with the payment header attached. The server verifies payment and processes your request.

If you are using x402-axios or another x402 client library, steps 2-4 are handled automatically.

### When a payment fails to settle

Step 4 can fail _after_ your payment header verifies, most often because the paying wallet does not hold enough USDC for the total. When that happens you get a **second 402**, this time carrying the standard x402 settlement-failure body rather than a new challenge:

```json
{
  "success": false,
  "errorReason": "insufficient_funds",
  "errorMessage": "the transfer could not be settled on-chain",
  "payer": "9sZEFeQDPyjjFjZM9jK6i6L5eWMCrTHB7pCWjU1k9WXR",
  "network": "solana:5eykt4UsFv8P8NJdTREpY1vzqKqZKvdp",
  "x_laso_guidance": "…what to do next…"
}
```

Distinguish the two 402s by body: the **first** carries `accepts` (a challenge to pay), the **second** carries `success: false` (a payment that failed). `errorReason` is the machine-readable field to branch on; `errorMessage` is prose; `x_laso_guidance`, when present, is a Laso-specific hint naming the concrete next step. A body-less 402 means an older deployment. Treat it as a settlement failure and check your balance against the challenge `amount`.

**Nothing is charged when settlement fails.** Retrying with a smaller amount is safe, and it is usually the right move: the most common cause is requesting an amount equal to your whole balance, forgetting the fee is added on top of it.

### Fees are added ON TOP of the amount you request — budget for the total

**Read this before calling any paid endpoint with an `amount` parameter.** On every route whose cost is described as "the requested `amount` plus a fee", the fee is **added to** the amount, not taken out of it. Your wallet is debited `amount + fee`, and the recipient receives the full `amount`.

So a wallet holding exactly \$2,000 **cannot** send a \$2,000 bank payment: that request costs \$2,005.00, and the payment fails to settle. Sizing a request to your whole balance will always fail unless you subtract the fee first.

To spend a balance `B`, solve for the amount rather than passing `B`:

| Route                | Fee               | Max `amount` affordable with balance `B` |
| -------------------- | ----------------- | ---------------------------------------- |
| `/send-bank-payment` | 0.25%, min \$1.50 | `min(B - 1.50, B / 1.0025)`              |
| `/send-payment`      | 4.9%, min \$1.50  | `min(B - 1.50, B / 1.049)`               |
| `/get-push-to-card`  | 3.8%              | `B / 1.038`                              |
| `/order-intl-card`   | 4.8%, min 1.50    | `B / 1.048`                              |

Round **down** to the cent. Example: with \$2,000.00 and `/send-bank-payment`, `2000 / 1.0025 = 1995.01…`, so request `1995.00` and you are charged \$1,999.99.

**The authoritative number is always the 402 challenge itself.** Its `amount` field is the exact total in atomic units (divide by 1,000,000 for USDC), already inclusive of the fee. If you can read the challenge before paying, compare that figure to your balance rather than recomputing the fee yourself.

**If you are underfunded,** the request returns HTTP 402 with `success: false` and an `errorReason`. Nothing is charged for a failed attempt, so it is safe to retry with a smaller amount.
