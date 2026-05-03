def calculate_net_profit(satis_fiyati, maliyet, mp_settings):
    """
    Pazaryeri giderlerini hesaplar ve net kâr/marj sonucunu döner.
    """
    # Oran bazlı giderler
    komisyon_tutari = satis_fiyati * (mp_settings['komisyon'] / 100)
    kdv_tutari = satis_fiyati * (mp_settings['kdv'] / 100)
    stopaj_tutari = satis_fiyati * (mp_settings['stopaj'] / 100)
    
    # Tüm giderlerin toplamı
    toplam_gider = (komisyon_tutari + mp_settings['kargo'] + 
                    mp_settings['kupon'] + stopaj_tutari + 
                    kdv_tutari + mp_settings['hizmet'] + 
                    mp_settings['ekstra'])
    
    net_kar = satis_fiyati - maliyet - toplam_gider
    kar_marji = (net_kar / satis_fiyati * 100) if satis_fiyati > 0 else 0
    
    return {
        "net_kar": round(net_kar, 2),
        "kar_marji": round(kar_marji, 2),
        "toplam_gider": round(toplam_gider, 2),
        "detaylar": {
            "Komisyon": round(komisyon_tutari, 2),
            "KDV": round(kdv_tutari, 2),
            "Kargo": mp_settings['kargo'],
            "Stopaj": round(stopaj_tutari, 2),
            "Hizmet/Ekstra": mp_settings['hizmet'] + mp_settings['ekstra']
        }
    }

def suggest_price(maliyet, hedef_kar_marji, mp_settings):
    """
    Hedef kâr marjına ulaşmak için gereken satış fiyatını hesaplar.
    """
    oranlar_toplami = (mp_settings['komisyon'] + mp_settings['kdv'] + 
                       mp_settings['stopaj'] + hedef_kar_marji) / 100
    
    sabit_giderler = mp_settings['kargo'] + mp_settings['kupon'] + \
                     mp_settings['hizmet'] + mp_settings['ekstra']
    
    if oranlar_toplami >= 1:
        return 0
        
    onerilen_fiyat = (maliyet + sabit_giderler) / (1 - oranlar_toplami)
    return round(onerilen_fiyat, 2)