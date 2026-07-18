---
name: Lasofinance
description: Order prepaid cards, gift cards, and send money to USD/EUR/GBP debit cards using USDC on Base or Solana via the x402 protocol. Use when a user or agent needs to spend cryptocurrency, buy a prepaid card, order a gift card, or send money to a debit card programmatically.
metadata:
  author: laso-finance
  mintlify-proj: lasofinance
  version: "1.0"
---

# Laso Finance API

Laso Finance provides a payment-gated API using the x402 protocol. You can programmatically order USA and international prepaid cards, gift cards, and send money to USD, EUR, or GBP debit cards using USDC on Base or Solana.

Base URL: `https://laso.finance`

> **CRITICAL — Two-step card flow:** `/get-card` does NOT return card numbers. It only provisions the card and returns a `card_id` with `status: "pending"`. You MUST then poll `/get-card-data` with that `card_id` to get the actual card number, CVV, and expiry once `status` becomes `"ready"` (~7-10 seconds).

## Prerequisites

You need a funded crypto wallet on Base or Solana with USDC. Choose a wallet provider:

**Option A — Locus (default):**

```
https://paywithlocus.com/SKILL.md
```

Follow the Locus onboarding instructions. Once you have a Locus API key (`claw_` prefix), you can make x402 payments to Laso Finance endpoints.

**Option B — Sponge:**

```
https://wallet.paysponge.com/skill.md
```

Follow the Sponge onboarding instructions. Sponge discovers x402 services automatically — no manual endpoint configuration needed.

**Option C — Ampersend:**

