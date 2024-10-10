# Fonctions appelés par app.py

import os
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
from pydeseq2.dds import DeseqDataSet
from pydeseq2.ds import DeseqStats
import io
import base64

def csv_to_pandaDF(csv_file):
    # Convertie .csv en pandas.Dataframe
    panda_df = pd.read_csv(csv_file)
    return panda_df

def preprocess_counts(counts, min_reads_per_gene):
    # pydeseq2 nécessite que la 1ère colonne de données (gènes/samples) soit la colonne index de la pandas.Dataframe afin d'avoir que des
    # des nombres dans la matrice counts (et non le nom des gènes/samples)
    counts = counts.set_index(counts.columns[0])    
    
    ## Filtrer les comptes brutes ##
    # @kanapathippilai.mathura DATA FILTERING: filter out NaN conditions, low counts per gene
    # Calcule la somme des counts/reads par gène (par row sans compter la 1ere colonne avec les noms des gènes) et
    # garder que les gènes qui ont une somme plus grande que min_reads_per_gene pour enlever les gènes qui
    # contiennent peu de reads/counts à travers tous les échantillons
    counts = counts[counts.sum(axis = 1) >= min_reads_per_gene]

    ## Inverser les colonnes et lignes ##
    # La majorité des données counts sur les base de données comme NCBI GEO sont comme-ci:
        # ligne: features/gènes
        # colonne: les échantillons
    # pydeseq2 nécessite que counts soit comme-ci:
        # ligne: les échantillons
        # colonne: features/gènes
    counts = counts.T
    return counts

def preprocess_df(counts_file, metadata_file, min_reads_per_gene):
    counts = csv_to_pandaDF(counts_file)
    metadata = csv_to_pandaDF(metadata_file)

    counts = preprocess_counts(counts, min_reads_per_gene)
    
    # pydeseq2 nécessite que la 1ère colonne de données (gènes/samples) soit la colonne index de la pandas.Dataframe afin d'avoir que des
    # des nombres dans la matrice counts (et non le nom des gènes/samples)
    metadata = metadata.set_index(metadata.columns[0])

    return counts, metadata

def get_design_factor(metadata):
    design_factor = str(metadata.columns[0])
    return design_factor

def pipeline_pydeseq(counts, metadata, design_factor, refit_cooks):
    # Creation d'objet DeseqDataSet à partir de counts et metadata qui contient:
    #   dds.X       Matrice des counts des gènes pour chaque sample (n_samples x n_gènes)
    #   dds.obs     Matrice 1D des valeurs des design_factors où index: nom des samples (length: n_samples)
    #   dds.var     Matrice 1D des annotations gene-level où index: nom des gènes (length: n_genes)
    #   dds.varm    Contient 'dispersions', 'fitted_dispersions', 'LFC', '_outlier_genes'
    #   etc. ...
    dds = DeseqDataSet(
        counts=counts,
        metadata=metadata,
        design_factors=design_factor,
        refit_cooks=refit_cooks
    )
    # Effectue l'estimation de la dispersion et log fold change (LFC)
    # Enveloppe pour la 1ère partie du pipeline pydeseq2 avant d'utiliser DeseqStats()
    dds.deseq2()

    ds = DeseqStats(dds)
    ds.summary()

    return dds, ds

def post_filt(res_df, dds, alpha_thres, lfc_thres):
    # Filtrer les gènes pour garder ceux qui sont expressés différentiellement de façon statistiquement significative (inférieur à alpha_thres)
    # et avec un plus grande variation d'expression génique (supérieur à lfc_thres)
    filt_res_df = res_df[(res_df.padj < alpha_thres) & (abs(res_df.log2FoldChange) > lfc_thres)]

    # Filter dds avec les index des gènes de filt_res_df
    filt_dds = dds[:,filt_res_df.index]
    return filt_res_df, filt_dds

def plot_heatmap(dea_df):
    clustermap_data = pd.DataFrame(dea_df.layers['log1p'].T, index=dea_df.var_names, columns=dea_df.obs_names)
    new_virtual_file = io.BytesIO()

    sns.clustermap(clustermap_data, z_score=0, cmap='RdYlBu_r')
    plt.title('Heatmap')
    plt.savefig(new_virtual_file, bbox_inches='tight', format='png')
    plt.close()

    base64_file = base64.b64encode(new_virtual_file.getvalue()).decode()
    return base64_file

