# Wallet-native authentication and Locus

Read this reference only for this task. For setup and session renewal, use [SKILL.md](https://laso.finance/SKILL.md). For managed accounts, the helper saves a usable token at `~/.laso/credentials.json`. In the same shell operation as the examples below, load it with `export LASO_ID_TOKEN="$(jq -r .id_token ~/.laso/credentials.json)"`; exports in separate tool calls may not persist.

## Prerequisites

Use your existing Locus, Sponge, or Ampersend wallet and USDC. You do not need a Laso managed API key. Authenticate with the wallet using `GET /auth` below, then use your wallet's x402 payment client for paid routes. See [payment challenges and settlement](payments.md#how-x402-works).

For a Laso managed wallet instead, follow [the setup helper](https://laso.finance/SKILL.md). It can sign in with an existing key or return a signup link for your human.

## Configuring Locus x402 Endpoints (Locus only)

Only relevant if you arrived with an existing **Locus** wallet. Locus requires the Laso Finance x402 endpoints to be registered in its dashboard before your agent can call them. Sponge and Ampersend discover endpoints automatically, and a Laso managed wallet needs none of this, so skip this section for all three.

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

### GET /auth — Get API credentials

**Cost:** Free.

**Registration metadata:** the machine-readable version of this section lives at https://laso.finance/auth.md, with discovery documents at https://laso.finance/.well-known/oauth-protected-resource and https://laso.finance/.well-known/oauth-authorization-server (whose `agent_auth` block carries `register_uri`, the supported identity and credential types, and the claim and verification endpoints). Read `/auth.md` if you arrived here from a well-known lookup rather than from this file.

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