[Ampersend](https://www.ampersend.ai/) provides self-custody agent wallets on Base or Solana with dual-approval spending (user + agent approve every payment) and per-transaction, daily, and monthly limits. Laso Finance is a default skill for Ampersend, so Ampersend wallets work natively with all paywalled endpoints — no manual endpoint registration required.

To set up an Ampersend wallet for Laso Finance:

1. Sign up at [ampersend.ai](https://www.ampersend.ai/).
2. From the dashboard, click **+ New agent**, then choose **Set up now** in the confirmation dialog and complete. You'll need at least \$5 to order a card; you can fund later from the agent's page.
3. On the **Set up your agent** screen, pick your framework. For Claude Code, OpenClaw, or other CLI-based agents, choose **OpenClaw, Claude Code or other CLI-based agents** at the top.
4. Ampersend displays a setup prompt of the form:

   ```
   Read https://www.ampersend.ai/getting-started.md
   and connect to my existing agent account:
     agent address: 0x...
   ```

   Paste it into your agent. The agent installs the Ampersend skill and CLI on its own and replies with an auth link (`https://app.ampersend.ai/approvals/setup-agent/<token>`) and a 6-digit verification code. Open the auth link, confirm the code matches, approve, then tell the agent it's done. The wallet is then ready to make x402 payments to Laso Finance.

**Option D — Laso managed account (no external wallet needed):**

If you were given a Laso agent API key (`lasoak_` prefix), you do **not** need a wallet from Locus, Sponge, or Ampersend, and you do **not** construct x402 payments yourself. The key signs you into a Laso account that a human already created (or will join). See [Using a Laso managed account](#using-a-laso-managed-account) below. If you have a `lasoak_` key, skip the rest of the wallet-provider setup and the Locus endpoint configuration.

## Using a Laso managed account

This section applies **only** if you have a Laso agent API key (`lasoak_` prefix). The key's core purpose is **shared account access**: you and a human use the same Laso account, and either of you can bring the other in.

- A human signs up on the Laso agent page, generates the `lasoak_` key, and gives it to you. You exchange it for a session below.
- In return, `agentAuth` gives you an `auth_url`, a login link you hand back to the human so they can sign into the web dashboard for the same account.

You do not have to spend or transfer anything for this to be useful; authenticating as the account is the point. Once signed in, spending is available too (see [Spending from the managed wallet](#spending-from-the-managed-wallet)).

### Sign in with your key

`POST` (or `GET`) your key to the auth endpoint as a Bearer header:

```bash
curl https://us-central1-kyc-ts.cloudfunctions.net/agentAuth \
  -H "Authorization: Bearer lasoak_YOUR_KEY"
```

Response:

```json
{
  "auth": { "id_token": "eyJ...", "refresh_token": "AMf...", "expires_in": "3600" },
  "user_id": "usr_...",
  "auth_url": "https://laso.finance/agent/dashboard/auth?authToken=..."
}
```

Use `id_token` as the Bearer token for any authenticated endpoint. It expires in about an hour; re-run this call (or refresh via `POST /auth`) to get a fresh one. Keep the `lasoak_` key itself secret, like a password; it is the long-lived credential that mints these sessions.

**Give `auth_url` to your human.** It is a one-click login link that signs them into the Laso web dashboard for this same account, so they can watch balances, cards, and transfers from their browser. Surface it to the person who set you up (for example, include it in your reply). The link is single-use and time-limited; call `agentAuth` again to get a fresh one.

**Have feedback on the API?** Once you have completed a real action, use `POST /submit-agent-feedback` (see [Endpoints](#endpoints)) to tell the humans running Laso what worked, what was confusing, or what you wish existed. It goes straight to their dashboard.

## Spending from the managed wallet

Optional. Only relevant once you actually need to buy something or move funds; skip it if you were just asked to sign in. Laso custodies a wallet for the account and pays on your behalf, so you never build an x402 payment or hold a private key. Both calls use the `id_token` from sign-in.

**Pay an x402 endpoint (`agentX402Pay`).** Call it with a route name and parameters instead of paying the paywalled routes directly. The `route` must be one of: `get-card`, `order-gift-card`, `order-intl-card`, `get-push-to-card`, `send-payment` (see the [Endpoints](#endpoints) section for what each does). It is a Firebase callable, so the body is wrapped in a `data` object:

```bash
curl https://us-central1-kyc-ts.cloudfunctions.net/agentX402Pay \
  -H "Authorization: Bearer YOUR_ID_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"data":{"userId":"usr_...","route":"get-card","params":{"amount":5}}}'
```

The response is wrapped in a `result` object: `{ "result": { "status": 200, "body": { ... } } }`, where `body` is the route's normal JSON response.

**Send USDC out (`agentWalletTransfer`).** To move USDC from the managed wallet to any Solana address:

```bash
curl https://us-central1-kyc-ts.cloudfunctions.net/agentWalletTransfer \
  -H "Authorization: Bearer YOUR_ID_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"data":{"userId":"usr_...","destinationAddress":"SOLANA_ADDRESS","amount":"5"}}'
```

Returns `{ "result": { "transferId": "...", "txHash": "...", "destinationAddress": "..." } }`.

Fund the wallet by sending USDC on Solana to the wallet address shown on the Laso agent account page. The endpoint descriptions below (prices, KYC, the two-step card flow) all still apply; you reach them through `agentX402Pay` rather than paying directly.

## Configuring Locus x402 Endpoints (Locus only)

If you chose **Locus**, you **must** register the Laso Finance x402 endpoints in the Locus dashboard before your agent can call them. (If you chose **Sponge**, skip this section — Sponge discovers endpoints automatically.)

### Step 1: Go to the x402 Endpoints page

Log in to [app.paywithlocus.com](https://app.paywithlocus.com) and navigate to **x402 Endpoints** in the left sidebar under "Config".

### Step 2: Add each Laso Finance endpoint

Click **+ Add Endpoint** and fill in the details for each paywalled endpoint. `GET /auth` is free (signature-based) and does not need to be registered here.

#### Endpoint 1: laso-get-card

| Field        | Value                                |
| ------------ | ------------------------------------ |
| Endpoint URL | `https://laso.finance/get-card`      |
| Slug         | `laso-get-card`                      |
| Name         | Laso Get Card                        |
| Description  | Order a USA prepaid card (U.S. only) |
| HTTP Method  | GET                                  |

**Input Parameters** (click "+ Add Parameter" for each):

| Name     | Type   | Location | Required |
| -------- | ------ | -------- | -------- |
| `amount` | number | query    | ✅ Yes   |

#### Endpoint 2: laso-push-to-card

| Field        | Value                                       |
| ------------ | ------------------------------------------- |
| Endpoint URL | `https://laso.finance/get-push-to-card`     |
| Slug         | `laso-push-to-card`                         |
| Name         | Laso Push to Card                           |
| Description  | Send money to a USD, EUR, or GBP debit card |
| HTTP Method  | GET                                         |

**Input Parameters** (click "+ Add Parameter" for each):

| Name       | Type   | Location | Required                                          |
| ---------- | ------ | -------- | ------------------------------------------------- |
| `amount`   | number | query    | Yes                                               |
| `currency` | string | query    | No (defaults to `USD`; also accepts `EUR`, `GBP`) |

#### Endpoint 3: laso-order-gift-card

| Field        | Value                                  |
| ------------ | -------------------------------------- |
| Endpoint URL | `https://laso.finance/order-gift-card` |
| Slug         | `laso-order-gift-card`                 |
| Name         | Laso Order Gift Card                   |
| Description  | Order a gift card from the catalog     |
| HTTP Method  | GET                                    |

**Input Parameters** (click "+ Add Parameter" for each):

| Name             | Type   | Location | Required |
| ---------------- | ------ | -------- | -------- |
| `amount`         | number | query    | ✅ Yes   |
| `laso_server_id` | string | query    | ✅ Yes   |
| `country`        | string | query    | No       |

### Step 3: Validate and save

For each endpoint, click **Validate & Add**. Locus will verify that the endpoint responds correctly before saving it.

### Important: Input Parameters

When adding GET endpoints, you **must** define input parameters with `Location: query`. This tells Locus to pass the parameters as URL query strings (e.g., `?amount=50`).

If you skip defining parameters, Locus won't know how to forward them to the Laso Finance API, and your requests will fail with errors like "amount query parameter is required".

### Calling endpoints via Locus

Once configured, your agent calls paywalled endpoints via the Locus API:

```bash
curl -X POST "https://api.paywithlocus.com/api/x402/laso-get-card" \
  -H "Authorization: Bearer YOUR_LOCUS_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"amount": 50}'
```

Locus handles the x402 payment negotiation automatically — it deducts the cost from your wallet and returns the API response.

`GET /auth` is free and signature-based, so call it directly with a `SIGN-IN-WITH-X` header (see below) instead of routing through Locus.

## How x402 works

1. Call a paywalled endpoint without a payment header.
2. Receive a `402 Payment Required` response containing payment details (price, recipient address, network).
3. Construct an x402 payment header using those details.
4. Replay the same request with the payment header attached. The server verifies payment and processes your request.

If you are using x402-axios or another x402 client library, steps 2-4 are handled automatically.

## Endpoints

### GET /auth — Get API credentials

**Cost:** Free.

Returns an `id_token`, `refresh_token`, and `user_id`. Use the `id_token` as a Bearer token for authenticated endpoints like `/get-card-data`.

Send a `SIGN-IN-WITH-X` header (a base64-encoded CAIP-122 signed message) to prove wallet ownership. The easiest way is `wrapFetchWithSIWx` from `@x402/extensions/sign-in-with-x`, which handles signature construction and the request round-trip automatically:

```typescript
import { wrapFetchWithSIWx } from "@x402/extensions/sign-in-with-x";
import { privateKeyToAccount } from "viem/accounts";

const signer = privateKeyToAccount(process.env.WALLET_PRIVATE_KEY);
const fetchWithSiwx = wrapFetchWithSIWx(fetch, signer);

const res = await fetchWithSiwx("https://laso.finance/auth");
const { auth, user_id } = await res.json();
```

A missing or failed signature returns `402 Payment Required` (never 401), with a fresh challenge base64-encoded in the `PAYMENT-REQUIRED` response header. Sign the new challenge and retry. A 402 received after sending a `SIGN-IN-WITH-X` header means the signature was rejected (invalid, expired, or nonce already used).

Response:

```json
{
  "auth": {
    "id_token": "eyJ...",
    "refresh_token": "AMf...",
    "expires_in": "3600"
  },
  "user_id": "0xabc..."
}
```

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

**Cost:** On-card amount plus a 3.8% fee, paid via x402. Min on-card $100, max $1,000.

Order an international non-reloadable prepaid card (USD). Unlike `/get-card`, international card orders are **queued** and fulfilled manually by a Laso admin — typically within 24 hours. Poll `/get-card-data?card_type=Non-Reloadable International` to check the status; when the card has been fulfilled, `card_details` will be populated.

If you change your mind, cancel a queued order via `POST /cancel-intl-order` — the charged amount is credited back to your account balance.

Parameters:

- `amount` (required): On-card USD amount. Min $100, max $1,000. The x402 payment is this amount plus a 3.8% fee.

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
  -H "Authorization: Bearer eyJ..." \
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

### GET /get-push-to-card — Send money to a USD, EUR, or GBP debit card

**Cost:** Dynamic. You specify the face value in the target currency; the x402 USDC price is the face value converted to USD plus a 4.8% fee (minimum fee of 1.50 in the target currency).

Supported currencies:

- `USD` — U.S. debit cards (U.S. bank account)
- `EUR` — Eurozone debit cards
- `GBP` — U.K. debit cards

Returns a `redemption_url` that must be opened to complete the transfer. The form requires multiple steps:

1. Sender name
2. Debit card number for receiving the funds
3. Cardholder name for that debit card

**Important:** Laso cannot perform the transfer directly. Either the agent or a human must open the `redemption_url` and fill out the form to complete the transfer.

Parameters:

- `amount` (required): Face value to send to the debit card, in `currency` (min 10, max 9,541.98).
- `currency` (optional): `USD` (default), `EUR`, or `GBP`.

```bash
# USD (default)
curl "https://laso.finance/get-push-to-card?amount=100"

# EUR
curl "https://laso.finance/get-push-to-card?amount=100&currency=EUR"

# GBP
curl "https://laso.finance/get-push-to-card?amount=100&currency=GBP"
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
  "success": true,
  "message": "Push-to-card transfer initiated. Open the redemption_url to enter your debit card details and complete the transfer.",
  "amount": 100,
  "currency": "EUR",
  "redemption_url": "https://pay.runa.io/...",
  "note": "The debit card must be tied to a Eurozone bank account."
}
```

**Next steps:** Open `redemption_url` in a browser and complete the multi-step form with the recipient's debit card details. The transfer is not complete until the form is submitted.

### GET /send-payment — Send a payment via Venmo or PayPal

**Cost:** Dynamic. The x402 USDC price is the requested `amount` plus a 4.9% fee with a \$1.50 minimum fee.

Send a payout to a Venmo or PayPal recipient. The on-chain USDC is always credited to the calling wallet's Laso account balance via the standard deposit webhook; the callable then debits the gross amount and dispatches the payout.

**KYC required.** The first time a wallet calls this endpoint, the response returns `kyc_required: true` and a `kyc_url`. Open the URL, complete the verification flow, and retry. If you don't want to proceed, the credited balance is recoverable via `POST /withdraw`.

Parameters:

- `platform` (required): `venmo` or `paypal`.
- `amount` (required): USD amount to send to the recipient (min \$5, max \$1,000).
- `recipient_id` (required): For Venmo, recipient's 10-digit U.S. phone number. For PayPal, recipient's email.
- `recipient_first_name` (required): English letters only.
- `recipient_last_name` (required): English letters only.
- `recipient_email`: Required for Venmo. Optional for PayPal, where it defaults to `recipient_id` (the PayPal email).

```bash
# Venmo
curl "https://laso.finance/send-payment?platform=venmo&amount=25&recipient_id=5551234567&recipient_first_name=Jane&recipient_last_name=Doe&recipient_email=jane%40example.com" \
  -H "X-Payment: <x402-payment-header>"

# PayPal (recipient_email defaults to recipient_id)
curl "https://laso.finance/send-payment?platform=paypal&amount=25&recipient_id=jane%40example.com&recipient_first_name=Jane&recipient_last_name=Doe" \
  -H "X-Payment: <x402-payment-header>"
```

Response (verified wallet):

```json
{
  "auth": {
    "id_token": "eyJ...",
    "refresh_token": "AMf...",
    "expires_in": "3600"
  },
  "user_id": "0xabc...",
  "success": true,
  "message": "Payment is being processed.",
  "platform": "venmo",
  "amount": 25,
  "recipient_id": "5551234567",
  "state": "in-process"
}
```

Response (unverified wallet):

```json
{
  "auth": {
    "id_token": "eyJ...",
    "refresh_token": "AMf...",
    "expires_in": "3600"
  },
  "user_id": "0xabc...",
  "kyc_required": true,
  "kyc_url": "https://api.sumsub.com/idensic/l/#/uni_...",
  "message": "KYC verification is required before sending Venmo or PayPal payouts. Complete the flow at kyc_url and retry, or call POST /withdraw to recover the funds credited to your account balance.",
  "platform": "venmo",
  "amount": 25,
  "recipient_id": "5551234567"
}
```

**Next steps:** If `kyc_required` is `true`, surface the `kyc_url` to a human and retry the request after they complete verification. Otherwise the payment is dispatched and will settle on Venmo or PayPal within minutes.

### GET /search-gift-cards — Search the gift card catalog

**Cost:** Free (requires Bearer token)

Browse and search available gift cards. Returns a list of gift card products with pricing, denomination, and catalog information. Use the `laso_server_id` from the results to order a card via `GET /order-gift-card`.

Parameters (all optional):

- `q`: Search query to filter by name (e.g. "Amazon", "Uber")
- `country`: ISO 3166-1 alpha-2 country code (e.g. "US", "GB"). Returns gift cards available in that country, including borderless products that have no country restriction.
- `currency`: Currency code (e.g. "USD", "EUR")
- `category`: Catalog category (e.g. "ecommerce", "travel", "gaming")

**Discovering valid filter values:** Every response includes a `facets` object listing all valid values for `category`, `currency`, and `country`. The facets are computed from the full catalog, not just the current results, so a single unfiltered request (`GET /search-gift-cards` with no query parameters) is enough to learn every value you can filter on. There is no separate "options" endpoint. Read `facets` first, then issue a filtered search.

Headers:

- `Authorization: Bearer <id_token>`

```bash
# Unfiltered request — read the `facets` object to discover valid filters
curl "https://laso.finance/search-gift-cards" \
  -H "Authorization: Bearer eyJ..."

# Filtered request using values discovered from `facets`
curl "https://laso.finance/search-gift-cards?q=amazon&country=US&category=ecommerce" \
  -H "Authorization: Bearer eyJ..."
```

Response:

```json
{
  "gift_cards": [
    {
      "laso_server_id": "amazon-us",
      "name": "Amazon",
      "description": "Amazon.com Gift Card",
      "category": "ecommerce",
      "country": "US",
      "currency": "USD",
      "min": 5,
      "max": 500,
      "increment": "1",
      "denominations": null,
      "product_image_url": "https://...",
      "catalog_info": {
        "brand_description": "Shop millions of products on Amazon.com",
        "redemption_instructions": "Go to amazon.com/redeem and enter the code"
      }
    }
  ],
  "count": 1,
  "filters": {
    "query": "amazon",
    "country": "US",
    "currency": null,
    "category": "ecommerce"
  },
  "facets": {
    "categories": ["ecommerce", "travel", "gaming", "streaming"],
    "currencies": ["USD", "EUR", "GBP", "CAD"],
    "countries": ["US", "GB", "DE", "CA"]
  }
}
```

### GET /order-gift-card — Order a gift card

**Cost:** \$5-\$9,000 USDC (x402 paywalled, dynamic pricing matches the amount parameter)

Order a gift card from the catalog. First browse available cards via `GET /search-gift-cards` to find the `laso_server_id`, then call this endpoint with the amount and product ID.

Parameters:

- `amount` (required): Gift card face value in the product's currency. Min $5, max $9,000.
- `laso_server_id` (required): The product identifier from the catalog (`GET /search-gift-cards`).
- `country` (optional): ISO 3166-1 alpha-2 country code. Defaults to "US".

```bash
curl "https://laso.finance/order-gift-card?amount=50&laso_server_id=amazon-us"
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
  "gift_card": {
    "card_id": "gc_abc123",
    "laso_server_id": "amazon-us",
    "amount": 50,
    "currency": "USD",
    "country": "US",
    "redemption_url": null,
    "redemption_code": "XXXX-XXXX-XXXX",
    "pin_code": null,
    "status": "completed",
    "timestamp": 1700000000000
  }
}
```

Redemption details vary by brand. Some cards return a `redemption_url`, others a `redemption_code` and/or `pin_code`. Check all three fields.

### GET /get-card-data — Get card details

**Cost:** Free (requires Bearer token)

Returns card status and details for both U.S. and international non-reloadable cards. If `card_id` is provided, returns the single matching card (the endpoint looks it up across both card types). If `card_id` is omitted, returns all cards of the given `card_type` — which defaults to `"Non-Reloadable U.S."` when omitted, so existing clients that previously called this endpoint without `card_type` continue to work unchanged. Pass `card_type=Non-Reloadable International` to list international cards instead.

After ordering a U.S. card via `/get-card`, poll this endpoint every 2-3 seconds until `status` is `"ready"`. For international cards ordered via `/order-intl-card`, the card stays `queued` until an admin fulfills it (typically within 24 hours), then moves to `ready`. International responses also include `label`, `charged_usd_amount`, `fees_paid`, `state`, `balance_update_requested_timestamp`, `queued_order_card_id`, and a `transactions` array (each entry has `amount`, `date`, `merchant`, `status`).

Possible `status` values:

- U.S. cards: `pending`, `ready`.
- International cards: `queued` (waiting for admin fulfillment), `ready` (card details available), `complete` (card fully spent), `refund-requested`, `refunded`, `archived`.

After admin fulfillment, the international `card_id` is reissued to the issuer's transaction id. The original queue id is preserved on the card as `queued_order_card_id`, and `/get-card-data?card_id=<original-queue-id>` continues to resolve to the fulfilled card, so you can keep polling with the same id.

Parameters:

- `card_id` (optional): The card ID from `/get-card` or `/order-intl-card`. If omitted, returns all cards of `card_type`.
- `card_type` (optional): Which card type to list when `card_id` is omitted. `"Non-Reloadable U.S."` (default) or `"Non-Reloadable International"`.

Headers:

- `Authorization: Bearer <id_token>` (from `/auth` or `/get-card` response)

```bash
# Single card (works for both U.S. and international)
curl "https://laso.finance/get-card-data?card_id=card_abc123" \
  -H "Authorization: Bearer eyJ..."

# All U.S. cards (default when card_type is omitted)
curl "https://laso.finance/get-card-data" \
  -H "Authorization: Bearer eyJ..."

# All international cards
curl "https://laso.finance/get-card-data?card_type=Non-Reloadable%20International" \
  -H "Authorization: Bearer eyJ..."
```

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

**Billing address / ZIP.** When a merchant asks for a billing address or ZIP code at checkout, use the `billing_address` in `card_details`. The billing **name** is always `Laso Finance`. Requirements differ by card type:

- **USA non-reloadable** (`/get-card`): no fixed billing address is enforced, so any valid U.S. billing address works. The `billing_address` returned is a known-good default (ZIP `91723`) you may use if you don't have your own.
- **International non-reloadable** (`/order-intl-card`): the merchant AVS check is validated against Laso's address, so you must use exactly the returned `billing_address` (ZIP `91723`). `required` is `true` in the response.

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

### GET /get-account-balance — Get account balance

**Cost:** Free (requires Bearer token)

Returns the current account balance and total deposits.

Headers:

- `Authorization: Bearer <id_token>`

```bash
curl "https://laso.finance/get-account-balance" \
  -H "Authorization: Bearer eyJ..."
```

Response:

```json
{
  "user_id": "0xabc...",
  "balance": 150.0,
  "total_deposits": 500.0,
  "created_timestamp": 1700000000000,
  "created_timestamp_readable": "1/15/2025, 3:00:00 PM"
}
```

### GET /get-kyc-status — Check KYC verification status

**Cost:** Free (requires Bearer token)

> **KYC is optional.** Most endpoints (cards, gift cards, push-to-card, account balance, withdrawals) need no verification. It is only required for certain features such as Venmo/PayPal payouts via `/send-payment`, and may be used for additional controls later. Ignore these two verification endpoints unless you're using a KYC-gated feature.

Returns whether the calling wallet has completed identity verification. Call this **before** paying for `/send-payment`: Venmo and PayPal payouts require a verified wallet, so checking first avoids paying for a send that comes back as `kyc_required`.

This reads the cached status kept current by the verification webhook. It does not start verification or return a verification link. When `kyc_verified` is `false`, call `/get-kyc-link` to get a verification link, complete it, then call `/send-payment`.

Headers:

- `Authorization: Bearer <id_token>`

```bash
curl "https://laso.finance/get-kyc-status" \
  -H "Authorization: Bearer eyJ..."
```

Response:

```json
{
  "user_id": "0xabc...",
  "kyc_verified": false,
  "kyc_review_status": "completed",
  "kyc_review_answer": "RED",
  "kyc_last_reviewed_at": 1700000000000
}
```

### GET /get-kyc-link — Get a KYC verification link

**Cost:** Free (requires Bearer token)

> **Optional**, only needed for KYC-gated features like `/send-payment`.

Returns a one-time identity-verification link (`kyc_url`) for the calling wallet. Open it (or give it to the wallet owner) to complete verification. Use it only when `/get-kyc-status` shows `kyc_verified: false` and you intend to use a KYC-gated feature.

Headers:

- `Authorization: Bearer <id_token>`

```bash
curl "https://laso.finance/get-kyc-link" \
  -H "Authorization: Bearer eyJ..."
```

Response:

```json
{
  "user_id": "0xabc...",
  "kyc_url": "https://api.sumsub.com/idensic/l/#/uni_..."
}
```

### POST /withdraw — Withdraw from account balance

**Cost:** Free (requires Bearer token)

Initiate a withdrawal from your account balance. Minimum amount is $0.01.

Headers:

- `Authorization: Bearer <id_token>`
- `Content-Type: application/json`

Body:

- `amount` (required): USD amount to withdraw.

```bash
curl -X POST "https://laso.finance/withdraw" \
  -H "Authorization: Bearer eyJ..." \
  -H "Content-Type: application/json" \
  -d '{"amount": 50}'
```

Response:

```json
{
  "success": true,
  "withdrawal": {
    "id": "withdrawal_abc123",
    "amount": 50,
    "state": "pending",
    "timestamp": 1700000000000,
    "timestamp_readable": "1/15/2025, 3:00:00 PM"
  }
}
```

### GET /get-withdrawal-status — Get withdrawal statuses

**Cost:** Free (requires Bearer token)

Returns the status of withdrawals for the authenticated user. If `withdrawal_id` is provided, returns a single withdrawal. If omitted, returns all withdrawals.

Parameters:

- `withdrawal_id` (optional): Get a specific withdrawal by ID. If omitted, returns all withdrawals.

Headers:

- `Authorization: Bearer <id_token>`

```bash
# Single withdrawal
curl "https://laso.finance/get-withdrawal-status?withdrawal_id=abc123" \
  -H "Authorization: Bearer eyJ..."

# All withdrawals
curl "https://laso.finance/get-withdrawal-status" \
  -H "Authorization: Bearer eyJ..."
```

Response for a single withdrawal:

```json
{
  "withdrawal": {
    "id": "abc123",
    "amount": 50,
    "asset": "USDC",
    "network": "BASE_MAINNET",
    "state": "completed",
    "address": "0xabc...",
    "timestamp": 1700000000000,
    "timestamp_readable": "1/15/2025, 3:00:00 PM",
    "tx_hash": "0xdef...",
    "tx_url": "https://basescan.org/tx/0xdef..."
  }
}
```

Response for all withdrawals:

```json
{
  "withdrawals": [
    {
      "id": "abc123",
      "amount": 50,
      "asset": "USDC",
      "network": "BASE_MAINNET",
      "state": "pending",
      "address": "0xabc...",
      "timestamp": 1700000000000,
      "timestamp_readable": "1/15/2025, 3:00:00 PM",
      "tx_hash": null
    }
  ]
}
```

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
  -H "Authorization: Bearer eyJ..." \
  -H "Content-Type: application/json" \
  -d '{"card_id": "card_abc123"}'

# International card
curl -X POST "https://laso.finance/refresh-card-data" \
  -H "Authorization: Bearer eyJ..." \
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
  -H "Authorization: Bearer eyJ..."

# International prepaid card
curl "https://laso.finance/search-merchants?q=amazon&card_type=Non-Reloadable%20International" \
  -H "Authorization: Bearer eyJ..."
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

### GET /get-auth-link — Get a login link for the web dashboard

**Cost:** Free (requires Bearer token)

Returns a URL that a human can open in a browser to log in to the Laso Finance web dashboard as the authenticated user. Useful when a human wants to see what their AI agent has been doing (view cards, transactions, balances, etc.).

Headers:

- `Authorization: Bearer <id_token>`

```bash
curl "https://laso.finance/get-auth-link" \
  -H "Authorization: Bearer eyJ..."
```

Response:

```json
{
  "auth_url": "https://laso.finance/?authToken=eyJ...",
  "user_id": "0xabc..."
}
```

The `auth_url` is a one-time login link. Open it in a browser to access the dashboard. The token expires after a short time, so generate a new link if needed.

### POST /submit-agent-feedback — Send feedback about the API

**Cost:** Free (requires Bearer token)

Share feedback about the Laso API with the humans who run it: what worked, what was confusing, what you wish existed. It reaches their dashboard directly, so it is the best channel for reporting API friction or requesting features.

This endpoint is served from the Cloud Function URL, not `laso.finance`. Send the `id_token` from `/auth` as a Bearer token. You must have completed at least one real action (a settled deposit, purchase, or withdrawal) before feedback is accepted, and you may submit at most 5 entries per 24 hours.

Body fields (all `snake_case`, JSON):

- `feedback` (required, string): the main free-text feedback.
- `what_they_want` (optional, string): what you were trying to do.
- `how_it_went` (optional, string): how it went.
- `endpoint` (optional, string): which endpoint or route the feedback is about.
- `rating` (optional, integer 1-5): a satisfaction rating.

```bash
curl -X POST https://us-central1-kyc-ts.cloudfunctions.net/submitAgentFeedback \
  -H "Authorization: Bearer eyJ..." \
  -H "Content-Type: application/json" \
  -d '{"feedback":"order-intl-card was smooth but I wanted a way to see the fee before paying","what_they_want":"order an international card","how_it_went":"worked, minor confusion on fees","endpoint":"/order-intl-card","rating":4}'
```

Response:

```json
{ "ok": true }
```

Failures: `401` if the Bearer token is missing or invalid, `403` if you have not completed a real action yet, `429` if you have hit the daily feedback limit, `400` if `feedback` is empty.

### POST /auth — Refresh an expired ID token

**Cost:** Free

Exchange a refresh token for a new ID token using the standard OAuth2 `grant_type=refresh_token` pattern. No x402 payment required.

```bash
curl -X POST https://laso.finance/auth \
  -H "Content-Type: application/json" \
  -d '{"grant_type": "refresh_token", "refresh_token": "AMf..."}'
```

Response:

```json
{
  "id_token": "eyJ...",
  "refresh_token": "AMf...",
  "expires_in": "3600",
  "user_id": "0xabc..."
}
```

## Common workflow: Make an online purchase

Cards are non-reloadable, so ideally you should order a card for the exact amount of the checkout total. That way there are no extra funds left over on the card.

1. **Set up wallet**: Follow https://paywithlocus.com/SKILL.md (Locus), https://wallet.paysponge.com/skill.md (Sponge), or https://www.ampersend.ai/getting-started.md (Ampersend) to get a wallet with USDC on Base or Solana.
2. **Navigate to checkout**: Browse the merchant's website, add items to cart, and proceed to checkout. Determine the exact total including tax and shipping.
3. **Order a card for the exact amount**: `GET /get-card?amount=<exact_total>` (pays via x402). Save the `auth.id_token` and `card.card_id` from the response.
4. **Poll for details**: `GET /get-card-data?card_id=<cardId>` with `Authorization: Bearer <id_token>`. Repeat every 2-3 seconds.
5. **Complete the purchase**: When `status` is `"ready"`, use `card_details.card_number`, `card_details.cvv`, `card_details.exp_month`, `card_details.exp_year` to fill in the payment form on the checkout page.

## Common workflow: Send to a debit card

1. **Set up wallet**: Follow https://paywithlocus.com/SKILL.md (Locus), https://wallet.paysponge.com/skill.md (Sponge), or https://www.ampersend.ai/getting-started.md (Ampersend) to get a wallet with USDC on Base or Solana.
2. **Initiate transfer**: `GET /get-push-to-card?amount=100&currency=USD` (or `EUR` / `GBP`). The x402 USDC price is the face value converted to USD plus a 4.8% fee (minimum fee of 1.50 in the chosen currency). Save the `redemption_url` from the response.
3. **Complete the transfer**: Open `redemption_url` in a browser. Fill out the multi-step form with the sender name, debit card number (matching the chosen currency's region), and cardholder name.

## Common workflow: Order a gift card

1. **Set up wallet**: Follow https://paywithlocus.com/SKILL.md (Locus), https://wallet.paysponge.com/skill.md (Sponge), or https://www.ampersend.ai/getting-started.md (Ampersend) to get a wallet with USDC on Base or Solana.
2. **Authenticate**: `GET /auth` to get an `id_token` (free, send a `SIGN-IN-WITH-X` header).
3. **Browse catalog**: `GET /search-gift-cards?q=amazon` with `Authorization: Bearer <id_token>`. Find the `laso_server_id` for the desired card.
4. **Order the card**: `GET /order-gift-card?amount=50&laso_server_id=amazon-us` (pays $50 USDC via x402). The response contains the redemption details immediately.

## Token management

- The `id_token` expires after ~1 hour.
- When it expires, call `POST /auth` with `grant_type: "refresh_token"` and your `refresh_token` to get a new `id_token`.
- `/auth` and `/get-card` return fresh `id_token` and `refresh_token` in the response. Always save these tokens so you can refresh later or use the `id_token` for authenticated endpoints.

## Technical details

- Networks: Base (eip155:8453) and Solana (solana:5eykt4UsFv8P8NJdTREpY1vzqKqZKvdp)
- Currency: USDC
- Base payment recipient: `0x3291e96b3bff7ed56e3ca8364273c5b4654b2b37`
- Solana payment recipient: `3MZVk97x9SeRxbYpc3jhzRfU2fyA3emYutnqfn9kNfYX`
- OpenAPI spec: https://laso.finance/openapi.json
- AI plugin manifest: https://laso.finance/.well-known/ai-plugin.json
- LLM context: https://laso.finance/llms.txt

## Support

If you encounter issues, contact agents+support@laso.finance.

## Limitations

- The USA prepaid card (`/get-card`) is U.S. only (USD, U.S. merchants, U.S. shipping addresses) but is issued instantly.
- The international prepaid card (`/order-intl-card`) is usable globally (USD, any merchant, any shipping address) but orders are queued for admin fulfillment — typically within 24 hours — and carry a 3.8% fee.
- USA card details take ~7-10 seconds after ordering. You must poll `/get-card-data`.
- Push-to-card USD is U.S. only (the debit card must be tied to a U.S. bank account); EUR is Eurozone-only; GBP is U.K.-only. The `redemption_url` must be opened and the form completed manually.
- Card and account limits may apply based on usage patterns.
