def calculate_net_profit(satis_fiyati, maliyet, mp_settings):
    # Komisyon, KDV ve Stopaj oran bazlı hesaplanır
    komisyon_tutari = satis_fiyati * (mp_settings['komisyon'] / 100)
    kdv_tutari = satis_fiyati * (mp_settings['kdv'] / 100)
    stopaj_tutari = satis_fiyati * (mp_settings['stopaj'] / 100)
    
    # Sabit giderler ve oranlı giderlerin toplamı
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

# Mevcut suggest_price fonksiyonun bunun altında kalmaya devam etsin...