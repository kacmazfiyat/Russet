def calculate_results(satis_fiyati, maliyet, mp):
    """
    Pazaryeri ayarlarına göre net kar, KDV ve gider kalemlerini hesaplar.
    """
    # Veritabanı sütun isimlerine göre güvenli veri çekme
    kdv_orani = mp.get('kdv', 20) / 100
    kdv_dahil = mp.get('kdv_dahil', 1)  # 1: Dahil, 0: Hariç

    # KDV Hesaplama Mantığı
    if kdv_dahil == 1:
        # Satış fiyatının içinden KDV ayıklanır (Brüt Fiyat üzerinden)
        kdv_tutari = satis_fiyati - (satis_fiyati / (1 + kdv_orani))
    else:
        # Satış fiyatının üzerine KDV eklenir (Fiyat + KDV)
        kdv_tutari = satis_fiyati * kdv_orani

    # Giderlerin Hesaplanması
    komisyon_tutari = satis_fiyati * (mp.get('komisyon', 0) / 100)
    stopaj_tutari = satis_fiyati * (mp.get('stopaj', 0) / 100)
    
    toplam_gider = (komisyon_tutari + 
                    mp.get('kargo', 0) + 
                    mp.get('kupon', 0) + 
                    stopaj_tutari + 
                    kdv_tutari + 
                    mp.get('hizmet', 0) + 
                    mp.get('ekstra', 0))
    
    # Toplam Tahsilat (Müşterinin ödediği toplam para)
    toplam_tahsilat = satis_fiyati if kdv_dahil == 1 else (satis_fiyati + kdv_tutari)
    
    net_kar = toplam_tahsilat - maliyet - toplam_gider
    kar_marji = (net_kar / toplam_tahsilat * 100) if toplam_tahsilat > 0 else 0
    
    return {
        "net_kar": round(net_kar, 2),
        "kar_marji": round(kar_marji, 2),
        "kdv_tutari": round(kdv_tutari, 2),
        "komisyon_tutari": round(komisyon_tutari, 2),
        "toplam_gider": round(toplam_gider, 2),
        "toplam_tahsilat": round(toplam_tahsilat, 2)
    }