import pandas as pd
import numpy as np
"""
ON PREPARE LES 3 DATASETS
"""
from app import df1, df2, df3, ID_PROFIL_ENEDIS

#Veuillez rensigner vos fichiers r63, r65 et r66
FICHIER_R63 = df1 #cdc       
FICHIER_R65 = df2 #index
FICHIER_R66 = df3 #pmax 

#préparer les bonnes 500 cdc de l'open data enedis
def cdc_500(id_profil_type=0):
    if id_profil_type==0:
        print("La prediction va se faire avec le profil 'RES 1 plage 3-6kVA'")
        cdc_500=pd.read_csv("DF_RES1_3-6.csv",sep=',')    #changer chemin

    elif id_profil_type==1:
        print("La prediction va se faire avec le profil 'PRO 2 plage 12-24kVA'")
        cdc_500=pd.read_csv("DF_PRO2-12-24.csv",sep=',')  #changer chemin

    else :
        print("veillez recommencer en choisissant un profil donné")  
        return 
    return cdc_500

CDC_500 = cdc_500(id_profil_type=ID_PROFIL_ENEDIS)#choix du bon dataset des 500cdc fictives open data enedis

#Comme les pas de temps des data enedis des cdc varie, il faut normaliser
#On normalise en fonction des 500 cdc, donc au pas de temps=30min
def passer_cdc_au_pas(df, pas_min):# df->df
    dfs = []
    for id_, g in df.groupby("id"):
        g = (g.set_index("datetime")[["value"]].resample(f"{pas_min}min").mean().fillna(0.0).reset_index())
        g["id"] = id_
        dfs.append(g)
    df_out = pd.concat(dfs, ignore_index=True)
    return df_out

#On rajoute un index cyclique adapté au jour de la semaine pour comparer d'une année sur l'autre
def ajouter_index_cyclique(df,col_time,pas_min,jour_ref=None):# df->df
    dt = pd.to_datetime(df[col_time])
    pts_jour = int(24 * 60 / pas_min)#nbr de pts au pas de temps/jours
    index_base = ((dt.dt.dayofyear - 1) * pts_jour + (dt.dt.hour * 60 + dt.dt.minute) // pas_min)# Index annuel de base au pdt (1janv 00:00->1)
    
    if jour_ref is not None:#On veut réaligner l'index cyclique sur une semaine de référence
        jours = dt.dt.weekday#0=lundi,6=dimanche
        dist = (jours - jour_ref).abs()#distance cyclique entre jours de semaine
        dist = np.minimum(dist, 7 - dist)#modulo?       
        idx_align = dist.idxmin()#index du point le plus proche en jour de semaine
        offset = index_base.loc[idx_align]#valeur d’index à cet endroit
        index_base = (index_base - offset) % (365 * pts_jour)# on décale tout pour que ça commence là

    df["index_cyclique"] = index_base#on ajoute l'index cyclique au df 
    return df

#Préparer les cdc (500cdc et fichier r63)
def préparer_cdc(df,col_id,col_time,col_val,jour_ref=None):# df->df
    df = df[[col_id, col_time, col_val]].copy()
    df = df.rename(columns={col_id: "id",col_time: "datetime",col_val: "value"})#rename pour simplifier
    df["datetime"] = pd.to_datetime(df["datetime"])#format datetime
    df["value"] = df["value"].fillna(0.0)#on enlève les nan
    df=passer_cdc_au_pas(df, pas_min=30)#on met au même pdt les datasets pour comparer
    df=ajouter_index_cyclique(df, "datetime", pas_min=30,jour_ref=jour_ref)#ajout index cyclique
    df["index_jour"] = df["datetime"].dt.dayofyear
    df["index_jour"] = ((df["index_jour"] - 1) % 365) + 1
    return df

#préparer le fichier R65
def fichier_r65(fichier_r65=FICHIER_R65):# df->df
    fichier_r65 = fichier_r65.copy()
    fichier_r65 = fichier_r65[#on gadre que les bonnes colonnes du df
        (fichier_r65['Grandeur physique'] == 'EA') &
        (fichier_r65['Unite'].str.lower() == 'wh') &
        (fichier_r65['Pas'] == 'P1D')
    ]
    fichier_r65['Date'] = pd.to_datetime(fichier_r65['Date'])#format datetime
    fichier_r65["index_jour"] = fichier_r65["Date"].dt.dayofyear
    fichier_r65["index_jour"] = ((fichier_r65["index_jour"] - 1) % 365) + 1
    fichier_r65 = fichier_r65[['Identifiant PRM', 'Date', 'Valeur','index_jour']]#on gadre que les bonnes colonnes du df
    fichier_r65["Valeur"] = fichier_r65["Valeur"].fillna(0.0)#on enlève les nan
    return fichier_r65

#préparer le fichier R66
def fichier_r66(fichier_r66=FICHIER_R66):# df->df
    fichier_r66 = fichier_r66.copy()
    fichier_r66 = fichier_r66[#on gadre que les bonnes colonnes du df
        (fichier_r66['Grandeur physique'] == 'PMA') & 
        (fichier_r66['Unité'].str.lower() == 'VA') & 
        (fichier_r66['Pas'] == 'P1D')
    ]
    fichier_r66['Horodate'] = pd.to_datetime(fichier_r66['Horodate'])#format datetime
    fichier_r66["Date"] = pd.to_datetime((fichier_r66["Horodate"]).dt.date)#format datetime
    fichier_r66["index_jour"] = fichier_r66["Date"].dt.dayofyear
    fichier_r66["index_jour"] = ((fichier_r66["index_jour"] - 1) % 365) + 1
    fichier_r66 = fichier_r66[['Identifiant PRM', 'Horodate','Date', 'Valeur','index_jour']]#on gadre que les bonnes colonnes du df
    fichier_r66["Valeur"] = fichier_r66["Valeur"].fillna(0.0)#on enlève les nan  
    return fichier_r66

#CDC 
df_fichier_r63=préparer_cdc(FICHIER_R63,col_id="Identifiant PRM",col_time="Horodate",col_val="Valeur",jour_ref=None)

#Energie journalier
df_fichier_r65=fichier_r65(FICHIER_R65)

#Pmax journalier
df_fichier_r66=fichier_r66(FICHIER_R66)

#500 CDC
jour_ref=pd.to_datetime(df_fichier_r63["datetime"].iloc[0]).weekday()# permet de synchronisé avec le jour de la semaine
df_cdc_500=préparer_cdc(CDC_500,col_id="ID",col_time="horodate",col_val="valeur",jour_ref=jour_ref)
