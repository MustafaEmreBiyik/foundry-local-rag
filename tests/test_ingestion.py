"""ingestion.py birim testleri: chunking, örtüşme ve belge okuma hataları."""

import pytest

import ingestion
from conftest import SahteEmbeddingClient
from ingestion import IngestionHatasi, metni_parcala


class TestMetniParcala:
    def test_bos_metin_bos_liste_dondurur(self):
        assert metni_parcala("") == []
        assert metni_parcala("   \n\t  ") == []

    def test_kisa_metin_tek_chunk_olur(self):
        metin = "Bu kısa bir cümledir."
        assert metni_parcala(metin) == [metin]

    def test_ortusmesiz_bolme_kelime_kaybetmez(self):
        kelimeler = [f"k{i}" for i in range(650)]
        parcalar = metni_parcala(" ".join(kelimeler), chunk_boyutu=300, ortusme=0)

        assert len(parcalar) == 3
        assert " ".join(parcalar).split() == kelimeler

    def test_uzun_paragraf_ortusmeli_bolunur(self):
        kelimeler = [f"k{i}" for i in range(650)]
        parcalar = metni_parcala(" ".join(kelimeler), chunk_boyutu=300, ortusme=50)

        # 0-299, 250-549, 500-649
        assert len(parcalar) == 3
        assert parcalar[0].split() == kelimeler[:300]
        assert parcalar[1].split() == kelimeler[250:550]
        assert parcalar[2].split() == kelimeler[500:650]

    def test_ardisik_chunklar_ortusme_paylasir(self):
        kelimeler = [f"k{i}" for i in range(400)]
        parcalar = metni_parcala(" ".join(kelimeler), chunk_boyutu=300, ortusme=50)

        onceki_kuyruk = parcalar[0].split()[-50:]
        sonraki_bas = parcalar[1].split()[:50]
        assert onceki_kuyruk == sonraki_bas

    def test_paragraf_siniri_korunur(self):
        # 3 paragraf: 200 + 200 + 50 kelime; chunk boyutu 300.
        # İkinci paragraf ilkine sığmaz -> ilk chunk yalnızca 1. paragraf olur;
        # paragraf ortadan bölünmez.
        p1 = " ".join(f"a{i}" for i in range(200))
        p2 = " ".join(f"b{i}" for i in range(200))
        p3 = " ".join(f"c{i}" for i in range(50))
        metin = f"{p1}\n\n{p2}\n\n{p3}"

        parcalar = metni_parcala(metin, chunk_boyutu=300, ortusme=0)

        assert len(parcalar) == 2
        assert parcalar[0].split() == p1.split()
        assert parcalar[1].split() == p2.split() + p3.split()

    def test_hicbir_kelime_kaybolmaz(self):
        kelimeler = [f"k{i}" for i in range(700)]
        parcalar = metni_parcala(" ".join(kelimeler), chunk_boyutu=300, ortusme=50)

        gorulen = set()
        for parca in parcalar:
            gorulen.update(parca.split())
        assert gorulen == set(kelimeler)


class TestBelgeleriYukle:
    def test_eksik_klasor_hata_verir(self, tmp_path):
        with pytest.raises(IngestionHatasi, match="bulunamadı"):
            ingestion.belgeleri_yukle(tmp_path / "yok")

    def test_txt_olmayan_klasor_hata_verir(self, tmp_path):
        (tmp_path / "not.md").write_text("markdown", encoding="utf-8")
        with pytest.raises(IngestionHatasi, match=r"\.txt dosyası yok"):
            ingestion.belgeleri_yukle(tmp_path)

    def test_bozuk_utf8_hata_verir(self, tmp_path):
        (tmp_path / "bozuk.txt").write_bytes(b"\xff\xfe\x00ge\xe7ersiz")
        with pytest.raises(IngestionHatasi, match="UTF-8"):
            ingestion.belgeleri_yukle(tmp_path)

    def test_tamamen_bos_belgeler_hata_verir(self, tmp_path):
        (tmp_path / "bos.txt").write_text("   \n  ", encoding="utf-8")
        with pytest.raises(IngestionHatasi, match="boş"):
            ingestion.belgeleri_yukle(tmp_path)

    def test_gecerli_belgeler_sira_numarali_chunk_dondurur(self, tmp_path):
        (tmp_path / "a.txt").write_text("Birinci belge içeriği.", encoding="utf-8")
        (tmp_path / "b.txt").write_text("İkinci belge içeriği.", encoding="utf-8")

        chunklar = ingestion.belgeleri_yukle(tmp_path)

        assert len(chunklar) == 2
        assert {c["kaynak"] for c in chunklar} == {"a.txt", "b.txt"}
        assert all(c["icerik"] for c in chunklar)
        assert all(c["sira"] == 0 for c in chunklar)

    def test_cok_chunkli_belgede_sira_artar(self, tmp_path):
        metin = " ".join(f"k{i}" for i in range(700))
        (tmp_path / "uzun.txt").write_text(metin, encoding="utf-8")

        chunklar = ingestion.belgeleri_yukle(tmp_path)

        assert len(chunklar) >= 2
        assert [c["sira"] for c in chunklar] == list(range(len(chunklar)))


class TestEmbeddingleriUret:
    def test_batchler_halinde_uretir(self):
        vektorler = {f"m{i}": [float(i)] for i in range(5)}
        client = SahteEmbeddingClient(vektorler)

        sonuc = ingestion.embeddingleri_uret(
            client, [f"m{i}" for i in range(5)], batch_boyutu=2
        )

        assert sonuc == [[0.0], [1.0], [2.0], [3.0], [4.0]]
        # 5 metin, batch=2 -> 3 çağrı: [m0,m1], [m2,m3], [m4]
        assert client.cagrilar == [["m0", "m1"], ["m2", "m3"], ["m4"]]