def plot_volcanoplot(volcano_data, volcano_data_filt, alpha_thres):
    volcano_data['-log10(padj)'] = -np.log10(volcano_data['padj'] + 1e-200)  
    volcano_data_filt['-log10(padj)'] = -np.log10(volcano_data_filt['padj'] + 1e-200)
    new_virtual_file = io.BytesIO()

    sns.scatterplot(x='log2FoldChange', y='-log10(padj)', data=volcano_data, color='grey', alpha=0.5)
    sns.scatterplot(x='log2FoldChange', y='-log10(padj)', data=volcano_data_filt, color='red')

    plt.axhline(y=-np.log10(alpha_thres + 1e-200), color='black', linestyle='--', linewidth=1)
    plt.xlabel('Log2 Fold Change')
    plt.ylabel('-log10(padj)')
    plt.title('Volcano Plot')
    plt.savefig(new_virtual_file, bbox_inches='tight', format='png')
    plt.close()

    base64_file = base64.b64encode(new_virtual_file.getvalue()).decode()
    return base64_file

# Affichage des résultats
def affichage_results(counts_file, metadata_file, design_factor, refit_cooks, min_reads_per_gene, alpha_thres, lfc_thres, dds, ds, filt_results_df):
    results = f"counts_file:{str(counts_file.rsplit('/', 1)[-1])}\n"
    results += f"metadata_file:{str(metadata_file.rsplit('/', 1)[-1])}\n"
    results += f"refit_cooks:{str(refit_cooks)}\n"
    results += f"min_reads_per_gene:{str(min_reads_per_gene)}\n"
    results += f"design_factor:{ds.contrast[0]}\n"
    results += f"condition_1:{ds.contrast[1]}\n"
    results += f"condition_2:{ds.contrast[2]}\n"
    results += f"alpha_thres:{alpha_thres}\nlfc_thres:{lfc_thres}\n"
    results += f"matrice:{filt_results_df.to_string()}"
    #results += f"1. DDS Dispersions:\n{str(dds.varm['dispersions'])}\n\n"
    #results += f"2. DDS LFC (log fold change):\n{str(dds.varm['LFC'])}\n\n"
    #results += f"3. DDS Outlier Genes:\n{str(dds.varm['_outlier_genes'])}\n\n"
    return results


# Analyse d'expression genetique differentiel
def analyse_dea(counts_file, metadata_file, refit_cooks, min_reads_per_gene, alpha_thres, lfc_thres):
    # DATA PREPROCESSING
    # Pré-filtrer des fichiers counts, metadata
    counts, metadata = preprocess_df(counts_file, metadata_file, min_reads_per_gene)

    # Récupérer design_factor
    design_factor = get_design_factor(metadata)

    # EXECUTER PIPELINE PYDESEQ2
    dds, ds = pipeline_pydeseq(counts, metadata, design_factor, refit_cooks)

    # POST PROCESSING
    # Effectue une transformation logarithmique sur les données contenues dans dds.layers['normed_counts']
    # et enregistre le résultat dans dds.layers['log1p'] nécessaire pour le heatmap
    dds.layers['log1p'] = np.log1p(dds.layers['normed_counts'])

    # Filtration pour avoir les genes significativement et hautement differentiel
    filt_results_df, filt_dds = post_filt(ds.results_df, dds, alpha_thres, lfc_thres)

    # HEATMAP
    heatmap_path = plot_heatmap(filt_dds)
    
    # VOLCANO PLOT
    # créer une copie du ds.results_df et ds.results_df filtré avec alpha_thres et lfc_thres pour ajouter une colone '-log10(padj)'à ces dataframes
    volcano_data = ds.results_df.copy()
    volcano_data_filt = filt_results_df.copy()

    volcanoplot_path = plot_volcanoplot(volcano_data, volcano_data_filt, alpha_thres)

    
    # RESULTS : à changer au fur et à mesure que j'ajoute des informations à afficher en sortie
    results = affichage_results(counts_file, metadata_file, design_factor, refit_cooks, min_reads_per_gene, alpha_thres, lfc_thres, dds, ds, filt_results_df)
    return results, heatmap_path, volcanoplot_path