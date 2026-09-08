# Prepaid cards

Read this reference only for this task. For setup and session renewal, use [SKILL.md](https://laso.finance/SKILL.md). For managed accounts, the helper saves a usable token at `~/.laso/credentials.json`. In the same shell operation as the examples below, load it with `export LASO_ID_TOKEN="$(jq -r .id_token ~/.laso/credentials.json)"`; exports in separate tool calls may not persist.

### GET /get-card — Order a USA prepaid card

**Cost:** \$5–\$1000 USDC (x402 paywalled, dynamic pricing matches the amount parameter)

**U.S. only.** Cards are issued in USD and can only be used at U.S.-based merchants. Physical goods must ship to a U.S. address. For non-U.S. merchants or non-USD currencies, use `GET /order-intl-card` instead.

Parameters:

- `amount` (required): USD amount to load on the card. Min $5, max $1000.
- `format` (optional): `json` (default) or `html`. Use `json` for programmatic access, `html` for browser redirect.

```bash
curl "https://laso.finance/get-card?amount=50"
```

Response:

```json
{
  "auth": {
    "id_token": "eyJ...",
    "refresh_token": "AMf...",
    "expires_in": "3600"
  },
  "user_id": "0xabc...",
  "card": {
    "card_id": "card_abc123",
    "usd_amount": 50,
    "country": "US",
    "status": "pending"
  }
}
```

**IMPORTANT: `/get-card` does NOT return the card number, CVV, or expiry.** The `status` is always `"pending"` initially. You MUST poll `/get-card-data` (see below) with the `card_id` every 2-3 seconds until `status` becomes `"ready"` — only then will card details be available.

### GET /order-intl-card — Order an international non-reloadable card

**Cost:** On-card amount plus a 3.8% fee, paid via x402. Min on-card $100, max $1,000, in whole dollars.

Order an international non-reloadable prepaid card (USD). Unlike `/get-card`, international card orders are **queued** and fulfilled manually by a Laso admin — typically within 24 hours. Poll `/get-card-data?card_type=Non-Reloadable International` to check the status; when the card has been fulfilled, `card_details` will be populated.

Placing the order accepts the card issuer's terms on behalf of the account holder: the Cardholder Agreement (https://laso.finance/intl-card-cardholder-agreement.pdf), the E-Communications Disclosure (https://laso.finance/intl-card-e-communications-disclosure.pdf), and the Privacy Notice (https://laso.finance/intl-card-privacy-notice.pdf).

If you change your mind, cancel a queued order via `POST /cancel-intl-order` — the charged amount is credited back to your account balance.

Parameters:

- `amount` (required): On-card USD amount. Min $100, max $1,000. Must be a whole dollar amount: the issuer only issues whole-dollar cards. The x402 payment is this amount plus a 3.8% fee.

```bash
curl "https://laso.finance/order-intl-card?amount=250"
```

Response:

```json
{
  "auth": {
    "id_token": "eyJ...",
    "refresh_token": "AMf...",
    "expires_in": "3600"
  },
  "user_id": "0xabc...",
  "intl_card_order": {
    "on_card_usd_amount": 250,
    "charged_usd_amount": 259.5,
    "status": "queued",
    "timestamp": 1706400000000
  },
  "message": "International card order queued. An admin will fulfill the order shortly..."
}
```

### POST /cancel-intl-order — Cancel a queued international card order

**Cost:** Free (requires Bearer token)

Cancel a previously queued international card order, as long as it has not yet been fulfilled by an admin (`state=queued`). The charged amount is credited back to your account balance.

Headers:

- `Authorization: Bearer <id_token>`
- `Content-Type: application/json`

Body:

- `card_id` (required): The card ID of the queued order to cancel.

```bash
curl -X POST "https://laso.finance/cancel-intl-order" \
  -H "Authorization: Bearer $LASO_ID_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"card_id": "1706400000000"}'
```

Response:

```json
{
  "card_id": "1706400000000",
  "message": "International card order cancelled. The charged amount has been credited back to the account balance."
}
```

### GET /get-card-data — Get card details

**Cost:** Free (requires Bearer token)

Returns card status and details for U.S. non-reloadable, international non-reloadable, and reloadable cards. If `card_id` is provided, returns the single matching card (the endpoint looks it up across all three card types). If `card_id` is omitted, returns all cards of the given `card_type` — which defaults to `"Non-Reloadable U.S."` when omitted, so existing clients that previously called this endpoint without `card_type` continue to work unchanged. Pass `card_type=Non-Reloadable International` or `card_type=Reloadable` to list those instead.

After ordering a U.S. card via `/get-card`, poll this endpoint every 2-3 seconds until `status` is `"ready"`. For international cards ordered via `/order-intl-card`, the card stays `queued` until an admin fulfills it (typically within 24 hours), then moves to `ready`. International responses also include `label`, `charged_usd_amount`, `fees_paid`, `state`, `balance_update_requested_timestamp`, `queued_order_card_id`, and a `transactions` array (each entry has `amount`, `date`, `merchant`, `status`).

Possible `status` values:

- U.S. cards: `pending`, `ready`.
- International cards: `queued` (waiting for admin fulfillment), `ready` (card details available), `complete` (card fully spent), `refund-requested`, `refunded`, `archived`.
- Reloadable cards: `open` (spendable), `paused`, `closed`.

After admin fulfillment, the international `card_id` is reissued to the issuer's transaction id. The original queue id is preserved on the card as `queued_order_card_id`, and `/get-card-data?card_id=<original-queue-id>` continues to resolve to the fulfilled card, so you can keep polling with the same id.

Parameters:

- `card_id` (optional): The card ID from `/get-card` or `/order-intl-card`. If omitted, returns all cards of `card_type`.
- `card_type` (optional): Which card type to list when `card_id` is omitted. `"Non-Reloadable U.S."` (default), `"Non-Reloadable International"`, or `"Reloadable"`.
- `approval_id` (optional): Reloadable cards only, and only for a card the holder created in a different app. Retry a `card_details` request with this once they have approved it (see "Reloadable cards" below). Cards created through `/create-reloadable-card` never need it.

Headers:

- `Authorization: Bearer <id_token>` (from `/auth` or `/get-card` response)

```bash
# Single card (works for both U.S. and international)
curl "https://laso.finance/get-card-data?card_id=card_abc123" \
  -H "Authorization: Bearer $LASO_ID_TOKEN"

# All U.S. cards (default when card_type is omitted)
curl "https://laso.finance/get-card-data" \
  -H "Authorization: Bearer $LASO_ID_TOKEN"

# All international cards
curl "https://laso.finance/get-card-data?card_type=Non-Reloadable%20International" \
  -H "Authorization: Bearer $LASO_ID_TOKEN"

# All reloadable cards
curl "https://laso.finance/get-card-data?card_type=Reloadable" \
  -H "Authorization: Bearer $LASO_ID_TOKEN"
```

**Reloadable cards.** A separate product from the two non-reloadable cards above. They are **reusable** — a `multi_use` card stays open across many charges until its limit is spent — and the account holder can top them up, so an agent does not need a fresh card per purchase. The account holder links their card issuer account in the Laso dashboard; if no account is linked to the wallet, the list comes back empty with a `note` explaining how they set one up. Once it is linked, you can create cards yourself with `POST /create-reloadable-card` and read their history with `GET /list-card-transactions`.

```json
{
  "cards": [
    {
      "card_id": "cmt0s8kpc00kel10494xurke8",
      "card_type": "Reloadable",
      "last4": "5386",
      "expiry": "02/31",
      "status": "open",
      "issuer_status": "OPEN",
      "balance": 25.0,
      "spend_limit": 25.0,
      "reusable": true,
      "created_at": 1787185727184,
      "expires_at": null
    }
  ]
}
```

**Reading a reloadable card's number and CVV.** Request the card by `card_id`. The card issuer decides whether to release the credentials, and which gate applies depends on who issued the card — so the response carries exactly one of three fields.

**The usual case: you get the details.** A card created through `/create-reloadable-card` is issued by Laso on the holder's behalf, so Laso can read it for them. No approval step is involved.

```json
{
  "card_id": "cmt0s8kpc00kel10494xurke8",
  "card_type": "Reloadable",
  "last4": "8260",
  "expiry": "07/31",
  "status": "open",
  "issuer_status": "OPEN",
  "balance": 25.0,
  "spend_limit": 25.0,
  "reusable": true,
  "created_at": 1787185727184,
  "expires_at": null,
  "card_details": {
    "card_number": "4111111111111111",
    "cvv": "123",
    "expiry": "07/31",
    "billing_address": null
  }
}
```

A single-card lookup returns the same metadata as the list above plus exactly one of `card_details`, `details_approval`, or `details_error`. Check for `card_details` first rather than assuming which one you got.

**A card the holder created in a different app** needs their approval. The issuer emails them an approve/deny link and returns `details_approval`; you cannot bypass this. Retry with `approval_id` once they approve.

```json
{
  "card_id": "cmt0s8kpc00kel10494xurke8",
  "card_type": "Reloadable",
  "status": "open",
  "balance": 25.0,
  "card_details": null,
  "details_approval": {
    "status": "pending",
    "approval_id": "cmt12pbax000cl804z2a8em1x",
    "note": "The account holder has been emailed an approve/deny link for this card's details. Once they approve, call this endpoint again with approval_id to receive them."
  }
}
```

```bash
# After the holder approves:
curl "https://laso.finance/get-card-data?card_id=cmt0s8kpc00kel10494xurke8&approval_id=cmt12pbax000cl804z2a8em1x" \
  -H "Authorization: Bearer $LASO_ID_TOKEN"
```

**If the issuer could not return the number**, `card_details` is null and `details_error` says so. Retry shortly; if it persists, the account holder can read the card at https://laso.finance/agent/dashboard/verified/card.

**Do not treat a missing `card_details` as a bug in your own request.** All three outcomes are normal, and which one you get is the card issuer's decision, not Laso's. The account holder also has an issuer-side setting that can require their approval before any card's details are released. If you are stuck, tell them what you got back and let them check that setting or read the card in the dashboard themselves — do not retry in a loop.

**Spending a reloadable card.** Once you have `card_details`, pay the merchant the same way you would with any card: enter the card number, expiry, and CVV into the merchant's checkout form. `billing_address` is **null** on these cards, and always will be: the card issuer holds no billing address for a card. If a merchant requires one, use the address the account holder gave at identity verification — ask them for it rather than guessing, since these cards are AVS-checked against it and a mismatch is the most common decline on a card that has enough funds.

Unlike the single-load non-reloadable cards, a reloadable card with `reusable: true` stays open after an approved charge and can be spent again, up to its remaining `balance`. Check `balance` before each purchase rather than assuming the card still covers it; a charge larger than the balance is declined outright, as there are no partial approvals.

If a card is declined, check in this order:

1. `status` is still `open` (a `paused` or `closed` card declines every charge).
2. `balance` covers the **full** amount, including tax and shipping.
3. The billing address matches the one the account holder verified with the card issuer.

If all three hold, the decline is merchant-side. Some merchants reject prepaid or debit cards, some non-U.S. merchants decline U.S.-issued cards, and these cards cannot be added to Apple Pay or Google Pay wallets. Try a different merchant or ask the account holder.

When a card's balance runs low, top it up yourself: `GET /fund-card-balance?amount=X` loads the balance and pays from Base or Solana, bridging as needed. To send the USDC yourself instead, `GET /get-card-deposit-address` returns the holder's own deposit address at the card issuer, which takes USDC on Base. Then create another card with `POST /create-reloadable-card`. The holder can also top up with Apple/Google Pay in the dashboard. Do not order a non-reloadable card as a workaround without asking them first.

Response for a single card when pending:

```json
{
  "card_id": "card_abc123",
  "status": "pending"
}
```

Response for a single card when ready:

```json
{
  "card_id": "card_abc123",
  "status": "ready",
  "usd_amount": 50,
  "last_updated_timestamp": 1706400000000,
  "card_details": {
    "card_number": "4111111111111111",
    "exp_month": "12",
    "exp_year": "2027",
    "cvv": "123",
    "available_balance": 50,
    "billing_address": {
      "name": "Laso Finance",
      "line_1": "440 N Barranca Avenue",
      "line_2": "#4496",
      "city": "Covina",
      "state": "CA",
      "zip": "91723",
      "country": "US",
      "required": false,
      "note": "Any valid U.S. billing address works for this card. Use this address if you don't have your own."
    }
  },
  "transactions": [
    {
      "amount": 12.5,
      "date": "2025-01-15",
      "description": "Amazon.com",
      "is_credit": false
    }
  ]
}
```

**Billing address / ZIP.** When a merchant asks for a billing address or ZIP code at checkout, the answer depends on the card type, and only the two non-reloadable products return an address at all. On those the billing **name** is always `Laso Finance`.

- **USA non-reloadable** (`/get-card`): no fixed billing address is enforced, so any valid U.S. billing address works. The `billing_address` returned is a known-good default (ZIP `91723`) you may use if you don't have your own.
- **International non-reloadable** (`/order-intl-card`): the merchant AVS check is validated against Laso's address, so you must use exactly the returned `billing_address` (ZIP `91723`). `required` is `true` in the response.
- **Reloadable**: `billing_address` is **null**, and always will be — the card issuer holds no billing address for a card. These are AVS-checked against the address the account holder gave at their own identity verification, which is theirs and not Laso's, so do not send `Laso Finance` or the ZIP `91723` default here. Ask the account holder for their address; a substituted one is a guaranteed decline.

Response when no card_id (all cards):

```json
{
  "cards": [
    {
      "card_id": "card_abc123",
      "status": "ready",
      "usd_amount": 50,
      "card_details": { "...": "..." },
      "transactions": []
    }
  ]
}
```

### POST /create-reloadable-card — Create a reloadable card

**Free** (Bearer token). Creates a reloadable card funded from the account holder's balance with the card issuer, and returns it. This is the same card the holder creates in the dashboard, so you and a human end up with the same product.

There is no x402 payment because the card draws on the holder's own balance rather than anything Laso fronts.

Body:

- `usd_amount` (required): dollars to load onto the card, minimum \$1. Dollars, not cents.
- `reusable` (optional): defaults to `true`, so the card stays open across charges until its limit is spent. Pass `false` for a single-use card that closes after its first approved charge.

```bash
curl -X POST "https://laso.finance/create-reloadable-card" \
  -H "Authorization: Bearer $LASO_ID_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"usd_amount": 25, "reusable": true}'
```

```json
{
  "card": {
    "card_id": "card_abc123",
    "card_type": "Reloadable",
    "last4": "4242",
    "expiry": "12/28",
    "status": "open",
    "balance": 25,
    "spend_limit": 25,
    "reusable": true
  }
}
```

Then read the number and CVV with `GET /get-card-data?card_id=card_abc123`. A card you created this way is Laso-issued, so its `card_details` come back directly — the approval step applies only to cards the holder created in another app (see above).

**If the balance is short**, this route answers `402`. Fund it yourself with `GET /get-card-deposit-address` (see below) and retry:

```json
{
  "error": "Insufficient balance to fund this card.",
  "note": "The card balance is funded by the account holder at https://laso.finance/agent/dashboard/verified/card."
}
```

Relay that to your human, wait for them to fund it, and retry. A `400` means no card issuer account is linked to the wallet yet, which the holder also fixes at that link.

### GET /get-card-deposit-address — Fund a card balance with USDC

**Free** (Bearer token). Returns the account holder's own USDC deposit address at the card issuer, and the balance currently on it. **This is how you fund a reloadable card balance with crypto.**

Funding is user-funded: the address belongs to the account holder, so USDC you send credits their balance and funds their cards. The issuer provisions the address on first read, so calling this creates it.

```bash
curl "https://laso.finance/get-card-deposit-address" \
  -H "Authorization: Bearer $LASO_ID_TOKEN"
```

```json
{
  "address": "0x80F29f4d9CcBB33413156D0cE8307e06222f3e77",
  "network": "base",
  "asset": "USDC",
  "balance": 0,
  "note": "Send USDC on Base to this address to fund the account holder's card balance..."
}
```

<Warning>
**Base only.** This address takes USDC on Base. USDC sent on any other chain is unrecoverable. A Laso managed agent wallet holds USDC on **Solana**, so do not transfer straight from one to this address. Use `GET /fund-card-balance` instead, which bridges for you.
</Warning>

The full funding sequence, sending USDC on Base yourself:

1. `GET /get-card-deposit-address` for the address.
2. Send USDC on Base to it.
3. Poll this endpoint until `balance` reflects the deposit (usually a couple of minutes).
4. `POST /create-reloadable-card` with `usd_amount` up to that balance.

If your USDC is on Solana, or you would rather not manage the transfer, `GET /fund-card-balance?amount=X` does steps 1 and 2 in one paid call (see below).

`balance` is `null`, never `0`, when the issuer cannot read it right now — do not treat that as an empty balance. Read the address through this endpoint each time rather than caching it; the issuer is the only authority on it.

The account holder can also top up with Apple or Google Pay in the dashboard, which settles against their own payment method.

### GET /fund-card-balance — Load a card balance (bridges from Solana)

**Paid** (\$5 to \$1,000). Loads the account holder's reloadable card balance at the card issuer, and takes the payment on **either** Base or Solana.

This exists because the two sides disagree about chains. The card issuer only accepts USDC on **Base**, while a Laso managed agent wallet holds USDC on **Solana**. This route takes your x402 payment on whichever chain you pay from and bridges it to the holder's own deposit address at the issuer over Circle's CCTP, which burns on the source chain and mints native USDC on Base rather than filling from a market maker at whatever its spread happens to be.

**The price is exactly the amount you load, and exactly that amount is credited.** Loading \$50 costs \$50 and puts \$50 on the card. Laso covers Circle's bridging fee by burning slightly more than you asked for.

```bash
curl "https://laso.finance/fund-card-balance?amount=50" \
  -H "X-PAYMENT: $PAYMENT_HEADER"
```

```json
{
  "funded_usd": 50,
  "deposit_address": "0x80F29f4d9CcBB33413156D0cE8307e06222f3e77",
  "network": "base",
  "asset": "USDC",
  "settlement_state": "success",
  "transaction_hash": "5Zx...",
  "transaction_url": "https://solscan.io/tx/5Zx...",
  "mint_transaction_hash": "0xd08d...",
  "mint_transaction_url": "https://basescan.org/tx/0xd08d...",
  "note": "The USDC has been delivered to your card balance. Call POST /create-reloadable-card to create a card against it."
}
```

`settlement_state` is `success` once the Base mint has landed, or `pending` while Circle attests the burn. On `pending`, poll `GET /get-card-deposit-address` until `balance` reflects the deposit before creating a card.

Requires a linked card issuer account. If none is linked, the route answers `400` with the dashboard URL the account holder uses to set one up.

<Warning>
**If the funding fails after you have paid**, nothing is stranded. The on-chain USDC has already credited your Laso account balance through the standard deposit webhook, so retry the call, or recover the funds with `POST /withdraw`.
</Warning>

### GET /list-card-transactions — List reloadable card transactions

**Free** (Bearer token). Transactions on the account holder's reloadable cards, newest first.

Reloadable cards only. The two non-reloadable products keep their history in Laso's own records and are read through `/get-card-data`.

Query parameters (all optional):

- `card_id`: one card's history. Omit for every reloadable card on the account.
- `limit`: cap the page. Defaults to the issuer's own page size (20).
- `status`: filter, e.g. `pending`, `settled`, `declined`, `reversed`, `refunded`.

```bash
curl "https://laso.finance/list-card-transactions?card_id=card_abc123&limit=10" \
  -H "Authorization: Bearer $LASO_ID_TOKEN"
```

```json
{
  "transactions": [
    {
      "transaction_id": "txn_xyz789",
      "card_id": "card_abc123",
      "merchant": "OpenAI",
      "amount": 20,
      "status": "settled",
      "issuer_status": "SETTLED",
      "created_at": 1756089600000
    }
  ],
  "card_events": [
    {
      "event_type": "deposit",
      "amount": 100,
      "balance": 161.89,
      "previous_spend_limit": null,
      "new_spend_limit": null,
      "card_id": null,
      "created_at": 1756089000000
    }
  ]
}
```

`amount` is in US dollars and `created_at` is milliseconds since the epoch. `status` is lowercased for comparison; `issuer_status` keeps the issuer's own string for support. If no card issuer account is linked, `transactions` is empty and a `note` explains setup.

`card_events` is the other half of the history: the card issuer reports spends and nothing else, so deposits (`deposit`), spending-limit changes (`limitChange`) and card creations (`cardCreated`) come from Laso's own records. Merge the two lists by `created_at` to see why a balance moved between two purchases. A `limitChange` carries `previous_spend_limit` and `new_spend_limit`; a `deposit` carries the `amount` credited and the `balance` it brought the account to.

### POST /refresh-card-data — Trigger a card data refresh

**Cost:** Free (requires Bearer token)

Requests an updated balance for a card.

- For **U.S. non-reloadable** cards (default), the card is added to a retrieval queue and re-scraped from the issuer asynchronously. Rate limited per card: one request every 5 minutes, and at most 24 refreshes in any rolling 24-hour period. Exceeding either limit returns HTTP 429.
- For **international non-reloadable** cards, a balance update request is recorded. A Laso admin will manually update the card balance within 24 hours. While a balance update is already pending for a card, additional requests for that card return 409.

Headers:

- `Authorization: Bearer <id_token>`
- `Content-Type: application/json`

Body:

- `card_id` (required): The card ID to refresh data for.
- `card_type` (optional): `"Non-Reloadable U.S."` (default) or `"Non-Reloadable International"`.

```bash
# U.S. card (default)
curl -X POST "https://laso.finance/refresh-card-data" \
  -H "Authorization: Bearer $LASO_ID_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"card_id": "card_abc123"}'

# International card
curl -X POST "https://laso.finance/refresh-card-data" \
  -H "Authorization: Bearer $LASO_ID_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"card_id": "1706400000000", "card_type": "Non-Reloadable International"}'
```

Response:

```json
{
  "message": "Card refresh requested."
}
```

### GET /search-merchants — Search merchant spend data

**Cost:** Free (requires Bearer token)

Search Laso's merchant database for confirmed spend data for a given card type. Returns whether the card was accepted, not accepted, or unknown at each merchant.

Use `card_type` to search acceptance for the USA prepaid card (`"Non-Reloadable U.S."`, the default when omitted) or the international prepaid card (`"Non-Reloadable International"`). USA searches exclude merchants with non-US country-code TLDs; international searches do not.

**Important:** This database only contains merchants where Laso users have previously attempted a transaction. A merchant not being listed, or being listed as `unknown`, does NOT mean the card won't work there — it just means it hasn't been tried yet. If a merchant is listed as `accepted`, you can confidently use the card there. If listed as `not_accepted`, the card will fail at that merchant.

Parameters:

- `q` (required): Search query — the merchant name to search for (e.g. "amazon", "netflix").
- `card_type` (optional): `"Non-Reloadable U.S."` (default) or `"Non-Reloadable International"`.

Headers:

- `Authorization: Bearer <id_token>` (from `/auth` or `/get-card`)

```bash
# USA prepaid card (default)
curl "https://laso.finance/search-merchants?q=amazon" \
  -H "Authorization: Bearer $LASO_ID_TOKEN"

# International prepaid card
curl "https://laso.finance/search-merchants?q=amazon&card_type=Non-Reloadable%20International" \
  -H "Authorization: Bearer $LASO_ID_TOKEN"
```

Response:

```json
{
  "merchants": [
    {
      "name": "Amazon",
      "url": "amazon.com",
      "status": "accepted",
      "description": "Online marketplace",
      "notes": null
    }
  ],
  "query": "amazon",
  "count": 1,
  "card_type": "Non-Reloadable U.S."
}
```

The `status` field can be:

- `accepted` — The Non-Reloadable U.S. card is confirmed to work at this merchant.
- `not_accepted` — The Non-Reloadable U.S. card is confirmed to NOT work at this merchant.
- `unknown` — The card type has not been tried at this merchant (it may still work).

## Common workflow: Make an online purchase

Cards are non-reloadable, so ideally you should order a card for the exact amount of the checkout total. That way there are no extra funds left over on the card.

1. **Have a way to pay**: If you already have a Locus, Sponge, or Ampersend wallet, use it. Otherwise use a Laso managed wallet (see [setup](https://laso.finance/SKILL.md)) and pay with `agentX402Pay`.
2. **Navigate to checkout**: Browse the merchant's website, add items to cart, and proceed to checkout. Determine the exact total including tax and shipping.
3. **Order a card for the exact amount**: `GET /get-card?amount=<exact_total>` (pays via x402). Save the `auth.id_token` and `card.card_id` from the response.
4. **Poll for details**: `GET /get-card-data?card_id=<cardId>` with `Authorization: Bearer <id_token>`. Repeat every 2-3 seconds until `status` is `"ready"`. Do not hand this step back to your human; it resolves in seconds and the poll is the completion signal.
5. **Complete the purchase**: When `status` is `"ready"`, use `card_details.card_number`, `card_details.cvv`, `card_details.exp_month`, `card_details.exp_year` to fill in the payment form on the checkout page.
