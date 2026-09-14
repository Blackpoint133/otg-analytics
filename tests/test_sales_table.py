import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parents[1] / "streamlit_opensea_sales"))

from ui import tables  # noqa: E402


def _frame(seller, buyer, tx="0x" + "a" * 64):
    return pd.DataFrame([{
        "formatted_date": "2026-01-01", "price_gun": 1, "type": "GUN",
        "seller": seller, "buyer": buyer, "transaction_hash": tx,
        "item_url": "https://opensea.io/item", "price_usd_at_sale": 1.0,
        "gun_usd_price_at_sale": 2.0,
    }])


def test_sales_table_uses_shared_identity_cards_and_preserves_links(monkeypatch):
    seller = "0x" + "b" * 40
    buyer = "0x" + "c" * 40
    contexts = {
        seller: {"Profile": "Alice", "_profile": {"username": "alice"}, "_wallet": seller, "_ranks": {}},
        buyer: {"Profile": "NoName0001", "_profile": {}, "_wallet": buyer, "_ranks": {}},
    }
    monkeypatch.setattr(tables, "build_trader_card_contexts", lambda wallets, show_usd: contexts)
    monkeypatch.setattr(tables, "trader_profile_card_styles", lambda: "")
    monkeypatch.setattr(tables, "render_trader_clipboard_wiring", lambda: None)
    runtime = []
    monkeypatch.setattr(tables.components, "html", lambda value, **kwargs: runtime.append(value))
    monkeypatch.setattr(tables, "build_trader_profile_card_html", lambda row: f'<div data-wallet="{row["_wallet"]}">card</div>')
    captured = []
    monkeypatch.setattr(tables.st, "markdown", lambda value, **kwargs: captured.append(value))
    tables.render_sales_table(_frame(seller, buyer), True, 1.0)
    rendered = captured[0]
    assert ">Alice</button>" in rendered
    assert ">NoName0001</button>" in rendered
    assert "shorten_address" not in rendered
    assert "GunzScan" in rendered
    tx_hash = "0x" + "a" * 64
    assert tx_hash in rendered
    assert ">OpenSea</a>" in rendered
    assert "aria-expanded=\"false\"" in rendered
    assert "aria-controls" in rendered
    assert "<script>" not in rendered
    assert runtime and "window.parent.document" in runtime[0]
    script = runtime[0]
    assert ".sales-trader-identity-trigger" in script
    assert "__otgSalesTraderOverlayState" in script
    assert "old&&old.destroy" in script
    assert "removeEventListener(\"click\"" in script
    assert "removeEventListener(\"keydown\"" in script
    assert "clearInterval(timer)" in script
    assert "open&&open.card===c" in script
    assert "aria-expanded" in script and "getBoundingClientRect()" in script
    assert "c.hidden=false" in script and "offsetWidth" in script
    assert "w-c.offsetWidth-16" in script
    assert "setInterval" in script and "clearInterval" in script
    assert "Escape" in script
    assert ">GunzScan</a>" in rendered


def test_sales_table_blank_transaction_hash_has_no_link(monkeypatch):
    monkeypatch.setattr(tables, "build_trader_card_contexts", lambda wallets, show_usd: {})
    monkeypatch.setattr(tables, "trader_profile_card_styles", lambda: "")
    monkeypatch.setattr(tables, "render_trader_clipboard_wiring", lambda: None)
    monkeypatch.setattr(tables.components, "html", lambda value, **kwargs: None)
    captured = []
    monkeypatch.setattr(tables.st, "markdown", lambda value, **kwargs: captured.append(value))
    tables.render_sales_table(_frame("0x" + "b" * 40, "0x" + "c" * 40, ""), True, 1.0)
    rendered = captured[0]
    assert ">GunzScan</a>" not in rendered
    assert 'transaction_hash' not in rendered
