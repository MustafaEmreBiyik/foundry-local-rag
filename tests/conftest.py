"""Ortak test yardımcıları: sahte Foundry Local istemcileri ve geçici veritabanı."""

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

# Proje kökündeki modüllerin (database, retrieval vb.) import edilebilmesi için
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config  # noqa: E402
import database as db  # noqa: E402


class SahteEmbeddingClient:
    """Metin -> vektör eşlemesiyle çalışan sahte embedding istemcisi."""

    def __init__(self, vektorler: dict[str, list[float]]):
        self.vektorler = vektorler
        self.cagrilar: list[str] = []

    def generate_embedding(self, metin: str):
        self.cagrilar.append(metin)
        return SimpleNamespace(
            data=[SimpleNamespace(embedding=self.vektorler[metin])]
        )

    def generate_embeddings(self, metinler: list[str]):
        self.cagrilar.append(list(metinler))
        return SimpleNamespace(
            data=[
                SimpleNamespace(embedding=self.vektorler[m]) for m in metinler
            ]
        )


class SahteChatClient:
    """Gönderilen mesajları kaydeden ve sabit cevap dönen sahte sohbet istemcisi."""

    def __init__(self, cevap: str = "Sahte cevap."):
        self.cevap = cevap
        self.cagrilar: list[list[dict]] = []

    def complete_chat(self, messages: list[dict]):
        self.cagrilar.append(messages)
        mesaj = SimpleNamespace(content=self.cevap)
        return SimpleNamespace(choices=[SimpleNamespace(message=mesaj)])


@pytest.fixture
def gecici_db(tmp_path, monkeypatch):
    """database modülünü geçici bir SQLite dosyasına yönlendirir."""
    yol = tmp_path / "test_veritabani.db"
    monkeypatch.setattr(config, "DB_YOLU", yol)
    conn = db.baglan()
    db.tablolari_olustur(conn)
    conn.close()
    return yol
