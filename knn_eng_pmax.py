import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import pairwise_distances

from prepa_data_set import df_cdc_500, df_fichier_r63, df_fichier_r65, df_fichier_r66
"""
CALCUL DE DISTANCE NORMALISATION +KNN + ENERGIE JOURNALIERE
"""

def cdc_plus_de_pts_que_les_500_cdc():# a améliorer cette alarme
    return False

def knn_cyclique(cdc_500,fichier_r63_etudie,K):#df, df, K ->dictionnaire

    #date et nbr de points nécéssaire pour le return et le debbogage
    date_depart = fichier_r63_etudie["datetime"].iloc[0].strftime("%Y-%m-%d")# date de départ pour avoir un point de départ
    NB_PTS_FENETRE=fichier_r63_etudie.shape[0]#sert au debbogage, il faut que les 500cdc aient plus de pts que la cdc (car 12mois>3mois), sinon le programme ne sert à rien

    #On crée le vecteur de test du fichier r63
    fichier_r63_etudie = fichier_r63_etudie.sort_values("index_cyclique")#on met dans l'ordre chronologique pour comprarer
    vect_test = fichier_r63_etudie["value"].to_numpy()#format pour calcul de distance
    
    #On crée le vecteur des 500cdc avec justes les values
    ids_ref = []#préparation 500cdc 
    vecteurs_ref = []#préparation 500cdc 
    for id_, g in cdc_500.groupby("id"):
        g = g.sort_values("index_cyclique").iloc[:NB_PTS_FENETRE]#on met dans l'ordre chronologique pour comprarer
        if len(g) == NB_PTS_FENETRE:
            vecteurs_ref.append(g["value"].to_numpy())#format pour calcul de distance
            ids_ref.append(id_)#format pour calcul de distance
        else :
            cdc_plus_de_pts_que_les_500_cdc()#il y a une erreur, le programme ne sert à rien car la cdc est plus grande que 12mois de data
            print(f"erreur, il n'y a pas le même nombre de point entre les 500 cdc et la courbe à tester :{len(g)},{NB_PTS_FENETRE}")
            break

    #Calcul KNN
    X_ref = np.vstack(vecteurs_ref)#stack les 500cdc pour calcul de distance
    scaler = StandardScaler()#outil de normalisation
    X_ref_n = scaler.fit_transform(X_ref)#transform 500cdc
    vect_test_n = scaler.transform(vect_test.reshape(1, -1))#transform cdc
    dist = pairwise_distances(X_ref_n,vect_test_n,metric="euclidean").ravel()#calcul distance euclidienne entre les 500cdc et la cdc transformées

    idx_k = np.argsort(dist)[:K]#les K indices des KNN
    poids = 1 / (dist[idx_k] + 1e-9)#poids des KNN
    poids /= poids.sum()#la somme des poids =1
    courbes_k = X_ref[idx_k]#on prend les KNN
    courbe_modelee = np.average(courbes_k, axis=0, weights=poids)#on met les KNN avec les bons poids
    return {
        "courbe_allure": courbe_modelee,
        "ids_voisins": np.array(ids_ref)[idx_k],
        "poids": poids,
        "date_depart": date_depart,
        "NB_PTS_FENETRE": NB_PTS_FENETRE
    }

#fonction qui prend en compte l'énergie journalière, fichier r65
def recaler_energie_journaliere(courbe, index_jour_df, date_depart):
    DT_H = 30 / 60#la puissance est tiré chaque 0.5h, or on doit sommer des energie pas des puissances, il faut donc passer par l'eng

    dates = pd.date_range(#format date pour comparer
        start=pd.to_datetime(date_depart),
        periods=len(courbe),
        freq="30min"
    )

    df = pd.DataFrame({"datetime": dates, "value": courbe})#format de la cdc à utiliser
    df["index_jour"] = df["datetime"].dt.dayofyear#on rajoute index journalier à la cdc
    df["index_jour"] = ((df["index_jour"] - 1) % 365) + 1#on prend en compte le chevauchement d'année

    for ij, g in df.groupby("index_jour"):
        ligne = index_jour_df.loc[index_jour_df["index_jour"] == ij]#on se cale aux bons jours
        if len(ligne) == 0:#debbogage
            continue

        E_cible = ligne["Valeur"].iloc[0]#l'eng qu'il faut attendre
        E_actuelle = g["value"].sum() * DT_H#on peut sommer car E=P*t et E extensive
        if E_actuelle == 0:#debbogage
            continue

        facteur = E_cible / E_actuelle#le facteur de diff entre l'eng/j de la vrai cdc et de celle modélisé
        df.loc[g.index, "value"] *= facteur#on multipie l'eng/j par le facteur pour avoir la bonne eng journalière
    return df["value"].to_numpy()#courbe avec la bonne eng journalière


#fonction qui prend en compte la pmax journalière, fichier r66
def recaler_pmax_journaliere_local(courbe, index_pmax_df, date_depart, largeur_fenetre=1):
    dates = pd.date_range(#format date pour comparer
        start=pd.to_datetime(date_depart),
        periods=len(courbe),
        freq="30min"
    )

    df = pd.DataFrame({"datetime": dates, "value": courbe})#format de la cdc à utiliser
    df["index_jour"] = df["datetime"].dt.dayofyear#on rajoute index journalier à la cdc
    df["index_jour"] = ((df["index_jour"] - 1) % 365) + 1#on prend en compte le chevauchement d'année

    for ij, g in df.groupby("index_jour"):
        ligne = index_pmax_df.loc[index_pmax_df["index_jour"] == ij]
        if len(ligne) == 0:#debbogage
            continue

        
        heure_pic = ligne["Horodate"].iloc[0].time()# heure cible du pic pour ce jour cyclique
        Pmax_cible = ligne["Valeur"].iloc[0]# valeur du pic pour ce jour cyclique

        # construire datetime fictif pour comparer les heures
        heures_g = g["datetime"].dt.time
        diff = heures_g.apply(lambda t: abs(#format date pour comparer
            (pd.Timestamp.combine(pd.Timestamp("2000-01-01"), t) -
             pd.Timestamp.combine(pd.Timestamp("2000-01-01"), heure_pic)).total_seconds()
        ))
        idx_pic = diff.idxmin()#points qui correspondent au mieux aux pics

        P_actuelle = df.loc[idx_pic, "value"]#valeur du pmax courbe modelisée
        if P_actuelle == 0:#debbogage
            continue

        facteur = Pmax_cible / P_actuelle#le facteur de diff entre pmax de la vrai cdc et de celle modélisé

        pos = df.index.get_loc(idx_pic)#position du point pmax
        i_avant_pmax = max(pos - largeur_fenetre, g.index.min())#point i avant le pmax
        i_apres_pmax = min(pos + largeur_fenetre, g.index.max())#point i après le pmax

        df.loc[i_avant_pmax:i_apres_pmax, "value"] *= facteur#on multiplie par le facteur pour avoir le bon pmax
    return df["value"].to_numpy()#on return la courbe modelisee avec le pmax journalier bien mis