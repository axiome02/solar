import streamlit as st

st.set_page_config(page_title="Solar Value", page_icon="🔌")

def sidebar_run():
    # --- SIDEBAR ---
    with st.sidebar:
        st.title("Solar Value 🔌")
        st.subheader("Application citoyenne")
        st.markdown("""
            ---
            **La mission de Solar Value :** Modeliser la consommation électrique de chacun pour déterminer si l'installation de Panneaux Photovoltaïques est une solution intéressante pour vous !
            
            *L'autoconsommation de façon objective*
            ---
            """)
        st.info("💡 **Conseil** : Avant de mieux produire il faut mieux consommer! Isoler correctement un batiment sera toujours plus intéressant que d'investir dans des moyens de production énergétique")
        
        status_placeholder = st.empty()
        
        # 2. On affiche l'état d'attente initial
        status_placeholder.warning("Base de données : Synchronisation... ⏳")
        
        # 3. On lance l'initialisation (le cache bloque l'exécution ici tant que ce n'est pas fini)
        if st.button("🗑️ Effacer la conversation"):
            #st.info("💡 **Conseil** : Avant de mieux produire il faut mieux consommer! Isoler correctement un batiment sera toujours plus intéressant que d'investir dans des moyens de production énergétique")
            st.rerun()
sidebar_run()

#PAGE Centrale
st.write("# Bienvenue sur Solar Value 🔌 👋")
st.write("Modelisez votre consommation électrique sur l'année à venir " \
"pour savoir si l'installation de PV a une réelle valeur chez vous !")

import pandas as pd

st.title("Importation de fichiers multiples")

# Fonction pour lire le fichier selon son extension
def load_data(file):
    if file.name.endswith('.csv'):
        return pd.read_csv(file)

# Création de trois colonnes pour un affichage élégant
col1, col2, col3 = st.columns(3)

with col1:
    st.subheader("Fichier R63 cdc")
    file1 = st.file_uploader("Upload CSV", type='csv', key="1")
    if file1:
        df1 = load_data(file1)
        st.write("Aperçu :", df1.head(3))

with col2:
    st.subheader("Fichier R65 index")
    file2 = st.file_uploader("Upload CSV", type='csv', key="2")
    if file2:
        df2 = load_data(file2)
        st.write("Aperçu :", df2.head(3))

with col3:
    st.subheader("Fichier R66 Pmax")
    file3 = st.file_uploader("Upload CSV", type='csv', key="3")
    if file3:
        df3 = load_data(file3)
        st.write("Aperçu :", df3.head(3))

# Zone de traitement global
if file1 and file2 and file3:
    st.success("Les 3 fichiers sont chargés ! Prêts pour le traitement.")

ID_PROFIL_ENEDIS=1
