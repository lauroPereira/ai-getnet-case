"""Demo ticketing service, separate from the assistant (spec v0.7.0, D16).

It has its own SQLite database and talks to the assistant only over HTTP: signed webhooks in both directions,
operator JWTs validated by the assistant's JWKS and a client-credentials token for its own calls. It must not
import any other module of the assistant (architecture test)."""
