# Account, verification, withdrawals, and webhooks

Read this reference only for this task. For setup and session renewal, use [SKILL.md](https://laso.finance/SKILL.md). For managed accounts, the helper saves a usable token at `~/.laso/credentials.json`. In the same shell operation as the examples below, load it with `export LASO_ID_TOKEN="$(jq -r .id_token ~/.laso/credentials.json)"`; exports in separate tool calls may not persist.

### GET /get-account-balance — Get account balance

**Cost:** Free (requires Bearer token)

Returns the current account balance and total deposits.

Headers:

- `Authorization: Bearer <id_token>`

```bash
curl "https://laso.finance/get-account-balance" \
  -H "Authorization: Bearer $LASO_ID_TOKEN"
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
  -H "Authorization: Bearer $LASO_ID_TOKEN"
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
  -H "Authorization: Bearer $LASO_ID_TOKEN"
```

Response:

```json
{
  "user_id": "0xabc...",
  "kyc_url": "https://api.sumsub.com/idensic/l/#/uni_..."
}
```

### POST /register-webhook — Receive notifications by webhook

**Cost:** Free (requires Bearer token)

Registers (or replaces) an HTTPS URL that receives every notification for the calling account as a signed POST: banking application status changes, bank transfer and payout completions, agent wallet deposits, card orders, withdrawals, and anything else the account owner is notified about. Use it instead of polling status endpoints on a timer. If your runtime cannot receive inbound HTTP, point it at your harness's inbound webhook/gateway endpoint or a relay you can poll, or skip this and keep polling.

Body:

- `url` (required): public HTTPS URL, max 512 characters. Private/internal hosts are rejected.

```bash
curl -X POST "https://laso.finance/register-webhook" \
  -H "Authorization: Bearer $LASO_ID_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://agent.example.com/hooks/laso"}'
```

Response:

```json
{
  "registered": true,
  "url": "https://agent.example.com/hooks/laso",
  "secret": "whsec_EXAMPLEONLYnotarealsecretAAAAAAA",
  "signing": "standard-webhooks"
}
```

**The `secret` is returned only here.** Store it; re-registering rotates it. Registering fires a first signed test delivery (`type` of `notification.account`) at the URL and notifies the account owner that an agent registered a webhook.

Each delivery is a POST with body `{"type": "notification.<category>", "timestamp": "<ISO 8601>", "data": {"user_id", "title", "text", "category"}}` and Standard Webhooks headers (`webhook-id`, `webhook-timestamp`, `webhook-signature: v1,<base64 HMAC-SHA256>`), verifiable with any standard-webhooks library (https://www.standardwebhooks.com/). The signed content is `{webhook-id}.{webhook-timestamp}.{raw body}` keyed with the base64-decoded portion of the secret after `whsec_`. Categories: `account`, `transaction`, `deposit`, `withdrawal`, `card`, `giftCard`, `refund`, `balanceUpdate`.

Deliveries time out after 10 seconds and are not retried; treat them as low-latency hints and the status endpoints as the source of truth. After 50 consecutive failed deliveries the registration auto-disables; re-register to re-enable.

### GET /get-webhook — Check webhook registration and delivery health

**Cost:** Free (requires Bearer token)

Returns the registration (`registered: false` when none) and delivery health. The secret is never returned here.

```bash
curl "https://laso.finance/get-webhook" \
  -H "Authorization: Bearer $LASO_ID_TOKEN"
```

Response:

```json
{
  "registered": true,
  "url": "https://agent.example.com/hooks/laso",
  "disabled": false,
  "disabled_reason": null,
  "consecutive_failures": 0,
  "last_delivery_status": "delivered",
  "last_delivery_timestamp": 1753900000000,
  "last_delivery_detail": "HTTP 200",
  "last_delivery_message_id": "msg_a1b2c3d4e5f6a7b8c9d0e1f2"
}
```

### POST /delete-webhook — Remove the webhook

**Cost:** Free (requires Bearer token)

Removes the registration. The account owner keeps their other notification channels; only webhook deliveries stop. Returns `{"deleted": true}` (or `false` when nothing was registered).

```bash
curl -X POST "https://laso.finance/delete-webhook" \
  -H "Authorization: Bearer $LASO_ID_TOKEN"
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
  -H "Authorization: Bearer $LASO_ID_TOKEN" \
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
  -H "Authorization: Bearer $LASO_ID_TOKEN"

# All withdrawals
curl "https://laso.finance/get-withdrawal-status" \
  -H "Authorization: Bearer $LASO_ID_TOKEN"
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

### GET /get-auth-link — Get a login link for the web dashboard

**Cost:** Free (requires Bearer token)

Returns a URL that a human can open in a browser to log in to the Laso Finance web dashboard as the authenticated user. Useful when a human wants to see what their AI agent has been doing (view cards, transactions, balances, etc.).

Headers:

- `Authorization: Bearer <id_token>`

```bash
curl "https://laso.finance/get-auth-link" \
  -H "Authorization: Bearer $LASO_ID_TOKEN"
```

Response:

```json
{
  "auth_url": "https://laso.finance/agent/dashboard/auth?code=K7MPQ-W3XZ9",
  "user_id": "0xabc...",
  "expires_in": 900
}
```

The `auth_url` is a one-time login link for your human. Pass it back exactly as received; it carries only a short single-use login code (no long token), so it survives tool-output credential filters and is safe to paste in full. Do not open or fetch it yourself, since redeeming the code consumes the human's login. The code expires after 15 minutes (`expires_in` is in seconds), so generate a new link if needed.

### POST /feedback — Send feedback about the API

**Cost:** Free (requires Bearer token)

Tell the humans running Laso what worked, what was confusing, and what you wish existed. It lands on their dashboard, so it is the best channel for API friction and feature requests.

Served from the Cloud Function URL, not `laso.finance`. Requires at least one completed real action (a settled deposit, purchase, or withdrawal); at most 5 entries per 24 hours.

```bash
curl -X POST https://us-central1-kyc-ts.cloudfunctions.net/feedback \
  -H "Authorization: Bearer $LASO_ID_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"feedback":"order-intl-card was smooth but I wanted to see the fee before paying","endpoint":"/order-intl-card","rating":4}'
```

JSON body: `feedback` (required). Optional: `what_they_want`, `how_it_went`, `endpoint`, `rating` (1-5).

Returns `{ "ok": true }`. Errors: `400` empty `feedback`, `401` bad token, `403` no completed action yet, `429` daily limit reached.
