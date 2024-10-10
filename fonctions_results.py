# fonctions_results.py
# traiter_results() traite le run.text_results stocké dans la BD pour chaque analyse pour créer un dictionnaire des informations dans le texte

def traiter_results(texte):
    result_dict = {} # dictionnaire pour stocker chaque pair de key:value dans chaque ligne
    lines = texte.split('\n')
    for line in lines:
        if ':' in line:
            key, value = line.split(':', 1)
            result_dict[key.strip()] = value.strip()

    # Traitement separe du key 'matrice' pour ne pas separer les lignes
    matrice_index = texte.find('matrice:')
    if matrice_index != -1:
        result_dict['matrice'] = texte[matrice_index + len('matrice:'):].strip()
        
        # les 2 premières lignes sont mals alignés donc il faut les enlever et les remplacer par une ligne wui contient les noms des colonnes
        matrice_lines = result_dict['matrice'].split('\n')
        matrice_lines = matrice_lines[2:]
        
        # rejoin les lignes
        result_dict['matrice'] = '\n'.join(matrice_lines)
        # definir la premiere ligne qui sert de noms de colonnes
        column_names = 'Geneid              baseMean    log2FoldChange   lfcSE     stat       pvalue          pdj\n'
        # join cette ligne
        matrice_value = column_names + '\n'.join(matrice_lines)
        # Update the result_dict
        result_dict['matrice'] = matrice_value

    return result_dict

