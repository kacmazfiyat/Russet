def calculate_results(satis_fiyati, maliyet, mp):
    """
    Pazaryeri ayarlarına göre net kar, KDV ve gider kalemlerini hesaplar.
    """
    kdv_orani = mp.get('kdv', 20) / 100
    kdv_dahil = mp.get('kdv_dahil', 1)  # 1: Dahil, 0: Hariç

    # KDV Hesaplama Mantığı
    if kdv_dahil == 1:
        # Satış fiyatının içinden KDV ayıklanır
        kdv_tutari = satis_fiyati - (satis_fiyati / (1 + kdv_orani))
    else:
        # Satış fiyatının üzerine KDV eklenir
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
    
    # Toplam Tahsilat (Bankaya yatan net para - Görselde gizli, hesapta var)
    tahsilat = (satis_fiyati if kdv_dahil == 1 else (satis_fiyati + kdv_tutari)) - toplam_gider
    
    net_kar = tahsilat - maliyet
    kar_marji = (net_kar / (satis_fiyati if kdv_dahil == 1 else (satis_fiyati + kdv_tutari)) * 100) if satis_fiyati > 0 else 0
    
    return {
        "net_kar": round(net_kar, 2),
        "kar_marji": round(kar_marji, 2),
        "kdv_tutari": round(kdv_tutari, 2),
        "komisyon_tutari": round(komisyon_tutari, 2),
        "toplam_gider": round(toplam_gider, 2)
    }