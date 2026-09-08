# Bank accounts

Read this reference only for this task. For setup and session renewal, use [SKILL.md](https://laso.finance/SKILL.md). For managed accounts, the helper saves a usable token at `~/.laso/credentials.json`. In the same shell operation as the examples below, load it with `export LASO_ID_TOKEN="$(jq -r .id_token ~/.laso/credentials.json)"`; exports in separate tool calls may not persist.

## Bank accounts for the managed account (on-ramp and off-ramp)

Optional, managed accounts only. Laso can open real banking rails for the account through its banking partner: an **on-ramp** account (a virtual US bank account; dollars sent to it arrive as USDC in the managed wallet) and an **off-ramp** account (a crypto deposit address; USDC sent to it pays out to a bank account). All calls are Firebase callables using the `id_token` from sign-in, with the `{ "data": ... }` body wrapping and `{ "result": ... }` response wrapping shown above.

**Step 1 — create the banking profile.** Identity verification is required first, the same verification used for Venmo/PayPal payouts. If the human has not verified yet, this returns a link to give them; retry after they finish.

```bash
curl https://laso.finance/createBankingProfile \
  -H "Authorization: Bearer $LASO_ID_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"data":{"userId":"usr_..."}}'
```

Responses:

- Not yet verified: `{ "result": { "kycRequired": true, "kycUrl": "https://..." } }`. Give `kycUrl` to your human, wait for them to finish, then call again. **This is the only step you cannot do yourself** — identity verification must be completed by the account owner in person.
- Verified: `{ "result": { "profileId": "...", "applicationStatus": "...", "applicationUrl": "https://..." } }`. Identity carries over automatically. A few non-identity questions remain (employment status, source of funds, terms) — you can answer these yourself with `getBankingApplication` + `updateBankingApplicationDetails` + `submitBankingApplication` (step 1b), or hand `applicationUrl` to your human if you would rather they did.

**Step 1b — complete and submit the application yourself.** Read what is outstanding:

```bash
curl https://laso.finance/getBankingApplication \
  -H "Authorization: Bearer $LASO_ID_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"data":{"userId":"usr_..."}}'
```

Returns `{ "result": { "applicationId": "...", "applicationStatus": "...", "ready": false, "missingFields": ["ssn"], "hostedOnly": false, "statusMessage": "..." } }`.

If `hostedOnly` is `true`, this application can only be finished on the partner's own page — give `applicationUrl` to your human and skip to step 2. Otherwise submit the details:

```bash
curl https://laso.finance/updateBankingApplicationDetails \
  -H "Authorization: Bearer $LASO_ID_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"data":{
        "userId":"usr_...",
        "firstName":"Jane","lastName":"Doe",
        "dateOfBirth":"1990-04-17",
        "nationalities":["US"],
        "emailAddress":"jane@example.com",
        "address":{"street1":"1 Main St","city":"Austin","region":"TX","postal_code":"78701","country":"US"},
        "employmentStatus":"employed",
        "purposeOfAccount":["sending_and_receiving_payments"],
        "sourceOfWealth":["employment"],
        "ssn":"123456789"
      }}'
```

Field rules (all validated server-side, so a bad value returns `invalid-argument` rather than failing silently):

- `dateOfBirth` — ISO `YYYY-MM-DD`; the person must be 18 or older.
- `nationalities` — non-empty array of ISO 3166-1 alpha-2 codes, e.g. `["US"]`.
- `employmentStatus` — one of `employed`, `self_employed`, `unemployed`, `student`, `retired`.
- `purposeOfAccount` — non-empty array from `investing`, `sending_and_receiving_payments`, `storage_of_funds_or_digital_assets`, `making_online_payments`, `trading_on_other_platforms`.
- `sourceOfWealth` — non-empty array from `investments`, `employment`, `court_settlement`, `lottery_winnings`, `retirement_income`, `savings`, `sale_of_assets`, `family_funds`, `gambling_winnings`, `gift`, `inheritance`, `insurance_claim`, `loan`, `redundancy_severance`, `benefits`.
- `ssn` — required for US persons; nine digits, no hyphens. `getBankingApplication` reports it in `missingFields` when it is needed.

**These are the account owner's real personal details.** Only send values the owner actually gave you. Do not invent, guess, or infer them — a wrong answer on a bank application is a compliance problem for your human, not a retryable error.

Then submit:

```bash
curl https://laso.finance/submitBankingApplication \
  -H "Authorization: Bearer $LASO_ID_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"data":{"userId":"usr_..."}}'
```

The required legal attestations (e-sign, terms of service, privacy policy, funds transfer agreement) are accepted on the account owner's behalf as part of this call, in the order the partner requires. Only call it once the owner has agreed to those terms. Retries are safe: attestations already recorded are not re-sent.

Poll `getBankingProfileStatus` (same body) until `applicationStatus` shows approval; it also lists per-rail capabilities and anything still outstanding.

**Step 1c — proof of address (needed above \$3,000).** `getBankingApplication` returns a `poaStatus` field. When it is `missing` or `rejected`, the account still opens and works, but it cannot transact more than **\$3,000 in a rolling 7-day period** until a document is approved. Crossing that limit without one freezes the profile and holds the transfers in compliance review, so handle it before it bites rather than after.

The document is a utility bill or bank statement from the last 90 days showing the owner's name and address. Your human has to supply the file; you upload it:

```bash
curl https://laso.finance/uploadBankingDocument \
  -H "Authorization: Bearer $LASO_ID_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"data":{"userId":"usr_...","documentType":"proof_of_address","fileType":"jpeg","fileContent":"<base64>","country":"US"}}'
```

A `.jpg` must be sent as `fileType: "jpeg"`, and the decoded file must be 10MB or under. After upload `poaStatus` becomes `submitted_pending_review`; a human at the partner reviews it, usually within a business day.

**Step 2a — on-ramp account (dollars in, USDC out).** Once approved:

```bash
curl https://laso.finance/createBankingAccount \
  -H "Authorization: Bearer $LASO_ID_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"data":{"userId":"usr_...","accountType":"onramp"}}'
```

Returns `bankAccount` with real ACH/wire details (routing number, account number, bank name). Dollars sent there are converted and delivered as USDC to the managed wallet on Solana (pass `cryptoAddress` to land somewhere else). Share these bank details with whoever needs to pay the account.

**Step 2b — off-ramp account (USDC in, dollars out).** First register the payout bank account as a recipient destination, then create the account:

```bash
# Create a recipient (the person/company being paid). ALWAYS include `address`:
# a bank account cannot be attached to a recipient that has none.
curl https://laso.finance/createBankingRecipient \
  -H "Authorization: Bearer $LASO_ID_TOKEN" -H "Content-Type: application/json" \
  -d '{"data":{"userId":"usr_...","name":"Jane Doe","address":{"street1":"1 Main St","street2":"Apt 2","city":"Austin","region":"TX","postal_code":"78701","country":"US"}}}'

# Attach their US bank account (returns destinationId). `nickname` is an
# optional label ("Rent account") and the ONLY field editable later.
curl https://laso.finance/addBankingDestination \
  -H "Authorization: Bearer $LASO_ID_TOKEN" -H "Content-Type: application/json" \
  -d '{"data":{"userId":"usr_...","recipientId":"...","nickname":"Rent account","destination":{"destination_type":"fiat_us","name":"Jane checking","aba_routing_number":"021000021","account_number":"123456789","account_type":"checking","account_holder_name":"Jane Doe","bank_name":"Chase"}}}'

# Create the off-ramp account pointing at that destination
curl https://laso.finance/createBankingAccount \
  -H "Authorization: Bearer $LASO_ID_TOKEN" -H "Content-Type: application/json" \
  -d '{"data":{"userId":"usr_...","accountType":"offramp","fiatDestinationId":"..."}}'
```

**The recipient's `address` is required for a bank destination.** It is the postal address of whoever is being paid (`street1`, optional `street2`, `city`, `region`, `postal_code`, `country`) and it is **not** the bank's address. A crypto destination does not need it, but a `fiat_us` or `fiat_iban` one does, and `addBankingDestination` rejects the attempt with `failed-precondition` if it is missing.

If you already created a recipient without an address, you do not have to start over. Pass `recipientAddress` to `addBankingDestination` and it sets the address before attaching the account:

```bash
curl https://laso.finance/addBankingDestination \
  -H "Authorization: Bearer $LASO_ID_TOKEN" -H "Content-Type: application/json" \
  -d '{"data":{"userId":"usr_...","recipientId":"...",
        "recipientAddress":{"street1":"1 Main St","city":"Austin","region":"TX","postal_code":"78701","country":"US"},
        "destination":{"destination_type":"fiat_us","name":"Jane checking","aba_routing_number":"021000021","account_number":"123456789","account_type":"checking","account_holder_name":"Jane Doe","bank_name":"Chase"}}}'
```

These are a real person's address and real bank details, so use only values your human actually gave you. Do not guess an address to satisfy the requirement.

**Paying a destination.** Once a destination exists, `GET /send-bank-payment?amount=250&destination_id=...` pays it over x402 in one call, opening the off-ramp account for you if there isn't one and handling the funding leg. This is the only way to send a bank payout: the off-ramp's internal funding address is not returned by any endpoint, so there is no separate address for you to send USDC to. Listing your destinations is free at `GET /bank-recipients` (each destination includes its `nickname` when one is set).

**Managing recipients.** A destination's `nickname` is the only thing that can ever be edited. Set or change it with `updateBankingDestination` (`{"data":{"userId":"usr_...","destinationId":"...","nickname":"Rent account"}}`; an empty string clears it, 40 characters max). If any other detail is wrong (routing number, account number, name), delete the recipient and create a new one: `deleteBankingRecipient` (`{"data":{"userId":"usr_...","recipientId":"..."}}`) removes the recipient, its destinations, and any off-ramp account paying out to them. That deletion is irreversible, so confirm with your human before calling it. Your human can also add, rename, and delete recipients themselves on the dashboard; the two surfaces share these same calls, so anything either of you changes is visible to both.

**Step 3 — read back your bank details at any time.** `createBankingAccount` is idempotent, so calling it again returns the existing account rather than opening a second one. To list what already exists without creating anything:

```bash
curl https://laso.finance/listBankingAccounts \
  -H "Authorization: Bearer $LASO_ID_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"data":{"userId":"usr_..."}}'
```

Returns `{ "result": { "accounts": [ ... ] } }`. Each entry carries `accountId`, `accountType` (`onramp` / `offramp`), `status`, and then whichever side applies:

- **On-ramp** — `bankAccount` with the deposit details to give a payer: `account_holder_name`, `account_number`, `aba_routing_number`, `bank_name`, `bank_address`, and `capabilities` (e.g. `["ach","fedwire"]`).
- **Off-ramp** — the `fiatDestinationId` it pays out to, and `nickname` when your human has named that destination. Its internal funding address is deliberately not returned; pay it with `GET /send-bank-payment` instead.

**Use the `nickname` as the account's primary label.** When an entry has one, your human chose it, so it is how they actually think and talk about that account ("Rent account", not "off-ramp `acct_9f2c...`"). Lead with it whenever you show the account, name it in a confirmation before you move money, and keep the bank name, last four digits, or `accountId` as the secondary detail that disambiguates. Fall back to `accountType` plus the bank details only when there is no nickname. The same goes for the destinations from `listBankingRecipients` and `GET /bank-recipients`, which carry the same `nickname`.

These are real bank details for a real account. Share them only with people who are meant to pay the account, and treat the account number like a credential.

**Watching money move.** Every ramp transaction is mirrored as it settles, so you can follow one without polling the partner: `getBankingTransaction` (`{"data":{"userId":"usr_...","transactionId":"..."}}`) and `listBankingTransactions` (`{"data":{"userId":"usr_..."}}`). A transaction reports `status` (`pending` → `completed` / `failed` / `cancelled`), `direction` (`onramp` / `offramp`), `amount` with `amountAsset`, `sendAmount` with `sendAsset`, and `txHash` once it settles on-chain. Your human is notified automatically when one completes or fails.

Note that a fiat on-ramp settles in two stages: the bank transfer clears first, and the USDC arrives in the managed wallet minutes to hours later. Both stages appear on your human's dashboard, so a gap between "bank transfer complete" and the wallet balance moving is expected, not an error.

**Paying someone.** `GET /send-bank-payment` (above) is the way to do it. Pay in USDC per call; nothing needs to be in your account balance first. Limits are \$10-\$50,000, plus a 0.25% fee with a \$1.50 minimum added on top. It opens the off-ramp account for the destination if one does not exist yet, so it is the single call needed to pay someone. Track the payment with `getBankingTransaction` / `listBankingTransactions`, and list everything with `listBankingAccounts` / `listBankingRecipients`.
