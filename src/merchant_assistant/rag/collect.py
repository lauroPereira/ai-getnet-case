"""Collects the public sources into versioned snapshots (explicit `ingest` command; never run at startup)."""

from __future__ import annotations

import json
import re
import time
import urllib.robotparser
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import httpx

from merchant_assistant.rag.documents import content_hash, slug_for

USER_AGENT = "ai-getnet-case-ingest/0.1 (+https://github.com/lauroPereira/ai-getnet-case)"
MIN_TEXT_CHARS = 200

# Lines and markers repeated on every page of the official site (menus, help-center footer, contact blocks).
STOP_MARKERS = ("Respondeu à sua dúvida?", "Fale já\nVamos começar", "Nossas ofertas imperdíveis")
NOISE_LINES = {
    "Permitir",
    "Dispensar",
    "Preferências de Cookie",
    "Open",
    "SAIBA MAIS",
    "QUERO AGORA",
    "EU QUERO",
    "Sim",
    "Não",
    "Clique aqui",
    "Clique abaixo e baixe agora",
    "BAIXAR APP",
    "Nos informe CPF ou CNPJ",
    "Para melhor direcionamento, informe o documento solicitado.",
    "Quero contratar",
    "QUERO VENDER",
}


def clean_text(text: str) -> str:
    for marker in STOP_MARKERS:
        idx = text.find(marker)
        if idx > 200:
            text = text[:idx]
    text = re.sub(r"Utilizamos cookies.*?(Preferências de Cookie|Política de Privacidade\.)", "", text, flags=re.S)
    lines = [re.sub(r"\s+", " ", line).strip() for line in text.splitlines()]
    kept = [line for line in lines if line and line not in NOISE_LINES]
    return "\n".join(kept).strip()


def extract_text(html: str) -> tuple[str, str]:
    """Returns (title, text) choosing the richer of two extractors after cleaning."""
    import trafilatura
    from bs4 import BeautifulSoup

    candidates = []
    extracted = trafilatura.extract(html, favor_recall=True, include_tables=True) or ""
    candidates.append(clean_text(extracted))
    soup = BeautifulSoup(html, "html.parser")
    title = (soup.title.string or "").strip() if soup.title else ""
    for tag in soup(["script", "style", "noscript", "svg", "header", "footer", "nav", "form"]):
        tag.decompose()
    main = soup.find("main") or soup.find("article") or soup.body
    if main is not None:
        candidates.append(clean_text(main.get_text("\n", strip=True)))
    return title, max(candidates, key=len)


@dataclass
class CollectResult:
    url: str
    path: Path | None
    chars: int
    ok: bool
    message: str = ""


def collect(manifest_path: Path, out_dir: Path, *, project_root: Path, delay_s: float = 1.0) -> list[CollectResult]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    out_dir.mkdir(parents=True, exist_ok=True)
    robots: dict[str, urllib.robotparser.RobotFileParser] = {}
    results: list[CollectResult] = []
    with httpx.Client(headers={"User-Agent": USER_AGENT}, timeout=30, follow_redirects=True) as client:
        for source in manifest["sources"]:
            url = source["url"]
            collected_at = datetime.now(UTC).isoformat(timespec="seconds")
            try:
                if source.get("capture") == "browser_rendered":
                    text = clean_text((project_root / source["rendered_path"]).read_text(encoding="utf-8"))
                    title = source.get("title") or url
                    html_title, _ = extract_text(client.get(url).text)
                    title = html_title or title
                    collected_at = source.get("verified_at", collected_at)
                else:
                    host = httpx.URL(url).host
                    if host not in robots:
                        rp = urllib.robotparser.RobotFileParser()
                        rp.parse(client.get(f"https://{host}/robots.txt").text.splitlines())
                        robots[host] = rp
                    if not robots[host].can_fetch(USER_AGENT, url):
                        results.append(CollectResult(url, None, 0, False, "blocked by robots.txt"))
                        continue
                    response = client.get(url)
                    response.raise_for_status()
                    title, text = extract_text(response.text)
                    time.sleep(delay_s)
            except (httpx.HTTPError, OSError) as exc:
                results.append(CollectResult(url, None, 0, False, f"error: {exc}"))
                continue
            if len(text) < MIN_TEXT_CHARS:
                results.append(CollectResult(url, None, len(text), False, "extracted text too short"))
                continue
            snapshot = {
                "url": url,
                "title": title,
                "market": source.get("market"),
                "language": source.get("language"),
                "topic": source.get("topic"),
                "products": source.get("products", []),
                "capture": source.get("capture", "http"),
                "capture_note": source.get("capture_note"),
                "collected_at": collected_at,
                "content_hash": content_hash(text),
                "text": text,
            }
            path = out_dir / f"{slug_for(url)}.json"
            path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=1), encoding="utf-8")
            results.append(CollectResult(url, path, len(text), True))
    return results
