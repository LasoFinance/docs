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
