# Synthetic business-service fixtures

`pricing-v1.json` and `charges-v1.json` are intentionally maintained as separate evidence sources. Keys are synthetic sale IDs; each record repeats both its synthetic merchant ID and transaction ID so the services can enforce ownership and link the two responses. The charge records are never generated from the pricing rules.

Fixtures cover matching fees, different plan conditions, a cent-level divergence and missing applicable evidence, plus an independent second merchant. All values, rule names, protocols and statuses are fictional. Do not add real customer data or real Getnet pricing here.
