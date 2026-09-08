# Gift cards

Read this reference only for this task. For setup and session renewal, use [SKILL.md](https://laso.finance/SKILL.md). For managed accounts, the helper saves a usable token at `~/.laso/credentials.json`. In the same shell operation as the examples below, load it with `export LASO_ID_TOKEN="$(jq -r .id_token ~/.laso/credentials.json)"`; exports in separate tool calls may not persist.

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
  -H "Authorization: Bearer $LASO_ID_TOKEN"

# Filtered request using values discovered from `facets`
curl "https://laso.finance/search-gift-cards?q=amazon&country=US&category=ecommerce" \
  -H "Authorization: Bearer $LASO_ID_TOKEN"
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

**Cost:** \$5-\$9,000 USDC (x402 paywalled, dynamic pricing)

Order a gift card from the catalog. First browse available cards via `GET /search-gift-cards` to find the `laso_server_id`, then call this endpoint with the amount and product ID.

**`amount` is in the product's currency, not USD.** Laso converts it to USD at the current exchange rate and adds the product fee (up to 4.8%); that total is the USDC price you pay. A 100 SAR card costs about \$28 USDC, not \$100. Check the `currency` field on the product in `GET /search-gift-cards` before choosing an amount, and read the price from the 402 response rather than assuming it equals `amount`.

The \$5 minimum and \$9,000 maximum apply to the converted USD value, so a foreign-currency amount is accepted only when its USD equivalent falls in that range.

Parameters:

- `amount` (required): Gift card face value in the product's own currency (not USD). Must be worth at least \$5 and at most \$9,000 USD after conversion.
- `laso_server_id` (required): The product identifier from the catalog (`GET /search-gift-cards`).
- `country` (optional): ISO 3166-1 alpha-2 country code. Defaults to "US". Determines the regional variant, and therefore the currency `amount` is denominated in.

```bash
# 50 USD Amazon US card: x402 price is ~$52 USDC
curl "https://laso.finance/order-gift-card?amount=50&laso_server_id=amazon-us"

# 100 SAR Amazon SA card: x402 price is ~$28 USDC, not $100
curl "https://laso.finance/order-gift-card?amount=100&laso_server_id=amazon&country=SA"
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

`amount` and `currency` echo the face value in the product's own currency, so a Saudi card returns `"amount": 100, "currency": "SAR"` even though the USDC you paid was about \$28.

## Common workflow: Order a gift card

1. **Have a way to pay**: If you already have a Locus, Sponge, or Ampersend wallet, use it. Otherwise use a Laso managed wallet (see [setup](https://laso.finance/SKILL.md)) and pay with `agentX402Pay`.
2. **Authenticate**: `GET /auth` to get an `id_token` (free, send a `SIGN-IN-WITH-X` header).
3. **Browse catalog**: `GET /search-gift-cards?q=amazon` with `Authorization: Bearer <id_token>`. Find the `laso_server_id` for the desired card.
4. **Order the card**: `GET /order-gift-card?amount=50&laso_server_id=amazon-us` (pays $50 USDC via x402). The response contains the redemption details immediately.
