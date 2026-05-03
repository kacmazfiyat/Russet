def suggest_price(maliyet, hedef_kar_marji, mp_settings):
    """
    Hedef kâr marjına ulaşmak için gereken satış fiyatını hesaplar.
    Formül: Satış Fiyatı = (Maliyet + Sabit Giderler) / (1 - (Komisyon% + KDV% + Stopaj% + HedefMarj%))
    """
    oranlar_toplami = (mp_settings['komisyon'] + mp_settings['kdv'] + 
                       mp_settings['stopaj'] + hedef_kar_marji) / 100
    
    sabit_giderler = mp_settings['kargo'] + mp_settings['kupon'] + \
                     mp_settings['hizmet'] + mp_settings['ekstra']
    
    if oranlar_toplami >= 1:
        return 0
        
    onerilen_fiyat = (maliyet + sabit_giderler) / (1 - oranlar_toplami)
    return round(onerilen_fiyat, 2)