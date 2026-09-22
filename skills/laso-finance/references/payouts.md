# Debit card, Venmo, PayPal, and bank payouts

Read this reference only for this task. For setup and session renewal, use [SKILL.md](https://laso.finance/SKILL.md). For managed accounts, the helper saves a usable token at `~/.laso/credentials.json`. In the same shell operation as the examples below, load it with `export LASO_ID_TOKEN="$(jq -r .id_token ~/.laso/credentials.json)"`; exports in separate tool calls may not persist.

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
- `recipient_id` (required): For Venmo, recipient's 10-digit U.S. phone number. For PayPal, recipient's email. If your human names someone they have paid before rather than giving you the number, read [GET /payment-recipients](#get-payment-recipients--list-who-this-account-has-paid-before) first and match on the saved name.
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

**Next steps:** If `kyc_required` is `true`, surface the `kyc_url` to a human and retry the request after they complete verification. Otherwise the payment is dispatched and will settle on Venmo or PayPal within minutes. Follow it with [GET /get-payment-status](#get-get-payment-status--check-venmo-and-paypal-payout-status).

### GET /get-payment-status — Check Venmo and PayPal payout status

**Cost:** Free. Reading the state of a payout costs nothing; only `GET /send-payment` is paywalled.

`GET /send-payment` answers as soon as the payout is dispatched, not when the money lands. Use this route to find out whether it did, and to tell your human which payouts are still in flight.

**Parameters** (all optional)

- `payment_id`: one payout by its `id`. Takes precedence over `recipient_id`.
- `recipient_id`: every payout to one saved recipient. This is the `recipient_id` that `GET /payment-recipients` returns, not the phone number or email.
- Neither: every Venmo and PayPal payout this account has sent, newest first.

```bash
# One payout
curl "https://laso.finance/get-payment-status?payment_id=otlUYhH8n7Q2KWmt6FBs" \
  -H "Authorization: Bearer $LASO_ID_TOKEN"

# Everything sent from this account
curl "https://laso.finance/get-payment-status" \
  -H "Authorization: Bearer $LASO_ID_TOKEN"
```

Response for one payout (the list forms return the same objects under `payments`, newest first):

```json
{
  "payment": {
    "id": "otlUYhH8n7Q2KWmt6FBs",
    "amount_pre_fees": 10,
    "amount_with_fees": 11.5,
    "fees_paid": 1.5,
    "platform": "venmo",
    "state": "complete",
    "state_updated_at": 1789365621369,
    "recipient_id": "Bh3bHdQwErTyUiOpAsDf",
    "recipient_first_name": "Jane",
    "recipient_last_name": "Doe",
    "timestamp": 1789364854261,
    "timestamp_readable": "9/14/2026, 6:47:34 AM"
  }
}
```

`amount_pre_fees` is what the recipient receives; `amount_with_fees` is what left the account balance. `state` is one of:

- `queued`: waiting for the account balance to cover it.
- `in-process`: handed to Venmo or PayPal. Normally completes within minutes.
- `complete`: the recipient has the money.
- `failed` or `cancelled`: the money was not delivered. The debited balance is credited back.

`queued` and `in-process` are the two states still in flight. Poll every few minutes, or register a webhook with `POST /register-webhook` (see [account.md](account.md)) to be told when a payout completes instead. A payout still `in-process` after an hour is worth raising with your human. `state` is absent on payouts sent before state tracking existed.

A `payment_id` that matches nothing on this account returns `404` with code `payment_not_found`. Bank payouts are not listed here; follow those with `listBankingTransactions` (see [banking.md](banking.md)). Push-to-card transfers are completed by the recipient in the browser and have no server-side state.

### GET /payment-recipients — List who this account has paid before

**Cost:** Free. Reading and organizing who you can pay costs nothing; only `GET /send-payment` is paywalled.

`GET /send-payment` needs a `recipient_id`: a 10-digit phone number for Venmo, an email address for PayPal. Rather than asking your human to retype one they have used before, read the saved list first and match on the name they said.

**Parameters**

- `platform` (required): `venmo` or `paypal`.
- `include_archived`: `true` to include entries that were archived. Defaults to `false`.

```bash
curl "https://laso.finance/payment-recipients?platform=venmo" \
  -H "Authorization: Bearer $LASO_ID_TOKEN"
```

```json
{
  "user_id": "usr_...",
  "platform": "venmo",
  "recipients": [
    {
      "recipient_id": "5551234567",
      "handle": "5551234567",
      "name": "Jane Doe",
      "display_name": "Jane (rent)",
      "status": "active",
      "total_sent": 450,
      "send_count": 6,
      "last_sent_timestamp": 1789000000000
    }
  ]
}
```

`recipient_id` is exactly what `GET /send-payment` takes. `display_name` is the label your human chose, so prefer it when confirming an amount back to them; `name` is the account's own name on the platform. Use `total_sent` and `last_sent_timestamp` to disambiguate when two entries have similar names, and confirm with your human rather than guessing between them.

### POST /payment-recipients — Rename or archive a saved recipient

**Cost:** Free.

Send a JSON body with `platform`, `recipient_id`, and at least one of `display_name` or `archived`. Archiving hides an entry from the default list without losing its history, which is the reversible way to retire a recipient.

```bash
curl -X POST "https://laso.finance/payment-recipients" \
  -H "Authorization: Bearer $LASO_ID_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"platform":"venmo","recipient_id":"5551234567","display_name":"Jane (rent)"}'
```

```json
{
  "user_id": "usr_...",
  "platform": "venmo",
  "recipient_id": "5551234567",
  "display_name": "Jane (rent)"
}
```

`display_name` must be a string and `archived` must be a boolean; sending either as the wrong type returns a terminal `400` with a `code` of `invalid_display_name` or `invalid_archived`, so correct the type rather than retrying the same body.

### DELETE /payment-recipients — Remove a saved recipient

**Cost:** Free.

Takes `platform` and `recipient_id`, in either the JSON body or the query string. Payment history is kept; only the saved entry stops being offered. **Prefer archiving** (`POST` with `"archived": true`) when your human may want the recipient back, because deletion is not reversible from the API.

```bash
curl -X DELETE "https://laso.finance/payment-recipients?platform=venmo&recipient_id=5551234567" \
  -H "Authorization: Bearer $LASO_ID_TOKEN"
```

```json
{
  "user_id": "usr_...",
  "recipient_id": "5551234567",
  "deleted": true
}
```

Deleting someone your human did not ask you to remove is not recoverable through this API, so confirm before calling it.

### GET /send-bank-payment — Send dollars to a bank account

**Cost:** Dynamic. The x402 USDC price is the requested `amount` plus a 0.25% transfer fee with a \$1.50 minimum fee.

Sends dollars to a bank account by ACH. The on-chain USDC is credited to the calling wallet's Laso account balance via the standard deposit webhook; the callable then debits the gross amount and queues the transfer.

**Set up the destination first.** `destination_id` comes from the banking callables described in [Bank accounts for the managed account](banking.md#bank-accounts-for-the-managed-account-on-ramp-and-off-ramp): `createBankingProfile`, then `createBankingRecipient`, then `addBankingDestination` (which returns the id). `GET /bank-recipients` lists what you already have. The banking profile requires identity verification by the account owner, which only they can complete.

Parameters:

- `amount` (required): USD delivered to the recipient's bank account (min \$10, max \$50,000).
- `destination_id` (required): the bank destination to pay out to.

```bash
curl "https://laso.finance/send-bank-payment?amount=250&destination_id=dest_123" \
  -H "X-Payment: <x402-payment-header>"
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
  "message": "Bank payment is being processed. It settles by ACH, which normally takes 1-2 business days.",
  "bank_payment": {
    "payout_id": "abc123",
    "amount": 250,
    "fee_amount": 1.5,
    "charged_amount": 251.5,
    "destination_id": "dest_123",
    "state": "in-process",
    "destination": {
      "name": "Jane checking",
      "bank_name": "Chase",
      "account_holder_name": "Jane Doe",
      "account_number_last4": "6789"
    }
  }
}
```

**If it fails**, nothing is stranded. The USDC you paid has already credited your account balance, so fix what the error names (usually an unapproved banking profile, or a `destination_id` that is not yours) and retry, or call `POST /withdraw` to move the funds back to your wallet.

**Next steps:** follow the transfer with `listBankingTransactions` / `getBankingTransaction`. ACH normally settles in 1-2 business days.

### GET /bank-recipients — List bank payout recipients

**Cost:** Free (requires Bearer token)

Lists the recipients on your banking profile and the destinations attached to each, so you can find the `destination_id` for `GET /send-bank-payment`. Registering recipients is free; only the payout costs anything.

```bash
curl https://laso.finance/bank-recipients \
  -H "Authorization: Bearer $LASO_ID_TOKEN"
```

Response:

```json
{
  "user_id": "0xabc...",
  "recipients": [
    {
      "recipient_id": "rcp_123",
      "name": "Jane Doe",
      "status": "active",
      "destinations": [
        {
          "destination_id": "dest_123",
          "destination_type": "fiat_us",
          "name": "Jane checking",
          "nickname": "Rent account",
          "bank_name": "Chase",
          "account_holder_name": "Jane Doe",
          "account_number_last4": "6789",
          "routing_number": "021000021"
        }
      ]
    }
  ]
}
```

Account numbers come back masked to their last four digits; routing numbers are returned in full. `nickname` appears only when one is set. Create new recipients and destinations with `createBankingRecipient` and `addBankingDestination`, rename with `updateBankingDestination`, and remove with `deleteBankingRecipient` (see [Managing recipients](banking.md#bank-accounts-for-the-managed-account-on-ramp-and-off-ramp)).

## Common workflow: Send to a debit card

1. **Have a way to pay**: If you already have a Locus, Sponge, or Ampersend wallet, use it. Otherwise use a Laso managed wallet (see [setup](https://laso.finance/SKILL.md)) and pay with `agentX402Pay`.
2. **Initiate transfer**: `GET /get-push-to-card?amount=100&currency=USD` (or `EUR` / `GBP`). The x402 USDC price is the face value converted to USD plus a 4.8% fee (minimum fee of 1.50 in the chosen currency). Save the `redemption_url` from the response.
3. **Complete the transfer**: Open `redemption_url` in a browser. Fill out the multi-step form with the sender name, debit card number (matching the chosen currency's region), and cardholder name.
